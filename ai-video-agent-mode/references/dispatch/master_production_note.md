# Master Production Execution Note

每个 `packet.items` 只生成一条即梦 T2V 主镜任务，输出顶层只能是 `{"shots":[...]}`，并写入
`packet._batch_output_path`。先读 scene lock cache 和 composer scaffold；保留全部 locked fields，
再按 sidecar 的 direct-copy、Master、视觉质量和静态/动态美学切片填写空字段。
scaffold 的 `scene_motion_plan_path` 提供跨镜动态职责，不得把内部角色名写进正文；
`scene_texture_plan_path` 提供场级视频质感，预填 `video_texture_contract` 不得清空。
风险字段仅填 scaffold 已有项；缺席即不适用，不得补回；质量门槛不变。

## 生成顺序

1. 锁定源文、单一 `narrative_beat_id`、时长、人物、台词和起终态。第二目标、第二动作链、回切或
   第二次注意力交接必须拆镜，不得把两个可独立复述的事件塞入同一 `shot_group`。
2. 建立 source basemap、`scene_tone_palette`、人物行动/关系、序列/切点、声音和信息预算。
3. 执行 `visual_bible → aesthetic_director → continuity_compiler`，填写
   `static_aesthetic_contract`、`dynamic_aesthetic_contract` 与 `aesthetic_priority`。
4. 编写五段 `full_prompt`、独立负面词和 QA。每镜完成即运行 `incremental_validation_command`，
   只修报告范围；批末 `local_validation_command` 必须覆盖全部 items 并 PASS，增量通过不能替代它。

## 源文、空间与连续性

- Scene Lock 是空间、入口、左右、道具活动区、服装、光源和影调唯一来源。同地点复用
  `space_id/space_master_sentence`；从 `foreground_layer/midground_layer/background_layer`
  选择至少两层具体空间细节，并保留题材气味、生活痕迹和焦平面主次。
- 将制作级影调色卡压缩进 `scene_tone_palette`，只消费当前镜的一项光影任务。风景身份使用
  `landscape_identity/landscape_composition`、自然运动、环境弧、揭示、光候和呼吸事实；人物镜
  只取一项不抢戏环境事实，环境镜取两项。
- 活动道具写完整物理结构链和生命周期；多人纵深保持共同支撑平面、近大远小和连续尺度。
  功能面风险填写 `prop_functional_surface_contract`，写正向可见面与操作证据，
  不得用“禁止翻转”替代空间事实。
- 先做视觉先验风险分类：背对视线、镜面/照片、驾驶视线、功能面、遮挡/肩线/倒影误生人物。
  高风险镜使用起始/戏眼/结束三状态关键帧并检查事实一致性。

## 人物、表演与声音

- 先写可见人数闸门；清晰、肩线/背影/虚化和纯画外分开。不可见人物不能作为看向目标；
  清晰非主表演者必须有低幅观察/受击反应或降为非清晰层。
- 人物镜填写 `character_scene_objective_contract`，对手戏填写 `relationship_emotion_arc`；目标、
  信息差和权力判断只作推导，正文只写可见策略、距离、道具和行动落幅。
- 角色表演基线锁定常态控制、泄露部位、动作幅度、爆发阈值和禁用习惯。情绪微表演链只选
  当前景别可见的 3–5 个证据，禁止只写开心、伤心、生气等抽象标签。
- 台词逐字保留。`dialogue_performance_kernel` 与逐句 `dialogue_events` 先推导功能、潜台词、
  1–3 个原文重音词和 `subtext_visible_evidence`；`emotion_delta` 只留元数据。正文只写说法、口型、
  听者反应、句末闭口和余波。`dialogue_events.time_range` 必须容纳自然气口，可见口型窗不得重叠。
- `response_latency`、抢话/打断窗口和短暂声音重叠必须有源文依据，不改字、不增词。
  OS/OV/画外声闭口。项目级声音锁定保持音色基准，`sound_directing_plan` 再写空间声、方向距离、
  房间响应、声画先后与 ducking。

## 导演、美学与信息预算

- `sequence_directing_plan` 让镜头处于建立/推进/破格/释放之一；`cut_decision_contract` 只选一个
  切点并写切后信息增量。分析词和“切到/反打/继承/尾帧”不得进入 direct-copy。
- 每镜只保留一个构图优先级、一个有触发的运镜或固定策略、一个主要人物动作、一条因果响应链
  和至多一次焦点交接。低风险镜的响应链最多两个共享动力源的低幅响应，长对白、多人、道具转移、
  复杂支撑或腾空镜只保留一个。特殊视角必须锁定摄影机关系、主路径和稳定落幅；
  穿越、ACT、FPV、POV、水平横移、鸟瞰不能只写标签。
- `visual_bible` 锁定色彩职责、动机光、曝光、构图家族、材质与空气层。光影句必须包含光源、
  方向、受光面和阴影结果；清晰人物填写 `skin_tone_protection_contract`，保持自然面光并把空气介质退后。
- 静态合同先确定唯一视线路径和记忆帧；动态合同按起始→触发→稳定终态组织。材质、反射、雨雾尘
  只响应同一物理原因。失稳时先去运镜，再去次要环境运动，不删剧情终态。
- 动态合同先服从 motion plan 的跨镜职责和响应预算：没有源文/Scene Lock 动力源时允许稳定观察；
  不得为了匹配 initiate/propagate/payoff 等内部职责而新增动作。同一场相邻镜优先轮换道具接触、
  重心、视线/头身相位、声音呼吸、现实光源或稳定观察，不把慢推、眨眼、衣摆和薄雾当默认灵动。
- `video_texture_contract` 继承场级影像基调、曝光、材质运动、空气运动、镜头稳定和跨镜连续；
  单镜正文只落地一个曝光/受光点、一个材质响应和一条镜头稳定规则，不复制完整场级合同。
- `prompt_information_budget` 保护源文、空间、口型、动作终态、关键道具和唯一视觉论点，只选
  1–2 个增强点；新增导演合同不构成加长正文。镜头组件只能作为知识储备使用并改写成当前事实。
- 前台导演精修层只优化可见表达。`creative_profile` 只能 safe/balanced/expressive；
  `emotion_residue_contract`、分析标签、分值和风险结论不进入正文。

## 直投与稳定

- `full_prompt` 只写正向、可见、可执行事实；负向概念只进入 `negative_prompt`。复杂度分档只减少内部合同，
  不降低直投质量；不设最低字数，短镜仍必须具备当前任务所需的空间、表演、光影和终端稳定事实。
- 每场先填写镜头组构图/运镜计划，每镜选择一个有空间依据的构图骨架和一个固定/单一路径策略；连续三镜不得复用同一“景别+角度+构图+运镜”组合。每镜填写 `terminal_frame_contract`，并将最后20%的可见人数、槽位、人物边界、道具归属、支撑接触、摄影机停稳、光曝锁定及不新增/不重复主体编译进 `full_prompt`。
- 写完 `【本镜制作控制】` 后逐项反查 `full_prompt`：质感、光曝、动态、表演、穿帮、可见降级结果和已启用蒙太奇结果必须各有画面证据；风险级别、人工检查、后期和拆镜决定只留在制作控制。不要依赖 Export 自动补写，grounding 缺失会直接阻断。
- direct-copy 顺序保持画幅/风格→空间影调→主体与可见人数→表演/台词→镜头→光影材质→落幅。
  不复制整张色卡，不堆多色温、雾、光晕、反射、多运镜或多次转焦。
- 接触、受力、交接、多人走位或长台词先保物理和口型；动作强时固定或低幅运镜。风险高时启用
  `reroll_control` 和人工首轮检查，不得以更长修辞掩盖生成负担。
- 不新增剧情、人物、道具、天气或声音。不要输出分析过程；完成前运行 packet 中的完整
  `local_validation_command`，失败按报告的字段/主镜/pair/window 范围修复，不得用不同命令或局部检查声称 PASS。
