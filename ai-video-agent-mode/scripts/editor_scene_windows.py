"""Build one deterministic review window per contiguous scene."""

import json
import os


MAX_SCENE_WINDOW_SHOTS = 16
MAX_SCENE_WINDOW_RECORD_CHARS = 90000


def build(run_dir, shot_ids=None):
    package = _load(os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json"))
    plan = _load(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"))
    available = {str(item.get("shot_id", "")) for item in package.get("shots", []) if isinstance(item, dict)}
    planned = [item for item in plan.get("shots", []) if isinstance(item, dict)]
    wanted = {str(value) for value in shot_ids or [] if str(value).strip()}
    package_by_id = {
        str(item.get("shot_id", "")): item
        for item in package.get("shots", []) if isinstance(item, dict)
    }
    groups = []
    for index, shot in enumerate(planned):
        shot_id = str(shot.get("shot_id", ""))
        if shot_id not in available:
            continue
        scene = str(shot.get("scene", "") or "__default__")
        if not groups or groups[-1]["scene"] != scene:
            groups.append({"scene": scene, "members": []})
        groups[-1]["members"].append((index, shot_id))

    windows = []
    for group_index, group in enumerate(groups, 1):
        member_ids = [shot_id for _, shot_id in group["members"]]
        if wanted and not wanted.intersection(member_ids):
            continue
        segments = _bounded_segments(group["members"], planned, package_by_id)
        for segment_index, segment in enumerate(segments, 1):
            segment_ids = [shot_id for _, shot_id in segment]
            first_index = segment[0][0]
            last_index = segment[-1][0]
            previous_id = str(planned[first_index - 1].get("shot_id", "")) if first_index else ""
            next_id = str(planned[last_index + 1].get("shot_id", "")) if last_index + 1 < len(planned) else ""
            base_id = "W%03d" % group_index
            window_id = base_id if len(segments) == 1 else "%s-%02d" % (base_id, segment_index)
            windows.append({
                "capsule_version": "editor-scene-review-v3",
                "window_id": window_id,
                "scene": group["scene"],
                "scene_segment_index": segment_index,
                "scene_segment_count": len(segments),
                "review_tier": "full_model_review",
                "review_scope": "contiguous scene segment plus adjacent boundary shots",
                "shot_ids": segment_ids,
                "previous_boundary_shot_id": previous_id if previous_id in available else "",
                "next_boundary_shot_id": next_id if next_id in available else "",
            })
    return windows


def _bounded_segments(members, planned, package_by_id):
    segments = []
    current = []
    plan_by_id = {
        str(item.get("shot_id", "")): item for item in planned if isinstance(item, dict)
    }
    for member in members:
        candidate = current + [member]
        shot_ids = [shot_id for _, shot_id in candidate]
        record_chars = len(json.dumps({
            "shots": [package_by_id.get(shot_id, {}) for shot_id in shot_ids],
            "planned_shots": [plan_by_id.get(shot_id, {}) for shot_id in shot_ids],
        }, ensure_ascii=False, separators=(",", ":")))
        if current and (
            len(candidate) > MAX_SCENE_WINDOW_SHOTS
            or record_chars > MAX_SCENE_WINDOW_RECORD_CHARS
        ):
            segments.append(current)
            current = [member]
        else:
            current = candidate
    if current:
        segments.append(current)
    return segments


def _load(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
