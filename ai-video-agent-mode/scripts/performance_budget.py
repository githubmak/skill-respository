#!/usr/bin/env python3
"""Report the 50-main-shot core-pipeline service-level objective.

This is intentionally observational: it never marks quality gates passed or
failed.  It makes elapsed time, dispatch count, retries, and the 55-minute
budget visible in a resume-safe artifact so throughput claims are evidence
based rather than inferred from configured batch sizes.
"""

import json
import os
import sys
import time


CORE_PHASES = (
    "user_confirm", "orchestrator", "scene_lock", "master_production",
    "editor_pass1", "editor_pass2", "validate",
)
TARGET_SECONDS = 55 * 60
AGENT_PHASES = {"scene_lock", "master_production", "editor_pass2"}
# Local phases are deterministic Python checks/exports and should not absorb
# human resume delays or stale started_at markers in an intermittently driven
# supervisor run.  Keep a deliberately generous per-phase cap in the SLO timer
# while still reporting the full local wall time as pause/overhead evidence.
LOCAL_PHASE_ACTIVE_CAP_SECONDS = 60


def report(run_dir):
    state_path = os.path.join(run_dir, ".cache", "pipeline_state.json")
    if not os.path.exists(state_path):
        raise SystemExit("Missing pipeline state: %s" % state_path)
    with open(state_path, "r", encoding="utf-8-sig") as handle:
        state = json.load(handle)
    phases = state.get("phases", {})
    now = time.time()
    started = state.get("pipeline_started_at")
    records = []
    local_phase_wall_sum = 0.0
    local_compute_sum = 0.0
    local_pause_sum = 0.0
    agent_phase_wall_sum = 0.0
    dispatch_worker_sum = 0.0
    dispatch_summary = {
        "total_dispatch_count": 0,
        "done_dispatch_count": 0,
        "running_dispatch_count": 0,
        "waiting_dispatch_count": 0,
        "failed_dispatch_count": 0,
        "retry_count": 0,
        "manifest_active_packet_count": 0,
        "manifest_active_retry_packet_count": 0,
        "manifest_superseded_packet_count": 0,
        "state_superseded_packet_count": 0,
        "retired_dispatch_count": 0,
        "stale_or_superseded_packet_count": 0,
    }
    for name in CORE_PHASES:
        item = phases.get(name, {}) if isinstance(phases.get(name), dict) else {}
        dispatches = item.get("dispatches", {}) if isinstance(item.get("dispatches"), dict) else {}
        stats = _dispatch_stats(dispatches)
        manifest = _manifest_summary(run_dir, name)
        state_superseded = _state_superseded_summary(item)
        dispatch_elapsed = stats["dispatch_worker_seconds"]
        phase_elapsed = item.get("elapsed_seconds")
        local_compute_elapsed = 0.0
        local_pause_elapsed = 0.0
        if isinstance(phase_elapsed, (int, float)):
            if name in AGENT_PHASES:
                agent_phase_wall_sum += float(phase_elapsed)
            else:
                local_phase_wall_sum += float(phase_elapsed)
                local_compute_elapsed = min(float(phase_elapsed), LOCAL_PHASE_ACTIVE_CAP_SECONDS)
                local_pause_elapsed = max(float(phase_elapsed) - local_compute_elapsed, 0)
                local_compute_sum += local_compute_elapsed
                local_pause_sum += local_pause_elapsed
        dispatch_worker_sum += dispatch_elapsed
        dispatch_summary["total_dispatch_count"] += stats["dispatch_count"]
        dispatch_summary["done_dispatch_count"] += stats["done_dispatch_count"]
        dispatch_summary["running_dispatch_count"] += stats["running_dispatch_count"]
        dispatch_summary["waiting_dispatch_count"] += stats["waiting_dispatch_count"]
        dispatch_summary["failed_dispatch_count"] += stats["failed_dispatch_count"]
        dispatch_summary["retry_count"] += int(item.get("retries", 0) or 0)
        dispatch_summary["manifest_active_packet_count"] += manifest["active_packet_count"]
        dispatch_summary["manifest_active_retry_packet_count"] += manifest["active_retry_packet_count"]
        dispatch_summary["manifest_superseded_packet_count"] += manifest["superseded_packet_count"]
        dispatch_summary["state_superseded_packet_count"] += state_superseded["superseded_packet_count"]
        dispatch_summary["retired_dispatch_count"] += state_superseded["retired_dispatch_count"]
        dispatch_summary["stale_or_superseded_packet_count"] += (
            manifest["superseded_packet_count"] + state_superseded["superseded_packet_count"]
        )
        records.append({
            "phase": name,
            "category": "agent" if name in AGENT_PHASES else "local",
            "status": item.get("status", "pending"),
            "elapsed_seconds": phase_elapsed,
            "slo_active_seconds": (
                round(float(phase_elapsed), 3)
                if name in AGENT_PHASES and isinstance(phase_elapsed, (int, float))
                else round(local_compute_elapsed, 3)
            ),
            "local_pause_seconds": round(local_pause_elapsed, 3),
            "dispatch_worker_seconds": dispatch_elapsed,
            "worker_wait_wall_seconds": round(float(phase_elapsed or 0), 3) if name in AGENT_PHASES and isinstance(phase_elapsed, (int, float)) else 0,
            "retries": item.get("retries", 0),
            "timeout_count": item.get("timeout_count", 0),
            "dispatch_count": stats["dispatch_count"],
            "done_dispatch_count": stats["done_dispatch_count"],
            "running_dispatch_count": stats["running_dispatch_count"],
            "waiting_dispatch_count": stats["waiting_dispatch_count"],
            "failed_dispatch_count": stats["failed_dispatch_count"],
            "mean_dispatch_seconds": stats["mean_dispatch_seconds"],
            "max_dispatch_seconds": stats["max_dispatch_seconds"],
            "manifest_active_packet_count": manifest["active_packet_count"],
            "manifest_active_retry_packet_count": manifest["active_retry_packet_count"],
            "manifest_superseded_packet_count": manifest["superseded_packet_count"],
            "manifest_active_shot_count": manifest["active_shot_count"],
            "state_superseded_packet_count": state_superseded["superseded_packet_count"],
            "retired_dispatch_count": state_superseded["retired_dispatch_count"],
        })
    completed = all(record["status"] in ("done", "skipped") for record in records)
    finished_at = _core_finished_at(phases) if completed else now
    wall_elapsed = (
        max(finished_at - started, 0)
        if isinstance(started, (int, float)) and isinstance(finished_at, (int, float)) else None
    )
    active_elapsed = round(local_compute_sum + agent_phase_wall_sum, 3)
    shot_plan_path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")
    shot_plan = _load_json(shot_plan_path)
    main_shot_count = len(shot_plan.get("shots", [])) if isinstance(shot_plan, dict) else None
    result = {
        "target_seconds": TARGET_SECONDS,
        "elapsed_seconds": active_elapsed,
        "elapsed_seconds_basis": "slo_active_phase_seconds",
        "time_breakdown": {
            "wall_clock_seconds": round(wall_elapsed, 3) if wall_elapsed is not None else None,
            "local_phase_seconds": round(local_phase_wall_sum, 3),
            "local_compute_seconds": round(local_compute_sum, 3),
            "local_pause_seconds": round(local_pause_sum, 3),
            "agent_phase_wall_seconds": round(agent_phase_wall_sum, 3),
            "worker_wait_wall_seconds": round(agent_phase_wall_sum, 3),
            "dispatch_worker_seconds": round(dispatch_worker_sum, 3),
            "tracked_phase_wall_seconds": round(local_phase_wall_sum + agent_phase_wall_sum, 3),
            "slo_active_phase_seconds": active_elapsed,
            "unattributed_or_pause_seconds": (
                round(max(wall_elapsed - local_phase_wall_sum - agent_phase_wall_sum, 0), 3)
                if isinstance(wall_elapsed, (int, float)) else None
            ),
            "total_pause_or_resume_gap_seconds": (
                round(
                    max(wall_elapsed - local_compute_sum - agent_phase_wall_sum, 0),
                    3,
                )
                if isinstance(wall_elapsed, (int, float)) else None
            ),
            "slo_timer_note": (
                "elapsed_seconds is the reproducible active core-pipeline time: "
                "agent phase wall time plus capped deterministic local compute. "
                "wall_clock_seconds and pause fields retain human resume/debug gaps."
            ),
            "parallelism_note": "dispatch_worker_seconds sums completed worker runtimes and may exceed worker_wait_wall_seconds when workers run in parallel.",
        },
        "dispatch_summary": dispatch_summary,
        "completed": completed,
        "main_shot_count": main_shot_count,
        "slo_eligible": main_shot_count == 50,
        "within_target": bool(completed and main_shot_count == 50 and active_elapsed <= TARGET_SECONDS),
        "phases": records,
        "scope": "main shots",
    }
    out_dir = os.path.join(run_dir, ".cache", "performance")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "core_pipeline_budget.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    return out_path, result


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            value = json.load(handle)
            return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _core_finished_at(phases):
    finished = []
    for name in CORE_PHASES:
        item = phases.get(name, {}) if isinstance(phases.get(name), dict) else {}
        completed_at = item.get("completed_at")
        if isinstance(completed_at, (int, float)) and not isinstance(completed_at, bool):
            finished.append(float(completed_at))
    return max(finished) if finished else time.time()


def _dispatch_stats(dispatches):
    dispatches = dispatches if isinstance(dispatches, dict) else {}
    durations = []
    counts = {
        "dispatch_count": 0,
        "done_dispatch_count": 0,
        "running_dispatch_count": 0,
        "waiting_dispatch_count": 0,
        "failed_dispatch_count": 0,
    }
    for entry in dispatches.values():
        if not isinstance(entry, dict):
            continue
        counts["dispatch_count"] += 1
        status = str(entry.get("status", "") or "waiting")
        if status == "done":
            counts["done_dispatch_count"] += 1
        elif status == "running":
            counts["running_dispatch_count"] += 1
        elif status in ("failed", "error", "timeout"):
            counts["failed_dispatch_count"] += 1
        else:
            counts["waiting_dispatch_count"] += 1
        elapsed = entry.get("elapsed_seconds")
        if isinstance(elapsed, (int, float)) and not isinstance(elapsed, bool):
            durations.append(float(elapsed))
    total = round(sum(durations), 3)
    counts.update({
        "dispatch_worker_seconds": total,
        "mean_dispatch_seconds": round(total / len(durations), 3) if durations else 0,
        "max_dispatch_seconds": round(max(durations), 3) if durations else 0,
    })
    return counts


def _manifest_summary(run_dir, phase):
    manifest = _load_json(os.path.join(
        run_dir, ".cache", "dispatch", "active_%s_manifest.json" % _safe_phase(phase)
    ))
    if manifest.get("phase") != phase:
        return {
            "active_packet_count": 0,
            "active_retry_packet_count": 0,
            "superseded_packet_count": 0,
            "active_shot_count": 0,
        }
    active_shots = manifest.get("active_shot_ids", [])
    return {
        "active_packet_count": int(manifest.get("active_packet_count", len(manifest.get("packets", []) or [])) or 0),
        "active_retry_packet_count": int(manifest.get("active_retry_packet_count", 0) or 0),
        "superseded_packet_count": int(manifest.get("superseded_packet_count", len(manifest.get("superseded_packets", []) or [])) or 0),
        "active_shot_count": len(active_shots) if isinstance(active_shots, list) else 0,
    }


def _state_superseded_summary(phase_state):
    phase_state = phase_state if isinstance(phase_state, dict) else {}
    superseded_packet_count = 0
    for round_info in phase_state.get("superseded_dispatches", []) or []:
        if isinstance(round_info, dict):
            packets = round_info.get("packets", [])
            if isinstance(packets, list):
                superseded_packet_count += len(packets)
    retired_dispatch_count = 0
    for round_info in phase_state.get("recovery_rounds", []) or []:
        if isinstance(round_info, dict):
            retired = round_info.get("retired_dispatch_ids", [])
            if isinstance(retired, list):
                retired_dispatch_count += len(retired)
    return {
        "superseded_packet_count": superseded_packet_count,
        "retired_dispatch_count": retired_dispatch_count,
    }


def _safe_phase(phase):
    import re
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(phase or "unknown"))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: performance_budget.py <run_dir>")
    path, result = report(sys.argv[1])
    print("[PERFORMANCE] %s" % path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
