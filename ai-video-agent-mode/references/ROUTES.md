# Route Context Policy

`scripts/route_task.py` 是机器来源。先运行它，再遵守返回的 `context_plan`；本文件仅解释
各路由为什么需要这些上下文。不要在路由前加载完整 runbook 或大合同。

| Route | 适用任务 | `read_first` | `read_on_demand` | `run_only` |
|---|---|---|---|---|
| `full` | 新源文、剧情或配置变化；明确续跑 | `stage_gates.md` | 最新 source-gate/stage summary、命中的合同索引行 | `workflow_supervisor.py` |
| `compose` | 已有 shot plan 与 Scene Lock | `agent_protocol.md` | packet 的 constraints/scaffold/scene lock cache | dispatch 与 Composer validator |
| `single-repair` | 修一个失败主镜或字段 | packet constraints、retry context | 对应 stage summary | provenance 与 merge 脚本 |
| `audit` | 诊断现有包，不重生成 | 无 | validator 报告、命中的合同索引行 | 全集/导演/情绪/ModeC/export audit |
| `export` | 导出已通过验证的包 | 无 | 仅格式诊断时读 `export_spec.md` | `export_with_validation.py` |

## 读取纪律

- 不在正常 `full`、`compose`、`audit` 中预读 `format_constraints.md`、
  `production_quality_knowledge.md` 或完整 Python 实现。
- Worker 只处理 `packet.items`，先读 `constraints_path`；Master Production 再读 scaffold 和
  scene lock cache。`source_path` 仅在 packet 信息不足时作为局部回退。
- 续跑先读 `.cache/pipeline_state.json` 和当前阶段已验证产物。只为 validator 点名的主镜或字段重开大产物。
- 审查先运行 validator，再用 `contracts/contract_index.md` 定位一个相关切片；不要为了一个
  口型、道具或光影问题同时读取全部质量知识。
- 只有静态/动态美学问题命中时，按需读取
  `contracts/aesthetic_directing_contract.md`，不把它加入正常路由的 `read_first`。
- 脚本能确定性验证或生成的内容直接运行脚本，不把实现源码加载进模型上下文。
- 修改技能合同才读取完整权威段落，并同步 schema、validator、Golden 和 rule consistency。

## 初始化

- 手动新调用默认 `full --intent new`，必须使用新的空 `run_dir`。
- 只有用户明确要求继续时使用 `full --intent resume`。
- 参数不完整时按 `resolve_run_mode.py` 返回的 `next_fields` 逐轮确认。
- 高质量快速模式要求同次提供全部九个基础字段配置和源文件，可用
  `--config ... --source ... --auto-start`；缺字段、
  路径越界、源文件缺失或非空 run_dir 必须原子失败。
- `audit`、`compose`、`single-repair` 复用已确认配置；`export --intent reexport` 使用锁定的
  `delivery.markdown_path`。
- 目标模型在配置确认阶段触发：`seedance_target=auto`（默认）只导出 dual-safe 文件；
  `2.0` 或 `2.5` 导出对应单版本；`both` 导出 `*_Seedance2.0.md`、`*_Seedance2.5.md` 和
  `00_双版本索引.md`。不需要另起一次管线。

## Supervisor 循环

配置确认后持续调用 `workflow_supervisor.py`。本地阶段自动运行；
`host_dispatch_required` 才派发 Agent；`waiting_for_workers` 只等待回执、心跳或验证结果。
完成每个 packet 的 provenance 链后立即继续 supervisor。仅 `needs_user_confirm=true` 可以暂停提问。

## Packet 热路径

派发只读 packet、所列 sidecar 和 `references/agent_protocol.md`。运行而不预读：
`validate_scene_locks.py`、`validate_composer_output.py`、`pre_editor_gate.py`、
`record_batch_provenance.py`、`merge_agent_outputs.py`、`episode_state_graph.py`、
`episode_director_audit.py`、`check_export.py`。仅在调试状态机实现时读取
`pipeline_runner.py`、`pipeline_state.py`、`pipeline_runtime.py` 或 `sources.py`。

`dispatch/scene_lock_note.md`、`dispatch/master_production_note.md` 与
`dispatch/editor_pass2_note.md` 由 `dispatch_cache.py` 自动写入阶段 sidecar，宿主不重复预读。
