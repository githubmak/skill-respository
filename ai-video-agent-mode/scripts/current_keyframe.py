"""从已验证的 T2V 主镜头派生一张当前镜头剧情关键帧提示词。

这是当前主镜头的单张静态生图辅助资料，不是九宫格剧情包、
不是首尾帧控制，也不是 T2V 参考素材声明。
"""

import re

from modec_v4 import PROMPT_LABELS, split_sections


CHARACTER_RE = re.compile(r"角色|人物|男人|女人|少年|少女|老人|孩子|主角|配角")
DRAMATIC_RE = re.compile(r"rising|peak|高|critical|反转|质问|拒绝|承认|威胁|危险|压迫|揭示|出场|道具|交接|转身|停住")


def build_current_shot_keyframe_reference(task, planned=None, canvas="16:9", visual_style=""):
    """Return one static dramatic keyframe prompt for the current main shot.

    The keyframe captures the most readable story moment inside this shot:
    spatial lock + prop state + emotional evidence + camera composition +
    end-frame residue.  It must never branch into multiple panels.
    """
    task = task if isinstance(task, dict) else {}
    planned = planned if isinstance(planned, dict) else {}
    prompt = str(task.get("full_prompt", "") or "")
    if not prompt.strip():
        return None
    metadata = task.get("qa_metadata", {}) if isinstance(task.get("qa_metadata"), dict) else {}
    sections = split_sections(prompt, PROMPT_LABELS)
    spatial = _compact(sections.get("主体与空间锁定", ""), 360)
    continuity = _compact(sections.get("主镜头连续规则", ""), 360)
    timeline = _compact(sections.get("子镜头组", ""), 520)
    light = _compact(sections.get("光照、声音与稳定约束", ""), 180)
    dramatic = metadata.get("dramatic_design", {}) if isinstance(metadata.get("dramatic_design"), dict) else {}
    performance = metadata.get("performance_contract", {}) if isinstance(metadata.get("performance_contract"), dict) else {}
    continuity_contract = metadata.get("continuity_contract", {}) if isinstance(metadata.get("continuity_contract"), dict) else {}
    pressure = metadata.get("pressure_release_design", {}) if isinstance(metadata.get("pressure_release_design"), dict) else {}

    story_moment = _choose_story_moment(dramatic, performance, pressure, metadata, continuity)
    if not _worth_keyframe(prompt, metadata, dramatic, pressure):
        return None

    scene = str(planned.get("scene", "当前场景") or "当前场景")
    style = (visual_style + "，") if visual_style else ""
    end_residue = _compact(
        continuity_contract.get("next_carryover")
        or continuity_contract.get("end_anchor")
        or metadata.get("end_state", ""),
        180,
    )
    prompt_text = (
        f"{canvas}画幅，{style}当前镜头剧情关键帧生图提示。"
        f"只绘制《{scene}》这一主镜头内部最关键的一个静态瞬间，不分格、不做九宫格、不画连续漫画。"
        f"剧情瞬间：{story_moment}。"
        f"空间与人物锁定：{spatial}。"
        f"主镜头规则：{continuity}。"
        f"画面选择子镜头组中信息量最高的单一落点：{timeline}。"
        f"构图必须让观众一眼读懂当前冲突、人物关系、关键道具归属和未完成状态；"
        f"保留人物身体朝向、视线对象、手部/道具接触、重心和尾帧残留。"
        f"光照与气氛：{light}。"
        f"落幅残留：{end_residue}。"
        "画面只保留一个主要视觉焦点，其他人物只作为空间压力或反应层级；"
        "不得新增人物、道具、台词气泡、分格边框、P01-P09标记、漫画页排版或下一镜事件。"
    )
    negative = (
        "九宫格, 多格漫画, P01, P09, 面板标签, 分镜编号, 连环画排版, "
        "新增剧情人物, 新增道具, 道具瞬移, 人物换位, 口型错误, 表情夸张失控, "
        "左右站位颠倒, 光源突变, 服装身份漂移, 文本气泡, 水印"
    )
    return {
        "priority": "必需" if _high_priority(metadata, dramatic, pressure) else "建议",
        "reason": _reason(metadata, dramatic, pressure),
        "keyframe_prompt": prompt_text,
        "negative_prompt": negative,
    }


def _choose_story_moment(dramatic, performance, pressure, metadata, continuity):
    candidates = [
        pressure.get("release_trigger"),
        pressure.get("pressure_object") or pressure.get("pressure_mechanism"),
        dramatic.get("information_gain"),
        dramatic.get("reaction_ownership"),
        performance.get("画面可读瞬间") if isinstance(performance, dict) else "",
        performance.get("readable_moment") if isinstance(performance, dict) else "",
        metadata.get("dramatic_goal"),
        continuity,
    ]
    for candidate in candidates:
        text = _compact(candidate, 160)
        if text:
            return text
    return "当前镜头的唯一剧情问题与落幅残留"


def _worth_keyframe(prompt, metadata, dramatic, pressure):
    if not CHARACTER_RE.search(prompt) and not metadata.get("dialogue_events"):
        return False
    blob = " ".join(str(value or "") for value in (
        prompt,
        metadata.get("dramatic_goal", ""),
        dramatic.get("narrative_weight", ""),
        dramatic.get("information_gain", ""),
        dramatic.get("reaction_ownership", ""),
        pressure.get("pressure_source", ""),
        pressure.get("release_trigger", ""),
    ))
    return bool(DRAMATIC_RE.search(blob)) or bool(metadata.get("dialogue_events"))


def _high_priority(metadata, dramatic, pressure):
    tension = str((metadata.get("emotion_driver", {}) or {}).get("tension_intent", "") if isinstance(metadata.get("emotion_driver"), dict) else "")
    weight = str(dramatic.get("narrative_weight", ""))
    return tension in ("rising", "peak") or weight in ("high", "critical") or bool(pressure)


def _reason(metadata, dramatic, pressure):
    reasons = []
    if metadata.get("dialogue_events"):
        reasons.append("当前镜头含台词/OS/OV或听者反应，关键帧可锁定说话口型与反应层级")
    if dramatic.get("information_gain"):
        reasons.append("当前镜头含新的观众认知或信息落点")
    if pressure:
        reasons.append("当前镜头含压迫/释放机制，需要锁定压力物与未完成状态")
    if dramatic.get("narrative_weight") in ("high", "critical"):
        reasons.append("当前镜头叙事权重高")
    return "；".join(reasons) if reasons else "当前镜头存在人物表演或关系状态，建议生成单张剧情关键帧辅助稳定"


def _compact(value, limit=200):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else text[:limit].rstrip("，。；; ") + "…"
