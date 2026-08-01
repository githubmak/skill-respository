#!/usr/bin/env python3
"""Regression tests for the three-state keyframe delivery pipeline."""

from current_keyframe import build_current_shot_keyframe_reference, build_keyframe_sequence
from prompt_contract import aesthetic_directing_contract_issues
from export_with_validation import _build_direct_copy_prompt, _build_director_card


def main():
    task = _fixture()
    sequence = build_keyframe_sequence(task, {"scene": "客厅对峙"}, "16:9", "写实电影级动态漫")
    assert sequence and sequence["pass"], sequence
    assert [frame["label"] for frame in sequence["frames"]] == [
        "起始状态关键帧", "戏眼关键帧", "结束状态关键帧",
    ]
    assert len(sequence["state_diff"]) >= 2
    assert all(item["pass"] for item in sequence["continuity_check"])
    assert all(item["pass"] for item in sequence["fact_consistency"])
    assert "0.0-" in sequence["video_prompt"] and "即梦执行正文" in sequence["video_prompt"]
    assert "门框留白把视线引向抬眼瞬间" in sequence["frames"][1]["prompt"]
    assert "低幅推近在抬眼后减速停稳" in sequence["video_prompt"]
    assert "均匀棚拍光" in sequence["negative_prompt"]
    aesthetic_issues = aesthetic_directing_contract_issues(task["qa_metadata"], task["full_prompt"])
    assert not aesthetic_issues, aesthetic_issues
    incomplete = _fixture()
    incomplete["qa_metadata"]["dynamic_aesthetic_contract"]["camera_path"] = ""
    assert any("camera_path" in issue for issue in aesthetic_directing_contract_issues(
        incomplete["qa_metadata"], incomplete["full_prompt"]
    ))
    assert "手机" in sequence["frames"][0]["prompt"]
    legacy = build_current_shot_keyframe_reference(
        task, {"scene": "客厅对峙"}, "16:9", "写实电影级动态漫"
    )
    assert legacy and legacy["keyframe_prompt"].endswith(sequence["frames"][1]["prompt"])
    export_plan = {"canvas": "16:9", "visual_style": "写实电影级动态漫"}
    direct_copy = _build_direct_copy_prompt(task, export_plan)
    director_card = _build_director_card(task, export_plan)
    assert "写实影像约束（静态美术）" in direct_copy
    assert "视频质感约束（动态美术）" in direct_copy
    assert 180 <= len(director_card) <= 500
    assert "你终于回来了。" in director_card and len(director_card) <= len(direct_copy)

    conflicting = _fixture()
    conflicting["qa_metadata"]["end_state"] = "角色A稳定站在画面右侧，手机仍在右手"
    bad = build_keyframe_sequence(conflicting, {"scene": "客厅对峙"})
    assert bad and not bad["pass"]
    assert any(not item["pass"] for item in bad["fact_consistency"])
    print("keyframe pipeline regression passed")


def _fixture():
    prompt = (
        "生成规格：16:9画幅，8秒，写实电影级动态漫。\n\n"
        "主体与空间锁定：前景桌角轻虚化，中景角色A站在画面左侧，后景角色B弱虚化；两人双脚落在同一连续地面，遵循近大远小，真实体型与头身比例不变。\n\n"
        "主镜头连续规则：角色A右手握手机，手机屏幕朝角色A，背壳朝摄影机，角色B闭口观察。\n\n"
        "子镜头组：0.0-3.0秒角色A低头看手机；3.0-6.0秒角色A看清门口人物，抬眼并把手机从腰间抬到胸前，说“你终于回来了。”；6.0-8.0秒角色A闭口停住，手机稳定在胸前。\n\n"
        "光照、色彩与稳定约束：左前方中性面光照亮角色A脸侧；主色暖灰落在人物与室内空间，辅助低饱和冷色落在门外背景，手机金属边缘冷白反光作点缀；肤色自然，固定机位。"
    )
    return {
        "shot_id": "S1", "subshot_id": "S1-A", "duration": 8, "full_prompt": prompt,
        "qa_metadata": {
            "start_state": "角色A站在画面左侧，右手手机停在腰间",
            "end_state": "角色A稳定站在画面左侧，右手手机停在胸前",
            "dramatic_goal": "角色A用一句话确认对方回归",
            "dialogue_events": [{"text": "你终于回来了。"}],
            "dramatic_design": {"narrative_weight": "high", "information_gain": "对方的回归第一次被确认"},
            "performance_contract": {
                "trigger_event": "看清门口人物", "mask_leak": "抬眼后停半拍", "primary_body_action": "右手把手机抬到胸前",
                "end_residue": "闭口仍看向门口", "start_intensity": 2, "end_intensity": 4,
            },
            "continuity_contract": {
                "start_anchor": "角色A在画面左侧右手持手机", "end_anchor": "角色A在画面左侧右手手机停胸前",
                "next_carryover": "角色A闭口，手机仍在右手胸前",
            },
            "prop_lifecycle_contract": {
                "prop": "手机", "visible_surface": "屏幕朝角色A，背壳朝摄影机", "start_location": "角色A右手腰间",
                "contact_owner": "角色A", "contact_mode": "右手握持", "motion_path": "从腰间抬到胸前",
                "end_location": "角色A胸前", "end_orientation": "屏幕仍朝角色A", "next_shot_state": "亮屏且由角色A右手持有",
            },
            "perspective_scale_contract": {
                "subjects_depth": "角色A在中景，角色B在后景", "support_plane": "两人双脚落在同一连续地面",
                "projection_scale_rule": "遵循近大远小", "body_ratio_lock": "真实体型与头身比例不变",
            },
            "lighting_topology_contract": {
                "motivated_source": "左前方中性面光", "face_light_layer": "照亮角色A脸侧并保持自然肤色",
            },
            "scene_tone_palette": {"visual_scene_prefix": "暖灰客厅，前中后景层次清楚"},
            "visual_bible": {
                "visual_thesis": "克制重逢让观众先看抬眼再看手机",
                "palette_system": "主色暖灰落在人物与室内空间，辅助低饱和冷色落在门外背景，手机金属边缘冷白反光作点缀",
                "light_motivation": "左前方窗光为人物主光，室内暖反光只托住手部",
                "contrast_exposure": "脸部曝光稳定，右脸浅阴影保留层次，高光不过曝",
                "composition_grammar": "门框与桌角构成纵深骨架并保留关系空位",
                "material_world": "棉质衣料哑光，木桌半反光，手机金属边缘压暗",
                "atmosphere_rule": "室内空气干净，后景只保留轻微距离衰减",
                "imperfection_policy": "桌沿细划痕和衣料自然褶皱不均匀分布",
                "reference_policy": "none",
                "continuity_lock": "跨镜保持暖灰基调、左前主光和门框构图家族",
            },
            "static_aesthetic_contract": {
                "visual_intent": "克制重逢，观众先看角色A的眼睛再看右手手机",
                "composition_hierarchy": "门框留白把视线引向抬眼瞬间，角色B只作后景压力",
                "light_design": "左前方中性面光照亮角色A脸侧，右脸浅阴影保留层次",
                "color_grade": "暖灰室内与门外低饱和冷色分离，肤色保持自然",
                "lens_rendering": "50mm眼平中近景，焦平面覆盖双眼和手机边缘",
                "depth_atmosphere": "桌角轻虚化，中景清楚，门口低对比退后",
                "material_anchor": "棉质衣料自然褶皱，手机金属边缘压暗反光",
                "signature_frame": "角色A抬眼停住而手机仍悬在胸前",
                "aesthetic_exclusions": "均匀棚拍光, 平均构图",
            },
            "dynamic_aesthetic_contract": {
                "motion_thesis": "静止被抬眼打破后重新收住",
                "start_state": "角色A低头，固定关系构图保持半拍",
                "trigger": "角色A看清门口人物",
                "primary_subject_motion": "角色A抬眼并把手机从腰间抬到胸前",
                "secondary_environment_motion": "窗帘边缘只有一次低幅摆动",
                "camera_path": "低幅推近在抬眼后减速停稳",
                "focus_behavior": "焦点始终留在角色A双眼，不转焦",
                "material_motion": "棉质袖口随抬手产生轻微褶皱",
                "atmosphere_motion": "后景空气保持稳定，不增加雾粒",
                "tempo_easing": "起幅静止，抬眼稍快，推近平滑减速",
                "end_state": "角色A闭口停住，手机稳定在胸前",
                "stability_fallback": "取消推近并保持固定机位，保留抬眼和手机终态",
            },
            "aesthetic_priority": {
                "visual_thesis": "静止被一次抬眼打破后重新收住",
                "primary_eye_target": "角色A双眼",
                "secondary_visual_layer": "角色A右手手机",
                "must_preserve": "抬眼瞬间、左前主光和门框留白",
                "degrade_first": "后景窗帘运动和低幅推近",
            },
        },
    }


if __name__ == "__main__":
    main()
