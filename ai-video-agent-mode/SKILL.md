---
name: ai-video-agent-mode
description: >
  将剧本、分镜或场景转换为可直接投喂即梦 T2V 的提示词包，提供剧情节拍、表演、
  连续性、动作预算、风险审查与 Markdown/XLSX 导出。适用于剧本转 AI 视频提示词、
  即梦 T2V、跨镜连续和低抽卡风险控制。
---

# AI Video Agent Mode

将源文转换为可审查、可恢复、可导出的即梦 T2V 提示词包。技能只生成提示词与制作元数据，
不调用、观看或评分视频生成结果；`ai_model_readiness_score` 只表示提示词合同的执行风险，
不表示成片质量。

## 权威契约

- 详细字段、五段提示词、动作预算和验证规则：`references/format_constraints.md`。
- 路由和按需读取规则：先读 `references/ROUTES.md`。
- 当前运行时阶段、输出和门禁：`scripts/pipeline_templates.py` 与 `scripts/pipeline_state.py`。
- 历史 Emotion / Camera / Director 分阶段文档不是当前可派发阶段；当前实现不兼容旧 pipeline。

当前仅支持即梦 `t2v`。禁止 I2V、R2V、参考素材槽位、首尾帧和动作素材路径。允许导出当前镜头剧情关键帧与空间调度辅助图，但它们不属于 T2V 正文。

## 当前管线

| 顺序 | 阶段 | 执行者 | 产物/门禁 |
|---|---|---|---|
| 0 | 配置确认 | Wizard | 已确认 `project_config.json` |
| 1 | Orchestrator | 本地脚本 | shot plan、source ledger、dramatic beat ledger、preflight |
| 2 | Scene Lock | Agent | 不可变场景、光源、服装和空间事实 |
| 3 | Master Production | Agent | 每主镜一条 T2V 任务与完整合同 |
| 4 | Editor Pass 1 | 本地脚本 | `pre_editor_gate.py` |
| 5 | Editor Pass 2 | Agent | 仅修语义穿帮与执行竞争 |
| 6 | Validate | 本地脚本 | `emotion_camera_audit.py`、`validate_modec.py`、`check_export.py` |
| 7 | Export | 本地脚本 | 已确认路径下 Markdown 与 XLSX |

不得跳过、重命名或假设存在其它运行时阶段。`master_production` 内部仍须遵守
`emotion_driver → camera_beat_map → full_prompt` 的字段接力，但它们是同一任务内的有序字段，
不是可单独派发的 Agent。

## 运行规则

1. 手动新调用默认 `full --intent new`，必须使用新的空 `run_dir`。续跑、审查、导出、单镜修复才可复用已确认运行。
2. 先执行 `route_task.py`，再按返回路由读取；新运行按 Wizard 顺序逐轮确认：输出目录、画幅与风格、时长与平台、音频、交付路径。
3. 确认后只由 `workflow_supervisor.py` 驱动状态机。`waiting_for_workers` 不需要用户确认。
4. Agent 只能写 packet 的 `_batch_output_path`。每次派发必须经过注册回执、至少一次心跳、完成 provenance 和阶段验证，之后才可合并。
5. 公共合并使用 `merge_agent_outputs.py --require-provenance`；失败只修 validator 指定字段，第二次重试为单主镜批次。
6. 每个主镜仅服务一个 `narrative_beat_id`。`shot_group` 仅描述该节拍内的连续变化，最多一次单向注意力交接；需回切、第二目标或第二独立动作链时拆为下一主镜。
7. 台词、OS、OV 按 `ref/kind/speaker/text` 锁定，逐字保留。OS/OV 无口型；无源文不得新增人声。
8. `full_prompt` 只包含可执行画面指令。QA、负面词、工程数据、风险结论和迁移说明必须位于 JSON 独立字段。
9. Scene Lock 是光源、色温、服装与空间不可变事实的唯一来源。后续阶段只能消费这些事实。
10. 高风险镜指多人走位、受力/打斗、道具交接、长台词、`shot_group` 或高抽卡风险。高风险 Master Production 批次上限为 **2**，standard 为 6，light 为 10；具体值以 `dispatch_risk()` 为唯一实现来源。
11. 同一地点跨镜必须复用 Scene Lock 的空间ID、空间主锁定、入口出口、人物槽位和道具活动区；同一场景影调从场景色卡消费，不得逐镜重新解释空间或乱换光色。
12. 直接投喂即梦的导出文本不得保留“上一镜、继承、尾帧、剪辑、切到、反打到”等元叙述；规范正文可用于验证落幅，导出 feed 必须转成当前可见事实。

## 质量规则

- 先满足站位、朝向、道具归属、口型、动作预算和落幅继承，再追求风格化镜头。
- 每个子镜只有一个实焦主体、一个主要动作或状态变化、一个景别可见的表演证据和一个可继承落幅。
- 表演按“触发 → 可见泄露 → 身体承接 → 声音/呼吸 → 残留”组织；运镜只能响应已确认的可见重音。
- Master Production 写镜前先建立 `source_constraint_basemap`：空间、人物朝向、状态/道具、物理反推、张弛功能、情绪钩子、多人体反应、影调、声音/口型和屏幕文字策略；后期校验只兜底，不承担主要创作修复。
- 画面质感必须落成可执行视觉锚点：光源方向/色温、脸/手/道具受光面、浅阴影/反光、背景虚化或剧情相关材质；不得只写电影感、高级感、质感。
- 构图、焦段、运镜和材质只服务本镜唯一任务；复杂对白、多人反应、道具转移或复杂运镜镜头优先保稳定，只保留一个光影/构图锚点。
- 多人戏中清晰入画的具名非主表演者不能只是闭口站着；必须分配受击反应、观察反应、背景弱化，或降为肩线/边缘虚化/画外。
- 每镜标记张弛功能：铺垫、升压、峰值、释放或缓冲；不要连续强推近、强表情、强停顿，强张力后必须给短余波、关系缓冲或明确悬置理由。
- 道具交接、转身、起身、开门、离场、手腕控制等状态变化必须写“起始 → 接近/接触 → 移动/受力 → 释放/稳定终态”；动作强时运镜降为固定或低幅推近。
- 手机聊天、来电名称、通知弹窗等 UI 文字若由 AI 生成，必须声明独立二维浮层、安全区和透视隔离；否则把具体文字留到后期文字表。
- 人物、对白、道具变化、重要叙事或高风险镜必须有 `story_punch_contract`、`performance_contract`、`continuity_contract` 与 `reroll_control`。`rising/peak` 另需 `pressure_release_design`。
- 复杂互动优先拆镜或降运镜，不能靠更多修辞、更多表情或更长静止来掩盖模型负担。
- 原生音频开启时，台词必须以 `{人物}（台词/OS/OV）: "原文"` 在子镜头组逐字出现一次；关闭时原文仅保留在元数据与导出表。

## 性能与测试

- 性能目标是 50 主镜 P95 不超过 55 分钟，不是当前声明。只有三类场景（对白、动作、混合）各一组正常与 10% 失败注入的真实运行通过 `benchmark_core_pipeline.py` 后，才能声称达标。
- `performance_budget.py` 从 pipeline state 输出总耗时、local/worker/暂停估算拆分、每阶段耗时、dispatch 数、重试数和达标状态。
- 结构回归：`python3 scripts/test_current_pipeline.py` 与 `python3 scripts/golden_jimeng_check.py`。
- 真实源文 smoke test：`python3 scripts/test_source_smoke.py --source <source.txt> --min-shots <n>`。该测试只验证确定性配置、拆镜、台账、时长、preflight 与 packet 化，不伪造 Agent 输出或成片验收。
- 已完成真实 E2E 回归：`python3 scripts/test_completed_e2e_run.py --run-dir <completed_run_dir> --source <source.txt> --expected-shots <n>`。该测试只验收真实 supervisor/worker/provenance 产物，不生成或伪造 Agent 输出。
- 构造 50 镜 benchmark fixture：`python3 scripts/create_benchmark_fixtures.py --out-dir <fixture_dir>`，再用 `benchmark_core_pipeline.py` 验证六组结构。fixture 报告只证明 benchmark 机制可复跑；只有 `evidence_kind=real_pipeline` 的六组真实 Agent 运行才可声明真实 SLO。

## 常用命令

```bash
python3 scripts/route_task.py full --run-dir <run_dir> --intent new
python3 scripts/workflow_supervisor.py --run-dir <run_dir> --source <source.txt>
python3 scripts/test_current_pipeline.py
python3 scripts/golden_jimeng_check.py
python3 scripts/test_source_smoke.py --source <source.txt> --min-shots 1
python3 scripts/test_completed_e2e_run.py --run-dir <completed_run_dir> --source <source.txt> --expected-shots <n>
python3 scripts/run_regression_suite.py --source <source.txt> --min-shots <n> --completed-run <completed_run_dir> --expected-shots <n> --benchmark-report <report.json>
python3 scripts/run_regression_suite.py --source <source.txt> --min-shots <n> --completed-run <completed_run_dir> --expected-shots <n> --synthetic-benchmark-dir <fixture_dir>
python3 scripts/create_benchmark_fixtures.py --out-dir <fixture_dir>
python3 scripts/benchmark_core_pipeline.py --out <benchmark_report.json> <completed_50_shot_run_dir> [...]
```

Windows 的多行内容先写入文件，再将短参数与路径交给 `scripts/run_skill_tool.ps1`；不得将 JSON、提示词或 here-string 拼入 shell 命令。
