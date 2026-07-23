"""Archive explicitly rejected, unverified dispatch packets before redispatch."""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from pipeline_state import load_state, save_state


def archive(run_dir, phase, packet_paths, reason):
    run_dir = os.path.abspath(run_dir)
    dispatch_dir = os.path.join(run_dir, ".cache", "dispatch")
    archive_dir = os.path.join(dispatch_dir, "rejected")
    provenance_dir = os.path.join(run_dir, ".cache", "provenance")
    os.makedirs(archive_dir, exist_ok=True)
    os.makedirs(provenance_dir, exist_ok=True)
    state = load_state(run_dir)
    archived = []
    for packet_path in packet_paths:
        packet_path = os.path.abspath(packet_path)
        if os.path.dirname(packet_path) != dispatch_dir:
            raise ValueError("packet must be in the active dispatch directory")
        packet = _load(packet_path)
        dispatch_id = str(packet.get("dispatch_id", "") or "")
        if packet.get("phase") != phase or not dispatch_id:
            raise ValueError("packet phase or dispatch id does not match")
        output = str(packet.get("_batch_output_path", "") or "")
        if os.path.exists(output + ".provenance.json"):
            raise ValueError("verified packet cannot be archived")
        rejection_path = os.path.join(provenance_dir, dispatch_id + ".rejected.json")
        _write(rejection_path, {
            "contract_version": "jimeng-t2v-v1", "dispatch_id": dispatch_id,
            "phase": phase, "packet_path": packet_path, "reason": reason,
            "rejected_sha256": _sha256(output) if os.path.isfile(output) else "",
            "rejected_at": time.time(),
        })
        shutil.move(packet_path, os.path.join(archive_dir, os.path.basename(packet_path)))
        scaffold = str(packet.get("composer_scaffold_path", "") or "")
        if scaffold and os.path.isfile(scaffold) and os.path.dirname(scaffold) == dispatch_dir:
            shutil.move(scaffold, os.path.join(archive_dir, os.path.basename(scaffold)))
        dispatch = state["phases"][phase].get("dispatches", {}).get(dispatch_id)
        if isinstance(dispatch, dict):
            dispatch["status"] = "rejected"
            dispatch["rejection_path"] = rejection_path
        archived.append(dispatch_id)
    state["phases"][phase]["status"] = "failed"
    state["phases"][phase]["retries"] = state["phases"][phase].get("retries", 0) + 1
    save_state(run_dir, state)
    return archived


def _load(path):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


def _write(path, value):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("packets", nargs="+")
    args = parser.parse_args()
    print(json.dumps(archive(args.run_dir, args.phase, args.packets, args.reason), ensure_ascii=False))
