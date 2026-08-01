---
name: ai-video-agent-mode
description: >
  将剧本、分镜或场景转换为可直接投喂即梦 T2V 的提示词包，提供剧情节拍、表演、
  连续性、动作预算、风险审查与 Markdown/XLSX 导出。适用于剧本转 AI 视频提示词、
  即梦 T2V、跨镜连续和低抽卡风险控制。
---

# AI Video Agent Mode

将源文转换为可审查、可恢复、可导出的即梦 T2V 提示词包。技能只生成提示词与制作元数据，
不调用、观看或评分视频生成结果；`ai_model_readiness_score` 只表示提示词合同的执行风险，
不表示成片质量。

## 权威契约

- 当前阶段顺序、执行者、输入输出、超时、批次和 validator 的机器唯一来源：`scripts/contract_registry.py`；其它脚本只能派生消费，不得复制维护第二套阶段表。
- 详细字段、五段提示词、动作预算和验证规则：`references/format_constraints.md`。
- 按需合同索引与低耗读取切片：`references/contracts/contract_index.md`。
- 制作质量知识储备、人物一致性、空间/物理连续和画面质感：`references/production_quality_knowledge.md`。
- Agent 派发角色说明维护在 `references/dispatch/*.md`，`scripts/dispatch_cache.py` 只负责读取、拼装和 fallback。
- 路由和按需读取规则：先读 `references/ROUTES.md`。
- 当前运行时阶段、输出和门禁：`scripts/pipeline_templates.py` 与 `scripts/pipeline_state.py`。
- 历史 Emotion / Camera / Director 分阶段文档不是当前可派发阶段；当前实现不兼容旧 pipeline。

当前仅支持即梦 `t2v`。禁止 I2V、R2V、参考素材槽位、把首尾帧当平台输入槽位或写入动作素材路径。允许导出起始/戏眼/结束三状态关键帧和空间调度辅助图作为前期稳定参考，但它们不改变 T2V-only 合同，也不冒充已上传素材。

## 当前管线

| 顺序 | 阶段 | 执行者 | 产物/门禁 |
|---|---|---|---|
| 0 | 配置确认 | Wizard | 已确认 `project_config.json` |
| 1 | Orchestrator | 本地脚本 | shot plan、source ledger、dramatic beat ledger、preflight |
| 2 | Scene Lock | Agent | 不可变场景、光源、服装和空间事实 |
| 3 | Master Production | Agent | 每主镜一条 T2V 任务与完整合同 |
| 4 | Editor Pass 1 | 本地脚本 | `pre_editor_gate.py` |
| 5 | Editor Pass 2 | Agent | 仅修语义穿帮与执行竞争 |
| 6 | Validate | 本地脚本 | `episode_state_graph.py`、`episode_director_audit.py`、`emotion_camera_audit.py`、`validate_modec.py`、`check_export.py` |
| 7 | Export | 本地脚本 | 已确认路径下 Markdown 与 XLSX |

不得跳过、重命名或假设存在其它运行时阶段。`master_production` 内部仍须遵守
`emotion_driver → camera_beat_map → full_prompt` 的字段接力，但它们是同一任务内的有序字段，
不是可单独派发的 Agent。

## 运行规则

1. 手动新调用默认 `full --intent new`，必须使用新的空 `run_dir`。续跑、审查、导出、单镜修复才可复用已确认运行。
2. 先执行 `route_task.py`，再按返回路由读取。新运行有两种等质量入口：参数缺失时按 Wizard 顺序逐轮确认输出目录、画幅与风格、时长与平台、音频、交付路径；用户一次明确提供包含全部八个基础字段的 JSON 配置和源文件时，使用高质量快速模式 `--config <json> --source <source> --auto-start` 原子确认并立即启动。快速模式只减少配置交互，不得跳过任何管线阶段、Agent provenance、validator、Golden 或导出门禁。
3. 确认后只由 `workflow_supervisor.py` 驱动状态机。`waiting_for_workers` 不需要用户确认。
4. Agent 只能写 packet 的 `_batch_output_path`。每次派发必须经过注册回执、至少一次心跳、完成 provenance 和阶段验证，之后才可合并。
5. 公共合并使用 `merge_agent_outputs.py --require-provenance`；失败只修 validator 指定字段，第二次重试为单主镜批次。
6. 每个主镜仅服务一个 `narrative_beat_id`。`shot_group` 仅描述该节拍内的连续变化，最多一次单向注意力交接；需回切、第二目标或第二独立动作链时拆为下一主镜。
7. 台词、OS、OV 按 `ref/kind/speaker/text` 锁定，逐字保留。OS/OV 无口型；无源文不得新增人声。
8. Orchestrator 必须把带 `△/动作：` 前缀和无前缀的普通剧本动作行都登记为源文制作单元；每个动作/对白 source ID 必须进入一个剧情节拍。相邻低风险起幅状态、声音触发和台词后反应可在同一叙事目标与时长上限内合并，强动作、第二动作链或超时必须拆镜。OV 说话者只锁为声音来源，不得进入可见人物列表；OS 可按源文锁定闭口可见人物。
9. `full_prompt` 只包含可执行画面指令。QA、负面词、工程数据、风险结论和迁移说明必须位于 JSON 独立字段。
10. Scene Lock 是光源、色温、服装与空间不可变事实的唯一来源。后续阶段只能消费这些事实。
11. 高风险镜指多人走位、受力/打斗、道具交接、长台词、`shot_group` 或高抽卡风险。高风险 Master Production 批次上限为 **2**，standard 为 6，light 为 10；具体值以 `dispatch_risk()` 为唯一实现来源。
12. 同一地点跨镜必须复用 Scene Lock 的空间ID、空间主锁定、入口出口、人物槽位和道具活动区；同一场景影调从场景色卡消费，不得逐镜重新解释空间或乱换光色。
13. 直接投喂即梦的导出文本统一写入 `【画面描述｜直接复制】`，不得保留“上一镜、继承、尾帧、剪辑、切到、反打到”等元叙述；规范正文可用于验证落幅，导出 feed 必须转成当前可见事实，并保留压缩视觉场景前缀、画幅、影调、色卡、画面主体、运镜、光影、1–2 个具体材质锚点，以及可选 `video_texture_contract` 的短视频质感继承句。
14. 新运行或 Compose 派发前必须将 `production_quality_knowledge.md` 的知识储备转成项目内事实：制作级影调色卡、空间锁定索引、角色声音锁定表、角色表演基线、人物可见人数闸门、情绪微表演链、物理结构链、特殊视角运动语法和单镜 1–2 个质感锚点；不得把该参考中的示例场景、左右站位、光线或人物关系原样套入项目。
15. 前台导演精修层只优化可见表达，不改变源文事实、字段合同或验证门禁。`creative_profile` 仅允许 `safe/balanced/expressive` 三档：safe 稳定直投，balanced 默认增强表演与质感，expressive 只在低风险或用户明确要风格化时扩大镜头语法；任何档位都不准牺牲 direct-copy 质量、T2V-only、provenance、validator、golden 与规则一致性。
16. Export 只通过 `direct_prompt_compiler.py` 按视觉前缀→空间→连续性→表演→光影→视频质感→电影质感编译完整直投正文；跨段精确去重，只整句压缩，台词与硬事实受保护，不能满足 700 字完整视图上限时阻断回修，禁止静默截断。另由同一事实源生成 180–500 字 `【导演卡｜直接复制】`；压缩会删受保护事实或密度低于180字时同样阻断，不用空话补齐。
17. Validate 必须生成全集状态图和语义谱系，并联合审计张力、景别、运镜能量、关系距离四条曲线，以及角色策略/权力变化、关系情绪弧、环境演进、构图母题、切点信息增量、微表演重复、动作失败概率、对白自然时长和可见口型窗；明确事实冲突、容量不足、口型窗重叠及连续机械重复阻断，低置信度创作节奏问题保留为警告供 Editor 复核。
18. 隐性视觉先验先分类再正向改写：覆盖职业/场景负向概念、背对人物的头肩视线物理、镜面/照片反射几何、屏幕与通用道具功能面、驾驶视线、遮挡/肩线/倒影误生成人物；负向坏概念不得进入正向正文。
19. 活动道具统一使用 `prop_lifecycle_contract`：用途、可见面、起始位置、接触者/接触方式、运动路径、终点、终点方向和下一镜状态。多人镜使用可见人数闸门、主表演/受击观察/背景分区和最多一次注意力交接。
20. 多人纵深、前中后景人物或沿景深移动必须使用 `perspective_scale_contract`：共同支撑平面和消失关系成立，画面投影遵循近大远小；人物真实体型、头身/骨架比例及道具相对持有者比例不变，靠近/远离镜头时画面占比连续变化，不得突然缩放或用变焦伪装位移。
21. 清晰人物镜使用 `lighting_topology_contract` 与肤色保护：写清动机光源、方向、色温范围、人物面光独立层、环境光层、阴影曝光、体积光边界和混合色温冲突处理；霓虹、火光、车灯、水波和丁达尔光只在授权空间落点运动，不把综合色斑、墙面纹理或雾粒投到脸上。
22. 复杂/高风险镜的关键帧使用 Jimeng 同名字段 `【关键帧生图提示】` 与 `【即梦视频提示｜配合关键帧】`，包含起始状态、戏眼、结束状态三帧、人物/道具状态差异、跨帧连续检查和关键帧/T2V事实一致性检查；旧单张关键帧 API 仅作兼容适配。

## 质量规则

- 先满足站位、朝向、道具归属、口型、动作预算和落幅继承，再追求风格化镜头。
- 每个子镜只有一个实焦主体、一个主要动作或状态变化、一个景别可见的表演证据和一个可继承落幅。
- 表演按“角色表演基线 → 触发 → 内在情绪/对外展示差 → 可见泄露 → 身体承接 → 声音/呼吸 → 残留”组织；角色基线仍须锁定常态控制、优先泄露部位、默认动作幅度、爆发阈值和禁用习惯。`inner_emotion/display_intent` 只用于推导，`mask_leak` 才落成眉眼、嘴角、下颌、肩颈、手指、袖口/道具、视线或呼吸中的 3–5 个微动作。每镜记录 0–5 起止强度与变化量，但这些分析词和数字不得进入直投正文；运镜只能响应已确认的可见泄露或台词重音。
- 人物镜在情绪之前建立 `character_scene_objective_contract`：角色要得到什么、失败代价、障碍、当前策略、可见策略证据、策略切换/维持、信息差、权力前后状态和行动落幅。对手戏再建立 `relationship_emotion_arc`：关系起点、冲突欲望、情绪错位、转折触发、权力变化、关系终态和共同余波。心理、目标与信息差只供推导，正文只写可见行动和关系证据。
- Master Production 写镜前先建立 `source_constraint_basemap`：空间、人物朝向、状态/道具、物理反推、张弛功能、情绪钩子、多人体反应、影调、声音/口型和屏幕文字策略；后期校验只兜底，不承担主要创作修复。
- 前台导演精修层把合规提示词润成可直接投喂的即梦导演卡，但不得新增第二套事实。`【画面描述｜直接复制】` 推荐顺序为：画幅/风格 → 场景色卡/影调 → 主体位置与可见人数 → 表演/台词/听者反应 → 运镜路径或稳定状态 → 光影材质 → 落幅。对白镜以 `dialogue_performance_kernel` 先判断本句功能、潜台词和轮次关系，再只把 1–3 个原文重音词、说法、潜台词可见证据、说话者口型、听者低幅反应、句末闭口与余波落幅写进正文；不得把 `subtext/line_function/turn_relation` 标签直接投喂即梦。
- Scene Lock 需沉淀项目级知识，而不是只写单镜位置：每个地点必须有 `space_id`、`space_master_sentence`、入口出口、人物槽位基准、道具活动区、完整影调色卡压缩版与光源事实；每个有台词/OS/OV的人物应有稳定声音锁定，单镜只写情绪造成的声音微调。
- 画面质感必须落成可执行视觉锚点：光源方向/色温、脸/手/道具受光面、浅阴影/反光、背景虚化或剧情相关材质；不得只写电影感、高级感、质感。写实/实拍/电影剧照目标必须使用 `cinematic_image_contract` 或等价正文，明确构图锚点、焦平面/景深、曝光黑位、色彩分离、空气层、真实材质、非完美瑕疵和记忆帧，并主动规避镜面水面、塑料墙、均匀雨线、过曝灯管、过度霓虹和虚拟摄影棚感。
- 每个场景必须建立生活化景深合同：前景框景或轻遮挡、中景人物活动与接触区、后景纵深锚点、题材视觉气味、1–2项自然使用痕迹，以及实焦/焦外/空气透视主次。再建立风景导演事实：地域季节与地貌/建筑身份、主形体/引导线/视觉重心/留白构图、风叶草水云雾雨雪的差速自然运动、环境起态→剧情触发→余波、揭示顺序、光候演进和建立镜/人物镜/缓冲镜呼吸策略。单镜仍只消费任务相关内容：至少两层景物，环境镜再取两项风景事实，人物镜只取一项不抢戏的环境事实；不准把随机花草、薄雾、逆光和湿地反光当通用美化包。
- 特殊视角不是标签。使用穿越、ACT、FPV、POV、水平横移或鸟瞰时，必须锁定摄影机与主体关系、相对高度/距离、唯一主路径与速度曲线、至多一次焦点交接和稳定落幅；若需要多层级穿越、两次以上方向变化、第二个动作链或回切，优先拆镜，不得靠堆叠“高速、环绕、甩镜、慢动作”冒险。
- 整条视频的质感提升优先使用 `video_texture_contract`：统一全片影像基调、曝光黑位、高光不过曝、材质运动响应、雨雾尘空气层运动、镜头稳定/运动预算和跨镜质感继承。单镜 direct-copy 可提高到 700 个中文字符以内，但仍只选择 1–2 个核心视觉增强点，不把图片级细节密度复制到每条视频提示词里。
- 复杂度分档只减内部合同和可选字段，不准牺牲 `【画面描述｜直接复制】` 的核心质量。轻量镜也必须含视觉场景前缀、景别/机位、人物位置与面向、台词或声音文本、说话者表演、听者/环境反应、镜头状态、光影/材质落点和画面结束状态；普通剧情镜低于 180 中文字符视为密度不足，应重写或升级为 standard。
- 情绪跨镜一致性使用 `emotion_residue_contract`：触发前状态 → 泄露部位 → 压抑/释放方式 → 尾帧残留。它只记录可见尾韵和下一镜可继承表演，不把“尾帧/继承”写进 direct-copy 正文。
- 构图、焦段、运镜和材质只服务本镜唯一任务；复杂对白、多人反应、道具转移或复杂运镜镜头优先保稳定，只保留一个光影/构图锚点。
- 多人、画外声或同场人物多于本镜入画人物时，必须先建立“可见人数闸门”：清楚区分清晰人物、肩线/背影/倒影/虚化人物和纯画外声音；不入画人物不得作为“看向/面对”的视觉目标。
- 多人戏中清晰入画的具名非主表演者不能只是闭口站着；必须分配受击反应、观察反应、背景弱化，或降为肩线/边缘虚化/画外。
- 情绪连续不是只记强度数字；全集状态图必须把触发、表情泄露、身体承接、声音/呼吸变化和余波编译为 `visible_emotion_state`，下一镜只能消费上一镜已经可见的残留。
- 每镜标记张弛功能：铺垫、升压、峰值、释放或缓冲；不要连续强推近、强表情、强停顿，强张力后必须给短余波、关系缓冲或明确悬置理由。
- 道具交接、转身、起身、开门、离场、手腕控制、躺/靠/伏/抱/扶/摔倒/坐起/披衣/下车/屏幕显示等状态变化必须写“起始 → 支撑/接触/方向 → 可见转换 → 释放/稳定终态 → 下一镜继承”；动作强时运镜降为固定或低幅推近。
- 镜头语言使用组件化知识储备：听者被击中、关系拉开、手部泄露、正反打保轴、手机消息浮层、口型交接、物件缓冲、行走转对白等组件每个子镜最多选一个，并改写成当前人物、空间、道具和台词。
- 每镜建立 `sequence_directing_plan`，说明它在整场“建立→保持/推进→破格→释放/解决”视觉句子中的位置，并锁定距离/焦段阶段、构图母题、人物与摄影机联合调度、环境节拍和交接目标。运镜后的信息收益为空时保持机位；联合调度失败时使用不删戏眼的稳定备选。
- 每镜建立 `cut_decision_contract`，在 hold/action/reaction/dialogue/sound/delayed/match/scene_transition 中只选一种，写清触发、切前停留、切后信息增量、声音策略、镜头经济性和稳定备选。剪辑分析不进入直投正文，正文只呈现当前可见触发。
- 每镜建立 `sound_directing_plan`：主声源、方向与距离、房间/环境响应、前后声部优先级、静音/骤停、声音先于画面进入或延后退出、对切点的支持。原生音频关闭时只保留为配音/后期元数据；开启时正文至少落实一项空间声或声画先后，不让音乐和环境声压住台词。
- 写正文前建立 `prompt_information_budget`：按 environment/object/action/dialogue/dramatic 保护唯一主渲染任务、不可删除事实和一个辅助视觉层，明确只留元数据的分析，并限制1–2个视觉增强点。新增导演合同不得增加信息竞争、突破700字或挤压源文、口型、动作终态与关键道具。
- 手机聊天、来电名称、通知弹窗等 UI 文字若由 AI 生成，必须声明独立二维浮层、安全区和透视隔离；否则把具体文字留到后期文字表。
- 人物正在看、读、玩、点击或操作手机屏幕、平板、电脑屏幕、书页、文件、照片、表盘、镜面或仪表盘时，必须启用 `prop_functional_surface_contract`。先锁“功能面朝使用者、使用者视线落在功能面、摄影机实际看见哪一面、手部接触与操作证据、方向终态”，再写正文；默认用背壳/背面/侧边朝摄影机和屏幕光/翻页/点按等证据表达，不靠“禁止翻转”长负面句。需要观众读内容时改用肩后/过肩/俯拍/斜上方同侧机位，复杂内容另拆展示镜头。普通静置或递交不触发，不增加批次负载。
- 所有清晰人物表演镜必须启用 `skin_tone_protection_contract`。脸部主光、补光和曝光独立于环境色卡：冷青、冷绿、霓虹只落在背景、衣物边缘或轮廓反光，旧墙斑驳、水渍、灰尘、雾粒与丁达尔光束只留在环境或中后景；正文用正向空间事实写清边界。源文明示的伤痕、妆容、泪痕、污迹和剪影分别使用 `source_authorized_marks/silhouette`，不得被肤色保护误删；同场跨镜保持肤色基准、白平衡和面部明暗方向。
- 人物、对白、道具变化、重要叙事或高风险镜必须有 `story_punch_contract`、`performance_contract`、`continuity_contract` 与 `reroll_control`。戏眼合同必须额外锁定唯一构图优先级与运镜动机：构图说明主体、前中后景/留白/遮挡/距离或焦点关系，运镜说明唯一策略及它响应的表演、台词、道具或空间触发；不得以“电影感、聚焦人物、缓慢推近”代替。`rising/peak` 另需 `pressure_release_design`。
- 复杂互动优先拆镜或降运镜，不能靠更多修辞、更多表情或更长静止来掩盖模型负担。
- 原生音频开启时，台词必须以 `{人物}（台词/OS/OV）: "原文"` 在子镜头组逐字出现一次；关闭时原文仅保留在元数据与导出表。
- 每条台词时间窗必须容纳按人物本镜语速、原文标点、句前/中段气口和句末收气估算的自然表演时长；两个 `visible + lip_sync=true` 事件不得重叠，可见对白必须写口型同步和句末闭口落幅。
- 新对白事件记录 `conversation_mode/response_latency/overlap_or_interrupt_window/conversation_source_basis`。源文支持时允许抢话、被打断、半句停住、自我修正、答非所问或短暂声音重叠，但只调整时间、气口、声音交接和闭口边界，不改字、不增词；直投正文只写可见停顿、抢话、收句与反应，不泄漏会话分析标签。

## 性能与测试

- 性能目标是 50 主镜 P95 不超过 55 分钟，不是当前声明。只有三类场景（对白、动作、混合）各一组正常与 10% 失败注入的真实运行通过 `benchmark_core_pipeline.py` 后，才能声称达标。
- `performance_budget.py` 从 pipeline state 输出总耗时、local/worker/暂停估算拆分、每阶段耗时、dispatch 数、重试数和达标状态。
- 结构回归：`python3 scripts/test_current_pipeline.py`、`python3 scripts/test_quality_upgrades.py`、`python3 scripts/test_production_intelligence.py`、`python3 scripts/test_keyframe_pipeline.py` 与 `python3 scripts/golden_jimeng_check.py`；Golden 同时覆盖对白、动作、道具、UI、多人、环境、冷青/霓虹/火光/车灯/水波/混合色温/深色肤色、透视纵深和沿景深移动。
- 真实源文 smoke test：`python3 scripts/test_source_smoke.py --source <source.txt> --min-shots <n>`。该测试只验证确定性配置、拆镜、台账、时长、preflight 与 packet 化，不伪造 Agent 输出或成片验收。
- 实际成片 A/B 只能用 `validate_visual_ab_review.py <manifest.json>` 登记。每例必须提供两个不同的真实非空视频文件、盲评确认、评审者、七维1–10分、提示词SHA256和盲评后揭示的 before/after 映射；缺少视频时阻断，Golden 文本不得冒充成片证据。
- 已完成真实 E2E 回归：`python3 scripts/test_completed_e2e_run.py --run-dir <completed_run_dir> --source <source.txt> --expected-shots <n>`。该测试只验收真实 supervisor/worker/provenance 产物，不生成或伪造 Agent 输出。
- 构造 50 镜 benchmark fixture：`python3 scripts/create_benchmark_fixtures.py --out-dir <fixture_dir>`，再用 `benchmark_core_pipeline.py` 验证六组结构。fixture 报告只证明 benchmark 机制可复跑；只有 `evidence_kind=real_pipeline` 的六组真实 Agent 运行才可声明真实 SLO。

## 常用命令

```bash
python3 scripts/route_task.py full --run-dir <run_dir> --intent new
python3 scripts/route_task.py full --run-dir <run_dir> --intent new --config <complete_config.json> --source <source.txt> --auto-start
python3 scripts/workflow_supervisor.py --run-dir <run_dir> --source <source.txt>
python3 scripts/test_fast_start.py
python3 scripts/test_current_pipeline.py
python3 scripts/test_quality_upgrades.py
python3 scripts/golden_jimeng_check.py
python3 scripts/test_source_smoke.py --source <source.txt> --min-shots 1
python3 scripts/test_completed_e2e_run.py --run-dir <completed_run_dir> --source <source.txt> --expected-shots <n>
python3 scripts/run_regression_suite.py --source <source.txt> --min-shots <n> --completed-run <completed_run_dir> --expected-shots <n> --benchmark-report <report.json>
python3 scripts/run_regression_suite.py --source <source.txt> --min-shots <n> --completed-run <completed_run_dir> --expected-shots <n> --synthetic-benchmark-dir <fixture_dir>
python3 scripts/create_benchmark_fixtures.py --out-dir <fixture_dir>
python3 scripts/benchmark_core_pipeline.py --out <benchmark_report.json> <completed_50_shot_run_dir> [...]
```

Windows 的多行内容先写入文件，再将短参数与路径交给 `scripts/run_skill_tool.ps1`；不得将 JSON、提示词或 here-string 拼入 shell 命令。
