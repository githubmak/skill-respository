#!/usr/bin/env python3
"""Classify Composer findings into the smallest safe repair scope."""

import hashlib
import re

from creative_engineering_boundary import ENGINE, field_owner, repair_executor


SCOPE_ORDER = {"field": 0, "shot": 1, "pair": 2, "window": 3, "scene": 4}
ALL_MUTABLE_FIELDS = "__all_mutable__"

_SHOT_PREFIX = re.compile(r"^([^:]+):\s*(.*)$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")
_QA_PATH = re.compile(r"(qa_metadata(?:\.[A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?)+)")
_LOCKED_FIELD = re.compile(r"确定性骨架锁定字段被改写：([^；，,\s]+)")
_MISSING_SHOT_FIELD = re.compile(r"缺少字段([A-Za-z_][A-Za-z0-9_]*)")
_MISSING_QA_FIELD = re.compile(r"qa_metadata缺少([A-Za-z_][A-Za-z0-9_]*)")

_QA_CONTRACTS = (
    "source_constraint_basemap", "scene_tone_palette", "screen_text_policy",
    "prop_functional_surface_contract", "skin_tone_protection_contract",
    "prop_lifecycle_contract", "perspective_scale_contract",
    "lighting_topology_contract", "tension_curve_role", "story_punch_contract",
    "character_scene_objective_contract", "relationship_emotion_arc",
    "sequence_directing_plan", "cut_decision_contract",
    "prompt_information_budget", "sound_directing_plan", "performance_causality",
    "performance_contract", "listener_reaction_plan", "continuity_contract",
    "reroll_control", "dialogue_events", "dialogue_refs", "quality_contract",
    "quality_evidence", "duration_design", "dramatic_design", "emotion_driver",
    "camera_beat_map", "attention_handoff", "terminal_frame_contract",
    "visual_bible", "static_aesthetic_contract", "dynamic_aesthetic_contract",
    "aesthetic_priority", "video_texture_contract", "cinematic_image_contract",
)


def build_repair_report(issues, shots):
    """Return a structured repair report without changing validator severity."""
    shot_rows = [row for row in shots or [] if isinstance(row, dict)]
    known_ids = [
        str(row.get("subshot_id", "") or row.get("shot_id", "")).strip()
        for row in shot_rows
    ]
    known_ids = [value for value in known_ids if value]
    owner_by_id = {
        str(row.get("subshot_id", "") or row.get("shot_id", "")): str(
            row.get("shot_id", "") or row.get("subshot_id", "")
        )
        for row in shot_rows
    }
    failures = [classify_issue(issue, known_ids, owner_by_id) for issue in issues or []]
    global_failure = any(item["repair_scope"] == "scene" for item in failures)
    failed_ids = []
    for item in failures:
        affected = known_ids if item["repair_scope"] == "scene" else item["dependent_subshot_ids"]
        for subshot_id in affected:
            if subshot_id in known_ids and subshot_id not in failed_ids:
                failed_ids.append(subshot_id)

    targets = _aggregate_targets(failures, known_ids, owner_by_id, global_failure)
    highest = _highest_scope(item["repair_scope"] for item in failures) if failures else "field"
    return {
        "strategy_version": 1,
        "repair_scope": highest,
        "partial_reuse_safe": bool(failures) and not global_failure and 0 < len(failed_ids) < len(known_ids),
        "failed_subshot_ids": failed_ids,
        "failures": failures,
        "repair_targets": targets,
    }


def classify_issue(issue, known_ids, owner_by_id=None):
    text = str(issue or "").strip()
    owner_by_id = owner_by_id or {}
    prefix, message = _split_issue(text)
    ids = [part.strip() for part in prefix.split("→") if part.strip()] if prefix else []
    ids = [value for value in ids if value in set(known_ids)]
    if not ids:
        scope = "scene"
        fields = []
        code = "BATCH_CONTRACT"
    else:
        fields = infer_field_paths(message)
        scope = "pair" if len(ids) > 1 else ("field" if fields else "shot")
        code = _issue_code(message, scope, fields)
    owners = []
    for subshot_id in ids:
        owner = owner_by_id.get(subshot_id, subshot_id)
        if owner and owner not in owners:
            owners.append(owner)
    field_owners = {field: field_owner(field) for field in fields}
    executors = [repair_executor(field, code) for field in fields] or [repair_executor("", code)]
    executor = ENGINE if executors and all(value == ENGINE for value in executors) else "model"
    return {
        "code": code,
        "message": text,
        "shot_id": owners[0] if owners else "",
        "subshot_id": ids[0] if ids else "",
        "field_paths": fields,
        "field_owners": field_owners,
        "repair_executor": executor,
        "repair_scope": scope,
        "dependent_shot_ids": owners,
        "dependent_subshot_ids": ids,
        "failure_id": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
    }


def infer_field_paths(message):
    text = str(message or "")
    fields = []
    locked = _LOCKED_FIELD.search(text)
    if locked:
        fields.append(locked.group(1))
    missing = _MISSING_SHOT_FIELD.search(text)
    if missing:
        fields.append(missing.group(1))
    missing_qa = _MISSING_QA_FIELD.search(text)
    if missing_qa:
        fields.append("qa_metadata." + missing_qa.group(1))
    for path in _QA_PATH.findall(text):
        fields.append(path)
    for contract in _QA_CONTRACTS:
        if contract in text:
            fields.append("qa_metadata." + contract)
    if "generation_control" in text:
        fields.append("generation_control")
    if "negative_prompt" in text or "Composer阶段negative_prompt" in text:
        fields.append("negative_prompt")
    prompt_terms = (
        "full_prompt", "五个即梦模型段落", "字段生成规格", "字段主体与空间锁定",
        "字段主镜头连续规则", "字段子镜头组", "字段光照、声音与稳定约束",
        "提示词", "时间窗", "口型", "画幅", "横屏", "竖屏", "色温",
    )
    if any(term in text for term in prompt_terms):
        fields.append("full_prompt")
    if "dialogue" in text or any(term in text for term in ("台词", "OS", "OV", "系统音", "发声")):
        fields.append("qa_metadata.dialogue_events")
    return _dedupe(fields)


def _aggregate_targets(failures, known_ids, owner_by_id, global_failure):
    by_owner = {}
    for failure in failures:
        affected = known_ids if global_failure and failure["repair_scope"] == "scene" else failure["dependent_subshot_ids"]
        for subshot_id in affected:
            owner = owner_by_id.get(subshot_id, subshot_id)
            target = by_owner.setdefault(owner, {
                "shot_id": owner,
                "subshot_ids": [],
                "fields": [],
                "repair_scope": failure["repair_scope"],
                "dependent_shot_ids": [],
                "codes": [],
                "reasons": [],
                "repair_executor": failure.get("repair_executor", "model"),
                "field_owners": {},
            })
            if subshot_id not in target["subshot_ids"]:
                target["subshot_ids"].append(subshot_id)
            target["fields"] = _dedupe(target["fields"] + failure["field_paths"])
            target["repair_scope"] = _highest_scope((target["repair_scope"], failure["repair_scope"]))
            target["dependent_shot_ids"] = _dedupe(
                target["dependent_shot_ids"] + failure["dependent_shot_ids"]
            )
            if failure["code"] not in target["codes"]:
                target["codes"].append(failure["code"])
            if failure["message"] not in target["reasons"]:
                target["reasons"].append(failure["message"])
            target["field_owners"].update(failure.get("field_owners", {}))
            if failure.get("repair_executor") == "model":
                target["repair_executor"] = "model"
    for target in by_owner.values():
        if target["repair_scope"] != "field" and not target["fields"]:
            target["fields"] = [ALL_MUTABLE_FIELDS]
    return [by_owner[key] for key in sorted(by_owner)]


def _split_issue(text):
    match = _SHOT_PREFIX.match(text)
    if not match:
        return "", text
    prefix = match.group(1).strip()
    if all(_SAFE_ID.match(part.strip()) for part in prefix.split("→")):
        return prefix, match.group(2).strip()
    return "", text


def _highest_scope(scopes):
    values = [scope for scope in scopes if scope in SCOPE_ORDER]
    return max(values, key=lambda value: SCOPE_ORDER[value]) if values else "field"


def _issue_code(message, scope, fields):
    if scope == "pair":
        return "PAIR_CONTINUITY"
    if "确定性骨架锁定字段" in message:
        return "LOCKED_FIELD"
    if "缺少字段" in message or "qa_metadata缺少" in message:
        return "MISSING_FIELD"
    if any("dialogue_events" in field for field in fields):
        return "DIALOGUE_CONTRACT"
    if "full_prompt" in fields:
        return "PROMPT_CONTRACT"
    return "FIELD_CONTRACT" if fields else "SHOT_CONTRACT"


def _dedupe(values):
    result = []
    for value in values:
        value = str(value or "").strip()
        if value and value not in result:
            result.append(value)
    return result
