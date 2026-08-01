"""Shared subshot classification helpers.

These helpers keep the "base_action may be empty" rule consistent across
preflight, duration validation, and director assembly.
"""

from production_intelligence import prop_lifecycle_risk

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
MEMORY_MARKERS = ["当年", "曾经", "回忆", "想起", "往昔", "旧日", "那年", "记得"]
WEDDING_MEMORY_MARKERS = ["大婚", "成婚", "婚仪", "赐婚", "迎亲"]
MEMORY_EVENT_MARKERS = WEDDING_MEMORY_MARKERS + ["相遇", "告白", "争吵", "离开", "去世", "死去", "救下", "受伤", "事故", "火灾", "背叛", "毕业", "出生"]
EVENT_TRANSITION_MARKERS = ["穿越", "时空", "异世", "另一个时代", "来到过去", "来到未来", "梦醒", "幻觉消退", "传送", "瞬移", "重生", "变身", "变形", "苏醒"]

# A functional surface is the side of a prop that its user must face to use it.
# Video models often rotate that surface toward the audience for readability,
# so active use needs an explicit user/prop/camera orientation contract.
FUNCTIONAL_SURFACE_PROP_WORDS = [
    "手机", "智能手机", "平板", "平板电脑", "笔记本电脑", "电脑屏幕", "显示器",
    "书页", "书本", "文件", "纸张", "照片", "相片", "手表", "表盘", "仪表盘",
    "镜子", "镜面",
]
FUNCTIONAL_SURFACE_USE_WORDS = [
    "玩", "游戏", "查看", "察看", "看", "盯", "望", "凝视", "阅读", "读",
    "浏览", "刷", "滑动", "点击", "点按", "操作", "使用", "输入", "打字",
    "回复", "翻页", "照镜子", "对镜",
]


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


def functional_surface_risk(value):
    """Return True when a person actively uses a prop's functional face.

    Static props and transfers intentionally do not trigger this contract. The
    check walks source_subshots so a main task cannot hide the risky action in
    a later child beat.
    """
    for text in _semantic_text_leaves(value):
        normalized = str(text or "").replace("书桌", "").replace("书架", "").replace("书房", "")
        if not any(prop in normalized for prop in FUNCTIONAL_SURFACE_PROP_WORDS):
            continue
        if any(action in normalized for action in FUNCTIONAL_SURFACE_USE_WORDS):
            return True
    return False


def _semantic_text_leaves(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from _semantic_text_leaves(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            yield from _semantic_text_leaves(child)
    elif isinstance(value, str) and value.strip():
        yield value


def validation_profile(subshot, metadata=None, visible_characters=None):
    """Return the single authority for risk-triggered Composer contracts.

    Core delivery checks are intentionally not represented here: shape, source
    locks, timeline, dialogue, action/camera budgets and continuity remain
    mandatory in every applicable shot.  This profile only controls the
    expensive, explanatory quality contracts so an environment insert is not
    forced to impersonate a character-performance scene.
    """
    subshot = subshot if isinstance(subshot, dict) else {}
    metadata = metadata if isinstance(metadata, dict) else {}
    # Dispatch tier is an immutable routing fact.  Never let Agent-authored
    # metadata promote a light packet during validation; that would make the
    # packet hint and the validator disagree after the work has started.
    risk = dispatch_risk(subshot)
    quality = quality_contract(subshot)
    profile = quality["profile"]
    visible = visible_characters
    if visible is None:
        visible = subshot.get("visible_characters", subshot.get("characters", [])) or []
    if isinstance(visible, str):
        visible = [visible] if visible.strip() else []
    visible = [str(value).strip() for value in visible if str(value).strip()]
    events = metadata.get("dialogue_events", subshot.get("dialogue_events", []))
    events = events if isinstance(events, list) else []
    tension = ""
    for key in ("performance_contract", "emotion_driver", "performance_causality"):
        value = metadata.get(key, subshot.get(key, {}))
        if isinstance(value, dict) and value.get("tension_intent"):
            tension = str(value["tension_intent"])
            break
    has_character_performance = bool(visible) and profile in ("action", "dialogue", "dramatic")
    reasons = set(risk.get("reasons", []))
    prop_transition = "prop_transfer" in reasons or bool(
        isinstance(metadata.get("continuity_contract"), dict)
        and metadata["continuity_contract"].get("state_change")
    )
    expectation = metadata.get("expectation_anchor", {})
    participants = set(visible)
    participants.update(
        str(event.get("speaker", "") or "").strip()
        for event in events if isinstance(event, dict)
        and str(event.get("speaker", "") or "").strip()
    )
    return {
        "profile": profile,
        "risk_tier": risk.get("tier", "standard"),
        "performance_causality": has_character_performance,
        "performance_contract": has_character_performance,
        "story_punch_contract": has_character_performance or prop_transition,
        "ai_model_readiness_score": risk.get("tier") == "high",
        "pressure_release_design": tension in ("rising", "peak"),
        "listener_reaction_plan": bool(events) and len(visible) > 1,
        "expectation_anchor": isinstance(expectation, dict) and expectation.get("applicable") is True,
        "character_scene_objective_contract": has_character_performance,
        "relationship_emotion_arc": has_character_performance and len(participants) > 1,
        "sequence_directing_plan": True,
        "cut_decision_contract": True,
        "prompt_information_budget": True,
        "sound_directing_plan": True,
        "prop_functional_surface_contract": functional_surface_risk(subshot),
        "skin_tone_protection_contract": has_character_performance,
        "prop_lifecycle_contract": prop_lifecycle_risk(subshot),
        "perspective_scale_contract": len(visible) > 1,
        "lighting_topology_contract": has_character_performance,
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
    transition = temporal_transition_candidate(item)
    if transition.get("eligible"):
        reasons.append("temporal_transition")
    if reasons:
        # High risk is not one size.  Keep simple long-dialogue work reasonably
        # grouped, but reduce the blast radius for shots that often force
        # expensive full-batch retries.
        complex_reasons = {
            "fight_or_force",
            "prop_transfer",
            "shot_group",
            "high_reroll_risk",
            "temporal_transition",
        }
        capacity = 2 if any(reason in complex_reasons for reason in reasons) or len(reasons) > 1 else 3
        return {"tier": "high", "reasons": reasons, "batch_capacity": capacity, "review_scope": "full_scene_window"}
    is_non_character = bool(sources) and all(is_true_non_action_subshot(source) for source in sources if isinstance(source, dict))
    single_stable = len(unique_characters) <= 1 and not has_shot_group and not any(
        token in text for token in FIGHT_OR_FORCE_WORDS + PROP_TRANSFER_WORDS
    )
    if is_non_character:
        return {"tier": "light", "reasons": ["non_character_insert"], "batch_capacity": 10, "review_scope": "current_with_carryover"}
    if single_stable and (not has_dialogue or duration <= 6):
        return {"tier": "light", "reasons": ["single_stable" if not has_dialogue else "simple_dialogue"], "batch_capacity": 10, "review_scope": "current_with_carryover"}
    return {"tier": "standard", "reasons": ["normal_contract"], "batch_capacity": 6, "review_scope": "bounded_scene_window"}


def temporal_transition_candidate(item):
    """Return a source-grounded candidate for an in-model temporal transition.

    A memory reference or explicit event-driven state shift is eligible, never
    automatic: the Composer must either supply a bounded contract whose effect
    is derived from the source event or record why a normal cut is more truthful.
    """
    item = item if isinstance(item, dict) else {}
    explicit = item.get("temporal_transition_candidate")
    if isinstance(explicit, dict) and explicit.get("eligible"):
        return dict(explicit)
    texts = _transition_source_texts(item)
    text = "\n".join(texts)
    if any(marker in text for marker in EVENT_TRANSITION_MARKERS):
        return {
            "eligible": True, "kind": "story_event_transition",
            "source_trigger": _matching_source_texts(texts, EVENT_TRANSITION_MARKERS),
        }
    if any(marker in text for marker in MEMORY_MARKERS) and (
        any(marker in text for marker in MEMORY_EVENT_MARKERS) or "过去" in text or "从前" in text
    ):
        return {
            "eligible": True, "kind": "memory_flashback",
            "source_trigger": _first_matching_text(texts, MEMORY_MARKERS),
        }
    return {"eligible": False, "kind": "none", "source_trigger": ""}


def _transition_source_texts(item):
    texts = []
    sources = item.get("source_subshots")
    sources = sources if isinstance(sources, list) and sources else [item]
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in ("base_action", "source_text", "source_line", "source_summary", "core_action", "visual_intent"):
            value = str(source.get(key, "") or "").strip()
            if value:
                texts.append(value)
        for event in source.get("dialogue_events", []) or []:
            if isinstance(event, dict):
                value = str(event.get("text", "") or "").strip()
                if value:
                    texts.append(value)
    for event in item.get("dialogue_events", []) or []:
        if isinstance(event, dict):
            value = str(event.get("text", "") or "").strip()
            if value:
                texts.append(value)
    return texts


def _first_matching_text(texts, markers):
    return next((text for text in texts if any(marker in text for marker in markers)), "")


def _matching_source_texts(texts, markers):
    return "；".join(dict.fromkeys(text for text in texts if any(marker in text for marker in markers)))
