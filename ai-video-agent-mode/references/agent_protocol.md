# Agent Protocol — 子Agent调度协议

## 子Agent类型

| 类型 | 技能 | 产出 | 并行 |
|------|------|------|------|
| 情绪分析 | emotion-analysis | emotion_output.json | 与2b/2c并行 |
| 场景分析 | frames-analysis | scene_output.json | 与2a/2c并行 |
| 镜头运镜 | camera-analysis | camera_output.json | 与2a/2b并行 |
| QA/整合 | content-review | director_pass.json | 串行依赖前3个 |

## 输出字段规范

### emotion_output.json 每项：
shot_id, subshot_id
emotion: {cause, expression_chain, micro_expression, psychology_flow, performance_anchor}
character_action (>=50), micro_actions (>=15)
performance_plan: {body_action, facial_expression, micro_actions, voice_performance, end_state}

### scene_output.json 每项：
shot_id, subshot_id
axis_space (>=30), composition, lighting (>=30), audio_design (>=20)

### camera_output.json 每项：
shot_id, subshot_id
shot_size, camera_position (>=20)
camera: {lens, angle, movement, axis, transition, virtual_camera}

### director_pass.json（由QA/整合Agent产出）
包含以上全部字段 + dialogue_audio + negative_risks + commercial_quality

## 失败重派
- 超时(>5min)或输出不存在 → 重派(最多2次)
- 分析矛盾 → 记录矛盾点，请求主Agent决策


## Agent ID 追踪与复用

每次 spawn_agent 返回的 agent_id 必须通过 agent_registry.py 记录，确保可在同一独立上下文中复呼。

### 标准流程

1. 创建子Agent，记录ID:
   result = spawn_agent(agent_type="worker", message="...")
   register(run_dir, "emotion_analysis", result.agent_id)

2. 后续复用（同一上下文）:
   agent_id = get_agent_id(run_dir, "emotion_analysis")
   send_input(target=agent_id, message="继续分析下一批镜头...")

3. 完成后标记:
   set_status(run_dir, "emotion_analysis", "completed")
   close_agent(agent_id)

### 关闭后恢复

close_agent(agent_id) 后可通过 resume_agent 恢复:
resume_agent(agent_id)
send_input(target=agent_id, message="新任务...")

### 注册表文件位置

.cache/agents.json:
{
  "emotion_analysis": {"agent_id": "xxx", "status": "active"},
  "scene_analysis": {"agent_id": "yyy", "status": "active"},
  "camera_movement": {"agent_id": "zzz", "status": "active"},
  "qa_integration": {"agent_id": null, "status": "pending"}
}

### 角色命名规范
- emotion_analysis, scene_analysis, camera_movement
- qa_integration, prompt_composer

## 子Agent输出格式契约

所有子Agent输出的JSON必须遵守以下格式规范，否则QA/整合Agent拒绝读取。

### 格式总则
1. 所有文本字段必须是纯字符串，不得嵌套JSON对象/数组
2. 不得包含XYZ坐标或工程术语（vector/coordinate/axis_line）
3. 使用自然语言描述空间位置：左/右/前/后/上/下
4. items数组条目顺序必须与shot_plan的subshots顺序一致

### emotion_output.json（Phase 2a）

{"items": [{"shot_id": "S1-01", "subshot_id": "S1-01-01", "emotion": {"cause": "string", "expression_chain": "string", "micro_expression": "string", "psychology_flow": "string", "performance_anchor": "string"}, "character_action": "string >=50字", "micro_actions": "string >=15字", "performance_plan": {"body_action": "string", "facial_expression": "string", "micro_actions": "string", "voice_performance": "string", "end_state": "string"}}]}

### scene_output.json（Phase 2b）

{"items": [{"shot_id": "S1-01", "subshot_id": "S1-01-01", "axis_space": "string >=30字", "composition": "string", "lighting": "string >=30字", "audio_design": "string >=20字"}]}

### camera_output.json（Phase 2c）

{"items": [{"shot_id": "S1-01", "subshot_id": "S1-01-01", "shot_size": "string", "camera_position": "string >=20字", "camera": {"lens": "string", "angle": "string", "movement": "string", "axis": "string", "transition": "string", "virtual_camera": "string"}}]}

### 污染检测规则

由 validator/contamination.py 在编排引擎中自动检查：

| 检测项 | 违规示例 | 处理 |
|--------|---------|------|
| XYZ坐标 | "X: 2.5, Y: 1.8" | 打回重做 |
| 工程术语 | "vector", "coordinate" | 打回重做 |
| JSON嵌入文本 | "{\"lens\": \"50mm\"}" | 打回重做 |
| 嵌套dict | camera.movement是对象而非字符串 | 打回重做 |
