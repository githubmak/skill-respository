#!/usr/bin/env python3
"""Validate a normalized Mode C v4 package in a run directory."""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from modec_v4 import (
    FORBIDDEN_MODEL_TERMS,
    LEGACY_LABELS,
    PROMPT_LABELS,
    action_budget_issues,
    attention_handoff_issues,
    camera_competition_issues,
    dialogue_event_issues,
    fight_continuity_issues,
    fight_transition_issues,
    performance_causality_issues,
    prompt_length_issues,
    role_partition_issues,
    split_sections,
    timeline_issues,
    visibility_issues,
)
from negative_prompts import PLACEHOLDER, is_fight_context


def main(run_dir):
    package = _load_json(_first_existing(run_dir, [
        ".cache/composer/merged.prompt_package.json",
        ".cache/composer/prompt_package.json",
        ".cache/prompt_package.json",
    ]))
    plan = _load_json(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"))
    director = _load_optional_json(os.path.join(run_dir, ".cache", "director", "director_pass.json"))
    llm_review = _load_optional_json(os.path.join(run_dir, ".cache", "review", "llm_gate_result.json"))
    shots = package.get("shots", [])
    items = package.get("items", [])
    expected = {
        subshot.get("subshot_id", ""): subshot
        for shot in plan.get("shots", [])
        for subshot in shot.get("subshots", [])
    }
    director_map = {
        item.get("subshot_id", ""): item for item in director.get("items", []) if item.get("subshot_id")
    }
    errors = []
    warnings = []
    fight_records = []

    if package.get("contract_version") != "modec-v4":
        errors.append("contract_version必须是modec-v4")
    if not isinstance(llm_review, dict) or not llm_review or "items" in llm_review:
        errors.append("缺少editor_pass2的llm_gate_result.json")
    else:
        if llm_review.get("pass") is not True:
            errors.append("editor_pass2复审未通过")
        blocking = llm_review.get("blocking")
        if not isinstance(blocking, list) or blocking:
            errors.append("editor_pass2复审存在blocking")
    if not isinstance(shots, list) or not shots:
        errors.append("shots必须是非空数组")
    if items != shots:
        errors.append("items与shots必须内容完全相同")
    actual_ids = [shot.get("subshot_id", "") for shot in shots]
    if set(actual_ids) != set(expected) or len(actual_ids) != len(expected):
        errors.append("subshot覆盖或唯一性不一致")

    for shot in shots:
        sid = shot.get("subshot_id", "?")
        prefix = sid + ": "
        full_prompt = str(shot.get("full_prompt", "") or "")
        metadata = shot.get("qa_metadata", {})
        metadata = metadata if isinstance(metadata, dict) else {}
        sections = split_sections(full_prompt, PROMPT_LABELS)
        if list(sections) != PROMPT_LABELS:
            errors.append(prefix + "full_prompt必须按顺序包含v4四段")
        if full_prompt.count("\n\n") != 3:
            errors.append(prefix + "四段之间必须恰好三个空行")
        if any(re.search(rf"(?:^|\n\n){re.escape(label)}[：:]", full_prompt) for label in LEGACY_LABELS):
            errors.append(prefix + "含v3旧字段")
        if any(term in full_prompt for term in FORBIDDEN_MODEL_TERMS):
            errors.append(prefix + "模型提示词混入工程/QA文本")
        if "负面提示词" in full_prompt or PLACEHOLDER in full_prompt:
            errors.append(prefix + "负面词混入full_prompt")
        for issue in prompt_length_issues(full_prompt, shot.get("duration", 0)):
            errors.append(prefix + issue)
        for issue in timeline_issues(full_prompt, shot.get("duration", 0)):
            errors.append(prefix + issue)
        for issue in camera_competition_issues(full_prompt, metadata.get("editorial_mode", shot.get("editorial_mode", "continuous_take"))):
            errors.append(prefix + issue)

        plan_item = expected.get(sid, {})
        director_item = director_map.get(sid, {})
        visible = _as_list(plan_item.get("visible_characters", plan_item.get("characters", [])))
        for issue in role_partition_issues(metadata, visible):
            errors.append(prefix + issue)
        for issue in performance_causality_issues(metadata, visible):
            errors.append(prefix + issue)
        fight = is_fight_context(
            plan_item.get("scene_type", ""), plan_item.get("shot_type", ""), full_prompt
        )
        for issue in action_budget_issues(metadata, shot.get("duration", 0), fight):
            errors.append(prefix + issue)
        for issue in attention_handoff_issues(metadata, full_prompt):
            errors.append(prefix + issue)
        if fight:
            for issue in fight_continuity_issues(metadata, shot.get("duration", 0)):
                errors.append(prefix + issue)
            fight_records.append((sid, metadata))
        shot_size = director_item.get("shot_size", plan_item.get("shot_size", ""))
        for issue in visibility_issues(full_prompt, shot_size):
            errors.append(prefix + issue)

        negative = str(shot.get("negative_prompt", "") or "").strip()
        if not negative or PLACEHOLDER in negative:
            errors.append(prefix + "negative_prompt尚未注入")
        if "禁止" in negative or "无需" in negative:
            errors.append(prefix + "negative_prompt含命令式歧义词")

        control = shot.get("generation_control")
        if not isinstance(control, dict):
            errors.append(prefix + "generation_control缺失")
        else:
            mode = control.get("mode")
            assets = control.get("reference_assets")
            if mode not in ("t2v", "i2v", "r2v"):
                errors.append(prefix + "generation mode非法")
            if not isinstance(control.get("audio_enabled"), bool):
                errors.append(prefix + "audio_enabled必须是布尔值")
            if not isinstance(assets, list):
                errors.append(prefix + "reference_assets必须是数组")
            elif mode in ("i2v", "r2v") and not assets:
                errors.append(prefix + f"{mode}缺少参考资产")
            if mode == "t2v" and visible:
                warnings.append(prefix + "人物镜使用T2V，角色一致性抽卡风险高于I2V/R2V")
        audio_enabled = control.get("audio_enabled") if isinstance(control, dict) else None
        for issue in dialogue_event_issues(
            metadata,
            director_item.get("dialogue_events", []),
            visible,
            full_prompt,
            audio_enabled,
            shot.get("duration", 0),
        ):
            errors.append(prefix + issue)

    for (previous_id, previous_metadata), (current_id, current_metadata) in zip(fight_records, fight_records[1:]):
        for issue in fight_transition_issues(previous_metadata, current_metadata):
            errors.append(f"{previous_id}→{current_id}: {issue}")

    for warning in warnings[:30]:
        print("[WARN] " + warning)
    if errors:
        print(f"[MODEC V4] FAIL - {len(errors)} error(s), {len(warnings)} warning(s)")
        for error in errors[:80]:
            print("  - " + error)
        return 1
    print(f"[MODEC V4] PASS - {len(shots)} shots, {len(warnings)} warning(s)")
    return 0


def _first_existing(run_dir, candidates):
    for relative in candidates:
        path = os.path.join(run_dir, relative)
        if os.path.exists(path):
            return path
    return os.path.join(run_dir, candidates[0])


def _load_json(path):
    if not os.path.exists(path):
        raise SystemExit("Missing required file: %s" % path)
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _load_optional_json(path):
    return _load_json(path) if os.path.exists(path) else {"items": []}


def _as_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[;；,，、/]+", value) if part.strip()]
    return []


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: validate_modec.py <run_dir>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
