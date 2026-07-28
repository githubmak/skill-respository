#!/usr/bin/env python3
"""Supersede one incomplete Agent dispatch round before a clean redispatch."""

import argparse
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from pipeline_state import load_state, save_state


def reset(run_dir, phase, reason):
    run_dir = os.path.abspath(run_dir)
    dispatch_dir = os.path.join(run_dir, ".cache", "dispatch")
    archive_dir = os.path.join(dispatch_dir, "superseded", "%s-%d" % (phase, int(time.time())))
    os.makedirs(archive_dir, exist_ok=True)
    state = load_state(run_dir)
    moved = []
    for name in sorted(os.listdir(dispatch_dir)):
        if not name.endswith("_packet.json"):
            continue
        path = os.path.join(dispatch_dir, name)
        try:
            with open(path, encoding="utf-8-sig") as handle:
                packet = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if packet.get("phase") != phase:
            continue
        shutil.move(path, os.path.join(archive_dir, name))
        moved.append({"dispatch_id": packet.get("dispatch_id", ""), "packet": name})
    phase_state = state["phases"][phase]
    phase_state["status"] = "pending"
    phase_state["agent_id"] = None
    phase_state["dispatches"] = {}
    phase_state["retries"] = phase_state.get("retries", 0) + 1
    phase_state["superseded_dispatches"] = phase_state.get("superseded_dispatches", []) + [{
        "at": time.time(), "reason": reason, "archive_dir": archive_dir, "packets": moved,
    }]
    save_state(run_dir, state)
    return {"archive_dir": archive_dir, "packets": moved}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    print(json.dumps(reset(args.run_dir, args.phase, args.reason), ensure_ascii=False, indent=2))
