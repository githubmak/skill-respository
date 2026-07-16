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

```
Phase 1: Orchestrator (本地)           → shot_plan.json
Phase 2: Director 子Agent (并行4-6)    → director_pass.json → 校验失败重派
Phase 3: 连续性检查 (不可跳过)          → continuity_check.py --live
Phase 4: Prompt Composer (全走子Agent) → prompt_package.json → 校验失败重派
Phase 5: Editor Pass 1 (不可跳过)      → merge_prompts.py
Phase 6: Editor Pass 2 LLM评审 (不可跳过)→ editor_pass2_prompt()
Phase 7: 最终验证 (不可跳过)            → validate_prompt_package.py
Phase 8: 导出 (不可跳过)               → export_workbook.py → Excel+Markdown
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
