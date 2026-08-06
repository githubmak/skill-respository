# Master Production Execution Note

`creative_engineering_boundary.md` 是最高合同。剧情、情绪、表演、构图、运镜、光影、声音和提示词精炼
由本 Agent 创作；不得依赖 Normalizer、Merge 或 Export 删句、选句、改写 Scene Lock 或删除字段。

每个 `packet.items` 只生成一条即梦 T2V 主镜任务，输出 `{"shots":[...]}` 到
`packet._batch_output_path`。从 `composer_scaffold_path` 开始，保留锁定字段；风险字段只填 scaffold
已有项，缺席即不适用、不得补回。每镜运行 `incremental_validation_command`，批末运行完整校验，增量通过不能替代批末验证。

## 创作顺序

1. 锁定源文、单一 `narrative_beat_id`、时长、人物、台词和起终态；第二目标或第二动作链拆镜。
2. 读取 Scene Lock 与模型蓝图，建立视觉、表演、连续性、声音和本镜 `video_texture_contract` 设计。
3. 执行 `visual_bible → aesthetic_director → continuity_compiler`，填写
   `static_aesthetic_contract`、`dynamic_aesthetic_contract`、`aesthetic_priority` 和 `video_texture_contract`。
4. 创作五段 `full_prompt` 和不超过500字的 `director_card`。两者都由模型语义精炼，工程层只计数和精确去重。

## 必要创作控制

- Scene Lock 是空间、入口、道具活动区、服装、光源和影调事实源。从
  `foreground_layer/midground_layer/background_layer` 取至少两层具体空间细节；`scene_tone_palette`
  是制作级影调色卡。风景身份消费 `landscape_identity/landscape_composition`，人物镜不让环境抢戏。
- 活动道具写物理结构链、接触、运动和终态。功能面使用 `prop_functional_surface_contract`，不得用“禁止翻转”替代空间事实；
  清晰人物使用 `skin_tone_protection_contract` 并把空气介质退后。
- 先做可见人数闸门；不可见人物不能作为看向目标。角色表演基线锁定常态控制、泄露部位、动作幅度、
  爆发阈值和禁用习惯。情绪微表演链只写当前景别可见证据，禁止只写开心、伤心、生气等标签。
- 人物镜填写 `character_scene_objective_contract`，对手戏填写 `relationship_emotion_arc`。对白使用
  `dialogue_performance_kernel` 和 `dialogue_events`；`subtext_visible_evidence` 转成可见证据，`emotion_delta`
  只留元数据。`dialogue_events.time_range` 容纳气口且口型窗不得重叠；`response_latency` 和短暂声音重叠必须有源文依据。
- 项目级声音锁定保持音色；`sound_directing_plan` 负责空间声、方向、距离、房间响应和 ducking。
- `sequence_directing_plan` 组织建立/推进/破格/释放，`cut_decision_contract` 只选一个有信息增量的切点。
  每镜一个构图优先级、一个运镜或固定策略、一个主体动作和一条响应链；镜头组件只能作为知识储备使用。
- 特殊视角必须写摄影机关系、主路径和稳定落幅；穿越、ACT、FPV、POV、水平横移、鸟瞰不能只写标签。
  视觉先验风险分类命中高风险时创作三状态关键帧，但不得改变 T2V 事实。
- 前台导演精修层只优化可见表达；`creative_profile` 只控制创作自由度，`emotion_residue_contract` 不直接进入正文。
  `prompt_information_budget` 保护源文、空间、口型、动作终态和关键道具；新增导演合同不构成加长正文。
- 复杂度分档只减少内部合同，不降低直投质量；不设最低字数。直投按画幅/风格→空间影调→主体与人数→
  表演/台词→镜头→光影材质→落幅组织，由本 Agent 控制在700字内；超限时由模型重写，不得让工程层删句。

不新增剧情、人物、道具、天气或声音，不输出分析过程。校验失败只修报告授权范围；如果修复需要改变
整体导演逻辑，明确升级到主镜或场景创作范围，不能用字段补丁破坏镜头整体性。
