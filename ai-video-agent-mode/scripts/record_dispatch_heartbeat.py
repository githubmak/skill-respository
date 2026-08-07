#!/usr/bin/env python3
"""CLI used by a running worker to prove liveness for its own packet."""
import json, sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from pipeline_state import record_heartbeat
from dispatch_receipts import heartbeat
from dispatch_progress import inspect_output

if len(sys.argv) != 3:
    raise SystemExit("usage: record_dispatch_heartbeat.py <packet.json> <agent_id>")
with open(sys.argv[1], encoding="utf-8-sig") as handle:
    packet = json.load(handle)
agent_id = sys.argv[2]
progress = inspect_output(packet)
timestamp = record_heartbeat(
    packet["run_dir"], packet["phase"], agent_id, packet["dispatch_id"], progress=progress
)
receipt, receipt_path = heartbeat(
    sys.argv[1], packet, agent_id, progress=progress, observed_at=timestamp
)
print(json.dumps({
    "heartbeat_at": timestamp,
    "receipt_path": receipt_path,
    "heartbeat_count": receipt["heartbeat_count"],
    "content_progress": progress,
    "checkpoint_count": receipt.get("progress_count", 0),
    "last_progress_at": receipt.get("last_progress_at"),
}, ensure_ascii=False))
