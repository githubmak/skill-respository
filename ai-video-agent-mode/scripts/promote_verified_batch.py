#!/usr/bin/env python3
"""Promote one verified Agent batch to its public output path."""

import hashlib
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from record_batch_provenance import verify


def promote(packet_path):
    packet = _load(packet_path)
    batch_path = packet.get("_batch_output_path", "")
    output_path = packet.get("output_path", "")
    if not batch_path or not output_path:
        raise SystemExit("packet is missing _batch_output_path or output_path")
    verified, reason, manifest = verify(batch_path)
    if not verified:
        raise SystemExit("unverified batch cannot be promoted: %s" % reason)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    temporary = output_path + ".tmp"
    shutil.copyfile(batch_path, temporary)
    os.replace(temporary, output_path)
    promotion = {
        "contract_version": "jimeng-t2v-v1",
        "packet_path": os.path.abspath(packet_path),
        "source_batch": os.path.abspath(batch_path),
        "source_provenance": manifest,
        "output_path": os.path.abspath(output_path),
        "output_sha256": _sha256(output_path),
        "promoted_at": time.time(),
    }
    with open(output_path + ".promotion_provenance.json", "w", encoding="utf-8") as handle:
        json.dump(promotion, handle, ensure_ascii=False, indent=2)
    print("[PROMOTE] PASS %s -> %s" % (batch_path, output_path))
    return output_path


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: promote_verified_batch.py <dispatch_packet.json>")
        sys.exit(2)
    promote(sys.argv[1])
