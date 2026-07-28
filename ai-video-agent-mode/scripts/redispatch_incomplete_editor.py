#!/usr/bin/env python3
"""Redispatch only unverified Editor Pass 2 windows.

Verified Editor packets remain authoritative.  This closes the recovery gap
where recreating a whole review round either duplicated completed windows or
discarded their provenance when one worker failed.
"""

import argparse
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from dispatch_cache import prepare_dispatch_packets
from pipeline_state import load_state, save_state
from record_batch_provenance import verify as verify_provenance


PHASE = "editor_pass2"


def redispatch(run_dir, reason):
    run_dir = os.path.abspath(run_dir)
    dispatch_dir = os.path.join(run_dir, ".cache", "dispatch")
    archive_dir = os.path.join(dispatch_dir, "rejected", "%s-%d" % (PHASE, int(time.time())))
    os.makedirs(archive_dir, exist_ok=True)
    state = load_state(run_dir)
    verified_windows = set()
    retired = []

    for path in _active_packets(dispatch_dir):
        packet = _load(path)
        output = str(packet.get("_batch_output_path", "") or "")
        valid, _reason, _manifest = verify_provenance(output) if output else (False, "missing output", None)
        if valid:
            verified_windows.update(_window_ids(packet))
            continue
        dispatch_id = str(packet.get("dispatch_id", "") or "")
        shutil.move(path, os.path.join(archive_dir, os.path.basename(path)))
        entry = state["phases"][PHASE].get("dispatches", {}).get(dispatch_id)
        if isinstance(entry, dict):
            entry["status"] = "rejected"
            entry["rejection_reason"] = reason
        retired.append(dispatch_id)

    regenerated = prepare_dispatch_packets(run_dir, PHASE)
    retained = []
    for path in regenerated:
        packet = _load(path)
        windows = set(_window_ids(packet))
        if windows and windows.issubset(verified_windows):
            shutil.move(path, os.path.join(archive_dir, os.path.basename(path)))
            continue
        retained.append(path)

    phase_state = state["phases"][PHASE]
    phase_state["status"] = "pending"
    phase_state["agent_id"] = None
    phase_state["retries"] = phase_state.get("retries", 0) + 1
    phase_state.setdefault("recovery_rounds", []).append({
        "at": time.time(), "reason": reason, "verified_window_ids": sorted(verified_windows),
        "retired_dispatch_ids": retired, "new_packets": retained,
    })
    save_state(run_dir, state)
    return {"verified_window_ids": sorted(verified_windows), "retired_dispatch_ids": retired, "new_packets": retained}


def _active_packets(dispatch_dir):
    paths = []
    for name in os.listdir(dispatch_dir):
        if not name.endswith("_packet.json"):
            continue
        path = os.path.join(dispatch_dir, name)
        if _load(path).get("phase") == PHASE:
            paths.append(path)
    return sorted(paths)


def _window_ids(packet):
    return [str(item.get("window_id", "")) for item in packet.get("items", []) if isinstance(item, dict) and item.get("window_id")]


def _load(path):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    print(json.dumps(redispatch(args.run_dir, args.reason), ensure_ascii=False, indent=2))
