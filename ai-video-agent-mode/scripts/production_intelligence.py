"""Deterministic production intelligence shared by validation and export.

These helpers derive risk and audit artifacts from the canonical package. They
do not add model calls or duplicate prompt facts into dispatch packets.
"""

from __future__ import annotations

import difflib
import re


NEGATIVE_VISUAL_CLAUSE_RE = re.compile(
    r"(?:不要(?:出现|生成|添加|戴|带|穿)?|禁止(?:出现|生成|添加)?|避免(?:出现|生成|添加)?|"
    r"不是|不戴|不带|不穿|去掉|去除|移除|排除|没有)"
    r"(?P<concept>[^，。；;\n]{1,18})"
)
SAFE_NEGATIVE_ARTIFACT_TERMS = (
    "新增人物", "重复人物", "新增主体", "重复主体", "多余人物", "多余主体",
    "变形", "畸形", "错位", "穿模", "粘连", "融合", "断裂", "扭曲", "拉伸",
    "抖动", "闪烁", "漂移", "跳变", "乱码", "水印", "字幕", "标志", "logo",
    "噪点", "失焦", "模糊", "过曝", "死黑", "偏色", "污染", "锯齿", "裁切",
    "光晕", "粒子", "运动模糊", "鬼影", "压缩伪影", "色带", "摩尔纹",
)
PROP_MANIPULATION_RE = re.compile(
    r"(?:把|将)(?P<object_after_ba>[\u4e00-\u9fffA-Za-z0-9_·]{1,12})"
    r"[^，。；;\n]{0,8}(?:拿起|拿出|取出|握住|递给|递出|交给|接过|接住|放下|放到|"
    r"推开|拉开|翻开|点击|滑动|操作|塞进|收起|佩戴|脱下|展示)|"
    r"(?:拿起|拿出|取出|握住|递给|递出|交给|接过|接住|放下|放到|推开|拉开|翻开|"
    r"点击|滑动|操作|塞进|收起|佩戴|脱下|展示|阅读|玩)"
    r"(?P<object_after_action>[\u4e00-\u9fffA-Za-z0-9_·]{1,12})"
)
DEPTH_TERMS = ("前景", "中景", "后景", "近处", "远处", "靠近镜头", "远离镜头")
COLLECTIVE_SUBJECTS = ("所有清晰入画人物", "全部清晰入画人物", "所有可见人物")
DEPTH_MOTION_TERMS = ("靠近镜头", "远离镜头", "走向镜头", "走入前景", "退向后景", "从后景走向", "沿景深")
LOCOMOTION_TERMS = ("行走", "走向", "走近", "跑向", "奔向", "追逐", "上楼", "下楼")
SUPPORTED_POSTURE_TERMS = ("坐下", "坐在", "坐着", "靠坐", "躺", "卧", "伏", "趴", "骑马", "骑乘", "倒地")
AIRBORNE_POSTURE_TERMS = ("轻功", "腾空", "跃起", "跳起", "飞行", "凌空", "被击飞", "坠落", "下落")
FACE_TO_FACE_TERMS = ("对峙", "面对面", "相互面对", "彼此面对", "对望", "看见彼此", "四目相对")
CAMERA_FACING_TERMS = (
    "面向镜头", "朝向镜头", "正对镜头", "面对镜头", "面向摄影机", "正对摄影机",
    "看向镜头", "望向镜头", "直视镜头", "看向摄影机", "直视摄影机",
)
DIRECT_ADDRESS_AUTH_TERMS = (
    "打破第四面墙", "对镜口播", "对观众说话", "向观众独白", "直面观众表演",
    "主观视角", "第一人称视角", "POV", "摄影机代表对手视线", "摄影机代表观众视线",
)
DIRECT_ADDRESS_TIMING_TERMS = ("短暂", "随后", "期间", "说完后", "台词期间", "独白期间")
DIRECT_ADDRESS_END_TERMS = (
    "视线回到", "视线重新落在", "恢复看向", "重新看向", "重新面向",
    "保持直视镜头到结束", "直视镜头保持到结束", "落幅仍直视镜头", "直视观众保持到结束",
)
CAMERA_VISIBLE_PLANE_TERMS = (
    "正面可见", "正脸可见", "正面和双肩可见", "背面可见", "背影可见", "后脑可见",
    "背对摄影机", "背对镜头", "侧面可见", "侧脸可见", "三分之二侧面可见",
)
DOORWAY_EVENT_TERMS = ("回家", "进门", "走进", "进入屋内", "跨过门槛", "跨进门槛", "迈过门槛")
OCCLUSION_RESULT_TERMS = ("仍可见", "保持可见", "清晰可见", "不被遮住", "露出", "视觉通道", "视线通道", "中央空隙")
SIMILAR_PROP_GROUP_RE = re.compile(
    r"(?:双|两个|两只|两件|两根|两把|两盏|两部|两台|两枚)"
    r"(?P<object>[\u4e00-\u9fffA-Za-z0-9_·]{1,10})"
)
NON_PROP_PAIRED_OBJECTS = ("手", "脚", "眼", "耳", "臂", "腿", "肩", "膝", "人", "人物", "孩子", "男女")
PROP_DISTINCTION_TERMS = (
    "不同", "区分", "圆口", "方口", "深色", "浅色", "宽", "窄", "高筒", "矮筒", "鱼", "菜",
    "布盖", "藤编", "竹编", "粗编", "细编", "形状", "颜色", "内容物", "尺寸差",
)


def classify_visual_prior_risks(prompt, source_text=""):
    """Return explicit/implicit visual-prior risks with positive repair hints."""
    text = str(prompt or "")
    source = str(source_text or "")
    risks = []
    for match in NEGATIVE_VISUAL_CLAUSE_RE.finditer(text):
        matched_clause = match.group(0)
        if matched_clause in source:
            continue
        concept = match.group("concept").strip()
        if not concept or any(term in matched_clause for term in SAFE_NEGATIVE_ARTIFACT_TERMS):
            continue
        risks.append(_risk(
            "negative_concept_priming", "high", concept,
            "删除该错误概念，改写真实身份、服装、发型和目标场景固定锚点",
        ))
    if re.search(r"背对(?:镜头|摄影机).{0,24}(?:看向|望向|盯着|凝视)(?:某人|人物|角色|他|她)", text):
        risks.append(_risk(
            "back_facing_eyeline", "high", "背对镜头却看向未空间化的人物",
            "锁定肩线、头部可转角度和画面侧固定声源/门口/窗边目标",
        ))
    if any(term in text for term in ("镜子", "镜面", "倒影", "反射")) and not all(
        any(term in text for term in group)
        for group in (("镜面位置", "镜中", "倒影位于", "反射面"), ("摄影机", "镜头", "机位"))
    ):
        risks.append(_risk(
            "mirror_reflection_geometry", "medium", "镜面/倒影缺少反射面与摄影机关系",
            "写清镜面所在平面、人物本体位置、倒影范围和摄影机实际可见面",
        ))
    display = re.search(r"(?:手机|照片|证件|书页|文件|表盘).{0,18}(?:正对|朝向|展示给)(?:镜头|观众)", text)
    if display and not any(term in source for term in ("展示", "给他看", "给她看", "给镜头看", "看清")):
        risks.append(_risk(
            "unsupported_display_prior", "high", display.group(0),
            "恢复功能面朝使用者；需要内容时改用肩后/俯拍同侧机位或拆展示镜",
        ))
    if re.search(r"(?:驾驶|开车).{0,30}(?:回头|转身|长时间看向后方|背对前路)", text):
        risks.append(_risk(
            "vehicle_eyeline_physics", "high", "驾驶动作与道路视线冲突",
            "保持胸口朝前、双手与方向盘接触；只允许短暂眼神侧移并回到前路",
        ))
    if any(term in text for term in ("前景肩线", "前景背影", "镜中倒影", "玻璃倒影")) and not re.search(
        r"(?:可见人数|入画人数)[：:]?\s*[一二三四五六七八九十\d]+人", text
    ):
        risks.append(_risk(
            "occlusion_person_spawn", "medium", "遮挡/倒影可能被升级为额外人物",
            "增加可见人数闸门，并限定肩线、背影或倒影不出现可辨认五官与新动作",
        ))
    return _dedupe_risks(risks)


def visual_prior_risk_issues(prompt, source_text=""):
    return [
        "视觉先验风险[%s]：%s；正向修复：%s" % (risk["category"], risk["evidence"], risk["repair"])
        for risk in classify_visual_prior_risks(prompt, source_text)
        if risk["severity"] == "high"
    ]


def multi_person_attention_budget_issues(metadata, prompt="", visible_characters=None):
    metadata = metadata if isinstance(metadata, dict) else {}
    visible = _string_list(visible_characters)
    if len(visible) < 2:
        return []
    issues = []
    roles = metadata.get("performance_priority", {})
    if not isinstance(roles, dict):
        return ["多人镜必须提供performance_priority并分配主表演、受击/观察反应与背景层级"]
    primary = str(roles.get("primary", "") or "").strip()
    supporting = _string_list(roles.get("supporting", []))
    background = _string_list(roles.get("background", []))
    assigned = [value for value in [primary] + supporting + background if value]
    if set(assigned) != set(visible) or len(assigned) != len(set(assigned)):
        issues.append("多人注意力预算必须恰好覆盖全部可见人物且角色分区不得重叠")
    handoff = metadata.get("attention_handoff", {})
    if isinstance(handoff, dict):
        count = handoff.get("handoff_count")
        if isinstance(count, int) and count > 1:
            issues.append("单镜注意力交接最多一次；第二次交接必须拆为下一主镜")
    text = str(prompt or "")
    if len(visible) >= 3 and not any(term in text for term in ("弱虚化", "不抢焦", "肩线", "后景", "观察反应")):
        issues.append("三人以上镜必须把非主表演者降为受击/观察反应、肩线、弱虚化或后景层级")
    return issues


def _actor_faces_target(text, actor, target):
    actor_re = re.escape(actor)
    target_re = re.escape(target)
    patterns = (
        r"%s[^。；;\n]{0,42}(?:身体|胸口|肩线|脚尖|正面)[^。；;\n]{0,12}(?:面向|朝向|正对|转向)[^。；;\n]{0,16}%s" % (actor_re, target_re),
        r"%s[^。；;\n]{0,42}(?:面向|朝向|正对)[^。；;\n]{0,16}%s" % (actor_re, target_re),
        r"%s[^。；;\n]{0,16}(?:正对|对面)[^。；;\n]{0,42}%s" % (target_re, actor_re),
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _name_has_threshold_side(text, name):
    name_re = re.escape(name)
    side = r"(?:门槛|房门)(?:内侧|外侧)|(?:屋内|门内|屋外|门外)(?:一侧|区域|土面|院地)?"
    return bool(
        re.search(r"%s[^。；;\n]{0,36}%s" % (name_re, side), text)
        or re.search(r"%s[^。；;\n]{0,24}%s" % (side, name_re), text)
    )


def _actor_camera_facing(text, actor):
    actor_re = re.escape(actor)
    camera_terms = "|".join(re.escape(term) for term in CAMERA_FACING_TERMS)
    return bool(re.search(r"%s[^。；;\n]{0,18}(?:%s)" % (actor_re, camera_terms), text))


def _direct_address_has_timing(text):
    return any(term in text for term in DIRECT_ADDRESS_TIMING_TERMS) or bool(
        re.search(r"\d+(?:\.\d+)?\s*[-–—至]\s*\d+(?:\.\d+)?\s*(?:s|秒)", text)
    )


def spatial_facing_issues(metadata, prompt="", visible_characters=None):
    """Validate visible topology, actor-facing targets and camera-visible planes."""
    text = str(prompt or "")
    visible = [name for name in _string_list(visible_characters) if name in text]
    issues = []
    relational = len(visible) >= 2 and any(term in text for term in FACE_TO_FACE_TERMS)
    reverse_or_plane = len(visible) >= 2 and any(
        term in text for term in ("肩后", "背对镜头", "背对摄影机", "正面可见", "正脸可见", "背影")
    )
    if relational or reverse_or_plane:
        reciprocal_pairs = [
            (first, second)
            for index, first in enumerate(visible)
            for second in visible[index + 1:]
            if _actor_faces_target(text, first, second) and _actor_faces_target(text, second, first)
        ]
        if not reciprocal_pairs:
            issues.append("双人对峙/正背关系必须分别写A身体面向B、B身体面向A，不能只写对望、面对面或前后景")
        if any(term in text for term in CAMERA_FACING_TERMS):
            authorized = any(term in text for term in DIRECT_ADDRESS_AUTH_TERMS)
            camera_facing_actors = [name for name in visible if _actor_camera_facing(text, name)]
            if not authorized:
                issues.append("双人关系镜不得用面向/正对镜头代替人物关系；只有源文明示的POV、口播或打破第四面墙可授权直视镜头")
            else:
                if len(camera_facing_actors) != 1:
                    issues.append("授权直面镜头必须明确且只能有一名人物直视摄影机，其他人物继续看向场内目标")
                if not _direct_address_has_timing(text):
                    issues.append("授权直面镜头必须写开始/结束时间窗或短暂触发时点")
                if not any(term in text for term in DIRECT_ADDRESS_END_TERMS):
                    issues.append("授权直面镜头必须写视线回到对手或保持直视到落幅的结束状态")
                if any(term in text for term in ("面向镜头", "朝向镜头", "正对镜头", "面对镜头", "面向摄影机", "正对摄影机")) and not any(
                    term in text for term in ("转向镜头", "转向摄影机", "转身面向镜头", "肩线转向镜头", "身体仍面向")
                ):
                    issues.append("授权人物若身体转向镜头，必须写从原关系到直面镜头的可见转向；仅眼神直视时写身体仍面向对手")
    if reverse_or_plane and not any(term in text for term in CAMERA_VISIBLE_PLANE_TERMS):
        issues.append("正背/肩后关系必须另写摄影机看到每人的正面、背面或侧面")

    doorway = "门槛" in text and any(term in text for term in ("门外", "门内", "屋外", "屋内", "门框"))
    if doorway and len(visible) >= 2:
        missing = [name for name in visible if not _name_has_threshold_side(text, name)]
        if missing:
            issues.append("门槛关系镜必须逐人绑定门槛内/外侧：" + "、".join(missing))
    camera_outside = bool(re.search(r"(?:摄影机|镜头|机位)[^。；;\n]{0,24}(?:门槛外侧|门外|院中|院地)", text))
    looks_inside = bool(re.search(r"(?:朝|拍向|对准|看向)[^。；;\n]{0,10}(?:屋内|门内|室内)", text))
    if camera_outside and doorway and not looks_inside:
        issues.append("门外门槛机位必须声明朝屋内/朝门外的拍摄方向和真实可见背景")
    if camera_outside and re.search(r"门外[^。；;\n]{0,12}(?:留在|位于|作为)[^。；;\n]{0,8}(?:背景|后景)", text):
        issues.append("摄影机在门外朝屋内拍摄时，背景应是屋内墙面/灯/家具，门外夜色不能同时位于后景")

    if any(term in text for term in DOORWAY_EVENT_TERMS):
        has_start = any(term in text for term in ("起点在门外", "从门外", "门槛外侧起步", "屋外起步"))
        has_cross = any(term in text for term in ("跨过门槛", "跨进门槛", "迈过门槛", "脚掌越过门槛"))
        has_end = any(term in text for term in ("停在门槛内侧", "进入屋内", "最终站在屋内", "双脚落在屋内"))
        if not (has_start and has_cross and has_end):
            issues.append("回家/进门必须写门外起点 -> 跨过门槛 -> 屋内终点的完整可见动作链")

    if len(visible) >= 2 and any(term in text for term in ("前景", "近处")) and any(term in text for term in ("后景", "远处")):
        if "遮挡" not in text or not any(term in text for term in OCCLUSION_RESULT_TERMS):
            issues.append("具名前后景人物必须写允许遮挡部位及后景脸/手/关键道具的可见结果；占比只能辅助")
    similar_group = next(
        (
            match.group("object")
            for match in SIMILAR_PROP_GROUP_RE.finditer(text)
            if not any(match.group("object").startswith(term) for term in NON_PROP_PAIRED_OBJECTS)
        ),
        "",
    )
    if similar_group and not any(term in text for term in PROP_DISTINCTION_TERMS):
        issues.append("同类道具同时入画必须用持有人加形状/颜色/内容物至少一项区分")
    return issues


def prop_lifecycle_risk(value):
    text = _flatten_text(value)
    return bool(PROP_MANIPULATION_RE.search(text))


def prop_lifecycle_contract_issues(metadata, prompt="", required=False):
    metadata = metadata if isinstance(metadata, dict) else {}
    contract = metadata.get("prop_lifecycle_contract")
    if contract in (None, {}, ""):
        return ["活动道具镜必须提供qa_metadata.prop_lifecycle_contract"] if required else []
    if not isinstance(contract, dict):
        return ["qa_metadata.prop_lifecycle_contract必须是对象"]
    fields = (
        "prop", "purpose", "visible_surface", "start_location", "contact_owner",
        "contact_mode", "motion_path", "end_location", "end_orientation", "next_shot_state",
    )
    issues = _required_flat_fields(contract, "prop_lifecycle_contract", fields)
    text = str(prompt or "")
    for field in ("visible_surface", "start_location", "contact_mode", "motion_path", "end_location", "end_orientation"):
        if not _grounded(contract.get(field), text):
            issues.append("prop_lifecycle_contract.%s必须转译为full_prompt中的可见事实" % field)
    if str(contract.get("start_location", "")).strip() == str(contract.get("end_location", "")).strip() and any(
        term in str(contract.get("motion_path", "")) for term in ("递", "移动", "拿起", "放下", "推", "拉")
    ):
        issues.append("道具发生移动时start_location与end_location不能相同")
    return issues


def perspective_scale_contract_issues(metadata, prompt="", visible_characters=None, required=False):
    metadata = metadata if isinstance(metadata, dict) else {}
    visible = _string_list(visible_characters)
    contract = metadata.get("perspective_scale_contract")
    text = str(prompt or "")
    depth_risk = len(visible) > 1 and any(term in text for term in DEPTH_TERMS)
    if contract in (None, {}, ""):
        return ["多人纵深构图必须提供qa_metadata.perspective_scale_contract"] if required or depth_risk else []
    if not isinstance(contract, dict):
        return ["qa_metadata.perspective_scale_contract必须是对象"]
    fields = (
        "subjects_depth", "support_plane", "projection_scale_rule", "body_ratio_lock",
        "motion_scaling", "prop_scale_lock", "grounding_evidence", "fallback",
    )
    issues = _required_flat_fields(contract, "perspective_scale_contract", fields)
    subjects = str(contract.get("subjects_depth", "") or "")
    if visible and not any(term in subjects for term in COLLECTIVE_SUBJECTS):
        missing = [name for name in visible if name not in subjects]
        if missing:
            issues.append("perspective_scale_contract.subjects_depth未覆盖：" + "、".join(missing))
    for field in ("subjects_depth", "support_plane", "projection_scale_rule", "body_ratio_lock", "grounding_evidence"):
        if not _grounded(contract.get(field), text):
            issues.append("perspective_scale_contract.%s必须转译为full_prompt中的可见事实" % field)
    projection = " ".join(str(contract.get(field, "") or "") for field in ("projection_scale_rule", "body_ratio_lock"))
    if not any(term in projection for term in ("近大远小", "近处投影", "远处投影", "同一深度", "画面占比")):
        issues.append("透视合同必须说明近大远小或同一深度的投影尺度关系")
    if not any(term in projection for term in ("头身比例", "骨架比例", "真实体型", "体型不变")):
        issues.append("透视合同必须锁定真实体型、骨架或头身比例不随纵深改变")
    body_lock = str(contract.get("body_ratio_lock", "") or "")
    if not any(term in body_lock for term in ("真实身高", "身高不变", "身高稳定")):
        issues.append("perspective_scale_contract.body_ratio_lock必须锁定人物真实身高")
    if not any(term in body_lock for term in ("四肢长度", "手臂长度", "腿部长度", "肢体长度")):
        issues.append("perspective_scale_contract.body_ratio_lock必须锁定四肢长度")
    if len(visible) >= 2 and not any(term in body_lock for term in ("身高差", "相对身高")):
        issues.append("多人透视合同必须锁定人物身高差或相对身高")
    if any(term in text for term in ("儿童", "孩子", "男孩", "女孩", "少年")) and any(
        term in text for term in ("成人", "男人", "女人", "父亲", "母亲", "男主", "女主")
    ) and not any(term in body_lock + " " + text for term in ("低于成人肩", "只到成人胸", "头顶低于", "肩线以下", "胸口以下")):
        issues.append("儿童与成人同框必须用头顶相对成人肩/胸位置锁定相对身高，不能只靠画面占比")
    grounding = " ".join(str(contract.get(field, "") or "") for field in ("support_plane", "grounding_evidence"))
    if not any(term in grounding for term in ("地平线", "消失点", "消失关系", "透视线")):
        issues.append("透视合同必须用地平线、消失点或透视线固定空间投影")
    if not any(term in grounding for term in ("接地", "脚底", "接触点", "支撑", "承载面")):
        issues.append("透视合同必须提供脚底接触点、支撑或承载面证据")
    motion_scaling = str(contract.get("motion_scaling", "") or "")
    if any(term in text for term in DEPTH_MOTION_TERMS):
        if not any(term in motion_scaling for term in ("连续", "平滑", "逐步")):
            issues.append("沿景深移动时motion_scaling必须说明画面投影连续变化")
        if not any(term in motion_scaling for term in ("物理距离", "靠近", "远离", "景深")):
            issues.append("沿景深移动时motion_scaling必须绑定人物物理距离变化")
    return issues


def physical_stability_issues(metadata, prompt="", visible_characters=None):
    """Require support and trajectory evidence only for physically changing poses."""
    metadata = metadata if isinstance(metadata, dict) else {}
    text = str(prompt or "")
    if not text:
        return []
    issues = []
    perspective = metadata.get("perspective_scale_contract", {})
    perspective = perspective if isinstance(perspective, dict) else {}
    evidence = text + " " + _flatten_text(perspective)

    if any(term in text for term in LOCOMOTION_TERMS) and not any(
        term in evidence for term in ("步态", "脚步", "交替接地", "双脚", "地面", "路面", "台阶", "重心")
    ):
        issues.append("行走/奔跑镜必须写步态、脚步接地、连续地面/台阶或重心证据")
    if any(term in text for term in SUPPORTED_POSTURE_TERMS) and not any(
        term in evidence for term in ("承载面", "支撑", "接触", "臀", "腰背", "椅", "沙发", "床", "马背", "地面")
    ):
        issues.append("坐卧/骑乘/倒地镜必须写身体主支撑点与承载面接触")
    if any(term in text for term in AIRBORNE_POSTURE_TERMS):
        if not any(term in evidence for term in ("起跳", "离地", "轨迹", "抛物线", "空中路径", "飞行路径", "下落")):
            issues.append("腾空/飞行镜必须写起跳或空中轨迹")
        if not any(term in evidence for term in ("落地", "停稳", "稳定飞行", "保持飞行", "持续飞行", "稳定在空中")):
            issues.append("腾空/飞行镜必须写落地支撑或稳定飞行终态")
    if any(term in text for term in DEPTH_MOTION_TERMS):
        if not any(term in evidence for term in ("头身比例", "骨架", "真实身高", "真实体型")):
            issues.append("人物沿景深移动时必须锁定头身、骨架、真实身高或真实体型")
        if not (
            any(term in evidence for term in ("画面占比", "投影尺度", "投影占比", "近大远小"))
            and any(term in evidence for term in ("连续", "平滑", "逐步"))
        ):
            issues.append("人物沿景深移动时必须说明投影占比随物理距离连续变化")
    return issues


def lighting_topology_contract_issues(metadata, prompt="", required=False):
    metadata = metadata if isinstance(metadata, dict) else {}
    contract = metadata.get("lighting_topology_contract")
    if contract in (None, {}, ""):
        return ["清晰人物镜必须提供qa_metadata.lighting_topology_contract"] if required else []
    if not isinstance(contract, dict):
        return ["qa_metadata.lighting_topology_contract必须是对象"]
    fields = (
        "motivated_source", "source_direction", "temperature_range", "face_light_layer",
        "environment_light_layer", "shadow_exposure_policy", "volume_light_boundary",
        "conflict_resolution",
    )
    issues = _required_flat_fields(contract, "lighting_topology_contract", fields)
    text = str(prompt or "")
    for field in fields[:-1]:
        if not _grounded(contract.get(field), text):
            issues.append("lighting_topology_contract.%s必须转译为full_prompt中的可见事实" % field)
    face = str(contract.get("face_light_layer", "") or "")
    if not any(term in face for term in ("脸", "面部", "眼窝", "鼻翼", "下颌", "肤色")):
        issues.append("lighting_topology_contract.face_light_layer必须明确人物面光或肤色落点")
    direction = str(contract.get("source_direction", "") or "")
    if not any(term in direction for term in ("左", "右", "前", "后", "上", "下", "侧", "顶部", "窗外", "门外")):
        issues.append("lighting_topology_contract.source_direction必须给出可执行光源方向")
    temperature = str(contract.get("temperature_range", "") or "")
    if not re.search(r"\d{4}K|冷|暖|中性|日光|月光|火光", temperature):
        issues.append("lighting_topology_contract.temperature_range必须给出色温或冷暖关系")
    shadow = str(contract.get("shadow_exposure_policy", "") or "")
    if not any(term in shadow for term in ("阴影", "暗部", "黑位")) or not any(
        term in shadow for term in ("保留", "可读", "细节", "不过曝", "不死黑")
    ):
        issues.append("lighting_topology_contract.shadow_exposure_policy必须说明暗部可读与高光保护")
    conflict = str(contract.get("conflict_resolution", "") or "")
    if not any(term in conflict for term in ("脸", "面部", "肤色", "皮肤")):
        issues.append("lighting_topology_contract.conflict_resolution必须声明面部/肤色优先级")
    return issues


def predict_action_failure(shot):
    shot = shot if isinstance(shot, dict) else {}
    metadata = shot.get("qa_metadata", {}) if isinstance(shot.get("qa_metadata"), dict) else {}
    prompt = str(shot.get("full_prompt", "") or "")
    budget = metadata.get("action_budget", {}) if isinstance(metadata.get("action_budget"), dict) else {}
    score, reasons = 0, []
    factors = (
        (int(budget.get("primary_action_count", 0) or 0) >= 2, 18, "多主动作"),
        (int(budget.get("physical_camera_move_count", 0) or 0) >= 1, 12, "人物动作与实体运镜竞争"),
        (any(term in prompt for term in ("递", "接", "抓", "扶", "抱", "摔", "拉住")), 16, "手部/身体接触"),
        (any(term in prompt for term in ("遮挡", "穿过", "镜面", "玻璃倒影")), 12, "遮挡或反射几何"),
        (len(re.findall(r"(?:同时|一边|并且)", prompt)) >= 2, 16, "并行动作过多"),
        (prop_lifecycle_risk(prompt), 12, "活动道具生命周期"),
        (not any(term in prompt for term in ("落幅", "最终", "停在", "稳定在", "保持")), 14, "缺少稳定终态"),
    )
    for active, weight, reason in factors:
        if active:
            score += weight
            reasons.append(reason)
    score = min(score, 100)
    tier = "high" if score >= 55 else "medium" if score >= 30 else "low"
    return {
        "score": score,
        "risk_level": tier,
        "reasons": reasons,
        "split_recommendation": "拆分第二动作链或降低运镜" if tier == "high" else "保持当前动作预算" if tier == "low" else "优先固定机位并锁定接触终态",
    }


def analyze_sequence_curves(shots):
    shots = [shot for shot in shots if isinstance(shot, dict)]
    tension_map = {"neutral": 1, "latent": 2, "rising": 3, "peak": 4, "release": 1}
    size_map = {"远景": 1, "全景": 2, "中远景": 3, "中景": 4, "中近景": 5, "近景": 6, "特写": 7}
    nodes, warnings = [], []
    for shot in shots:
        meta = shot.get("qa_metadata", {}) if isinstance(shot.get("qa_metadata"), dict) else {}
        prompt = str(shot.get("full_prompt", "") or "")
        tension = str((meta.get("emotion_driver", {}) or {}).get("tension_intent", "neutral") if isinstance(meta.get("emotion_driver"), dict) else "neutral")
        size = next((term for term in size_map if term in prompt), "")
        camera_energy = sum(1 for term in ("推近", "拉远", "横移", "跟拍", "环绕", "甩镜") if term in prompt)
        relation_distance = 1 if any(term in prompt for term in ("贴近", "并肩", "相拥")) else 3 if any(term in prompt for term in ("远处", "拉开距离", "隔着长桌")) else 2
        nodes.append({
            "shot_id": shot.get("shot_id", ""), "tension": tension_map.get(tension, 1),
            "shot_size": size_map.get(size, 0), "camera_energy": min(camera_energy, 3),
            "relationship_distance": relation_distance,
        })
    if len(nodes) >= 4:
        for field, label in (("tension", "张力"), ("shot_size", "景别"), ("camera_energy", "运镜能量"), ("relationship_distance", "关系距离")):
            values = [node[field] for node in nodes]
            if len(set(values)) == 1:
                warnings.append("整场%s曲线连续%d镜无变化" % (label, len(values)))
        if all(node["tension"] >= 3 and node["camera_energy"] >= 2 for node in nodes):
            warnings.append("整场高张力与高运镜持续叠加，缺少释放或稳定观察镜")
    return {"nodes": nodes, "warnings": warnings}


def build_emotion_visible_state(shot):
    shot = shot if isinstance(shot, dict) else {}
    meta = shot.get("qa_metadata", {}) if isinstance(shot.get("qa_metadata"), dict) else {}
    performance = meta.get("performance_contract", {}) if isinstance(meta.get("performance_contract"), dict) else {}
    return {
        "trigger": performance.get("trigger_event") or performance.get("trigger") or "",
        "facial_leak": performance.get("mask_leak") or performance.get("primary_expression") or "",
        "body_carry": performance.get("primary_body_action") or "",
        "voice_breath": performance.get("voice_or_breath_control") or "",
        "residue": performance.get("end_residue") or meta.get("end_state", ""),
        "intensity": {
            "start": performance.get("start_intensity"), "end": performance.get("end_intensity"),
            "delta": performance.get("emotion_delta"),
        },
    }


def build_sentence_provenance(task, direct_text):
    task = task if isinstance(task, dict) else {}
    sources = task.get("source_subshots", []) if isinstance(task.get("source_subshots"), list) else []
    source_ids = [str(item.get("subshot_id", "") or "") for item in sources if isinstance(item, dict)]
    metadata = task.get("qa_metadata", {}) if isinstance(task.get("qa_metadata"), dict) else {}
    palette = metadata.get("scene_tone_palette", {})
    palette = palette if isinstance(palette, dict) else {}
    scene_lock_ref = str(task.get("_scene_lock_ref", "") or palette.get("space_id", "") or "")
    contract_names = [key for key, value in metadata.items() if isinstance(value, dict) and value]
    rows = []
    for index, sentence in enumerate(_sentences(direct_text), 1):
        matched = []
        for source in sources:
            if not isinstance(source, dict):
                continue
            blob = _flatten_text(source)
            if any(token in blob for token in _tokens(sentence)[:6]):
                matched.append(str(source.get("subshot_id", "") or ""))
        rows.append({
            "sentence_index": index,
            "text": sentence,
            "source_ids": sorted(set(value for value in matched if value)) or source_ids,
            "scene_lock_ref": scene_lock_ref,
            "contract_fields": contract_names,
            "match_confidence": "source_token_match" if matched else "shot_source_scope",
        })
    return rows


def build_repair_preview(before, after, repair_fields=None):
    before_text = str(before or "")
    after_text = str(after or "")
    return {
        "changed": before_text != after_text,
        "repair_fields": _string_list(repair_fields),
        "before": before_text,
        "after": after_text,
        "diff": list(difflib.unified_diff(
            before_text.splitlines(), after_text.splitlines(),
            fromfile="before", tofile="after", lineterm="",
        )),
    }


def _risk(category, severity, evidence, repair):
    return {"category": category, "severity": severity, "evidence": evidence, "repair": repair}


def _dedupe_risks(risks):
    seen, result = set(), []
    for risk in risks:
        key = (risk["category"], risk["evidence"])
        if key not in seen:
            seen.add(key)
            result.append(risk)
    return result


def _required_flat_fields(contract, prefix, fields):
    return [
        "%s.%s不能为空" % (prefix, field)
        for field in fields if len(str(contract.get(field, "") or "").strip()) < 2
    ]


def _grounded(value, text):
    value = str(value or "").strip()
    if not value:
        return False
    if value in str(text or ""):
        return True
    parts = [part.strip() for part in re.split(r"[，,；;。！？]", value) if len(part.strip()) >= 4]
    return any(part in str(text or "") for part in parts[:4])


def _flatten_text(value):
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(_flatten_text(item) for item in value)
    return str(value or "")


def _string_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in re.split(r"[，,、；;/]", value) if part.strip()]
    return []


def _sentences(text):
    return [part.strip() for part in re.findall(r"[^。！？；;]+[。！？；;]?", str(text or "")) if part.strip()]


def _tokens(text):
    return [token for token in re.findall(r"[\u4e00-\u9fff]{2,8}|[A-Za-z0-9_-]+", str(text or "")) if token not in {"画面", "人物", "镜头", "保持"}]
