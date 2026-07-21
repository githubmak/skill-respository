#!/usr/bin/env python3
"""Validate one Composer batch and dispatch only its failed subshots."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from dispatch_cache import prepare_dispatch_packets
from record_batch_provenance import record as record_provenance
from validate_composer_output import validate_composer_output


def prepare(run_dir, batch_path):
    review_dir = os.path.join(run_dir, ".cache", "review")
    os.makedirs(review_dir, exist_ok=True)
    stem = os.path.basename(batch_path).replace(".prompt_package.json", "")
    report_path = os.path.join(review_dir, "%s_validation.json" % stem)
    result = validate_composer_output(batch_path, run_dir, report_path)
    if result == 0:
        print("[COMPOSER RETRY] PASS - no redispatch required")
        return []

    report = _load(report_path)
    batch = _load(batch_path)
    all_ids = [
        item.get("subshot_id") for item in batch.get("shots", [])
        if isinstance(item, dict) and item.get("subshot_id")
    ]
    failed_ids = [sid for sid in report.get("failed_subshot_ids", []) if sid in all_ids]
    if not failed_ids:
        failed_ids = all_ids
    passed_ids = [sid for sid in all_ids if sid not in failed_ids]

    baseline_packet_path = _find_packet_for_batch(run_dir, batch_path)
    baseline_provenance_path = None
    rejection_seal_path = None
    if baseline_packet_path:
        rejection_seal_path = _write_rejection_seal(
            run_dir, baseline_packet_path, report_path, report
        )
    if baseline_packet_path and passed_ids:
        baseline_provenance_path = record_provenance(
            baseline_packet_path, allow_partial=True
        )

    packet_paths = prepare_dispatch_packets(
        run_dir, "prompt_composer", batch_size=4, subshot_ids=failed_ids
    )
    issues_by_subshot = {
        sid: [issue for issue in report.get("issues", []) if issue.startswith(sid + ":")]
        for sid in failed_ids
    }
    for packet_path in packet_paths:
        packet = _load(packet_path)
        packet["retry_context"] = {
            "baseline_batch_path": os.path.abspath(batch_path),
            "validation_report_path": os.path.abspath(report_path),
            "failed_subshot_ids": failed_ids,
            "passed_subshot_ids": passed_ids,
            "baseline_packet_path": baseline_packet_path,
            "baseline_provenance_path": baseline_provenance_path,
            "rejection_seal_path": rejection_seal_path,
            "issues_by_subshot": issues_by_subshot,
            "instruction": (
                "Rewrite only packet.items. Preserve passed baseline shots; the provenance-aware merge "
                "will replace only matching failed subshot_id values."
            ),
        }
        _write(packet_path, packet)
    print("[COMPOSER RETRY] %d failed / %d total -> %d unique packet(s)" % (
        len(failed_ids), len(all_ids), len(packet_paths)
    ))
    for path in packet_paths:
        print(path)
    return packet_paths


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _write(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def _find_packet_for_batch(run_dir, batch_path):
    dispatch_dir = os.path.join(run_dir, ".cache", "dispatch")
    if not os.path.isdir(dispatch_dir):
        return None
    target = os.path.abspath(batch_path)
    for name in os.listdir(dispatch_dir):
        if not name.endswith("_packet.json"):
            continue
        path = os.path.join(dispatch_dir, name)
        try:
            packet = _load(path)
        except (OSError, json.JSONDecodeError):
            continue
        if os.path.abspath(str(packet.get("_batch_output_path", ""))) == target:
            return path
    return None


def _write_rejection_seal(run_dir, packet_path, report_path, report):
    packet = _load(packet_path)
    provenance_dir = os.path.join(run_dir, ".cache", "provenance")
    os.makedirs(provenance_dir, exist_ok=True)
    path = os.path.join(provenance_dir, packet["dispatch_id"] + ".rejected.json")
    _write(path, {
        "contract_version": "modec-v4",
        "dispatch_id": packet["dispatch_id"],
        "packet_path": os.path.abspath(packet_path),
        "batch_path": os.path.abspath(report.get("batch_path", "")),
        "rejected_sha256": report.get("batch_sha256"),
        "validation_report_path": os.path.abspath(report_path),
        "failed_subshot_ids": report.get("failed_subshot_ids", []),
        "redispatch_required": True,
    })
    return path


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: prepare_composer_retry.py <run_dir> <composer_batch.json>")
        sys.exit(2)
    prepare(sys.argv[1], sys.argv[2])
