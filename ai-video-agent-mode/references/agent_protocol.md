# Agent 协议

状态监督器负责整个流程循环。它先执行本地确定性阶段；只有当
`workflow_supervisor.py` 返回 `host_dispatch_required` 时，才请求 Codex 宿主派发 Agent packet。宿主记录并验证 provenance 后，必须继续同一个状态监督器；worker 完成不能被当成“等待用户确认”的节点。

当前只允许三类派发角色：

- **Scene Lock Agent：** 每个场景写一条 `scenes[]` 记录，只产出不可变制作事实。
- **Master Production Agent：** 每个主镜写一条 T2V `shots[]` 任务，`source_subshot_ids` 用于记录该主镜内部节拍来源。
- **Editor Pass 2 Agent：** 每个 packet 审查一个有边界的场景窗口，只写 `windows[]` 审查记录，并可请求按字段修复。

Worker 只能写 `packet._batch_output_path`，随后记录 provenance。运行中的 worker 必须记录心跳。重试包只接收 validator 问题库，并且只修复所属主镜任务中被点名的字段。不得派发其他 Agent 角色或阶段。

状态监督器每返回一个 packet，宿主必须按固定顺序执行：spawn 一个 worker，调用 `register_dispatch_agent.py`，运行期间至少记录一次 `record_dispatch_heartbeat.py`，等待可解析的 batch 文件，调用 `record_batch_provenance.py`，然后继续状态监督器。

进入 Editor Pass 2 前，本地 `pre_editor_gate.py` 会为合并包写一份按 SHA-256 缓存的“确定性 + 语义”审查产物。确定性失败会阻断派发；语义问题交给 Editor 修复。Editor 仍需对每个窗口执行 Agent 语义复审：`light` 窗口审当前主镜和承接摘要，`high` 窗口审完整有界场景窗口。`light` 风险层级绝不免除 Agent 复审、最终验证或导出质检。
