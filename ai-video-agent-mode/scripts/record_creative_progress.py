#!/usr/bin/env python3
"""Record mechanical byte/item growth for model-authored Orchestrator drafts."""

import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from pipeline_runtime import atomic_json


def record(request_path):
    with open(request_path, encoding="utf-8-sig") as handle:
        request = json.load(handle)
    outputs = request.get("required_outputs", {}) if isinstance(request, dict) else {}
    artifacts = {}
    total_items = 0
    for name, path in outputs.items():
        row = {"path": path, "exists": os.path.isfile(path), "bytes": 0, "parseable": False, "item_count": 0}
        if row["exists"]:
            row["bytes"] = os.path.getsize(path)
            row["sha256"] = _sha256(path)
            try:
                with open(path, encoding="utf-8-sig") as handle:
                    payload = json.load(handle)
                row["parseable"] = isinstance(payload, dict)
                key = "shots" if name == "shot_plan_draft" else "scenes"
                values = payload.get(key, []) if isinstance(payload, dict) else []
                row["item_count"] = len(values) if isinstance(values, list) else 0
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                pass
        total_items += row["item_count"]
        artifacts[name] = row
    progress_path = request.get("checkpoint_policy", {}).get("progress_path")
    if not progress_path:
        raise ValueError("creative request has no progress_path")
    previous = _load(progress_path)
    now = time.time()
    total_bytes = sum(item["bytes"] for item in artifacts.values())
    grew = total_items > int(previous.get("total_items", 0) or 0) or total_bytes > int(previous.get("total_bytes", 0) or 0)
    report = {
        "authority": "engineering_observation_only",
        "semantic_transform": False,
        "authoring_started_at": request.get("authoring_started_at"),
        "observed_at": now,
        "last_progress_at": now if grew else previous.get("last_progress_at"),
        "progress_count": int(previous.get("progress_count", 0) or 0) + (1 if grew else 0),
        "total_items": max(total_items, int(previous.get("total_items", 0) or 0)),
        "total_bytes": max(total_bytes, int(previous.get("total_bytes", 0) or 0)),
        "artifacts": artifacts,
    }
    atomic_json(progress_path, report)
    print(json.dumps(report, ensure_ascii=False))
    return report


def _load(path):
    try:
        with open(path, encoding="utf-8-sig") as handle:
            value = json.load(handle)
            return value if isinstance(value, dict) else {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: record_creative_progress.py <creative_blueprint_request.json>")
    record(sys.argv[1])
