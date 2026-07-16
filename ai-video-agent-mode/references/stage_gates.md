# Stage Gates — 管线阶段质量门禁

每个 Phase 切换前加载，确认当前阶段输出是否满足进入下阶段的条件。

## 门禁总表

由 `pipeline_templates.py` 的 `GATES` 字典定义每个阶段的输入/输出文件依赖：

| Phase | 必需输入文件 | 必须输出文件 | 通过条件 |
|-------|------------|------------|---------|
| orchestrator | shot_plan.json, project_config.json | shot_plan.json | 所有镜头有 shot_id/subshot_id/duration |
| director | shot_plan.json, project_config.json | director_pass.json | 每镜 actor_data 全字段完整 |
| continuity | director_pass.json, shot_plan.json | (无) | continuity_check.py 返回 0 问题 |
| prompt_composer | director_pass.json | prompt_package.json | 每镜 full_prompt >= 500 chars |
| editor_pass1 | prompt_package.json | prompt_package.json(扩充) | 所有 prompt 已合并到 merged_full_prompts |
| editor_pass2 | prompt_package.json | prompt_package.json(修订) | LLM 评审通过 |
| validate | prompt_package.json, project_config.json | (无) | 验证返回空问题列表 |
| export | prompt_package.json, shot_plan.json | (无) | 导出文件已生成 |

## 门禁检查流程

```python
# 通过 scripts/pipeline_templates.py 的 check_gate() 执行
check_gate(run_dir, phase, strict=True)
# strict=True → 失败时退出
# strict=False → 返回 False（用于 Phase 3/5/6/7/8 不可跳过检查）
```

## 质量阈值

### Director 质量门槛（quality.py）

| 字段 | 最少字符数 | 检查方式 |
|------|-----------|---------|
| character_action | 50 chars | 字符串长度 |
| lighting | 30 chars | 字符串长度 |
| audio_design | 20 chars | 字符串长度 |
| axis_space | 30 chars | 字符串长度 |
| camera_position | 20 chars | 字符串长度 |
| micro_actions | 15 chars | 字符串长度 |
| emotion.expression_chain | 15 chars | 字符串长度 |
| action_beats.{start/transition/contact_or_peak/end_state} | >=10 chars | 字符串长度 |
| 文件大小 | >= items * 1500 bytes | 整体文件 |

### Prompt Composer 质量门槛

| 检查项 | 门槛 | 说明 |
|-------|------|------|
| full_prompt 长度 | >= 500 chars | 每镜提示词 |
| JSON 结构 | 合法 JSON | 输出文件可解析 |

## 关卡阻断处理

```
门禁失败 → 打印 BLOCKED 信息 + 列出缺失文件
  ├─ Director/Composer 门禁失败 → 回到 Phase 2/4 重派
  ├─ 连续性检查失败 → 回到 Phase 2 修复
  ├─ Editor Pass 2 失败 → 提示 LLM 重新评审
  └─ 验证/导出失败 → 修复数据后重试
```
