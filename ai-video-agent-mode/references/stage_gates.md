# Stage Gates — 管线阶段质量门禁

## 门禁总表

| Phase | 必需输入 | 必须输出 | 通过条件 |
|-------|---------|---------|---------|
| user_confirm | (无) | project_config.json | 4项配置齐全 |
| orchestrator | source.txt | shot_plan.json | 所有镜头有shot_id/subshot_id/duration |
| emotion_analysis | shot_plan.json | emotion_output.json | 每镜emotion+performance_plan完整 |
| scene_analysis | shot_plan.json | scene_output.json | 每镜axis_space+lighting+composition |
| camera_analysis | shot_plan.json | camera_output.json | 每镜camera dict完整 |
| qa_integration | 3个analysis输出 | director_pass.json + llm_gate_review.md | 字段类型通过 + 混合门禁无blocking |
| continuity | director_pass.json | continuity/report.json | 0 errors，无无解释越轴 |
| prompt_composer | director_pass.json | prompt_package.json + llm_gate_review.md | full_prompt >= 500，台词边界无违规 |
| editor_pass1 | prompt_package.json | merged.json | 所有shot已合并 |
| editor_pass2 | prompt_package.json | llm_gate_result.json | LLM语义复审通过 |
| validate | merged.json | llm_gate_review.md | 脚本门禁 + LLM门禁均无blocking |
| export | merged.json, shot_plan.json | (无) | 文件已生成 |

## 质量阈值
同现有 — character_action>=50, lighting>=30, audio_design>=20等。

## 关卡阻断
- Phase 2a-c 失败 → 重派子Agent
- Phase 3 检测矛盾 → 回对应分析Agent修正
- 脚本门禁失败 → 直接按 issue 的字段/子镜头退回对应阶段
- LLM门禁失败 → 按 `repair_targets[].send_back_to` 退回对应子Agent
- LLM门禁只处理语义判断，不覆盖脚本确定性错误
