"""Build deterministic shot-ID windows; creative text is staged unclipped elsewhere."""

import json
import os


def build(run_dir, shot_ids=None):
    package = _load(os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json"))
    plan = _load(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"))
    available = {str(item.get("shot_id", "")) for item in package.get("shots", []) if isinstance(item, dict)}
    planned = [item for item in plan.get("shots", []) if isinstance(item, dict)]
    wanted = {str(value) for value in shot_ids or [] if str(value).strip()}
    windows = []
    for index, shot in enumerate(planned):
        shot_id = str(shot.get("shot_id", ""))
        if shot_id not in available or (wanted and shot_id not in wanted):
            continue
        previous_id = str(planned[index - 1].get("shot_id", "")) if index else ""
        next_id = str(planned[index + 1].get("shot_id", "")) if index + 1 < len(planned) else ""
        windows.append({
            "capsule_version": "editor-review-v2",
            "window_id": "W%03d" % (index + 1),
            "scene": shot.get("scene", ""),
            "review_tier": "full_model_review",
            "review_scope": "previous-current-next exact creative records",
            "risk_reasons": [],
            "previous": {"shot_id": previous_id} if previous_id in available else None,
            "current": {"shot_id": shot_id},
            "next": {"shot_id": next_id} if next_id in available else None,
        })
    return windows


def _load(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
