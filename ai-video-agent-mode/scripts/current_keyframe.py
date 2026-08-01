"""从已验证的 T2V 主镜头派生一张当前镜头剧情关键帧提示词。

这是当前主镜头的单张静态生图辅助资料，不是九宫格剧情包、
不是首尾帧控制，也不是 T2V 参考素材声明。
"""

import re

from modec_v4 import PROMPT_LABELS, split_sections
from modec_v4 import jimeng_feed_prompt


CHARACTER_RE = re.compile(r"角色|人物|男人|女人|少年|少女|老人|孩子|主角|配角")
DRAMATIC_RE = re.compile(r"rising|peak|高|critical|反转|质问|拒绝|承认|威胁|危险|压迫|揭示|出场|道具|交接|转身|停住")
FACT_ALTERNATIVES = {
    "左右站位": (("画面左", "左侧"), ("画面右", "右侧")),
    "持物手": (("左手",), ("右手",)),
    "身体支撑": (("站立", "站着"), ("坐着", "坐在"), ("躺着", "躺在")),
    "屏幕状态": (("亮屏", "屏幕亮"), ("熄屏", "黑屏")),
    "屏幕朝向": (("屏幕朝人物", "屏幕朝男孩", "屏幕朝女孩", "屏幕朝角色"), ("屏幕朝镜头", "屏幕朝观众")),
}


def build_keyframe_sequence(task, planned=None, canvas="16:9", visual_style=""):
    """Build start/dramatic/end keyframes and their T2V consistency audit."""
    task = task if isinstance(task, dict) else {}
    planned = planned if isinstance(planned, dict) else {}
    prompt = str(task.get("full_prompt", "") or "")
    if not prompt.strip():
        return None
    metadata = task.get("qa_metadata", {}) if isinstance(task.get("qa_metadata"), dict) else {}
    sections = split_sections(prompt, PROMPT_LABELS)
    dramatic = metadata.get("dramatic_design", {}) if isinstance(metadata.get("dramatic_design"), dict) else {}
    performance = metadata.get("performance_contract", {}) if isinstance(metadata.get("performance_contract"), dict) else {}
    pressure = metadata.get("pressure_release_design", {}) if isinstance(metadata.get("pressure_release_design"), dict) else {}
    continuity = metadata.get("continuity_contract", {}) if isinstance(metadata.get("continuity_contract"), dict) else {}
    lifecycle = metadata.get("prop_lifecycle_contract", {}) if isinstance(metadata.get("prop_lifecycle_contract"), dict) else {}
    if not _worth_keyframe(prompt, metadata, dramatic, pressure):
        return None

    scene = str(planned.get("scene", "当前场景") or "当前场景")
    common = _common_keyframe_anchor(task, sections, canvas, visual_style, scene)
    start_state = _compact(metadata.get("start_state") or continuity.get("start_anchor"), 240)
    dramatic_state = _choose_story_moment(dramatic, performance, pressure, metadata, sections.get("主镜头连续规则", ""))
    end_state = _compact(
        metadata.get("end_state") or continuity.get("end_anchor") or continuity.get("next_carryover"), 240
    )
    start_prop = _prop_state(lifecycle, "start")
    dramatic_prop = _prop_state(lifecycle, "dramatic")
    end_prop = _prop_state(lifecycle, "end")
    frames = [
        _frame("起始状态关键帧", 0.0, common, start_state, start_prop, "稳定起幅，不提前发生戏眼动作"),
        _frame("戏眼关键帧", _dramatic_time(task), common, dramatic_state, dramatic_prop, "只锁定本镜信息增量最高的动作或表情落点"),
        _frame("结束状态关键帧", float(task.get("duration", 0) or 0), common, end_state, end_prop, "形成可供下一镜继承的稳定终态"),
    ]
    state_diff = _state_diff_rows(start_state, dramatic_state, end_state, lifecycle, performance)
    continuity_check = _keyframe_continuity_checks(frames, common, lifecycle)
    fact_consistency = _fact_consistency_checks(prompt, frames)
    video_prompt = _keyframe_video_prompt(task, frames, prompt)
    return {
        "priority": "必需" if _high_priority(metadata, dramatic, pressure) else "建议",
        "reason": _reason(metadata, dramatic, pressure),
        "frames": frames,
        "state_diff": state_diff,
        "continuity_check": continuity_check,
        "fact_consistency": fact_consistency,
        "video_prompt": video_prompt,
        "negative_prompt": _keyframe_negative_prompt(),
        "pass": all(item["pass"] for item in continuity_check + fact_consistency),
    }


def build_current_shot_keyframe_reference(task, planned=None, canvas="16:9", visual_style=""):
    """Return one static dramatic keyframe prompt for the current main shot.

    The keyframe captures the most readable story moment inside this shot:
    spatial lock + prop state + emotional evidence + camera composition +
    end-frame residue.  It must never branch into multiple panels.
    """
    sequence = build_keyframe_sequence(task, planned, canvas, visual_style)
    if sequence:
        dramatic_frame = sequence["frames"][1]
        return {
            "priority": sequence["priority"],
            "reason": sequence["reason"],
            "keyframe_prompt": "当前镜头剧情关键帧生图提示。" + dramatic_frame["prompt"],
            "negative_prompt": sequence["negative_prompt"],
        }
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


def _common_keyframe_anchor(task, sections, canvas, visual_style, scene):
    metadata = task.get("qa_metadata", {}) if isinstance(task.get("qa_metadata"), dict) else {}
    palette = metadata.get("scene_tone_palette", {}) if isinstance(metadata.get("scene_tone_palette"), dict) else {}
    perspective = metadata.get("perspective_scale_contract", {}) if isinstance(metadata.get("perspective_scale_contract"), dict) else {}
    lighting = metadata.get("lighting_topology_contract", {}) if isinstance(metadata.get("lighting_topology_contract"), dict) else {}
    pieces = [
        "%s画幅" % canvas,
        visual_style,
        "《%s》" % scene,
        sections.get("主体与空间锁定", ""),
        palette.get("visual_scene_prefix", ""),
        perspective.get("subjects_depth", ""),
        perspective.get("support_plane", ""),
        perspective.get("projection_scale_rule", ""),
        perspective.get("body_ratio_lock", ""),
        lighting.get("motivated_source", ""),
        lighting.get("face_light_layer", ""),
    ]
    return _compact("；".join(str(piece).strip("；。 ") for piece in pieces if str(piece).strip()), 820)


def _frame(label, time_seconds, common, state, prop_state, purpose):
    prompt = (
        "%s。%s；状态：%s；道具：%s；%s。"
        "单张静态画面，不分格；重复人物位置、身体朝向、支撑点、接触边界、道具归属、可见面、景别机位和光源关系。"
        % (common, label, state or "保持本镜已确认状态", prop_state or "保持已确认道具状态", purpose)
    )
    return {"label": label, "time_seconds": round(float(time_seconds or 0), 3), "prompt": prompt}


def _prop_state(contract, phase):
    if not contract:
        return ""
    prop = str(contract.get("prop", "关键道具") or "关键道具")
    if phase == "start":
        return "%s位于%s，由%s以%s接触，可见面%s" % (
            prop, contract.get("start_location", "已确认起始位置"),
            contract.get("contact_owner", "已确认人物"), contract.get("contact_mode", "已确认方式"),
            contract.get("visible_surface", "保持固定"),
        )
    if phase == "dramatic":
        return "%s沿%s运动，接触关系保持%s，可见面%s" % (
            prop, contract.get("motion_path", "已确认路径"), contract.get("contact_mode", "连续"),
            contract.get("visible_surface", "保持固定"),
        )
    return "%s稳定在%s，方向%s，下一镜%s" % (
        prop, contract.get("end_location", "已确认终点"), contract.get("end_orientation", "保持固定"),
        contract.get("next_shot_state", "继承当前状态"),
    )


def _state_diff_rows(start_state, dramatic_state, end_state, lifecycle, performance):
    rows = [{
        "subject": "人物整体", "start": start_state, "dramatic": dramatic_state, "end": end_state,
    }]
    if performance:
        rows.append({
            "subject": "人物情绪/身体", "start": str(performance.get("primary_emotion", "") or performance.get("start_intensity", "")),
            "dramatic": str(performance.get("mask_leak", "") or performance.get("primary_body_action", "")),
            "end": str(performance.get("end_residue", "") or performance.get("end_intensity", "")),
        })
    if lifecycle:
        rows.append({
            "subject": str(lifecycle.get("prop", "关键道具") or "关键道具"),
            "start": _prop_state(lifecycle, "start"), "dramatic": _prop_state(lifecycle, "dramatic"),
            "end": _prop_state(lifecycle, "end"),
        })
    return rows


def _keyframe_continuity_checks(frames, common, lifecycle):
    checks = []
    for frame in frames:
        checks.append({
            "name": "%s重复共同空间/身份锚点" % frame["label"],
            "pass": bool(common and common in frame["prompt"]),
            "evidence": "共同锚点已逐帧重写" if common in frame["prompt"] else "缺少共同锚点",
        })
    if lifecycle:
        prop = str(lifecycle.get("prop", "") or "")
        checks.append({
            "name": "道具三帧连续",
            "pass": bool(prop and all(prop in frame["prompt"] for frame in frames)),
            "evidence": "%s在起始/戏眼/结束三帧均有状态" % (prop or "关键道具"),
        })
    return checks


def _fact_consistency_checks(t2v_prompt, frames):
    checks = []
    for frame in frames:
        conflicts = []
        for label, alternatives in FACT_ALTERNATIVES.items():
            source_values = _matched_alternatives(t2v_prompt, alternatives)
            frame_values = _matched_alternatives(frame["prompt"], alternatives)
            if source_values and frame_values and not frame_values.issubset(source_values):
                conflicts.append(label)
        checks.append({
            "name": "%s与T2V事实一致" % frame["label"],
            "pass": not conflicts,
            "evidence": "未检测到左右、持物手、支撑或屏幕状态冲突" if not conflicts else "冲突：" + "、".join(conflicts),
        })
    return checks


def _matched_alternatives(text, alternatives):
    value = str(text or "")
    return {index for index, terms in enumerate(alternatives) if any(term in value for term in terms)}


def _dramatic_time(task):
    duration = float(task.get("duration", 0) or 0)
    return duration * 0.55 if duration > 0 else 0.0


def _keyframe_video_prompt(task, frames, t2v_prompt):
    duration = float(task.get("duration", 0) or 0)
    middle = frames[1]["time_seconds"]
    end = duration if duration > 0 else frames[2]["time_seconds"]
    direct = _compact(jimeng_feed_prompt(t2v_prompt), 1500)
    return (
        "0.0-%.1f秒：从起始状态稳定进入戏眼，不改变人物身份、空间、支撑点和道具归属；"
        "%.1f-%.1f秒：只执行已确认主动作与表演变化，保持可见面、视线和接触路径连续；"
        "%.1f-%.1f秒：动作收束到结束关键帧并稳定保持。即梦执行正文：%s"
        % (middle, middle, max(middle, end * 0.85), max(middle, end * 0.85), end, direct)
    )


def _keyframe_negative_prompt():
    return (
        "九宫格, 多格漫画, P01, P09, 面板标签, 分镜编号, 连环画排版, 新增人物, "
        "新增道具, 人物换位, 左右颠倒, 支撑点漂移, 接触穿插, 道具瞬移, 功能面翻转, "
        "人体比例突变, 近远比例失调, 光源跳变, 肤色污染, 文本气泡, 水印"
    )
