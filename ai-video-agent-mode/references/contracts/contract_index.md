# Contract Index

本索引用于降低按需读取成本；它不替代 `references/format_constraints.md`。当需要修改规则时，先按本表定位权威段落，再同步 validator、golden 和 rule consistency。

| 任务 | 优先读取 | 权威锚点 | 对应验证 |
|---|---|---|---|
| 即梦直投正文、700字上限、元叙述清除 | `direct_copy_contract.md` | `format_constraints.md` §B0/§B2/§B6 | `direct_copy_prompt_issues`、`jimeng_feed_prompt`、`golden_jimeng_check.py` |
| 结构化直投编译、去重、整句压缩、台词保护 | `direct_copy_contract.md` | `format_constraints.md` §B0/§B2 | `direct_prompt_compiler.py`、`test_quality_upgrades.py` |
| 全集状态、语义谱系、导演曲线和表演重复 | `format_constraints.md` §B0/§B3 | `format_constraints.md` §B0/§B3 | `episode_state_graph.py`、`episode_director_audit.py` |
| 对白自然时长、语速、气口与可见口型窗 | `format_constraints.md` §B2/§B3 | `format_constraints.md` §B2/§B3 | `dialogue_timing.py`、`dialogue_event_issues` |
| 台词功能、潜台词、原文重音、轮次关系与可见转译 | `direct_copy_contract.md` + `production_quality_knowledge.md` §11 | `format_constraints.md` §B7 `dialogue_events` | `dialogue_event_issues`、`test_quality_upgrades.py`、`golden_jimeng_check.py` |
| 内在情绪/对外展示差、面具泄露与情绪变化量 | `production_quality_knowledge.md` §3.5/§12 | `format_constraints.md` §B7 `performance_contract` | `performance_contract_issues`、`episode_director_audit.py` |
| 唯一构图戏眼、运镜动机与记忆帧曲线 | `production_quality_knowledge.md` §10 | `format_constraints.md` §B7 `story_punch_contract` | `story_punch_issues`、`episode_director_audit.py` |
| 前台导演精修、对白表演核、情绪残留、创作档位 | `direct_copy_contract.md` + `source_basemap_contract.md` + `production_quality_knowledge.md` §10–§13 | `format_constraints.md` §B0/§B7 | `source_constraint_basemap_issues`、`golden_jimeng_check.py`、`check_rule_consistency.py` |
| Master Production 源头底图 | `source_basemap_contract.md` | `format_constraints.md` §B7 `source_constraint_basemap` | `source_constraint_basemap_issues`、`check_rule_consistency.py` |
| 画面质感与视频质感继承 | `visual_quality_contract.md` | `format_constraints.md` §B0/§B7 + `production_quality_knowledge.md` §2/§8 | `visual_texture_issues`、`cinematic_image_contract_issues`、`video_texture_contract_issues` |
| 派发提示 | `references/dispatch/*.md` | `dispatch_cache.py` `_phase_note_text()` | `test_current_pipeline.py` constraints sidecar assertions |
| 特殊视角 | `production_quality_knowledge.md` §6.5 | `format_constraints.md` camera + basemap rules | `viewpoint_motion_grammar` rule consistency + golden cases |

结构优化规则：新增质量知识时，不把长规则堆进 `SKILL.md` 或 Python 字符串；优先放入 reference/dispatch/contract 文件，并在 `check_rule_consistency.py` 增加跨文件锚点。
