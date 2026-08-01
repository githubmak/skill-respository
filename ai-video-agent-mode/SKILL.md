---
name: ai-video-agent-mode
description: >
  将剧本、分镜或场景转换为可直接投喂即梦 T2V 的提示词包，提供剧情节拍、表演、
  连续性、静态关键帧美学、动态运动美学、动作预算、风险审查与 Markdown/XLSX 导出。
  适用于剧本转 AI 视频提示词、即梦 T2V、跨镜连续、画面美术指导和低抽卡风险控制。
---

# AI Video Agent Mode

把源文转换为可审查、可恢复、可导出的即梦 T2V 提示词包。只生成提示词与制作元数据；
不调用、观看或评分生成结果。`ai_model_readiness_score` 表示合同执行风险，不代表成片质量。

## 执行

1. 先运行 `python3 scripts/route_task.py <route> --run-dir <run_dir> --intent <intent>`。
2. 只读取返回的 `context_plan.read_first`；只有当前错误或任务明确命中时，才读取
   `read_on_demand`。`run_only` 中的脚本直接运行，不预读源码。
3. 新任务默认使用 `full --intent new` 和新的空 `run_dir`。只有用户明确要求续跑时使用
   `full --intent resume`。完整配置与源文件已一次提供时，可使用 `--auto-start`；它不得跳过
   任何阶段、provenance、validator 或导出门禁。
4. 配置确认后，只循环调用 `workflow_supervisor.py`。`waiting_for_workers` 是内部等待状态，
   不是用户确认点；只有路由明确返回 `needs_user_confirm=true` 时才提问。
5. supervisor 返回 `host_dispatch_required` 时，按 `references/agent_protocol.md` 处理每个
   packet：注册 Agent、至少一次心跳、等待 batch、记录 provenance，然后立即继续 supervisor。
6. Agent 只能写 `packet._batch_output_path`。合并必须使用 provenance 门禁；失败只修 validator
   点名字段，第二次重试缩为单主镜。
7. Validate 全部通过后，才调用 `export_with_validation.py` 写入配置中已确认的交付路径。

## 上下文预算

正常运行不得预读完整的 `references/format_constraints.md` 或
`references/production_quality_knowledge.md`。阶段约束已由 `dispatch_cache.py` 选择并写入
`packet.constraints_path`，Master Production 的锁定字段已写入 scaffold。

| 情况 | 最小读取 |
|---|---|
| 新运行 | route 输出、`stage_gates.md` |
| 续跑 | route 输出、最新 `.cache/stage_summary/<phase>.json` |
| Agent 派发 | packet、`constraints_path`、对应 scaffold/cache、`agent_protocol.md` |
| 单镜修复 | packet、`retry_context_path`、validator 点名字段 |
| 审查 | 先运行 validator；再按 `contracts/contract_index.md` 读取命中的一个合同切片 |
| 导出 | 直接运行导出脚本；仅在诊断格式时读取 `export_spec.md` |
| 修改技能合同 | 才读取完整字段合同、知识库、schema、validator、Golden 与一致性检查 |

不得为“更保险”同时加载全部合同。先依赖结构化 packet、scaffold、stage summary 和 validator；
只有这些信息不足以解释一个具体失败时，再打开对应权威段落。

## 不可破坏约束

- 仅支持即梦 `t2v`。禁止 I2V、R2V、参考素材槽位或动作素材路径；三状态关键帧只是前期参考。
- 台词、OS、OV 按 `ref/kind/speaker/text` 逐字锁定；OS/OV 无口型，无源文不得新增人声。
- 每个主镜只服务一个 `narrative_beat_id`；回切、第二目标、第二独立动作链或容量不足时拆镜。
- Scene Lock 是空间、服装、道具活动区、光源与影调事实的唯一来源；后续阶段只消费，不重写。
- `full_prompt` 只写当前可见、可执行画面事实。QA、负面词、工程数据、风险与分析标签留在独立字段。
- Master Production 内部按 `visual_bible → aesthetic_director → continuity_compiler → full_prompt`
  接力；这些是同一任务内字段，不是额外 Agent 阶段。
- 直投正文只由 `direct_prompt_compiler.py` 编译：保护源文与硬事实，只整句压缩，超过 700 字
  且无法无损压缩时阻断；180–500 字导演卡使用同一事实源，不静默截断或用空话补齐。
- 复杂度和风险只改变批次与专项合同，不降低 direct-copy、连续性、口型、审美或导出门槛。
- 只有用户提供真实候选并明确要求视觉复核时才记录候选评分；不得用 Golden 或提示词推测成片。

## 权威来源

- 机器阶段、版本、执行者、产物、超时与批次：`scripts/contract_registry.py`
- 路由上下文清单：`scripts/route_task.py`；说明版：`references/ROUTES.md`
- 字段与验证规则：`references/format_constraints.md`
- 低耗合同定位：`references/contracts/contract_index.md`
- 画面/连续性知识候选池：`references/production_quality_knowledge.md`
- 静态与动态美学：`references/contracts/aesthetic_directing_contract.md`
- 当前 Agent 指令：`references/dispatch/*.md`
- 运行状态与门禁：`scripts/pipeline_state.py`、`scripts/pipeline_templates.py`

历史 `references/agents/*.md` 仅为归档指针，不得派发。当前实现不兼容旧 Emotion、Camera、
Director 或 Composer 独立阶段。

## 验证

修改技能后运行：

```bash
python3 scripts/check_rule_consistency.py
python3 scripts/test_current_pipeline.py
python3 scripts/test_quality_upgrades.py
python3 scripts/test_production_intelligence.py
python3 scripts/test_keyframe_pipeline.py
python3 scripts/golden_jimeng_check.py
python3 scripts/test_fast_start.py
```

真实源文使用 `test_source_smoke.py`；真实已完成运行使用 `test_completed_e2e_run.py`；真实成片
A/B 只用 `validate_visual_ab_review.py`。benchmark fixture 只证明机制可复跑，不代表真实 SLO。

Windows 只把短参数与路径传给 `scripts/run_skill_tool.ps1`；不要把 JSON、提示词或 here-string
拼入 shell 命令。
