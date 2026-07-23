#!/usr/bin/env python3
"""Validate Phase 6 Composer batches against the current contract."""

import json
import hashlib
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
    coverage_role_issues,
    continuity_contract_issues,
    dialogue_event_issues,
    expectation_anchor_issues,
    fight_continuity_issues,
    fight_transition_issues,
    listener_reaction_issues,
    performance_causality_issues,
    performance_contract_issues,
    prompt_length_profile,
    prompt_length_issues,
    prompt_soft_range,
    reroll_control_issues,
    role_partition_issues,
    shot_group_handoff_issues,
    jimeng_shot_group_issues,
    split_sections,
    timeline_issues,
    temporal_transition_contract_issues,
    visibility_issues,
)
from negative_prompts import PLACEHOLDER, is_fight_context
from shot_semantics import quality_contract as derive_quality_contract


FORBIDDEN_ENGINES = ["C4D", "Octane", "Blender", "Redshift", "Arnold", "Unreal Engine"]
DIRECT_TO_CAMERA_PATTERNS = [
    r"面向镜头", r"面对镜头", r"朝向镜头", r"正对镜头", r"看向镜头", r"直视镜头", r"盯着镜头",
]
DIRECT_TO_CAMERA_AUTH_PATTERNS = [
    r"原文明确.*(?:面向|面对|看向|直视|正对).*镜头",
    r"(?:自拍|自拍视频|直播|对观众|对屏幕观众|镜头内设备|面向观众|直视观众)",
]


def validate_composer_output(path, run_dir=None, report_path=None):
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    issues = []
    length_guidance = []
    if set(data.keys()) != {"shots"}:
        issues.append("batch顶层必须且只能包含shots")
    shots = data.get("shots", [])
    if not isinstance(shots, list) or not shots:
        issues.append("shots必须是非空数组")

    plan_map, director_map = _load_context(run_dir)
    main_plan = _load_main_plan(run_dir)
    project_config = _load_project_config(run_dir)
    hard_max_chars = (project_config.get("prompt_limits", {}) or {}).get("hard_max_chars")
    scaffold_map = _load_scaffold_for_batch(path, run_dir)
    seen = set()
    fight_records = []
    for shot in shots if isinstance(shots, list) else []:
        sid = shot.get("subshot_id", "?")
        prefix = f"{sid}: "
        if "duration_sec" in shot:
            issues.append(prefix + "duration_sec已废弃，只允许使用duration")
        if sid in seen:
            issues.append(prefix + "subshot_id重复")
        seen.add(sid)
        for field in (
            "shot_id", "subshot_id", "duration", "full_prompt", "negative_prompt",
            "qa_metadata", "generation_control",
        ):
            if field not in shot:
                issues.append(prefix + f"缺少字段{field}")

        full_prompt = str(shot.get("full_prompt", "") or "")
        metadata = shot.get("qa_metadata", {})
        metadata = metadata if isinstance(metadata, dict) else {}
        sections = split_sections(full_prompt, PROMPT_LABELS)
        for label in PROMPT_LABELS:
            count = len(re.findall(rf"(?:^|\n\n){re.escape(label)}[：:]", full_prompt))
            if count != 1:
                issues.append(prefix + f"字段{label}出现{count}次，必须恰好1次")
            elif not sections.get(label, "").strip():
                issues.append(prefix + f"字段{label}内容为空")
        if full_prompt.count("\n\n") != 4:
            issues.append(prefix + "五个即梦模型段落之间必须各有一个空行")
        for obsolete_label in LEGACY_LABELS:
            if re.search(rf"(?:^|\n\n){re.escape(obsolete_label)}[：:]", full_prompt):
                issues.append(prefix + f"旧结构字段泄漏：{obsolete_label}")
        for term in FORBIDDEN_MODEL_TERMS:
            if term in full_prompt:
                issues.append(prefix + f"工程/审核文本泄漏：{term}")
        for engine in FORBIDDEN_ENGINES:
            if engine in full_prompt:
                issues.append(prefix + f"禁用渲染引擎名：{engine}")
        if "负面提示词" in full_prompt or PLACEHOLDER in full_prompt:
            issues.append(prefix + "负面词必须位于negative_prompt字段，不能进入full_prompt")
        if shot.get("negative_prompt") != PLACEHOLDER:
            issues.append(prefix + f"Composer阶段negative_prompt必须精确等于{PLACEHOLDER}")

        duration = shot.get("duration", 0)
        for problem in prompt_length_issues(full_prompt, duration, hard_max_chars):
            issues.append(prefix + problem)
        profile = prompt_length_profile(metadata, duration)
        soft_min, soft_max = prompt_soft_range(duration, profile)
        if len(full_prompt) < soft_min or len(full_prompt) > soft_max:
            length_guidance.append(
                "%s: %d字，%s软区间%d-%d；只诊断信息密度，不自动填充或拆镜"
                % (sid, len(full_prompt), profile, soft_min, soft_max)
            )
        for problem in timeline_issues(full_prompt, duration):
            issues.append(prefix + problem)
        for problem in jimeng_shot_group_issues(full_prompt, metadata.get("editorial_mode", "continuous_take")):
            issues.append(prefix + problem)
        for problem in camera_competition_issues(full_prompt, metadata.get("editorial_mode", shot.get("editorial_mode", "continuous_take"))):
            issues.append(prefix + problem)
        for problem in coverage_role_issues(metadata, full_prompt):
            issues.append(prefix + problem)

        source_ids = shot.get("source_subshot_ids", [])
        if isinstance(source_ids, list) and source_ids:
            plan_item = _aggregate_context(plan_map, source_ids)
            director_item = _aggregate_context(director_map, source_ids)
            expected_sources = main_plan.get(str(shot.get("shot_id", "")), [])
            if expected_sources and source_ids != expected_sources:
                issues.append(prefix + "source_subshot_ids必须与主镜头计划一致")
        else:
            plan_item = plan_map.get(sid, {})
            director_item = director_map.get(sid, {})
        visible = _as_char_list(
            plan_item.get("visible_characters", plan_item.get("characters", director_item.get("visible_characters", [])))
        )
        _validate_scaffold_lock(prefix, shot, scaffold_map.get(sid), issues)
        expected_transition = ((scaffold_map.get(sid) or {}).get("qa_metadata", {}) or {}).get("temporal_transition_contract", {})
        for problem in temporal_transition_contract_issues(metadata, full_prompt, duration, expected_transition):
            issues.append(prefix + problem)
        _validate_quality_contract(prefix, metadata, plan_item, director_item, full_prompt, issues)
        _validate_scene_light_authority(prefix, director_item, full_prompt, issues)
        for problem in role_partition_issues(metadata, visible):
            issues.append(prefix + problem)
        for problem in performance_causality_issues(metadata, visible):
            issues.append(prefix + problem)
        for problem in performance_contract_issues(metadata, full_prompt, visible):
            issues.append(prefix + problem)
        for problem in listener_reaction_issues(metadata, full_prompt):
            issues.append(prefix + problem)
        for problem in expectation_anchor_issues(metadata, full_prompt):
            issues.append(prefix + problem)
        for problem in continuity_contract_issues(metadata, full_prompt, visible):
            issues.append(prefix + problem)
        for problem in reroll_control_issues(metadata, shot.get("generation_control"), visible):
            issues.append(prefix + problem)
        fight = is_fight_context(
            plan_item.get("scene_type", ""), plan_item.get("shot_type", ""), full_prompt
        )
        for problem in action_budget_issues(metadata, duration, fight):
            issues.append(prefix + problem)
        for problem in attention_handoff_issues(metadata, full_prompt):
            issues.append(prefix + problem)
        for problem in shot_group_handoff_issues(metadata):
            issues.append(prefix + problem)
        if fight:
            for problem in fight_continuity_issues(metadata, duration):
                issues.append(prefix + problem)
            fight_records.append((sid, metadata))
        shot_size = director_item.get("shot_size", plan_item.get("shot_size", ""))
        for problem in visibility_issues(full_prompt, shot_size):
            issues.append(prefix + problem)

        control = shot.get("generation_control")
        audio_enabled = control.get("audio_enabled") if isinstance(control, dict) else None
        for problem in dialogue_event_issues(
            metadata,
            director_item.get("dialogue_events", []),
            visible,
            full_prompt,
            audio_enabled,
            duration,
        ):
            issues.append(prefix + problem)
        _validate_metadata(prefix, metadata, director_item, full_prompt, audio_enabled, issues)
        _validate_generation_control(prefix, control, issues)

        if _has_direct_to_camera_text(full_prompt) and not _director_authorizes_direct_to_camera(director_item):
            issues.append(prefix + "原文未授权角色直视镜头")

    for (previous_id, previous_metadata), (current_id, current_metadata) in zip(fight_records, fight_records[1:]):
        for problem in fight_transition_issues(previous_metadata, current_metadata):
            issues.append(f"{previous_id}→{current_id}: {problem}")

    expected = set(main_plan) if main_plan else (set(plan_map) if plan_map else set())
    if expected and seen != expected and len(expected) == len(shots):
        missing = sorted(expected - seen)
        extra = sorted(seen - expected)
        if missing:
            issues.append("batch缺少subshot：" + "、".join(missing))
        if extra:
            issues.append("batch含未派发subshot：" + "、".join(extra))

    if issues:
        _write_report(report_path, path, issues)
        print(f"[VALIDATE COMPOSER] {len(issues)} issue(s):")
        for issue in issues[:80]:
            print("  - " + issue)
        for note in length_guidance[:20]:
            print("  [LENGTH GUIDANCE] " + note)
        return 1
    _write_report(report_path, path, [])
    print(f"[VALIDATE COMPOSER] PASS - {len(shots)} shots")
    for note in length_guidance[:20]:
        print("  [LENGTH GUIDANCE] " + note)
    return 0


def _load_main_plan(run_dir):
    if not run_dir:
        return {}
    path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return {str(shot.get("shot_id", "")): [str(sub.get("subshot_id", "")) for sub in shot.get("subshots", [])]
            for shot in data.get("shots", []) if isinstance(shot, dict) and shot.get("shot_id")}


def _aggregate_context(index, source_ids):
    """Use subshot facts for semantic QA while preserving main-shot identity."""
    values = [index.get(str(identifier), {}) for identifier in source_ids]
    values = [value for value in values if isinstance(value, dict)]
    if not values:
        return {}
    result = dict(values[0])
    result["visible_characters"] = list(dict.fromkeys(
        character for value in values for character in _as_char_list(value.get("visible_characters", value.get("characters", [])))
    ))
    result["dialogue_events"] = [event for value in values for event in value.get("dialogue_events", []) if isinstance(event, dict)]
    result["lighting"] = "；".join(str(value.get("lighting", "") or "") for value in values if value.get("lighting"))
    return result


def _validate_scaffold_lock(prefix, shot, scaffold, issues):
    if not scaffold:
        return
    for field in ("shot_id", "subshot_id", "duration", "negative_prompt", "generation_control"):
        if shot.get(field) != scaffold.get(field):
            issues.append(prefix + f"确定性骨架锁定字段被改写：{field}")
    metadata = shot.get("qa_metadata", {}) if isinstance(shot.get("qa_metadata"), dict) else {}
    expected_metadata = scaffold.get("qa_metadata", {})
    if metadata.get("dialogue_refs") != expected_metadata.get("dialogue_refs"):
        issues.append(prefix + "确定性骨架锁定字段被改写：qa_metadata.dialogue_refs")
    for field in (
        "editorial_mode", "camera_beat_map", "sequence_context", "quality_contract",
        "dramatic_design", "duration_design", "viewpoint", "visual_hierarchy",
        "entry_strategy", "reveal_strategy", "focus_strategy",
    ):
        if metadata.get(field) != expected_metadata.get(field):
            issues.append(prefix + f"确定性骨架锁定字段被改写：qa_metadata.{field}")
    locked = lambda events: [
        tuple(str(event.get(field, "") or "") for field in ("ref", "kind", "speaker", "text"))
        for event in events if isinstance(event, dict)
    ]
    if locked(metadata.get("dialogue_events", [])) != locked(expected_metadata.get("dialogue_events", [])):
        issues.append(prefix + "确定性骨架锁定字段被改写：qa_metadata.dialogue_events[].ref/kind/speaker/text")


def _load_scaffold_for_batch(batch_path, run_dir):
    if not run_dir:
        return {}
    dispatch_dir = os.path.join(run_dir, ".cache", "dispatch")
    if not os.path.isdir(dispatch_dir):
        return {}
    target = os.path.abspath(batch_path)
    for name in os.listdir(dispatch_dir):
        if not name.endswith("_packet.json"):
            continue
        packet_path = os.path.join(dispatch_dir, name)
        try:
            with open(packet_path, "r", encoding="utf-8-sig") as handle:
                packet = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if os.path.abspath(str(packet.get("_batch_output_path", ""))) != target:
            continue
        scaffold_path = packet.get("composer_scaffold_path")
        if not scaffold_path or not os.path.exists(scaffold_path):
            return {}
        with open(scaffold_path, "r", encoding="utf-8-sig") as handle:
            scaffold = json.load(handle)
        return {
            item.get("subshot_id", ""): item
            for item in scaffold.get("shots", []) if item.get("subshot_id")
        }
    return {}


def _write_report(report_path, batch_path, issues):
    if not report_path:
        return
    failed = []
    for issue in issues:
        prefix = str(issue).split(":", 1)[0]
        ids = prefix.split("→") if "→" in prefix else [prefix]
        for subshot_id in ids:
            if re.match(r"^[A-Za-z0-9_-]+$", subshot_id) and subshot_id not in failed:
                failed.append(subshot_id)
    os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump({
            "contract_version": "jimeng-t2v-v1",
            "batch_path": os.path.abspath(batch_path),
            "batch_sha256": _sha256(batch_path),
            "pass": not issues,
            "failed_subshot_ids": failed,
            "issues": issues,
        }, handle, ensure_ascii=False, indent=2)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_metadata(prefix, metadata, director_item, full_prompt, audio_enabled, issues):
    if not isinstance(metadata, dict):
        issues.append(prefix + "qa_metadata必须是对象")
        return
    for field in (
        "dramatic_goal", "performance_priority", "action_budget", "start_state", "end_state",
        "performance_contract", "continuity_contract", "reroll_control", "dialogue_refs", "dialogue_events",
        "editorial_mode", "camera_beat_map", "sequence_context", "quality_contract",
        "dramatic_design", "duration_design", "viewpoint", "visual_hierarchy",
        "entry_strategy", "reveal_strategy", "focus_strategy",
        "temporal_transition_contract",
    ):
        if field not in metadata:
            issues.append(prefix + f"qa_metadata缺少{field}")
    if len(str(metadata.get("dramatic_goal", "")).strip()) < 6:
        issues.append(prefix + "dramatic_goal必须是本镜具体目标")
    if len(str(metadata.get("start_state", "")).strip()) < 4:
        issues.append(prefix + "start_state过于空泛")
    if len(str(metadata.get("end_state", "")).strip()) < 4:
        issues.append(prefix + "end_state过于空泛")
    if metadata.get("editorial_mode") not in ("continuous_take", "shot_group"):
        issues.append(prefix + "editorial_mode只允许continuous_take/shot_group")
    if not isinstance(metadata.get("camera_beat_map"), list):
        issues.append(prefix + "camera_beat_map必须是数组")
    if not isinstance(metadata.get("sequence_context"), dict):
        issues.append(prefix + "sequence_context必须是对象")
    dramatic = metadata.get("dramatic_design")
    if not isinstance(dramatic, dict):
        issues.append(prefix + "dramatic_design必须是对象")
    else:
        if dramatic.get("narrative_weight") not in ("low", "medium", "high", "critical"):
            issues.append(prefix + "dramatic_design.narrative_weight无效")
        for field in ("shot_function", "information_gain"):
            if not str(dramatic.get(field, "") or "").strip():
                issues.append(prefix + "dramatic_design.%s不能为空" % field)
        if not isinstance(dramatic.get("dramatic_beat_ids"), list) or not dramatic.get("dramatic_beat_ids"):
            issues.append(prefix + "dramatic_design.dramatic_beat_ids必须是非空数组")
        punctuation = dramatic.get("visual_punctuation")
        if not isinstance(punctuation, list):
            issues.append(prefix + "dramatic_design.visual_punctuation必须是数组")
    duration_design = metadata.get("duration_design")
    if not isinstance(duration_design, dict):
        issues.append(prefix + "duration_design必须是对象")
    else:
        if duration_design.get("duration_strategy") != "pack_toward_limit":
            issues.append(prefix + "duration_design.duration_strategy必须是pack_toward_limit")
        if not isinstance(duration_design.get("justified_content_duration"), (int, float)):
            issues.append(prefix + "duration_design.justified_content_duration必须是数字")
        if not isinstance(duration_design.get("utilization_ratio"), (int, float)):
            issues.append(prefix + "duration_design.utilization_ratio必须是数字")
        if not isinstance(duration_design.get("dramatic_beats"), list) or not duration_design.get("dramatic_beats"):
            issues.append(prefix + "duration_design.dramatic_beats必须是非空数组")
        if isinstance(dramatic, dict) and duration_design.get("dramatic_beats") != dramatic.get("dramatic_beat_ids"):
            issues.append(prefix + "duration_design与dramatic_design节拍ID不一致")
    allowed_design = {
        "viewpoint": ("observer", "participant", "authority", "vulnerable", "objective"),
        "entry_strategy": ("none", "enter_frame", "camera_follow", "occlusion_reveal", "reaction_first"),
        "reveal_strategy": ("direct", "progressive", "delayed", "reaction_then_subject"),
        "focus_strategy": ("single_plane", "deep_focus", "rack_focus", "single_reframe", "actor_blocking"),
    }
    for field, allowed in allowed_design.items():
        if metadata.get(field) not in allowed:
            issues.append(prefix + "%s无效" % field)
    if not str(metadata.get("visual_hierarchy", "") or "").strip():
        issues.append(prefix + "visual_hierarchy不能为空")
    if isinstance(dramatic, dict) and dramatic.get("shot_function") == "entrance" and dramatic.get("narrative_weight") in ("high", "critical"):
        punctuation = dramatic.get("visual_punctuation", [])
        allowed_punctuation = {
            "occlusion_reveal", "low_angle_scale", "foreground_reaction",
            "camera_follow", "light_reveal", "stop_mark", "rack_focus",
        }
        if not isinstance(punctuation, list) or not 1 <= len(punctuation) <= 2:
            issues.append(prefix + "重要出场必须选择1-2个有动机视觉标点")
        elif len(set(punctuation)) != len(punctuation) or any(item not in allowed_punctuation for item in punctuation):
            issues.append(prefix + "重要出场visual_punctuation含重复或非法项")
        else:
            _validate_entrance_punctuation(prefix, punctuation, metadata, full_prompt, issues)
    contract = metadata.get("quality_contract")
    if not isinstance(contract, dict):
        issues.append(prefix + "quality_contract必须是对象")
    elif contract.get("profile") not in ("environment", "object", "action", "dialogue", "dramatic"):
        issues.append(prefix + "quality_contract.profile无效")
    elif not isinstance(contract.get("required_evidence"), list) or not contract.get("required_evidence"):
        issues.append(prefix + "quality_contract.required_evidence必须是非空数组")
    evidence = metadata.get("quality_evidence")
    if not isinstance(evidence, dict):
        issues.append(prefix + "quality_evidence必须将每项质量证据映射到提示词段落")
    refs = metadata.get("dialogue_refs", [])
    if not isinstance(refs, list):
        issues.append(prefix + "dialogue_refs必须是数组")
        refs = []
    expected_refs = director_item.get("dialogue_refs", [])
    if isinstance(expected_refs, list) and set(refs) != set(expected_refs):
        issues.append(prefix + "dialogue_refs与Director不一致")
    raw = str(director_item.get("dialogue_raw_text", "") or "").strip()
    if not raw and re.search(r"[“\"]([^”\"]{2,})[”\"]", full_prompt):
        issues.append(prefix + "无原始台词镜头疑似新增引号台词")


def _validate_quality_contract(prefix, metadata, plan_item, director_item, full_prompt, issues):
    """Reject profile spoofing and require every quality demand to reach a prompt section."""
    source = plan_item or director_item
    if not source:
        return
    expected = derive_quality_contract(source)
    actual = metadata.get("quality_contract")
    if actual != expected:
        issues.append(prefix + "quality_contract必须由源子镜重新推导，不能伪造或删减")
        return
    evidence = metadata.get("quality_evidence")
    if not isinstance(evidence, dict):
        return
    sections = split_sections(full_prompt, PROMPT_LABELS)
    allowed = set(PROMPT_LABELS)
    for requirement in expected["required_evidence"]:
        mapped = evidence.get(requirement)
        if not isinstance(mapped, dict):
            issues.append(prefix + "quality_evidence.%s必须提供section和可追溯fragment" % requirement)
            continue
        section = mapped.get("section")
        fragment = str(mapped.get("fragment", "") or "").strip()
        if section not in allowed or len(fragment) < 3 or fragment not in sections.get(section, ""):
            issues.append(prefix + "quality_evidence未将%s以真实fragment落实到提示词段落" % requirement)


def _validate_generation_control(prefix, control, issues):
    if not isinstance(control, dict):
        issues.append(prefix + "generation_control必须是对象")
        return
    mode = control.get("mode")
    if mode != "t2v":
        issues.append(prefix + "generation_control.mode必须固定为t2v")
    if not isinstance(control.get("audio_enabled"), bool):
        issues.append(prefix + "generation_control.audio_enabled必须是布尔值")
    if "reference_assets" in control:
        issues.append(prefix + "T2V-only契约禁止generation_control.reference_assets")


def _validate_scene_light_authority(prefix, director_item, full_prompt, issues):
    """Keep numeric light facts owned by Scene through the Director packet."""
    expected = set(re.findall(r"\b\d{4}K\b", str(director_item.get("lighting", "") or "")))
    actual = set(re.findall(r"\b\d{4}K\b", str(full_prompt or "")))
    invented = sorted(actual - expected)
    if invented:
        issues.append(prefix + "Composer发明Scene未提供的色温：" + "/".join(invented))
    if expected and not actual:
        issues.append(prefix + "光照与声音缺少Scene锁定色温：" + "/".join(sorted(expected)))


def _validate_entrance_punctuation(prefix, punctuation, metadata, full_prompt, issues):
    checks = {
        "occlusion_reveal": metadata.get("entry_strategy") == "occlusion_reveal",
        "foreground_reaction": metadata.get("entry_strategy") == "reaction_first",
        "camera_follow": (
            metadata.get("entry_strategy") == "camera_follow"
            and bool(re.search(r"跟拍|摄影机跟随|镜头跟随", full_prompt))
        ),
        "rack_focus": metadata.get("focus_strategy") == "rack_focus",
        "low_angle_scale": (
            metadata.get("viewpoint") == "authority"
            and bool(re.search(r"低机位|微仰|仰拍", full_prompt))
        ),
        "light_reveal": (
            metadata.get("reveal_strategy") in ("progressive", "delayed")
            and bool(re.search(r"由暗到明|进入光区|光线.{0,8}揭示|轮廓光.{0,8}面光", full_prompt))
        ),
        "stop_mark": bool(re.search(r"停步|顿住|站定|停在", full_prompt)),
    }
    for item in punctuation:
        if not checks.get(item, False):
            issues.append(prefix + "重要出场视觉标点未落实到策略/提示词：" + item)


def _load_context(run_dir):
    if not run_dir:
        return {}, {}
    plan_map = {}
    director_map = {}
    plan_path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")
    if os.path.exists(plan_path):
        with open(plan_path, "r", encoding="utf-8-sig") as handle:
            plan = json.load(handle)
        for shot in plan.get("shots", []):
            for subshot in shot.get("subshots", []):
                copied = dict(subshot)
                copied.setdefault("scene_type", shot.get("scene_type", ""))
                plan_map[copied.get("subshot_id", "")] = copied
    return plan_map, director_map


def _load_project_config(run_dir):
    if not run_dir:
        return {}
    path = os.path.join(run_dir, "project_config.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    return value if isinstance(value, dict) else {}


def _as_char_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[;；,，、/]+", value) if part.strip()]
    return []


def _has_direct_to_camera_text(text):
    return any(re.search(pattern, str(text or "")) for pattern in DIRECT_TO_CAMERA_PATTERNS)


def _director_authorizes_direct_to_camera(item):
    blob = "\n".join(str(item.get(key, "")) for key in (
        "character_action", "axis_space", "axis_start", "axis_end", "camera_facing_desc",
        "dialogue_audio", "base_action",
    ))
    return any(re.search(pattern, blob) for pattern in DIRECT_TO_CAMERA_AUTH_PATTERNS)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: validate_composer_output.py <composer_output.json> [--run-dir <run_dir>]")
        sys.exit(2)
    run_dir = None
    report_path = None
    args = []
    index = 1
    while index < len(sys.argv):
        if sys.argv[index] == "--run-dir" and index + 1 < len(sys.argv):
            run_dir = sys.argv[index + 1]
            index += 2
        elif sys.argv[index] == "--report" and index + 1 < len(sys.argv):
            report_path = sys.argv[index + 1]
            index += 2
        else:
            args.append(sys.argv[index])
            index += 1
    sys.exit(validate_composer_output(args[0], run_dir, report_path))
