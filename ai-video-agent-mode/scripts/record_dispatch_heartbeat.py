#!/usr/bin/env python3
"""CLI used by a running worker to prove liveness for its own packet."""
import json, sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from pipeline_state import record_heartbeat

if len(sys.argv) != 3:
    raise SystemExit("usage: record_dispatch_heartbeat.py <packet.json> <agent_id>")
with open(sys.argv[1], encoding="utf-8-sig") as handle:
    packet = json.load(handle)
print(record_heartbeat(packet["run_dir"], packet["phase"], sys.argv[2], packet["dispatch_id"]))
