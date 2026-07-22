#!/usr/bin/env python3
"""Thirty-point Mode C v4 package/export quality gate."""

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
    continuity_contract_issues,
    dialogue_event_issues,
    fight_continuity_issues,
    fight_transition_issues,
    performance_causality_issues,
    performance_contract_issues,
    prompt_length_issues,
    reroll_control_issues,
    role_partition_issues,
    split_sections,
    timeline_issues,
    timeline_ranges,
    visibility_issues,
)
from negative_prompts import PLACEHOLDER, is_fight_context


FORBIDDEN_ENGINES = ["C4D", "Octane", "Blender", "Redshift", "Arnold", "Unreal Engine"]


def check_export(md_path, run_dir, quality_mode=False):
    plan = _load(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"))
    config = _load_optional(os.path.join(run_dir, "project_config.json"))
    package_path = _find_package(run_dir)
    package = _load(package_path) if package_path else {}
    director = _load_optional(os.path.join(run_dir, ".cache", "director", "director_pass.json"))
    llm_review = _load_optional(os.path.join(run_dir, ".cache", "review", "llm_gate_result.json"))
    scene = _load_optional(os.path.join(run_dir, ".cache", "analysis", "scene_output.json"))
    grid_packages = _load_optional(os.path.join(run_dir, ".cache", "grid_storyboard", "packages.json"))
    shots = package.get("shots", [])
    items = package.get("items", [])
    plan_map, scene_by_id = _plan_index(plan)
    director_map = {item.get("subshot_id", ""): item for item in director.get("items", [])}
    scene_map = {item.get("subshot_id", ""): item for item in scene.get("items", [])}
    failures = []

    def check(number, label, condition, detail=""):
        print(f"  [{'OK' if condition else '!!'}] {number:02d}. {label}: {detail or ('OK' if condition else 'FAIL')}")
        if not condition:
            failures.append(f"{label}: {detail}")

    required = {
        "shot_id", "subshot_id", "duration", "full_prompt", "negative_prompt",
        "qa_metadata", "generation_control",
    }
    ids = [shot.get("subshot_id", "") for shot in shots if isinstance(shot, dict)]
    expected_ids = set(plan_map)

    check(1, "Package exists", bool(package_path), package_path or "missing")
    check(2, "Mode C v4 contract", package.get("contract_version") == "modec-v4", str(package.get("contract_version")))
    check(3, "Items/shots identical", items == shots and isinstance(shots, list), f"{len(items)}/{len(shots)}")
    check(4, "Subshot coverage", set(ids) == expected_ids, f"{len(set(ids))}/{len(expected_ids)}")
    check(5, "Unique subshots", len(ids) == len(set(ids)), f"{len(ids) - len(set(ids))} duplicate(s)")
    missing_fields = sum(1 for shot in shots if not required.issubset(shot))
    check(6, "Required shot fields", missing_fields == 0, f"{missing_fields} incomplete")
    bad_duration = sum(1 for shot in shots if not isinstance(shot.get("duration"), (int, float)) or shot.get("duration", 0) <= 0)
    check(7, "Positive durations", bad_duration == 0, f"{bad_duration} invalid")

    bad_sections = 0
    bad_spacing = 0
    legacy_hits = 0
    pollution = 0
    length_issues = 0
    timeline_missing = 0
    timeline_coverage = 0
    timeline_overload = 0
    negative_missing = 0
    negative_ambiguous = 0
    metadata_missing = 0
    performance_causality_errors = 0
    performance_contract_errors = 0
    continuity_contract_errors = 0
    reroll_control_errors = 0
    role_issues = 0
    primary_issues = 0
    budget_issues = 0
    camera_budget_issues = 0
    visible_detail_issues = 0
    dialogue_issues = 0
    mode_issues = 0
    asset_issues = 0
    audio_issues = 0
    eyeline_issues = 0
    engine_issues = 0
    fight_continuity_errors = 0
    fight_records = []

    for shot in shots:
        sid = shot.get("subshot_id", "")
        full_prompt = str(shot.get("full_prompt", "") or "")
        sections = split_sections(full_prompt, PROMPT_LABELS)
        if list(sections) != PROMPT_LABELS or any(not sections.get(label) for label in PROMPT_LABELS):
            bad_sections += 1
        if full_prompt.count("\n\n") != 3:
            bad_spacing += 1
        if any(re.search(rf"(?:^|\n\n){re.escape(label)}[：:]", full_prompt) for label in LEGACY_LABELS):
            legacy_hits += 1
        if any(term in full_prompt for term in FORBIDDEN_MODEL_TERMS) or "负面提示词" in full_prompt or PLACEHOLDER in full_prompt:
            pollution += 1
        if prompt_length_issues(full_prompt, shot.get("duration", 0)):
            length_issues += 1
        t_issues = timeline_issues(full_prompt, shot.get("duration", 0))
        if any("缺少" in issue for issue in t_issues):
            timeline_missing += 1
        if any(word in issue for issue in t_issues for word in ("断档", "重叠", "倒置", "不一致", "开始")):
            timeline_coverage += 1
        if len(timeline_ranges(full_prompt)) > 3:
            timeline_overload += 1

        negative = str(shot.get("negative_prompt", "") or "").strip()
        if not negative or PLACEHOLDER in negative:
            negative_missing += 1
        if "禁止" in negative or "无需" in negative:
            negative_ambiguous += 1

        metadata = shot.get("qa_metadata")
        if not isinstance(metadata, dict) or any(key not in metadata for key in (
            "dramatic_goal", "performance_priority", "action_budget", "start_state", "end_state",
            "performance_contract", "continuity_contract", "reroll_control", "dialogue_refs", "dialogue_events"
        )):
            metadata_missing += 1
            metadata = metadata if isinstance(metadata, dict) else {}
        plan_item = plan_map.get(sid, {})
        visible = _as_list(plan_item.get("visible_characters", plan_item.get("characters", [])))
        role_errors = role_partition_issues(metadata, visible)
        if role_errors:
            role_issues += 1
        if performance_causality_issues(metadata, visible):
            performance_causality_errors += 1
        if performance_contract_issues(metadata, full_prompt, visible):
            performance_contract_errors += 1
        if continuity_contract_issues(metadata, full_prompt, visible):
            continuity_contract_errors += 1
        if reroll_control_issues(metadata, shot.get("generation_control"), visible):
            reroll_control_errors += 1
        roles = metadata.get("performance_priority", {}) if isinstance(metadata, dict) else {}
        if visible and (not isinstance(roles, dict) or not roles.get("primary")):
            primary_issues += 1
        fight = is_fight_context(plan_item.get("scene_type", ""), plan_item.get("shot_type", ""), full_prompt)
        b_issues = action_budget_issues(metadata, shot.get("duration", 0), fight)
        if b_issues:
            budget_issues += 1
        if fight:
            if fight_continuity_issues(metadata, shot.get("duration", 0)):
                fight_continuity_errors += 1
            fight_records.append((sid, metadata))
        budget = metadata.get("action_budget", {}) if isinstance(metadata, dict) else {}
        editorial_mode = metadata.get("editorial_mode", shot.get("editorial_mode", "continuous_take"))
        camera_errors = camera_competition_issues(full_prompt, editorial_mode) + attention_handoff_issues(metadata, full_prompt)
        if not isinstance(budget, dict) or budget.get("physical_camera_move_count") not in (0, 1) or camera_errors:
            camera_budget_issues += 1
        shot_size = director_map.get(sid, {}).get("shot_size", plan_item.get("shot_size", ""))
        if visibility_issues(full_prompt, shot_size):
            visible_detail_issues += 1

        refs = metadata.get("dialogue_refs", []) if isinstance(metadata, dict) else []
        expected_refs = director_map.get(sid, {}).get("dialogue_refs", plan_item.get("dialogue_refs", []))
        raw = str(director_map.get(sid, {}).get("dialogue_raw_text", plan_item.get("dialogue_raw_text", "")) or "").strip()
        if set(refs if isinstance(refs, list) else []) != set(expected_refs if isinstance(expected_refs, list) else []):
            dialogue_issues += 1
        elif raw:
            control = shot.get("generation_control", {})
            if isinstance(control, dict) and control.get("audio_enabled") is True and raw not in full_prompt:
                dialogue_issues += 1
            elif isinstance(control, dict) and control.get("audio_enabled") is False and raw in full_prompt:
                dialogue_issues += 1

        control = shot.get("generation_control")
        if not isinstance(control, dict) or control.get("mode") not in ("t2v", "i2v", "r2v"):
            mode_issues += 1
            control = control if isinstance(control, dict) else {}
        assets = control.get("reference_assets")
        if not isinstance(assets, list) or (control.get("mode") in ("i2v", "r2v") and not assets):
            asset_issues += 1
        elif isinstance(assets, list) and any(not isinstance(asset, dict) or not asset.get("type") or not asset.get("path") for asset in assets):
            asset_issues += 1
        if not isinstance(control.get("audio_enabled"), bool):
            audio_issues += 1
        dialogue_issues += len(dialogue_event_issues(
            metadata,
            director_map.get(sid, {}).get("dialogue_events", []),
            visible,
            full_prompt,
            control.get("audio_enabled"),
            shot.get("duration", 0),
        ))
        if _has_direct_to_camera(full_prompt) and not _direct_to_camera_authorized(director_map.get(sid, {})):
            eyeline_issues += 1
        if any(engine in full_prompt for engine in FORBIDDEN_ENGINES):
            engine_issues += 1

    for (_, previous_metadata), (_, current_metadata) in zip(fight_records, fight_records[1:]):
        fight_continuity_errors += len(fight_transition_issues(previous_metadata, current_metadata))

    check(8, "Four executable sections", bad_sections == 0, f"{bad_sections} bad")
    check(9, "Exact paragraph spacing", bad_spacing == 0, f"{bad_spacing} bad")
    check(10, "No v3 fields", legacy_hits == 0, f"{legacy_hits} leak(s)")
    check(11, "No model-prompt pollution", pollution == 0, f"{pollution} polluted")
    check(12, "Prompt length 120-1100", length_issues == 0, f"{length_issues} outside")
    check(13, "Timeline present", timeline_missing == 0, f"{timeline_missing} missing")
    check(14, "Timeline exact coverage", timeline_coverage == 0, f"{timeline_coverage} bad")
    check(15, "Timeline <=3 segments", timeline_overload == 0, f"{timeline_overload} overloaded")
    check(16, "Negative prompt injected separately", negative_missing == 0, f"{negative_missing} missing")
    check(17, "No ambiguous negative commands", negative_ambiguous == 0, f"{negative_ambiguous} ambiguous")
    check(
        18,
        "QA contracts complete",
        metadata_missing == 0 and performance_causality_errors == 0 and performance_contract_errors == 0 and continuity_contract_errors == 0 and reroll_control_errors == 0,
        f"metadata={metadata_missing}, causality={performance_causality_errors}, performance={performance_contract_errors}, continuity={continuity_contract_errors}, reroll={reroll_control_errors}",
    )
    check(19, "Role partition complete", role_issues == 0, f"{role_issues} bad")
    check(20, "Exactly one primary when visible", primary_issues == 0, f"{primary_issues} bad")
    check(21, "Action budget/fight continuity", budget_issues == 0 and fight_continuity_errors == 0, f"budget={budget_issues}, fight={fight_continuity_errors}")
    check(22, "Single camera move budget", camera_budget_issues == 0, f"{camera_budget_issues} bad")
    check(23, "Shot-size visibility", visible_detail_issues == 0, f"{visible_detail_issues} invisible-detail shot(s)")
    check(24, "Dialogue boundary", dialogue_issues == 0, f"{dialogue_issues} mismatch(es)")
    check(25, "Generation mode", mode_issues == 0, f"{mode_issues} invalid")
    check(26, "Reference assets", asset_issues == 0, f"{asset_issues} invalid")
    check(27, "Audio capability", audio_issues == 0, f"{audio_issues} invalid")
    check(28, "Story-correct eyeline", eyeline_issues == 0, f"{eyeline_issues} unauthorized")
    light_jumps = _light_jumps(plan, scene_by_id, scene_map)
    check(29, "Lighting continuity", light_jumps == 0, f"{light_jumps} unexplained jump(s)")
    grid_enabled = _grid_enabled(config)
    grid_expected = grid_enabled and bool(grid_packages.get("packages"))
    export_ok, export_detail = _export_check(md_path, quality_mode, expected_ids, grid_enabled, grid_expected)
    editor_ok, editor_detail = _editor_review_check(llm_review)
    check(30, "Export separation/readiness", export_ok and engine_issues == 0 and editor_ok, export_detail + f"; engines={engine_issues}; editor={editor_detail}")

    total = 30
    passed = total - len(failures)
    print(f"\n  RESULT: {passed}/{total} passed" + (f", {len(failures)} issues" if failures else " - ALL CLEAN"))
    if failures:
        print("  ISSUES:")
        for index, issue in enumerate(failures, 1):
            print(f"    {index}. {issue}")
    return passed, len(failures)


def _find_package(run_dir):
    for relative in (
        ".cache/composer/merged.prompt_package.json",
        ".cache/composer/prompt_package.json",
        ".cache/prompt_package.json",
    ):
        path = os.path.join(run_dir, relative)
        if os.path.exists(path):
            return path
    return ""


def _plan_index(plan):
    by_id = {}
    scene_by_id = {}
    for shot in plan.get("shots", []):
        for subshot in shot.get("subshots", []):
            copied = dict(subshot)
            copied.setdefault("scene_type", shot.get("scene_type", ""))
            by_id[copied.get("subshot_id", "")] = copied
            scene_by_id[copied.get("subshot_id", "")] = shot.get("scene", "")
    return by_id, scene_by_id


def _light_jumps(plan, scene_by_id, scene_map):
    ordered = [subshot.get("subshot_id", "") for shot in plan.get("shots", []) for subshot in shot.get("subshots", [])]
    jumps = 0
    for left, right in zip(ordered, ordered[1:]):
        if scene_by_id.get(left) != scene_by_id.get(right):
            continue
        t1 = scene_map.get(left, {}).get("light_temp")
        t2 = scene_map.get(right, {}).get("light_temp")
        if isinstance(t1, (int, float)) and isinstance(t2, (int, float)) and abs(t1 - t2) > 500:
            jumps += 1
    return jumps


def _export_check(md_path, quality_mode, expected_ids, grid_enabled=False, grid_expected=False):
    if quality_mode:
        return True, "quality mode"
    if not md_path or not os.path.exists(md_path):
        return False, "markdown missing"
    with open(md_path, "r", encoding="utf-8-sig") as handle:
        text = handle.read()
    ids_ok = all(subshot_id in text for subshot_id in expected_ids)
    required_sections = ("模型提示词", "负面提示词", "下一镜转场提示词", "台词/OS/OV表演")
    forbidden_sections = ("QA元数据", "qa_metadata", "生成控制", "generation_control")
    separated = all(label in text for label in required_sections) and not any(label in text for label in forbidden_sections)
    has_grid_section = "自动九宫格剧情包" in text
    grid_ok = has_grid_section == grid_expected if grid_enabled else not has_grid_section
    xlsx_path = os.path.splitext(md_path)[0] + ".xlsx"
    return ids_ok and separated and grid_ok and os.path.exists(xlsx_path), f"ids={ids_ok}, separated={separated}, grid={grid_ok}, xlsx={os.path.exists(xlsx_path)}"


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _load_optional(path):
    return _load(path) if os.path.exists(path) else {"items": []}


def _grid_enabled(config):
    grid = config.get("storyboard_grid", {}) if isinstance(config, dict) else {}
    return isinstance(grid, dict) and grid.get("enabled") is True


def _editor_review_check(llm_review):
    if not isinstance(llm_review, dict) or not llm_review or "items" in llm_review:
        return False, "missing llm review"
    if llm_review.get("pass") is not True:
        return False, "pass!=true"
    blocking = llm_review.get("blocking")
    if not isinstance(blocking, list) or blocking:
        return False, "blocking not empty"
    return True, "ok"


def _as_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[;；,，、/]+", value) if part.strip()]
    return []


def _has_direct_to_camera(text):
    return bool(re.search(r"(?:面向|面对|朝向|正对|看向|直视|盯着)镜头", str(text or "")))


def _direct_to_camera_authorized(item):
    blob = "\n".join(str(item.get(key, "")) for key in (
        "character_action", "axis_space", "camera_facing_desc", "dialogue_audio", "base_action",
    ))
    return bool(re.search(r"自拍|直播|对观众|直视观众|镜头内设备|原文明确.*镜头", blob))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--quality":
        passed, failed = check_export("", sys.argv[2], quality_mode=True)
        sys.exit(0 if failed == 0 else 1)
    if len(sys.argv) == 3:
        passed, failed = check_export(sys.argv[1], sys.argv[2], quality_mode=False)
        sys.exit(0 if failed == 0 else 1)
    print("Usage: python3 check_export.py <export_md> <run_dir>")
    print("       python3 check_export.py --quality <run_dir>")
    sys.exit(2)
