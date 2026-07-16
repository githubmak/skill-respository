# Stage Gates — 管线阶段质量门禁

## 门禁总表

| Phase | 必需输入 | 必须输出 | 通过条件 |
|-------|---------|---------|---------|
| user_confirm | (无) | project_config.json | 4项配置齐全 |
| orchestrator | source.txt | shot_plan.json | 所有镜头有shot_id/subshot_id/duration |
| emotion_analysis | shot_plan.json | emotion_output.json | 每镜emotion+performance_plan完整 |
| scene_analysis | shot_plan.json | scene_output.json | 每镜axis_space+lighting+composition |
| camera_analysis | shot_plan.json | camera_output.json | 每镜camera dict完整 |
| qa_integration | 3个analysis输出 | director_pass.json | 无字段类型错误 |
| continuity | director_pass.json | (无) | 0 errors |
| prompt_composer | director_pass.json | prompt_package.json | full_prompt >= 500 |
| editor_pass1 | prompt_package.json | merged.json | 所有shot已合并 |
| validate | merged.json | (无) | 无问题列表 |
| export | merged.json, shot_plan.json | (无) | 文件已生成 |

## 质量阈值
同现有 — character_action>=50, lighting>=30, audio_design>=20等。

## 关卡阻断
- Phase 2a-c 失败 → 重派子Agent
- Phase 3 检测矛盾 → 回对应分析Agent修正
