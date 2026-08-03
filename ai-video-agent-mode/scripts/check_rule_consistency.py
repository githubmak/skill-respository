#!/usr/bin/env python3
"""Deterministic coverage check for cross-file production-quality rules."""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from contract_registry import (
    PIPELINE_PHASES, PROMPT_CONTRACT_VERSION, machine_contract_issues,
    pipeline_gates,
)
from audit_skill_surface import audit as audit_skill_surface
from pipeline_templates import GATES
from route_task import ROUTES as TASK_ROUTES


RULES = {
    "skill_control_plane": {
        "label": "技能最小控制面与按需上下文",
        "checks": {
            "SKILL.md": (
                "route_task.py", "context_plan.read_first", "workflow_supervisor.py",
                "packet._batch_output_path", "上下文预算", "contracts/contract_index.md",
            ),
            "references/ROUTES.md": (
                "read_first", "read_on_demand", "run_only", "不在正常",
            ),
            "scripts/route_task.py": (
                '"context_plan"', '"read_first"', '"read_on_demand"',
                '"run_only"', '"preload_full_contracts": False',
            ),
        },
    },
    "risk_gated_qa_scaffolds": {
        "label": "风险专项合同按需脚手架",
        "checks": {
            "SKILL.md": ("专业能力按风险进入 Master 字段", "稳定产物接口"),
            "references/format_constraints.md": (
                "scaffold 缺席即不适用", "不得补回空对象", "输出必须省略",
            ),
            "references/dispatch/master_production_note.md": (
                "缺席即不适用", "不得补回",
            ),
            "scripts/contract_registry.py": (
                "RISK_GATED_QA_FIELDS", "core and risk-gated QA fields overlap",
            ),
            "scripts/dispatch_cache.py": (
                "RISK_GATED_QA_FIELDS.items()", "metadata.pop(field, None)",
                "scaffold-present risk fields only",
            ),
            "scripts/test_current_pipeline.py": (
                "all(field not in light_scaffold_metadata", "high_scaffold_profile",
            ),
            "scripts/run_regression_suite.py": (
                '"skill_surface"', '"audit_skill_surface.py"',
            ),
        },
    },
    "prop_functional_surface_orientation": {
        "label": "道具功能面朝向与手机翻屏防护",
        "checks": {
            "references/production_quality_knowledge.md": ("道具功能面与摄影机可见面", "content_visibility", "不要只写“不要翻屏”"),
            "references/format_constraints.md": ("prop_functional_surface_contract", "hidden/partial/readable/post_overlay/not_applicable", "普通静置和递交不触发"),
            "references/contracts/contract_index.md": ("道具功能面朝向", "prop_functional_surface_contract_issues"),
            "references/contracts/direct_copy_contract.md": ("功能面道具风险镜", "camera_half_space"),
            "references/dispatch/master_production_note.md": ("prop_functional_surface_contract", "不得用“禁止翻转”替代空间事实"),
            "references/export_spec.md": ("道具功能面合同", "prop_functional_surface_contract"),
            "references/schemas/pipeline.schema.json": ("prop_functional_surface_contract", "camera_visible_surface", "content_visibility"),
            "scripts/shot_semantics.py": ("def functional_surface_risk", "FUNCTIONAL_SURFACE_USE_WORDS"),
            "scripts/dispatch_cache.py": ("functional_surface_risk", "prop_functional_surface_contract"),
            "scripts/prompt_contract.py": ("def prop_functional_surface_contract_issues", "FUNCTIONAL_SURFACE_VISIBILITY_MODES"),
            "scripts/validate_composer_output.py": ("prop_functional_surface_contract_issues",),
            "scripts/export_with_validation.py": ("道具功能面合同", "prop_functional_surface_contract"),
            "scripts/test_quality_upgrades.py": ("_valid_hidden_surface_case", "flipped_prompt", "readable_metadata"),
            "scripts/test_current_pipeline.py": ("functional_surface_risk", "男孩双手横握手机玩游戏"),
        },
    },
    "skin_tone_protection": {
        "label": "人物肤色保护与环境光影边界",
        "checks": {
            "references/production_quality_knowledge.md": ("skin_tone_protection_contract", "丁达尔/体积光束", "motivated_color_cast"),
            "references/format_constraints.md": ("skin_tone_protection_contract", "environment_color_boundary", "texture_atmosphere_boundary"),
            "references/contracts/visual_quality_contract.md": ("skin_tone_protection_contract", "脸部主光/补光"),
            "references/contracts/contract_index.md": ("人物肤色、面光曝光", "skin_tone_protection_contract_issues"),
            "references/dispatch/master_production_note.md": ("skin_tone_protection_contract", "把空气介质退后"),
            "references/export_spec.md": ("肤色保护合同", "skin_tone_protection_contract"),
            "references/schemas/pipeline.schema.json": ("skin_tone_protection_contract", "protection_mode", "texture_atmosphere_boundary"),
            "scripts/shot_semantics.py": ("skin_tone_protection_contract", "has_character_performance"),
            "scripts/dispatch_cache.py": ("skin_tone_protection_contract", "natural_protected"),
            "scripts/prompt_contract.py": ("def skin_tone_protection_contract_issues", "ACCIDENTAL_FACE_CONTAMINATION_PATTERNS"),
            "scripts/validate_composer_output.py": ("skin_tone_protection_contract_issues",),
            "scripts/export_with_validation.py": ("肤色保护合同", "skin_tone_protection_contract"),
            "scripts/test_quality_upgrades.py": ("skin_tone_protection_contract_issues", "青绿色渗入脸部"),
            "scripts/test_current_pipeline.py": ("skin_tone_protection_contract", "清晰人物表演镜"),
            "scripts/golden_jimeng_check.py": ("cold_cyan_clean_face", "tyndall_beam_clean_face"),
        },
    },
    "natural_conversation_rhythm": {
        "label": "真实会话节奏与源文约束",
        "checks": {
            "references/production_quality_knowledge.md": ("真实会话异常", "答非所问", "不把普通顺序对白强行演成争抢"),
            "references/contracts/contract_index.md": ("会话源文依据", "dialogue_event_issues"),
            "references/contracts/direct_copy_contract.md": ("conversation_mode", "可见停顿/抢话/收句"),
            "references/format_constraints.md": ("conversation_mode", "overlap_or_interrupt_window", "conversation_source_basis"),
            "references/dispatch/master_production_note.md": ("response_latency", "短暂声音重叠"),
            "references/export_spec.md": ("会话模式", "抢话/打断窗口", "conversation_source_basis"),
            "references/schemas/pipeline.schema.json": ("conversation_mode", "response_latency", "conversation_source_basis"),
            "scripts/dispatch_cache.py": ("conversation_mode", "overlap_or_interrupt_window", "conversation_source_basis"),
            "scripts/prompt_contract.py": ("CONVERSATION_MODES", "非顺序轮次必须写overlap_or_interrupt_window"),
            "scripts/export_with_validation.py": ("会话模式", "抢话/打断窗口", "conversation_source_basis"),
            "scripts/test_quality_upgrades.py": ("interrupted_issues", "overlapping_issues", "leaked_conversation_analysis"),
        },
    },
    "character_action_relationship_arc": {
        "label": "角色戏剧行动与关系情绪弧",
        "checks": {
            "references/production_quality_knowledge.md": ("角色戏剧行动与关系弧", "当前策略", "关系终态"),
            "references/format_constraints.md": ("character_scene_objective_contract", "relationship_emotion_arc", "power_state_change"),
            "references/dispatch/master_production_note.md": ("character_scene_objective_contract", "relationship_emotion_arc"),
            "references/schemas/pipeline.schema.json": ("character_scene_objective_contract", "relationship_emotion_arc"),
            "scripts/dispatch_cache.py": ("character_scene_objective_contract", "relationship_emotion_arc"),
            "scripts/prompt_contract.py": ("def character_scene_objective_issues", "def relationship_emotion_arc_issues"),
            "scripts/episode_director_audit.py": ("_audit_character_and_relationship_arcs", "active_tactic"),
            "scripts/test_quality_upgrades.py": ("_valid_directing_contracts", "bad_objective"),
        },
    },
    "landscape_environment_story": {
        "label": "风景美学与环境叙事",
        "checks": {
            "references/production_quality_knowledge.md": ("风景美学与环境叙事", "自然运动系统", "镜头呼吸"),
            "references/format_constraints.md": ("landscape_identity/landscape_composition", "environment_story_arc", "breathing_policy"),
            "references/dispatch/scene_lock_note.md": ("landscape_identity", "natural_motion_system", "breathing_policy"),
            "references/dispatch/master_production_note.md": ("landscape_identity/landscape_composition", "风景身份"),
            "references/schemas/pipeline.schema.json": ("landscape_identity", "environment_story_arc", "breathing_policy"),
            "scripts/validate_scene_locks.py": ("landscape_identity", "environment_story_arc", "breathing_policy"),
            "scripts/prompt_contract.py": ("风景身份/构图/自然运动", "light_weather_progression"),
            "scripts/export_with_validation.py": ("风景身份与构图", "环境演进与呼吸"),
            "scripts/golden_jimeng_check.py": ("ancient_mountain_landscape_arc", "rural_rain_environment_story", "coastal_release_landscape"),
        },
    },
    "sequence_cut_directing": {
        "label": "序列导演语言与剪辑切点",
        "checks": {
            "references/production_quality_knowledge.md": ("序列导演语言与联合调度", "剪辑切点与镜头经济性"),
            "references/format_constraints.md": ("sequence_directing_plan", "cut_decision_contract", "scene_transition"),
            "references/dispatch/master_production_note.md": ("sequence_directing_plan", "cut_decision_contract"),
            "references/schemas/pipeline.schema.json": ("sequence_directing_plan", "cut_decision_contract"),
            "scripts/dispatch_cache.py": ("sequence_directing_plan", "cut_decision_contract"),
            "scripts/prompt_contract.py": ("def sequence_directing_plan_issues", "def cut_decision_contract_issues"),
            "scripts/episode_director_audit.py": ("_audit_sequence_cut_and_environment", "cut_information_gain"),
            "scripts/test_quality_upgrades.py": ("bad_sequence", "bad_cut"),
        },
    },
    "adaptive_prompt_information_budget": {
        "label": "自适应提示词信息预算",
        "checks": {
            "references/production_quality_knowledge.md": ("自适应信息预算", "environment：", "dialogue："),
            "references/format_constraints.md": ("prompt_information_budget", "visual_enhancer_limit"),
            "references/dispatch/master_production_note.md": ("prompt_information_budget", "新增导演合同不构成加长正文"),
            "references/schemas/pipeline.schema.json": ("prompt_information_budget", "visual_enhancer_limit"),
            "scripts/dispatch_cache.py": ("prompt_information_budget", "visual_enhancer_limit"),
            "scripts/prompt_contract.py": ("def prompt_information_budget_issues", "PROMPT_INFORMATION_PROFILES"),
            "scripts/test_quality_upgrades.py": ("bad_budget", "visual_enhancer_limit"),
        },
    },
    "spatial_sound_directing": {
        "label": "空间声音与声画导演",
        "checks": {
            "references/production_quality_knowledge.md": ("空间声音与声画导演", "房间响应", "声音可以先于画面进入"),
            "references/format_constraints.md": ("sound_directing_plan", "source_direction_distance", "lead_lag_strategy"),
            "references/dispatch/master_production_note.md": ("sound_directing_plan", "空间声"),
            "references/schemas/pipeline.schema.json": ("sound_directing_plan", "room_environment_response"),
            "scripts/dispatch_cache.py": ("sound_directing_plan", "lead_lag_strategy"),
            "scripts/prompt_contract.py": ("def sound_directing_plan_issues", "SOUND_DIRECTING_PLAN_FIELDS"),
            "scripts/test_quality_upgrades.py": ("sound_directing_plan_issues", "source_direction_distance"),
        },
    },
    "lived_in_scene_depth": {
        "label": "场景生活化与景深层次",
        "checks": {
            "references/production_quality_knowledge.md": ("场景生活化与景深层次", "foreground_layer", "lived_in_detail", "“舒服”不是直接提示词"),
            "references/format_constraints.md": ("foreground_layer/midground_layer/background_layer", "题材视觉气味", "生活痕迹"),
            "references/dispatch/scene_lock_note.md": ("genre_visual_signature", "lived_in_detail", "depth_focus_policy"),
            "references/dispatch/master_production_note.md": ("foreground_layer/midground_layer/background_layer", "至少两层具体空间细节"),
            "references/schemas/pipeline.schema.json": ("foreground_layer", "genre_visual_signature", "depth_focus_policy"),
            "scripts/validate_scene_locks.py": ("foreground_layer", "lived_in_detail", "depth_focus_policy"),
            "scripts/prompt_contract.py": ("至少两层具体场景细节", "题材视觉气味或生活化使用痕迹"),
            "scripts/export_with_validation.py": ("前中后景层次", "题材与生活质感", "depth_focus_policy"),
            "scripts/golden_jimeng_check.py": ("lived_in_scene_depth_card",),
            "scripts/test_current_pipeline.py": ("layered_prompt", "至少两层", "scene_rows"),
        },
    },
    "high_quality_fast_mode": {
        "label": "高质量快速模式",
        "checks": {
            "references/ROUTES.md": ("高质量快速模式", "--auto-start", "全部八个基础字段"),
            "references/project_config.template.json": ("高质量快速模式", "模板值不等于用户确认"),
            "scripts/configuration_wizard.py": ("def confirm_all", "batch config must explicitly provide"),
            "scripts/route_task.py": ("def high_quality_fast_start", "quality_pipeline_preserved", "skipped_phases"),
            "scripts/test_fast_start.py": ("host_dispatch_required", "incomplete batch config was accepted", "dirty run_dir was accepted"),
            "scripts/run_regression_suite.py": ("fast_start", "test_fast_start.py"),
        },
    },
    "visible_people_gate": {
        "label": "可见人数闸门",
        "checks": {
            "references/ROUTES.md": ("production_quality_knowledge.md",),
            "references/production_quality_knowledge.md": ("可见人数闸门", "纯画外声不算"),
            "references/format_constraints.md": ("visible_people_gate", "不可见人物不得作为视觉朝向目标"),
            "references/dispatch/master_production_note.md": ("可见人数闸门", "不可见人物不能作为看向"),
            "scripts/validate_composer_output.py": ("visible_people_gate_issues",),
            "scripts/prompt_contract.py": ("def visible_people_gate_issues",),
            "scripts/golden_jimeng_check.py": ("dialogue_speaker_pressure",),
        },
    },
    "tone_palette": {
        "label": "制作级影调色卡",
        "checks": {
            "references/production_quality_knowledge.md": ("制作级影调色卡",),
            "references/format_constraints.md": ("完整色卡", "肤色保护"),
            "references/dispatch/master_production_note.md": ("制作级影调色卡", "scene_tone_palette"),
            "scripts/prompt_contract.py": ("def scene_tone_palette_issues",),
            "scripts/golden_jimeng_check.py": ("live_action_rain_hallway",),
        },
    },
    "shot_components": {
        "label": "镜头组件",
        "checks": {
            "references/production_quality_knowledge.md": ("镜头组件库",),
            "references/format_constraints.md": ("shot_component_choice",),
            "references/dispatch/master_production_note.md": ("镜头组件只能作为知识储备使用",),
            "scripts/prompt_contract.py": ("shot_component_choice",),
        },
    },
    "physical_structure": {
        "label": "物理结构链",
        "checks": {
            "references/production_quality_knowledge.md": ("空间与物理结构",),
            "references/format_constraints.md": ("physical_structure_chain",),
            "references/dispatch/master_production_note.md": ("物理结构链",),
            "scripts/prompt_contract.py": ("def physical_transition_chain_issues",),
            "scripts/validate_composer_output.py": ("physical_transition_chain_issues",),
            "scripts/golden_jimeng_check.py": ("prop_transfer", "single_action_chain"),
        },
    },
    "voice_lock": {
        "label": "角色声音锁定",
        "checks": {
            "references/production_quality_knowledge.md": ("角色声音锁定表",),
            "references/format_constraints.md": ("声音锁定",),
            "references/dispatch/master_production_note.md": ("项目级声音锁定",),
            "scripts/prompt_contract.py": ("dialogue_event_issues",),
        },
    },
    "emotion_micro_performance": {
        "label": "情绪微表演链",
        "checks": {
            "references/production_quality_knowledge.md": ("情绪微表演链", "假装生气", "失望无奈", "悲伤痛苦"),
            "references/format_constraints.md": ("emotion_micro_chain", "情绪微表演链"),
            "references/dispatch/master_production_note.md": ("情绪微表演链", "禁止只写开心"),
            "scripts/golden_jimeng_check.py": ("micro_emotion_disappointed", "micro_emotion_grief_restraint"),
            "scripts/test_current_pipeline.py": ("情绪微表演链",),
        },
    },
    "performance_baseline_lock": {
        "label": "角色表演基线",
        "checks": {
            "references/production_quality_knowledge.md": ("角色表演基线", "常态控制方式", "优先情绪泄露部位", "禁用表演习惯"),
            "references/format_constraints.md": ("performance_baseline_lock", "角色表演基线"),
            "references/dispatch/master_production_note.md": ("角色表演基线", "爆发阈值"),
            "scripts/golden_jimeng_check.py": ("performance_baseline_cold_restraint",),
            "scripts/test_current_pipeline.py": ("performance_baseline_lock",),
            "references/schemas/pipeline.schema.json": ("performance_baseline_lock",),
            "scripts/prompt_contract.py": ("performance_baseline_lock",),
        },
    },
    "direct_prompt_density_floor": {
        "label": "直投必要语义底线",
        "checks": {
            "references/format_constraints.md": ("复杂度分档只减少内部合同", "不设最低字数"),
            "references/contracts/direct_copy_contract.md": ("不设最低字数", "画面描述｜直接复制"),
            "references/dispatch/master_production_note.md": ("复杂度分档只减少内部合同", "不设最低字数"),
            "scripts/golden_jimeng_check.py": ("performance_baseline_cold_restraint",),
        },
    },
    "structured_direct_compiler": {
        "label": "结构化直投编译",
        "checks": {
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
            "references/format_constraints.md": ("dialogue_timing.py", "自然表演时长", "不得重叠"),
            "references/dispatch/master_production_note.md": ("dialogue_events.time_range", "不得重叠"),
            "scripts/dialogue_timing.py": ("def estimate_event_seconds", "def analyze_dialogue_timing", "speech_rate_cps"),
            "scripts/prompt_contract.py": ("analyze_dialogue_timing", "句末闭口/口型闭合落幅"),
            "scripts/test_quality_upgrades.py": ("口型窗重叠", "时间窗"),
        },
    },
    "viewpoint_motion_grammar": {
        "label": "特殊视角运动语法",
        "checks": {
            "references/production_quality_knowledge.md": ("特殊视角与运动语法", "穿越尺度", "ACT 第三人称", "FPV 贴身", "POV 第一人称", "水平横移", "鸟瞰实拍"),
            "references/format_constraints.md": ("viewpoint_motion_lock", "特殊视角运动语法"),
            "references/dispatch/master_production_note.md": ("特殊视角", "穿越、ACT、FPV、POV、水平横移、鸟瞰"),
            "scripts/golden_jimeng_check.py": ("viewpoint_scale_traversal", "viewpoint_pov_hospital"),
            "scripts/test_current_pipeline.py": ("特殊视角", "viewpoint_motion_lock"),
            "references/schemas/pipeline.schema.json": ("viewpoint_motion_lock",),
            "scripts/prompt_contract.py": ("viewpoint_motion_lock",),
        },
    },
    "frontstage_director_layer": {
        "label": "前台导演精修层",
        "checks": {
            "references/production_quality_knowledge.md": ("前台导演精修层", "对白表演核", "情绪残留契约", "可控创作档位"),
            "references/format_constraints.md": ("前台导演精修层", "dialogue_performance_kernel", "emotion_residue_contract", "creative_profile"),
            "references/contracts/contract_index.md": ("前台导演精修", "对白表演核", "情绪残留", "创作档位"),
            "references/contracts/direct_copy_contract.md": ("即梦友好导演卡", "dialogue_performance_kernel"),
            "references/contracts/source_basemap_contract.md": ("dialogue_performance_kernel", "emotion_residue_contract", "premium_director_polish", "creative_profile"),
            "references/dispatch/master_production_note.md": ("前台导演精修层", "dialogue_performance_kernel", "emotion_residue_contract", "creative_profile"),
            "scripts/dispatch_cache.py": ("dialogue_performance_kernel", "emotion_residue_contract", "premium_director_polish", "creative_profile"),
            "scripts/golden_jimeng_check.py": ("premium_director_polish_card", "dialogue_performance_kernel_card", "emotion_residue_contract_card", "creative_profile_expressive_safe"),
            "scripts/test_current_pipeline.py": ("dialogue_performance_kernel", "emotion_residue_contract", "premium_director_polish", "creative_profile"),
            "references/schemas/pipeline.schema.json": ("dialogue_performance_kernel", "emotion_residue_contract", "premium_director_polish", "creative_profile"),
            "scripts/prompt_contract.py": ("dialogue_performance_kernel", "emotion_residue_contract", "premium_director_polish", "creative_profile"),
        },
    },
    "creative_translation_layer": {
        "label": "对白潜台词、内外情绪与构图动机转译层",
        "checks": {
            "references/format_constraints.md": ("subtext_visible_evidence", "emotion_delta=end_intensity-start_intensity", "camera_motivation"),
            "references/production_quality_knowledge.md": ("内在情绪 → 对外展示 → 面具泄露", "潜台词可见证据", "构图戏眼"),
            "references/contracts/contract_index.md": ("台词功能、潜台词、原文重音", "面具泄露与情绪变化量", "运镜动机与记忆帧曲线"),
            "references/contracts/direct_copy_contract.md": ("line_function/subtext/turn_relation", "分析标签", "构图戏眼"),
            "references/export_spec.md": ("原文重音词", "潜台词可见证据", "inner_emotion/display_intent/emotion_delta"),
            "references/dispatch/master_production_note.md": ("subtext_visible_evidence", "emotion_delta", "构图优先级"),
            "references/schemas/pipeline.schema.json": ("line_function", "subtext_visible_evidence", "inner_emotion", "emotion_delta", "composition_priority", "camera_motivation"),
            "scripts/dispatch_cache.py": ("line_function", "subtext_visible_evidence", "inner_emotion", "emotion_delta", "composition_priority", "camera_motivation"),
            "scripts/prompt_contract.py": ("DIALOGUE_LINE_FUNCTIONS", "mask_leak", "emotion_delta", "composition_priority", "camera_motivation"),
            "scripts/episode_director_audit.py": ("emotion_delta", "memory_frame", "_audit_emotion_and_memory_curve"),
            "scripts/export_with_validation.py": ("原文重音词", "subtext_visible_evidence", "story_punch_contract"),
            "scripts/golden_jimeng_check.py": ("dialogue_subtext_stress_card", "masked_emotion_leak_card", "composition_camera_motivation_card"),
            "scripts/test_quality_upgrades.py": ("subtext不能复述原台词", "emotion_delta必须等于", "必须说明镜头为何响应"),
        },
    },
    "source_fidelity_split": {
        "label": "普通动作行、OV可见性与少镜头保真拆分",
        "checks": {
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
            "references/ROUTES.md": ("contracts/contract_index.md", "dispatch/master_production_note.md"),
            "references/contracts/contract_index.md": ("direct_copy_contract.md", "source_basemap_contract.md", "visual_quality_contract.md"),
            "references/contracts/source_basemap_contract.md": ("performance_baseline_lock", "viewpoint_motion_lock"),
            "references/contracts/visual_quality_contract.md": ("video_texture_contract", "cinematic_image_contract"),
            "scripts/dispatch_cache.py": ("def _phase_note_text", "references\", \"dispatch"),
            "references/dispatch/scene_lock_note.md": ("场景锁定 Agent", "space_id"),
            "references/dispatch/editor_pass2_note.md": ("Semantic Review Contract", "repair_targets", "不要返回完整提示词"),
        },
    },
    "production_intelligence": {
        "label": "制作智能、透视与关键帧流水线",
        "checks": {
            "references/format_constraints.md": ("B0.1 制作智能合同", "visible_emotion_state", "production_intelligence.py"),
            "references/production_quality_knowledge.md": ("视觉先验、尺度和修复审计", "近大远小", "关键帧与T2V正文"),
            "references/contracts/visual_quality_contract.md": ("隐性视觉先验", "perspective_scale_contract", "高风险关键帧"),
            "references/export_spec.md": ("关键帧流水线", "【关键帧生图提示】", ".concise.md"),
            "references/dispatch/master_production_note.md": ("视觉先验风险分类", "三状态关键帧"),
            "scripts/production_intelligence.py": ("classify_visual_prior_risks", "perspective_scale_contract_issues", "build_sentence_provenance"),
            "scripts/episode_state_graph.py": ("visible_emotion_state",),
            "scripts/episode_director_audit.py": ("analyze_sequence_curves", "动作生成失败风险"),
            "scripts/current_keyframe.py": ("build_keyframe_sequence", "fact_consistency"),
            "scripts/test_production_intelligence.py": ("back_facing_eyeline", "lighting_topology"),
            "scripts/test_keyframe_pipeline.py": ("起始状态关键帧", "结束状态关键帧"),
        },
    },
    "aesthetic_directing_layer": {
        "label": "静态与动态美术指导层",
        "checks": {
            "references/ROUTES.md": ("contracts/aesthetic_directing_contract.md", "静态/动态美学"),
            "references/format_constraints.md": ("visual_bible", "static_aesthetic_contract", "dynamic_aesthetic_contract", "aesthetic_priority"),
            "references/contracts/contract_index.md": ("aesthetic_directing_contract.md", "静态关键帧美学", "动态运动美学"),
            "references/contracts/aesthetic_directing_contract.md": ("Visual Bible", "Static Frame", "Moving Shot", "Aesthetic Review"),
            "references/dispatch/master_production_note.md": ("visual_bible → aesthetic_director → continuity_compiler", "static_aesthetic_contract", "dynamic_aesthetic_contract", "aesthetic_priority"),
            "references/schemas/pipeline.schema.json": ("visual_bible", "static_aesthetic_contract", "dynamic_aesthetic_contract", "aesthetic_priority"),
            "scripts/current_keyframe.py": ("_static_aesthetic_sentence", "_dynamic_aesthetic_sentence", "均匀棚拍光"),
            "scripts/export_with_validation.py": ("审美优先级", "真实候选审美评分", "审美复核清单"),
            "scripts/test_keyframe_pipeline.py": ("门框留白把视线引向抬眼瞬间", "低幅推近在抬眼后减速停稳"),
        },
    },
    "preproduction_visual_motion_texture_plans": {
        "label": "前置视觉路由、跨镜动态与场级视频质感底图",
        "checks": {
            "references/stage_gates.md": ("scene_motion_plan.json", "scene_texture_plan.json", "video_texture_contract"),
            "references/visual-direction-profiles.md": ("visual_profile_router.py", "项目回执", "逐场回执"),
            "references/dispatch/scene_lock_note.md": ("source_rules.style_evidence", "scene_receipt_count", "矛盾证据"),
            "references/dispatch/master_production_note.md": ("scene_motion_plan_path", "scene_texture_plan_path", "video_texture_contract"),
            "scripts/visual_profile_router.py": ("route_visual_profile", "scene_receipts", "contradictions"),
            "scripts/scene_motion_plan.py": ("dynamic_role", "response_budget", "source_grounding_required"),
            "scripts/scene_texture_plan.py": ("video_texture_contract", "exposure_policy", "continuity_carryover"),
            "scripts/dispatch_cache.py": ("scene_motion_plan_path", "scene_texture_plan_path", "contract_for_scene"),
            "scripts/test_preproduction_quality_plans.py": ("mixed_source", "超过声明预算", "语义运动家族"),
            "scripts/run_regression_suite.py": ("preproduction_quality_plans", "test_preproduction_quality_plans.py"),
        },
    },
}


def check(skill_root):
    issues = []
    issues.extend("机器契约：" + issue for issue in machine_contract_issues())
    issues.extend("技能表面：" + issue for issue in audit_skill_surface(skill_root))
    if tuple(GATES) != PIPELINE_PHASES:
        issues.append("pipeline_templates.GATES顺序必须由机器契约生成")
    if GATES != pipeline_gates():
        issues.append("pipeline_templates.GATES与机器契约产物边界不一致")
    skill_text = _read(os.path.join(skill_root, "SKILL.md")) or ""
    if len(skill_text.encode("utf-8")) > 16000:
        issues.append("SKILL.md超过16KB最小控制面预算")
    heavy_contracts = {
        "references/format_constraints.md",
        "references/production_quality_knowledge.md",
        "references/contracts/aesthetic_directing_contract.md",
    }
    for route_name, route_spec in TASK_ROUTES.items():
        for field in ("read_first", "read_on_demand", "run_only"):
            if field not in route_spec:
                issues.append("route_task.%s缺少%s上下文清单" % (route_name, field))
        preloaded = heavy_contracts.intersection(route_spec.get("read_first", []))
        if preloaded:
            issues.append("route_task.%s预读大合同：%s" % (route_name, "、".join(sorted(preloaded))))
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
    if '{"B2", "B5", "B6"}' not in dispatch:
        issues.append("Master Production sidecar未选择B2/B5/B6执行段")
    for slice_name in (
        "direct_copy_contract.md", "source_basemap_contract.md",
        "visual_quality_contract.md", "aesthetic_directing_contract.md",
    ):
        if slice_name not in dispatch:
            issues.append("Master Production sidecar缺少快速切片：%s" % slice_name)
    if '"scene_lock": ()' not in dispatch:
        issues.append("Scene Lock sidecar仍可能注入归档§A合同")
    if '"editor_pass2": ()' not in dispatch:
        issues.append("Editor Pass 2 sidecar仍在加载Master Production大合同")
    scripts_dir = os.path.join(skill_root, "scripts")
    for filename in sorted(os.listdir(scripts_dir)):
        if not filename.endswith(".py") or filename in {
            "contract_registry.py", "check_rule_consistency.py", "audit_skill_surface.py",
        }:
            continue
        text = _read(os.path.join(scripts_dir, filename)) or ""
        if PROMPT_CONTRACT_VERSION in text:
            issues.append("%s复制了PROMPT_CONTRACT_VERSION字面量" % filename)
        if "modec_v4" in text:
            issues.append("%s仍依赖废弃的modec_v4模块名" % filename)
        if "[EXPORT V4]" in text or "pre-v4" in text:
            issues.append("%s仍包含误导性的V4代际文本" % filename)
    registry_path = os.path.join(skill_root, "scripts", "contract_registry.py")
    for root, _dirs, files in os.walk(skill_root):
        for filename in files:
            if not filename.endswith((".py", ".md", ".json", ".yaml")):
                continue
            path = os.path.join(root, filename)
            if path == registry_path:
                continue
            text = _read(path) or ""
            if PROMPT_CONTRACT_VERSION in text:
                issues.append("%s复制了当前提示合同版本字面量" % os.path.relpath(path, skill_root))
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
