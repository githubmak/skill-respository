#!/usr/bin/env python3
"""Normalize/upgrade prompt packages to the Mode C v4 contract.

Narrative wording is preserved. Legacy v3 sections are deterministically folded
into the four model-facing v4 sections; QA prose and negative prompts are moved
to sibling fields so they are not sent as visual instructions.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from modec_v4 import legacy_negative_prompt, normalize_v4_prompt
from negative_prompts import PLACEHOLDER, build_negative_prompt_for_item


def normalize_package(input_path, output_path=None):
    with open(input_path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)

    shots = data.get("shots", data.get("items", []))
    normalized = []
    for shot in shots:
        item = dict(shot)
        original = str(item.get("full_prompt", ""))
        item["full_prompt"] = normalize_prompt(original)
        item.setdefault("duration", item.get("duration_sec", 0))
        item.setdefault("duration_sec", item.get("duration", 0))
        item.setdefault("qa_metadata", _legacy_qa_metadata(item, original))
        item.setdefault("generation_control", {
            "mode": "t2v",
            "audio_enabled": False,
            "reference_assets": [],
        })

        current_negative = str(item.get("negative_prompt", "") or "").strip()
        legacy_negative = legacy_negative_prompt(original)
        if current_negative in ("", PLACEHOLDER) or PLACEHOLDER in current_negative:
            item["negative_prompt"] = build_negative_prompt_for_item(item)
        elif legacy_negative and current_negative == legacy_negative and PLACEHOLDER in legacy_negative:
            item["negative_prompt"] = build_negative_prompt_for_item(item)
        else:
            item["negative_prompt"] = current_negative
        normalized.append(item)

    result = {
        "contract_version": "modec-v4",
        "items": normalized,
        "shots": normalized,
        "merged_full_prompts": _merged_full_prompts(normalized),
    }

    out = output_path or input_path
    out_dir = os.path.dirname(out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print("[NORMALIZE V4] %d shots -> %s" % (len(normalized), out))
    return result


def normalize_prompt(prompt):
    text = str(prompt or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"(\d+(?:\.\d+)?)\s+K\b", r"\1K", text)
    text = re.sub(r"(\d+(?:\.\d+)?)\s+m/s\b", r"\1m/s", text)
    text = normalize_v4_prompt(text)
    text = text.replace(PLACEHOLDER, "").strip()
    return text


def _legacy_qa_metadata(item, original_prompt):
    """Best-effort compatibility metadata; regenerated v4 output is stricter."""
    existing = item.get("qa_metadata")
    if isinstance(existing, dict):
        return existing
    visible = item.get("visible_characters", item.get("characters", []))
    if isinstance(visible, str):
        visible = [part.strip() for part in re.split(r"[;；,，、/]+", visible) if part.strip()]
    visible = visible if isinstance(visible, list) else []
    primary = str(visible[0]) if visible else ""
    supporting = [str(char) for char in visible[1:2]]
    background = [str(char) for char in visible[2:]]
    duration = float(item.get("duration", item.get("duration_sec", 0)) or 0)
    return {
        "dramatic_goal": "旧版提示词迁移；下次Composer运行时重新生成精确目标",
        "performance_priority": {
            "primary": primary,
            "supporting": supporting,
            "background": background,
        },
        "action_budget": {
            "primary_action_count": 1 if primary else 0,
            "emotion_turn_count": 1 if primary else 0,
            "supporting_reaction_count": 1 if supporting else 0,
            "camera_move_count": 1,
        },
        "start_state": str(item.get("start_state", "") or "旧版迁移待复核"),
        "end_state": str(item.get("end_state", "") or "旧版迁移待复核"),
        "dialogue_refs": item.get("dialogue_refs", []),
        "migration_note": "modec-v3-to-v4",
        "duration": duration,
    }


def _merged_full_prompts(items):
    by_shot = {}
    for item in items:
        by_shot.setdefault(item.get("shot_id", ""), []).append(item)
    merged = []
    for shot_id in sorted(by_shot):
        subshots = sorted(by_shot[shot_id], key=lambda value: value.get("subshot_id", ""))
        total = sum(float(subshot.get("duration", 0) or 0) for subshot in subshots)
        merged.append({
            "shot_id": shot_id,
            "duration": total,
            "duration_sec": total,
            "full_prompt": "\n\n---\n\n".join(subshot.get("full_prompt", "") for subshot in subshots),
            "negative_prompt": " | ".join(dict.fromkeys(
                subshot.get("negative_prompt", "") for subshot in subshots
                if subshot.get("negative_prompt", "")
            )),
        })
    return merged


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: normalize_prompt_package.py <input.prompt_package.json> [output.prompt_package.json]")
        sys.exit(2)
    normalize_package(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)

