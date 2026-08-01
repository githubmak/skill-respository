"""Deterministic production intelligence shared by validation and export.

These helpers derive risk and audit artifacts from the canonical package. They
do not add model calls or duplicate prompt facts into dispatch packets.
"""

from __future__ import annotations

import difflib
import re


NEGATIVE_VISUAL_CONCEPTS = (
    "护士帽", "护士服", "白大褂", "医院", "病房", "校服", "教室",
    "警帽", "警服", "警局", "军装", "婚纱", "教堂", "囚服", "法庭",
)
PROP_WORDS = (
    "手机", "平板", "电脑", "书", "文件", "照片", "证件", "镜子", "镜面",
    "表盘", "杯", "钥匙", "卡", "银行卡", "笔", "包", "外套", "武器",
)
PROP_ACTIONS = (
    "拿", "握", "递", "接", "放", "推", "拉", "翻", "看", "读", "展示",
    "操作", "点击", "滑动", "塞", "取出", "收起", "佩戴", "脱下",
)
DEPTH_TERMS = ("前景", "中景", "后景", "近处", "远处", "靠近镜头", "远离镜头")
COLLECTIVE_SUBJECTS = ("所有清晰入画人物", "全部清晰入画人物", "所有可见人物")
DEPTH_MOTION_TERMS = ("靠近镜头", "远离镜头", "走向镜头", "走入前景", "退向后景", "从后景走向", "沿景深")
LOCOMOTION_TERMS = ("行走", "走向", "走近", "跑向", "奔向", "追逐", "上楼", "下楼")
SUPPORTED_POSTURE_TERMS = ("坐下", "坐在", "坐着", "靠坐", "躺", "卧", "伏", "趴", "骑马", "骑乘", "倒地")
AIRBORNE_POSTURE_TERMS = ("轻功", "腾空", "跃起", "跳起", "飞行", "凌空", "被击飞", "坠落", "下落")


def classify_visual_prior_risks(prompt, source_text=""):
    """Return explicit/implicit visual-prior risks with positive repair hints."""
    text = str(prompt or "")
    source = str(source_text or "")
    risks = []
    for concept in NEGATIVE_VISUAL_CONCEPTS:
        if re.search(r"(?:不要|禁止|避免|不是|没有|不戴|不穿|去掉).{0,5}" + re.escape(concept), text):
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


def prop_lifecycle_risk(value):
    text = _flatten_text(value)
    return any(prop in text for prop in PROP_WORDS) and any(action in text for action in PROP_ACTIONS)


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
