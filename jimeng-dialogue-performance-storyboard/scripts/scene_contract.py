#!/usr/bin/env python3
"""Validate compact internal scene contracts and prompt fact recovery."""

from __future__ import annotations

import argparse
import json
import re
from functools import reduce
from pathlib import Path

from validate_storyboard import (
    REFLECTIVE_OPTICAL_CUES,
    SHOT_SIZE_TERMS,
    camera_prop_motion_ownership_issues,
    direct_prompt,
    iter_children,
    iter_groups,
    reflective_light_transport_issues,
)


SHOT_ID_RE = re.compile(r"^S\d+-\d+-\d+$")
RISK_FLAGS = {
    "critical_performance_turn",
    "multi_person",
    "boundary",
    "prop_transfer",
    "physical_support",
    "screen_or_text",
    "complex_camera",
    "lighting_change",
}
PERFORMANCE_FIELDS = (
    "source_anchor",
    "relationship_goal",
    "speaker_actor",
    "speaker_visible_fact",
    "listener_actor",
    "listener_trigger",
    "listener_visible_fact",
    "end_residue",
    "readability",
    "camera_service",
)
EMOTION_CONTRACT_FIELDS = (
    "emotional_cause",
    "speaker_strategy",
    "speaker_leak",
    "listener_strategy_shift",
)
VISUAL_FIELDS = ("first_focus", "core_fact", "end_image")
CAMERA_STRATEGY_FIELDS = ("audience_position", "movement_arc", "static_rule", "forbidden_repetition")
CAMERA_FIELDS = ("visual_task", "mode", "trigger", "path", "dramatic_gain", "end_frame")
CAMERA_OPTIONAL_FIELDS = ("shot_size", "composition")
CAMERA_MODES = ("static", "push", "pull", "track", "pan", "arc", "rack_focus", "reframe", "handheld")
MOTION_OWNERSHIP_FIELDS = ("camera_path", "focus_path", "actor_path", "prop_path", "terminal_state")
LIGHTING_FIELDS = ("source_entities", "transport_path", "material_response", "luminance_order", "dark_region")
TONE_CARD_FIELDS = (
    "emotional_function",
    "dominant_palette",
    "support_palette",
    "accent_palette",
    "temperature",
    "key_light",
    "shadow_tone",
    "contrast_saturation",
    "background_brightness",
    "skin_protection",
    "material_anchor",
    "allowed_variation",
    "forbidden_contamination",
)
TONE_CARD_OPTIONAL_FIELDS = ("technical_baseline", "negative_lighting")
SCENE_WIDE_STATIC_TERMS = (
    "全场静止", "整场静止", "全程静止", "全场固定", "整场固定", "全程固定",
    "所有镜头静止", "全部镜头静止", "所有镜头固定", "全部镜头固定",
)
STATIC_BENEFIT_TERMS = (
    "等待", "观察", "监视", "僵持", "尴尬", "屏息", "留白", "压迫", "无处可退",
    "关系距离", "空位", "悬念", "沉默", "凝视", "对峙", "困住", "停顿",
)
STATIC_TEMPLATE_TERMS = ("摄影机固定", "固定机位", "镜头固定", "有意静止", "保持静止", "稳定到结束")
STYLE_ONLY_TERMS = ("3D", "UE5", "CG", "电影感", "高级感", "唯美", "写实风格", "渲染")
FACT_TERMS = (
    "站", "坐", "走", "停", "看", "望", "递", "接", "拿", "放", "门", "桌", "椅",
    "手", "脚", "眼", "距离", "隔", "靠", "转", "抬", "压", "退", "进", "出", "说",
)
MICRO_READABILITY_TERMS = ("眼睑", "睫毛", "眉尾", "嘴角", "指尖", "指节", "喉结", "泪光", "瞳孔", "唇角")
CLOSE_SHOT_SIZES = ("特写", "近景", "中近景")
DIRECT_PERFORMANCE_FIELDS = (
    "emotional_cause",
    "speaker_strategy",
    "speaker_visible_fact",
    "speaker_leak",
    "listener_trigger",
    "listener_visible_fact",
    "listener_strategy_shift",
)
DESIGN_ONLY_PERFORMANCE_FIELDS = ("source_anchor", "relationship_goal", "readability", "camera_service")
DESIGN_ONLY_CAMERA_FIELDS = ("visual_task", "shot_size", "composition", "dramatic_gain")


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    """Keep contract edits lossless; json.loads otherwise silently keeps the last key."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_contract(path: str | Path) -> dict:
    source = Path(path).expanduser().resolve()
    try:
        return json.loads(
            source.read_text(encoding="utf-8-sig"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc


def _text(value: object, label: str, *, required: bool = True) -> str:
    result = str(value or "").strip()
    if required and not result:
        raise ValueError(f"{label} is required")
    return result


def _shot_size(text: str) -> str:
    return next((term for term in sorted(SHOT_SIZE_TERMS, key=len, reverse=True) if term in str(text or "")), "")


def _normalize_motion_ownership(raw: object, label: str) -> dict[str, str] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be an object")
    return {
        field: _text(raw.get(field), f"{label}.{field}")
        for field in MOTION_OWNERSHIP_FIELDS
    }


def motion_ownership_issues(motion: dict[str, str]) -> list[str]:
    """Validate the typed ownership ledger carried by a moving camera design."""
    required_markers = {
        "camera_path": ("摄影机", "镜头", "机位"),
        "focus_path": ("焦点", "焦平面", "焦距", "无需转焦", "焦点固定"),
        "actor_path": ("手", "指尖", "手指", "人物", "角色", "无人物动作"),
        "prop_path": ("道具", "叶片", "野菜", "菜篮", "留在", "无道具", "无道具路径"),
        "terminal_state": ("停", "稳", "保持", "仍", "留在", "终态", "落幅"),
    }
    issues: list[str] = []
    for field, markers in required_markers.items():
        if not any(marker in motion[field] for marker in markers):
            issues.append(f"motion_ownership.{field} must name its subject and stable state")
    # The ledger is typed, but the individual clauses still go through the same
    # wording lint used for the final direct prompt.
    for issue in camera_prop_motion_ownership_issues("；".join(motion.values())):
        issues.append(f"motion_ownership wording is ambiguous -> {issue}")
    return issues


def validate_contract(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("scene contract must be an object")
    version = payload.get("version", 1)
    if version != 1:
        raise ValueError("scene contract version must be 1")
    scene_id = _text(payload.get("scene_id"), "scene_id")
    risks = payload.get("risk_vector", [])
    if not isinstance(risks, list):
        raise ValueError("risk_vector must be a list")
    risks = list(dict.fromkeys(_text(item, "risk_vector item") for item in risks))
    unknown = sorted(set(risks) - RISK_FLAGS)
    if unknown:
        raise ValueError("unknown risk flags: " + ",".join(unknown))
    raw_camera_strategy = payload.get("camera_strategy")
    if raw_camera_strategy is None:
        camera_strategy = None
    elif isinstance(raw_camera_strategy, dict):
        camera_strategy = {
            field: _text(raw_camera_strategy.get(field), f"camera_strategy.{field}")
            for field in CAMERA_STRATEGY_FIELDS
        }
    else:
        raise ValueError("camera_strategy must be an object")
    raw_tone_card = payload.get("tone_card")
    if raw_tone_card is None:
        tone_card = None
    elif isinstance(raw_tone_card, dict):
        tone_card = {
            field: _text(raw_tone_card.get(field), f"tone_card.{field}")
            for field in TONE_CARD_FIELDS
        }
        tone_card.update({
            field: _text(raw_tone_card.get(field), f"tone_card.{field}", required=False)
            for field in TONE_CARD_OPTIONAL_FIELDS
        })
    else:
        raise ValueError("tone_card must be an object")
    raw_shots = payload.get("shots")
    if not isinstance(raw_shots, list) or not raw_shots:
        raise ValueError("shots must contain at least one shot contract")
    shot_ids: set[str] = set()
    shots = []
    for index, shot in enumerate(raw_shots, start=1):
        if not isinstance(shot, dict):
            raise ValueError(f"shots[{index}] must be an object")
        shot_id = _text(shot.get("shot_id"), f"shots[{index}].shot_id")
        if not SHOT_ID_RE.fullmatch(shot_id):
            raise ValueError(f"shots[{index}].shot_id must match S1-01-1")
        if shot_id in shot_ids:
            raise ValueError(f"duplicate shot_id: {shot_id}")
        shot_ids.add(shot_id)
        performance = shot.get("performance")
        if performance is None:
            normalized_performance = None
        elif isinstance(performance, dict):
            normalized_performance = {
                field: _text(performance.get(field), f"{shot_id}.performance.{field}")
                for field in PERFORMANCE_FIELDS
            }
            normalized_performance.update({
                field: _text(performance.get(field), f"{shot_id}.performance.{field}", required=False)
                for field in EMOTION_CONTRACT_FIELDS
            })
            if normalized_performance["speaker_actor"] == normalized_performance["listener_actor"]:
                raise ValueError(f"{shot_id} speaker_actor and listener_actor must differ")
        else:
            raise ValueError(f"{shot_id}.performance must be an object or null")
        visual = shot.get("visual_core")
        if not isinstance(visual, dict):
            raise ValueError(f"{shot_id}.visual_core must be an object")
        normalized_visual = {
            field: _text(visual.get(field), f"{shot_id}.visual_core.{field}")
            for field in VISUAL_FIELDS
        }
        raw_camera = shot.get("camera")
        if raw_camera is None:
            normalized_camera = None
        elif isinstance(raw_camera, dict):
            normalized_camera = {
                field: _text(raw_camera.get(field), f"{shot_id}.camera.{field}")
                for field in CAMERA_FIELDS
            }
            normalized_camera.update({
                field: _text(raw_camera.get(field), f"{shot_id}.camera.{field}", required=False)
                for field in CAMERA_OPTIONAL_FIELDS
            })
            if normalized_camera["mode"] not in CAMERA_MODES:
                raise ValueError(f"{shot_id}.camera.mode must be one of {','.join(CAMERA_MODES)}")
            normalized_camera["motion_ownership"] = _normalize_motion_ownership(
                raw_camera.get("motion_ownership"), f"{shot_id}.camera.motion_ownership"
            )
        else:
            raise ValueError(f"{shot_id}.camera must be an object")
        raw_lighting = shot.get("lighting")
        if raw_lighting is None:
            normalized_lighting = None
        elif isinstance(raw_lighting, dict):
            normalized_lighting = {
                field: _text(raw_lighting.get(field), f"{shot_id}.lighting.{field}")
                for field in LIGHTING_FIELDS
            }
        else:
            raise ValueError(f"{shot_id}.lighting must be an object")
        spatial = shot.get("spatial") or {}
        if not isinstance(spatial, dict):
            raise ValueError(f"{shot_id}.spatial must be an object")
        blocking_id = _text(spatial.get("blocking_id"), f"{shot_id}.spatial.blocking_id", required=False)
        protected = shot.get("protected_facts", [])
        if not isinstance(protected, list):
            raise ValueError(f"{shot_id}.protected_facts must be a list")
        protected = list(dict.fromkeys(_text(item, f"{shot_id}.protected_facts item") for item in protected))
        shots.append({
            "shot_id": shot_id,
            "performance": normalized_performance,
            "visual_core": normalized_visual,
            "camera": normalized_camera,
            "lighting": normalized_lighting,
            "spatial": {"blocking_id": blocking_id},
            "protected_facts": protected,
        })
    return {
        "version": 1,
        "scene_id": scene_id,
        "risk_vector": risks,
        "camera_strategy": camera_strategy,
        "tone_card": tone_card,
        "shots": shots,
    }


def completeness_issues(payload: dict) -> list[str]:
    """Reject contract omissions before prompts, blocking sheets, or controls exist.

    This is deliberately opt-in so legacy object-only contracts remain readable;
    generation routing enables it as a hard pre-generation gate.
    """
    contract = validate_contract(payload)
    risks = set(contract["risk_vector"])
    issues: list[str] = []
    if contract["tone_card"] is None:
        issues.append(
            "tone_card is required before prompt compilation; freeze dominant/support/accent palette, temperature, "
            "key light, shadow tone, contrast/saturation, background brightness, skin protection, allowed variation "
            "and forbidden contamination"
        )
    elif bool(contract["tone_card"].get("technical_baseline")) != bool(contract["tone_card"].get("negative_lighting")):
        issues.append("tone_card technical_baseline and negative_lighting must be supplied together")
    high_risk_performance = bool(risks & {"critical_performance_turn", "multi_person"})
    if contract["camera_strategy"] is None:
        issues.append("camera_strategy is required before shot compilation")
    moving_shots: list[str] = []
    for shot in contract["shots"]:
        shot_id = shot["shot_id"]
        performance = shot["performance"]
        camera = shot["camera"]
        if camera is None:
            issues.append(f"{shot_id}: camera design is required before prompt compilation")
        elif camera["mode"] != "static":
            moving_shots.append(shot_id)
            motion = camera.get("motion_ownership")
            if motion is None:
                issues.append(
                    f"{shot_id}: moving camera requires camera.motion_ownership with separate camera_path, "
                    "focus_path, actor_path, prop_path and terminal_state"
                )
            else:
                issues.extend(f"{shot_id}: {issue}" for issue in motion_ownership_issues(motion))
        if camera is not None and not camera.get("shot_size"):
            issues.append(f"{shot_id}: camera.shot_size is required; choose a shot size for the performance and camera gain")
        if camera is not None and not camera.get("composition"):
            issues.append(f"{shot_id}: camera.composition is required; describe the visible relationship geometry, not a style label")
        if camera:
            for issue in camera_prop_motion_ownership_issues(camera["path"]):
                issues.append(f"{shot_id}: camera.path motion ownership is ambiguous -> {issue}")
        if performance is None and high_risk_performance:
            issues.append(
                f"{shot_id}: performance:null is not allowed for a critical/multi-person scene; "
                "declare a visible performance or explicitly route this as an object-only shot"
            )
        elif performance is not None:
            missing_emotion = [field for field in EMOTION_CONTRACT_FIELDS if not performance.get(field)]
            if missing_emotion:
                issues.append(
                    f"{shot_id}: performance emotion chain incomplete -> {','.join(missing_emotion)}; "
                    "declare cause, speaker strategy/leak and listener strategy shift before prompt compilation"
                )
        if camera is not None and performance is not None:
            camera_size = _shot_size(camera.get("shot_size", ""))
            readability_size = _shot_size(performance.get("readability", ""))
            if camera_size and readability_size and camera_size != readability_size:
                issues.append(
                    f"{shot_id}: camera.shot_size conflicts with performance.readability -> "
                    f"{camera_size} vs {readability_size}"
                )
            detail_payload = "；".join([
                performance.get("speaker_leak", ""),
                performance.get("listener_visible_fact", ""),
                performance.get("readability", ""),
            ])
            if any(term in detail_payload for term in MICRO_READABILITY_TERMS) and camera_size not in CLOSE_SHOT_SIZES:
                issues.append(
                    f"{shot_id}: micro-expression/detail requires 特写/近景/中近景, not {camera_size or 'unspecified'}"
                )
        visual = shot["visual_core"]
        lighting = shot["lighting"]
        reflective_risk = any(
            term in " ".join([*visual.values(), *shot["protected_facts"]])
            for term in REFLECTIVE_OPTICAL_CUES
        )
        if reflective_risk and lighting is None:
            issues.append(
                f"{shot_id}: reflective visual focus requires lighting source/transport/material/luminance/dark-region contract"
            )
        elif lighting is not None:
            lighting_text = "；".join(lighting.values())
            if reflective_risk and not any(term in lighting["material_response"] for term in REFLECTIVE_OPTICAL_CUES):
                issues.append(f"{shot_id}: lighting.material_response must name the reflective subject/cue")
            for issue in reflective_light_transport_issues(lighting_text):
                issues.append(f"{shot_id}: lighting transport is incomplete -> {issue}")
        for field in ("first_focus", "core_fact", "end_image"):
            value = visual[field]
            if any(term in value for term in STYLE_ONLY_TERMS) and not any(term in value for term in FACT_TERMS):
                issues.append(f"{shot_id}: visual_core.{field} is style-only, not a plot/relationship fact")
        if risks & {"multi_person", "boundary"} and not shot["spatial"]["blocking_id"]:
            issues.append(f"{shot_id}: spatial.blocking_id is required for multi-person/boundary scenes")
        if risks & {"critical_performance_turn", "multi_person"} and not shot["protected_facts"]:
            issues.append(f"{shot_id}: protected_facts must contain the non-degradable relationship or state fact")
    shot_count = len(contract["shots"])
    camera_strategy = contract["camera_strategy"]
    camera_designs = [shot["camera"] for shot in contract["shots"]]
    all_static = bool(camera_designs) and all(camera and camera["mode"] == "static" for camera in camera_designs)
    deliberate_static_scene = False
    if camera_strategy and all_static:
        static_rule = camera_strategy["static_rule"]
        gains = [camera["dramatic_gain"] for camera in camera_designs if camera]
        visual_tasks = [camera["visual_task"] for camera in camera_designs if camera]
        gain_payloads = [
            _compact(reduce(lambda text, term: text.replace(term, ""), STATIC_TEMPLATE_TERMS, gain))
            for gain in gains
        ]
        deliberate_static_scene = (
            any(term in static_rule for term in SCENE_WIDE_STATIC_TERMS)
            and all(any(term in gain for term in STATIC_BENEFIT_TERMS) for gain in gains)
            and all(gain_payloads)
            and len({_compact(task) for task in visual_tasks}) == shot_count
            and len(set(gain_payloads)) == shot_count
        )
    minimum_moves = 0 if shot_count < 2 else max(1, (shot_count + 3) // 4)
    if shot_count >= 2 and not moving_shots:
        issues.append(
            "scene camera design is entirely static across multiple shots; choose at least one motivated camera response "
            "or split the scene into a single intentional-static shot"
        )
    elif len(moving_shots) < minimum_moves and not deliberate_static_scene:
        issues.append(
            f"scene camera design has {len(moving_shots)}/{shot_count} moving shots; "
            f"at least {minimum_moves} motivated camera responses are required, unless the whole scene declares "
            "distinct intentional-static tasks and dramatic gains"
        )
    if len(moving_shots) >= 3:
        moving_modes = [
            shot["camera"]["mode"]
            for shot in contract["shots"]
            if shot["camera"] and shot["camera"]["mode"] != "static"
        ]
        if len(set(moving_modes)) == 1:
            issues.append("all moving shots reuse one camera mode; vary the dramatic mechanism, not just wording")
    return issues


def _compact(text: str) -> str:
    return re.sub(r"[\s，。；;：:、|/（）()《》【】\[\]“”\"'‘’]+", "", text)


def _covered(fact: str, prompt: str) -> bool:
    fact_text = _compact(fact)
    prompt_text = _compact(prompt)
    if not fact_text:
        return True
    if fact_text in prompt_text:
        return True
    if len(fact_text) < 4:
        return fact_text in prompt_text
    grams = {fact_text[index:index + 2] for index in range(len(fact_text) - 1)}
    prompt_grams = {prompt_text[index:index + 2] for index in range(max(0, len(prompt_text) - 1))}
    return bool(grams) and len(grams & prompt_grams) / len(grams) >= 0.68


def _merge_clause(clauses: list[dict], field_id: str, text: str) -> None:
    """Deduplicate executable facts while retaining every source field ID."""
    value = str(text or "").strip()
    compact_value = _compact(value)
    if not compact_value:
        return
    for clause in clauses:
        compact_existing = _compact(clause["text"])
        if compact_value == compact_existing or compact_value in compact_existing:
            clause["field_ids"].append(field_id)
            return
        if compact_existing in compact_value and len(compact_existing) >= 4:
            clause["text"] = value
            clause["field_ids"].append(field_id)
            return
    clauses.append({"field_ids": [field_id], "text": value})


def compiled_prompt_contract(contract: dict, shot: dict) -> dict:
    """Compile only generation-executable contract facts, not director-analysis prose."""
    tone = contract.get("tone_card") or {}
    tone_fields = (
        "dominant_palette", "temperature", "key_light", "shadow_tone",
        "background_brightness", "skin_protection",
    )
    prefix_clauses: list[dict] = []
    for field in tone_fields:
        _merge_clause(prefix_clauses, f"tone_card.{field}", tone.get(field, ""))

    body_clauses: list[dict] = []
    visual = shot["visual_core"]
    _merge_clause(body_clauses, "visual_core.first_focus", visual["first_focus"])
    _merge_clause(body_clauses, "visual_core.core_fact", visual["core_fact"])
    for index, fact in enumerate(shot["protected_facts"], start=1):
        _merge_clause(body_clauses, f"protected_facts[{index}]", fact)

    performance = shot.get("performance")
    if performance:
        for field in DIRECT_PERFORMANCE_FIELDS:
            _merge_clause(body_clauses, f"performance.{field}", performance.get(field, ""))

    camera = shot.get("camera")
    if camera:
        _merge_clause(body_clauses, "camera.trigger", camera["trigger"])
        _merge_clause(body_clauses, "camera.path", camera["path"])
        motion = camera.get("motion_ownership")
        if motion:
            for field in MOTION_OWNERSHIP_FIELDS:
                if field != "terminal_state":
                    _merge_clause(body_clauses, f"camera.motion_ownership.{field}", motion[field])

    lighting = shot.get("lighting")
    if lighting:
        for field in LIGHTING_FIELDS:
            _merge_clause(body_clauses, f"lighting.{field}", lighting[field])

    terminal_clauses: list[dict] = []
    if performance:
        _merge_clause(terminal_clauses, "performance.end_residue", performance["end_residue"])
    _merge_clause(terminal_clauses, "visual_core.end_image", visual["end_image"])
    if camera:
        _merge_clause(terminal_clauses, "camera.end_frame", camera["end_frame"])
        motion = camera.get("motion_ownership")
        if motion:
            _merge_clause(
                terminal_clauses,
                "camera.motion_ownership.terminal_state",
                motion["terminal_state"],
            )

    prefix = "，".join(item["text"].rstrip("；;，,") for item in prefix_clauses) + "；"
    body = "；".join(item["text"].rstrip("；;") for item in body_clauses) + "。"
    terminal = "最后" + "；".join(item["text"].rstrip("；;。") for item in terminal_clauses) + "，稳定到结束。"
    assembly = prefix + body + terminal
    high_risk = bool(set(contract.get("risk_vector", [])) & {
        "critical_performance_turn", "multi_person", "boundary", "prop_transfer",
        "physical_support", "complex_camera", "lighting_change",
    })
    prompt_limit = 650 if high_risk else 500
    reserved_for_scene_dialogue = 120
    issues = []
    if len(prefix) > 220:
        issues.append(f"{shot['shot_id']}: compiled tone prefix exceeds 220 chars")
    if len(assembly) > prompt_limit - reserved_for_scene_dialogue:
        issues.append(
            f"{shot['shot_id']}: executable contract uses {len(assembly)} chars; "
            f"compress contract facts to leave {reserved_for_scene_dialogue} chars for scene and dialogue "
            f"within the {prompt_limit}-char limit"
        )
    return {
        "shot_id": shot["shot_id"],
        "prefix": prefix,
        "body": body,
        "terminal": terminal,
        "assembly": assembly,
        "character_count": len(assembly),
        "prompt_limit": prompt_limit,
        "reserved_for_scene_dialogue": reserved_for_scene_dialogue,
        "clauses": {
            "prefix": prefix_clauses,
            "body": body_clauses,
            "terminal": terminal_clauses,
        },
        "design_only_fields": [
            *[f"performance.{field}" for field in DESIGN_ONLY_PERFORMANCE_FIELDS],
            *[f"camera.{field}" for field in DESIGN_ONLY_CAMERA_FIELDS],
        ],
        "issues": issues,
    }


def compile_contract(payload: dict, shot_id: str = "") -> dict:
    contract = validate_contract(payload)
    selected = [shot for shot in contract["shots"] if not shot_id or shot["shot_id"] == shot_id]
    if shot_id and not selected:
        raise ValueError(f"shot_id not found in contract: {shot_id}")
    compiled = [compiled_prompt_contract(contract, shot) for shot in selected]
    issues = [issue for item in compiled for issue in item["issues"]]
    tone = contract.get("tone_card") or {}
    tone_labels = (
        ("剧情情绪功能", "emotional_function"), ("主色", "dominant_palette"),
        ("辅助色", "support_palette"), ("点缀色", "accent_palette"),
        ("色温", "temperature"), ("主光", "key_light"), ("阴影色", "shadow_tone"),
        ("对比度/饱和度", "contrast_saturation"), ("背景亮度", "background_brightness"),
        ("肤色保护", "skin_protection"), ("材质反光/纹理", "material_anchor"),
        ("允许变化", "allowed_variation"), ("禁止偏色", "forbidden_contamination"),
    )
    tone_card_header = "本集影调色卡索引：" + " | ".join(
        f"{label}={tone.get(field, '')}" for label, field in tone_labels
    )
    scene_tone_line = "影调色卡句：" + "；".join(
        tone.get(field, "")
        for field in (
            "dominant_palette", "temperature", "key_light", "shadow_tone",
            "background_brightness", "skin_protection",
        )
        if tone.get(field)
    ) + "。角色声音使用：使用本集角色声音锁定表。"
    return {
        "pass": not issues,
        "scene_id": contract["scene_id"],
        "shot_count": len(compiled),
        "shots": compiled,
        "issues": issues,
        "tone_card_header": tone_card_header,
        "scene_tone_line": scene_tone_line,
        "primary_storyboard_modified": False,
    }


def _tone_prefix_issues(tone_card: dict[str, str], prompt: str, shot_id: str) -> list[str]:
    """Require a compact, per-shot recovery of the frozen scene tone.

    The full card stays internal. Only the five generation-critical facts are
    recovered in the first 220 characters so a prompt cannot silently choose a
    new palette while avoiding meaningful token growth.
    """
    prefix = prompt[:220]
    required = (
        ("dominant_palette", "主色/影调"),
        ("temperature", "色温"),
        ("key_light", "主光"),
        ("shadow_tone", "阴影色"),
        ("skin_protection", "肤色保护"),
    )
    issues: list[str] = []
    for field, label in required:
        if not _covered(tone_card[field], prefix):
            issues.append(
                f"{shot_id}: tone_card.{field} must be compressed into the first 220 prompt chars ({label})"
            )
    return issues


def storyboard_prompts(markdown: str) -> dict[str, str]:
    prompts: dict[str, str] = {}
    for group in iter_groups(markdown):
        group_id = group.group(1)
        for number, child in enumerate(iter_children(group.group(3)), start=1):
            prompts[f"{group_id}-{number}"] = direct_prompt(child.group(0))
    return prompts


def recovery_issues(contract: dict, markdown: str) -> list[str]:
    contract = validate_contract(contract)
    prompts = storyboard_prompts(markdown)
    issues: list[str] = []
    tone_card = contract.get("tone_card")
    if tone_card is None:
        issues.append("scene tone_card is missing; direct prompt recovery cannot prove palette continuity")
    for shot in contract["shots"]:
        shot_id = shot["shot_id"]
        prompt = prompts.get(shot_id, "")
        if not prompt:
            issues.append(f"{shot_id}: missing direct prompt for contract recovery")
            continue
        if tone_card is not None:
            issues.extend(_tone_prefix_issues(tone_card, prompt, shot_id))
        performance = shot["performance"]
        if performance:
            for actor_field in ("speaker_actor", "listener_actor"):
                actor = performance[actor_field]
                if actor not in prompt:
                    issues.append(f"{shot_id}: protected actor missing -> {actor}")
        compiled = compiled_prompt_contract(contract, shot)
        for phase in ("body", "terminal"):
            search_text = prompt if phase == "body" else prompt[max(0, len(prompt) * 3 // 4):]
            for clause in compiled["clauses"][phase]:
                if not _covered(clause["text"], search_text):
                    labels = ",".join(clause["field_ids"])
                    issues.append(f"{shot_id}: executable contract not recovered [{labels}] -> {clause['text']}")
        terminal_window = prompt[max(0, len(prompt) * 3 // 4):]
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract")
    parser.add_argument("--storyboard")
    parser.add_argument("--report")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--strict-completeness", action="store_true")
    args = parser.parse_args(argv)
    if not args.compact or not args.report or not args.strict_completeness:
        parser.error("legacy contract validation is disabled; --strict-completeness, --compact and --report are required")
    try:
        contract_path = Path(args.contract).expanduser().resolve()
        contract = validate_contract(load_contract(contract_path))
        issues = []
        if args.strict_completeness:
            issues.extend(completeness_issues(contract))
        if args.storyboard:
            markdown = Path(args.storyboard).expanduser().resolve().read_text(encoding="utf-8-sig")
            issues.extend(recovery_issues(contract, markdown))
        result = {
            "pass": not issues,
            "scene_id": contract["scene_id"],
            "shot_count": len(contract["shots"]),
            "risk_vector": contract["risk_vector"],
            "issues": issues,
            "strict_completeness": args.strict_completeness,
            "primary_storyboard_modified": False,
        }
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"pass": False, "error": str(exc), "primary_storyboard_modified": False}
    if args.report:
        report = Path(args.report).expanduser().resolve()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.compact:
        print(json.dumps({
            "status": "PASS" if result.get("pass") else "FAIL",
            "scene_id": result.get("scene_id"),
            "shot_count": result.get("shot_count"),
            "risk_vector": result.get("risk_vector", []),
            "issue_count": len(result.get("issues", [])),
            "report": str(Path(args.report).expanduser().resolve()) if args.report else None,
        }, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
