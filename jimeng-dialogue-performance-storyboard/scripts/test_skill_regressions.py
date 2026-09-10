#!/usr/bin/env python3
"""Architecture and non-regression checks for the storyboard skill."""

from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "references"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


SKILL = read(ROOT / "SKILL.md")
CONTRACT = read(REF / "production-contract.md")
SHOOTING = read(REF / "shooting-method-reference.md")
DRAMATIC = read(REF / "ai-manga-dramatic-direction-engine.md")
LIGHTING = read(REF / "cinematic-lighting-color-bible.md")
DURATION = read(REF / "ai-manga-duration-budget.md")
VISUAL = read(REF / "visual-input-governance.md")
BASELINE = read(REF / "non-regression-baseline.md")
GENRE = read(REF / "genre-story-spectacle-engine.md")
SPECTACLE = read(REF / "spectacle-action-vfx-montage.md")
ON_DEMAND = read(REF / "on-demand-storyboard-reference.md")

VALIDATOR_PATH = ROOT / "scripts" / "validate_seedance_delivery.py"
SPEC = importlib.util.spec_from_file_location("seedance_delivery_validator", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator: {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class StoryboardSkillTests(unittest.TestCase):
    def test_entrypoint_is_compact_and_discriminating(self) -> None:
        self.assertLessEqual(len(SKILL.splitlines()), 120)
        self.assertIn("name: jimeng-dialogue-performance-storyboard", SKILL)
        self.assertIn("用户明确指定仅按独立 MD 规范执行时不使用本技能", SKILL)

    def test_all_linked_references_exist(self) -> None:
        links = re.findall(r"\[[^]]+\]\((references/[^)]+)\)", SKILL)
        self.assertGreaterEqual(len(links), 10)
        for relative in links:
            with self.subTest(reference=relative):
                self.assertTrue((ROOT / relative).is_file())

    def test_contract_is_loaded_only_after_blueprint_freeze(self) -> None:
        before, after = SKILL.split("## 整集—场景—镜头生成链", maxsplit=1)
        self.assertIn("底稿冻结前", before)
        self.assertIn("不读取", before)
        self.assertIn("冻结后需要正式交付", before)
        self.assertIn("production-contract.md", after)
        self.assertLessEqual(len(CONTRACT.splitlines()), 200)

    def test_independent_md_exits_without_merging(self) -> None:
        boundary = SKILL[SKILL.index("## 输入与边界") : SKILL.index("## 整集—场景—镜头生成链")]
        for concept in ("退出本技能", "不加载本技能入口或任何内部参考", "不把两套规则合并"):
            self.assertIn(concept, boundary)

    def test_facts_and_dialogue_remain_protected(self) -> None:
        self.assertRegex(SKILL, r"不改人物、身份、性格、关系、知情、事件顺序、因果")
        self.assertRegex(SKILL, r"台词、OS、OV 默认逐字、逐句、按原归属和顺序保留")
        self.assertIn("除非用户明确授权改写", SKILL)

    def test_asset_scope_distinguishes_full_and_local_tasks(self) -> None:
        combined = f"{SKILL}\n{CONTRACT}"
        self.assertIn("完整项目每个场景", combined)
        self.assertRegex(combined, r"局部镜头、修复或审核任务只输出用户要求")
        self.assertIn("不输出俯视调度图", combined)

    def test_all_genres_route_from_open_decision_factors(self) -> None:
        combined = f"{SKILL}\n{SHOOTING}"
        for concept in ("主/辅题材承诺", "场景任务", "人物现实任务", "过程乐趣/冲突载体", "结果兑现", "未列题材"):
            self.assertIn(concept, combined)
        for family in ("种田/基建", "都市/职场", "关系/言情", "悬疑/调查", "喜剧/荒诞", "动作/战争", "历史/古装"):
            self.assertIn(family, SHOOTING)

    def test_synthetic_stress_matrix_covers_upper_and_lower_bounds(self) -> None:
        cases = (
            "灌溉渠受阻",
            "半袋米谈判",
            "克制告别",
            "门外钥匙声",
            "严肃误会",
            "公开揭示",
            "雨夜旧屋",
            "职业交接",
            "狭道追逐",
            "安静早餐",
            "复用院落资产",
            "宴会权力入场",
            "被忽视之物成为宝贝",
            "五秒满载归途",
            "村巷流言升级",
        )
        self.assertIn("合成压力测试集", BASELINE)
        for case in cases:
            with self.subTest(case=case):
                self.assertIn(case, BASELINE)

    def test_specificity_check_and_observable_fallback_coexist(self) -> None:
        combined = f"{SKILL}\n{SHOOTING}\n{CONTRACT}"
        for concept in ("反事实专属性", "替换人物", "最可观察的现实因果", "朴素方案"):
            self.assertIn(concept, combined)
        self.assertIn("不为求新而改", SHOOTING)
        self.assertNotIn("每镜必须创新", combined)

    def test_adjacent_shots_progress_instead_of_cosmetic_recutting(self) -> None:
        combined = f"{SKILL}\n{SHOOTING}\n{CONTRACT}"
        for concept in ("进度", "压力", "信息", "关系", "触感"):
            self.assertIn(concept, combined)
        self.assertIn("相邻镜", combined)
        self.assertIn("无增长地重复同一作用", CONTRACT)
        self.assertIn("靠换景别、推近或加快切镜伪造节奏", SHOOTING)

    def test_heavy_direction_reference_has_narrow_trigger(self) -> None:
        self.assertIn("单一关键情绪先按本入口", SKILL)
        self.assertIn("三人以上反应传播", SKILL)
        self.assertIn("普通对白、单次情绪变化和已经成立的关键镜不加载", DRAMATIC)
        self.assertLessEqual(len(DRAMATIC.splitlines()), 150)

    def test_pressure_transmission_is_conditional_and_same_source(self) -> None:
        combined = f"{SKILL}\n{CONTRACT}\n{DRAMATIC}\n{BASELINE}"
        for concept in ("压力来源", "主压力方向", "受限选择", "人物压向空间", "空间/群体压向人物", "人物揭示"):
            self.assertIn(concept, combined)
        for false_signal in ("推近", "暗光", "慢动作", "全员转头"):
            self.assertIn(false_signal, combined)
        self.assertIn("安静早餐", BASELINE)
        self.assertIn("不单独触发", combined)
        self.assertNotIn("所有场景必须有压力", combined)

    def test_every_shot_is_directed_during_generation_not_enriched_in_review(self) -> None:
        combined = f"{SKILL}\n{SHOOTING}\n{CONTRACT}\n{DRAMATIC}\n{DURATION}\n{GENRE}\n{SPECTACLE}\n{BASELINE}"
        for concept in ("逐镜导演命题", "观众怎样看见并感受什么", "简单完整", "人物做事方式", "动作清单", "价值重估"):
            self.assertIn(concept, combined)
        self.assertIn("复审不负责临时创造", SKILL)
        self.assertIn("复审不得通过临时增加", CONTRACT)
        self.assertNotIn("每镜固定四层景深", combined)
        self.assertNotIn("每镜至少三个动作", combined)

    def test_generation_unit_can_choose_continuity_internal_cuts_or_split(self) -> None:
        combined = f"{SKILL}\n{SHOOTING}\n{CONTRACT}\n{BASELINE}"
        for concept in (
            "视频生成单元",
            "不自动等于一次连续摄影镜头",
            "连续长镜头",
            "时间线内有因切镜",
            "拆成独立镜头",
            "子镜A/子镜B",
            "切前落态",
            "切后起态",
            "声音桥",
        ):
            with self.subTest(concept=concept):
                self.assertIn(concept, combined)
        self.assertIn("每次切换须新增信息、触感、情绪、关系或结果", CONTRACT)
        self.assertNotIn("短镜优先一条物理连续的主摄影路径", combined)

    def test_non_plot_world_texture_is_allowed_and_bounded(self) -> None:
        combined = f"{SKILL}\n{SHOOTING}\n{CONTRACT}\n{LIGHTING}\n{VISUAL}\n{BASELINE}"
        for concept in (
            "氛围性世界细节",
            "不改剧情",
            "时代、地域、季节、地点",
            "炊烟",
            "环境生活声",
            "人物知情",
            "连续状态",
        ):
            with self.subTest(concept=concept):
                self.assertIn(concept, combined)
        self.assertIn("鸡叫", BASELINE)
        self.assertNotIn("不得无因改成夕阳", combined)
        self.assertNotIn("不得为质感无因改动时段、天气", combined)

    def test_scene_arc_precedes_shot_design_and_avoids_repetitive_escalation(self) -> None:
        combined = f"{SKILL}\n{SHOOTING}\n{CONTRACT}\n{DRAMATIC}\n{BASELINE}"
        for concept in (
            "场景级导演曲线",
            "进入秩序",
            "离场结果",
            "镜头组",
            "不可替代职责",
            "递进、错峰或释放",
            "骤停",
            "声音抽空",
            "连续慢推",
            "重复特写",
        ):
            with self.subTest(concept=concept):
                self.assertIn(concept, combined)
        self.assertRegex(combined, r"无冲突场景.{0,30}(?:不强造|不得.*强造)")
        self.assertIn("村巷流言升级", BASELINE)
        self.assertIn("重磅信息命中", BASELINE)

    def test_rich_execution_is_preserved_without_load_based_compression(self) -> None:
        combined = f"{SKILL}\n{SHOOTING}\n{CONTRACT}\n{BASELINE}"
        for concept in (
            "观众能够感知的主要呈现方式",
            "主节奏、观众观看关系与主要呈现方式",
            "景别只决定可见粒度",
            "至少两个真正参与叙事的空间层次",
            "底层环境",
            "静默或声音抽空",
            "细节多少不设人为字数、输出栏目长度或细节数量上限",
            "导演版承担创作指导",
            "直投版删除分析过程但完整保留",
            "有效手法可以在同题材复用",
        ):
            with self.subTest(concept=concept):
                self.assertIn(concept, combined)
        for forbidden in ("生成负载", "组合负载过高", "AI 负载", "Seedance 负载"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, combined)

    def test_shooting_comparison_is_conditional_not_a_quota(self) -> None:
        combined = f"{SKILL}\n{SHOOTING}\n{DRAMATIC}"
        self.assertIn("明显成立的单一方案", combined)
        self.assertRegex(combined, r"只有.*难以取舍时.*非同构")
        self.assertNotIn("至少再比较一套", combined)

    def test_performance_allows_inner_change_without_forced_action(self) -> None:
        combined = f"{SKILL}\n{CONTRACT}\n{DRAMATIC}"
        for concept in ("可感知", "优先载体", "无须强造外部动作", "纯内在冲击", "短暂失语", "身体冻结"):
            self.assertIn(concept, combined)
        self.assertNotIn("不能只用心理结论、表情或声音完成现实状态变化", combined)
        self.assertNotRegex(combined, r"关键情绪.{0,20}必须改变任务")

    def test_dialogue_timing_does_not_map_emotion_to_fixed_speed(self) -> None:
        forbidden = re.compile(r"(?:激烈|争吵|忧伤|迟疑|低沉|悲伤).{0,24}\d(?:\.\d)?[-—]\d(?:\.\d)?\s*字/秒")
        self.assertIsNone(forbidden.search(DURATION))
        self.assertIn("自然试读", DURATION)
        self.assertIn("不是演员语速档位", DURATION)
        self.assertIn("不得直接映射为固定字速", DURATION)
        self.assertLessEqual(len(DURATION.splitlines()), 90)

    def test_natural_dialogue_keeps_action_and_voice_from_one_source(self) -> None:
        combined = f"{SKILL}\n{CONTRACT}\n{DRAMATIC}"
        for concept in ("话语行动", "自然语义", "平静不等于平直", "完整语义组不得被切成逐词停顿", "音画同源不等于"):
            self.assertIn(concept, combined)
        self.assertIn("普通信息对白", combined)
        self.assertIn("关键情绪对白", combined)

    def test_voice_identity_is_cross_shot_but_not_a_fixed_preset(self) -> None:
        combined = f"{SKILL}\n{CONTRACT}"
        for concept in ("说话身份", "语义分组", "咬字", "气息连接", "句尾", "关系差异"):
            self.assertIn(concept, combined)
        self.assertIn("不是固定语速或音高", SKILL)
        self.assertIn("偏离人物表演基线时", CONTRACT)

    def test_dialogue_and_performance_have_character_swap_checks(self) -> None:
        combined = f"{SKILL}\n{CONTRACT}\n{DRAMATIC}"
        self.assertIn("关系、性格和目的不同的人物", combined)
        self.assertIn("完成关键表演后做换人检验", DRAMATIC)
        self.assertIn("不靠增加参数制造差异", SKILL)
        self.assertIn("不因幅度小而判为不足", DRAMATIC)

    def test_rhythm_has_one_axis_but_allows_subordinate_takeover(self) -> None:
        combined = f"{SKILL}\n{SHOOTING}\n{DRAMATIC}"
        self.assertIn("主节奏", combined)
        self.assertIn("从属", combined)
        self.assertIn("短剧感不等于全程快切", combined)
        self.assertIn("爆发前需要积累", combined)
        self.assertIn("命中后必须读到结果", combined)

    def test_dramatic_engine_has_no_giant_mandatory_source_table(self) -> None:
        self.assertIn("六项核心结论", DRAMATIC)
        self.assertIn("条件模块", DRAMATIC)
        self.assertNotIn("镜号/节拍 |", DRAMATIC)
        self.assertIn("不得建立要求每镜填满的巨型源表或能力覆盖账本", DRAMATIC)
        self.assertNotIn("每镜在时间线上明确", DRAMATIC)

    def test_lighting_uses_baseline_plus_real_delta(self) -> None:
        self.assertLessEqual(len(LIGHTING.splitlines()), 120)
        for concept in ("人物—场景融合与干净影像基线", "同一次摄影中形成", "接触阴影", "大面积低频明暗", "逐镜编译", "真实差量"):
            self.assertIn(concept, LIGHTING)
        self.assertNotRegex(LIGHTING, r"每镜至少写清")
        self.assertIn("图案光并非一律禁止", LIGHTING)

    def test_blocking_changes_drive_visible_scene_integration(self) -> None:
        combined = f"{SKILL}\n{LIGHTING}\n{CONTRACT}"
        for concept in ("人物转身", "跨越光区", "接触改变", "至少一种可见变化", "纯肖像"):
            self.assertIn(concept, combined)
        self.assertIn("人物位置或接触已改变而人物—环境关系完全不变", LIGHTING)

    def test_scene_asset_views_are_conditional_and_topology_locked(self) -> None:
        combined = f"{SKILL}\n{CONTRACT}"
        for concept in ("同一拓扑共识", "空间总览", "功能视角", "反向机位", "横向调度"):
            self.assertIn(concept, combined)
        self.assertIn("每个视角分别给出正向/负向提示词", CONTRACT)
        self.assertIn("只改变摄影方向与覆盖范围", CONTRACT)
        self.assertIn("普通单轴场景", combined)
        self.assertNotIn("每场至少三个视角", combined)

    def test_visual_input_uses_the_runtime_contract_only(self) -> None:
        self.assertNotIn("seedance-dual-delivery-contract.md", VISUAL)
        self.assertIn("production-contract.md", VISUAL)
        self.assertIn("模型为无参考的新场景", VISUAL)

    def test_runtime_and_maintenance_references_are_separated(self) -> None:
        self.assertIn("仅用于修改技能和回归检查", SKILL)
        self.assertIn("普通生成不读取", SKILL)
        self.assertNotIn("seedance-dual-delivery-contract.md", SKILL)
        self.assertLessEqual(len(BASELINE.splitlines()), 90)
        self.assertIn("不锁定历史措辞", BASELINE)

    def test_genre_engine_has_no_rigid_retention_formula_or_hidden_dependency(self) -> None:
        for forbidden in ("通用五段", "整集五段", "2秒内异常", "尾钩必须", "每集/目标片段至少建立一个"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, GENRE)
        self.assertNotIn("ai-manga-dramatic-direction-engine.md", GENRE)
        for concept in ("安静生活状态", "中性表情", "不套固定阶段数量", "不是每场或每集配额"):
            self.assertIn(concept, GENRE)

    def test_spectacle_engine_is_self_contained_and_attention_aware(self) -> None:
        self.assertNotIn("ai-manga-dramatic-direction-engine.md", SPECTACLE)
        self.assertIn("不假定任何其他导演参考已经运行", SPECTACLE)
        self.assertIn("阅读信息应按因果交接", SPECTACLE)
        self.assertIn("不是以 Seedance 执行负担为由限制复杂度", SPECTACLE)
        self.assertIn("不为层数齐全", SPECTACLE)

    def test_blocking_diagrams_require_an_explicit_user_request(self) -> None:
        self.assertIn("仅用户明确要求时", ON_DEMAND)
        self.assertIn("普通分镜、场景资产、空间排错和自动复审均不得调用", ON_DEMAND)
        self.assertIn("不输出俯视调度图", SKILL)

    def test_forward_evaluation_separates_md_and_skill_bounds(self) -> None:
        for concept in ("独立 MD", "本技能", "隐藏工具名称", "平均分", "最低分", "最高分", "跨样本方差"):
            self.assertIn(concept, BASELINE)
        self.assertIn("静态脚本通过不等同于前向评测通过", BASELINE)

    def test_realistic_3d_template_preserves_directional_modeling(self) -> None:
        self.assertIn("自然方向性面部受光", VALIDATOR.CG3D_TEMPLATE)
        self.assertIn("暗侧保留连续纹理", VALIDATOR.CG3D_TEMPLATE)
        for forbidden in ("8K纹理贴图", "均匀皮肤光照", "柔和面部补光"):
            self.assertNotIn(forbidden, VALIDATOR.CG3D_TEMPLATE)

    def test_camera_physics_and_continuity_remain_executable(self) -> None:
        combined = f"{SKILL}\n{CONTRACT}\n{DRAMATIC}"
        for concept in ("摄影机不得穿墙、穿物", "可追踪路径", "重力、支撑、接触、受力、惯性", "持物手", "轴线"):
            self.assertIn(concept, combined)

    def test_direct_and_director_schemas_remain_complete(self) -> None:
        for marker in (
            "# 作品名｜导演审核版",
            "### 场景资产图提示词",
            "# 作品名｜Seedance独立直投版",
            "## 【全局摄影规则】",
            "## 【场景空间位置关系】",
            "**起幅与连续性**",
            "**光影、环境色彩与材质**",
            "**画面与表演时间线**",
            "**台词与声音层次**",
            "**落幅状态**",
        ):
            self.assertIn(marker, CONTRACT)

    def test_direct_fields_are_self_contained_without_repeating_every_baseline(self) -> None:
        self.assertIn("第一帧完整执行快照", CONTRACT)
        self.assertIn("独立投喂需要知道的当前主光", CONTRACT)
        self.assertIn("无真实差量时用一句简洁当前状态", CONTRACT)
        self.assertNotIn("每镜至少写清", CONTRACT)

    def test_timeline_is_continuous_without_word_level_false_precision(self) -> None:
        combined = f"{SKILL}\n{CONTRACT}\n{DURATION}"
        self.assertIn("时间线第一行从 `0.0秒` 开始", CONTRACT)
        self.assertIn("相邻时间窗首尾相接", combined)
        self.assertIn("不宣称某个字必然落在某个小数秒点", combined)
        self.assertIn("一个词或一句即时短反应不自动展开完整表演链", SKILL)

    def test_fixed_templates_match_validator_once(self) -> None:
        for template in (
            VALIDATOR.IDENTITY_TEMPLATE,
            VALIDATOR.CG3D_TEMPLATE,
            VALIDATOR.FACE_NEGATIVE_TEMPLATE,
            VALIDATOR.CG3D_NEGATIVE,
        ):
            with self.subTest(template=template[:20]):
                self.assertEqual(1, CONTRACT.count(template))

    def test_identity_template_does_not_freeze_performance(self) -> None:
        self.assertIn("表情肌肉、眼球视线、眼睑、嘴唇、下颌、头颈姿态与呼吸按剧情自然联动", VALIDATOR.IDENTITY_TEMPLATE)
        self.assertIn("不得改变人物身份、五官基础比例", VALIDATOR.IDENTITY_TEMPLATE)
        self.assertNotIn("仅面部肌肉做表情运动", VALIDATOR.IDENTITY_TEMPLATE)

    def test_shot_specific_constraints_are_optional(self) -> None:
        self.assertIn("仅有本镜新增风险时保留", CONTRACT)
        self.assertIn("不存在的 OS、OV、BGM、特效或特殊约束删除整项", CONTRACT)

    def test_review_is_semantic_and_local(self) -> None:
        combined = f"{SKILL}\n{CONTRACT}"
        self.assertIn("模型语义复审", CONTRACT)
        self.assertIn("不能用关键词命中代替导演判断", SKILL)
        self.assertIn("只局部重开", combined)
        self.assertIn("没有实际失败时，不得改写", CONTRACT)

    def test_default_delivery_is_single_direct_main_with_optional_director(self) -> None:
        combined = f"{SKILL}\n{CONTRACT}"
        self.assertIn("默认输出 `作品名_Seedance独立直投版.md`", SKILL)
        self.assertIn("仅在用户要求导演分析、人工审核或双版本时", SKILL)
        self.assertIn("导演审核版（按需）", CONTRACT)
        self.assertNotIn("完整项目输出双文件", combined)

    def test_project_scene_shot_chain_preserves_directing_and_state(self) -> None:
        combined = f"{SKILL}\n{CONTRACT}"
        for concept in (
            "整集—场景—镜头",
            "每场先在内部冻结一句本场核心变化",
            "每镜须新增信息、关系、压力",
            "长项目按场景",
            "不重新导演",
            "未受刺激者继续任务",
            "不让配角木讷",
        ):
            self.assertIn(concept, combined)

    def test_core_facts_are_locked_while_audiovisual_expression_is_free(self) -> None:
        combined = f"{SKILL}\n{CONTRACT}"
        for concept in (
            "关键动作/信息",
            "关系变化",
            "怎样表达",
            "影视化改编",
            "核心信息",
            "到达时点",
            "关系策略",
            "人物口吻",
        ):
            self.assertIn(concept, combined)

    def test_advanced_sound_grammar_is_conditional(self) -> None:
        combined = f"{SKILL}\n{CONTRACT}"
        for concept in ("声画反差", "主观", "J-Cut", "L-Cut", "声音匹配切"):
            self.assertIn(concept, combined)
        self.assertIn("不强制使用", SKILL)
        self.assertIn("不作为固定配置", CONTRACT)

    def test_global_and_shot_negative_rules_have_distinct_scope(self) -> None:
        combined = f"{SKILL}\n{CONTRACT}"
        self.assertIn("全局负向只集中", combined)
        self.assertIn("本镜特殊负向只处理该镜新增风险", CONTRACT)
        self.assertIn("不把摄影选择写成全局禁令", CONTRACT)

    def test_splus_compaction_preserves_directing_core(self) -> None:
        combined = f"{SKILL}\n{CONTRACT}\n{BASELINE}"
        for concept in (
            "S+ 保护",
            "题材专属拍法",
            "人物专属演绎",
            "关键动作",
            "唯美构图",
            "运镜触发/路径",
            "台词声音弧线",
            "色影差量",
            "镜尾余波",
            "连续接点",
            "不可压缩的主执行层",
        ):
            self.assertIn(concept, combined)
        for forbidden_shortcut in ("情绪升级", "镜头推近", "人物爆发"):
            self.assertIn(forbidden_shortcut, combined)

    def test_three_level_inheritance_reduces_repetition_without_ellipsis(self) -> None:
        combined = f"{SKILL}\n{CONTRACT}\n{BASELINE}"
        for concept in (
            "三级继承",
            "全剧层",
            "场景层",
            "镜头层",
            "同一执行事实",
            "简洁完整句",
            "不用省略指代",
        ):
            self.assertIn(concept, combined)

    def test_beautiful_composition_is_story_driven_not_a_style_quota(self) -> None:
        combined = f"{SKILL}\n{BASELINE}"
        for concept in (
            "构图策略",
            "主体与负空间",
            "几何秩序",
            "颜色面积",
            "人物—环境尺度",
            "视觉秩序变化",
            "唯美不得退化",
        ):
            self.assertIn(concept, combined)

    def test_heavy_reference_overlap_is_not_loaded_preemptively(self) -> None:
        self.assertIn("先读取能解决主要难题的最窄一份专项参考", SKILL)
        self.assertIn("仍存在具体未解决", SKILL)
        self.assertIn("不再为了“更丰富”叠加", SKILL)
        self.assertIn("不按场重新加载或重新设计", SKILL)


if __name__ == "__main__":
    unittest.main(verbosity=2)
