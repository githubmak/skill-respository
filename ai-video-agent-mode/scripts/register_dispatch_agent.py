#!/usr/bin/env python3
"""Register the real Agent assigned to one immutable dispatch packet."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pipeline_state import set_agent_id
from dispatch_receipts import issue


def register(packet_path, agent_id):
    with open(packet_path, "r", encoding="utf-8-sig") as handle:
        packet = json.load(handle)
    if packet.get("contract_version") != "jimeng-t2v-v1":
        raise SystemExit("Invalid or pre-v4 dispatch packet")
    run_dir = str(packet.get("run_dir", "") or "")
    phase = str(packet.get("phase", "") or "")
    dispatch_id = str(packet.get("dispatch_id", "") or "")
    if not run_dir or not phase or not dispatch_id or not str(agent_id).strip():
        raise SystemExit("packet run_dir/phase/dispatch_id and agent_id are required")
    normalized_agent_id = str(agent_id).strip()
    receipt, receipt_path = issue(packet_path, packet, normalized_agent_id)
    set_agent_id(run_dir, phase, normalized_agent_id, dispatch_id=dispatch_id)
    print("[DISPATCH AGENT] %s %s %s" % (phase, dispatch_id, normalized_agent_id))
    print("[DISPATCH RECEIPT] %s" % receipt_path)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: register_dispatch_agent.py <dispatch_packet.json> <agent_id>")
        sys.exit(2)
    register(sys.argv[1], sys.argv[2])
