"""Write a compact, factual resume summary from validated phase artifacts."""
import hashlib
import json
import os
import sys
import time


def write_summary(run_dir, phase, output_paths):
    artifacts = [_artifact(path) for path in output_paths if os.path.exists(path)]
    summary = {
        "contract_version": "modec-v4",
        "phase": phase,
        "written_at": time.time(),
        "artifacts": artifacts,
    }
    state_path = os.path.join(run_dir, ".cache", "pipeline_state.json")
    try:
        with open(state_path, "r", encoding="utf-8-sig") as handle:
            phase_state = json.load(handle).get("phases", {}).get(phase, {})
        summary["timing"] = {
            key: phase_state.get(key)
            for key in ("started_at", "spawn_time", "completed_at", "elapsed_seconds", "retries", "timeout_count")
            if phase_state.get(key) is not None
        }
    except (OSError, json.JSONDecodeError):
        pass
    summary_dir = os.path.join(run_dir, ".cache", "stage_summary")
    os.makedirs(summary_dir, exist_ok=True)
    path = os.path.join(summary_dir, "%s.json" % phase)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    return path


def _artifact(path):
    with open(path, "rb") as handle:
        raw = handle.read()
    artifact = {
        "path": path,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        artifact["format"] = "binary_or_text"
        return artifact
    artifact["format"] = "json"
    if isinstance(data, dict):
        artifact["top_level_keys"] = sorted(data.keys())[:12]
        for key in ("items", "shots", "repair_targets"):
            value = data.get(key)
            if isinstance(value, list):
                artifact["%s_count" % key] = len(value)
        ids = []
        for key in ("items", "shots", "repair_targets"):
            for item in data.get(key, []) if isinstance(data.get(key), list) else []:
                if isinstance(item, dict):
                    identifier = item.get("subshot_id") or item.get("shot_id")
                    if identifier and identifier not in ids:
                        ids.append(identifier)
        if ids:
            artifact["sample_ids"] = ids[:12]
    return artifact


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("usage: write_stage_summary.py <run_dir> <phase> <output_path> [...]")
        sys.exit(2)
    print(write_summary(sys.argv[1], sys.argv[2], sys.argv[3:]))
