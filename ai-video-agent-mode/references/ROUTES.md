# Routes And Script Index

Read this file first. Select one explicit route, then read only the linked contract and script entry points. Do not load unrelated Python files or the full runbook.

| Request | Route | Required reading | Run only |
|---|---|---|---|
| New script, changed story, or changed project settings | `full` | `SKILL.md`, `format_constraints.md`, `stage_gates.md` | `pipeline_runner.py`, validators, dispatch scripts |
| Diagnose pacing, continuity, or prompt quality | `audit` | relevant exported prompt package, `format_constraints.md` | `check_export.py`, `validate_modec.py` |
| Generate files from a passed package | `export` | `export_spec.md` | `check_export.py`, `export_with_validation.py` |
| Repair one failed subshot | `single-repair` | packet `constraints_path`, `retry_context_path`, compact handoff | `dispatch_cache.py`, phase validator, provenance scripts |
| Generate prompts from approved Director data | `compose` | Composer sections of `format_constraints.md` | `dispatch_cache.py`, `validate_composer_output.py` |

## Initialization

- 用户手动再次调用时默认选择 `full --intent new`，且必须指向新的空 `run_dir`。不要删除或读取旧缓存；新运行从 Phase 0 重新建立全部质量合同。
- `full/new` 先运行 `resolve_run_mode.py`，只询问返回的 `next_fields`（首轮 1 项、后续每轮最多 2 项）。使用 `configuration_wizard.py start/answer/status` 记录每轮答案；完成确认前不得派发 Agent。
- 仅用户明确要求“继续/续跑”时使用 `full --intent resume`；`audit`、`compose`、`single-repair` 复用已确认配置而不重复提问。`export --intent reexport` 复用配置但必须确认本次 Markdown 输出路径。

## Reading Rules

- Run `python3 scripts/route_task.py <route> --run-dir <run_dir> --intent <new|resume|audit|reexport>` before loading a route.
- Use `rg -n` to find a script entry point or function, then read only the relevant region.
- Treat packet `items`, scaffold, scene locks, handoff, and retry context as authoritative. `source_path` is fallback context, not default reading.
- Read a stage summary from `.cache/stage_summary/<phase>.json` before an older full artifact when resuming. Reopen the full artifact only for the named subshot or field.

## Hot Paths

- Must read before dispatch: `dispatch_cache.py` entry/packet fields, the selected phase constraints, `agent_protocol.md` provenance sequence.
- Must run, not reread: `validate_agent_output.py`, `validate_composer_output.py`, `record_batch_provenance.py`, `merge_agent_outputs.py`, `check_export.py`.
- Read only when debugging: `pipeline_runner.py`, `pipeline_state.py`, `sources.py`, `gate_check.py`.
