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
            if isinstance(target, dict):
                shot_id = str(target.get("shot_id", "") or target.get("subshot_id", ""))
            else:
                shot_id = str(target or "")
            if not shot_id:
                continue
            shots.append(shot_id)
            if isinstance(target, dict):
                target_fields = target.get("fields")
                if not target_fields:
                    target_fields = [target.get("field") or target.get("field_path") or "validator_reported_field"]
            else:
                target_fields = ["validator_reported_field"]
            fields.setdefault(shot_id, set()).update(str(field) for field in target_fields if field)
    shots = sorted(set(shots))
    retry_batch_size = 1 if _has_previous_retry(run_dir, shots) else None
    try:
        packets = prepare_dispatch_packets(run_dir, "master_production", batch_size=retry_batch_size, subshot_ids=shots)
    except ValueError as error:
        if "packet exceeds" not in str(error):
            raise
        packets = prepare_dispatch_packets(run_dir, "master_production", batch_size=1, subshot_ids=shots)
    for packet_path in packets:
        with open(packet_path, encoding="utf-8-sig") as handle:
            packet = json.load(handle)
        packet["retry_context_path"] = atomic_json(packet_path + ".retry.json", {
            "mode": "field_patch", "fields_by_main_shot": {key: sorted(value) for key, value in fields.items()},
            "rule": "Return only listed main shots and modify only listed fields; locked fields survive merge.",
        })
        atomic_json(packet_path, packet)
    return packets


def _has_previous_retry(run_dir, shot_ids):
    targets = set(str(shot_id) for shot_id in shot_ids or [])
    if not targets:
        return False
    dispatch_dir = os.path.join(run_dir, ".cache", "dispatch")
    if not os.path.isdir(dispatch_dir):
        return False
    for name in os.listdir(dispatch_dir):
        if not name.endswith("_packet.json"):
            continue
        path = os.path.join(dispatch_dir, name)
        try:
            with open(path, encoding="utf-8-sig") as handle:
                packet = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if packet.get("phase") != "master_production":
            continue
        if not (packet.get("is_retry") or packet.get("retry_context_path")):
            continue
        packet_shots = {
            str(item.get("shot_id", "") or item.get("subshot_id", ""))
            for item in packet.get("items", []) if isinstance(item, dict)
        }
        if targets & packet_shots:
            return True
    return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: prepare_master_retry.py <run_dir>")
    print("\n".join(prepare(sys.argv[1])))
