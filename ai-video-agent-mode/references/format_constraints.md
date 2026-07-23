# Format Constraints — Current Contract

本文件是 AI Video Agent Mode 的唯一权威数据契约。主 `SKILL.md`、Agent 指令、验证器、归一化与导出脚本必须服从本文件。

## §0 — Prompt-Only And Project Isolation

本管线只输出提示词和结构化制作元数据，不生成、读取、观看或评价图片/视频。任何“成片效果”判断只能写成提示词层面的预期与风险，不得声称已经完成视觉验收。

技能目录只保存 schema、算法、枚举、验证器和中性占位符。项目名、人物名、题材、服装、灯光、场景细节和剧情事实只允许出现在运行目录的 `project_config.json`、project bible、`source_ledger.json`、`scene_locks.json`、`dramatic_beat_ledger.json`、`shot_plan.json` 与 `prompt_package.json`。示例只能使用 `角色A/角色B/场景A/关键道具` 等中性占位符。

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
    "detail_leak": "由当前景别可见的身体细部或已确认关键道具开始的泄露",
    "body_follow_through": "肩背、重心、步伐或接触关系如何承接",
    "voice_delivery": "台词/OS/OV的语气，或无台词时的呼吸落点",
    "end_residue": "下一节拍仍可见的状态"
  },
  "expectation_anchor": {
    "applicable": false,
    "semantic_mode": "literal_agent | figurative_personification | need_or_lack | symbolic_association | none",
    "anchor_type": "none | object | person_action | event | space | custom_visible",
    "anchor": "无则N/A；有则写原文可见的信、门、屏幕、对方动作或空间位置",
    "expecting_subject": "字面等待者、拟人意象或需求主体；无则N/A",
    "source_interpretation": "说明为何按字面、拟人、缺失/需求或象征处理；不能只靠类型枚举",
    "progress_event": "锚点本镜是否发生可见进展；无则N/A",
    "detail_cut_eligibility": "hold | eligible_on_progress | not_applicable"
  }
}
```

- `expression_level` 只允许 `micro / visible / strong`。
- `performance_role` 只允许 `primary / supporting / background`。
- 有人物镜头只能有一个 primary；最多一个 supporting focus，其他角色归 background。
- background 不强制独立微反应，可使用群体连续状态。
- “有意不反应”允许，但必须写明触发原因与可见终态。
- `performance_chain` 是所有后续镜头决策的共同输入。每项只写当前景别可见的一个主证据；道具未由剧本、配置或前镜确认时不得伪造为情绪泄露载体。
- Emotion Agent 只在等待、观察、担心或期待会影响本镜焦点、切镜或连续性时登记 `expectation_anchor`。先判断语义模式而不是套枚举：`literal_agent` 为字面人物的可拍期待；`figurative_personification` 为“花等归人”一类借物拟人，默认改为环境意象，除非源文明确授权拟人演出；`need_or_lack` 为“渴者等水”一类需求/匮乏，锚点必须是实际可见的水源、容器或抵达事件；`symbolic_association` 是不承担实体因果的意象联想。只有源文可见对象、人物动作、事件、空间位置或 `custom_visible` 状态可作为锚点；纯修辞或不可见愿望不得强建字段。`detail_cut_eligibility=eligible_on_progress` 仅表示锚点发生可见进展时允许 Director 选择一次切镜，不等于必须切镜；没有候选时可省略整个字段。

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
- Scene Item 是项目内光源类型、方向、软硬和色温事实的唯一权威。Camera/Director/Composer 只能逐字引用或压缩表达，不得重新发明光源事实。
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
  "viewpoint": "observer | participant | authority | vulnerable | objective",
  "visual_hierarchy": "主体、支持层与背景层的画面权重",
  "entry_strategy": "none | enter_frame | camera_follow | occlusion_reveal | reaction_first",
  "reveal_strategy": "direct | progressive | delayed | reaction_then_subject",
  "focus_strategy": "single_plane | deep_focus | rack_focus | single_reframe | actor_blocking",
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
  "editorial_mode": "continuous_take | shot_group",
  "camera_beat_map": [
    {
      "trigger": "表演链中的具体重音",
      "visual_priority": "当前主要人物/道具/关系",
      "camera_response": "hold | push_in | reframe | cut_reaction | cut_detail | follow",
      "time_range": "1.2-2.0秒",
      "focus_owner": "承担当前画面注意力的人物名；道具细节写object；不得在同一T2V任务中A→B→A",
      "focus_subject": "承担本节拍的人物、手部或道具",
      "framing": "中近景 | 特写 | 双人中景等落幅景别与构图",
      "axis_relation": "相对既有轴线的同侧/反打关系与左右位置",
      "transition_type": "hold | motivated_cut | hard_cut | motivated_reframe | continuous_move",
      "carryover": "切换后必须保留的人物、道具、轴线或光源状态"
    }
  ],
  "scene_anchor_usage": {
    "position_anchor": "引用 Scene Lock 的具体站位或无人物构图锚点",
    "light_anchor": "引用 Scene Lock 的光源方向与色温",
    "prop_anchor": "引用 Scene Lock 的道具状态",
    "carryover_anchor": "引用前一主镜的终态与当前主镜起态"
  },
  "sequence_context": {
    "sequence_id": "仅连续拆分时填写",
    "segment_index": 1,
    "segment_count": 1,
    "entry_carryover": "本段开头继承的状态",
    "exit_carryover": "本段结束交给下一段的状态"
  },
  "expectation_anchor_plan": {
    "applicable": false,
    "semantic_mode": "literal_agent | figurative_personification | need_or_lack | symbolic_association | none",
    "anchor_type": "none | object | person_action | event | space | custom_visible",
    "anchor": "来自 Emotion/source ledger 的期待锚点；无则N/A",
    "expecting_subject": "字面人物、需求主体或拟人意象；无则N/A",
    "source_interpretation": "字面/拟人/需求/象征的判别依据；无则N/A",
    "progress_event": "本镜可见进展；无则N/A",
    "camera_decision": "hold_same_framing | detail_cut_on_progress | reframe_on_progress | not_applicable",
    "return_target": "细节/重构后必须回到的期待者；无则N/A",
    "end_carryover": "锚点未兑现时必须保留的可见状态；无则N/A"
  }
}
```

- `shot_size`：大特写、特写、中近景、中景、全景、大远景。
- `movement_type`：固定、推、拉、摇、移、跟、升、降、俯、仰、环绕、甩、变焦、旋转、手持、穿梭。
- `continuous_take` 每子镜只能有一个主要 `movement_type`；复合移动必须是同一方向的连续轨迹。`movement_detail` 必须说明固定机位是否允许极慢推近，并排除未授权的摇移、跟拍、拉焦或变焦；这只锁定摄影机，不得抹掉 `visual_progression` 中已确认的人物、道具、视线或关系变化。`shot_group` 使用 1–3 项 `camera_beat_map`，每项必须由 `performance_chain` 的表情、细部/道具泄露、身体承接或语气落点触发；每项明确发生时间、`focus_owner`、视觉主体、落幅景别、轴线关系、转场类型与状态承接。允许一次 `A→B` 的自然反打/切特写/移镜；同一即梦任务禁止 `A→B→A` 或第二次人物交接，必须拆为下一 T2V 任务并交后期硬切。
- `hard_cut` 只用于 `shot_group`，每个即梦任务最多一次，必须由具体表演重音触发并写明准确时间点；它表示无淡入淡出、无黑场、无特效过渡的瞬时硬切。切后必须重新写明景别、实焦主体、屏幕左右、轴线关系和可见承接，禁止只写“明确剪切”。若需要回切到切前人物，不得在本条继续写第二次硬切；以当前落幅作为剪辑接点，在下一条 T2V 的起幅继承状态。
- 有前中后景人物关系时，`composition` 或 `camera_beat_map.framing` 必须写清前景为实焦、轻度虚焦或强焦外，中景/背景哪个人物为实焦，焦点是否稳定；焦外人物用空间距离、景深和“不出现可辨认五官/不抢焦点”约束，不得以不合理压暗人物亮度替代景深控制。
- 仅当一个连续剧情动作、长台词或连续关系判断必须拆成多个子镜时，填写 `sequence_context`。各段继承上一段的姿态、道具、声音边界和情绪残留；不得每段从中性站姿重新起演。
- 注意力交接只能选择一种主策略：固定双人构图内一次拉焦、一次单向重构图、或演员走位改变画面权重而机位固定。单向重构图允许一次摇、轨道横移或跟随人物走位的同向轨迹；必须写清跟随对象、起止构图与落幅，不得叠加拉焦或变焦。
- 重要人物出场先由 `narrative_weight` 决定是否需要视觉标点。high/critical 出场从遮挡揭示、低机位比例、前景反应、单向跟随、光线揭示、停步落幅或一次拉焦中选择 1–2 项；不得为了“重要”堆叠所有手段。
- 相邻镜头允许相同景别；不为“景别梯度”强制变化。
- 焦距是剧情启发式。情绪镜不强制 85mm；镜头必须同时满足空间关系、人物数量和面部可见性。
- 人物朝向剧情对象。除非原文明确自拍视频、直播、对观众说话或看镜头内设备，不得直视镜头。
- Master Production 必须消费 packet 中的 Scene Lock，并在三份合同中写明站位、光线、道具与承接。不得用抽象“延续场景”代替可核验锚点。
- Director 必须先消费 `expectation_anchor` 的语义判别再决定景别：字面主体可围绕其可见期待与进展组织；拟人/象征仅可作为环境意象或主观联想，不能被误拍成实体角色行动；需求/缺失不得把尚未出现的满足物拍成已在场。锚点静止或当前构图已读清进展与反应时选 `hold_same_framing`；只有 `progress_event` 发生且局部信息无法在当前景别读清时选 `detail_cut_on_progress`；切到锚点后 `return_target` 必须回到字面人物期待者，或在环境意象模式回到叙事主体/保持环境构图。禁止因为“有信/手机/门”本身自动插入特写。

## §B — Phase 6 Composer Batch Output

### B0. 即梦投喂视图与注意力预算

`full_prompt` 是可验证的规范正文，保留 B2 的五段标签；Phase 10 必须从它派生一份无标签的“即梦直接投喂提示词”。后者是用户复制进即梦的唯一推荐文本，严格保持五段内容原有顺序、时间窗、原文台词和声音边界，只删除栏目名，不新增第二份提示词事实。审阅性空话必须由 Composer 和 Editor Pass 2 在规范正文阶段删除，而不是在导出时进行不可靠的语义改写。

每个子镜的注意力预算固定为：一个实焦主体、一个主动作或状态变化、一个可读表演证据、一个落幅承接。优先语序为“主体与屏幕位置 → 触发动作 → 当前景别可见的表情/身体 → 声音或口型 → 必要稳定约束”。同主镜已锁定的画幅、风格、服装、光源、空间结构和通用禁令不得在每段复述；只有发生变化或影响本段执行时才再出现。

禁止保留不产生可见结果的导演话术，例如“建立空间”“体现关系”“提升质感”“增强感染力”“保证质量”“整体层次分明”。以可见动作、焦点、景深、光线、声音或终态替代。字数软区间用于诊断而非填充；实际时长只由连续对白、互动、动作或揭示的可见节拍证明。

人物镜的情感传递采用单一共情锚点：角色此刻在护住、害怕、忍住、失去或被刺中的一件具体事，并用一个当前景别可见的证据承载。表演顺序固定为“压住的起态 → 触发时点 → 身体先泄露 → 面部/视线跟上 → 声音落点 → 不复位残留”；一个人物在一个时间段至多一个主情绪转折，支持角色至多一次因果反应，背景不分配独立情绪任务。

每个时间段的画面层级固定为三层以内：实焦主体为第一层；前景肩线、手部、已确认道具或遮挡为可选第二层；空间和低幅背景为第三层。光线只服务实焦主体与一个真实接触点。不得为“电影感”同时堆叠多色轮廓光、雾气、反射、景深跳变和复杂运镜。

下一时间段或下一镜必须从上一段的可见落幅状态起演，继承姿态、视线、道具接触、重心、屏幕左右、焦点关系与同源光；只有源文可见动作或已声明的硬切/走位可改变状态。人物名称相同不构成连续性证据。

### B1. 顶层与 shot 结构

`risk_tier`、`risk_reasons`、`batch_capacity` 与 `review_scope` 仅存在于 dispatch packet；Editor review window 对应使用 `review_tier`、`risk_reasons` 与 `review_scope`。它们只决定批大小与可读上下文，不是 Composer 输出字段，不得写入 `full_prompt`、`qa_metadata`、`negative_prompt` 或 `generation_control`。`light` 只代表可缩窄审查上下文，绝不代表免除 Agent 复审、三份合同、确定性验证或最终导出验证。

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
        "dramatic_design": {
          "shot_function": "establish | reveal | entrance | reaction | confrontation | transition | action | dialogue | object",
          "narrative_weight": "low | medium | high | critical",
          "information_gain": "本镜新增的唯一信息或关系变化",
          "reaction_ownership": "本镜拥有的反应人物；无则为空",
          "dramatic_beat_ids": ["B001"],
          "visual_punctuation": ["camera_follow", "stop_mark"]
        },
        "duration_design": {
          "duration_strategy": "pack_toward_limit",
          "justified_content_duration": 5.0,
          "utilization_ratio": 0.5,
          "duration_rationale": "simple_action | continuous_dialogue | continuous_interaction | continuous_action | sustained_reveal",
          "dramatic_beats": ["B001"]
        },
        "editorial_mode": "continuous_take | shot_group",
        "camera_beat_map": [],
        "sequence_context": {},
        "viewpoint": "objective",
        "visual_hierarchy": "",
        "entry_strategy": "none",
        "reveal_strategy": "direct",
        "focus_strategy": "single_plane",
        "temporal_transition_contract": {
          "enabled": false,
          "kind": "none | memory_flashback | story_event_transition",
          "source_trigger": "源文逐字触发依据；none时为空",
          "decision_reason": "候选未启用时的源文依据；启用时的选择依据",
          "time_range": "0.0-0.0秒；启用时必须为有效窗口",
          "effect": "启用时根据当前事件配置的唯一视觉效果",
          "effect_source_basis": "该效果如何来自当前源文事件",
          "from_state": "转场前锁定的时空/人物状态",
          "to_state": "转场后锁定的时空/人物状态",
          "audio_bridge": "与提示词逐字一致的声音桥",
          "lip_sync": false,
          "prompt_anchor": "与提示词逐字一致的单一视觉效果锚点",
          "fallback": "split_with_matched_cut"
        },
        "quality_contract": {
          "profile": "environment | object | action | dialogue | dramatic",
          "required_analysis": ["scene", "camera"],
          "required_evidence": ["该类型必须在成片提示词中可见的质量证据"]
        },
        "quality_evidence": {"每项required_evidence": {"section": "主体与空间锁定|主镜头连续规则|子镜头组|光照、声音与稳定约束", "fragment": "该段中逐字存在的可见证据"}},
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
          "visual_progression": "",
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
          ,"state_change": false,
          "state_transitions": []
        },
        "reroll_control": {
          "risk_level": "medium",
          "identity_anchor": "",
          "motion_anchor": "",
          "scene_anchor": "",
          "camera_anchor": "",
          "risk_reason": "",
          "mitigation_steps": [],
          "manual_first_pass_check": false
        },
        "listener_reaction_plan": {
          "speaker": "角色A",
          "listener": "角色B",
          "trigger": "角色A说到关键事实后的0.2秒",
          "time_range": "1.4-2.2秒",
          "visual_evidence": "角色B先把视线从角色A嘴角移到其眼睛，拇指在已确认的杯沿轻收一次",
          "motion_limit": "只允许一次低幅手指收紧，不起身、不转向抢画面",
          "lip_sync": false,
          "end_residue": "角色B口型闭合，手仍停在杯沿，视线留在角色A方向"
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
            "breath_pause_plan": "",
            "lip_sync": true
          }
        ],
        "dialogue_refs": ["D1"]
      },
      "generation_control": {
        "mode": "t2v",
        "audio_enabled": true
      }
    }
  ]
}
```

- batch 顶层不能出现 `items` 或其他键。
- 每个 dispatch subshot 恰好输出一次，顺序一致。
- 输出必须以 dispatch 的 `composer_scaffold_path` 为骨架；`shot_id/subshot_id/duration/negative_prompt/qa_metadata.dialogue_refs/qa_metadata.dialogue_events[].ref|kind|speaker|text/generation_control` 是确定性锁定字段，Agent 不得改写。
- 相同场景的画幅、风格、服装、共享光源与空间锚点只从 `scene_lock_cache_path` 读取一次；各镜通过 `scene_lock_ref` 引用，不重复推导场景不变项。
- `mode` 必须固定为 `t2v`，且 `generation_control` 不得出现素材、路径或引用字段。
- `temporal_transition_contract` 是每镜必填合同。它只能消费派发骨架中的源文候选：没有候选时 `kind=none` 且不得启用；`memory_flashback` 只适用于明确回忆且存在可拍过去事实；`story_event_transition` 只适用于源文事件确实造成场景、意识、时空或人物状态切换。候选并不强制特效，Composer 可以在 `decision_reason` 说明为何正常切换更忠实。启用时必须先写 `effect_source_basis`，再根据当前事件配置一个且仅一个效果；它不得来自固定白名单、通用模板或无关风格。合同还必须有不超时的时间窗、前后状态、声音桥、`lip_sync=false`、逐字出现在 `full_prompt` 的 `prompt_anchor` 与降级方案；不得叠加效果、虚构回忆事实。所有已启用的合同一律 `high` 抽卡风险且 `manual_first_pass_check=true`。

### B2. full_prompt 五段

`full_prompt` 必须且只能包含：

1. `生成规格：...`
2. `主体与空间锁定：...`
3. `主镜头连续规则：...`
4. `子镜头组：...`
5. `光照、声音与稳定约束：...`
4. `光照、声音与稳定约束：...`

段间恰好一个空行。禁止旧版八字段、模板编号、自包含验证、负面词、QA 结论和工程字段。

#### 主体与空间锁定

- 以 `{canvas}画幅，{visual_style}` 开头。
- `主体与空间锁定` 不得出现图片、视频、素材槽位或外部引用标记。人物一致性只能依靠固定身份锚点、服装、屏幕左右、朝向、场景锚点和上一子镜终态。
- `{canvas}` 与 `{visual_style}` 只能来自当前项目配置或 scene lock cache；不得沿用任何示例的项目限定词。
- 只写本镜必须锁定的主体、服装、站位、朝向、场景接触和身份连续性。
- 场景不变项只写一次，不重复灯光和动作过程。
- 有人物时提供一项真实场景接触：脚底/椅面/桌沿/道具/接触阴影/前景遮挡/环境反射。
- 系统声、系统提示或悬浮文字只允许作为画外声、界面层或侧边安全区彩色悬浮文字出现；不得实体入画、遮挡人物脸部、压住口型或破坏主表演焦点。
- 既定室内/酒店等空间必须保持结构、入口方向、主要物件与屏幕左右关系稳定；“不穿越空间、不改变空间结构”只作为低优先级稳定约束，不能覆盖已声明的走位、硬切、重构图或跟随路径。

#### 主镜头连续规则

使用顺序：

```text
时长：5.0秒。景别：中近景。焦距：50mm。机位：……。轴线：……。主要运镜：固定，落幅时轻微收紧构图……。
```

- `continuous_take` 使用一种主要运镜、任一时刻一个注意力中心、一个落幅；必须写清固定机位的允许运动或唯一已授权运动，禁止未声明的摇移、跟拍、变焦或拉焦。同一互动链允许一次由台词/动作触发的 `A→B` 注意力交接。`shot_group` 可在同一剧情目标内由表演链重音带出自然景别变化、反打或移镜；每个内部节拍仍只有一个主体，并沿用同一人物、道具、轴线与光源状态。
- 禁止只写“聚焦甲/聚焦乙”或“保持虚化”；必须写可见构图权重、前后景谁实焦/谁轻度虚焦或焦外、焦点是否稳定、摄影机方向与最终双人或关系落幅。
- 稳定控制优先级固定为：本段戏剧主体与实焦 > 已声明运镜/切换 > 空间结构与屏幕左右连续 > 通用固定机位/轻微推近控制。不得让通用的“固定、微推、不摇移”否定已声明的硬切、重构图、跟随或焦点转移。
- 数值只保留 1–2 个决定性锚点；不堆 mm、度、速度和距离。
- `dramatic_goal` 留在 QA 元数据，不重复写入模型提示词。
- Camera 必须落实 `viewpoint/visual_hierarchy/entry_strategy/reveal_strategy/focus_strategy`。人物跟随属于合法单一运镜；采用跟随时，以起幅、路径和落幅锁定空间，不得同时声称固定机位或固定框景全程不变。

#### 子镜头组

- 使用 2–3 个连续小数秒时间段，从 `0.0` 覆盖到镜头总时长，无断档、重叠或倒置。
- 面向短视频生成平台时，段内语序优先为：景别可见主体 → 触发动作 → 表情控制 → 肢体承接 → 语气/呼吸/口型 → 必要动态稳定约束。该语序必须嵌入现有五段结构，不新增“动态约束”独立段落。
- 每段按 `可见触发 → 主角身体反应 → 对手必要反应 → 镜头落点` 写。
- 每段只保留一个实焦主体。若该段的画面证据是主角的眼神、手部或关键道具，则这些可成为同一近距离焦平面的实焦；若该段承担另一人物的揭示，则该人物为实焦，主角只能作为轻度虚焦的前景或背景空间锚点。背景人物以焦外、不出现可辨认五官、不抢焦点控制，禁止要求所有人物同时清晰。
- `shot_group` 的切换在对应时间段内写明转场类型与触发。使用硬切时，写“于 X.X 秒由〔具体视线/动作/台词〕触发无转场硬切”，随后立刻写切后景别、实焦主体、屏幕位置、轴线和承接状态；不得用“明确剪切”代替这些事实。
- 每个人物镜必须有一个观众可直接读懂的共情锚点和画面可读瞬间：先明确角色此刻被什么刺中、想护住什么、怕失去什么或正在忍住什么，再落成一个可见证据。共情锚点不能是“观众共情、感染力强、情绪到位”等结果词。
- 现代都市剧情人物镜默认表演克制：不用夸张瞪眼、扭曲表情或大幅肢体动作；以当前景别可见的眼神停留、呼吸变化、手部/关键道具力度、肩背姿态和重心微调承载情绪。原文明确要求夸张喜剧、惊吓或肢体爆发时，以原文事件为准。
- 画面可读瞬间只选 1 个主证据并贯穿时间轴，如手停住、视线避开、肩背收紧、呼吸断半拍、道具状态改变或空间距离被压缩；不得为了画面感堆叠过多表情/肢体细节。
- 先按原剧情选择 `neutral / latent / rising / peak / release` 张力意图；不得默认把每镜都做成高张力，也不得用增加动作数量替代张力设计。
- 触发发生在时间段内部时必须写明确时点；角色反应要区分直接感知触发与观察他人后再反应，禁止无依据的多人同步启动。
- 突发、短促、立即类动作应在所属时间段前部完成接触点、转折点或制动点，并为受力、回稳和终态残留保留时间；原文明确缓慢动作时除外。
- 接触、阻挡、受力或截停的结果必须匹配接触点、支撑关系、受力方向和重心。杠杆不足时写提示、警告或角色主动收住，不得写成不可信的强制位移。
- 中断动作必须分别写清被取消的主运动与仍允许的残余运动；后段相似方向动作必须以幅度、身体部位或目的区分，禁止完整重做已被截停的动作。
- 长停顿占镜头超过约三分之一或持续超过 1.5 秒时，只保留 1–2 个景别可见的生命迹象，或给出有意静止的剧情理由；不得用密集微动作破坏静止状态。
- 3–6 秒镜头：主动作≤1、情绪转折≤1、对手反应≤1、主要运镜≤1。
- 6–10 秒镜头：主动作≤2、情绪转折≤1、对手反应总数≤2、主要运镜≤1。
- 10–15 秒连续互动：允许 2–3 个因果相接的内部节拍、多个短台词轮次和一次因果注意力交接。`continuous_take` 保持一条摄影机轨迹；`shot_group` 可由表演重音带出 1–3 个自然景别/视角变化。两者都只能服务一个整体戏剧目标；第二个独立戏剧目标、无触发的反复抢焦或无关动作链必须拆镜。
- 时长服务于可见事件，不服务于氛围填充。单一微表情、一次视线变化、静态压场、群体凝视或落幅余韵默认不得超过 `project_config.max_static_shot_duration`（默认 6 秒）。落幅残留是承接下一镜的终态，不是额外延时。
- Phase 1 先尝试把同一戏剧目标内因果连续的节拍打包到接近平台上限，再以内容所需时长落定，不强行补满。每镜记录 `duration_strategy=pack_toward_limit`、`justified_content_duration`、`utilization_ratio`、`duration_rationale` 与 `dramatic_beats[]`。超过静态上限时，rationale 仅允许 `continuous_dialogue / continuous_interaction / continuous_action / sustained_reveal`；6–10 秒至少 2 个可见因果节拍，10–15 秒至少 3 个。不得以“压迫感、静默、停顿、余韵、保持状态”作为理由。
- 有意静止仍可用于屏息、庄重或对峙，但必须在短镜内完成；若静止本身构成持续事件，`dramatic_beats[]` 必须写出期间发生的可见信息变化，而非重复“人物保持不动”。
- 打斗镜优先作为一个不切镜的连续动作链：≤6 秒最多 1 个接触节拍、6–10 秒最多 2 个、10–15 秒最多 3 个；所有节拍必须因果相接并共享同一主要摄影机轨迹。攻防双方之间的因果注意力传递不算独立换焦；换轴、切到独立主编舞链/戏剧焦点、换场景、第二条无关动作链或超过 15 秒才拆片段。
- 打斗镜按平台稳定性控制速度、幅度、接触节拍和镜头抖动；当动作复杂度超过单条可稳定生成范围时，必须在 `fight_continuity` 中锁定连续片段，或拆成下一生成片段。
- background 只写群体低幅连续状态，不逐人分配动作。
- 每个台词/OS/OV事件按 `qa_metadata.dialogue_events` 执行；`ref/kind/speaker/text` 不得改写，语气控制不得通过改标点或增删文字污染原文。
- `audio_enabled=true` 时，原文必须逐字且只出现一次，并且只放在子镜头组。统一格式为 `{人物}（台词/OS/OV）：“{原文}”`，同一事件紧接人物神态、身体状态、说话语气和口型边界。
- `audio_enabled=false` 时，原文不得进入 `full_prompt`；子镜头组仍写可见人物的神态、身体状态及台词口型边界，原文和配音控制保留在 `qa_metadata.dialogue_events` 与制作表。
- 可见台词人物按原文同步口型；可见OS/OV人物口型闭合。画外或非实体发声者不驱动任何可见角色口型；非说话 focus 角色口型闭合，背景统一无同步口型。
- 终态必须是画面可见状态并能承接下一镜，同时保留上一事件造成的姿态、接触、重心、视线、呼吸、道具或空间距离残留；除非剧情明确复位，不得落成“无事发生”。需要戏剧停顿时，最后短时间窗保持镜头稳定、人物动作自然减缓并留下 1–2 个可见生命迹象；除非源文明确要求，禁止“画面定格/冻结”或人为慢动作，以免卡帧、拖影或肢体僵硬。

#### 光照、声音与稳定约束

- 光源方向、色温、软硬和人物/环境同源关系保持跨镜连续。
- 光线风格服从当前剧本和项目配置；不得把任何示例的光线、空间、节奏或色调作为默认光声方案。
- 未指定更强题材调性时，现代都市关系镜保持精致都市剧情感与克制的社交压迫或尴尬感；不得自动渲染为惊悚、强暧昧或夸张喜剧。只有源文明确建立对应关系和强度时才提高其权重。
- `audio_enabled=true`：写关键环境声、声音同步关系及必要声部层级；原始台词/OV/OS已在子镜头组逐字出现，本段不得重复。原文台词、OS 或 OV 为前景主声，关键动作声为次级同步声，环境声为低频底噪；音效最多保留 1–2 个叙事事件，且不得覆盖原文人声或凭空新增人声。
- `audio_enabled=false`：只写光照；台词与音频计划留在 `qa_metadata`/制作表，不占模型提示词。

### B3. 表演角色优先级

- `primary`：唯一主表演者，获得完整起始—触发—泄露—终态链。
- `supporting`：只对主事件做一次因果反应，不发起竞争动作。
- `background`：保持空间连续、低幅活动、无同步口型，不逐人写微表情。
- 每个可见角色必须且只能被分配到一个层级。

### B4. 动作预算与长度

- 长度是信息密度诊断，不是审美配额：环境/物件 200–700 字；3–6 秒简单动作 300–900 字；3–6 秒对白/情绪 400–1100 字；6–10 秒表演 500–1400 字；重要出场/关系建立 600–1600 字；10–15 秒互动 800–2000 字；复杂连续动作 900–2200 字。
- 上述范围全部是 soft guidance。只有 `project_config.prompt_limits.hard_max_chars` 或平台适配配置明确给出硬上限时，超过该值才 blocking。
- 不因软区间溢出单独拆镜。拆镜理由只允许：多个戏剧目标、动作预算溢出、重复注意力交接、竞争运镜、不可兼容空间状态或平台硬上限溢出。
- 不能通过增加背景微动作、光学数字、重复状态或 QA 文案凑字数。
- `duration_design` 只属于 Phase 1 时长门禁和 QA，不得写入 `full_prompt`；其节拍必须能被 Composer 时间轴追溯。

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

### B6.1 自动空间分镜图导出

Phase 10 可从已验证的主镜和连续性合同自动派生“人物站位空间分镜图”提示词。它们不属于 `full_prompt`、`negative_prompt` 或 `generation_control`，不改变 T2V 契约，也不要求 T2V 使用图片参考。只有当人物/道具状态变化、服装/道具交接、多人左右站位、可见走位、硬切/重构图/跟拍或多层景深关系提高位置穿帮风险时导出。

每个被选中的主镜导出：一条垂直正交俯视空间调度图提示词、一条横向人物站位姿态分镜图提示词和一条分镜图负面词。两条提示词必须复用本镜可见的场景锚点、人物、左右、朝向、道具和摄影机关系；信息缺失可标为合理空间推断，但不得新增剧情人物、道具或动作。Markdown 将它们置于对应主镜的即梦操作卡后，供用户结合场景图和人物图生成辅助图。

### B7. qa_metadata

- 只用于制作和验证，不投喂视频模型。
- `dramatic_goal` 必须是本镜具体目标。
- `dramatic_design` 必须包含镜头功能、叙事权重、唯一信息增量、反应归属、`dramatic_beat_ids` 与 `visual_punctuation`。每个 beat ID 必须在 `dramatic_beat_ledger.json` 中唯一归属于当前子镜。high/critical 重要出场的 `visual_punctuation` 必须从 `occlusion_reveal / low_angle_scale / foreground_reaction / camera_follow / light_reveal / stop_mark / rack_focus` 中选 1–2 项；其他镜可为空。
- `duration_design` 必须逐字继承 Phase 1 的时长策略和依据；低利用率本身不是错误，缺少内容依据或用静态余韵填充才是错误。
- `editorial_mode` 必须从 Director 逐字继承；它决定本镜执行一条连续轨迹，或一组由表演重音触发的镜头响应。
- `camera_beat_map` 与 `sequence_context` 也必须从 Director 逐字继承。前者不得由 Composer 重新发明；后者要求连续拆分从上一段状态起演而非重置。
- `shot_group` 的每个镜头节拍都写明 `trigger/time_range/focus_subject/framing/axis_relation/transition_type/carryover`；Composer 将这些信息落到主镜头连续规则与子镜头组，不增加未声明的切换。
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
  "breath_pause_plan": "句前0.2秒吸气；必要时在原文分句/转折后停0.2秒；句末0.3秒收气。短句可写无中段气口，但起句与句末不可省略",
  "lip_sync": true
}
```

- `ref/kind/speaker/text` 是确定性锁定字段；Composer 不得改变顺序、人物、类型、文字或标点。
- `time_range` 必须位于本镜时长内。`facial_state/body_state/delivery` 必须非空；可见人物的神态与身体状态必须落实到子镜头组。
- `speaker_visibility=visible` 时人物必须在本镜可见；`offscreen/nonphysical` 时 `facial_state/body_state` 明确写 `N/A` 及不可见原因，不伪造表演。
- 可见台词人物 `lip_sync=true`；OS、OV、画外人物和非实体声音一律 `lip_sync=false`。
- `delivery` 至少覆盖语速、音量/气息、停顿/咬字/尾音中的两项；只写“紧张地、悲伤地、愤怒地、自然地”不合格。`breath_pause_plan` 必须有带秒数的句前气口和句末收气；含多个分句、转折或情绪折点的原文还必须写中段气口，短句可明确无中段气口。气口为自然呼吸与情绪节奏服务，不能机械地逐标点等长停顿。
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
- `performance_causality` 是 QA/导演元数据，不得拼入 `full_prompt`；Composer 根据它把必要的可见结果落实到子镜头组，Editor Pass 2 复核语义真实性。
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
  "readable_image_moment": "承载共情锚点的单一可见画面证据，必须能在子镜头组中找到",
  "suppression_or_release": "压住、泄露、爆开或回收的可见方式",
  "camera_pressure": "运镜、焦点、构图权重如何服务张力",
  "scene_pressure": "光源、遮挡、空间距离、环境声或道具如何加压",
  "end_residue": "落幅仍可见的姿态、呼吸、视线、距离、接触或道具残留"
}
```

- `performance_contract` 的表情、身体、视线、呼吸/语气、观众共情锚点、画面可读瞬间、`visual_progression`、压制/释放、运镜压力、场景压力和落幅残留必须落实进 `full_prompt` 对应段落；只写“紧张、震惊、自然反应、有张力、表情细腻、感染力强、观众共情”等抽象词不合格。`visual_progression` 写起幅→可见变化→落幅，或在有意静止时写静止理由→低幅生命迹象→落幅；它不要求每镜切换景别或移动摄影机，但禁止用“固定机位/稳定”代替人物与画面的真实推进。
- `expectation_anchor` 是按需字段：仅当期待/等待会改变本镜焦点、切镜或下一镜连续性时增加。先写 `semantic_mode` 与 `source_interpretation`，以说明它是字面人物行为、借物拟人、需求/缺失还是象征意象；不得让登记类型替代语义判断。锚点可以是实体对象、人物动作、事件、空间位置或其他可见状态；无候选时省略该字段，不用填 `N/A`。有期待锚点时，必须在子镜头组落地锚点、进展事件、期待主体回反应和终态：

```json
{
  "applicable": true,
  "semantic_mode": "literal_agent",
  "anchor_type": "object",
  "anchor": "信纸",
  "expecting_subject": "角色A",
  "source_interpretation": "角色A正在看着角色B书写的信纸，属于字面人物的可见等待",
  "start_state": "角色A的视线停在角色B笔下的信纸上，信纸仍在书桌中央",
  "progress_event": "2.8秒笔尖停住后继续落下，信纸新增一行可见笔迹",
  "detail_cut_rule": "仅由笔尖停顿触发一次信纸特写；对象静止时不切镜",
  "return_reaction": "细节镜后切回角色A，角色A手指收紧且视线仍挂在信纸方向",
  "end_state": "信纸仍未递出，角色A保持前倾等待姿态"
}
```

- 锚点细节镜或关系重构只能由 `progress_event` 触发，不得因锚点静止或为了增加景别变化而切镜。若 `detail_cut_rule` 使用特写，后续时间窗必须回到 `expecting_character` 的可见反应；锚点未兑现时，`end_state`、`continuity_contract.prop_state` 与 `next_carryover` 必须共同保留未完成状态。当前构图已能读清锚点进展与反应时，`detail_cut_rule` 可明确写“不切景别，保持同镜头”。
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
- 若人物位置、视线或可移动道具发生变化，必须设置 `state_change=true`，并在 `state_transitions[]` 为每项变化写 `subject/from_state/to_state/cause/time_range`。`cause` 必须是本镜可见动作、接触、人物走位或明确转场；否则阻断，禁止无解释换位或道具复位。
- 外套、手机、武器、门、领口、伤势等道具/状态发生转移时，必须在 `prop_state` 写清“从谁/哪里 → 到谁/哪里 → 结束状态”，并在 `next_carryover` 写下一镜继承状态；禁止外套、遮挡、伤势或道具复位。
- 有可见人物时必须增加 `reroll_control`：

```json
{
  "risk_level": "low | medium | high",
  "identity_anchor": "角色身份、脸部气质、站姿或关系锚点；不得新增服装设计",
  "motion_anchor": "动作路径、接触点、幅度、速度或停顿锚点",
  "scene_anchor": "固定空间、光源、道具、遮挡或接触阴影锚点",
  "camera_anchor": "景别、焦距、机位、轴线、落幅和唯一运镜锚点",
  "risk_reason": "抽卡风险来自身份、动作、多人关系、口型、参考缺失还是复杂空间",
  "mitigation_steps": ["至少两条具体缓解策略"],
  "manual_first_pass_check": true
}
```

- T2V 人物镜不得把风险标为 `low`。T2V 的 `rising/peak` 人物镜必须标记 `manual_first_pass_check=true`，并用身份、服装、屏幕左右、场景、动作或镜头降负载等策略降低抽卡；不得要求或伪造外部素材。
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
- 当可见台词人物与可见 supporting 人物同框时，必须增加 `listener_reaction_plan`。它只指定一名倾听者、一条由说话/动作触发的低幅反应和闭口落幅：`speaker/listener/trigger/time_range/visual_evidence/motion_limit/lip_sync/end_residue` 均必填。`lip_sync=false`；`visual_evidence`、`motion_limit`、`end_residue` 必须逐字落在子镜头组，且子镜头组明确倾听者口型闭合。听者最多一次眼神、呼吸、手指、肩背、重心或已确认道具反应；不得新增台词、大幅走位、同步口型或第二条情绪爆发。剧情要求僵住时，`motion_limit` 说明原因并保留 1–2 个生命迹象。打斗、追逐、推搡、控制与救援镜不填本字段，改由 `fight_continuity` 写双方“动作→受力/判断→结果”的连续反应链；非主攻方必须格挡、闪避、回稳、主动收住或准备反制，不能作为静止倾听者。
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
  "contract_version": "jimeng-t2v-v1",
  "shots": []
}
```

- `shots` 是提示词包唯一权威数组。禁止在同一包中复制为 `items` 或派生 `merged_full_prompts`。
- 主镜头聚合只允许在导出时临时计算，不得持久化第二份提示词事实。
- `normalize_prompt_package.py` 只规范当前契约，不负责旧版迁移。

## §D — Export Separation

### D0. 九宫格剧情图技能接入

当 `storyboard_grid.enabled=true`，Phase 8.5 必须调用 `nine-panel-video-storyboard`，而不是用本技能自由改写九格剧情。多事件链选 `nine-panel-ai-video-storyboard`，单一连续镜选 `single-shot-keyframe-grid`。输入只能来自已通过 Editor Pass 2 的 T2V 主镜、三份合同、台词事件和空间分镜图；不得改变已锁定剧情事实。

返回 JSON 必须包含严格有序的 `01` 至 `09` 九格。随后使用 `scripts/adapt_nine_panel_storyboard.py` 适配成 `.cache/grid_storyboard/packages.json`；适配器会拒绝少于/多于九格、面板序号错误、缺少摄影、可见画面、动作控制或叙事标签的结果。导出器将九宫格总图提示词、负面词与九格节拍加入 Markdown/XLSX，不把它们混入 T2V 的 `full_prompt`。

Markdown 只导出可直接投喂和人工操作所需内容：

1. 模型提示词 `full_prompt`；
2. 独立负面提示词 `negative_prompt`；
3. 台词/OS/OV制作信息：引用、类型、人物、逐字原文、时间窗、发声时神态、身体状态、语气与口型同步。

XLSX/缓存保留 QA/导演元数据、`generation_control`、表演合同、连续性合同和抽卡风险控制，供制作复核与二次生成使用。

不得把负面词、QA/导演元数据、生成控制或工程字段拼回 `full_prompt` 冒充一条“更完整”的模型提示词。

## §E — Encoding And File Rules

- JSON 使用 UTF-8 无 BOM；读取时用 `utf-8-sig` 防御 BOM。
- 禁止尾随逗号、单引号 JSON、中文结构键。
- batch 文件必须带批次后缀。
- 公共输出只由主 Agent 的合并/归一化脚本写入。
