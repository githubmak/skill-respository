# Source Basemap Contract Slice

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
