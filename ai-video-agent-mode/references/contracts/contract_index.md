# Contract Index

只在 validator、审查报告或用户任务命中具体问题后读取对应一行的“快速切片”。正常运行依赖
packet sidecar 和 validator，不读取本索引列出的全部文件。修改规则时再打开“权威锚点”，并同步
schema、validator、Golden 与 rule consistency。

## 直投与导出

| 触发问题 | 快速切片 | 权威锚点 | 验证/实现 |
|---|---|---|---|
| 即梦直投正文、700字上限、元叙述清除 | `direct_copy_contract.md` | `format_constraints.md` §B0/§B2/§B6 | `direct_copy_prompt_issues`、`jimeng_feed_prompt`、`golden_jimeng_check.py` |
| 至多500字导演卡、双视图、整句压缩与台词保护 | `direct_copy_contract.md` | `format_constraints.md` §B0/§B2 | `direct_prompt_compiler.py`、`compile_director_card`、`export_with_validation.py` |
| 镜头组构图/运镜变化与终端帧稳定 | `aesthetic_directing_contract.md`、`direct_copy_contract.md` | `format_constraints.md` §B0/§B7 | `terminal_frame_contract_issues`、`export_with_validation.py` |
| 派发与字段修复 | packet `constraints_path/retry_context_path` | `references/dispatch/*.md`、`dispatch_cache.py` | sidecar assertions、provenance validator |

## 表演、对白与序列

| 触发问题 | 快速切片 | 权威锚点 | 验证/实现 |
|---|---|---|---|
| Master Production 源头底图、前台导演精修、对白表演核、情绪残留与创作档位 | `source_basemap_contract.md` | `format_constraints.md` §B7 | `source_constraint_basemap_issues`、`check_rule_consistency.py` |
| 台词功能、潜台词、原文重音、轮次关系与可见转译 | `direct_copy_contract.md` | `format_constraints.md` §B7 `dialogue_events`、知识库 §11 | `dialogue_event_issues`、`test_quality_upgrades.py` |
| 抢话、打断、自我修正、答非所问与会话源文依据 | `direct_copy_contract.md` | 知识库 §11、`format_constraints.md` §B7 | `dialogue_event_issues`、`golden_jimeng_check.py` |
| 自然时长、语速、气口与可见口型窗 | `format_constraints.md` §B2/§B3 | 同左 | `dialogue_timing.py`、`dialogue_event_issues` |
| 面具泄露与情绪变化量、角色目标、策略与关系情绪弧 | `source_basemap_contract.md` | 知识库 §12/§14、`format_constraints.md` §B7 | performance/objective/relationship validators |
| 序列导演、联合调度、剪辑切点与切后信息增量 | `source_basemap_contract.md` | 知识库 §16–§17、`format_constraints.md` §B7 | sequence/cut validators、`episode_director_audit.py` |
| 空间声音、声音先后与切点支持 | `source_basemap_contract.md` | 知识库 §19、`format_constraints.md` §B7 | `sound_directing_plan_issues`、`dialogue_timing.py` |
| 全集状态、语义谱系、导演曲线和微表演重复 | validator 报告 | `format_constraints.md` §B0/§B3 | `episode_state_graph.py`、`episode_director_audit.py` |

## 画面、空间与美学

| 触发问题 | 快速切片 | 权威锚点 | 验证/实现 |
|---|---|---|---|
| 项目视觉圣经、静态关键帧美学、动态运动美学、运镜动机与记忆帧曲线 | `aesthetic_directing_contract.md` | `format_constraints.md` §B0/§B7、知识库 §2/§8/§10/§16/§18 | aesthetic/cinematic/video texture validators、候选审美复核 |
| 画面质感、视频质感继承与风景环境叙事 | `visual_quality_contract.md` | `format_constraints.md` §B0/§B7、知识库 §2/§8/§15 | visual/cinematic/video texture validators |
| 隐性视觉先验、多人注意力与动作失败预测 | `visual_quality_contract.md` | 知识库“生成先验” | `production_intelligence.py`、`test_production_intelligence.py` |
| 道具生命周期、透视比例与光源拓扑 | `visual_quality_contract.md` | `format_constraints.md`“制作智能合同” | prop/perspective/lighting validators |
| 道具功能面朝向、手机翻屏与内容展示机位 | `visual_quality_contract.md`、`direct_copy_contract.md` | 知识库 §20、`format_constraints.md` §B7 | `functional_surface_risk`、`prop_functional_surface_contract_issues` |
| 人物肤色、面光曝光与环境色/纹理/雾粒边界 | `visual_quality_contract.md` | 知识库 §2、`format_constraints.md` §B7 | `skin_tone_protection_contract_issues`、Golden |
| 三状态关键帧与T2V事实一致性 | `visual_quality_contract.md` | `export_spec.md`“关键帧流水线” | `build_keyframe_sequence`、`test_keyframe_pipeline.py` |
| 特殊视角运动语法 | `source_basemap_contract.md` | 知识库 §6.5、`format_constraints.md` camera/basemap | viewpoint rule consistency、Golden |
| 自适应提示词信息预算、1–2个视觉增强点 | `direct_copy_contract.md` | 知识库 §18、`format_constraints.md` §B7 | `prompt_information_budget_issues`、`direct_prompt_compiler.py` |

新增知识不要写回 `SKILL.md` 或 Python 长字符串。把字段规则放入权威合同，把 worker 执行摘要放入
`references/dispatch/`，把可迁移拍法放入知识库，并在本索引增加一个可定位入口。
