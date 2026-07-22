"""Shared Mode C v4 prompt contract helpers.

The model-facing prompt is intentionally small. Production metadata, negative
prompts, and validation traces live in sibling JSON fields and are never mixed
into ``full_prompt``.
"""

from __future__ import annotations

import re


PROMPT_LABELS = ["画面锁定", "镜头设计", "表演时间轴", "光照与声音"]
LEGACY_LABELS = [
    "全局声明",
    "人物站位与服装连续",
    "时长运镜场景目的",
    "时间分段叙事",
    "光照方案",
    "环境音设计",
    "负面提示词",
    "自包含验证",
]

FORBIDDEN_MODEL_TERMS = [
    "project_config",
    "costume_map",
    "dialogue_map",
    "director_pass",
    "dispatch packet",
    "packet",
    "source_path",
    "run_dir",
    "_batch_output_path",
    "output_path",
    "subshot_id",
    "auto补全",
    "自包含验证",
    "提示词自动注入",
    "管线级",
    "QA通过",
    "校验通过",
]

TIME_RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)秒")

WIDE_INVISIBLE_CUES = [
    "瞳孔", "虹膜", "眼睑", "鼻翼", "唇线", "眼神光", "眼轮匝肌", "咬肌",
]
MEDIUM_INVISIBLE_CUES = ["瞳孔", "虹膜", "鼻翼", "眼神光", "眼轮匝肌"]
FIGHT_LOCK_FIELDS = [
    "positions",
    "stance_weight",
    "weapon_prop_state",
    "injury_damage_state",
    "screen_direction",
    "axis_side",
]
ATTENTION_HANDOFF_STRATEGIES = {"rack_focus", "single_reframe", "actor_blocking"}
TENSION_INTENTS = {"neutral", "latent", "rising", "peak", "release"}
SPEECH_KINDS = {"台词", "OS", "OV"}
SPEAKER_VISIBILITIES = {"visible", "offscreen", "nonphysical"}
REROLL_RISK_LEVELS = {"low", "medium", "high", "reference_required"}
GENERIC_PERFORMANCE_TERMS = {
    "紧张", "震惊", "愤怒", "悲伤", "害怕", "自然", "自然反应", "有张力",
    "情绪复杂", "表情细腻", "保持状态", "微微变化", "很强烈",
    "感染力强", "观众共情", "共情感强", "画面感强", "情绪到位", "内心张力拉满",
}

CAMERA_MOVE_PATTERNS = {
    "push": r"推镜|推近|摄影机[^。；]{0,12}推进",
    "pull": r"拉镜|后拉|摄影机[^。；]{0,12}退远",
    "pan": r"摇镜|平摇|横摇|甩镜",
    "slide": r"横移|侧移|轨道移|滑轨|弧移",
    "track": r"跟拍|跟随摄影|摄影机跟随",
    "orbit": r"环绕|绕拍|绕行摄影",
    "vertical": r"升镜|降镜|升降镜头|摄影机[^。；]{0,12}(?:上升|下降)",
    "handheld": r"手持",
    "zoom": r"变焦|焦距[^。；]{0,12}(?:变化|拉长|缩短)",
}
FOCUS_TRANSFER_RE = re.compile(r"拉焦|焦点(?:从|由).{0,24}(?:转|移|交接|落到)|焦点转移|景深(?:从|由).{0,24}(?:转|移)")


def split_sections(text, labels=None):
    """Return exact top-level sections keyed by their Chinese labels."""
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    labels = labels or PROMPT_LABELS
    if not text:
        return {}
    joined = "|".join(re.escape(label) for label in labels)
    matches = list(re.finditer(rf"(?:^|\n\n)({joined})[：:]", text))
    sections = {}
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[start:end].strip()
    return sections


def normalize_v4_prompt(text):
    """Normalize paragraph spacing or upgrade a legacy Mode C v3 prompt."""
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    current = split_sections(text, PROMPT_LABELS)
    if all(label in current for label in PROMPT_LABELS):
        return "\n\n".join(f"{label}：{current[label]}" for label in PROMPT_LABELS)

    legacy = split_sections(text, LEGACY_LABELS)
    if not legacy:
        return text

    locked_parts = [legacy.get("全局声明", ""), legacy.get("人物站位与服装连续", "")]
    light_parts = [legacy.get("光照方案", ""), legacy.get("环境音设计", "")]
    upgraded = {
        "画面锁定": " ".join(part for part in locked_parts if part).strip(),
        "镜头设计": legacy.get("时长运镜场景目的", "").strip(),
        "表演时间轴": legacy.get("时间分段叙事", "").strip(),
        "光照与声音": " ".join(part for part in light_parts if part).strip(),
    }
    return "\n\n".join(f"{label}：{upgraded[label]}" for label in PROMPT_LABELS)


def legacy_negative_prompt(text):
    legacy = split_sections(text, LEGACY_LABELS)
    return legacy.get("负面提示词", "").strip()


def timeline_ranges(full_prompt):
    sections = split_sections(full_prompt, PROMPT_LABELS)
    return [(float(a), float(b)) for a, b in TIME_RANGE_RE.findall(sections.get("表演时间轴", ""))]


def timeline_issues(full_prompt, duration, tolerance=0.08):
    ranges = timeline_ranges(full_prompt)
    issues = []
    if not ranges:
        return ["表演时间轴缺少小数秒时间段"]
    if abs(ranges[0][0]) > tolerance:
        issues.append("时间轴必须从0.0秒开始")
    for idx, (start, end) in enumerate(ranges):
        if start >= end:
            issues.append(f"时间段{idx + 1}起止倒置")
        if idx:
            previous_end = ranges[idx - 1][1]
            if abs(start - previous_end) > tolerance:
                kind = "重叠" if start < previous_end else "断档"
                issues.append(f"时间段{idx}与{idx + 1}{kind}")
    try:
        target = float(duration or 0)
    except (TypeError, ValueError):
        target = 0
    if target <= 0:
        issues.append("镜头时长必须大于0")
    elif abs(ranges[-1][1] - target) > tolerance:
        issues.append(f"时间轴终点{ranges[-1][1]:g}秒与镜头时长{target:g}秒不一致")
    if len(ranges) > 3:
        issues.append("时间段超过3段；应拆分子镜头")
    return issues


def action_budget_limits(duration, is_fight=False, editorial_mode="continuous_take"):
    """Return maximum executable events for one generated clip."""
    try:
        seconds = float(duration or 0)
    except (TypeError, ValueError):
        seconds = 0
    if is_fight:
        contact_limit = 1 if seconds <= 6 else 2 if seconds <= 10 else 3
        return {
            "primary_action_count": 1,  # one uninterrupted causal choreography chain
            "emotion_turn_count": 1,
            "supporting_reaction_count": contact_limit,
            "physical_camera_move_count": 1,
            "editorial_response_count": 0,
        }
    return {
        "primary_action_count": 1 if seconds <= 6 else 2,
        "emotion_turn_count": 1,
        "supporting_reaction_count": 1 if seconds <= 6 else 2,
        "physical_camera_move_count": 1,
        "editorial_response_count": 0 if editorial_mode == "continuous_take" else (2 if seconds <= 6 else 3),
    }


def action_budget_issues(metadata, duration, is_fight=False):
    metadata = metadata if isinstance(metadata, dict) else {}
    budget = metadata.get("action_budget", {})
    if not isinstance(budget, dict):
        return ["qa_metadata.action_budget必须是对象"]
    editorial_mode = metadata.get("editorial_mode", "continuous_take")
    limits = action_budget_limits(duration, is_fight, editorial_mode)
    issues = []
    for key, limit in limits.items():
        value = budget.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            issues.append(f"action_budget.{key}必须是非负整数")
        elif value > limit:
            issues.append(f"action_budget.{key}={value}超过上限{limit}")
    beats = metadata.get("camera_beat_map", [])
    if editorial_mode == "motivated_sequence":
        if not isinstance(beats, list) or not 1 <= len(beats) <= 3:
            issues.append("motivated_sequence必须提供1-3项camera_beat_map")
        elif budget.get("editorial_response_count") != len(beats):
            issues.append("action_budget.editorial_response_count必须等于camera_beat_map数量")
    elif isinstance(beats, list) and beats:
        issues.append("continuous_take不得包含camera_beat_map")
    return issues


def performance_causality_issues(metadata, visible_characters=None):
    """Validate the structured performance-causality audit for character shots."""
    metadata = metadata if isinstance(metadata, dict) else {}
    causality = metadata.get("performance_causality")
    if visible_characters is None:
        roles = metadata.get("performance_priority", {})
        has_visible = bool(
            isinstance(roles, dict)
            and (
                str(roles.get("primary", "") or "").strip()
                or _string_list(roles.get("supporting", []))
                or _string_list(roles.get("background", []))
            )
        )
    else:
        has_visible = bool([char for char in visible_characters if str(char).strip()])

    if not has_visible and (
        causality is None
        or causality == {}
        or (
            isinstance(causality, dict)
            and not any(
                str(value).strip() if not isinstance(value, list) else bool(value)
                for value in causality.values()
            )
        )
    ):
        return []
    if not isinstance(causality, dict):
        return ["有人物镜头必须提供qa_metadata.performance_causality"] if has_visible else [
            "qa_metadata.performance_causality必须是对象"
        ]

    issues = []
    if causality.get("tension_intent") not in TENSION_INTENTS:
        issues.append("performance_causality.tension_intent只允许neutral/latent/rising/peak/release")
    order = causality.get("response_order")
    if not isinstance(order, list) or not order or any(not str(stage).strip() for stage in order):
        issues.append("performance_causality.response_order必须是非空有序文本数组")
    for field in ("trigger", "physical_logic", "motion_boundary", "hold_strategy", "end_residue"):
        if len(str(causality.get(field, "") or "").strip()) < 2:
            issues.append(f"performance_causality.{field}不能为空")
    return issues


def performance_contract_issues(metadata, full_prompt="", visible_characters=None):
    """Validate the integrated expression/body/camera/scene tension contract."""
    metadata = metadata if isinstance(metadata, dict) else {}
    visible = _string_list(visible_characters or [])
    has_visible = bool(visible)
    contract = metadata.get("performance_contract")
    if not has_visible and contract in (None, {}):
        return []
    if not isinstance(contract, dict):
        return ["有人物镜头必须提供qa_metadata.performance_contract"]

    issues = []
    required = (
        "tension_intent",
        "trigger_event",
        "trigger_time",
        "primary_expression",
        "primary_body_action",
        "eye_focus",
        "reaction_delay",
        "voice_or_breath_control",
        "viewer_empathy_anchor",
        "readable_image_moment",
        "suppression_or_release",
        "camera_pressure",
        "scene_pressure",
        "end_residue",
    )
    for field in required:
        if len(str(contract.get(field, "") or "").strip()) < 2:
            issues.append(f"performance_contract.{field}不能为空")
    if contract.get("tension_intent") not in TENSION_INTENTS:
        issues.append("performance_contract.tension_intent只允许neutral/latent/rising/peak/release")
    trigger_time = str(contract.get("trigger_time", "") or "")
    if trigger_time and not re.search(r"\d+(?:\.\d+)?秒|无明确时点|N/A", trigger_time):
        issues.append("performance_contract.trigger_time必须写秒点，或明确无明确时点/N/A")
    for field in (
        "primary_expression",
        "primary_body_action",
        "eye_focus",
        "reaction_delay",
        "voice_or_breath_control",
        "viewer_empathy_anchor",
        "readable_image_moment",
        "suppression_or_release",
        "camera_pressure",
        "scene_pressure",
        "end_residue",
    ):
        value = str(contract.get(field, "") or "").strip()
        if value in GENERIC_PERFORMANCE_TERMS or len(value) < 4:
            issues.append(f"performance_contract.{field}过于抽象，必须写景别可见的具体控制")

    sections = split_sections(full_prompt, PROMPT_LABELS)
    timeline = sections.get("表演时间轴", "")
    camera_text = sections.get("镜头设计", "") + "\n" + timeline
    scene_text = sections.get("画面锁定", "") + "\n" + sections.get("光照与声音", "")
    for field in (
        "primary_expression",
        "primary_body_action",
        "eye_focus",
        "voice_or_breath_control",
        "viewer_empathy_anchor",
        "readable_image_moment",
        "suppression_or_release",
        "end_residue",
    ):
        if not _fragment_grounded(contract.get(field, ""), timeline):
            issues.append(f"performance_contract.{field}未落实到表演时间轴")
    if not _fragment_grounded(contract.get("camera_pressure", ""), camera_text):
        issues.append("performance_contract.camera_pressure未落实到镜头设计或表演时间轴")
    if not _fragment_grounded(contract.get("scene_pressure", ""), scene_text):
        issues.append("performance_contract.scene_pressure未落实到画面锁定或光照与声音")
    return issues


def continuity_contract_issues(metadata, full_prompt="", visible_characters=None):
    """Validate cross-shot continuity anchors for positions, eyelines, props, and light."""
    metadata = metadata if isinstance(metadata, dict) else {}
    visible = _string_list(visible_characters or [])
    contract = metadata.get("continuity_contract")
    if not visible and contract in (None, {}):
        return []
    if not isinstance(contract, dict):
        return ["有人物镜头必须提供qa_metadata.continuity_contract"]
    issues = []
    required = (
        "start_anchor",
        "end_anchor",
        "position_continuity",
        "eyeline_continuity",
        "prop_state",
        "lighting_continuity",
        "next_carryover",
    )
    for field in required:
        if len(str(contract.get(field, "") or "").strip()) < 3:
            issues.append(f"continuity_contract.{field}不能为空")
    if not _fragment_grounded(contract.get("end_anchor", ""), full_prompt):
        issues.append("continuity_contract.end_anchor必须能在模型提示词中找到可见落幅")
    if not _fragment_grounded(contract.get("next_carryover", ""), full_prompt):
        issues.append("continuity_contract.next_carryover必须落实为可承接的画面残留")
    return issues


def reroll_control_issues(metadata, generation_control=None, visible_characters=None):
    """Validate reroll-risk acknowledgement and mitigation before export."""
    metadata = metadata if isinstance(metadata, dict) else {}
    visible = _string_list(visible_characters or [])
    control = generation_control if isinstance(generation_control, dict) else {}
    reroll = metadata.get("reroll_control")
    if not visible and reroll in (None, {}):
        return []
    if not isinstance(reroll, dict):
        return ["有人物镜头必须提供qa_metadata.reroll_control"]

    issues = []
    risk = reroll.get("risk_level")
    if risk not in REROLL_RISK_LEVELS:
        issues.append("reroll_control.risk_level只允许low/medium/high/reference_required")
    for field in ("identity_anchor", "motion_anchor", "scene_anchor", "camera_anchor", "risk_reason"):
        if len(str(reroll.get(field, "") or "").strip()) < 4:
            issues.append(f"reroll_control.{field}不能为空或过于空泛")
    mitigation = reroll.get("mitigation_steps")
    if not isinstance(mitigation, list) or len([step for step in mitigation if str(step).strip()]) < 2:
        issues.append("reroll_control.mitigation_steps至少需要两条具体降抽卡策略")
    if not isinstance(reroll.get("needs_reference"), bool):
        issues.append("reroll_control.needs_reference必须是布尔值")

    mode = control.get("mode")
    assets = control.get("reference_assets") if isinstance(control.get("reference_assets"), list) else []
    tension = (
        metadata.get("performance_contract", {}).get("tension_intent")
        if isinstance(metadata.get("performance_contract"), dict)
        else metadata.get("performance_causality", {}).get("tension_intent")
        if isinstance(metadata.get("performance_causality"), dict)
        else ""
    )
    if visible and mode == "t2v" and risk == "low":
        issues.append("T2V人物镜不得把reroll_control.risk_level标为low")
    if risk == "reference_required" and reroll.get("needs_reference") is not True:
        issues.append("reference_required风险必须标记needs_reference=true")
    if mode in ("i2v", "r2v") and not assets:
        issues.append(f"{mode}模式缺少reference_assets，无法兑现降抽卡控制")
    if mode == "t2v" and tension in ("rising", "peak") and reroll.get("needs_reference") is not True:
        issues.append("T2V rising/peak人物镜必须标记needs_reference=true，提示需要参考图/动作参考降低抽卡")
    return issues


def dialogue_event_issues(
    metadata,
    expected_events=None,
    visible_characters=None,
    full_prompt="",
    audio_enabled=None,
    duration=None,
):
    """Validate dialogue/OS/OV identity, timing, performance, and prompt placement."""
    metadata = metadata if isinstance(metadata, dict) else {}
    refs = _string_list(metadata.get("dialogue_refs", []))
    events = metadata.get("dialogue_events")
    if not refs and events in (None, []):
        return []
    if not isinstance(events, list):
        return ["qa_metadata.dialogue_events必须是数组"]

    issues = []
    event_refs = [str(event.get("ref", "") or "").strip() for event in events if isinstance(event, dict)]
    if len(event_refs) != len(events):
        issues.append("dialogue_events每项必须是对象")
    if event_refs != refs:
        issues.append("dialogue_events必须按dialogue_refs顺序一一覆盖")

    expected_was_provided = expected_events is not None
    expected = expected_events if isinstance(expected_events, list) else []
    expected_identity = [
        (
            str(event.get("ref", "") or ""),
            str(event.get("kind", "") or ""),
            str(event.get("speaker", "") or ""),
            str(event.get("text", "") or ""),
        )
        for event in expected if isinstance(event, dict)
    ]
    actual_identity = [
        (
            str(event.get("ref", "") or ""),
            str(event.get("kind", "") or ""),
            str(event.get("speaker", "") or ""),
            str(event.get("text", "") or ""),
        )
        for event in events if isinstance(event, dict)
    ]
    if expected_was_provided and refs and not expected:
        issues.append("Director缺少锁定的dialogue_events源记录")
    elif expected and actual_identity != expected_identity:
        issues.append("dialogue_events的ref/kind/speaker/text与Director原文不一致")

    sections = split_sections(full_prompt, PROMPT_LABELS)
    timeline = sections.get("表演时间轴", "")
    visible = set(_string_list(visible_characters or [])) if visible_characters is not None else set()
    try:
        total_duration = float(duration or 0)
    except (TypeError, ValueError):
        total_duration = 0

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        prefix = f"dialogue_events[{index}]"
        ref = str(event.get("ref", "") or "").strip()
        kind = str(event.get("kind", "") or "").strip()
        speaker = str(event.get("speaker", "") or "").strip()
        line = str(event.get("text", "") or "")
        visibility = str(event.get("speaker_visibility", "") or "").strip()
        facial = str(event.get("facial_state", "") or "").strip()
        body = str(event.get("body_state", "") or "").strip()
        delivery = str(event.get("delivery", "") or "").strip()
        lip_sync = event.get("lip_sync")

        if not ref:
            issues.append(f"{prefix}.ref不能为空")
        if kind not in SPEECH_KINDS:
            issues.append(f"{prefix}.kind只允许台词/OS/OV")
        if not speaker:
            issues.append(f"{prefix}.speaker不能为空")
        if not line:
            issues.append(f"{prefix}.text不能为空")
        if visibility not in SPEAKER_VISIBILITIES:
            issues.append(f"{prefix}.speaker_visibility只允许visible/offscreen/nonphysical")
        if len(facial) < 2:
            issues.append(f"{prefix}.facial_state不能为空")
        if len(body) < 2:
            issues.append(f"{prefix}.body_state不能为空")
        if len(delivery) < 2:
            issues.append(f"{prefix}.delivery不能为空")

        match = re.fullmatch(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)秒", str(event.get("time_range", "") or "").strip())
        if not match:
            issues.append(f"{prefix}.time_range必须是连续小数秒范围")
        else:
            start, end = float(match.group(1)), float(match.group(2))
            if start >= end or start < 0 or (total_duration > 0 and end > total_duration + 0.08):
                issues.append(f"{prefix}.time_range超出镜头或起止倒置")

        if visibility == "visible":
            if visible and speaker not in visible:
                issues.append(f"{prefix}.speaker标为visible但不在可见人物中")
            if facial and facial not in timeline:
                issues.append(f"{prefix}.facial_state未落实到表演时间轴")
            if body and body not in timeline:
                issues.append(f"{prefix}.body_state未落实到表演时间轴")
        elif visibility in ("offscreen", "nonphysical"):
            if not facial.startswith("N/A") or not body.startswith("N/A"):
                issues.append(f"{prefix}不可见说话者的facial_state/body_state必须明确写N/A及原因")

        expected_lip_sync = kind == "台词" and visibility == "visible"
        if lip_sync is not expected_lip_sync:
            issues.append(f"{prefix}.lip_sync与台词类型或说话者可见性不一致")

        if audio_enabled is True:
            if line and full_prompt.count(line) != 1:
                issues.append(f"{prefix}.text必须逐字且只出现一次")
            label = f"{speaker}（{kind}）"
            if label not in timeline:
                issues.append(f"{prefix}必须在表演时间轴明确人物与台词/OS类型")
            if delivery and delivery not in timeline:
                issues.append(f"{prefix}.delivery未落实到表演时间轴")
            if expected_lip_sync and "口型" not in timeline:
                issues.append(f"{prefix}可见对白缺少口型同步说明")
            if kind in ("OS", "OV") and not any(token in timeline for token in ("口型闭合", "无口型同步", "不驱动口型")):
                issues.append(f"{prefix}的OS/OV缺少无口型同步说明")
        elif audio_enabled is False and line and line in full_prompt:
            issues.append(f"{prefix}.text在原生音频关闭时不得进入full_prompt")
    return issues


def attention_handoff_issues(metadata, full_prompt):
    """Validate an optional, single causal attention handoff."""
    metadata = metadata if isinstance(metadata, dict) else {}
    handoff = metadata.get("attention_handoff")
    if handoff is None:
        return []
    if not isinstance(handoff, dict):
        return ["qa_metadata.attention_handoff必须是对象"]

    issues = []
    if handoff.get("mode") != "causal_handoff":
        issues.append("attention_handoff.mode必须是causal_handoff")
    if handoff.get("count") != 1:
        issues.append("attention_handoff.count必须精确为1")
    strategy = handoff.get("strategy")
    if strategy not in ATTENTION_HANDOFF_STRATEGIES:
        issues.append("attention_handoff.strategy只允许rack_focus/single_reframe/actor_blocking")
    for field in ("from", "to", "trigger", "end_composition"):
        if not str(handoff.get(field, "") or "").strip():
            issues.append(f"attention_handoff.{field}不能为空")
    if str(handoff.get("from", "")).strip() == str(handoff.get("to", "")).strip():
        issues.append("attention_handoff.from与to不能相同")

    roles = metadata.get("performance_priority", {})
    if isinstance(roles, dict):
        assigned = set(
            ([str(roles.get("primary", "")).strip()] if str(roles.get("primary", "")).strip() else [])
            + _string_list(roles.get("supporting", []))
            + _string_list(roles.get("background", []))
        )
        for field in ("from", "to"):
            value = str(handoff.get(field, "") or "").strip()
            if value and value not in assigned:
                issues.append(f"attention_handoff.{field}不在表演优先级角色中")

    design = split_sections(full_prompt, PROMPT_LABELS).get("镜头设计", "")
    moves = camera_move_types(design)
    has_focus_transfer = bool(FOCUS_TRANSFER_RE.search(design))
    if strategy == "rack_focus":
        if moves:
            issues.append("rack_focus策略要求摄影机固定，不能叠加物理运镜或变焦")
        if not has_focus_transfer:
            issues.append("rack_focus策略必须在镜头设计中写一次可执行拉焦")
    elif strategy == "single_reframe":
        if len(moves) != 1 or not (moves & {"pan", "slide", "orbit"}):
            issues.append("single_reframe策略必须且只能使用一次摇/移/弧移重构图")
        if has_focus_transfer or "zoom" in moves:
            issues.append("single_reframe策略不能叠加拉焦或变焦")
    elif strategy == "actor_blocking":
        if moves or has_focus_transfer:
            issues.append("actor_blocking策略要求机位与焦点稳定，只由演员走位改变画面权重")

    return issues


def camera_competition_issues(full_prompt, editorial_mode="continuous_take"):
    """Reject competing controls in a take, while preserving motivated editorial beats."""
    sections = split_sections(full_prompt, PROMPT_LABELS)
    design = sections.get("镜头设计", "")
    timeline = sections.get("表演时间轴", "")
    issues = []
    moves = camera_move_types(design)
    if editorial_mode != "motivated_sequence" and len(moves) > 1:
        issues.append("镜头设计叠加多种主要运镜：" + "/".join(sorted(moves)))
    has_focus_transfer = bool(FOCUS_TRANSFER_RE.search(design))
    if editorial_mode != "motivated_sequence" and has_focus_transfer and moves:
        issues.append("物理运镜/变焦与拉焦同时叠加，形成竞争控制")
    if re.search(r"(?:再|再次|重新).{0,12}(?:拉焦|焦点.{0,6}(?:转|移|回))|[^。；]{0,12}→[^。；]{0,12}→", design + timeline):
        issues.append("同一镜头发生反复注意力抢焦")
    if ("聚焦" in design or "聚焦" in timeline) and not re.search(
        r"三分位|画面(?:左|右|中央|中心)|占画面|前景|中景|后景|拉焦|焦点(?:从|由)|平摇|横摇|横移|侧移|弧移|走位|落幅",
        design + timeline,
    ):
        issues.append("只写聚焦主体但缺少可执行构图、焦点、走位或落幅")
    return issues


def camera_move_types(design):
    design = str(design or "")
    moves = {name for name, pattern in CAMERA_MOVE_PATTERNS.items() if re.search(pattern, design)}
    # “横移跟拍” describes one lateral tracking trajectory, not two competing
    # camera moves. Preserve track as the canonical category.
    if moves.issuperset({"slide", "track"}) and re.search(r"(?:横移|侧移|轨道移|滑轨).{0,6}跟拍", design):
        moves.discard("slide")
    return moves


def fight_continuity_issues(metadata, duration):
    """Validate one continuous-take fight chain and its structured handoff."""
    metadata = metadata if isinstance(metadata, dict) else {}
    continuity = metadata.get("fight_continuity")
    if not isinstance(continuity, dict):
        return ["打斗镜必须提供qa_metadata.fight_continuity"]
    issues = []
    if continuity.get("mode") != "continuous_take":
        issues.append("fight_continuity.mode必须是continuous_take")
    for field in ("sequence_id", "clip_id"):
        if not str(continuity.get(field, "") or "").strip():
            issues.append(f"fight_continuity.{field}不能为空")
    participants = continuity.get("participants")
    if not isinstance(participants, list) or len([p for p in participants if str(p).strip()]) < 2:
        issues.append("fight_continuity.participants必须至少包含两名角色")
    beats = continuity.get("contact_beats")
    if not isinstance(beats, list) or not beats:
        issues.append("fight_continuity.contact_beats必须是非空数组")
        beats = []
    try:
        seconds = float(duration or 0)
    except (TypeError, ValueError):
        seconds = 0
    max_beats = 1 if seconds <= 6 else 2 if seconds <= 10 else 3
    if seconds > 15:
        issues.append("连续打斗生成片段超过15秒；必须拆成可续接片段")
    if len(beats) > max_beats:
        issues.append(f"fight_continuity.contact_beats={len(beats)}超过当前时长上限{max_beats}")
    for index, beat in enumerate(beats):
        if not isinstance(beat, dict):
            issues.append(f"fight_continuity.contact_beats[{index}]必须是对象")
            continue
        for field in (
            "time_range", "attacker", "defender", "attack_path",
            "contact_point", "force_direction", "result",
        ):
            if not str(beat.get(field, "") or "").strip():
                issues.append(f"fight_continuity.contact_beats[{index}].{field}不能为空")
    for lock_name in ("start_lock", "end_lock"):
        lock = continuity.get(lock_name)
        if not isinstance(lock, dict):
            issues.append(f"fight_continuity.{lock_name}必须是对象")
            continue
        for field in FIGHT_LOCK_FIELDS:
            if not str(lock.get(field, "") or "").strip():
                issues.append(f"fight_continuity.{lock_name}.{field}不能为空")
    return issues


def fight_transition_issues(previous_metadata, current_metadata):
    """Require exact end-lock/start-lock inheritance within one fight sequence."""
    previous = previous_metadata.get("fight_continuity", {}) if isinstance(previous_metadata, dict) else {}
    current = current_metadata.get("fight_continuity", {}) if isinstance(current_metadata, dict) else {}
    if not isinstance(previous, dict) or not isinstance(current, dict):
        return []
    previous_sequence = str(previous.get("sequence_id", "") or "")
    current_sequence = str(current.get("sequence_id", "") or "")
    if not previous_sequence or previous_sequence != current_sequence:
        return []
    end_lock = previous.get("end_lock")
    start_lock = current.get("start_lock")
    if isinstance(end_lock, dict) and isinstance(start_lock, dict) and end_lock != start_lock:
        return ["同一打斗序列中，上镜end_lock必须与本镜start_lock完全相同"]
    return []


def role_partition_issues(metadata, visible_characters):
    metadata = metadata if isinstance(metadata, dict) else {}
    roles = metadata.get("performance_priority", {})
    if not isinstance(roles, dict):
        return ["qa_metadata.performance_priority必须是对象"]
    primary = str(roles.get("primary", "") or "").strip()
    supporting = _string_list(roles.get("supporting", []))
    background = _string_list(roles.get("background", []))
    assigned = ([primary] if primary else []) + supporting + background
    issues = []
    if len(assigned) != len(set(assigned)):
        issues.append("角色不能同时属于多个表演优先级")
    visible = [str(char).strip() for char in visible_characters if str(char).strip()]
    if visible and not primary:
        issues.append("有人物镜头必须指定一个primary角色")
    if set(assigned) != set(visible):
        missing = sorted(set(visible) - set(assigned))
        extra = sorted(set(assigned) - set(visible))
        if missing:
            issues.append("未分配表演优先级：" + "、".join(missing))
        if extra:
            issues.append("优先级包含不可见角色：" + "、".join(extra))
    return issues


def visibility_issues(full_prompt, shot_size):
    sections = split_sections(full_prompt, PROMPT_LABELS)
    performance = sections.get("表演时间轴", "")
    if shot_size in ("全景", "大远景", "远景"):
        cues = WIDE_INVISIBLE_CUES
    elif shot_size == "中景":
        cues = MEDIUM_INVISIBLE_CUES
    else:
        cues = []
    hits = [cue for cue in cues if cue in performance]
    return (["景别不可见细节：" + "、".join(hits)] if hits else [])


def prompt_length_issues(full_prompt, duration):
    length = len(str(full_prompt or ""))
    issues = []
    if length < 120:
        issues.append(f"模型提示词仅{length}字，缺少可执行信息")
    if length > 1100:
        issues.append(f"模型提示词{length}字，超过v4硬上限1100字；应拆镜")
    return issues


def _string_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in re.split(r"[;；,，、/]+", value) if part.strip()]
    return []


def _fragment_grounded(value, text):
    """Return true when a concrete phrase from value appears in text."""
    value = str(value or "").strip()
    text = str(text or "")
    if not value:
        return False
    if value in text:
        return True
    fragments = [
        fragment.strip()
        for fragment in re.split(r"[，,；;。！？、\s]+", value)
        if len(fragment.strip()) >= 4 and fragment.strip() not in GENERIC_PERFORMANCE_TERMS
    ]
    return any(fragment in text for fragment in fragments[:4])
