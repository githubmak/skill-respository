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
    "user_confirm", "orchestrator", "master_production",
    "editor_pass1", "editor_pass2", "validate",
)
TARGET_SECONDS = 55 * 60
AGENT_PHASES = {"master_production", "editor_pass2"}
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
    provenance_by_phase = _provenance_summary(run_dir)
    now = time.time()
    started = state.get("pipeline_started_at")
    records = []
    local_phase_wall_sum = 0.0
    local_compute_sum = 0.0
    local_pause_sum = 0.0
    agent_phase_wall_sum = 0.0
    worker_active_union_sum = 0.0
    agent_idle_gap_sum = 0.0
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
        "exact_token_dispatch_count": 0,
        "unavailable_token_dispatch_count": 0,
        "exact_input_tokens": 0,
        "exact_output_tokens": 0,
        "exact_total_tokens": 0,
        "checkpoint_count": 0,
        "completed_item_count": 0,
        "mean_time_to_first_progress_seconds": None,
        "max_time_to_first_progress_seconds": None,
        "absolute_packet_timeout_count": 0,
        "startup_content_stall_count": 0,
        "content_progress_stall_count": 0,
        "verified_reuse_phase_count": 0,
        "verified_reuse_item_count": 0,
    }
    all_first_progress_times = []
    for name in CORE_PHASES:
        item = phases.get(name, {}) if isinstance(phases.get(name), dict) else {}
        dispatches = item.get("dispatches", {}) if isinstance(item.get("dispatches"), dict) else {}
        stats = _dispatch_stats(dispatches)
        manifest = _manifest_summary(run_dir, name)
        state_superseded = _state_superseded_summary(item)
        telemetry = provenance_by_phase.get(name, _empty_provenance_summary())
        retirements = _retirement_summary(item)
        dispatch_elapsed = stats["dispatch_worker_seconds"]
        worker_active_union = _dispatch_active_union_seconds(dispatches)
        agent_idle_gap = 0.0
        reported_phase_elapsed = item.get("elapsed_seconds")
        phase_elapsed = reported_phase_elapsed
        if name in AGENT_PHASES:
            inferred_phase_elapsed = _agent_phase_wall_seconds(item, dispatches, now)
            if inferred_phase_elapsed is not None:
                phase_elapsed = max(float(reported_phase_elapsed or 0), inferred_phase_elapsed)
        local_compute_elapsed = 0.0
        local_pause_elapsed = 0.0
        if isinstance(phase_elapsed, (int, float)):
            if name in AGENT_PHASES:
                agent_phase_wall_sum += float(phase_elapsed)
                worker_active_union_sum += min(worker_active_union, float(phase_elapsed))
                agent_idle_gap = max(float(phase_elapsed) - worker_active_union, 0)
                agent_idle_gap_sum += agent_idle_gap
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
        if item.get("reuse_provenance_path"):
            dispatch_summary["verified_reuse_phase_count"] += 1
            dispatch_summary["verified_reuse_item_count"] += int(item.get("reused_item_count", 0) or 0)
        dispatch_summary["manifest_active_packet_count"] += manifest["active_packet_count"]
        dispatch_summary["manifest_active_retry_packet_count"] += manifest["active_retry_packet_count"]
        dispatch_summary["manifest_superseded_packet_count"] += manifest["superseded_packet_count"]
        dispatch_summary["state_superseded_packet_count"] += state_superseded["superseded_packet_count"]
        dispatch_summary["retired_dispatch_count"] += state_superseded["retired_dispatch_count"]
        dispatch_summary["stale_or_superseded_packet_count"] += (
            manifest["superseded_packet_count"] + state_superseded["superseded_packet_count"]
        )
        for field in (
            "exact_token_dispatch_count", "unavailable_token_dispatch_count",
            "exact_input_tokens", "exact_output_tokens", "exact_total_tokens",
            "checkpoint_count", "completed_item_count",
        ):
            dispatch_summary[field] += telemetry[field]
        all_first_progress_times.extend(telemetry["time_to_first_progress_values"])
        for reason in (
            "absolute_packet_timeout", "startup_content_stall", "content_progress_stall"
        ):
            dispatch_summary[reason + "_count"] += retirements.get(reason, 0)
        records.append({
            "phase": name,
            "category": "agent" if name in AGENT_PHASES else "local",
            "status": item.get("status", "pending"),
            "elapsed_seconds": phase_elapsed,
            "reported_elapsed_seconds": reported_phase_elapsed,
            "slo_active_seconds": (
                round(float(phase_elapsed), 3)
                if name in AGENT_PHASES and isinstance(phase_elapsed, (int, float))
                else round(local_compute_elapsed, 3)
            ),
            "local_pause_seconds": round(local_pause_elapsed, 3),
            "dispatch_worker_seconds": dispatch_elapsed,
            "worker_wait_wall_seconds": round(float(phase_elapsed or 0), 3) if name in AGENT_PHASES and isinstance(phase_elapsed, (int, float)) else 0,
            "worker_active_union_seconds": round(min(worker_active_union, float(phase_elapsed or 0)), 3) if name in AGENT_PHASES else 0,
            "agent_idle_gap_seconds": round(agent_idle_gap, 3) if name in AGENT_PHASES else 0,
            "verified_reuse": bool(item.get("reuse_provenance_path")),
            "reused_item_count": int(item.get("reused_item_count", 0) or 0),
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
            "token_usage": {
                "exact_dispatch_count": telemetry["exact_token_dispatch_count"],
                "unavailable_dispatch_count": telemetry["unavailable_token_dispatch_count"],
                "input_tokens": telemetry["exact_input_tokens"],
                "output_tokens": telemetry["exact_output_tokens"],
                "total_tokens": telemetry["exact_total_tokens"],
            },
            "checkpoint_count": telemetry["checkpoint_count"],
            "completed_item_count": telemetry["completed_item_count"],
            "mean_time_to_first_progress_seconds": telemetry["mean_time_to_first_progress_seconds"],
            "max_time_to_first_progress_seconds": telemetry["max_time_to_first_progress_seconds"],
            "stall_retirements": retirements,
        })
    if all_first_progress_times:
        dispatch_summary["mean_time_to_first_progress_seconds"] = round(
            sum(all_first_progress_times) / len(all_first_progress_times), 3
        )
        dispatch_summary["max_time_to_first_progress_seconds"] = round(
            max(all_first_progress_times), 3
        )
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
        "elapsed_seconds": round(wall_elapsed, 3) if wall_elapsed is not None else active_elapsed,
        "elapsed_seconds_basis": "pipeline_state_wall_clock_seconds",
        "time_breakdown": {
            "wall_clock_seconds": round(wall_elapsed, 3) if wall_elapsed is not None else None,
            "local_phase_seconds": round(local_phase_wall_sum, 3),
            "local_compute_seconds": round(local_compute_sum, 3),
            "local_pause_seconds": round(local_pause_sum, 3),
            "agent_phase_wall_seconds": round(agent_phase_wall_sum, 3),
            "worker_wait_wall_seconds": round(agent_phase_wall_sum, 3),
            "worker_active_union_seconds": round(worker_active_union_sum, 3),
            "agent_idle_gap_seconds": round(agent_idle_gap_sum, 3),
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
            "non_worker_wall_seconds": (
                round(max(wall_elapsed - local_compute_sum - worker_active_union_sum, 0), 3)
                if isinstance(wall_elapsed, (int, float)) else None
            ),
            "slo_timer_note": (
                "elapsed_seconds starts at pipeline state initialization and excludes pre-initialization "
                "configuration/process startup. worker_active_union_seconds "
                "counts wall time with at least one registered worker active; "
                "agent_idle_gap_seconds exposes queue refill, host polling, and phase-finalization gaps."
            ),
            "parallelism_note": "dispatch_worker_seconds sums completed worker runtimes and may exceed worker_wait_wall_seconds when workers run in parallel.",
        },
        "dispatch_summary": dispatch_summary,
        "token_telemetry": {
            "status": "exact_for_reported_dispatches_only",
            "exact_dispatch_count": dispatch_summary["exact_token_dispatch_count"],
            "unavailable_dispatch_count": dispatch_summary["unavailable_token_dispatch_count"],
            "input_tokens": dispatch_summary["exact_input_tokens"],
            "output_tokens": dispatch_summary["exact_output_tokens"],
            "total_tokens": dispatch_summary["exact_total_tokens"],
            "note": "No token estimate is fabricated when host telemetry is unavailable.",
        },
        "completed": completed,
        "main_shot_count": main_shot_count,
        "slo_eligible": main_shot_count == 50,
        "within_target": bool(
            completed and main_shot_count == 50
            and isinstance(wall_elapsed, (int, float)) and wall_elapsed <= TARGET_SECONDS
        ),
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
        elif status in ("failed", "error", "timeout", "timed_out"):
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


def _dispatch_active_union_seconds(dispatches):
    """Return wall time covered by at least one registered worker interval."""
    intervals = []
    for entry in dispatches.values() if isinstance(dispatches, dict) else []:
        if not isinstance(entry, dict):
            continue
        start = entry.get("spawn_time")
        end = entry.get("recorded_at")
        if not isinstance(start, (int, float)) or isinstance(start, bool):
            continue
        if not isinstance(end, (int, float)) or isinstance(end, bool) or end < start:
            continue
        intervals.append((float(start), float(end)))
    if not intervals:
        return 0.0
    intervals.sort()
    total = 0.0
    current_start, current_end = intervals[0]
    for start, end in intervals[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            total += current_end - current_start
            current_start, current_end = start, end
    total += current_end - current_start
    return round(total, 3)


def _agent_phase_wall_seconds(phase_state, dispatches, now):
    """Rebuild phase wall time when legacy worker registration overwrote it."""
    starts = []
    phase_started = phase_state.get("started_at") if isinstance(phase_state, dict) else None
    if isinstance(phase_started, (int, float)) and not isinstance(phase_started, bool):
        starts.append(float(phase_started))
    for entry in dispatches.values() if isinstance(dispatches, dict) else []:
        start = entry.get("spawn_time") if isinstance(entry, dict) else None
        if isinstance(start, (int, float)) and not isinstance(start, bool):
            starts.append(float(start))
    if not starts:
        return None
    completed = phase_state.get("completed_at") if isinstance(phase_state, dict) else None
    end = float(completed) if isinstance(completed, (int, float)) and not isinstance(completed, bool) else float(now)
    return round(max(end - min(starts), 0), 3)


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
    retired_dispatch_count = sum(
        1 for entry in (phase_state.get("dispatches", {}) or {}).values()
        if isinstance(entry, dict) and str(entry.get("retirement_reason", "")).strip()
    )
    for round_info in phase_state.get("recovery_rounds", []) or []:
        if isinstance(round_info, dict):
            retired = round_info.get("retired_dispatch_ids", [])
            if isinstance(retired, list):
                retired_dispatch_count = max(retired_dispatch_count, len(retired))
    return {
        "superseded_packet_count": superseded_packet_count,
        "retired_dispatch_count": retired_dispatch_count,
    }


def _empty_provenance_summary():
    return {
        "exact_token_dispatch_count": 0,
        "unavailable_token_dispatch_count": 0,
        "exact_input_tokens": 0,
        "exact_output_tokens": 0,
        "exact_total_tokens": 0,
        "checkpoint_count": 0,
        "completed_item_count": 0,
        "time_to_first_progress_values": [],
        "mean_time_to_first_progress_seconds": None,
        "max_time_to_first_progress_seconds": None,
    }


def _provenance_summary(run_dir):
    directory = os.path.join(run_dir, ".cache", "provenance")
    result = {}
    seen = set()
    if not os.path.isdir(directory):
        return result
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        manifest = _load_json(os.path.join(directory, name))
        dispatch_id = str(manifest.get("dispatch_id", "") or "")
        phase = str(manifest.get("phase", "") or "")
        if not dispatch_id or not phase or manifest.get("validated") is not True:
            continue
        identity = (phase, dispatch_id)
        if identity in seen:
            continue
        seen.add(identity)
        summary = result.setdefault(phase, _empty_provenance_summary())
        token_usage = manifest.get("token_usage", {})
        if isinstance(token_usage, dict) and token_usage.get("status") == "exact":
            summary["exact_token_dispatch_count"] += 1
            summary["exact_input_tokens"] += int(token_usage.get("input_tokens", 0) or 0)
            summary["exact_output_tokens"] += int(token_usage.get("output_tokens", 0) or 0)
            summary["exact_total_tokens"] += int(token_usage.get("total_tokens", 0) or 0)
        else:
            summary["unavailable_token_dispatch_count"] += 1
        summary["checkpoint_count"] += int(manifest.get("checkpoint_count", 0) or 0)
        summary["completed_item_count"] += int(manifest.get("completed_item_count", 0) or 0)
        first = manifest.get("time_to_first_progress_seconds")
        if isinstance(first, (int, float)) and not isinstance(first, bool):
            summary["time_to_first_progress_values"].append(float(first))
    for summary in result.values():
        values = summary["time_to_first_progress_values"]
        if values:
            summary["mean_time_to_first_progress_seconds"] = round(sum(values) / len(values), 3)
            summary["max_time_to_first_progress_seconds"] = round(max(values), 3)
    return result


def _retirement_summary(phase_state):
    counts = {
        "absolute_packet_timeout": 0,
        "startup_content_stall": 0,
        "content_progress_stall": 0,
    }
    dispatches = phase_state.get("dispatches", {}) if isinstance(phase_state, dict) else {}
    for entry in dispatches.values() if isinstance(dispatches, dict) else []:
        reason = str(entry.get("retirement_reason", "") or "") if isinstance(entry, dict) else ""
        if reason in counts:
            counts[reason] += 1
    return counts


def _safe_phase(phase):
    import re
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(phase or "unknown"))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: performance_budget.py <run_dir>")
    path, result = report(sys.argv[1])
    print("[PERFORMANCE] %s" % path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
