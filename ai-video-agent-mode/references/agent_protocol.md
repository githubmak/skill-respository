# Agent Protocol — 子Agent通信与调度协议

Phase 2（Director）和 Phase 4（Prompt Composer）需要派发子Agent时加载。

## 子Agent调度规则

### 1. 创建子Agent线程

调用 `create_thread` 创建新的子Agent线程。每批 Director 子Agent 4-6 个，Composer 每批 1 镜。

```json
create_thread {
  "title": "Director — {shot_id}",
  "content": "[完整的系统提示词 + 镜头数据]"
}
```

### 2. 系统提示词结构

每个子Agent必须收到明确的角色定义和输入数据：

```
# 角色定义
你是 {role_name}，负责 {role_description}。

## 输入数据
{shot_plan 中该镜的完整数据}

## 输出要求
- 输出格式：JSON（写入指定路径）
- 必须包含的字段：{根据角色定义}
- 不得输出与要求无关的内容

## 质量门槛
- {quality_thresholds}
- 字段类型约束：{field_type_constraints}

## 输出路径
文件写入: {output_path}
```

### 3. 输出格式规范

#### Director Agent 输出格式
每镜输出为 director_packet.json，items 数组中每项必须含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| shot_id | str | 镜头编号 |
| subshot_id | str | 子镜头编号 |
| duration | float | 时长 |
| shot_size | str | 景别(中英文) |
| camera_position | str | 机位描述 |
| camera | dict | 镜头参数：lens/angle/movement/axis/transition/virtual_camera |
| axis_space | str | 轴线与空间描述 |
| composition | str | 构图描述 |
| character_action | str | 角色动作描述(>=50 chars) |
| action_beats | dict | start/transition/contact_or_peak/end_state |
| micro_actions | str | 微动作(>=15 chars) |
| emotion | dict | cause/expression_chain/micro_expression/psychology_flow/performance_anchor |
| dialogue_audio | dict | dialogue_refs/raw_text/dubbing_text/pause_plan/mouth_visibility/voice_performance/timing |
| lighting | str | 灯光描述(>=30 chars) |
| audio_design | str | 音效描述(>=20 chars) |
| negative_risks | list[str] | 风险列表 |
| commercial_quality | dict | camera_compatibility/continuity_axis/lighting_logic/performance_specificity/action_boundary/shot_size_facing/repair_notes |
| performance_plan | dict | body_action/facial_expression/micro_actions/voice_performance/end_state |

#### Prompt Composer Agent 输出格式
每镜输出为 prompt_package.json，items 数组中每项必须含：

| 字段 | 类型 | 说明 |
|------|------|------|
| shot_id | str | 镜头编号 |
| subshot_id | str | 子镜头编号 |
| duration | float | 时长 |
| shot_size | str | 景别 |
| camera_position | str | 机位 |
| camera | str | 运镜描述 |
| axis_space | str | 空间描述(>=30 chars) |
| character_action | str | 动作描述(>=50 chars) |
| lighting | str | 灯光(>=30 chars) |
| audio_design | str | 音效(>=20 chars) |
| full_prompt | str | 完整提示词(>=500 chars) |

### 4. 失败重派协议

```
成功: 子Agent退出码0 + 输出文件存在 + 字段校验通过 + 质量检查通过
     → 标记完成，继续下一批

失败: 子Agent退出码非0 / 输出文件不存在 / 校验失败
     → 记录失败原因
     → 重新创建子Agent线程（最多重试2次）
     → 第3次失败则标记为BLOCKED，通知主Agent
```

### 5. 并行合并

Director 子Agent 的 items 数组按 shot_id 分组，同 shot_id 的 items 合并为一个 director_pass.json。

Prompt Composer 子Agent 的输出直接存入 `.cache/composer/`，由 Editor Pass 1 汇总。 
