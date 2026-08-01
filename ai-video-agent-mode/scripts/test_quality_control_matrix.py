#!/usr/bin/env python3
"""Cross-dimension regression matrix for production quality gates."""

from episode_director_audit import analyze_package as analyze_directing
from episode_state_graph import analyze_package as analyze_state_graph
from production_intelligence import (
    lighting_topology_contract_issues,
    perspective_scale_contract_issues,
    physical_stability_issues,
)
from prompt_contract import (
    cinematic_realism_prompt_issues,
    direct_copy_prompt_issues,
    prompt_information_budget_issues,
)


def main():
    _prompt_information_control()
    _continuity_control()
    _physical_and_scale_control()
    _liveness_control()
    _material_anti_ai_control()
    _light_color_control()
    print("[QUALITY CONTROL MATRIX] PASS - 7 dimensions")


def _prompt_information_control():
    metadata = {"prompt_information_budget": {
        "profile": "object",
        "primary_render_task": "读清钥匙归属变化",
        "must_render": "钥匙起幅在甲右手；钥匙落幅在乙左手",
        "supporting_visual": "门外冷光进入",
        "metadata_only": "权力关系逆转",
        "visual_enhancer_limit": 1,
        "compression_rule": "先整句删除辅助视觉，保留道具起终态",
    }}
    issues = prompt_information_budget_issues(metadata, "钥匙起幅在甲右手。")
    assert any("钥匙落幅在乙左手" in issue for issue in issues), issues
    repeated = "左侧窗光照亮钥匙。左侧窗光照亮钥匙。"
    assert any("重复执行句" in issue for issue in direct_copy_prompt_issues(
        repeated, require_visual_texture=False
    ))


def _continuity_control():
    package = {"shots": [
        {
            "shot_id": "S1", "subshot_id": "S1", "source_subshot_ids": ["SRC-1"],
            "qa_metadata": {"scene_tone_palette": {"space_id": "SP1"}, "continuity_contract": {
                "start_anchor": "角色A屈膝起跳", "end_anchor": "角色A保持空中路径",
                "next_carryover": "角色A沿腾空轨迹保持空中路径", "state_transitions": [],
            }},
        },
        {
            "shot_id": "S2", "subshot_id": "S2", "source_subshot_ids": ["SRC-2"],
            "qa_metadata": {"scene_tone_palette": {"space_id": "SP1"}, "continuity_contract": {
                "start_anchor": "角色A双脚接地站立接地", "end_anchor": "角色A站稳",
                "next_carryover": "角色A站稳", "state_transitions": [],
            }},
        },
    ]}
    result = analyze_state_graph(package)
    assert any("support_mode" in issue or "body_level" in issue for issue in result["issues"]), result


def _physical_and_scale_control():
    walking = "角色A从后景走向镜头，最后停住。"
    assert physical_stability_issues({}, walking, ["角色A"])
    weak = {
        "subjects_depth": "甲在前景，乙在后景", "support_plane": "两人位于地面",
        "projection_scale_rule": "遵循近大远小", "body_ratio_lock": "头身比例不变",
        "motion_scaling": "靠近时变大", "prop_scale_lock": "道具不变",
        "grounding_evidence": "地平线确认纵深", "fallback": "改为同深度中景",
    }
    issues = perspective_scale_contract_issues(
        {"perspective_scale_contract": weak}, "甲在前景，乙在后景，遵循近大远小。", ["甲", "乙"], True
    )
    assert any("真实身高" in issue for issue in issues), issues
    assert any("四肢长度" in issue for issue in issues), issues
    assert any("身高差" in issue for issue in issues), issues


def _liveness_control():
    shots = []
    for index, phrase in enumerate(("镜头缓慢推近", "摄影机轻推", "镜头小幅推进", "摄影机逐渐靠近"), 1):
        shots.append({
            "shot_id": "L%d" % index, "subshot_id": "L%d" % index,
            "scene": "SC-L", "full_prompt": phrase + "，角色A完成不同的剧情动作。",
            "qa_metadata": {},
        })
    result = analyze_directing({"shots": shots})
    assert any("重复灵动性套路camera_push" in issue for issue in result["issues"]), result


def _material_anti_ai_control():
    prompt = "写实电影感，塑料墙与镜面水面非常干净，所有雨线均匀落下。"
    issues = cinematic_realism_prompt_issues(prompt, require_live_action_style=True)
    assert any("AI感/CG感" in issue for issue in issues), issues
    assert any("真实材质" in issue for issue in issues), issues
    assert any("非完美" in issue for issue in issues), issues


def _light_color_control():
    contract = {
        "motivated_source": "室内灯光", "source_direction": "自然方向",
        "temperature_range": "漂亮色彩", "face_light_layer": "人物面部受光",
        "environment_light_layer": "背景灯光", "shadow_exposure_policy": "气氛阴影",
        "volume_light_boundary": "后景光束", "conflict_resolution": "整体更高级",
    }
    issues = lighting_topology_contract_issues(
        {"lighting_topology_contract": contract}, "室内灯光照亮人物面部，背景灯光形成气氛阴影，后景光束。", True
    )
    assert any("可执行光源方向" in issue for issue in issues), issues
    assert any("色温或冷暖关系" in issue for issue in issues), issues
    assert any("面部/肤色优先级" in issue for issue in issues), issues


if __name__ == "__main__":
    main()
