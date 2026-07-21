#!/usr/bin/env python3
"""Idempotently assemble the canonical Mode C v4 prompt package.

Phase 6 batch files are the source of truth when they exist. Otherwise the
existing canonical package is normalized in place. The canonical package is
never read alongside its own batch inputs, which prevents repeated Phase 7
runs from duplicating subshots.
"""

import json
import os
import re
import sys


BATCH_RE = re.compile(r"^composer_b\d+(?:_[0-9a-f]{8})?\.prompt_package\.json$")


def run(export_dir):
    """Merge Composer batches into ``merged.prompt_package.json`` once."""
    composer_dir = os.path.join(export_dir, ".cache", "composer")
    if not os.path.isdir(composer_dir):
        print("[MERGE V4] No composer cache found")
        return None

    input_paths = _input_paths(composer_dir)
    if not input_paths:
        print("[MERGE V4] No prompt packages found")
        return None

    items_by_subshot = {}
    anonymous_items = []
    duplicate_count = 0
    provenance_mode = any(os.path.exists(path + ".provenance.json") for path in input_paths)
    ranked_paths = []
    for path in input_paths:
        priority = os.path.getmtime(path)
        if provenance_mode:
            from record_batch_provenance import verify as verify_provenance
            verified, reason, manifest = verify_provenance(path)
            if not verified:
                print("[MERGE V4] WARN: Skipping unverified batch %s: %s" % (os.path.basename(path), reason))
                continue
            priority = float(manifest.get("recorded_at", priority) or priority)
        ranked_paths.append((priority, path, manifest if provenance_mode else None))

    for _, path, manifest in sorted(ranked_paths, key=lambda pair: (pair[0], pair[1])):
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError) as error:
            print("[MERGE V4] WARN: Skipping %s: %s" % (os.path.basename(path), error))
            continue
        source_items = data.get("shots", data.get("items", []))
        if not isinstance(source_items, list):
            print("[MERGE V4] WARN: Skipping non-array package %s" % os.path.basename(path))
            continue
        allowed_subshots = None
        if isinstance(manifest, dict) and manifest.get("validation_mode") == "partial":
            allowed_subshots = set(manifest.get("validated_subshot_ids", []))
        for item in source_items:
            if not isinstance(item, dict):
                continue
            subshot_id = str(item.get("subshot_id", "") or "")
            if allowed_subshots is not None and subshot_id not in allowed_subshots:
                continue
            copied = dict(item)
            copied.setdefault("duration", copied.get("duration_sec", 0))
            if subshot_id:
                if subshot_id in items_by_subshot:
                    duplicate_count += 1
                items_by_subshot[subshot_id] = copied
            else:
                anonymous_items.append(copied)

    items = anonymous_items + list(items_by_subshot.values())

    if not items:
        print("[MERGE V4] No valid shots found")
        return None

    items.sort(key=lambda item: (str(item.get("shot_id", "")), str(item.get("subshot_id", ""))))
    result = _build_package(items)
    output_path = os.path.join(composer_dir, "merged.prompt_package.json")
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)

    print(
        "[MERGE V4] %d source file(s) -> %d unique subshot(s), %d duplicate(s) removed -> %s"
        % (len(ranked_paths), len(items), duplicate_count, output_path)
    )
    return result


def _input_paths(composer_dir):
    names = sorted(os.listdir(composer_dir))
    batches = [os.path.join(composer_dir, name) for name in names if BATCH_RE.match(name)]
    if batches:
        return batches
    for name in ("merged.prompt_package.json", "prompt_package.json"):
        path = os.path.join(composer_dir, name)
        if os.path.exists(path):
            return [path]
    return []


def _build_package(items):
    by_shot = {}
    for item in items:
        by_shot.setdefault(str(item.get("shot_id", "")), []).append(item)

    merged = []
    for shot_id in sorted(by_shot):
        subshots = sorted(by_shot[shot_id], key=lambda item: str(item.get("subshot_id", "")))
        duration = sum(float(item.get("duration", 0) or 0) for item in subshots)
        merged.append({
            "shot_id": shot_id,
            "duration": duration,
            "duration_sec": duration,
            "full_prompt": "\n\n---\n\n".join(str(item.get("full_prompt", "") or "") for item in subshots),
            "negative_prompt": " | ".join(dict.fromkeys(
                str(item.get("negative_prompt", "") or "") for item in subshots
                if item.get("negative_prompt")
            )),
        })
    return {
        "contract_version": "modec-v4",
        "items": items,
        "shots": items,
        "merged_full_prompts": merged,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: merge_prompts.py <run_dir>")
        sys.exit(2)
    sys.exit(0 if run(sys.argv[1]) is not None else 1)
