# Stage Gate Summary

阶段顺序、执行者和产物只以 `scripts/contract_registry.py` 为准。本文件只说明 supervisor
何时继续、何时派发、何时阻断，不复制阶段表或字段合同。生成 shot plan 前先运行
`scripts/source_gate.py`；它只拦截源文/配置不可读、为空或平台模式不支持的问题，弱场景证据写入
advisory，并输出多证据 `style_evidence` 供视觉 profile 路由，不要求用户为缺失的审美细节返工。

| Gate | 继续条件 | 失败处理 |
|---|---|---|
| 配置 | `project_config.json` 已完成当前确认 | 只询问 `resolve_run_mode.py` 返回的字段 |
| 源文闸门 | source gate `blocking=[]`，并生成可复用的源文证据回执 | 仅修复源文可读性、配置平台/模式或空输入 |
| 本地准备 | shot plan、source/beat ledger、preflight 的 blocking 为空 | 修源文登记、拆镜或配置，不派发 Agent；advisory 进入后续规划 |
| Scene Lock | 每场景一条通过 validator 的不可变事实记录 | 仅重派失败场景 |
| Master Production | 每主镜一条通过 Composer validator 的 T2V 任务 | 只修点名字段；再次失败缩为单主镜 |
| Editor | pre-editor gate 通过，所有语义 blocking 已按字段解决 | 回到最早负责字段，不整包重写 |
| Validate | 全集状态、导演、情绪/镜头、合同与导出预检全部通过 | 按报告定位一个合同切片修复 |
| Export | provenance、路径、直投编译和最终质检通过 | 不写临时残件，不静默截断 |

`waiting_for_workers` 不是门禁也不是用户确认点。Agent 完成 provenance 后立即继续 supervisor。

## 门禁分级

- `blocking`：源文保真、身份/对白引用、节拍归属、时长、唯一 ID、平台模式或输出结构失败；必须在派发前修复。
- `advisory`：视觉标点数量、风格证据不足、题材细节稀疏等可由 Scene Lock/Master Production 补足的问题；记录到报告，不单独阻断。
- 后置 Validate 仍保留全集连续性、提示词合同和导出检查，前置闸门只是把可确定的问题提前，不替代最终证据。
