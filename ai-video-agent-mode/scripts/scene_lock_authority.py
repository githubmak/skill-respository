#!/usr/bin/env python3
"""Validate immutable Scene Lock references without rewriting creative facts."""

import json
import os


SCENE_LOCK_PALETTE_FIELDS = (
    "space_id",
    "space_master_sentence",
    "tone_palette",
    "light_texture_purpose",
)


def scene_lock_authority_issues(items, output_path):
    run_dir = _run_dir_from_output(output_path)
    lock_path = os.path.join(run_dir, ".cache", "analysis", "scene_locks.json") if run_dir else ""
    if not lock_path or not os.path.isfile(lock_path):
        return []
    try:
        with open(lock_path, encoding="utf-8-sig") as handle:
            locks = json.load(handle).get("scenes", [])
    except (OSError, json.JSONDecodeError, AttributeError):
        return []

    by_scene = {}
    by_space = {}
    for lock in locks if isinstance(locks, list) else []:
        if not isinstance(lock, dict):
            continue
        scene = str(lock.get("scene", "") or "").strip()
        space_id = str(lock.get("space_id", "") or "").strip()
        if scene:
            by_scene[scene] = lock
        if space_id:
            by_space[space_id] = lock

    issues = []
    for item in items:
        if not isinstance(item, dict):
            continue
        metadata = item.get("qa_metadata")
        if not isinstance(metadata, dict):
            continue
        palette = metadata.get("scene_tone_palette")
        if not isinstance(palette, dict):
            continue
        scene_ref = str(item.get("scene", "") or item.get("_scene_lock_ref", "") or "").strip()
        lock = by_scene.get(scene_ref) or by_space.get(str(palette.get("space_id", "") or "").strip())
        if not lock:
            continue
        identity = str(item.get("shot_id", "") or item.get("subshot_id", "") or "unknown")
        for field in SCENE_LOCK_PALETTE_FIELDS:
            value = lock.get(field)
            if isinstance(value, str) and value.strip() and palette.get(field) != value:
                issues.append("%s.%s" % (identity, field))
    return issues


def _run_dir_from_output(output_path):
    absolute = os.path.abspath(output_path)
    marker = os.sep + ".cache" + os.sep
    return absolute.split(marker, 1)[0] if marker in absolute else ""
