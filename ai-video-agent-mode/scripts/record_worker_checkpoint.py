#!/usr/bin/env python3
"""Validate one worker item and record content progress in one local call."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from dispatch_progress import inspect_output
from dispatch_receipts import heartbeat as receipt_heartbeat
from pipeline_state import record_heartbeat
from validate_composer_output import validate_composer_output


def record(packet_path, agent_id, item_id=None):
    with open(packet_path, encoding="utf-8-sig") as handle:
        packet = json.load(handle)
    validation_code = 0
    report_path = None
    if packet.get("phase") == "master_production":
        if not item_id:
            raise ValueError("master_production checkpoint requires --item-id")
        report_path = packet["_batch_output_path"] + "." + item_id + ".incremental.validation.json"
        validation_code = validate_composer_output(
            packet["_batch_output_path"],
            packet.get("run_dir"),
            report_path,
            allow_incomplete=True,
            selected_shot_ids=[item_id],
        )
    progress = inspect_output(packet)
    timestamp = record_heartbeat(
        packet["run_dir"], packet["phase"], agent_id, packet["dispatch_id"], progress=progress
    )
    receipt, receipt_path = receipt_heartbeat(
        packet_path, packet, agent_id, progress=progress, observed_at=timestamp
    )
    print(json.dumps({
        "validation_pass": validation_code == 0,
        "validation_report_path": report_path,
        "heartbeat_at": timestamp,
        "receipt_path": receipt_path,
        "content_progress": progress,
        "checkpoint_count": receipt.get("progress_count", 0),
    }, ensure_ascii=False))
    return validation_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("packet_path")
    parser.add_argument("agent_id")
    parser.add_argument("--item-id")
    args = parser.parse_args()
    raise SystemExit(record(args.packet_path, args.agent_id, args.item_id))
