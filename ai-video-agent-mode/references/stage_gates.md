# Stage Gates — 管线阶段质量门禁

## 门禁总表

| Phase | 必需输入 | 必须输出 | 通过条件 |
|-------|---------|---------|---------|
| user_confirm | 用户本次明确给出的输出文件位置/输出目录 | project_config.json | 画幅、风格、最大时长、平台、音频能力、T2V/I2V/R2V、真实参考资产和本次导出目录齐全；不得使用默认目录或上次目录 |
| orchestrator | 用户源文件/文本 | .cache/orchestrator/shot_plan.json | 所有 shot/subshot 有 id、duration、dialogue_refs 可回溯 |
| emotion_analysis | .cache/orchestrator/shot_plan.json | .cache/analysis/emotion_output.json | `items[]` 按 subshot_id 覆盖全部派发项；全部 batch provenance 通过 |
| scene_analysis | .cache/orchestrator/shot_plan.json | .cache/analysis/scene_output.json | `items[]` 按 subshot_id 覆盖全部派发项；全部 batch provenance 通过 |
| camera_movement | .cache/orchestrator/shot_plan.json | .cache/analysis/camera_output.json | `items[]` 按 subshot_id 覆盖全部派发项；全部 batch provenance 通过 |
| qa_integration | 三个 analysis 输出 | .cache/director/director_pass.json | 本地 handler 按 subshot_id 合并，字段类型通过 |
| director | .cache/director/director_pass.json | .cache/director/director_pass.json | director 字段和污染检查无 blocking |
| continuity | director_pass.json + shot_plan.json | .cache/continuity/report.json | 0 errors，无无解释越轴 |
| prompt_composer | .cache/director/director_pass.json | .cache/composer/merged.prompt_package.json | v4 四段齐全；120-1100字；时间轴连续；角色优先级、动作预算、表演合同、连续性合同、抽卡控制、参考资产有效；负面词独立保留占位；全部 batch provenance 通过 |
| editor_pass1 | .cache/composer/merged.prompt_package.json | .cache/composer/merged.prompt_package.json | Python Pass 1 幂等归并完成；重复执行不增加 subshot |
| editor_pass2 | .cache/composer/merged.prompt_package.json | .cache/review/llm_gate_result.json | LLM 语义复审通过；三份合同与 full_prompt 落地关系无 blocking |
| validate | .cache/composer/merged.prompt_package.json + project_config.json | review packet/result | `validate_composer_output.py`、`validate_modec.py`、`check_export.py` + LLM门禁均无 blocking |
| export | .cache/composer/merged.prompt_package.json + shot_plan.json | 用户导出目录下的文件 | Excel/Markdown 已生成并可打开；Markdown 不含 QA 元数据或生成控制 |

## 关卡阻断

- Phase 2a-c/Composer 失败：重新运行 `dispatch_cache.py`，只发送失败 subshot_id 与新返回的唯一 dispatch packet；禁止覆盖已验证 batch。
- Phase 3 检测矛盾：回对应分析 Agent 修正，不由主Agent手改分析结果。
- 脚本门禁失败：直接按 issue 的字段/子镜头退回对应阶段。
- LLM门禁失败：按 `repair_targets[].send_back_to` 退回对应子Agent。
- 修复合并只接受 provenance 通过的 batch；同一 subshot_id 由最新已验证修复替换，未失败的 baseline 保持不变。
- LLM门禁只处理语义判断，不覆盖脚本确定性错误。
