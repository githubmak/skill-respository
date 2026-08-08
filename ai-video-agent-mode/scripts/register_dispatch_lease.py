#!/usr/bin/env python3
"""Bind one persistent worker to an ordered list of immutable packets."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from contract_registry import PROMPT_CONTRACT_VERSION
from dispatch_receipts import issue
from pipeline_state import reserve_dispatch_lease


def register(agent_id, lease_id, packet_paths):
    records = []
    run_dir = phase = None
    for path in packet_paths:
        with open(path, encoding="utf-8-sig") as handle:
            packet = json.load(handle)
        if packet.get("contract_version") != PROMPT_CONTRACT_VERSION:
            raise ValueError("unsupported packet contract: " + path)
        if run_dir is None:
            run_dir, phase = packet["run_dir"], packet["phase"]
        if packet.get("run_dir") != run_dir or packet.get("phase") != phase:
            raise ValueError("one lease may contain only one run and phase")
        issue(path, packet, agent_id)
        records.append({"dispatch_id": packet["dispatch_id"], "packet_path": os.path.abspath(path)})
    reserve_dispatch_lease(run_dir, phase, agent_id, lease_id, records)
    return {"lease_id": lease_id, "agent_id": agent_id, "phase": phase, "packet_count": len(records)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("agent_id")
    parser.add_argument("lease_id")
    parser.add_argument("packet_paths", nargs="+")
    args = parser.parse_args()
    print(json.dumps(register(args.agent_id, args.lease_id, args.packet_paths), ensure_ascii=False))
