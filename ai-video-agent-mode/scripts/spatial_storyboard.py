"""Derive image-generation prompts for high-risk character blocking references.

These prompts are separate production aids.  They are never appended to the
Jimeng T2V prompt and never claim to be reference assets for T2V generation.
"""

import re

from modec_v4 import PROMPT_LABELS, split_sections


SPATIAL_ACTION_RE = re.compile(r"接近|走向|进入|离开|让开|递给|交给|接住|阻挡|擦肩|绕过|跟随|转身|落步|换位|站位")
CAMERA_RISK_RE = re.compile(r"硬切|重构图|跟拍|横移|环绕|拉焦|焦点转移")
SCREEN_SIDE_RE = re.compile(r"画(?:面)?(?:左|右|中)|前景|中景|后景")
TRANSFER_RE = re.compile(r"外套|手机|文件|杯|包|钥匙|武器|道具|领口")


def build_spatial_storyboard_reference(task, planned=None, canvas="16:9", visual_style=""):
    """Return a map + blocking-board prompt when spatial risk warrants it."""
    task = task if isinstance(task, dict) else {}
    planned = planned if isinstance(planned, dict) else {}
    prompt = str(task.get("full_prompt", "") or "")
    metadata = task.get("qa_metadata", {}) if isinstance(task.get("qa_metadata"), dict) else {}
    sections = split_sections(prompt, PROMPT_LABELS)
    spatial = _compact(sections.get("主体与空间锁定", ""), 420)
    timeline = _compact(sections.get("子镜头组", ""), 700)
    continuity = metadata.get("continuity_contract", {}) if isinstance(metadata.get("continuity_contract"), dict) else {}
    state_change = continuity.get("state_change") is True or bool(continuity.get("state_transitions"))
    screen_hits = len(set(SCREEN_SIDE_RE.findall(prompt)))
    action = bool(SPATIAL_ACTION_RE.search(prompt))
    camera = bool(CAMERA_RISK_RE.search(prompt))
    transfer = bool(TRANSFER_RE.search(prompt)) and bool(re.search(r"交|递|接|披|取|放|拿", prompt))
    speakers = _speakers(metadata)
    multi_party = len(speakers) >= 2 or (screen_hits >= 2 and bool(re.search(r"人物|角色|两人|双方|队列|随行", prompt)))

    score = (4 if state_change else 0) + (3 if transfer else 0) + (2 if multi_party else 0) + (2 if action else 0) + (2 if camera else 0) + (1 if screen_hits >= 2 else 0)
    if score < 3:
        return None
    priority = "必需" if score >= 6 else "建议"
    reasons = []
    if state_change:
        reasons.append("人物或关键道具发生状态变化")
    if transfer:
        reasons.append("存在道具/服装交接风险")
    if multi_party:
        reasons.append("多人屏幕空间关系需要锁定")
    if action:
        reasons.append("存在可见走位或接近动作")
    if camera:
        reasons.append("镜头切换或重构图需要承接")
    if screen_hits >= 2:
        reasons.append("出现多层景深或左右站位")

    scene = str(planned.get("scene", "当前场景") or "当前场景")
    character_text = "、".join(speakers) if speakers else "主镜头中已锁定的可见人物"
    style = (visual_style + "，") if visual_style else ""
    map_prompt = (
        f"{canvas}画幅，{style}垂直正交纯上帝俯视图，orthographic top-down plan view，no perspective horizon。"
        f"为《{scene}》制作AI视频连续性空间调度图，使用用户提供的场景图作为真实场景基底、人物图仅用于人物身份和服装核对；"
        f"固定空间锚点：{spatial}。可见人物：{character_text}。"
        f"把人物起点与终点画成俯视全身剪影，蓝色/黄色虚线分别标注人物路径，S/E圆点和箭头明确方向；"
        f"按镜头节拍布置：{timeline}。摄影机用白色轨道或固定机位视锥标注，保持人物屏幕左右、道具接触和通行动线一致；"
        "右侧留出不遮挡主体的简洁图例，中文标签清晰，作为生成视频前的人物站位与空间连续性参考。"
    )
    blocking_prompt = (
        f"{canvas}横向电影分镜图，{style}使用用户提供的场景图和人物图保持场景、人物身份与服装一致。"
        f"为《{scene}》绘制一张人物站位与姿态控制关键帧：{spatial}。"
        f"人物为{character_text}；严格保持画面左右、前中后景距离、脚底接触地面、身体朝向、视线对象与关键道具归属。"
        f"关键动作与姿态：{timeline}。画面只保留一个明确视觉主体，其他人物按既定前景/中景/后景承担空间锚点；"
        "全身或至少膝上可读，手部和道具接触关系准确，人物不漂浮、不互相穿透、不无故换位。"
    )
    negative = (
        "倾斜鸟瞰, 透视地平线, 空白平面图, 裁切场景, 人物无起终点, 缺少摄像机轨迹, "
        "标签重叠, 路线颜色相同, 人物漂浮, 人物穿透, 左右站位颠倒, 道具消失, 身份服装漂移"
    )
    return {
        "priority": priority,
        "reason": "；".join(reasons),
        "overhead_map_prompt": map_prompt,
        "blocking_board_prompt": blocking_prompt,
        "negative_prompt": negative,
    }


def _speakers(metadata):
    speakers = []
    for event in metadata.get("dialogue_events", []) if isinstance(metadata.get("dialogue_events"), list) else []:
        name = str(event.get("speaker", "") or "").strip()
        if name and name not in speakers:
            speakers.append(name)
    return speakers


def _compact(value, limit):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else text[:limit].rstrip("，。；; ") + "…"
