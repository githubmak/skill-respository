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


def report(run_dir):
    state_path = os.path.join(run_dir, ".cache", "pipeline_state.json")
    if not os.path.exists(state_path):
        raise SystemExit("Missing pipeline state: %s" % state_path)
    with open(state_path, "r", encoding="utf-8-sig") as handle:
        state = json.load(handle)
    phases = state.get("phases", {})
    now = time.time()
    started = state.get("pipeline_started_at")
    elapsed = max(now - started, 0) if isinstance(started, (int, float)) else None
    records = []
    for name in CORE_PHASES:
        item = phases.get(name, {}) if isinstance(phases.get(name), dict) else {}
        records.append({
            "phase": name,
            "status": item.get("status", "pending"),
            "elapsed_seconds": item.get("elapsed_seconds"),
            "retries": item.get("retries", 0),
            "timeout_count": item.get("timeout_count", 0),
            "dispatch_count": len(item.get("dispatches", {})) if isinstance(item.get("dispatches"), dict) else 0,
        })
    completed = all(record["status"] in ("done", "skipped") for record in records)
    result = {
        "target_seconds": TARGET_SECONDS,
        "elapsed_seconds": round(elapsed, 3) if elapsed is not None else None,
        "completed": completed,
        "within_target": bool(completed and elapsed is not None and elapsed <= TARGET_SECONDS),
        "phases": records,
        "excludes_optional_grid_storyboard": True,
    }
    out_dir = os.path.join(run_dir, ".cache", "performance")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "core_pipeline_budget.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    return out_path, result


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: performance_budget.py <run_dir>")
    path, result = report(sys.argv[1])
    print("[PERFORMANCE] %s" % path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
