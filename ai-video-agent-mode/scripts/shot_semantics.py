"""Shared subshot classification helpers.

These helpers keep the "base_action may be empty" rule consistent across
preflight, duration validation, and director assembly.
"""

NON_ACTION_TYPES = [
    "empty", "background", "object", "prop", "environment", "establishing",
    "transition", "black", "still", "insert",
    "空镜", "背景", "物件", "道具", "环境", "转场", "黑场", "静帧", "插入",
]

NON_CHARACTER_WORDS = [
    "空镜", "背景", "环境", "街景", "天空", "建筑", "房间", "走廊", "门牌",
    "手机屏幕", "短信", "微信", "物件", "道具", "窗外", "灯光", "雨水", "桌面",
]

CHARACTER_ACTION_WORDS = [
    "说", "看", "走", "跑", "站", "坐", "转身", "抬头", "低头", "伸手",
    "拿", "放", "哭", "笑", "抱", "推", "拉", "打", "躲", "盯", "望",
]

CHARACTER_BODY_WORDS = ["眼", "眉", "嘴", "手", "肩", "背", "脚", "袖", "衣", "呼吸", "步伐", "身影", "背影"]
CHARACTER_STATE_ACTION_WORDS = [
    "伫立", "凝神", "不语", "沉默", "整理", "停住", "僵住", "发怔", "出神", "驻足",
    "倚", "靠", "伏", "蹲", "跪", "徘徊", "等待", "回避", "躲闪", "皱眉", "叹气",
]

RENDER_ANCHOR_FIELDS = ["visual_intent", "image_subject", "atmosphere"]

# Dispatch risk is deliberately derived only from already-approved shot facts.
# It chooses context and batch capacity; it never relaxes the quality contract
# or allows an Agent/validator stage to be skipped.
FIGHT_OR_FORCE_WORDS = [
    "打斗", "搏斗", "互殴", "攻击", "格挡", "闪避", "追逐", "推搡", "拉扯",
    "扭打", "受力", "制服", "抢夺", "救援", "fight", "combat",
]
PROP_TRANSFER_WORDS = ["递给", "交给", "传给", "塞给", "接过", "交接", "移交", "抢走", "夺过"]
MULTI_PERSON_MOTION_WORDS = ["走向", "靠近", "后退", "错身", "围住", "围堵", "跟随", "追", "拉", "推"]


def shot_type_text(subshot):
    return str(
        subshot.get("shot_type", "")
        or subshot.get("visual_type", "")
        or subshot.get("purpose", "")
    ).lower()


def render_anchor(subshot):
    for field in RENDER_ANCHOR_FIELDS:
        value = str(subshot.get(field, "") or "").strip()
        if value:
            return value
    return ""


def is_declared_non_action(subshot):
    text = shot_type_text(subshot)
    return any(token.lower() in text for token in NON_ACTION_TYPES)


def is_true_non_action_subshot(subshot):
    """Only an explicitly confirmed, genuinely empty insert may skip performance."""
    if subshot.get("dialogue_refs"):
        return False
    if subshot.get("characters"):
        return False
    if is_implicit_character_action(subshot.get("base_action", "")):
        return False
    return (
        subshot.get("non_character_confirmed") is True
        and is_declared_non_action(subshot)
        and bool(render_anchor(subshot))
    )


def is_implicit_character_action(base_action):
    """Labels never override visible human action hidden in a supposed insert."""
    text = str(base_action or "")
    return any(token in text for token in CHARACTER_ACTION_WORDS + CHARACTER_BODY_WORDS + CHARACTER_STATE_ACTION_WORDS)


def requires_base_action(subshot):
    """Return True when missing base_action would leave downstream agents blind."""
    if subshot.get("base_action"):
        return False
    return not is_true_non_action_subshot(subshot)


def requires_characters(base_action, dialogue_refs, shot_size, shot_type):
    """Return True when an empty characters list is likely an omission."""
    if dialogue_refs:
        return True
    if is_implicit_character_action(base_action):
        return True
    blob = " ".join(str(x) for x in [base_action, shot_size, shot_type]).lower()
    if any(token.lower() in blob for token in NON_ACTION_TYPES):
        return False
    if any(word in str(base_action) for word in NON_CHARACTER_WORDS):
        return False
    return any(word in str(base_action) for word in CHARACTER_ACTION_WORDS)


def analysis_profile(subshot):
    """Classify the creative work a subshot needs without lowering its quality bar."""
    if is_true_non_action_subshot(subshot):
        shot_type = shot_type_text(subshot)
        if any(token in shot_type for token in ("object", "prop", "物件", "道具", "insert", "插入")):
            return "object"
        return "environment"
    if subshot.get("dialogue_refs"):
        return "dialogue"
    characters = subshot.get("characters", []) or []
    if len(characters) > 1 or str(subshot.get("emotion_tone", "") or "").strip():
        return "dramatic"
    return "action"


def quality_contract(subshot):
    """Return model-agnostic quality requirements for every subshot class."""
    profile = analysis_profile(subshot)
    common = ["composition_readability", "source_light_continuity", "camera_execution", "end_state_carryover"]
    requirements = {
        "environment": ["narrative_function", "visual_anchor", "space_light_layering", "transition_carryover"],
        "object": ["narrative_function", "prop_identity_or_state", "focus_readability", "transition_carryover"],
        "action": ["visible_intent", "action_completion", "body_or_prop_contact", "end_state_carryover"],
        "dialogue": ["exact_dialogue_boundary", "delivery_and_lip_sync", "caused_listener_response", "axis_continuity"],
        "dramatic": ["performance_causality", "visible_emotion_chain", "motivated_camera_response", "cross_shot_residue"],
    }[profile]
    return {
        "profile": profile,
        "required_analysis": ["scene_lock", "master_production"],
        "required_evidence": common + requirements,
    }


def workload_units(subshot, phase):
    """Estimate context load for batching without changing any quality contract.

    The score is intentionally conservative: a complex performance gets a
    smaller batch, while an explicitly confirmed empty insert can share a
    batch with peers. Every item still receives the same required analyses.
    """
    profile = analysis_profile(subshot)
    units = {
        "environment": 1,
        "object": 1,
        "action": 2,
        "dialogue": 3,
        "dramatic": 4,
    }[profile]
    characters = subshot.get("visible_characters", subshot.get("characters", [])) or []
    if isinstance(characters, str):
        characters = [characters] if characters.strip() else []
    units += max(len(characters) - 1, 0)
    if subshot.get("editorial_mode") == "shot_group":
        units += 1
    if phase == "master_production" and subshot.get("dialogue_refs"):
        units += 1
    return units


def dispatch_risk(item):
    """Classify review depth and batch capacity from source-supported facts.

    ``light`` still receives the Master Production and Editor Pass 2 Agent
    stages.  It merely carries a narrower review window because it has no
    high-risk spatial, contact, dialogue, or handoff dependency.
    """
    item = item if isinstance(item, dict) else {}
    sources = item.get("source_subshots")
    sources = sources if isinstance(sources, list) and sources else [item]
    text_parts = []
    characters = []
    dialogue_text_length = 0
    has_dialogue = False
    has_shot_group = False
    duration = 0.0
    metadata = item.get("qa_metadata", {}) if isinstance(item.get("qa_metadata"), dict) else {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        text_parts.extend(str(source.get(key, "") or "") for key in (
            "base_action", "scene_type", "shot_type", "visual_type", "purpose", "axis_space",
        ))
        people = source.get("visible_characters", source.get("characters", [])) or []
        if isinstance(people, str):
            people = [people] if people.strip() else []
        characters.extend(str(person).strip() for person in people if str(person).strip())
        events = source.get("dialogue_events", []) or []
        refs = source.get("dialogue_refs", []) or []
        has_dialogue = has_dialogue or bool(events or refs)
        dialogue_text_length += sum(len(str(event.get("text", "") or "")) for event in events if isinstance(event, dict))
        has_shot_group = has_shot_group or source.get("editorial_mode") == "shot_group"
        try:
            duration += float(source.get("duration", 0) or 0)
        except (TypeError, ValueError):
            pass
    if not characters:
        roles = metadata.get("performance_priority", {}) if isinstance(metadata.get("performance_priority"), dict) else {}
        characters = [roles.get("primary", "")] + list(roles.get("supporting", []) or []) + list(roles.get("background", []) or [])
        characters = [str(person).strip() for person in characters if str(person).strip()]
    if not has_dialogue:
        has_dialogue = bool(metadata.get("dialogue_refs") or metadata.get("dialogue_events"))
    has_shot_group = has_shot_group or metadata.get("editorial_mode") == "shot_group"
    reroll = metadata.get("reroll_control", {}) if isinstance(metadata.get("reroll_control"), dict) else {}
    text = " ".join(text_parts + [str(metadata.get("continuity_contract", "") or "")])
    unique_characters = list(dict.fromkeys(characters))
    reasons = []
    if any(token in text for token in FIGHT_OR_FORCE_WORDS):
        reasons.append("fight_or_force")
    if any(token in text for token in PROP_TRANSFER_WORDS):
        reasons.append("prop_transfer")
    if has_shot_group:
        reasons.append("shot_group")
    if len(unique_characters) > 1 and any(token in text for token in MULTI_PERSON_MOTION_WORDS):
        reasons.append("multi_person_motion")
    if has_dialogue and (duration >= 8 or dialogue_text_length >= 32):
        reasons.append("long_dialogue")
    if reroll.get("risk_level") == "high":
        reasons.append("high_reroll_risk")
    if reasons:
        return {"tier": "high", "reasons": reasons, "batch_capacity": 4, "review_scope": "full_scene_window"}
    is_non_character = bool(sources) and all(is_true_non_action_subshot(source) for source in sources if isinstance(source, dict))
    single_stable = len(unique_characters) <= 1 and not has_shot_group and not any(
        token in text for token in FIGHT_OR_FORCE_WORDS + PROP_TRANSFER_WORDS
    )
    if is_non_character:
        return {"tier": "light", "reasons": ["non_character_insert"], "batch_capacity": 10, "review_scope": "current_with_carryover"}
    if single_stable and (not has_dialogue or duration <= 6):
        return {"tier": "light", "reasons": ["single_stable" if not has_dialogue else "simple_dialogue"], "batch_capacity": 10, "review_scope": "current_with_carryover"}
    return {"tier": "standard", "reasons": ["normal_contract"], "batch_capacity": 6, "review_scope": "bounded_scene_window"}
