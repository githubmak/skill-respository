"""Compact, context-aware negative prompts for the current contract.

Only undesirable visual/audio concepts belong here. Positive imperatives such as
``禁止角色静止`` are deliberately excluded because they compete with restrained
performance and can be interpreted inconsistently by generation platforms.
"""

PLACEHOLDER = "{{NEGATIVE_PROMPT_AUTO_INJECT}}"

BASE_NEGATIVE = (
    "肢体畸形，手部扭曲，五官变形，人物变脸漂移，帧间频闪，"
    "光影骤变，物体凭空消失，肢体穿插，口型错乱，多余肢体，"
    "画面撕裂，水印文字，画风突变，过度曝光，人物闪烁，"
    "鬼影重叠，穿模，物体悬浮，动作抽搐，背景扭曲，过度运动模糊，"
    "人物忽高忽低，体型动态变化，腿部拉长缩短，无因尺度跳变，"
    "无因浮空，透视错乱，广角畸变"
)

GROUNDED_NEGATIVE = "站立时无因浮空 脚底脱离支撑面 接触阴影缺失"
LOCOMOTION_NEGATIVE = "脚底打滑 步幅跳变 身体无位移滑行"
SUPPORTED_NEGATIVE = "身体脱离承载面 支撑点漂移 双腿异常拉伸"
AIRBORNE_NEGATIVE = "腾空轨迹断裂 空中无因悬停 落地无支撑 身体比例跳变"

AIRBORNE_TERMS = ("轻功", "腾空", "跃起", "跳起", "飞行", "凌空", "被击飞", "坠落", "下落", "起跳", "落地", "翻越")
SUPPORTED_TERMS = ("坐下", "坐在", "坐着", "靠坐", "躺", "卧", "伏", "趴", "倒地", "沙发", "座椅", "床上", "骑马")
LOCOMOTION_TERMS = ("行走", "走向", "走近", "跑", "奔", "追逐", "冲向", "上楼", "下楼")
GROUNDED_TERMS = ("站立", "站定", "站在", "停住", "蹲下", "跪下")

MULTI_CHARACTER_NEGATIVE = (
    "人物瞬移 左右位置无理由翻转 角色间距离突变 人物重叠融合 "
    "前后景遮挡错误 接触阴影缺失 主体抠图感"
)

DIALOGUE_NEGATIVE = (
    "口型错位 非说话角色同步口型 嘴部抽搐 台词停顿时突变表情"
)

REFERENCE_NEGATIVE = (
    "主体身份漂移 人物换脸 服装漂移 发型漂移 帧间身份突变"
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
    support_mode="neutral",
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
    support_negative = {
        "grounded": GROUNDED_NEGATIVE,
        "locomotion": LOCOMOTION_NEGATIVE,
        "supported": SUPPORTED_NEGATIVE,
        "airborne": AIRBORNE_NEGATIVE,
    }.get(support_mode)
    if support_negative:
        parts.append(support_negative)
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
    has_reference = False
    dialogue_refs = metadata.get("dialogue_refs", [])
    return build_negative_prompt(
        is_fight=is_fight_context(
            item.get("scene_type", ""), item.get("shot_type", ""), item.get("full_prompt", "")
        ),
        multi_character=len(set(str(p) for p in people if p)) >= 2,
        has_dialogue=bool(dialogue_refs),
        has_reference=has_reference,
        support_mode=support_mode_for_text(item.get("full_prompt", "")),
    )


def is_fight_context(*values):
    text = " ".join(str(value or "") for value in values)
    lower = text.lower()
    return any(keyword in lower for keyword in FIGHT_KEYWORDS[:2]) or any(
        keyword in text for keyword in FIGHT_KEYWORDS[2:]
    )


def support_mode_for_text(*values):
    text = " ".join(str(value or "") for value in values)
    for mode, terms in (
        ("airborne", AIRBORNE_TERMS),
        ("supported", SUPPORTED_TERMS),
        ("locomotion", LOCOMOTION_TERMS),
        ("grounded", GROUNDED_TERMS),
    ):
        if any(term in text for term in terms):
            return mode
    return "neutral"


def required_keywords(
    is_fight=False,
    multi_character=False,
    has_dialogue=False,
    has_reference=False,
    support_mode="neutral",
):
    return build_negative_prompt(
        is_fight=is_fight,
        multi_character=multi_character,
        has_dialogue=has_dialogue,
        has_reference=has_reference,
        support_mode=support_mode,
    ).split()
