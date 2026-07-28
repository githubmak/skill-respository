"""Current-contract runner: Scene Lock → Master Production → Editor.

There is deliberately no compatibility branch for the former Emotion, Scene,
Camera, Director or Composer stages.  New runs can only enter this pipeline.
"""
import json
import os
import sys
import hashlib
import time

sys.path.insert(0, os.path.dirname(__file__))
from pipeline_state import AGENT_PHASES, LOCAL_PHASES, PHASE_BATCH_SIZE, PHASE_TIMEOUT_SECONDS, advance, load_state, save_state, mark_done, mark_started, mark_waiting
from pipeline_templates import GATES
from dispatch_cache import active_packet_paths, prepare_dispatch_packets
from dispatch_queue import fill_slots, pending_packet_paths
from merge_agent_outputs import merge_agent_outputs
from record_batch_provenance import verify


def run(run_dir):
    state = load_state(run_dir)
    phase = state["current_phase"]
    gate = GATES.get(phase)
    if not gate:
        return {"action": "completed", "requires_user_input": False}
    if state["phases"][phase].get("status") == "done":
        if not _completed_phase_valid(run_dir, phase, gate):
            if phase in LOCAL_PHASES:
                state["phases"][phase].update({
                    "status": "pending",
                    "agent_id": None,
                    "invalidated_at": time.time(),
                    "invalidation_reason": "current artifact hash changed or output missing",
                })
                save_state(run_dir, state)
                return {"action": "local_action_required", "phase": phase,
                        "expected_outputs": gate.get("output", []),
                        "reason": "stale local artifact",
                        "requires_user_input": False}
            return {"action": "blocked", "phase": phase,
                    "reason": "completed phase is missing a current verified artifact",
                    "requires_user_input": False}
        if phase == state.get("phase_order", [])[-1]:
            return {"action": "completed", "requires_user_input": False}
        advance(run_dir)
        return {"action": "advance", "from": phase, "next": load_state(run_dir)["current_phase"],
                "requires_user_input": False}
    missing = [path for path in gate.get("input", []) if not os.path.exists(os.path.join(run_dir, path))]
    if missing:
        return {"action": "blocked", "phase": phase, "reason": "missing: " + ", ".join(missing),
                "requires_user_input": False}
    if phase in LOCAL_PHASES:
        # Local phases are deterministic gates whose output is produced by the
        # caller's dedicated scripts.  Do not silently revive old handlers.
        absent = [path for path in gate.get("output", []) if not os.path.exists(os.path.join(run_dir, path))]
        if absent or not _local_phase_valid(run_dir, phase):
            if not state["phases"][phase].get("started_at"):
                mark_started(run_dir, phase)
            return {"action": "local_action_required", "phase": phase, "expected_outputs": absent,
                    "requires_user_input": False}
        mark_done(run_dir, phase)
        advance(run_dir)
        return {"action": "advance", "from": phase, "next": load_state(run_dir)["current_phase"],
                "requires_user_input": False}
    if phase not in AGENT_PHASES:
        return {"action": "blocked", "phase": phase, "reason": "unknown current-contract phase",
                "requires_user_input": False}
    target_ids = _phase_target_ids(state, phase)
    batch_size = PHASE_BATCH_SIZE.get(phase)
    if phase == "editor_pass2" and target_ids and int(state["phases"][phase].get("targeted_retry_rounds", 0) or 0) >= 2:
        batch_size = 1
    packets = pending_packet_paths(run_dir, phase)
    packets = _current_source_packets(packets)
    if not packets:
        packets = prepare_dispatch_packets(run_dir, phase, batch_size, subshot_ids=target_ids)
    ready = fill_slots(run_dir, phase, packets)
    if ready:
        return {"action": "spawn", "phase": phase, "dispatch_packets": ready,
                "dispatch_packet": ready[0], "timeout": PHASE_TIMEOUT_SECONDS.get(phase),
                "requires_user_input": False,
                "after_spawn": "register_dispatch_agent_then_record_heartbeat_then_record_batch_provenance"}
    verified = _verified_packets(run_dir, phase)
    # A phase may only be materialized once *every* packet has provenance and
    # validation.  Previously, one completed batch plus a full worker pool
    # could be merged while sibling packets were still running.
    if len(verified) != len(packets):
        mark_waiting(run_dir, phase)
        return {
            "action": "wait_for_workers",
            "phase": phase,
            "verified_batches": len(verified),
            "total_batches": len(packets),
            "worker_status": _worker_status(run_dir, phase, packets),
            "requires_user_input": False,
            "automatic_resume": True,
            "next_action": "poll_pipeline_runner_after_worker_state_changes",
        }
    output = os.path.join(run_dir, gate["output"][0])
    _materialize(phase, output, verified)
    if phase == "editor_pass2":
        review = _load(output)
        if not review.get("pass", False):
            from prepare_master_retry import prepare
            targets = _review_target_shot_ids(review)
            packets = prepare(run_dir, output)
            state = load_state(run_dir)
            state["phases"]["master_production"].update({"status": "pending", "agent_id": None})
            editor_state = state["phases"]["editor_pass2"]
            editor_state.update({"status": "pending", "agent_id": None})
            if targets:
                editor_state["target_shot_ids"] = targets
                editor_state["targeted_retry_rounds"] = int(editor_state.get("targeted_retry_rounds", 0) or 0) + 1
            else:
                editor_state.pop("target_shot_ids", None)
            state["current_phase"] = "master_production"
            save_state(run_dir, state)
            return {"action": "field_patch_retry", "phase": "editor_pass2", "next": "master_production",
                    "dispatch_packets": packets, "target_shot_ids": targets, "reason": "scene_window_blocking",
                    "requires_user_input": False,
                    "automatic_resume": True}
        state = load_state(run_dir)
        state["phases"]["editor_pass2"].pop("target_shot_ids", None)
        state["phases"]["editor_pass2"].pop("targeted_retry_rounds", None)
        save_state(run_dir, state)
    mark_done(run_dir, phase)
    advance(run_dir)
    return {"action": "advance", "from": phase, "next": load_state(run_dir)["current_phase"],
            "requires_user_input": False}


def _verified_packets(run_dir, phase):
    records = []
    for packet_path in _current_source_packets(_phase_packet_paths(run_dir, phase)):
        packet = _load(packet_path)
        output = packet.get("_batch_output_path", "")
        valid, _reason, manifest = verify(output) if output and os.path.exists(output) else (False, "missing", None)
        if valid:
            records.append((
                1 if packet.get("retry_context_path") else 0,
                float(packet.get("created_at") or 0),
                float((manifest or {}).get("recorded_at") or 0),
                output,
            ))
    return [output for _is_retry, _created_at, _recorded_at, output in sorted(records)]


def _phase_packet_paths(run_dir, phase):
    """Return active packet files that still belong to the current source.

    Recovery can create verified retry packets outside the current pending
    queue.  A public merge should therefore consider every active packet for
    the phase, then let provenance, source hashes and retry ordering decide
    which records are authoritative.
    """
    active = active_packet_paths(run_dir, phase)
    if active:
        return sorted(active)
    dispatch_dir = os.path.join(run_dir, ".cache", "dispatch")
    if not os.path.isdir(dispatch_dir):
        return []
    paths = []
    for name in os.listdir(dispatch_dir):
        if not name.endswith("_packet.json"):
            continue
        path = os.path.join(dispatch_dir, name)
        if _load(path).get("phase") == phase:
            paths.append(path)
    return sorted(paths)


def _current_source_packets(packet_paths):
    current = []
    for packet_path in packet_paths:
        packet = _load(packet_path)
        expected = packet.get("source_sha256")
        source_path = packet.get("source_path", "")
        if expected and (not os.path.isfile(source_path) or _sha256(source_path) != expected):
            continue
        current.append(packet_path)
    return current


def _worker_status(run_dir, phase, packet_paths):
    """Expose why a worker wait is automatic rather than a user decision."""
    state = load_state(run_dir)
    dispatches = state.get("phases", {}).get(phase, {}).get("dispatches", {})
    result = []
    for packet_path in packet_paths:
        packet = _load(packet_path)
        dispatch_id = packet.get("dispatch_id", "")
        entry = dispatches.get(dispatch_id, {}) if isinstance(dispatches, dict) else {}
        result.append({
            "dispatch_id": dispatch_id,
            "status": entry.get("status", "awaiting_registration") if isinstance(entry, dict) else "awaiting_registration",
            "agent_id": entry.get("agent_id") if isinstance(entry, dict) else None,
        })
    return result


def _phase_target_ids(state, phase):
    phase_state = state.get("phases", {}).get(phase, {}) if isinstance(state, dict) else {}
    values = phase_state.get("target_shot_ids", []) if isinstance(phase_state, dict) else []
    if not isinstance(values, list):
        return None
    result = [str(value).strip() for value in values if str(value).strip()]
    return result or None


def _review_target_shot_ids(review):
    targets = []
    for target in review.get("repair_targets", []) if isinstance(review, dict) else []:
        shot_id = ""
        if isinstance(target, dict):
            shot_id = str(target.get("shot_id", "") or target.get("subshot_id", "") or "")
        else:
            shot_id = str(target or "")
        if shot_id and shot_id not in targets:
            targets.append(shot_id)
    if targets:
        return sorted(targets)
    for window in review.get("windows", []) if isinstance(review, dict) else []:
        if not isinstance(window, dict) or window.get("pass"):
            continue
        current = window.get("current", {}) if isinstance(window.get("current"), dict) else {}
        shot_id = str(current.get("shot_id", "") or "")
        if shot_id and shot_id not in targets:
            targets.append(shot_id)
    return sorted(targets)


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


def _completed_phase_valid(run_dir, phase, gate):
    if not all(os.path.isfile(os.path.join(run_dir, path)) for path in gate.get("output", [])):
        return False
    if phase in LOCAL_PHASES:
        return _local_phase_valid(run_dir, phase)
    return True


def _local_phase_valid(run_dir, phase):
    if phase in ("user_confirm", "orchestrator"):
        return True
    package_path = os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json")
    package_sha256 = _sha256(package_path) if os.path.isfile(package_path) else ""
    if phase == "editor_pass1":
        result = _load(os.path.join(run_dir, ".cache", "review", "pre_editor_gate.json"))
        return result.get("pass") is True and result.get("package_sha256") == package_sha256
    if phase == "validate":
        result = _load(os.path.join(run_dir, ".cache", "validate", "result.json"))
        return result.get("pass") is True and result.get("package_sha256") == package_sha256
    if phase == "export":
        result = _load(os.path.join(run_dir, ".cache", "export", "result.json"))
        destination = result.get("markdown_path", "")
        return (
            result.get("pass") is True
            and result.get("package_sha256") == package_sha256
            and destination and os.path.isfile(destination)
            and result.get("markdown_sha256") == _sha256(destination)
        )
    return False


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
