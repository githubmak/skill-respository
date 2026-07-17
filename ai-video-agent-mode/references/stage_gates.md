# Stage Gates — 管线阶段质量门禁

## 门禁总表

| Phase | 必需输入 | 必须输出 | 通过条件 |
|-------|---------|---------|---------|
| user_confirm | (无) | project_config.json | 画幅、风格、最大时长、用户导出目录齐全 |
| orchestrator | 用户源文件/文本 | .cache/orchestrator/shot_plan.json | 所有 shot/subshot 有 id、duration、dialogue_refs 可回溯 |
| emotion_analysis | .cache/orchestrator/shot_plan.json | .cache/analysis/emotion_output.json | `items[]` 按 subshot_id 覆盖全部派发项 |
| scene_analysis | .cache/orchestrator/shot_plan.json | .cache/analysis/scene_output.json | `items[]` 按 subshot_id 覆盖全部派发项 |
| camera_movement | .cache/orchestrator/shot_plan.json | .cache/analysis/camera_output.json | `items[]` 按 subshot_id 覆盖全部派发项 |
| qa_integration | 三个 analysis 输出 | .cache/director/director_pass.json | 本地 handler 按 subshot_id 合并，字段类型通过 |
| director | .cache/director/director_pass.json | .cache/director/director_pass.json | director 字段和污染检查无 blocking |
| continuity | director_pass.json + shot_plan.json | .cache/continuity/report.json | 0 errors，无无解释越轴 |
| prompt_composer | .cache/director/director_pass.json | .cache/prompt_package.json | full_prompt >= 500，台词边界无违规 |
| editor_pass1 | .cache/prompt_package.json | .cache/prompt_package.json | Python Pass 1 清理完成 |
| editor_pass2 | .cache/prompt_package.json | .cache/review/llm_gate_result.json | LLM 语义复审通过 |
| validate | .cache/prompt_package.json + project_config.json | review packet/result | 脚本门禁 + LLM门禁均无 blocking |
| export | .cache/prompt_package.json + shot_plan.json | 用户导出目录下的文件 | Excel/Markdown 已生成并可打开 |

## 关卡阻断

- Phase 2a-c 失败：重派对应子Agent，只发送失败 subshot_id 和对应 dispatch packet。
- Phase 3 检测矛盾：回对应分析 Agent 修正，不由主Agent手改分析结果。
- 脚本门禁失败：直接按 issue 的字段/子镜头退回对应阶段。
- LLM门禁失败：按 `repair_targets[].send_back_to` 退回对应子Agent。
- LLM门禁只处理语义判断，不覆盖脚本确定性错误。
