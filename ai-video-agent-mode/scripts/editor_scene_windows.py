"""Build compact, bounded previous/current/next Editor review capsules."""
import json
import os

from shot_semantics import dispatch_risk


def build(run_dir, shot_ids=None):
    package = _load(os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json"))
    plan = _load(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"))
    tasks = {str(item.get("shot_id", "")): item for item in package.get("shots", []) if isinstance(item, dict)}
    planned = [shot for shot in plan.get("shots", []) if isinstance(shot, dict)]
    wanted = {str(shot_id).strip() for shot_id in (shot_ids or []) if str(shot_id).strip()}
    windows = []
    for index, shot in enumerate(planned):
        shot_id = str(shot.get("shot_id", "") or "")
        if wanted and shot_id not in wanted:
            continue
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
    if relation != "current":
        result = {
            "shot_id": task.get("shot_id", ""),
            "duration": task.get("duration", 0),
        }
        if relation == "previous":
            result["end_state"] = _clip(meta.get("end_state", ""), 70)
            result["carryover"] = {
                "end_anchor": _clip(continuity.get("end_anchor", ""), 70),
                "prop_state": _clip(continuity.get("prop_state", ""), 80),
                "next_carryover": _clip(continuity.get("next_carryover", ""), 70),
            }
        else:
            result["start_state"] = _clip(meta.get("start_state", ""), 70)
            result["carryover"] = {
                "start_anchor": _clip(continuity.get("start_anchor", ""), 70),
                "prop_state": _clip(continuity.get("prop_state", ""), 80),
            }
        return result
    if relation == "current" and tier != "high":
        return {
            "shot_id": task.get("shot_id", ""),
            "duration": task.get("duration", 0),
            "start_state": _clip(meta.get("start_state", ""), 70),
            "end_state": _clip(meta.get("end_state", ""), 70),
            "carryover": {
                "start_anchor": _clip(continuity.get("start_anchor", ""), 70),
                "end_anchor": _clip(continuity.get("end_anchor", ""), 70),
                "prop_state": _clip(continuity.get("prop_state", ""), 80),
                "next_carryover": _clip(continuity.get("next_carryover", ""), 70),
            },
            "prompt_digest": _prompt_digest(task.get("full_prompt", ""), max_section_chars=28),
            "review_contracts": _review_contract_digest(meta),
        }
    result = {
        "shot_id": task.get("shot_id", ""), "duration": task.get("duration", 0),
        "source_subshot_ids": task.get("source_subshot_ids", []),
        "start_state": _clip(meta.get("start_state", ""), 70), "end_state": _clip(meta.get("end_state", ""), 70),
        "carryover": {
            "start_anchor": _clip(continuity.get("start_anchor", ""), 55),
            "end_anchor": _clip(continuity.get("end_anchor", ""), 55),
            "eyeline_continuity": _clip(continuity.get("eyeline_continuity", ""), 70),
            "next_carryover": _clip(continuity.get("next_carryover", ""), 55),
        },
        "prompt_digest": _prompt_digest(task.get("full_prompt", ""), max_section_chars=18),
    }
    if relation == "current":
        # Editor Pass 2 is a semantic carryover pass after deterministic
        # validators have accepted the complete prompt.  Even high-risk action
        # windows must batch efficiently: carry a digest plus the contracts that
        # explain what to inspect.  The complete merged package is available via
        # packet.source_path for on-demand lookup and is not duplicated into
        # every window.
        result["review_contracts"] = _review_contract_digest(meta, detail="high" if tier == "high" else "standard")
    return result


def _prompt_digest(prompt, max_section_chars=35):
    prompt = str(prompt or "")
    labels = ["生成规格", "主体与空间锁定", "主镜头连续规则", "子镜头组", "光照、声音与稳定约束"]
    digest = {}
    for index, label in enumerate(labels):
        marker = label + "："
        start = prompt.find(marker)
        if start < 0:
            digest[label] = ""
            continue
        start += len(marker)
        end = len(prompt)
        for next_label in labels[index + 1:]:
            next_marker = "\n\n" + next_label + "："
            found = prompt.find(next_marker, start)
            if found >= 0:
                end = found
                break
        section = " ".join(prompt[start:end].split())
        digest[label] = section[:max_section_chars]
    return digest


def _review_contract_digest(meta, detail="standard"):
    performance = meta.get("performance_contract", {}) if isinstance(meta.get("performance_contract"), dict) else {}
    reroll = meta.get("reroll_control", {}) if isinstance(meta.get("reroll_control"), dict) else {}
    continuity = meta.get("continuity_contract", {}) if isinstance(meta.get("continuity_contract"), dict) else {}
    pressure = meta.get("pressure_release_design", {}) if isinstance(meta.get("pressure_release_design"), dict) else {}
    punch = meta.get("story_punch_contract", {}) if isinstance(meta.get("story_punch_contract"), dict) else {}
    priority = meta.get("performance_priority", {}) if isinstance(meta.get("performance_priority"), dict) else {}
    dialogue_events = meta.get("dialogue_events", []) if isinstance(meta.get("dialogue_events"), list) else []
    digest = {
        "priority": priority,
        "trigger": _clip(performance.get("trigger_event", ""), 70),
        "body": _clip(performance.get("primary_body_action", ""), 70),
        "eye": _clip(performance.get("eye_focus", ""), 60),
        "end_residue": _clip(performance.get("end_residue", ""), 70),
        "continuity": {
            "state_change": continuity.get("state_change", ""),
            "next_carryover": _clip(continuity.get("next_carryover", ""), 70),
        },
        "risk": reroll.get("risk_level", ""),
        "risk_reason": _clip(reroll.get("risk_reason", ""), 70),
        "dialogue_locks": [
            {
                "ref": event.get("ref", ""),
                "speaker": event.get("speaker", ""),
                "text": _clip(event.get("text", ""), 90),
                "lip_sync": event.get("lip_sync", False),
            }
            for event in dialogue_events
            if isinstance(event, dict)
        ],
    }
    if detail == "high":
        digest["pressure"] = {
            "object": _clip(pressure.get("pressure_object", ""), 80),
            "release_trigger": _clip(pressure.get("release_trigger", ""), 80),
        }
        digest["story_punch"] = {
            "audience_question": _clip(punch.get("audience_question", ""), 100),
            "dramatic_turn": _clip(punch.get("dramatic_turn", ""), 100),
        }
    return digest


def _clip(value, limit):
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)] + "…"


def _load(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
