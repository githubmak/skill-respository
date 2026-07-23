#!/usr/bin/env python3
"""Dependency-safe worker-slot scheduler for on-disk dispatch packets."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pipeline_state import load_state


def fill_slots(run_dir, phase, packet_paths, max_workers=None):
    """Return only packets that fit free worker slots, in stable queue order.

    Packets are already dependency-ready when this is called.  Registration is
    the transition to running, so a later tick naturally fills slots released
    by completed batches without re-emitting active work.
    """
    config = _load(os.path.join(run_dir, "project_config.json"))
    capacity = int(max_workers or (config.get("execution", {}) or {}).get("worker_slots", 4) or 4)
    state = load_state(run_dir)
    dispatches = state.get("phases", {}).get(phase, {}).get("dispatches", {})
    active = sum(1 for entry in dispatches.values() if isinstance(entry, dict) and entry.get("status") in ("running", "waiting"))
    free = max(capacity - active, 0)
    selected = []
    for path in sorted(packet_paths):
        packet = _load(path)
        dispatch_id = packet.get("dispatch_id")
        status = (dispatches.get(dispatch_id) or {}).get("status")
        if status in ("running", "waiting", "done", "partial"):
            continue
        if free <= 0:
            break
        selected.append(path)
        free -= 1
    return selected


def pending_packet_paths(run_dir, phase):
    directory = os.path.join(run_dir, ".cache", "dispatch")
    if not os.path.isdir(directory):
        return []
    paths = []
    for name in os.listdir(directory):
        if not name.endswith("_packet.json"):
            continue
        path = os.path.join(directory, name)
        if _load(path).get("phase") == phase:
            paths.append(path)
    return sorted(paths)


def _load(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit("usage: dispatch_queue.py <run_dir> <phase> <packet> [...]")
    print("\n".join(fill_slots(sys.argv[1], sys.argv[2], sys.argv[3:])))
