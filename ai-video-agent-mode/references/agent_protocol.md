# Agent Protocol — 子Agent调度协议

## 子Agent类型

| 类型 | 技能 | 产出 | 并行 |
|------|------|------|------|
| 情绪分析 | emotion-analysis | emotion_output.json | 与2b/2c并行 |
| 场景分析 | frames-analysis | scene_output.json | 与2a/2c并行 |
| 镜头运镜 | camera-analysis | camera_output.json | 与2a/2b并行 |
| Prompt Composer | prompt-composer | prompt_package.json | 串行依赖本地整合 |
| Editor Pass 2 | editor-review | review/llm_gate_result.json | 串行依赖 Editor Pass 1 |

## 输出字段规范

所有子Agent输出统一使用 `items[]`。每个 item 必须包含 `shot_id` 和 `subshot_id`，主Agent和本地整合只按 `subshot_id` 对齐。

### emotion_output.json
`items[]`: shot_id, subshot_id, emotion_type, expression_level, gaze, micro_expression, body_tension, body_parts_focus, voice_tone, action_beat_start, action_beat_transition, action_beat_end, emotion_trigger_short, performance_note

### scene_output.json
`items[]`: shot_id, subshot_id, space_type, space_name, char_positions, char_wardrobes, bg_foreground, bg_midground, bg_background, light_type, light_temp, light_direction, light_hardness, mood_atmosphere, audio_* fields

### camera_output.json
`items[]`: shot_id, subshot_id, shot_size, camera_lens_mm, camera_relative_pos, camera_distance_steps, camera_height_relative, angle_str, camera_facing_desc, movement_type, movement_detail, movement_speed, axis_start, axis_end, char_entry, char_exit, end_state

### director_pass.json（由本地 qa_integration handler 产出）
`items[]` 按 subshot_id 合并以上字段，并生成 `merged_full_prompts[]`。

## 失败重派与超时

| 条件 | 处理方式 |
|------|---------|
| 超时 | 按阶段超时自动重派，最多 4 次 |
| 连续超时 3 次 | blocking，不自动带问题推进 |
| Agent 失活(>10min) | 触发 recover → 重派新Agent |
| 输出不存在 | 重派（与超时共用计数器） |
| 分析矛盾 | 通过 qa_integration 的 repair_notes 记录 |
| 质量门禁失败 | 增量重试：只发失败子镜头 + 当前仍失败的问题 |

### 增量重试规则

1. 验证失败时，标记通过的子镜头为 passed，不参与后续重试
2. send_back 只包含仍失败的子镜头
3. 修正消息只包含本轮仍失败的问题（已修正的不重复发送）
4. 重试次数用尽后 pipeline blocked，不自动降级


## 上下文溢出预防

| 策略 | 操作 |
|------|------|
| 分批处理 | 按阶段上限拆分为多个 `.cache/dispatch/*_batchNNN_packet.json`，通过 send_input 逐批处理 |
| 增量追加 | 每批结果追加到同一JSON数组，最后统一写入 |
| 重试刷新 | send_back 发现原 Agent 失活时，重新 spawn_agent 并附带 `.cache/handoff/*_handoff.json` 中的上下文摘要 |
| 轻量化输入 | 每批只传当前需要处理的 subshot 数据，不重复全量 shot_plan |
| 文件化记忆 | 每个子Agent输出后必须生成 handoff 摘要，禁止只依赖聊天上下文 |

## Handoff 记忆协议

每个子Agent完成一批输出后，必须确保主Agent可从输出生成或直接写入 `.cache/handoff/{role}_handoff.json`。handoff 是恢复上下文的轻量记忆，不替代正式 JSON 输出。

每个 subshot 的 handoff 至少包含：

```json
{
  "subshot_id": "S1-01-01",
  "summary": "本镜头最终选择摘要",
  "decision_basis": "为什么这样选表情/灯光/运镜/提示词",
  "continuity_anchors": "起幅、落幅、人物位置、视线、光源、轴线等连续性锚点",
  "open_questions": "仍需确认或下游注意的问题",
  "do_not_change": "台词、OV/OS、轴线、人物位置等不可改边界"
}
```

恢复规则：

1. 原子Agent失活或上下文丢失时，主Agent重新 spawn 新Agent，并把失败 subshot、qa_issues、对应 handoff 摘要一起发送。
2. 新Agent必须先读取 handoff，再修正当前失败点；不得重新自由发挥已通过镜头。
3. handoff 只保存决策摘要和连续性锚点，不保存大段完整提示词，避免污染和重复。
4. 若 handoff 与正式 JSON 冲突，以正式 JSON 为准，并在 repair_notes 中标记冲突。


## Agent ID 追踪与复用

每次 spawn_agent 返回的 agent_id 通过 agent_registry.py 记录到 .cache/agents.json，
后续用 send_input 在同一上下文中继续对话。

### 标准流程

1. 创建子Agent，记录ID:
   result = spawn_agent(agent_type="worker", items=[...])
   register(run_dir, "emotion_analysis", result.agent_id)

2. 后续复用（同一上下文）:
   agent_id = get_agent_id(run_dir, "emotion_analysis")
   send_input(target=agent_id, message="继续分析下一批镜头...")

3. 完成后标记:
   set_status(run_dir, "emotion_analysis", "completed")
   close_agent(agent_id)

4. Agent 失活恢复:
   收到 recover 动作后 → 重新 spawn_agent（旧agent_id视为失效）
   register(run_dir, role, new_agent_id)
   同时读取 `.cache/handoff/{role}_handoff.json`，把相关 subshot 摘要传给新Agent

### 注册表文件位置

.cache/agents.json:
{
  "emotion_analysis": {"agent_id": "xxx", "status": "active"},
  "scene_analysis": {"agent_id": "yyy", "status": "active"},
  "camera_movement": {"agent_id": "zzz", "status": "active"},
  "qa_integration": {"agent_id": null, "status": "pending"}
}

## 子Agent输出格式契约

所有子Agent输出的JSON必须遵守以下格式规范，否则QA/整合Agent拒绝读取。

### 格式总则
1. 所有文本字段必须是纯字符串，不得嵌套JSON对象/数组
2. 不得包含XYZ坐标或工程术语（vector/coordinate/axis_line）
3. 使用自然语言描述空间位置：左/右/前/后/上/下
4. items数组条目顺序必须与shot_plan的subshots顺序一致

（以下子Agent输出格式示例保持不变）
