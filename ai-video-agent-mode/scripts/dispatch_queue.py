#!/usr/bin/env python3
"""Dependency-safe worker-slot scheduler for on-disk dispatch packets."""
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(__file__))
from pipeline_state import MAX_RETRIES, PHASE_TIMEOUT_SECONDS, TIMEOUT_SECONDS, load_state, save_state
from dispatch_cache import active_packet_paths
from contract_registry import PIPELINE_WORKER_SLOT_CAP, PROMPT_CONTRACT_VERSION
from pipeline_runtime import atomic_json, json_lock


def fill_slots(run_dir, phase, packet_paths, max_workers=None):
    """Return only packets that fit free worker slots, in stable queue order.

    Packets are already dependency-ready when this is called.  Registration is
    the transition to running, so a later tick naturally fills slots released
    by completed batches without re-emitting active work.
    """
    config = _load(os.path.join(run_dir, "project_config.json"))
    configured = int(max_workers or (config.get("execution", {}) or {}).get(
        "worker_slots", PIPELINE_WORKER_SLOT_CAP) or PIPELINE_WORKER_SLOT_CAP)
    capacity = min(max(configured, 1), PIPELINE_WORKER_SLOT_CAP)
    state = load_state(run_dir)
    dispatches = state.get("phases", {}).get(phase, {}).get("dispatches", {})
    active = sum(
        1 for entry in dispatches.values()
        if isinstance(entry, dict)
        and entry.get("status") in ("running", "waiting")
    )
    free = max(capacity - active, 0)
    selected = []
    for path in sorted(packet_paths):
        packet = _load(path)
        dispatch_id = packet.get("dispatch_id")
        status = (dispatches.get(dispatch_id) or {}).get("status")
        if status in ("done", "partial"):
            continue
        if status in ("running", "waiting"):
            continue
        if free <= 0:
            break
        selected.append(path)
        free -= 1
    return selected


def pending_packet_paths(run_dir, phase):
    active = active_packet_paths(run_dir, phase)
    if active:
        return sorted(active)
    directory = os.path.join(run_dir, ".cache", "dispatch")
    if not os.path.isdir(directory):
        return []
    paths = []
    for name in os.listdir(directory):
        if name.startswith("._") or not name.endswith("_packet.json"):
            continue
        path = os.path.join(directory, name)
        if _load(path).get("phase") == phase:
            paths.append(path)
    return sorted(paths)


def retire_timed_out_dispatches(run_dir, phase, packet_paths, verified_dispatch_ids=None, now=None):
    """Retire only expired packets and replace each with a unique dispatch.

    Heartbeats report liveness but never extend the absolute packet timeout.
    A replacement gets a new packet path, output path and receipt identity, so
    an immutable receipt from the retired attempt cannot authorize its output.
    """
    now = float(now if now is not None else time.time())
    verified = set(str(value) for value in verified_dispatch_ids or [])
    packet_by_id = {}
    for path in packet_paths or []:
        packet = _load(path)
        dispatch_id = str(packet.get("dispatch_id", "") or "")
        if dispatch_id:
            packet_by_id[dispatch_id] = (path, packet)
    result = {"retired_dispatch_ids": [], "replacement_packets": [], "exhausted_dispatch_ids": []}
    state_path = os.path.join(run_dir, ".cache", "pipeline_state.json")
    with json_lock(state_path):
        state = load_state(run_dir)
        phase_state = state.get("phases", {}).get(phase, {})
        dispatches = phase_state.get("dispatches", {}) if isinstance(phase_state, dict) else {}
        for dispatch_id, entry in list(dispatches.items()) if isinstance(dispatches, dict) else []:
            if dispatch_id in verified or not isinstance(entry, dict):
                continue
            if entry.get("status") not in ("running", "waiting"):
                continue
            spawn_time = entry.get("spawn_time")
            if not isinstance(spawn_time, (int, float)):
                continue
            timeout = PHASE_TIMEOUT_SECONDS.get(phase, TIMEOUT_SECONDS)
            if now - float(spawn_time) < timeout:
                continue
            packet_record = packet_by_id.get(str(dispatch_id))
            if not packet_record:
                entry.update({"status": "timed_out", "retired_at": now,
                              "retirement_reason": "packet_timeout_missing_active_packet"})
                result["retired_dispatch_ids"].append(str(dispatch_id))
                result["exhausted_dispatch_ids"].append(str(dispatch_id))
                continue
            packet_path, packet = packet_record
            attempt = max(int(packet.get("dispatch_attempt", 1) or 1), 1)
            entry.update({"status": "timed_out", "retired_at": now,
                          "retirement_reason": "absolute_packet_timeout",
                          "elapsed_seconds": round(max(now - float(spawn_time), 0), 3)})
            result["retired_dispatch_ids"].append(str(dispatch_id))
            if attempt >= MAX_RETRIES:
                result["exhausted_dispatch_ids"].append(str(dispatch_id))
                continue
            replacement = _unique_replacement(run_dir, packet_path, packet, attempt + 1, now)
            result["replacement_packets"].append(replacement)
        if result["retired_dispatch_ids"]:
            phase_state["timeout_count"] = int(phase_state.get("timeout_count", 0) or 0) + len(
                result["retired_dispatch_ids"])
            phase_state["retries"] = int(phase_state.get("retries", 0) or 0) + len(
                result["replacement_packets"])
            phase_state["status"] = "failed" if result["exhausted_dispatch_ids"] else "pending"
            phase_state.setdefault("dispatch_recovery_events", []).append(dict(result, at=now))
            save_state(run_dir, state)
    if result["replacement_packets"]:
        _replace_manifest_entries(run_dir, phase, result["replacement_packets"], now, packet_paths)
    return result


def _unique_replacement(run_dir, packet_path, packet, attempt, now):
    dispatch_id = str(uuid.uuid4())
    tag = dispatch_id.split("-")[0]
    replacement = dict(packet)
    replacement.update({
        "dispatch_id": dispatch_id,
        "created_at": now,
        "dispatch_attempt": attempt,
        "retry_of_dispatch_id": packet.get("dispatch_id", ""),
        "retry_reason": "absolute_packet_timeout",
    })
    old_output = str(packet.get("_batch_output_path", "") or "")
    root, ext = os.path.splitext(old_output)
    replacement["_batch_output_path"] = "%s_retry%d_%s%s" % (root, attempt, tag, ext or ".json")
    directory = os.path.dirname(packet_path)
    replacement_path = os.path.join(
        directory, "%s_timeout_retry%d_%s_packet.json" % (phase_safe(packet.get("phase")), attempt, tag)
    )
    atomic_json(replacement_path, replacement)
    return {
        "old_dispatch_id": str(packet.get("dispatch_id", "") or ""),
        "dispatch_id": dispatch_id,
        "packet_path": replacement_path,
        "batch_output_path": replacement["_batch_output_path"],
        "attempt": attempt,
    }


def _replace_manifest_entries(run_dir, phase, replacements, now, active_paths=None):
    path = os.path.join(run_dir, ".cache", "dispatch", "active_%s_manifest.json" % phase_safe(phase))
    manifest = _load(path)
    entries = manifest.get("packets", []) if isinstance(manifest.get("packets"), list) else []
    if manifest.get("phase") != phase or not entries:
        entries = []
        for packet_path in active_paths or []:
            packet = _load(packet_path)
            if packet.get("phase") != phase or not packet.get("dispatch_id"):
                continue
            entries.append({
                "packet_path": os.path.abspath(packet_path),
                "dispatch_id": packet["dispatch_id"],
                "dispatch_group_id": packet.get("dispatch_group_id", ""),
                "created_at": packet.get("created_at"),
                "is_retry": bool(packet.get("is_retry") or packet.get("retry_context_path")),
                "shot_ids": _packet_shot_ids(packet),
                "source_sha256": packet.get("source_sha256", ""),
                "attempt": int(packet.get("dispatch_attempt", 1) or 1),
                "effective": True,
            })
        manifest = {"contract_version": PROMPT_CONTRACT_VERSION, "phase": phase}
    by_old = {item["old_dispatch_id"]: item for item in replacements}
    superseded = manifest.get("superseded_packets", []) if isinstance(manifest.get("superseded_packets"), list) else []
    updated = []
    for entry in entries:
        if not isinstance(entry, dict) or str(entry.get("dispatch_id", "")) not in by_old:
            updated.append(entry)
            continue
        replacement = by_old[str(entry.get("dispatch_id", ""))]
        old = dict(entry, effective=False, superseded_at=now,
                   superseded_reason="absolute_packet_timeout")
        superseded.append(old)
        packet = _load(replacement["packet_path"])
        updated.append(dict(entry,
                            packet_path=os.path.abspath(replacement["packet_path"]),
                            dispatch_id=replacement["dispatch_id"],
                            created_at=packet.get("created_at"),
                            attempt=replacement["attempt"],
                            effective=True,
                            retry_of_dispatch_id=replacement["old_dispatch_id"]))
    manifest.update({
        "updated_at": now,
        "active_packet_count": len(updated),
        "active_retry_packet_count": sum(1 for entry in updated if isinstance(entry, dict) and entry.get("is_retry")),
        "active_shot_ids": sorted({
            shot_id for entry in updated if isinstance(entry, dict)
            for shot_id in entry.get("shot_ids", []) if str(shot_id).strip()
        }),
        "attempt": max((int(entry.get("attempt", 1) or 1) for entry in updated if isinstance(entry, dict)), default=1),
        "superseded_packet_count": len(superseded),
        "superseded_packets": superseded[-200:],
        "packets": updated,
    })
    atomic_json(path, manifest)


def _packet_shot_ids(packet):
    result = []
    for item in packet.get("items", []) if isinstance(packet.get("items"), list) else []:
        if not isinstance(item, dict):
            continue
        identity = str(item.get("shot_id", "") or item.get("subshot_id", "") or item.get("scene", "")).strip()
        if identity and identity not in result:
            result.append(identity)
    return result


def phase_safe(value):
    return "".join(char if char.isalnum() or char in "_.-" else "_" for char in str(value or "unknown"))


def _load(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit("usage: dispatch_queue.py <run_dir> <phase> <packet> [...]")
    print("\n".join(fill_slots(sys.argv[1], sys.argv[2], sys.argv[3:])))
