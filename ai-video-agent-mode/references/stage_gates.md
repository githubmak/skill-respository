# Stage Gate Summary

阶段顺序、执行者和产物只以 `scripts/contract_registry.py` 为准。本文件只说明 supervisor
何时继续、何时派发、何时阻断，不复制阶段表或字段合同。

| Gate | 继续条件 | 失败处理 |
|---|---|---|
| 配置 | `project_config.json` 已完成当前确认 | 只询问 `resolve_run_mode.py` 返回的字段 |
| 本地准备 | shot plan、source/beat ledger、preflight 通过 | 修源文登记、拆镜或配置，不派发 Agent |
| Scene Lock | 每场景一条通过 validator 的不可变事实记录 | 仅重派失败场景 |
| Master Production | 每主镜一条通过 Composer validator 的 T2V 任务 | 只修点名字段；再次失败缩为单主镜 |
| Editor | pre-editor gate 通过，所有语义 blocking 已按字段解决 | 回到最早负责字段，不整包重写 |
| Validate | 全集状态、导演、情绪/镜头、合同与导出预检全部通过 | 按报告定位一个合同切片修复 |
| Export | provenance、路径、直投编译和最终质检通过 | 不写临时残件，不静默截断 |

`waiting_for_workers` 不是门禁也不是用户确认点。Agent 完成 provenance 后立即继续 supervisor。
