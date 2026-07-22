# Format Constraints — Mode C v4

本文件是 AI Video Agent Mode 的唯一权威数据契约。主 `SKILL.md`、Agent 指令、验证器、归一化与导出脚本必须服从本文件。

## §0 — Example Isolation Rule

示例和质量样例只传递结构方法，不传递项目风格。Agent 可以学习其中的因果表演链、连续时间段、道具状态转移、系统文字安全区、口型边界、落幅残留和低抽卡控制；禁止把示例里的现代都市、轻喜剧、柔光、酒店、韩漫、特定服装、特定角色关系或特定道具状态自动写进当前项目。当前镜头的题材、节奏、画幅、光线、服装、场景和角色关系只能来自原剧本、用户配置、项目 bible、scene lock cache 或已确认参考资产。

## §A — Phase 2 Analysis Output

### A1. 顶层结构

```json
{"items": []}
```

- Phase 2 只允许 `items` 一个顶层数组键。
- 禁止 `shots`、`sub_shots`、`analyses`、中文结构键或额外 meta/data。
- batch 与 merged 文件使用同一结构。

### A2. 通用字段

每个 item 必须包含：

```json
{
  "id": "S1-01-01",
  "shot_id": "S1-01",
  "subshot_id": "S1-01-01"
}
```

- `id` 与 `subshot_id` 相同。
- `shot_id` 是主镜头 ID。
- 字段使用 snake_case 英文，顺序与 dispatch 一致。

### A3. Emotion Item

```json
{
  "id": "",
  "shot_id": "",
  "subshot_id": "",
  "emotion_type": "",
  "expression_level": "micro",
  "gaze": "",
  "micro_expression": "",
  "body_tension": "",
  "body_parts_focus": "",
  "voice_tone": "",
  "action_beat_start": "",
  "action_beat_transition": "",
  "action_beat_end": "",
  "per_char_actions": [
    {
      "character": "",
      "performance_role": "primary",
      "beat_start": "",
      "beat_transition": "",
      "beat_end": "",
      "micro_expression": "",
      "body_parts_focus": ""
    }
  ],
  "emotion_trigger_short": "",
  "performance_note": "",
  "performance_chain": {
    "trigger": "剧情触发原因",
    "facial_control": "当前景别可见的眼神、眉尾、嘴角或呼吸变化",
    "detail_leak": "由指尖、袖口、领口、手机、外套或其他已确认道具开始的泄露",
    "body_follow_through": "肩背、重心、步伐或接触关系如何承接",
    "voice_delivery": "台词/OS/OV的语气，或无台词时的呼吸落点",
    "end_residue": "下一节拍仍可见的状态"
  }
}
```

- `expression_level` 只允许 `micro / visible / strong`。
- `performance_role` 只允许 `primary / supporting / background`。
- 有人物镜头只能有一个 primary；最多一个 supporting focus，其他角色归 background。
- background 不强制独立微反应，可使用群体连续状态。
- “有意不反应”允许，但必须写明触发原因与可见终态。
- `performance_chain` 是所有后续镜头决策的共同输入。每项只写当前景别可见的一个主证据；道具未由剧本、配置或前镜确认时不得伪造为情绪泄露载体。

### A4. Scene Item

```json
{
  "id": "",
  "shot_id": "",
  "subshot_id": "",
  "space_type": "",
  "space_name": "",
  "char_positions": [],
  "char_wardrobes": [],
  "bg_foreground": "",
  "bg_midground": "",
  "bg_background": "",
  "light_type": "",
  "light_temp": 5200,
  "light_direction": "",
  "light_hardness": "soft",
  "mood_atmosphere": "",
  "ambient_sound": "",
  "audio_background": "",
  "audio_foreground": "",
  "audio_midground": "",
  "bgm_style": "",
  "color_contrast_desc": "",
  "light_effect_primary_char": "",
  "light_effect_other_chars": "",
  "lighting": "",
  "sfx_timing": "",
  "prop_state": "本镜确认的道具归属、接触、遮挡、损伤或未变化状态；无关键道具则明确无",
  "start_carryover": "从上一镜继承的位置、道具、光线或空间状态；首镜写场景建立状态",
  "end_carryover": "本镜结束后下一镜必须继承的空间、道具或光线状态"
}
```

- `light_hardness` 只允许 `soft / hard / mixed`。
- `light_temp` 是数字 K 值，不带 K 后缀。
- 同一场景景别变化不改变光源与色温；变化必须由剧情内光源事件解释。
- 前中背景写可见物，不写工程标签。
- `prop_state`、`start_carryover`、`end_carryover` 是场景首产物，不得留给 Composer 猜测；它们必须与人物站位和光源一并承接到下一镜。

### A5. Camera Item

```json
{
  "id": "",
  "shot_id": "",
  "subshot_id": "",
  "shot_size": "",
  "camera_lens_mm": 35,
  "camera_relative_pos": "",
  "camera_distance_steps": 2,
  "camera_height_relative": "",
  "angle_str": "",
  "camera_facing_desc": "",
  "movement_type": "固定",
  "movement_detail": "",
  "movement_speed": "",
  "axis_start": "",
  "axis_end": "",
  "char_entry": "",
  "char_exit": "",
  "end_state": "",
  "composition": "",
  "lens_effect": "",
  "movement_arc_deg": 0,
  "body_extra": "",
  "editorial_mode": "continuous_take | motivated_sequence",
  "camera_beat_map": [
    {
      "trigger": "表演链中的具体重音",
      "visual_priority": "当前主要人物/道具/关系",
      "camera_response": "hold | push_in | reframe | cut_reaction | cut_detail | follow",
      "time_range": "1.2-2.0秒",
      "focus_subject": "承担本节拍的人物、手部或道具",
      "framing": "中近景 | 特写 | 双人中景等落幅景别与构图",
      "axis_relation": "相对既有轴线的同侧/反打关系与左右位置",
      "transition_type": "hold | motivated_cut | motivated_reframe | continuous_move",
      "carryover": "切换后必须保留的人物、道具、轴线或光源状态"
    }
  ],
  "scene_anchor_usage": {
    "position_anchor": "引用 scene_analysis.char_positions 的具体站位或无人物构图锚点",
    "light_anchor": "引用 scene_analysis.light_direction/light_temp 的构图或轴线约束",
    "prop_anchor": "引用 scene_analysis.prop_state 的焦点或遮挡约束",
    "carryover_anchor": "引用 scene_analysis.start_carryover/end_carryover 的起落幅承接"
  },
  "sequence_context": {
    "sequence_id": "仅连续拆分时填写",
    "segment_index": 1,
    "segment_count": 1,
    "entry_carryover": "本段开头继承的状态",
    "exit_carryover": "本段结束交给下一段的状态"
  }
}
```

- `shot_size`：大特写、特写、中近景、中景、全景、大远景。
- `movement_type`：固定、推、拉、摇、移、跟、升、降、俯、仰、环绕、甩、变焦、旋转、手持、穿梭。
- `continuous_take` 每子镜只能有一个主要 `movement_type`；复合移动必须是同一方向的连续轨迹。`motivated_sequence` 使用 1–3 项 `camera_beat_map`，每项必须由 `performance_chain` 的表情、细部/道具泄露、身体承接或语气落点触发；每项明确发生时间、视觉主体、落幅景别、轴线关系、转场类型与状态承接。可自然反打、切特写或移镜，但不能无动机反复抢焦。
- 仅当一个连续剧情动作、长台词或连续关系判断必须拆成多个子镜时，填写 `sequence_context`。各段继承上一段的姿态、道具、声音边界和情绪残留；不得每段从中性站姿重新起演。
- 注意力交接只能选择一种主策略：固定双人构图内一次拉焦、一次单向摇/移重构图、或演员走位改变画面权重而机位固定。物理运镜与拉焦不得叠加成竞争控制。
- 相邻镜头允许相同景别；不为“景别梯度”强制变化。
- 焦距是剧情启发式。情绪镜不强制 85mm；镜头必须同时满足空间关系、人物数量和面部可见性。
- 人物朝向剧情对象。除非原文明确自拍视频、直播、对观众说话或看镜头内设备，不得直视镜头。
- Camera 必须消费 packet 中的 `scene_analysis`，并在 `scene_anchor_usage` 中写明它如何使用站位、光线、道具与承接。不得用抽象“延续场景”代替可核验锚点。

## §B — Phase 6 Composer Batch Output

### B1. 顶层与 shot 结构

Composer batch 只输出：

```json
{
  "shots": [
    {
      "shot_id": "S1-01",
      "subshot_id": "S1-01-01",
      "duration": 5.0,
      "full_prompt": "",
      "negative_prompt": "{{NEGATIVE_PROMPT_AUTO_INJECT}}",
      "qa_metadata": {
        "dramatic_goal": "",
        "editorial_mode": "continuous_take | motivated_sequence",
        "camera_beat_map": [],
        "sequence_context": {},
        "quality_contract": {
          "profile": "environment | object | action | dialogue | dramatic",
          "required_analysis": ["scene", "camera"],
          "required_evidence": ["该类型必须在成片提示词中可见的质量证据"]
        },
        "quality_evidence": {"每项required_evidence": {"section": "画面锁定|镜头设计|表演时间轴|光照与声音", "fragment": "该段中逐字存在的可见证据"}},
        "performance_priority": {
          "primary": "角色A",
          "supporting": ["角色B"],
          "background": []
        },
        "action_budget": {
          "primary_action_count": 1,
          "emotion_turn_count": 1,
          "supporting_reaction_count": 1,
          "physical_camera_move_count": 1,
          "editorial_response_count": 0
        },
        "start_state": "",
        "end_state": "",
        "performance_causality": {
          "tension_intent": "latent",
          "trigger": "",
          "response_order": [],
          "physical_logic": "",
          "motion_boundary": "",
          "hold_strategy": "",
          "end_residue": ""
        },
        "performance_contract": {
          "tension_intent": "latent",
          "trigger_event": "",
          "trigger_time": "1.2秒",
          "primary_expression": "",
          "primary_body_action": "",
          "eye_focus": "",
          "reaction_delay": "",
        "voice_or_breath_control": "",
        "viewer_empathy_anchor": "",
        "readable_image_moment": "",
        "suppression_or_release": "",
        "camera_pressure": "",
        "scene_pressure": "",
          "end_residue": ""
        },
        "continuity_contract": {
          "start_anchor": "",
          "end_anchor": "",
          "position_continuity": "",
          "eyeline_continuity": "",
          "prop_state": "",
          "lighting_continuity": "",
          "next_carryover": ""
        },
        "reroll_control": {
          "risk_level": "medium",
          "identity_anchor": "",
          "motion_anchor": "",
          "scene_anchor": "",
          "camera_anchor": "",
          "risk_reason": "",
          "mitigation_steps": [],
          "needs_reference": false
        },
        "dialogue_events": [
          {
            "ref": "D1",
            "kind": "台词",
            "speaker": "角色A",
            "text": "原始台词逐字保留",
            "time_range": "0.8-2.6秒",
            "speaker_visibility": "visible",
            "facial_state": "",
            "body_state": "",
            "delivery": "",
            "lip_sync": true
          }
        ],
        "dialogue_refs": ["D1"]
      },
      "generation_control": {
        "mode": "t2v",
        "audio_enabled": true,
        "reference_assets": []
      }
    }
  ]
}
```

- batch 顶层不能出现 `items` 或其他键。
- 每个 dispatch subshot 恰好输出一次，顺序一致。
- 输出必须以 dispatch 的 `composer_scaffold_path` 为骨架；`shot_id/subshot_id/duration/negative_prompt/qa_metadata.dialogue_refs/qa_metadata.dialogue_events[].ref|kind|speaker|text/generation_control` 是确定性锁定字段，Agent 不得改写。
- 相同场景的画幅、风格、服装、共享光源与空间锚点只从 `scene_lock_cache_path` 读取一次；各镜通过 `scene_lock_ref` 引用，不重复推导场景不变项。
- `mode` 只允许 `t2v / i2v / r2v`。
- I2V/R2V 必须有真实 `reference_assets[]`，每项含 `type` 与 `path`。禁止伪造路径。

### B2. full_prompt 四段

`full_prompt` 必须且只能包含：

1. `画面锁定：...`
2. `镜头设计：...`
3. `表演时间轴：...`
4. `光照与声音：...`

段间恰好一个空行。禁止旧版八字段、模板编号、自包含验证、负面词、QA 结论和工程字段。

#### 画面锁定

- 以 `{canvas}画幅，{visual_style}` 开头。
- 当 `generation_control.mode=i2v/r2v` 且已确认参考图或参考视频存在时，`画面锁定` 段可在画幅前追加平台支持的参考资源标记，并写明锁定人物五官、发型、服饰和身份连续性。参考标记必须来自 `reference_assets` 的真实 `path/id/prompt_handle`，无真实资产时禁止出现伪造平台引用。
- `{canvas}` 与 `{visual_style}` 只能来自当前项目配置或 scene lock cache；不得沿用示例中的现代都市、轻喜剧、柔光、酒店、韩漫等项目限定词。
- 只写本镜必须锁定的主体、服装、站位、朝向、场景接触和身份连续性。
- 场景不变项只写一次，不重复灯光和动作过程。
- 有人物时提供一项真实场景接触：脚底/椅面/桌沿/道具/接触阴影/前景遮挡/环境反射。
- 系统声、系统提示或悬浮文字只允许作为画外声、界面层或侧边安全区彩色悬浮文字出现；不得实体入画、遮挡人物脸部、压住口型或破坏主表演焦点。

#### 镜头设计

使用顺序：

```text
时长：5.0秒。景别：中近景。焦距：50mm。机位：……。轴线：……。主要运镜：固定，落幅时轻微收紧构图……。
```

- `continuous_take` 使用一种主要运镜、任一时刻一个注意力中心、一个落幅。同一互动链允许一次由台词/动作触发的 `A→B` 注意力交接。`motivated_sequence` 可在同一剧情目标内由表演链重音带出自然景别变化、反打或移镜；每个内部节拍仍只有一个主体，并沿用同一人物、道具、轴线与光源状态。
- 禁止只写“聚焦甲/聚焦乙”；必须写可见构图权重、前后景/焦点落点、摄影机方向与最终双人或关系落幅。
- 数值只保留 1–2 个决定性锚点；不堆 mm、度、速度和距离。
- `dramatic_goal` 留在 QA 元数据，不重复写入模型提示词。

#### 表演时间轴

- 使用 2–3 个连续小数秒时间段，从 `0.0` 覆盖到镜头总时长，无断档、重叠或倒置。
- 面向短视频生成平台时，段内语序优先为：景别可见主体 → 触发动作 → 表情控制 → 肢体承接 → 语气/呼吸/口型 → 必要动态稳定约束。该语序必须嵌入现有四段结构，不新增“动态约束”独立段落。
- 每段按 `可见触发 → 主角身体反应 → 对手必要反应 → 镜头落点` 写。
- 每个人物镜必须有一个观众可直接读懂的共情锚点和画面可读瞬间：先明确角色此刻被什么刺中、想护住什么、怕失去什么或正在忍住什么，再落成一个可见证据。共情锚点不能是“观众共情、感染力强、情绪到位”等结果词。
- 画面可读瞬间只选 1 个主证据并贯穿时间轴，如手停住、视线避开、肩背收紧、呼吸断半拍、道具状态改变或空间距离被压缩；不得为了画面感堆叠过多表情/肢体细节。
- 先按原剧情选择 `neutral / latent / rising / peak / release` 张力意图；不得默认把每镜都做成高张力，也不得用增加动作数量替代张力设计。
- 触发发生在时间段内部时必须写明确时点；角色反应要区分直接感知触发与观察他人后再反应，禁止无依据的多人同步启动。
- 突发、短促、立即类动作应在所属时间段前部完成接触点、转折点或制动点，并为受力、回稳和终态残留保留时间；原文明确缓慢动作时除外。
- 接触、阻挡、受力或截停的结果必须匹配接触点、支撑关系、受力方向和重心。杠杆不足时写提示、警告或角色主动收住，不得写成不可信的强制位移。
- 中断动作必须分别写清被取消的主运动与仍允许的残余运动；后段相似方向动作必须以幅度、身体部位或目的区分，禁止完整重做已被截停的动作。
- 长停顿占镜头超过约三分之一或持续超过 1.5 秒时，只保留 1–2 个景别可见的生命迹象，或给出有意静止的剧情理由；不得用密集微动作破坏静止状态。
- 3–6 秒镜头：主动作≤1、情绪转折≤1、对手反应≤1、主要运镜≤1。
- 6–10 秒镜头：主动作≤2、情绪转折≤1、对手反应总数≤2、主要运镜≤1。
- 10–15 秒连续互动：允许 2–3 个因果相接的内部节拍、多个短台词轮次和一次因果注意力交接。`continuous_take` 保持一条摄影机轨迹；`motivated_sequence` 可由表演重音带出 1–3 个自然景别/视角变化。两者都只能服务一个整体戏剧目标；第二个独立戏剧目标、无触发的反复抢焦或无关动作链必须拆镜。
- 时长服务于可见事件，不服务于氛围填充。单一微表情、一次视线变化、静态压场、群体凝视或落幅余韵默认不得超过 `project_config.max_static_shot_duration`（默认 6 秒）。落幅残留是承接下一镜的终态，不是额外延时。
- Phase 1 中任何超过该上限的子镜必须写入 `duration_rationale`（仅 `continuous_dialogue / continuous_interaction / continuous_action / sustained_reveal`）和按发生顺序排列的 `dramatic_beats[]`。6–10 秒至少 2 个可见因果节拍，10–15 秒至少 3 个；`continuous_dialogue` 需至少 3 秒有效台词，`continuous_interaction` 需至少两轮且合计 3 秒有效台词，`continuous_action`/`sustained_reveal` 必须有持续发生的画面过程。不得以“压迫感、静默、停顿、余韵、保持状态”作为理由。
- 有意静止仍可用于屏息、庄重或对峙，但必须在短镜内完成；若静止本身构成持续事件，`dramatic_beats[]` 必须写出期间发生的可见信息变化，而非重复“人物保持不动”。
- 打斗镜优先作为一个不切镜的连续动作链：≤6 秒最多 1 个接触节拍、6–10 秒最多 2 个、10–15 秒最多 3 个；所有节拍必须因果相接并共享同一主要摄影机轨迹。攻防双方之间的因果注意力传递不算独立换焦；换轴、切到独立主编舞链/戏剧焦点、换场景、第二条无关动作链或超过 15 秒才拆片段。
- 打斗镜按平台稳定性控制速度、幅度、接触节拍和镜头抖动；当动作复杂度超过单条可稳定生成范围时，必须在 `fight_continuity` 中锁定连续片段，或拆成下一生成片段。
- background 只写群体低幅连续状态，不逐人分配动作。
- 每个台词/OS/OV事件按 `qa_metadata.dialogue_events` 执行；`ref/kind/speaker/text` 不得改写，语气控制不得通过改标点或增删文字污染原文。
- `audio_enabled=true` 时，原文必须逐字且只出现一次，并且只放在表演时间轴。统一格式为 `{人物}（台词/OS/OV）：“{原文}”`，同一事件紧接人物神态、身体状态、说话语气和口型边界。
- `audio_enabled=false` 时，原文不得进入 `full_prompt`；表演时间轴仍写可见人物的神态、身体状态及台词口型边界，原文和配音控制保留在 `qa_metadata.dialogue_events` 与制作表。
- 可见台词人物按原文同步口型；可见OS/OV人物口型闭合。画外或非实体发声者不驱动任何可见角色口型；非说话 focus 角色口型闭合，背景统一无同步口型。
- 终态必须是画面可见状态并能承接下一镜，同时保留上一事件造成的姿态、接触、重心、视线、呼吸、道具或空间距离残留；除非剧情明确复位，不得落成“无事发生”。

#### 光照与声音

- 光源方向、色温、软硬和人物/环境同源关系保持跨镜连续。
- 光线风格服从当前剧本和项目配置；不得把示例中的夜晚暖光、酒店柔光、轻喜剧节奏或城市质感作为默认光声方案。
- `audio_enabled=true`：写关键环境声和声音同步关系；原始台词/OV/OS已在表演时间轴逐字出现，本段不得重复。音效最多保留 1–2 个叙事事件。
- `audio_enabled=false`：只写光照；台词与音频计划留在 `qa_metadata`/制作表，不占模型提示词。

### B3. 表演角色优先级

- `primary`：唯一主表演者，获得完整起始—触发—泄露—终态链。
- `supporting`：只对主事件做一次因果反应，不发起竞争动作。
- `background`：保持空间连续、低幅活动、无同步口型，不逐人写微表情。
- 每个可见角色必须且只能被分配到一个层级。

### B4. 动作预算与长度

- 没有审美最低字数；少于 120 字判定信息不完整。
- 超过 1100 字 blocking，必须拆镜。
- 3–6 秒常规镜头软目标 220–650 字；6–10 秒 350–850 字；复杂动作 450–900 字。
- 10–15 秒连续互动/动作链软目标 500–1050 字；仍受 1100 字硬上限约束。
- 不能通过增加背景微动作、光学数字或 QA 文案凑字数。
- `duration_rationale` 与 `dramatic_beats[]` 只属于 Phase 1 时长门禁和 QA，不得写入 `full_prompt`。它们必须能被 Composer 的时间轴和 Editor 的节奏审查追溯。

### B5. 景别可见性

- 大远景/全景：走位、重心、轮廓、衣摆、人与空间关系；禁止瞳孔、虹膜、眼睑、鼻翼、唇线和咬肌细节。
- 中景：肩线、重心、手臂、头部转向、可见呼吸；禁止瞳孔、虹膜、鼻翼和眼神光细节。
- 中近景：视线、手、肩颈、呼吸、口型。
- 特写/大特写：眼周、嘴角、下颌、口型；避免大幅位移和竞争运镜。

### B6. negative_prompt

- Composer 精确输出 `{{NEGATIVE_PROMPT_AUTO_INJECT}}`。
- `full_prompt` 中不能出现负面提示词标题或占位符。
- 归一化脚本按普通、多人、对白、参考驱动和打斗上下文注入精简词组；通用负面词覆盖肢体、手部、五官、身份漂移、帧间闪烁、光影突变、物体消失、穿插、口型、水印和画风突变等崩坏维度。
- 负面词只写不希望出现的概念，不写“禁止……”式正向命令。

### B7. qa_metadata

- 只用于制作和验证，不投喂视频模型。
- `dramatic_goal` 必须是本镜具体目标。
- `editorial_mode` 必须从 Director 逐字继承；它决定本镜执行一条连续轨迹，或一组由表演重音触发的镜头响应。
- `camera_beat_map` 与 `sequence_context` 也必须从 Director 逐字继承。前者不得由 Composer 重新发明；后者要求连续拆分从上一段状态起演而非重置。
- `motivated_sequence` 的每个镜头节拍都写明 `trigger/time_range/focus_subject/framing/axis_relation/transition_type/carryover`；Composer 将这些信息落到镜头设计与表演时间轴，不增加未声明的切换。
- `quality_contract` 由子镜类型确定并从 Director 锁定继承。它适用于任何生成模型：环境镜也必须证明叙事功能、视觉锚点、空间光线和转场承接；物件镜证明道具状态与焦点；人物镜证明对应的动作、台词或表演因果。不得因为某项分析被跳过而省略合同要求。
- `performance_priority` 覆盖全部可见人物且不能重叠。
- `action_budget` 使用非负整数并满足 B4 上限。
- `start_state` / `end_state` 写可见状态。
- `dialogue_refs` 与 Director 完全一致。
- `dialogue_events` 与 `dialogue_refs` 按相同顺序一一对应；无台词/OS/OV时输出空数组。每项结构固定：

```json
{
  "ref": "D1",
  "kind": "台词 | OS | OV",
  "speaker": "原文人物或声音归属者",
  "text": "逐字逐标点原文",
  "time_range": "0.8-2.6秒",
  "speaker_visibility": "visible | offscreen | nonphysical",
  "facial_state": "发声时间窗内、当前景别可见的具体神态",
  "body_state": "发声时间窗内的肩颈、手、重心、站姿或道具接触",
  "delivery": "语速、音量/气息、停顿/咬字/尾音控制",
  "lip_sync": true
}
```

- `ref/kind/speaker/text` 是确定性锁定字段；Composer 不得改变顺序、人物、类型、文字或标点。
- `time_range` 必须位于本镜时长内。`facial_state/body_state/delivery` 必须非空；可见人物的神态与身体状态必须落实到表演时间轴。
- `speaker_visibility=visible` 时人物必须在本镜可见；`offscreen/nonphysical` 时 `facial_state/body_state` 明确写 `N/A` 及不可见原因，不伪造表演。
- 可见台词人物 `lip_sync=true`；OS、OV、画外人物和非实体声音一律 `lip_sync=false`。
- `delivery` 至少覆盖语速、音量/气息、停顿/咬字/尾音中的两项；只写“紧张地、悲伤地、愤怒地、自然地”不合格。
- 有可见物理角色时必须增加 `performance_causality`；无可见物理角色的环境镜可省略：

```json
{
  "tension_intent": "neutral | latent | rising | peak | release",
  "trigger": "本镜可感知的事件、台词、动作、物件变化，或由可见起势承载的自主意图",
  "response_order": ["感知或起势", "身体反应", "必要的对手反应", "回稳或落幅"],
  "physical_logic": "接触点、支撑、受力、重心与结果的关系；无物理阻断时明确为自主改变动作",
  "motion_boundary": "被取消或完成的主运动，以及后续仍允许的残余运动",
  "hold_strategy": "长停顿采用的少量生命迹象或有意静止理由；无长停顿时明确写无",
  "end_residue": "上一事件在落幅仍可见的持续状态"
}
```

- `tension_intent` 只能五选一，描述本镜功能而非统一追求高强度。
- `response_order` 必须是非空有序数组；只记录景别可见、对戏剧目标必要的阶段，不为凑数增加微动作。
- 其余字段必须是非空可执行说明，不得只写“紧张、震惊、停住、自然反应、保持状态”等抽象结果。
- `performance_causality` 是 QA/导演元数据，不得拼入 `full_prompt`；Composer 根据它把必要的可见结果落实到表演时间轴，Editor Pass 2 复核语义真实性。
- 有可见物理角色时必须增加 `performance_contract`，它是“人物表情 + 身体动作 + 运镜压力 + 场景压力”的统一张力骨架，必须先于 `full_prompt` 生成：

```json
{
  "tension_intent": "neutral | latent | rising | peak | release",
  "trigger_event": "本镜触发张力的台词、动作、物件变化或自主起势",
  "trigger_time": "1.2秒；无明确时点时写无明确时点/N/A",
  "primary_expression": "当前景别可见的面部控制，不写抽象情绪词",
  "primary_body_action": "肩颈、手、重心、步伐、接触点或呼吸的第一身体反应",
  "eye_focus": "视线方向、停留对象、闪避/锁定/回收",
  "reaction_delay": "反应延迟、停顿或无延迟理由",
  "voice_or_breath_control": "无对白时写呼吸/吞咽/停顿；有对白时写句前停顿、音量、语速、气息、咬字或尾音控制",
  "viewer_empathy_anchor": "观众能立刻读懂的角色处境、软肋、顾虑、保护对象或被刺中的原因，不写效果词",
  "readable_image_moment": "承载共情锚点的单一可见画面证据，必须能在表演时间轴中找到",
  "suppression_or_release": "压住、泄露、爆开或回收的可见方式",
  "camera_pressure": "运镜、焦点、构图权重如何服务张力",
  "scene_pressure": "光源、遮挡、空间距离、环境声或道具如何加压",
  "end_residue": "落幅仍可见的姿态、呼吸、视线、距离、接触或道具残留"
}
```

- `performance_contract` 的表情、身体、视线、呼吸/语气、观众共情锚点、画面可读瞬间、压制/释放、运镜压力、场景压力和落幅残留必须落实进 `full_prompt` 对应段落；只写“紧张、震惊、自然反应、有张力、表情细腻、感染力强、观众共情”等抽象词不合格。
- 有可见物理角色时必须增加 `continuity_contract`：

```json
{
  "start_anchor": "本镜起始位置、姿态、视线、道具和光源状态",
  "end_anchor": "本镜终止位置、姿态、视线、道具和光源状态",
  "position_continuity": "人物和摄影机相对位置如何承接上一镜/进入下一镜",
  "eyeline_continuity": "视线对象和屏幕方向如何连续",
  "prop_state": "关键道具、伤势、破坏、接触状态",
  "lighting_continuity": "光源方向、色温、阴影关系",
  "next_carryover": "下一镜必须继承的画面残留"
}
```

- `end_anchor` 与 `next_carryover` 必须能在模型提示词中找到可见落幅，不得只存在于 QA 字段。
- 外套、手机、武器、门、领口、伤势等道具/状态发生转移时，必须在 `prop_state` 写清“从谁/哪里 → 到谁/哪里 → 结束状态”，并在 `next_carryover` 写下一镜继承状态；禁止外套、遮挡、伤势或道具复位。
- 有可见人物时必须增加 `reroll_control`：

```json
{
  "risk_level": "low | medium | high | reference_required",
  "identity_anchor": "角色身份、脸部气质、站姿或关系锚点；不得新增服装设计",
  "motion_anchor": "动作路径、接触点、幅度、速度或停顿锚点",
  "scene_anchor": "固定空间、光源、道具、遮挡或接触阴影锚点",
  "camera_anchor": "景别、焦距、机位、轴线、落幅和唯一运镜锚点",
  "risk_reason": "抽卡风险来自身份、动作、多人关系、口型、参考缺失还是复杂空间",
  "mitigation_steps": ["至少两条具体缓解策略"],
  "needs_reference": true
}
```

- T2V 人物镜不得把风险标为 `low`。T2V 的 `rising/peak` 人物镜必须标记 `needs_reference=true`，说明需要角色图、首帧、动作参考、九宫格关键帧或 R2V/I2V 降低抽卡；未提供资产时不得伪造路径，只能在风险控制中如实标注。
- 连续互动发生注意力交接时增加 `attention_handoff`；无交接时可省略：

```json
{
  "mode": "causal_handoff",
  "count": 1,
  "strategy": "rack_focus | single_reframe | actor_blocking",
  "from": "甲",
  "to": "乙",
  "trigger": "乙开始回答",
  "end_composition": "双人关系构图，乙保持主要视觉权重"
}
```

- `count` 只能为 1；`strategy` 三选一。`rack_focus` 要求物理机位固定，`single_reframe` 禁止再叠加拉焦/变焦，`actor_blocking` 要求摄影机固定或仅同向轻微收束。
- 打斗上下文必须增加 `fight_continuity`：

```json
{
  "mode": "continuous_take",
  "sequence_id": "FIGHT-01",
  "clip_id": "FIGHT-01-C01",
  "participants": ["甲", "乙"],
  "contact_beats": [
    {
      "time_range": "2.0-5.0秒",
      "attacker": "甲",
      "defender": "乙",
      "attack_path": "甲由画左横挥至画右",
      "contact_point": "乙左前臂格挡点",
      "force_direction": "乙受力向画面右后方",
      "result": "刀停在乙左肩外侧，乙重心落到右后脚"
    }
  ],
  "start_lock": {
    "positions": "甲画左、乙画右，相距1.2米",
    "stance_weight": "甲右脚前；乙重心居中",
    "weapon_prop_state": "甲右手持刀；乙空手",
    "injury_damage_state": "双方无新增伤势，场景未破坏",
    "screen_direction": "甲由画左攻向画右",
    "axis_side": "摄影机位于人物连线南侧"
  },
  "end_lock": {
    "positions": "甲画中左、乙画右后，相距0.8米",
    "stance_weight": "甲重心前压；乙重心落到右后脚",
    "weapon_prop_state": "刀停在乙左肩外侧；乙左臂格挡",
    "injury_damage_state": "双方无新增伤势，场景未破坏",
    "screen_direction": "动作惯性继续指向画右",
    "axis_side": "摄影机仍位于人物连线南侧"
  }
}
```

- 同一 `sequence_id` 的下一生成片段，其 `start_lock` 必须与上一片段 `end_lock` 完全相同。

## §C — Merged Prompt Package

```json
{
  "contract_version": "modec-v4",
  "items": [],
  "shots": [],
  "merged_full_prompts": []
}
```

- `items` 与 `shots` 内容相同。
- `merged_full_prompts[]` 按 `shot_id` 聚合子镜 `full_prompt`；负面词独立聚合。
- 下游脚本优先读取 `shots`，兼容 `items`。
- v3 包由 `normalize_prompt_package.py` 确定性迁移；迁移后仍需 Composer/Editor 复核 QA 元数据。

## §D — Export Separation

Markdown 只导出可直接投喂和人工操作所需内容：

1. 模型提示词 `full_prompt`；
2. 独立负面提示词 `negative_prompt`；
3. 台词/OS/OV制作信息：引用、类型、人物、逐字原文、时间窗、发声时神态、身体状态、语气与口型同步。

XLSX/缓存保留 QA/导演元数据、`generation_control`、参考资产、表演合同、连续性合同和抽卡风险控制，供制作复核与二次生成使用。

不得把负面词、QA/导演元数据、生成控制或工程字段拼回 `full_prompt` 冒充一条“更完整”的模型提示词。

## §E — Encoding And File Rules

- JSON 使用 UTF-8 无 BOM；读取时用 `utf-8-sig` 防御 BOM。
- 禁止尾随逗号、单引号 JSON、中文结构键。
- batch 文件必须带批次后缀。
- 公共输出只由主 Agent 的合并/归一化脚本写入。
