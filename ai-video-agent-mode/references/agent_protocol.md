# Agent 协议

状态监督器负责整个流程循环。它先执行本地确定性阶段；只有当
`workflow_supervisor.py` 返回 `host_dispatch_required` 时，才请求 Codex 宿主派发 Agent packet。宿主记录并验证 provenance 后，必须继续同一个状态监督器；worker 完成不能被当成“等待用户确认”的节点。

当前只允许两类派发角色：

- **Master Production Agent：** 每个主镜写一条 T2V `shots[]` 任务，`source_subshot_ids` 用于记录该主镜内部节拍来源。
- **Editor Pass 2 Agent：** 每个 packet 审查一个有边界的场景窗口，只写 `windows[]` 验收记录；失败时指定最早责任阶段，不写字段补丁或替代提示词。

Scene Lock 由全局导演蓝图同一次创作，不单独派发。Worker 只能写 `packet._batch_output_path`，随后记录 provenance。
运行中的 worker 必须记录心跳；心跳只证明存活，内容进度由原子检查点单独记录，二者都不能延长绝对超时。
确定性 validator 失败可按机械字段修正；模型 Editor 失败必须把完整主镜退回 Master，或把全局理解退回
Orchestrator，不能转换成末端字段补丁。
不得派发其他 Agent 角色或阶段。

状态监督器每返回一个 packet，宿主必须按固定顺序执行：spawn 一个 worker，调用 `register_dispatch_agent.py`，
立即记录一次存活心跳。Master 每完成一个主镜、Editor 每完成一个窗口，都必须把当前完整集合原子替换到
`_batch_output_path`，再调用 packet 的 `checkpoint_command_template`。Master 的该命令在同一次本地调用中核对
机械事实并记录字节数/完成条目数；Editor 只记录进度，不解析、评分或改写创作语义。等待最终可解析的完整 batch 文件后，调用
`record_batch_provenance.py`，然后继续状态监督器。宿主在任一 worker 运行时每 10 秒或 worker 状态变化后立即轮询 supervisor；
只要有槽位释放就立即续派，不得等待整个 worker 组结束。

注册后 5 分钟仍没有第一个可解析且非空的内容检查点，或已有检查点后连续 3 分钟没有字节数/完成条目数增长，
supervisor 就退役该 packet 并定点重派；普通心跳不能刷新这两个内容计时器。packet 到达
`contract_registry.py` 定义的绝对超时时，宿主同样必须中断该 worker。supervisor 只退役这个 packet，
保留同阶段已验证和仍在时限内的其它 packet，并生成新 UUID、新输出路径和新不可复用回执。初始尝试加两次
唯一重派仍未完成时，流程立即写熔断报告并停止。整条流程从状态初始化起最多运行 90 分钟；超过截止或预测
无法在剩余预算内完成时，同样必须停止并报告，不能继续等待。

进入 Editor Pass 2 前，本地 `pre_editor_gate.py` 只写按 SHA-256 缓存的确定性审查产物。它不生成摄影、
情绪或审美结论。Editor 必须从源文、Scene Lock、相邻镜和完整提示词独立完成语义、Seedance 适配与
最终审美复审。每个窗口都读取未经截断的上一镜、当前镜、下一镜及对应场景资产；批次只控制上下文容量，
不产生质量等级。
