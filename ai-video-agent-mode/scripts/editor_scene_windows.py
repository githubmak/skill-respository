"""Build bounded previous/current/next main-shot review windows."""
import json
import os

from shot_semantics import dispatch_risk


def build(run_dir):
    package = _load(os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json"))
    plan = _load(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"))
    tasks = {str(item.get("shot_id", "")): item for item in package.get("shots", []) if isinstance(item, dict)}
    planned = [shot for shot in plan.get("shots", []) if isinstance(shot, dict)]
    windows = []
    for index, shot in enumerate(planned):
        current = tasks.get(str(shot.get("shot_id", "")))
        if not current:
            continue
        before = tasks.get(str(planned[index - 1].get("shot_id", ""))) if index else None
        after = tasks.get(str(planned[index + 1].get("shot_id", ""))) if index + 1 < len(planned) else None
        risk = dispatch_risk(current)
        windows.append({
            "window_id": "W%03d" % (index + 1), "scene": shot.get("scene", ""),
            "review_tier": risk["tier"], "review_scope": risk["review_scope"],
            "risk_reasons": risk["reasons"],
            "previous": _summary(before), "current": _summary(current, include_prompt=True), "next": _summary(after),
        })
    return windows


def _summary(task, include_prompt=False):
    if not isinstance(task, dict):
        return None
    meta = task.get("qa_metadata", {}) if isinstance(task.get("qa_metadata"), dict) else {}
    result = {"shot_id": task.get("shot_id", ""), "duration": task.get("duration", 0),
              "source_subshot_ids": task.get("source_subshot_ids", []),
              "end_state": meta.get("end_state", ""), "continuity": meta.get("continuity_contract", {})}
    if include_prompt:
        result["full_prompt"] = task.get("full_prompt", "")
    return result


def _load(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
