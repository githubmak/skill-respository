# Agent Split Review

当前拆分整体合理，保留 3 个并行分析 Agent + 1 个整合 Agent + 1 个提示词 Agent + 1 个最终审查 Agent。

## 保留现状

| Agent | 是否合理 | 原因 |
|-------|----------|------|
| Orchestrator | 合理 | 只负责拆 shot_plan 和 dialogue_refs，避免后续阶段私加台词 |
| Emotion Analysis | 合理 | 专注情绪、表情、语气、动作节拍，输出结构化轻量字段 |
| Scene Analysis | 合理 | 专注空间、人物位置、灯光、声音环境，适合并行 |
| Camera Movement | 合理 | 专注景别、焦距、机位、轴线和运镜，必须独立防越轴 |
| QA/Integration | 合理 | 对齐三路输出，发现矛盾并决定退回哪个分析 Agent |
| Prompt Composer | 合理 | 只做提示词组装，不再承担剧情判断和台词创作 |
| QA Review / Editor | 合理 | 用 LLM 能力审查语义穿帮、表演合理性和五维一致性 |

## 不建议再拆

- 不建议把表情和语气再拆成两个 Agent：二者强依赖，同镜头里分开容易出现表情和台词节奏不一致。
- 不建议把灯光从 Scene Analysis 拆出：光影需要跟空间和人物位置一起判断，否则容易造成光源跳变。
- 不建议让 Prompt Composer 同时承担 QA：Composer 容易维护自己生成的文本，最终审查应独立。

## 加强点

- Camera Movement 必须输出 `axis_start`、`axis_end`、`movement_detail`，否则 continuity gate 无法可靠判断越轴。
- QA/Integration 必须把原始 `dialogue_refs` 和 `dialogue_raw_text` 传到 director/prompt 阶段，给脚本门禁对照。
- Editor LLM 只审查语义类问题，不覆盖脚本确定性结果；脚本说 blocking 时不允许 LLM 降级放行。

## 退回路由

| 问题 | 退回目标 |
|------|----------|
| 无解释越轴、人物位置跳变、机位方向不连续 | camera-analysis |
| 表情/动作不符合角色状态或台词语气 | emotion-analysis |
| 光影、场景、道具、人物站位不连续 | frames-analysis |
| 三路分析字段互相矛盾 | qa-integration |
| 提示词拼贴、模板污染、台词混入画面描述 | prompt-composer |
| 最终语义穿帮但源分析正确 | QA Review / Editor |
