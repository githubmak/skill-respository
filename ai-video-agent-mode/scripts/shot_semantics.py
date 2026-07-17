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

RENDER_ANCHOR_FIELDS = ["visual_intent", "image_subject", "atmosphere"]


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
    """A non-action subshot can omit base_action only with a render anchor."""
    if subshot.get("dialogue_refs"):
        return False
    if subshot.get("characters"):
        return False
    return is_declared_non_action(subshot) and bool(render_anchor(subshot))


def requires_base_action(subshot):
    """Return True when missing base_action would leave downstream agents blind."""
    if subshot.get("base_action"):
        return False
    return not is_true_non_action_subshot(subshot)


def requires_characters(base_action, dialogue_refs, shot_size, shot_type):
    """Return True when an empty characters list is likely an omission."""
    if dialogue_refs:
        return True
    blob = " ".join(str(x) for x in [base_action, shot_size, shot_type]).lower()
    if any(token.lower() in blob for token in NON_ACTION_TYPES):
        return False
    if any(word in str(base_action) for word in NON_CHARACTER_WORDS):
        return False
    return any(word in str(base_action) for word in CHARACTER_ACTION_WORDS)

