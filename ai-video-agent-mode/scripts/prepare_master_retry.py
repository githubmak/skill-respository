"""Create a field-scoped retry packet for failed main-shot tasks."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from dispatch_cache import prepare_dispatch_packets
from pipeline_runtime import atomic_json


def prepare(run_dir, review_path=None):
    review_path = review_path or os.path.join(run_dir, ".cache", "review", "llm_gate_result.json")
    with open(review_path, encoding="utf-8-sig") as handle:
        review = json.load(handle)
    fields, shots = {}, []
    for window in review.get("windows", []):
        for target in window.get("repair_targets", []):
            shot_id = str(target.get("shot_id", "") or target.get("subshot_id", ""))
            if not shot_id:
                continue
            shots.append(shot_id)
            fields.setdefault(shot_id, set()).update(target.get("fields", ["validator_reported_field"]))
    shots = sorted(set(shots))
    packets = prepare_dispatch_packets(run_dir, "master_production", subshot_ids=shots)
    for packet_path in packets:
        with open(packet_path, encoding="utf-8-sig") as handle:
            packet = json.load(handle)
        packet["retry_context_path"] = atomic_json(packet_path + ".retry.json", {
            "mode": "field_patch", "fields_by_main_shot": {key: sorted(value) for key, value in fields.items()},
            "rule": "Return only listed main shots and modify only listed fields; locked fields survive merge.",
        })
        atomic_json(packet_path, packet)
    return packets


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: prepare_master_retry.py <run_dir>")
    print("\n".join(prepare(sys.argv[1])))
