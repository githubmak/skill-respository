#!/usr/bin/env python3
"""Start one packet in a persistent worker lease before its first heartbeat."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pipeline_state import start_leased_dispatch


if len(sys.argv) != 3:
    raise SystemExit("usage: start_leased_dispatch.py <packet.json> <agent_id>")
with open(sys.argv[1], encoding="utf-8-sig") as handle:
    packet = json.load(handle)
started = start_leased_dispatch(
    packet["run_dir"], packet["phase"], sys.argv[2], packet["dispatch_id"]
)
print(json.dumps({"dispatch_id": packet["dispatch_id"], "started_at": started}))
