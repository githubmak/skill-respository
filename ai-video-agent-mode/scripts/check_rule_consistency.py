#!/usr/bin/env python3
"""Deterministic coverage check for cross-file production-quality rules."""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from contract_registry import PIPELINE_PHASES, machine_contract_issues, pipeline_gates
from pipeline_templates import GATES


RULES = {
    "visible_people_gate": {
        "label": "可见人数闸门",
        "checks": {
            "SKILL.md": ("可见人数闸门",),
            "references/ROUTES.md": ("production_quality_knowledge.md",),
            "references/production_quality_knowledge.md": ("可见人数闸门", "纯画外声不算"),
            "references/format_constraints.md": ("visible_people_gate", "不可见人物不得作为视觉朝向目标"),
            "references/agents/03_master_production_agent.md": ("本镜画面内可见人数", "画外声源"),
            "references/dispatch/master_production_note.md": ("可见人数闸门", "不可见人物不能作为看向"),
            "scripts/validate_composer_output.py": ("visible_people_gate_issues",),
            "scripts/modec_v4.py": ("def visible_people_gate_issues",),
            "scripts/golden_jimeng_check.py": ("dialogue_speaker_pressure",),
        },
    },
    "tone_palette": {
        "label": "制作级影调色卡",
        "checks": {
            "SKILL.md": ("制作级影调色卡",),
            "references/production_quality_knowledge.md": ("制作级影调色卡",),
            "references/format_constraints.md": ("完整色卡", "肤色保护"),
            "references/agents/03_master_production_agent.md": ("制作级影调色卡",),
            "references/dispatch/master_production_note.md": ("制作级影调色卡", "scene_tone_palette"),
            "scripts/modec_v4.py": ("def scene_tone_palette_issues",),
            "scripts/golden_jimeng_check.py": ("live_action_rain_hallway",),
        },
    },
    "shot_components": {
        "label": "镜头组件",
        "checks": {
            "SKILL.md": ("镜头语言使用组件化知识储备",),
            "references/production_quality_knowledge.md": ("镜头组件库",),
            "references/format_constraints.md": ("shot_component_choice",),
            "references/agents/03_master_production_agent.md": ("镜头组件",),
            "references/dispatch/master_production_note.md": ("镜头组件只能作为知识储备使用",),
            "scripts/modec_v4.py": ("shot_component_choice",),
        },
    },
    "physical_structure": {
        "label": "物理结构链",
        "checks": {
            "SKILL.md": ("起始 → 支撑/接触/方向 → 可见转换",),
            "references/production_quality_knowledge.md": ("空间与物理结构",),
            "references/format_constraints.md": ("physical_structure_chain",),
            "references/agents/03_master_production_agent.md": ("物理结构链",),
            "references/dispatch/master_production_note.md": ("物理结构链",),
            "scripts/modec_v4.py": ("def physical_transition_chain_issues",),
            "scripts/validate_composer_output.py": ("physical_transition_chain_issues",),
            "scripts/golden_jimeng_check.py": ("prop_transfer", "single_action_chain"),
        },
    },
    "voice_lock": {
        "label": "角色声音锁定",
        "checks": {
            "SKILL.md": ("角色声音锁定",),
            "references/production_quality_knowledge.md": ("角色声音锁定表",),
            "references/format_constraints.md": ("声音锁定",),
            "references/agents/03_master_production_agent.md": ("声音锁定",),
            "references/dispatch/master_production_note.md": ("项目级声音锁定",),
            "scripts/modec_v4.py": ("dialogue_event_issues",),
        },
    },
    "emotion_micro_performance": {
        "label": "情绪微表演链",
        "checks": {
            "SKILL.md": ("情绪微表演链", "眉眼"),
            "references/production_quality_knowledge.md": ("情绪微表演链", "假装生气", "失望无奈", "悲伤痛苦"),
            "references/format_constraints.md": ("emotion_micro_chain", "情绪微表演链"),
            "references/agents/03_master_production_agent.md": ("表情",),
            "references/dispatch/master_production_note.md": ("情绪微表演链", "禁止只写开心"),
            "scripts/golden_jimeng_check.py": ("micro_emotion_disappointed", "micro_emotion_grief_restraint"),
            "scripts/test_current_pipeline.py": ("情绪微表演链",),
        },
    },
    "performance_baseline_lock": {
        "label": "角色表演基线",
        "checks": {
            "SKILL.md": ("角色表演基线", "爆发阈值"),
            "references/production_quality_knowledge.md": ("角色表演基线", "常态控制方式", "优先情绪泄露部位", "禁用表演习惯"),
            "references/format_constraints.md": ("performance_baseline_lock", "角色表演基线"),
            "references/agents/03_master_production_agent.md": ("performance_baseline_lock", "角色表演基线"),
            "references/dispatch/master_production_note.md": ("角色表演基线", "爆发阈值"),
            "scripts/golden_jimeng_check.py": ("performance_baseline_cold_restraint",),
            "scripts/test_current_pipeline.py": ("performance_baseline_lock",),
            "references/schemas/pipeline.schema.json": ("performance_baseline_lock",),
            "scripts/modec_v4.py": ("performance_baseline_lock",),
        },
    },
    "direct_prompt_density_floor": {
        "label": "直投质量密度底线",
        "checks": {
            "SKILL.md": ("复杂度分档只减内部合同", "低于 180"),
            "references/format_constraints.md": ("复杂度分档只减少内部合同", "低于 180"),
            "references/contracts/direct_copy_contract.md": ("低于 180", "画面描述｜直接复制"),
            "references/dispatch/master_production_note.md": ("复杂度分档只减少内部合同", "低于180"),
            "scripts/golden_jimeng_check.py": ("performance_baseline_cold_restraint",),
        },
    },
    "structured_direct_compiler": {
        "label": "结构化直投编译",
        "checks": {
            "SKILL.md": ("direct_prompt_compiler.py", "禁止静默截断"),
            "references/format_constraints.md": ("direct_prompt_compiler.py", "受保护事实", "只按完整句"),
            "references/contracts/direct_copy_contract.md": ("visual_prefix → space → continuity → performance → light → video_texture → cinematic", "不得静默裁切"),
            "references/export_spec.md": ("direct_prompt_compiler.py", "无法无损压缩"),
            "scripts/direct_prompt_compiler.py": ("def compile_direct_prompt", "PROTECTED_KINDS", "AUXILIARY_KINDS"),
            "scripts/export_with_validation.py": ("compile_direct_prompt", "direct_prompt_compile_report.json"),
            "scripts/test_quality_upgrades.py": ("hard_overflow", "compressed"),
        },
    },
    "episode_quality_audits": {
        "label": "全集状态与导演审计",
        "checks": {
            "SKILL.md": ("episode_state_graph.py", "episode_director_audit.py", "微表演重复"),
            "references/ROUTES.md": ("episode_state_graph.py", "episode_director_audit.py"),
            "references/contracts/contract_index.md": ("全集状态", "导演曲线", "表演重复"),
            "scripts/episode_state_graph.py": ("semantic_lineage", "state_transitions"),
            "scripts/episode_director_audit.py": ("def _audit_tension", "def _audit_camera_and_shot_size", "def _audit_performance_repetition"),
            "scripts/workflow_supervisor.py": ("episode state graph failed", "episode director audit failed"),
            "scripts/test_quality_upgrades.py": ("valid_episode", "flat_result"),
        },
    },
    "dialogue_timing_capacity": {
        "label": "对白自然时长与口型窗",
        "checks": {
            "SKILL.md": ("人物本镜语速", "可见口型窗"),
            "references/format_constraints.md": ("dialogue_timing.py", "自然表演时长", "不得重叠"),
            "references/agents/03_master_production_agent.md": ("对白时间窗", "句末闭口落幅"),
            "references/dispatch/master_production_note.md": ("dialogue_events.time_range", "不得重叠"),
            "scripts/dialogue_timing.py": ("def estimate_event_seconds", "def analyze_dialogue_timing", "speech_rate_cps"),
            "scripts/modec_v4.py": ("analyze_dialogue_timing", "句末闭口/口型闭合落幅"),
            "scripts/test_quality_upgrades.py": ("口型窗重叠", "时间窗"),
        },
    },
    "viewpoint_motion_grammar": {
        "label": "特殊视角运动语法",
        "checks": {
            "SKILL.md": ("特殊视角运动语法", "穿越", "FPV"),
            "references/production_quality_knowledge.md": ("特殊视角与运动语法", "穿越尺度", "ACT 第三人称", "FPV 贴身", "POV 第一人称", "水平横移", "鸟瞰实拍"),
            "references/format_constraints.md": ("viewpoint_motion_lock", "特殊视角运动语法"),
            "references/agents/03_master_production_agent.md": ("viewpoint_motion_lock", "特殊视角"),
            "references/dispatch/master_production_note.md": ("特殊视角", "穿越、ACT、FPV、POV、水平横移、鸟瞰"),
            "scripts/golden_jimeng_check.py": ("viewpoint_scale_traversal", "viewpoint_pov_hospital"),
            "scripts/test_current_pipeline.py": ("特殊视角", "viewpoint_motion_lock"),
            "references/schemas/pipeline.schema.json": ("viewpoint_motion_lock",),
            "scripts/modec_v4.py": ("viewpoint_motion_lock",),
        },
    },
    "frontstage_director_layer": {
        "label": "前台导演精修层",
        "checks": {
            "SKILL.md": ("前台导演精修层", "dialogue_performance_kernel", "emotion_residue_contract", "creative_profile"),
            "references/production_quality_knowledge.md": ("前台导演精修层", "对白表演核", "情绪残留契约", "可控创作档位"),
            "references/format_constraints.md": ("前台导演精修层", "dialogue_performance_kernel", "emotion_residue_contract", "creative_profile"),
            "references/contracts/contract_index.md": ("前台导演精修", "对白表演核", "情绪残留", "创作档位"),
            "references/contracts/direct_copy_contract.md": ("即梦友好导演卡", "dialogue_performance_kernel"),
            "references/contracts/source_basemap_contract.md": ("dialogue_performance_kernel", "emotion_residue_contract", "premium_director_polish", "creative_profile"),
            "references/agents/03_master_production_agent.md": ("前台导演精修层", "dialogue_performance_kernel", "creative_profile"),
            "references/dispatch/master_production_note.md": ("前台导演精修层", "dialogue_performance_kernel", "emotion_residue_contract", "creative_profile"),
            "scripts/dispatch_cache.py": ("dialogue_performance_kernel", "emotion_residue_contract", "premium_director_polish", "creative_profile"),
            "scripts/golden_jimeng_check.py": ("premium_director_polish_card", "dialogue_performance_kernel_card", "emotion_residue_contract_card", "creative_profile_expressive_safe"),
            "scripts/test_current_pipeline.py": ("dialogue_performance_kernel", "emotion_residue_contract", "premium_director_polish", "creative_profile"),
            "references/schemas/pipeline.schema.json": ("dialogue_performance_kernel", "emotion_residue_contract", "premium_director_polish", "creative_profile"),
            "scripts/modec_v4.py": ("dialogue_performance_kernel", "emotion_residue_contract", "premium_director_polish", "creative_profile"),
        },
    },
    "creative_translation_layer": {
        "label": "对白潜台词、内外情绪与构图动机转译层",
        "checks": {
            "SKILL.md": ("inner_emotion/display_intent", "subtext/line_function/turn_relation", "唯一构图优先级"),
            "references/format_constraints.md": ("subtext_visible_evidence", "emotion_delta=end_intensity-start_intensity", "camera_motivation"),
            "references/production_quality_knowledge.md": ("内在情绪 → 对外展示 → 面具泄露", "潜台词可见证据", "构图戏眼"),
            "references/contracts/contract_index.md": ("台词功能、潜台词、原文重音", "面具泄露与情绪变化量", "运镜动机与记忆帧曲线"),
            "references/contracts/direct_copy_contract.md": ("line_function/subtext/turn_relation", "分析标签", "构图戏眼"),
            "references/export_spec.md": ("原文重音词", "潜台词可见证据", "inner_emotion/display_intent/emotion_delta"),
            "references/agents/03_master_production_agent.md": ("面具泄露", "原文重音词", "运镜动机"),
            "references/dispatch/master_production_note.md": ("subtext_visible_evidence", "emotion_delta", "构图优先级"),
            "references/schemas/pipeline.schema.json": ("line_function", "subtext_visible_evidence", "inner_emotion", "emotion_delta", "composition_priority", "camera_motivation"),
            "scripts/dispatch_cache.py": ("line_function", "subtext_visible_evidence", "inner_emotion", "emotion_delta", "composition_priority", "camera_motivation"),
            "scripts/modec_v4.py": ("DIALOGUE_LINE_FUNCTIONS", "mask_leak", "emotion_delta", "composition_priority", "camera_motivation"),
            "scripts/episode_director_audit.py": ("emotion_delta", "memory_frame", "_audit_emotion_and_memory_curve"),
            "scripts/export_with_validation.py": ("原文重音词", "subtext_visible_evidence", "story_punch_contract"),
            "scripts/golden_jimeng_check.py": ("dialogue_subtext_stress_card", "masked_emotion_leak_card", "composition_camera_motivation_card"),
            "scripts/test_quality_upgrades.py": ("subtext不能复述原台词", "emotion_delta必须等于", "必须说明镜头为何响应"),
        },
    },
    "source_fidelity_split": {
        "label": "普通动作行、OV可见性与少镜头保真拆分",
        "checks": {
            "SKILL.md": ("无前缀的普通剧本动作行", "OV 说话者只锁为声音来源", "每个动作/对白 source ID"),
            "references/format_constraints.md": ("普通无前缀剧本动作", "SOURCE_UNIT_UNASSIGNED", "纯 OV 镜允许可见人物列表为空"),
            "scripts/generate_shotplan.py": ("_pack_source_actions_with_interactions", "_action_cues_following_speech", "_offscreen_character_mention", "_characters_in_source_order"),
            "scripts/preflight_check.py": ("SOURCE_UNIT_UNASSIGNED", "OV_SPEAKER_VISIBLE_LOCK", "OV-only shots"),
            "scripts/test_quality_upgrades.py": ("packed_source", "SRC4", "_offscreen_character_mention"),
            "scripts/test_source_smoke.py": ("assigned_source_unit_count", "ov_event_count", "OV speaker was locked as visible"),
        },
    },
    "structural_routing": {
        "label": "结构化路由",
        "checks": {
            "SKILL.md": ("contracts/contract_index.md", "references/dispatch/*.md"),
            "references/ROUTES.md": ("contracts/contract_index.md", "dispatch/master_production_note.md"),
            "references/contracts/contract_index.md": ("direct_copy_contract.md", "source_basemap_contract.md", "visual_quality_contract.md"),
            "references/contracts/source_basemap_contract.md": ("performance_baseline_lock", "viewpoint_motion_lock"),
            "references/contracts/visual_quality_contract.md": ("video_texture_contract", "cinematic_image_contract"),
            "scripts/dispatch_cache.py": ("def _phase_note_text", "references\", \"dispatch"),
            "references/dispatch/scene_lock_note.md": ("场景锁定 Agent", "space_id"),
            "references/dispatch/editor_pass2_note.md": ("§B/§C", "语义审查 JSON"),
        },
    },
}


def check(skill_root):
    issues = []
    issues.extend("机器契约：" + issue for issue in machine_contract_issues())
    if tuple(GATES) != PIPELINE_PHASES:
        issues.append("pipeline_templates.GATES顺序必须由机器契约生成")
    if GATES != pipeline_gates():
        issues.append("pipeline_templates.GATES与机器契约产物边界不一致")
    for key, rule in RULES.items():
        for relative, tokens in rule["checks"].items():
            path = os.path.join(skill_root, relative)
            text = _read(path)
            if text is None:
                issues.append("%s缺少文件：%s" % (rule["label"], relative))
                continue
            missing = [token for token in tokens if token not in text]
            if missing:
                issues.append("%s在%s缺少：%s" % (rule["label"], relative, "、".join(missing)))
    dispatch = _read(os.path.join(skill_root, "scripts", "dispatch_cache.py")) or ""
    if '{"B0", "B1", "B2", "B3", "B5", "B6", "B7"}' not in dispatch:
        issues.append("Master Production sidecar未选择B0/B2/B7质量合同段")
    for relative in (
        "SKILL.md", "references/ROUTES.md", "references/stage_gates.md",
        "references/export_spec.md", "references/format_constraints.md",
        "scripts/validate_composer_output.py", "scripts/validate_modec.py",
        "scripts/generate_shotplan.py", "scripts/route_task.py",
    ):
        text = _read(os.path.join(skill_root, relative)) or ""
        legacy = sorted(set(re.findall(r"Phase\s+[0-9]+(?:\s*[-/]\s*[0-9]+)?", text)))
        if legacy:
            issues.append("当前契约文件%s含废弃编号阶段术语：%s" % (relative, "、".join(legacy)))
    return {"pass": not issues, "issues": issues, "rule_count": len(RULES)}


def _read(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return handle.read()
    except OSError:
        return None


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(__file__))
    result = check(root)
    print("[RULE CONSISTENCY] %s" % ("PASS" if result["pass"] else "FAIL"))
    for issue in result["issues"]:
        print("- " + issue)
    raise SystemExit(0 if result["pass"] else 1)
