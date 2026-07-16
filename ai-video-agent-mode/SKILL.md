---
name: ai-video-agent-mode
description: >
  Use this skill when the user asks for a reusable/system-level 4-agent workflow
  for converting scripts, storyboards, scenes, or docx/txt/md source material
  into aligned AI video prompt packages. Triggers include agent模式, 4-agent,
  多agent, 剧本转AI视频提示词, 关键帧提示词, 静态分镜提示词, 动态视频提示词,
  完整提示词, 九宫格剧情分镜图, 四宫格关键帧展开, and requests that require
  canvas/style/duration/export-dir gates, one-to-one subshot/keyframe/motion
  correspondence, main-shot merged full prompts, and staged QA.
---

# AI Video Agent Mode

Use this skill as the top-level coordinator for commercial AI-video prompt production.

## 管线执行阶段（严格顺序,不可跳过）

### Phase 0: 用户确认（每次启动必走）
启动管线前先向用户确认以下 4 项，用户回复后填入 `project_config.json`：

| 确认项 | 格式 | 示例 |
|--------|------|------|
| 画布/画幅 | 选择: 9:16 / 16:9 / 1:1 | `16:9` |
| 视觉风格 | 用户输入文字 | `现代都市/冷幽默` |
| 单条视频最大时长 | 选择: 5/8/10/15/18/20/25/30 秒 | `15` |
| 最终存放位置 | 用户输入目录路径 | `C:\path\to\export` |

若用户重复输入（修改上面任何一项），用 `_run_{timestamp}` 形式创建新文件夹，将本次输出放进去。
旧输出保留不删除，防止覆盖。

```
Phase 0:  用户确认                           → project_config.json
Phase 1:  Orchestrator (本地)               → shot_plan.json
Phase 2a: 情绪分析 子Agent ($emotion-analysis)  → emotion_output.json
Phase 2b: 场景分析 子Agent ($frames-analysis)   → scene_output.json
Phase 2c: 镜头运镜 子Agent ($camera-analysis)   → camera_output.json
Phase 3:  QA/整合 子Agent ($content-review)    → director_pass.json
Phase 4:  连续性检查 (不可跳过)               → continuity_check.py --live
Phase 5:  Prompt Composer (全走子Agent)       → prompt_package.json → 校验失败重派
Phase 6:  Editor Pass 1 (不可跳过)            → merge_prompts.py
Phase 7:  Editor Pass 2 LLM评审 (不可跳过)     → editor_pass2_prompt()
Phase 8:  最终验证 (不可跳过)                 → validate_prompt_package.py
Phase 9:  导出 (不可跳过)                    → export_workbook.py → Excel+Markdown
```

## 核心脚本

- scripts/pipeline_templates.py — 子Agent派发模板 + 字段类型校验 + 质量门槛
- scripts/template_prompt.py — 本地模板提示词生成
- scripts/continuity_check.py — 连续性检查
- scripts/export_workbook.py — Excel 8 sheet + Markdown 导出
- scripts/validator/ — 字段类型、质量校验
- scripts/export/markdown.py — Markdown 导出

## 完整提示词6要素

每个子镜头段必须包含: 景别、机位、运镜、可见人物、动作过程+灯光、台词/OS。

## 铁律

严禁主Agent手动创建/复制下游文件绕过上游阶段。数据不对回到产生阶段重派。

### 子Agent技能加载方式

启动分析类子Agent时，用 spawn_agent 的 items 参数传技能文件路径，不继承会话上下文：

```python
spawn_agent(
  agent_type="worker",
  items=[
    {"type": "skill", "name": "emotion-analysis", "path": "~/.codex/skills/emotion-analysis/SKILL.md"},
    {"type": "text", "text": "任务描述..."}
  ]
)
```

注意：
1. items 和 message 不能同时用，任务描述放在 items 中的 type="text" 项
2. type="skill" 必须带 path 字段指向对应 SKILL.md
3. items 数组顺序无影响，子Agent同时加载技能指令和任务描述

### Agent ID 追踪

每次 spawn_agent 返回的 agent_id 通过 agent_registry.py 记录到 .cache/agents.json，
后续用 send_input 在同一上下文中继续对话。
