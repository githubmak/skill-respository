#!/usr/bin/env python3
"""Hard wall-clock deadline and completion-feasibility gate."""

import json
import math
import os
import time

from contract_registry import (
    PHASE_PLANNING_SECONDS,
    PIPELINE_DEADLINE_WARNING_SECONDS,
    PIPELINE_HARD_DEADLINE_SECONDS,
    PIPELINE_WORKER_SLOT_CAP,
    PIPELINE_PHASES,
)
from pipeline_runtime import atomic_json


REPORT_RELATIVE_PATH = os.path.join(".cache", "control", "fuse_report.json")
TERMINAL_STATUSES = {"done", "skipped"}


def ensure_state_contract(state, now=None):
    """Add deadline fields to new and resumable states without resetting time."""
    now = float(now if now is not None else time.time())
    started = state.get("pipeline_started_at")
    if not isinstance(started, (int, float)):
        started = now
        state["pipeline_started_at"] = started
    state.setdefault("pipeline_deadline_seconds", PIPELINE_HARD_DEADLINE_SECONDS)
    state.setdefault("pipeline_deadline_at", float(started) + PIPELINE_HARD_DEADLINE_SECONDS)
    state.setdefault("pipeline_status", "running")
    return state


def status(state, now=None):
    now = float(now if now is not None else time.time())
    ensure_state_contract(state, now)
    started = float(state["pipeline_started_at"])
    deadline = float(state["pipeline_deadline_at"])
    remaining = max(deadline - now, 0.0)
    return {
        "started_at": started,
        "deadline_at": deadline,
        "elapsed_seconds": round(max(now - started, 0.0), 3),
        "remaining_seconds": round(remaining, 3),
        "warning": 0 < remaining <= PIPELINE_DEADLINE_WARNING_SECONDS,
        "expired": now >= deadline,
    }


def estimate_remaining_seconds(run_dir, state, packet_count=None, worker_slots=None):
    """Estimate remaining wall time from queue waves and bounded phase targets."""
    phase = str(state.get("current_phase", "") or "")
    phases = state.get("phases", {}) if isinstance(state.get("phases"), dict) else {}
    try:
        current_index = list(PIPELINE_PHASES).index(phase)
    except ValueError:
        return 0
    config = _load(os.path.join(run_dir, "project_config.json"))
    configured_slots = ((config.get("execution") or {}).get("worker_slots")
                        if isinstance(config.get("execution"), dict) else None)
    slots = min(max(int(worker_slots or configured_slots or PIPELINE_WORKER_SLOT_CAP), 1),
                PIPELINE_WORKER_SLOT_CAP)
    estimate = 0.0
    for name in PIPELINE_PHASES[current_index:]:
        phase_state = phases.get(name, {}) if isinstance(phases.get(name), dict) else {}
        if phase_state.get("status") in TERMINAL_STATUSES:
            continue
        target = float(PHASE_PLANNING_SECONDS.get(name, 60))
        if name == phase and packet_count is not None and name in {"scene_lock", "master_production", "editor_pass2"}:
            waves = int(math.ceil(max(int(packet_count), 0) / float(slots)))
            estimate += waves * target
        else:
            estimate += target
    return round(estimate, 3)


def feasibility(run_dir, state, packet_count=None, worker_slots=None, now=None):
    budget = status(state, now)
    estimate = estimate_remaining_seconds(run_dir, state, packet_count, worker_slots)
    return dict(
        budget,
        estimated_remaining_seconds=estimate,
        feasible=(not budget["expired"] and estimate <= budget["remaining_seconds"]),
    )


def fuse(run_dir, state, reason, now=None, forecast=None):
    """Stop the pipeline durably and write the mandatory user-facing report."""
    now = float(now if now is not None else time.time())
    budget = status(state, now)
    phase = str(state.get("current_phase", "") or "")
    phase_state = state.get("phases", {}).get(phase, {})
    retired = []
    for dispatch_id, entry in (phase_state.get("dispatches", {}) or {}).items():
        if not isinstance(entry, dict) or entry.get("status") not in {"running", "waiting"}:
            continue
        entry["status"] = "fused"
        entry["fused_at"] = now
        entry["fuse_reason"] = reason
        retired.append(str(dispatch_id))
    if isinstance(phase_state, dict) and phase_state.get("status") not in TERMINAL_STATUSES:
        phase_state["status"] = "fused"
        phase_state["fused_at"] = now
    state["pipeline_status"] = "fused"
    state["fused_at"] = now
    state["fuse_reason"] = reason
    report = {
        "status": "fused",
        "reason": reason,
        "current_phase": phase,
        "started_at": budget["started_at"],
        "deadline_at": budget["deadline_at"],
        "stopped_at": now,
        "elapsed_seconds": budget["elapsed_seconds"],
        "remaining_seconds": budget["remaining_seconds"],
        "forecast": forecast or {},
        "completed_phases": [
            name for name, entry in state.get("phases", {}).items()
            if isinstance(entry, dict) and entry.get("status") in TERMINAL_STATUSES
        ],
        "retired_dispatch_ids": retired,
        "existing_artifacts": _existing_artifacts(run_dir),
        "resume_allowed": False,
        "next_step": "start a new run after fixing the reported throughput or worker failure",
    }
    state["fuse_report_path"] = os.path.join(run_dir, REPORT_RELATIVE_PATH)
    atomic_json(state["fuse_report_path"], report)
    return report


def _existing_artifacts(run_dir):
    relative_paths = (
        ".cache/orchestrator/shot_plan.json",
        ".cache/analysis/scene_locks.json",
        ".cache/composer/merged.prompt_package.json",
        ".cache/review/pre_editor_gate.json",
        ".cache/review/llm_gate_result.json",
        ".cache/validate/result.json",
        ".cache/export/result.json",
    )
    return [os.path.join(run_dir, value) for value in relative_paths if os.path.isfile(os.path.join(run_dir, value))]


def _load(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            value = json.load(handle)
            return value if isinstance(value, dict) else {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
