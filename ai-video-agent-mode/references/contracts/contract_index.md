# Contract Index

本索引用于降低按需读取成本；它不替代 `references/format_constraints.md`。当需要修改规则时，先按本表定位权威段落，再同步 validator、golden 和 rule consistency。

| 任务 | 优先读取 | 权威锚点 | 对应验证 |
|---|---|---|---|
| 即梦直投正文、700字上限、元叙述清除 | `direct_copy_contract.md` | `format_constraints.md` §B0/§B2/§B6 | `direct_copy_prompt_issues`、`jimeng_feed_prompt`、`golden_jimeng_check.py` |
| 180–500字导演卡、简洁/工程双视图 | `direct_copy_contract.md` | `format_constraints.md` §B0 | `compile_director_card`、`export_with_validation.py` |
| 隐性视觉先验、多人注意力、动作失败预测 | `visual_quality_contract.md` | `production_quality_knowledge.md`“生成先验” | `production_intelligence.py`、`test_production_intelligence.py` |
| 通用道具生命周期、透视比例、光源拓扑 | `visual_quality_contract.md` | `format_constraints.md`“制作智能合同” | `prop_lifecycle_contract_issues`、`perspective_scale_contract_issues`、`lighting_topology_contract_issues` |
| 三状态关键帧与T2V事实一致性 | `visual_quality_contract.md` | `export_spec.md`“关键帧流水线” | `build_keyframe_sequence`、`test_keyframe_pipeline.py` |
| 结构化直投编译、去重、整句压缩、台词保护 | `direct_copy_contract.md` | `format_constraints.md` §B0/§B2 | `direct_prompt_compiler.py`、`test_quality_upgrades.py` |
| 全集状态、语义谱系、导演曲线和表演重复 | `format_constraints.md` §B0/§B3 | `format_constraints.md` §B0/§B3 | `episode_state_graph.py`、`episode_director_audit.py` |
| 对白自然时长、语速、气口与可见口型窗 | `format_constraints.md` §B2/§B3 | `format_constraints.md` §B2/§B3 | `dialogue_timing.py`、`dialogue_event_issues` |
| 台词功能、潜台词、原文重音、轮次关系与可见转译 | `direct_copy_contract.md` + `production_quality_knowledge.md` §11 | `format_constraints.md` §B7 `dialogue_events` | `dialogue_event_issues`、`test_quality_upgrades.py`、`golden_jimeng_check.py` |
| 抢话、打断、半句停住、自我修正、答非所问与会话源文依据 | `production_quality_knowledge.md` §11 + `direct_copy_contract.md` | `format_constraints.md` §B7 `dialogue_events` | `dialogue_event_issues`、`test_quality_upgrades.py`、`check_rule_consistency.py` |
| 内在情绪/对外展示差、面具泄露与情绪变化量 | `production_quality_knowledge.md` §3.5/§12 | `format_constraints.md` §B7 `performance_contract` | `performance_contract_issues`、`episode_director_audit.py` |
| 唯一构图戏眼、运镜动机与记忆帧曲线 | `production_quality_knowledge.md` §10 | `format_constraints.md` §B7 `story_punch_contract` | `story_punch_issues`、`episode_director_audit.py` |
| 前台导演精修、对白表演核、情绪残留、创作档位 | `direct_copy_contract.md` + `source_basemap_contract.md` + `production_quality_knowledge.md` §10–§13 | `format_constraints.md` §B0/§B7 | `source_constraint_basemap_issues`、`golden_jimeng_check.py`、`check_rule_consistency.py` |
| Master Production 源头底图 | `source_basemap_contract.md` | `format_constraints.md` §B7 `source_constraint_basemap` | `source_constraint_basemap_issues`、`check_rule_consistency.py` |
| 画面质感与视频质感继承 | `visual_quality_contract.md` | `format_constraints.md` §B0/§B7 + `production_quality_knowledge.md` §2/§8 | `visual_texture_issues`、`cinematic_image_contract_issues`、`video_texture_contract_issues` |
| 派发提示 | `references/dispatch/*.md` | `dispatch_cache.py` `_phase_note_text()` | `test_current_pipeline.py` constraints sidecar assertions |
| 特殊视角 | `production_quality_knowledge.md` §6.5 | `format_constraints.md` camera + basemap rules | `viewpoint_motion_grammar` rule consistency + golden cases |
| 角色目标、策略切换、信息差与权力变化 | `production_quality_knowledge.md` §14 | `format_constraints.md` §B7 `character_scene_objective_contract` | `character_scene_objective_issues`、`episode_director_audit.py` |
| 关系情绪弧与共同余波 | `production_quality_knowledge.md` §14 | `format_constraints.md` §B7 `relationship_emotion_arc` | `relationship_emotion_arc_issues`、`episode_director_audit.py` |
| 风景美学、自然运动与环境叙事 | `visual_quality_contract.md` + `production_quality_knowledge.md` §15 | `format_constraints.md` §B7 `scene_tone_palette` | `validate_scene_locks.py`、`scene_tone_palette_issues`、`golden_jimeng_check.py` |
| 序列镜头语言、联合调度与剪辑切点 | `production_quality_knowledge.md` §16–§17 | `format_constraints.md` §B7 `sequence_directing_plan/cut_decision_contract` | `sequence_directing_plan_issues`、`cut_decision_contract_issues`、`episode_director_audit.py` |
| 自适应直投信息预算 | `production_quality_knowledge.md` §18 | `format_constraints.md` §B7 `prompt_information_budget` | `prompt_information_budget_issues`、`direct_prompt_compiler.py` |
| 空间声音、声画先后与切点支持 | `production_quality_knowledge.md` §19 | `format_constraints.md` §B7 `sound_directing_plan` | `sound_directing_plan_issues`、`dialogue_timing.py` |
| 道具功能面朝向、手机翻屏与内容展示机位 | `production_quality_knowledge.md` §20 + `direct_copy_contract.md` | `format_constraints.md` §B7 `prop_functional_surface_contract` | `functional_surface_risk`、`prop_functional_surface_contract_issues`、`test_quality_upgrades.py` |
| 人物肤色、面光曝光与环境色/纹理/雾粒边界 | `production_quality_knowledge.md` §2 + `visual_quality_contract.md` | `format_constraints.md` §B7 `skin_tone_protection_contract` | `skin_tone_protection_contract_issues`、`test_quality_upgrades.py`、`golden_jimeng_check.py` |

结构优化规则：新增质量知识时，不把长规则堆进 `SKILL.md` 或 Python 字符串；优先放入 reference/dispatch/contract 文件，并在 `check_rule_consistency.py` 增加跨文件锚点。
