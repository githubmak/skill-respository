#!/usr/bin/env python3
"""Redispatch only unverified Master Production main shots.

Verified Composer batches remain authoritative.  Incomplete or interrupted
packets are archived, then missing main-shot ids are regenerated as targeted
retry packets so the runner does not wait forever on stale dispatches.
"""

import argparse
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from dispatch_cache import active_packet_paths, prepare_dispatch_packets
from pipeline_state import load_state, save_state
from record_batch_provenance import verify as verify_provenance


PHASE = "master_production"


def redispatch(run_dir, reason, batch_size=None):
    run_dir = os.path.abspath(run_dir)
    dispatch_dir = os.path.join(run_dir, ".cache", "dispatch")
    archive_dir = os.path.join(dispatch_dir, "rejected", "%s-%d" % (PHASE, int(time.time())))
    os.makedirs(archive_dir, exist_ok=True)
    state = load_state(run_dir)
    target_shots = set(
        str(value).strip()
        for value in state.get("phases", {}).get(PHASE, {}).get("target_shot_ids", [])
        if str(value).strip()
    )
    verified_shots = set()
    all_shots = set()
    retired = []

    for path in active_packet_paths(run_dir, PHASE):
        packet = _load(path)
        shot_ids = set(_shot_ids(packet))
        all_shots.update(shot_ids)
        output = str(packet.get("_batch_output_path", "") or "")
        valid, _reason, _manifest = verify_provenance(output) if output and os.path.exists(output) else (False, "missing output", None)
        if valid:
            if target_shots:
                # A verified original packet does not satisfy a targeted retry.
                # Only retry packets may clear shots explicitly requested by
                # Editor Pass 2; otherwise stale original output can mask a
                # required field patch.
                if packet.get("is_retry") or packet.get("retry_context_path"):
                    verified_shots.update(shot_ids & target_shots)
            else:
                verified_shots.update(shot_ids)
            continue
        dispatch_id = str(packet.get("dispatch_id", "") or "")
        shutil.move(path, os.path.join(archive_dir, os.path.basename(path)))
        entry = state["phases"][PHASE].get("dispatches", {}).get(dispatch_id)
        if isinstance(entry, dict):
            entry["status"] = "rejected"
            entry["rejection_reason"] = reason
        retired.append(dispatch_id)

    wanted = target_shots or all_shots
    missing = sorted(wanted - verified_shots)
    try:
        regenerated = (
            prepare_dispatch_packets(run_dir, PHASE, batch_size=batch_size, subshot_ids=missing)
            if missing else []
        )
    except ValueError as error:
        if "packet context budget" not in str(error) and "packet exceeds" not in str(error):
            raise
        regenerated = prepare_dispatch_packets(run_dir, PHASE, batch_size=1, subshot_ids=missing)
    _preserve_verified_manifest_entries(run_dir, missing)
    phase_state = state["phases"][PHASE]
    phase_state["status"] = "pending"
    phase_state["agent_id"] = None
    phase_state["retries"] = phase_state.get("retries", 0) + 1
    phase_state.setdefault("recovery_rounds", []).append({
        "at": time.time(),
        "reason": reason,
        "verified_shot_ids": sorted(verified_shots),
        "retired_dispatch_ids": retired,
        "missing_shot_ids": missing,
        "new_packets": regenerated,
    })
    save_state(run_dir, state)
    return {
        "verified_shot_ids": sorted(verified_shots),
        "retired_dispatch_ids": retired,
        "missing_shot_ids": missing,
        "new_packets": regenerated,
    }


def _shot_ids(packet):
    ids = []
    for item in packet.get("items", []) if isinstance(packet.get("items"), list) else []:
        if not isinstance(item, dict):
            continue
        shot_id = str(item.get("shot_id", "") or item.get("subshot_id", "") or "").strip()
        if shot_id and shot_id not in ids:
            ids.append(shot_id)
    return ids


def _load(path):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


def _preserve_verified_manifest_entries(run_dir, retry_shots):
    manifest_path = os.path.join(run_dir, ".cache", "dispatch", "active_%s_manifest.json" % PHASE)
    try:
        manifest = _load(manifest_path)
    except (OSError, json.JSONDecodeError):
        return
    entries = manifest.get("packets", []) if isinstance(manifest.get("packets"), list) else []
    known = {os.path.abspath(str(entry.get("packet_path", "") or "")) for entry in entries if isinstance(entry, dict)}
    retry_shots = set(str(shot_id) for shot_id in retry_shots or [])
    candidates = []
    for path in _all_phase_packets(os.path.join(run_dir, ".cache", "dispatch")):
        path = os.path.abspath(path)
        if path in known:
            continue
        packet = _load(path)
        output = str(packet.get("_batch_output_path", "") or "")
        valid, _reason, provenance = verify_provenance(output) if output and os.path.exists(output) else (False, "missing output", None)
        if not valid:
            continue
        shot_ids = _shot_ids(packet)
        if retry_shots and shot_ids and set(shot_ids).issubset(retry_shots):
            # A new retry packet will replace this target-only packet.
            continue
        candidates.append((float(packet.get("created_at", 0) or 0), path, packet, shot_ids))
    if not candidates:
        return
    candidates.sort()
    prepend = []
    for _created, path, packet, shot_ids in candidates:
        prepend.append({
            "packet_path": path,
            "dispatch_id": packet.get("dispatch_id", ""),
            "dispatch_group_id": packet.get("dispatch_group_id", ""),
            "created_at": packet.get("created_at"),
            "is_retry": bool(packet.get("is_retry") or packet.get("retry_context_path")),
            "shot_ids": shot_ids,
            "source_sha256": packet.get("source_sha256", ""),
            "attempt": manifest.get("attempt", 0),
            "preserved_verified": True,
            "effective": True,
        })
    manifest["packets"] = prepend + entries
    manifest["active_packet_count"] = len(manifest["packets"])
    manifest["active_shot_ids"] = sorted({
        shot_id
        for entry in manifest["packets"] if isinstance(entry, dict)
        for shot_id in entry.get("shot_ids", [])
        if str(shot_id).strip()
    })
    manifest["updated_at"] = time.time()
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)


def _all_phase_packets(dispatch_dir):
    if not os.path.isdir(dispatch_dir):
        return []
    paths = []
    for name in os.listdir(dispatch_dir):
        if not name.endswith("_packet.json"):
            continue
        path = os.path.join(dispatch_dir, name)
        try:
            packet = _load(path)
        except (OSError, json.JSONDecodeError):
            continue
        if packet.get("phase") == PHASE:
            paths.append(path)
    return sorted(paths)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Optional maximum retry batch size. Omit to use dynamic Master Production batching; use 1 for forced single-shot isolation.",
    )
    args = parser.parse_args()
    print(json.dumps(redispatch(args.run_dir, args.reason, batch_size=args.batch_size), ensure_ascii=False, indent=2))
