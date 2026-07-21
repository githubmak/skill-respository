"""Compact, context-aware negative prompts for Mode C v4.

Only undesirable visual/audio concepts belong here. Positive imperatives such as
``禁止角色静止`` are deliberately excluded because they compete with restrained
performance and can be interpreted inconsistently by generation platforms.
"""

PLACEHOLDER = "{{NEGATIVE_PROMPT_AUTO_INJECT}}"

BASE_NEGATIVE = (
    "肢体畸形，手部扭曲，五官变形，人物变脸漂移，帧间频闪，"
    "光影骤变，物体凭空消失，肢体穿插，口型错乱，多余肢体，"
    "画面撕裂，水印文字，画风突变，过度曝光，人物闪烁，"
    "鬼影重叠，穿模，物体悬浮，动作抽搐，背景扭曲，过度运动模糊"
)

MULTI_CHARACTER_NEGATIVE = (
    "人物瞬移 左右位置无理由翻转 角色间距离突变 人物重叠融合 "
    "前后景遮挡错误 接触阴影缺失 主体抠图感"
)

DIALOGUE_NEGATIVE = (
    "口型错位 非说话角色同步口型 嘴部抽搐 台词停顿时突变表情"
)

REFERENCE_NEGATIVE = (
    "参考主体偏移 参考人物换脸 服装漂移 发型漂移 首尾帧身份突变"
)

FIGHT_NEGATIVE = (
    "空气拳，打击不命中，接触面无反馈，受力方向错误，肢体穿透，"
    "攻防节奏脱节，打击后无受力反应，关节反向弯曲，四肢拉伸，"
    "多人打击焦点混乱，高速动作残影，肢体错位"
)

FIGHT_KEYWORDS = (
    "fight", "combat", "打斗", "搏斗", "格斗", "追逐", "攻击", "挥拳",
    "踢击", "刀剑", "交锋", "冲撞",
)


def build_negative_prompt(
    is_fight=False,
    multi_character=False,
    has_dialogue=False,
    has_reference=False,
):
    parts = [BASE_NEGATIVE]
    if multi_character:
        parts.append(MULTI_CHARACTER_NEGATIVE)
    if has_dialogue:
        parts.append(DIALOGUE_NEGATIVE)
    if has_reference:
        parts.append(REFERENCE_NEGATIVE)
    if is_fight:
        parts.append(FIGHT_NEGATIVE)
    return " ".join(parts)


def build_negative_prompt_for_item(item):
    item = item if isinstance(item, dict) else {}
    metadata = item.get("qa_metadata", {}) if isinstance(item.get("qa_metadata"), dict) else {}
    roles = metadata.get("performance_priority", {}) if isinstance(metadata.get("performance_priority"), dict) else {}
    people = []
    primary = roles.get("primary")
    if primary:
        people.append(primary)
    for key in ("supporting", "background"):
        value = roles.get(key, [])
        if isinstance(value, list):
            people.extend(value)
    refs = item.get("generation_control", {})
    refs = refs if isinstance(refs, dict) else {}
    assets = refs.get("reference_assets", [])
    has_reference = bool(assets) or refs.get("mode") in ("i2v", "r2v")
    dialogue_refs = metadata.get("dialogue_refs", [])
    return build_negative_prompt(
        is_fight=is_fight_context(
            item.get("scene_type", ""), item.get("shot_type", ""), item.get("full_prompt", "")
        ),
        multi_character=len(set(str(p) for p in people if p)) >= 2,
        has_dialogue=bool(dialogue_refs),
        has_reference=has_reference,
    )


def is_fight_context(*values):
    text = " ".join(str(value or "") for value in values)
    lower = text.lower()
    return any(keyword in lower for keyword in FIGHT_KEYWORDS[:2]) or any(
        keyword in text for keyword in FIGHT_KEYWORDS[2:]
    )


def required_keywords(
    is_fight=False,
    multi_character=False,
    has_dialogue=False,
    has_reference=False,
):
    return build_negative_prompt(
        is_fight=is_fight,
        multi_character=multi_character,
        has_dialogue=has_dialogue,
        has_reference=has_reference,
    ).split()
