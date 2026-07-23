#!/usr/bin/env python3
"""Record and verify the provenance of one completed Agent batch."""

import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from pipeline_state import load_state, save_state
from validate_composer_output import validate_composer_output
from pipeline_runtime import cache_artifact, record_issues


def record(packet_path, allow_partial=False):
    packet = _load(packet_path)
    if packet.get("contract_version") != "jimeng-t2v-v1" or not packet.get("dispatch_id"):
        raise SystemExit("Invalid or pre-v4 dispatch packet")
    run_dir = packet.get("run_dir", "")
    phase = packet.get("phase", "")
    batch_path = packet.get("_batch_output_path", "")
    if not run_dir or not phase or not batch_path or not os.path.exists(batch_path):
        raise SystemExit("Missing run_dir, phase, or completed batch output")

    state = load_state(run_dir)
    phase_state = state.get("phases", {}).get(phase, {})
    dispatch_state = phase_state.get("dispatches", {}).get(packet.get("dispatch_id"), {})
    provenance_state = dispatch_state if dispatch_state else phase_state
    agent_id = str(provenance_state.get("agent_id", "") or "").strip()
    spawn_time = provenance_state.get("spawn_time")
    status = provenance_state.get("status")
    if not agent_id or not isinstance(spawn_time, (int, float)):
        raise SystemExit("Agent provenance missing: register agent_id and spawn_time before accepting output")
    if status not in ("running", "waiting", "done"):
        raise SystemExit("Agent phase status is not eligible for provenance: %s" % status)
    output_mtime = os.path.getmtime(batch_path)
    if output_mtime <= spawn_time:
        raise SystemExit("OUTPUT_BYPASS: batch output predates Agent spawn")

    provenance_dir = os.path.join(run_dir, ".cache", "provenance")
    os.makedirs(provenance_dir, exist_ok=True)
    rejection_path = os.path.join(provenance_dir, packet["dispatch_id"] + ".rejected.json")
    rejection = _load(rejection_path) if os.path.exists(rejection_path) else None
    if rejection:
        if not allow_partial:
            raise SystemExit("RETRY_REQUIRED: rejected dispatch cannot be repaired in place")
        if rejection.get("rejected_sha256") != _sha256(batch_path):
            raise SystemExit("RETRY_REQUIRED: rejected batch changed after validation; use the unique retry packet")

    validation_report_path = os.path.join(
        provenance_dir, packet["dispatch_id"] + ".validation.json"
    )
    validator_name, validation_pass = _validate(
        phase, batch_path, run_dir, validation_report_path
    )
    validated_subshot_ids = []
    failed_subshot_ids = []
    validation_mode = "full"
    if phase == "master_production":
        batch_data = _load(batch_path)
        all_subshot_ids = [
            item.get("subshot_id") for item in batch_data.get("shots", [])
            if isinstance(item, dict) and item.get("subshot_id")
        ]
        if os.path.exists(validation_report_path):
            report = _load(validation_report_path)
            failed_subshot_ids = [
                sid for sid in report.get("failed_subshot_ids", []) if sid in all_subshot_ids
            ]
        if not validation_pass and not failed_subshot_ids:
            failed_subshot_ids = list(all_subshot_ids)
        validated_subshot_ids = [sid for sid in all_subshot_ids if sid not in failed_subshot_ids]
        if not validation_pass and allow_partial and validated_subshot_ids:
            validation_mode = "partial"
        elif not validation_pass:
            raise SystemExit("Batch validation failed; provenance not recorded")
    elif not validation_pass:
        raise SystemExit("Batch validation failed; provenance not recorded")

    manifest = {
        "contract_version": "jimeng-t2v-v1",
        "dispatch_id": packet["dispatch_id"],
        "phase": phase,
        "agent_id": agent_id,
        "agent_status_at_record": status,
        "spawn_time": spawn_time,
        "packet_created_at": packet.get("created_at"),
        "packet_path": os.path.abspath(packet_path),
        "batch_path": os.path.abspath(batch_path),
        "batch_mtime": output_mtime,
        "sha256": _sha256(batch_path),
        "validator": validator_name,
        "validated": True,
        "validation_mode": validation_mode,
        "validated_subshot_ids": validated_subshot_ids,
        "failed_subshot_ids": failed_subshot_ids,
        "validation_report_path": validation_report_path if os.path.exists(validation_report_path) else None,
        "rejection_seal_path": rejection_path if rejection else None,
        "recorded_at": time.time(),
    }
    sidecar = batch_path + ".provenance.json"
    with open(sidecar, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    index_path = os.path.join(provenance_dir, packet["dispatch_id"] + ".json")
    with open(index_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    _mark_dispatch_recorded(run_dir, phase, packet["dispatch_id"], validation_mode)
    cache_artifact(run_dir, phase, manifest, {"packet": packet.get("dispatch_id")})
    if failed_subshot_ids:
        record_issues(run_dir, phase, [{"subshot_id": sid, "message": "composer validation failed"} for sid in failed_subshot_ids], manifest["sha256"])
    label = "PARTIAL" if validation_mode == "partial" else "PASS"
    print("[PROVENANCE] %s %s %s %s" % (label, phase, agent_id, manifest["sha256"]))
    print(sidecar)
    return sidecar


def _mark_dispatch_recorded(run_dir, phase, dispatch_id, validation_mode):
    state = load_state(run_dir)
    phase_state = state.get("phases", {}).get(phase, {})
    dispatch = phase_state.get("dispatches", {}).get(dispatch_id)
    if isinstance(dispatch, dict):
        dispatch["status"] = "done" if validation_mode == "full" else "partial"
        dispatch["recorded_at"] = time.time()
        if isinstance(dispatch.get("spawn_time"), (int, float)):
            dispatch["elapsed_seconds"] = round(max(dispatch["recorded_at"] - dispatch["spawn_time"], 0), 3)
    dispatches = phase_state.get("dispatches", {})
    statuses = [entry.get("status") for entry in dispatches.values() if isinstance(entry, dict)]
    if statuses and all(status == "done" for status in statuses):
        phase_state["status"] = "done"
        phase_state["completed_at"] = time.time()
        if isinstance(phase_state.get("spawn_time"), (int, float)):
            phase_state["elapsed_seconds"] = round(max(phase_state["completed_at"] - phase_state["spawn_time"], 0), 3)
    elif validation_mode == "partial":
        phase_state["status"] = "waiting"
    save_state(run_dir, state)


def verify(batch_path):
    sidecar = batch_path + ".provenance.json"
    if not os.path.exists(sidecar):
        return False, "provenance sidecar missing", None
    manifest = _load(sidecar)
    if manifest.get("contract_version") != "jimeng-t2v-v1" or not manifest.get("validated"):
        return False, "invalid provenance contract or validation state", manifest
    if os.path.abspath(batch_path) != manifest.get("batch_path"):
        return False, "batch path does not match provenance", manifest
    current_hash = _sha256(batch_path)
    if current_hash != manifest.get("sha256"):
        return False, "batch hash changed after Agent validation", manifest
    if not manifest.get("agent_id") or not manifest.get("dispatch_id"):
        return False, "agent_id or dispatch_id missing", manifest
    packet_path = manifest.get("packet_path")
    if packet_path and os.path.exists(packet_path):
        packet = _load(packet_path)
        run_dir = packet.get("run_dir", "")
        rejection_path = os.path.join(
            run_dir, ".cache", "provenance", manifest.get("dispatch_id", "") + ".rejected.json"
        )
        if os.path.exists(rejection_path):
            rejection = _load(rejection_path)
            if manifest.get("validation_mode") != "partial":
                return False, "rejected dispatch was repaired in place instead of uniquely redispatched", manifest
            if rejection.get("rejected_sha256") != current_hash:
                return False, "rejected batch changed after validation", manifest
    return True, "verified", manifest


def _validate(phase, batch_path, run_dir, validation_report_path=None):
    if phase == "scene_lock":
        from validate_scene_locks import validate as validate_scene_locks
        return "validate_scene_locks", not validate_scene_locks(batch_path)
    if phase == "master_production":
        return "validate_composer_output", validate_composer_output(
            batch_path, run_dir, validation_report_path
        ) == 0
    if phase == "editor_pass2":
        data = _load(batch_path)
        valid = (
            isinstance(data, dict)
            and isinstance(data.get("windows"), list)
            and bool(data["windows"])
            and all(isinstance(item, dict) and item.get("window_id") and isinstance(item.get("pass"), bool)
                    and isinstance(item.get("blocking", []), list) and isinstance(item.get("repair_targets", []), list)
                    for item in data["windows"])
        )
        return "editor_scene_window_contract", valid
    return "json_parse", isinstance(_load(batch_path), dict)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


if __name__ == "__main__":
    args = [arg for arg in sys.argv[1:] if arg != "--allow-partial"]
    if len(args) != 1:
        print("usage: record_batch_provenance.py [--allow-partial] <dispatch_packet.json>")
        sys.exit(2)
    record(args[0], allow_partial="--allow-partial" in sys.argv[1:])
