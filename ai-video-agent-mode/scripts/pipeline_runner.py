"""Current-contract runner: Scene Lock → Master Production → Editor.

There is deliberately no compatibility branch for the former Emotion, Scene,
Camera, Director or Composer stages.  New runs can only enter this pipeline.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pipeline_state import AGENT_PHASES, LOCAL_PHASES, PHASE_BATCH_SIZE, PHASE_TIMEOUT_SECONDS, advance, load_state, save_state, mark_done, mark_waiting
from pipeline_templates import GATES
from dispatch_cache import prepare_dispatch_packets
from dispatch_queue import fill_slots, pending_packet_paths
from merge_agent_outputs import merge_agent_outputs
from record_batch_provenance import verify


def run(run_dir):
    state = load_state(run_dir)
    phase = state["current_phase"]
    gate = GATES.get(phase)
    if not gate:
        return {"action": "completed"}
    if state["phases"][phase].get("status") == "done":
        advance(run_dir)
        return {"action": "advance", "from": phase, "next": load_state(run_dir)["current_phase"]}
    missing = [path for path in gate.get("input", []) if not os.path.exists(os.path.join(run_dir, path))]
    if missing:
        return {"action": "blocked", "phase": phase, "reason": "missing: " + ", ".join(missing)}
    if phase in LOCAL_PHASES:
        # Local phases are deterministic gates whose output is produced by the
        # caller's dedicated scripts.  Do not silently revive old handlers.
        absent = [path for path in gate.get("output", []) if not os.path.exists(os.path.join(run_dir, path))]
        if absent:
            return {"action": "local_action_required", "phase": phase, "expected_outputs": absent}
        mark_done(run_dir, phase)
        advance(run_dir)
        return {"action": "advance", "from": phase, "next": load_state(run_dir)["current_phase"]}
    if phase not in AGENT_PHASES:
        return {"action": "blocked", "phase": phase, "reason": "unknown current-contract phase"}
    packets = pending_packet_paths(run_dir, phase)
    if not packets:
        packets = prepare_dispatch_packets(run_dir, phase, PHASE_BATCH_SIZE.get(phase))
    ready = fill_slots(run_dir, phase, packets)
    if ready:
        return {"action": "spawn", "phase": phase, "dispatch_packets": ready,
                "dispatch_packet": ready[0], "timeout": PHASE_TIMEOUT_SECONDS.get(phase)}
    verified = _verified_packets(run_dir, phase)
    # A phase may only be materialized once *every* packet has provenance and
    # validation.  Previously, one completed batch plus a full worker pool
    # could be merged while sibling packets were still running.
    if len(verified) != len(packets):
        mark_waiting(run_dir, phase)
        return {"action": "waiting", "phase": phase, "verified_batches": len(verified), "total_batches": len(packets)}
    output = os.path.join(run_dir, gate["output"][0])
    _materialize(phase, output, verified)
    if phase == "editor_pass2":
        review = _load(output)
        if not review.get("pass", False):
            from prepare_master_retry import prepare
            packets = prepare(run_dir, output)
            state = load_state(run_dir)
            state["phases"]["master_production"].update({"status": "pending", "agent_id": None})
            state["phases"]["editor_pass2"].update({"status": "pending", "agent_id": None})
            state["current_phase"] = "master_production"
            save_state(run_dir, state)
            return {"action": "field_patch_retry", "phase": "editor_pass2", "next": "master_production",
                    "dispatch_packets": packets, "reason": "scene_window_blocking"}
    mark_done(run_dir, phase)
    advance(run_dir)
    return {"action": "advance", "from": phase, "next": load_state(run_dir)["current_phase"]}


def _verified_packets(run_dir, phase):
    paths = []
    for packet_path in pending_packet_paths(run_dir, phase):
        packet = _load(packet_path)
        output = packet.get("_batch_output_path", "")
        valid, _reason, _manifest = verify(output) if output and os.path.exists(output) else (False, "missing", None)
        if valid:
            paths.append(output)
    return paths


def _materialize(phase, output, batches):
    os.makedirs(os.path.dirname(output), exist_ok=True)
    if phase == "scene_lock":
        scenes = []
        for batch in batches:
            data = _load(batch)
            scenes.extend(data.get("scenes", []))
        with open(output, "w", encoding="utf-8") as handle:
            json.dump({"contract_version": "jimeng-t2v-v1", "scenes": scenes}, handle, ensure_ascii=False, indent=2)
        return
    if phase == "editor_pass2":
        windows = []
        for batch in batches:
            windows.extend(_load(batch).get("windows", []))
        blocking = []
        repair_targets = []
        for window in windows:
            for issue in window.get("blocking", []) if isinstance(window, dict) else []:
                if issue not in blocking:
                    blocking.append(issue)
            for target in window.get("repair_targets", []) if isinstance(window, dict) else []:
                if target not in repair_targets:
                    repair_targets.append(target)
        with open(output, "w", encoding="utf-8") as handle:
            json.dump({"contract_version": "jimeng-t2v-v1", "windows": windows,
                       "pass": bool(windows) and all(item.get("pass") for item in windows),
                       "blocking": blocking, "repair_targets": repair_targets}, handle, ensure_ascii=False, indent=2)
        return
    merge_agent_outputs(output, *batches, require_provenance=True)


def _load(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
