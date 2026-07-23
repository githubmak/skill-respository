"""Build compact, bounded previous/current/next Editor review capsules."""
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
            "capsule_version": "editor-review-v1",
            "window_id": "W%03d" % (index + 1), "scene": shot.get("scene", ""),
            "review_tier": risk["tier"], "review_scope": risk["review_scope"],
            "risk_reasons": risk["reasons"],
            # Every tier retains the current executable prompt and its
            # carryover. Tier only changes how much adjacent context is sent.
            "previous": _summary(before, relation="previous", tier=risk["tier"]),
            "current": _summary(current, relation="current", tier=risk["tier"]),
            "next": _summary(after, relation="next", tier=risk["tier"]),
        })
    return windows


def _summary(task, relation, tier):
    if not isinstance(task, dict):
        return None
    meta = task.get("qa_metadata", {}) if isinstance(task.get("qa_metadata"), dict) else {}
    continuity = meta.get("continuity_contract", {}) if isinstance(meta.get("continuity_contract"), dict) else {}
    result = {
        "shot_id": task.get("shot_id", ""), "duration": task.get("duration", 0),
        "source_subshot_ids": task.get("source_subshot_ids", []),
        "start_state": meta.get("start_state", ""), "end_state": meta.get("end_state", ""),
        "carryover": {
            "start_anchor": continuity.get("start_anchor", ""),
            "end_anchor": continuity.get("end_anchor", ""),
            "eyeline_continuity": continuity.get("eyeline_continuity", ""),
            "prop_state": continuity.get("prop_state", ""),
            "lighting_continuity": continuity.get("lighting_continuity", ""),
            "next_carryover": continuity.get("next_carryover", ""),
        },
    }
    if relation == "current":
        # Full current prompt is never shortened: it is the model-facing
        # source of truth. The explicit QA subset gives Editor its semantic
        # contracts without forwarding unrelated Composer scaffolding.
        result["full_prompt"] = task.get("full_prompt", "")
        result["review_contracts"] = {
            "performance_contract": meta.get("performance_contract", {}),
            "reroll_control": meta.get("reroll_control", {}),
            "dialogue_events": meta.get("dialogue_events", []),
        }
    elif tier == "high":
        # High risk retains the complete bounded scene window. If that cannot
        # fit in one packet, dispatch_cache splits the review task; it never
        # truncates dialogue or executable prompt content to save tokens.
        result["full_prompt"] = task.get("full_prompt", "")
    return result


def _load(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
