#!/usr/bin/env python3
"""Focused deterministic tests for production-intelligence contracts."""

from production_intelligence import (
    analyze_sequence_curves,
    build_emotion_visible_state,
    build_repair_preview,
    build_sentence_provenance,
    classify_visual_prior_risks,
    lighting_topology_contract_issues,
    multi_person_attention_budget_issues,
    perspective_scale_contract_issues,
    predict_action_failure,
    prop_lifecycle_contract_issues,
)


def main():
    _test_visual_prior_classifier()
    _test_multi_person_attention()
    _test_prop_and_action_contracts()
    _test_perspective_and_lighting()
    _test_sequence_emotion_provenance_and_repair()
    print("[PRODUCTION INTELLIGENCE] PASS")


def _categories(prompt, source=""):
    return {item["category"] for item in classify_visual_prior_risks(prompt, source)}


def _test_visual_prior_classifier():
    assert "negative_concept_priming" in _categories("女人不戴护士帽，站在客厅")
    assert "back_facing_eyeline" in _categories("男人背对镜头，望向某人")
    assert "back_facing_eyeline" not in _categories(
        "男人背对镜头，胸口朝窗，头向画面左转20度，看向门口固定声源"
    )
    assert "mirror_reflection_geometry" in _categories("女孩看着镜中倒影")
    assert "unsupported_display_prior" in _categories("男孩把手机正对镜头", "男孩玩手机游戏")
    assert "vehicle_eyeline_physics" in _categories("男人驾驶汽车，长时间看向后方")
    assert "occlusion_person_spawn" in _categories("前景肩线遮住镜中倒影")


def _test_multi_person_attention():
    visible = ["甲", "乙", "丙"]
    metadata = {
        "performance_priority": {"primary": "甲", "supporting": ["乙"], "background": ["丙"]},
        "attention_handoff": {"handoff_count": 1},
    }
    prompt = "甲主表演，乙观察反应，丙在后景弱虚化不抢焦。"
    assert not multi_person_attention_budget_issues(metadata, prompt, visible)
    metadata["attention_handoff"]["handoff_count"] = 2
    assert any("最多一次" in issue for issue in multi_person_attention_budget_issues(metadata, prompt, visible))


def _test_prop_and_action_contracts():
    contract = {
        "prop": "手机", "purpose": "游戏操作", "visible_surface": "屏幕朝男孩",
        "start_location": "男孩右手掌心", "contact_owner": "男孩", "contact_mode": "右手托底并拇指滑动",
        "motion_path": "保持在胸前小幅移动", "end_location": "男孩胸前", "end_orientation": "屏幕仍朝男孩",
        "next_shot_state": "男孩继续持有且亮屏",
    }
    prompt = "手机从男孩右手掌心保持在胸前小幅移动，右手托底并拇指滑动，屏幕朝男孩，最终停在男孩胸前，屏幕仍朝男孩。"
    assert not prop_lifecycle_contract_issues({"prop_lifecycle_contract": contract}, prompt, True)
    broken = dict(contract, end_location="男孩右手掌心")
    assert prop_lifecycle_contract_issues({"prop_lifecycle_contract": broken}, prompt, True)
    risky = {
        "full_prompt": "角色同时递出手机并抓住对方，摄影机环绕，玻璃倒影遮挡，没有稳定终态。",
        "qa_metadata": {"action_budget": {"primary_action_count": 2, "physical_camera_move_count": 1}},
    }
    prediction = predict_action_failure(risky)
    assert prediction["risk_level"] == "high" and prediction["score"] >= 55


def _test_perspective_and_lighting():
    perspective = {
        "subjects_depth": "甲在前景，乙在后景", "support_plane": "两人双脚落在同一连续地面",
        "projection_scale_rule": "遵循近大远小，甲画面占比大于乙", "body_ratio_lock": "两人真实体型与头身比例不变",
        "motion_scaling": "乙靠近镜头时画面占比连续增大", "prop_scale_lock": "手机真实尺寸相对持有者手掌不变",
        "grounding_evidence": "脚底接触点、地平线和遮挡关系共同确认纵深", "fallback": "纵深不稳定时改为同一深度双人中景",
    }
    perspective_prompt = "甲在前景，乙在后景；两人双脚落在同一连续地面。遵循近大远小，甲画面占比大于乙，两人真实体型与头身比例不变。脚底接触点、地平线和遮挡关系共同确认纵深。"
    assert not perspective_scale_contract_issues(
        {"perspective_scale_contract": perspective}, perspective_prompt, ["甲", "乙"], True
    )
    assert perspective_scale_contract_issues({}, perspective_prompt, ["甲", "乙"], True)
    lighting = {
        "motivated_source": "窗外日光", "source_direction": "画面左前方",
        "temperature_range": "主光5200K、室内环境光3800K", "face_light_layer": "面部中性补光保护肤色与眼窝层次",
        "environment_light_layer": "暖色只落在木墙与桌面", "shadow_exposure_policy": "鼻翼阴影保留细节不过曝",
        "volume_light_boundary": "丁达尔光束只穿过后景薄雾，不扫过脸", "conflict_resolution": "面部优先中性曝光，环境综合色不污染皮肤",
    }
    lighting_prompt = "窗外日光来自画面左前方，主光5200K、室内环境光3800K；面部中性补光保护肤色与眼窝层次，暖色只落在木墙与桌面，鼻翼阴影保留细节不过曝；丁达尔光束只穿过后景薄雾，不扫过脸。"
    assert not lighting_topology_contract_issues({"lighting_topology_contract": lighting}, lighting_prompt, True)


def _test_sequence_emotion_provenance_and_repair():
    shots = []
    for index, (tension, size, motion, distance) in enumerate((
        ("latent", "全景", "", "远处"), ("rising", "中景", "推近", ""),
        ("peak", "近景", "", "贴近"), ("release", "中远景", "拉远", "拉开距离"),
    ), 1):
        shots.append({
            "shot_id": "S%d" % index,
            "full_prompt": "%s，%s，%s" % (size, motion, distance),
            "qa_metadata": {"emotion_driver": {"tension_intent": tension}},
        })
    curves = analyze_sequence_curves(shots)
    assert len(curves["nodes"]) == 4 and not curves["warnings"]
    state = build_emotion_visible_state({"qa_metadata": {"performance_contract": {
        "trigger_event": "门响", "mask_leak": "眼神停顿", "primary_body_action": "肩线收紧",
        "voice_or_breath_control": "吸气停半拍", "end_residue": "仍盯着门口",
        "start_intensity": 2, "end_intensity": 4, "emotion_delta": 2,
    }}})
    assert state["trigger"] == "门响" and state["residue"] == "仍盯着门口"
    task = {
        "_scene_lock_ref": "SL-SC1", "source_subshots": [{"subshot_id": "S1-A", "base_action": "男孩玩手机游戏"}],
        "qa_metadata": {"prop_lifecycle_contract": {"prop": "手机"}},
    }
    provenance = build_sentence_provenance(task, "男孩低头玩手机游戏。屏幕朝向男孩。")
    assert provenance and all(row["scene_lock_ref"] == "SL-SC1" for row in provenance)
    assert "S1-A" in provenance[0]["source_ids"]
    preview = build_repair_preview("屏幕朝镜头", "屏幕朝男孩", ["prop_lifecycle_contract.visible_surface"])
    assert preview["changed"] and preview["diff"] and preview["repair_fields"]


if __name__ == "__main__":
    main()
