# Master Production Decision Slice

权威来源仍是 `references/format_constraints.md` §B7。本文件只作为快速定位切片。

`qa_metadata.source_constraint_basemap` 是生成前底图，不投喂模型。可包含：

`space_basis / state_prop_basis / character_orientation_basis / tension_curve_role / sound_lip_sync_basis / screen_text_policy / single_shot_risk / visible_people_gate / performance_baseline_lock / emotion_micro_chain / dialogue_performance_kernel / emotion_residue_contract / physical_structure_chain / shot_component_choice / viewpoint_motion_lock / premium_director_polish / creative_profile`

核心规则：

- 必填基础字段必须是非空扁平字符串。
- `visible_people_gate` 写本镜可见人数、清晰/肩线/虚化/画外分类。
- `performance_baseline_lock` 写主要人物常态控制方式、优先泄露部位、默认动作幅度、爆发阈值和禁用表演习惯。
- `emotion_micro_chain` 写本镜情绪触发后选择的 3–5 个微动作。
- `dialogue_performance_kernel` 写台词功能、说话者口型、关键词重音、听者低幅反应、句末闭口和余波落幅；无对白写 none。
- `dialogue_performance_kernel` 只压缩生成决策；逐句 `line_function/subtext/stress_words/subtext_visible_evidence/turn_relation` 仍写入 `dialogue_events`。投喂正文只接收原文重音的说法和潜台词的可见证据，不接收分析标签。
- `emotion_residue_contract` 写触发前状态、泄露部位、压抑/释放方式和尾帧残留；无情绪承接写 none。
- `physical_structure_chain` 写本镜所有概括动作的起点、接触、转换和终态。
- `shot_component_choice` 写本镜采用的唯一镜头组件或明确写 none。
- `viewpoint_motion_lock` 写特殊视角的摄影机绑定关系、相对高度/距离、唯一主路径、速度曲线、至多一次焦点交接、稳定落幅和降级/拆镜阈值；不使用时写 none。
- `premium_director_polish` 写本镜即梦友好卡的前台精修目标：顺序、戏眼、质感锚点和落幅；不得新增模型事实。
- `creative_profile` 只能为 safe、balanced 或 expressive；它只调节创作自由度，不降低任何质量门槛。

相邻的逐镜决策合同也在同一次 Master Production 任务内完成，不需要额外读取知识库全文：

- `character_scene_objective_contract`：锁定角色目标、失败代价、障碍、当前策略、可见策略证据、
  策略切换、信息差与权力变化；心理判断先转成行动证据再进入正文。
- `relationship_emotion_arc`：锁定关系起点、冲突欲望、情绪错位、转折、权力变化、关系终态与共同余波。
- `story_punch_contract`：只保留一个构图优先级和一个由台词、表演、道具或空间触发的运镜/固定策略。
- `sequence_directing_plan`：说明本镜在建立、推进、破格、释放中的位置及与相邻镜的交接目标。
- `cut_decision_contract`：只选一个切点类型，写触发、切前停留、切后信息增量、声音策略和稳定备选。
- `sound_directing_plan`：锁定主声源方向与距离、房间响应、声部优先级、声画先后和切点支持。
- `prompt_information_budget`：保护唯一主任务、源文、动作终态和关键道具，只允许 1–2 个视觉增强点；
  其余分析留在元数据。

逐句对白、情绪强度、角色目标、关系判断、序列位置、剪辑类型和声音分析都不得以字段名或枚举名
进入 `full_prompt`。只输出当前可见的口型、重音说法、停顿、手眼/道具/距离证据、构图、运镜响应、
空间声和稳定落幅。
