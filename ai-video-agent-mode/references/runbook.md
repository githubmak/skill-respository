# Runbook — AI Video Agent Mode Pipeline

本文件定义完整管线操作流程。启动新项目前必须加载。

## Phase 0: 用户确认（每次启动必走）

启动管线前先向用户确认：

| 确认项 | 格式 |
|--------|------|
| 画布/画幅 | 选择: 9:16 / 16:9 / 1:1 |
| 视觉风格 | 用户输入文字 |
| 单条视频最大时长 | 选择: 5/8/10/15/18/20/25/30 秒 |
| 最终存放位置 | 用户输入目录路径 |

用户回复后写入 project_config.json，按 _run_{timestamp} 创建运行目录。

## 项目目录结构

`
{export_base}/
├── source.txt
├── project_config.json
├── _run_{timestamp}/
│   ├── .cache/
│   │   ├── orchestrator/shot_plan.json
│   │   ├── analysis/
│   │   │   ├── emotion_output.json      (Phase 2a)
│   │   │   ├── scene_output.json         (Phase 2b)
│   │   │   └── camera_output.json        (Phase 2c)
│   │   ├── director/director_pass.json   (Phase 3 整合)
│   │   ├── continuity/report.json
│   │   ├── composer/{sid}.prompt_package.json
│   │   ├── editor/merged.json
│   │   └── qa/report.json
│   └── export/
│       ├── prompt_package.xlsx
│       └── prompts/{sid}.md
`

## 管线执行顺序

### Phase 0: 用户确认
请求用户输入配置，写入 project_config.json，创建运行目录。

### Phase 1: Orchestration
主Agent读取源文本，拆分为 shot_plan.json。

### Phase 2a: 情绪分析 Agent（并行）
加载 emotion-analysis 技能。分析每镜情绪原因、表情链、微表情、心理流、表演锚点。
输出: .cache/analysis/emotion_output.json

### Phase 2b: 场景分析 Agent（并行）
加载 frames-analysis 技能。分析每镜空间分层、场景描述、灯光设计、色调风格。
输出: .cache/analysis/scene_output.json

### Phase 2c: 镜头运镜 Agent（并行）
加载 camera-analysis 技能。分析每镜景别、机位、运镜类型、速度、视角、轴线、转场。
输出: .cache/analysis/camera_output.json

### Phase 3: QA/整合 Agent
加载 content-review 技能。读取3个分析输出，审查一致性，整合为完整的 director_pass.json。
补全 dialogue_audio、negative_risks、commercial_quality等字段。

### Phase 4-9: 连续性检查 → 提示词合成 → 合并 → LLM评审 → 验证 → 导出

## 子Agent技能加载
每个分析类子Agent启动时用 spawn_agent 的 items 参数传入技能引用:
items=[{type: "skill", name: "emotion-analysis"}]
不可用时将 SKILL.md指令嵌入消息体。

## 铁律
1. 禁手动绕道
2. Phase 0/4/6/7/8/9 不可跳过
3. 每子镜头段提示词须含6要素
4. 时间戳目录，旧输出保留
