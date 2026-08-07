# Stage Gate Summary

`creative_engineering_boundary.md` 高于本门禁。门禁可以阻断或定位问题，但不得自行改写模型创作语义。
涉及剧情、情绪、表演、构图、运镜、光影、声音或提示词精炼的失败必须回到对应模型阶段。

阶段顺序、执行者和产物只以 `scripts/contract_registry.py` 为准。本文件只说明 supervisor
何时继续、何时派发、何时阻断，不复制阶段表或字段合同。生成 shot plan 前先运行
`scripts/source_gate.py`；它只拦截源文/配置不可读、为空或平台模式不支持的问题，不生成视觉 profile，
也不要求用户为缺失的审美细节返工。

| Gate | 继续条件 | 失败处理 |
|---|---|---|
| 配置 | `project_config.json` 已完成当前确认 | 只询问 `resolve_run_mode.py` 返回的字段 |
| 源文闸门 | source gate `blocking=[]`，并生成可复用的源文证据回执 | 仅修复源文可读性、配置平台/模式或空输入 |
| 本地准备 | 工程逐行 source ledger、shot plan 的 JSON、ID、源文映射、逐字台词和时长有效 | 修机械事实；拆镜与节奏问题退回模型 |
| 模型导演蓝图 | `creative_blueprint_request.json` 和工程 source ledger 已交付，模型同时提交 `shot_plan.draft.json` 与 `scene_locks.draft.json` | 缺任一草案就暂停并返回 `creative_authoring_required`；工程不得代写分镜或 Scene Lock |
| Master Production | 每主镜首次落盘就是模型自审后的最终候选，且确定性结构有效 | 机械错误定点修复；语义问题由模型整镜重做，不做末端补丁 |
| Editor | 独立模型验收通过，`blocking=[]` | 只说明创作因果并回到 Orchestrator 或 Master，Editor 不改写提示词 |
| Validate | 确定性事实有效且模型 Editor 已通过 | 机械问题按字段修，创作问题回模型 |
| Export | provenance、路径、版本映射、字符数和原样排版通过 | 不写临时残件，不改写创作文本 |

`waiting_for_workers` 不是门禁也不是用户确认点。Agent 完成 provenance 后立即继续 supervisor。

## 门禁分级

- `blocking`：源文保真、身份/对白引用、源文映射、时长、唯一 ID、平台模式或输出结构失败；必须在派发前修复。
- 创作质量没有脚本 advisory 分数；模型 Editor 直接承担连续性、摄影、情绪、Seedance 和审美判断。
