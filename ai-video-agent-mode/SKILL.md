---
name: ai-video-agent-mode
description: >
  将剧本、分镜或场景转换为可直接投喂即梦 T2V 的提示词包，提供剧情节拍、表演、
  连续性、静态关键帧美学、动态运动美学、动作预算、风险审查与 Markdown/XLSX 导出。
  适用于剧本转 AI 视频提示词、即梦 T2V、跨镜连续、画面美术指导和低抽卡风险控制。
---

# AI Video Agent Mode

把源文转换为可审查、可恢复、可导出的即梦 T2V 提示词包。主流程生成提示词与制作元数据；
用户提供真实成片并明确要求复核时，才运行独立的视频指标或 A/B 校准。`ai_model_readiness_score`
表示合同执行风险，不代表成片质量。

## 执行

1. 先按平台运行路由：Windows 使用
   `powershell -ExecutionPolicy Bypass -File scripts/run_skill_tool.ps1 scripts/route_task.py <route> --run-dir <run_dir> --intent <intent>`；
   macOS 使用 `python3 scripts/route_task.py <route> --run-dir <run_dir> --intent <intent>`。
2. 只读取返回的 `context_plan.read_first`；只有当前错误或任务明确命中时，才读取
   `read_on_demand`。`run_only` 中的脚本直接运行，不预读源码。
3. 新任务默认使用 `full --intent new` 和新的空 `run_dir`。只有用户明确要求续跑时使用
   `full --intent resume`。完整配置与源文件已一次提供时，优先使用 `--auto-start`；它不得跳过
   任何阶段、provenance、validator 或导出门禁。
4. 配置确认后，只循环调用 `workflow_supervisor.py`。`waiting_for_workers` 是内部等待状态，
   不是用户确认点；只有路由明确返回 `needs_user_confirm=true` 时才提问。
5. supervisor 返回 `host_dispatch_required` 时，按 `references/agent_protocol.md` 处理每个
   packet：注册 Agent、至少一次心跳、等待 batch、记录 provenance，然后立即继续 supervisor。
6. Agent 只能写 `packet._batch_output_path`。Master Production 每完成一个主镜，先运行 packet 的
   `incremental_validation_command` 做字段级校验；批次结束仍必须运行完整 `local_validation_command`。
   合并必须使用 provenance 门禁。局部失败按 `字段 → 主镜 → pair/window → scene` 升级，合格主镜可由
   partial provenance 保留，未解决主镜自动定点重试；两次字段修复后才扩大到单主镜，无法归属镜头的全局
   合同错误禁止 partial 复用。任何增量通过都不能替代最终全量 Validate。
7. Validate 全部通过后，才调用 `export_with_validation.py` 写入配置中已确认的交付路径；导出目标由确认过的
   `seedance_target: auto | 2.0 | 2.5 | both` 决定。`auto` 生成一份 dual-safe 文件，`2.0`/`2.5`
   生成单一优化文件，`both` 从同一份合同原子生成两份可独立投喂 Markdown 和一个非投喂索引。

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
- `seedance_target` 是模型适配层，不是第二套剧情事实：`auto` 采用两版共同可读的光影与动作语法；
  `both` 必须保持镜号、时长、台词/OS/OV/系统音、人物、空间、道具、轴线和终态一致，只允许调整光影精度、
  高光/黑位控制和动态复杂度措辞。共享镜头时长仍按15秒以内的跨版本安全上限执行。
- 台词、OS、OV、系统音按 `ref/kind/speaker/text` 逐字锁定；OS/OV/系统音无口型。系统音属于
  非实体声源，不进入可见人物锁；无源文不得新增人声。
- 每个主镜只服务一个 `narrative_beat_id`；回切、第二目标、第二独立动作链或容量不足时拆镜。
- Scene Lock 是空间、服装、道具活动区、光源与影调事实的唯一来源；后续阶段只消费，不重写。
- `full_prompt` 只写当前可见、可执行画面事实。QA、负面词、工程数据、风险与分析标签留在独立字段。
- 最终完整 Markdown 必须包含项目级 `## 制作质量总控` 和逐镜 `【本镜制作控制】`，把画面质感、光效与曝光、动态美学、表演与情绪、穿帮控制、抽卡策略、蒙太奇与剪辑转译为用户可见的执行摘要；不得只存在于 `qa_metadata`、validator 或 engineering 视图。
- `【本镜制作控制】` 不是第二套事实：七项中的可见执行事实必须逐项在 `【画面描述｜直接复制】` 获得语义落地；风险等级、人工检查、失败重试、后期和拆镜决定保留在制作控制。Export 生成逐项 grounding 报告，任一适用可见维度未落地即阻断。
- Master Production 内部按 `visual_bible → aesthetic_director → continuity_compiler → full_prompt`
  接力；这些是同一任务内字段，不是额外 Agent 阶段。
- 每场先冻结 `camera_variation_plan`，每镜选择一个有源文依据的构图骨架和一个运镜家族；
  连续三镜不得重复“景别+角度+构图+运镜”组合，除非明确是情绪冻结镜。
- 不得把固定机位、0.2米微推和微表情停顿当作默认模板；运镜必须由动作、视线交接、关系压力或空间揭示触发，并形成可见信息增量与稳定落幅。
- 每镜建立 `terminal_frame_contract`，并把最后20%的可见人数、固定槽位、脸/手/肢体分离、
  道具归属、支撑接触、摄影机停稳、光曝锁定和“不新增/不重复主体”编译进 `full_prompt`。
- 双人对峙、相见、肩后和正背镜把人物实际面向与摄影机可见面分开：分别写摄影机位置/方向、双方身体/胸口/脚尖面向目标、正面/背面/侧面可见和视线目标。`正面可见` 不等于 `面向镜头`，抽象 `对望/面对面` 不能替代双方相反朝向。
- 源文明示 POV、对镜口播或打破第四面墙时，允许双人关系中唯一一人直视镜头；必须点名人物、限定时间窗、写身体保持关系或可见转向，以及回看对手/保持直视到落幅的终态。其他人物保持场内视线，普通正反打不得使用该例外。
- 门口镜逐人绑定门槛内/外侧；回家/进门必须写门外起点、跨门槛中间态和屋内终点。前后景与画面占比只作软锚点，必须补共同地面、真实相对身高、允许遮挡部位和必须露出的脸/手/关键道具。儿童用头顶相对成人肩/胸位置锁定比例；同类道具以持有人加形状、颜色或内容物区分。
- 直投正文只由 `direct_prompt_compiler.py` 编译：保护源文与硬事实，只整句压缩，超过 700 字
  且无法无损压缩时阻断；导演卡使用同一事实源，最多 500 字、不设最低字数，不静默截断或用空话补齐。
- 复杂度和风险只改变批次与专项合同，不降低 direct-copy、连续性、口型、审美或导出门槛。
- 只有用户提供真实候选并明确要求视觉复核时才记录候选评分；不得用 Golden 或提示词推测成片。
- 成片复核必须同时检查动作语义、门槛拓扑、人物面向/视线、纵深比例/遮挡、构图运镜因果、光源连续、伪文字和音轨有效性；FFmpeg/FFprobe 技术指标通过不代表语义通过。
- 光影适配：`2.0` 使用简洁动机光、浅至中等阴影和清晰面部受光；`auto` 使用主受光面清晰、背光侧
  中等层次阴影的 dual-safe 规则；`2.5` 可表达更完整的动机光、中深明暗层次、局部环境色、稳定黑位和
  高光滚降。三者都禁止无来源的正面均匀补光。
- Windows 与 macOS 必须执行同一合同和验证门槛：状态写入使用跨平台锁，packet 中的本地命令使用
  当前 Python 解释器；真实视频校准统一使用 FFmpeg/FFprobe 指标后端，不得按平台跳过指标或降低阈值。
- Validate 通过后写入包含提示词包、配置、分镜计划、Editor 复审、审计产物和验证代码摘要的验证收据。
  Export 仅在全部摘要仍一致时复用该结果；旧运行、缺收据或任一输入/代码变化时自动执行原完整门禁。
  每份临时导出 Markdown 始终重新执行最终交付校验。

## 权威来源

- 机器阶段、版本、执行者、产物、超时与批次：`scripts/contract_registry.py`
- 路由上下文清单：`scripts/route_task.py`；说明版：`references/ROUTES.md`
- 字段与验证规则：`references/format_constraints.md`
- 低耗合同定位：`references/contracts/contract_index.md`
- 画面/连续性知识候选池：`references/production_quality_knowledge.md`
- 静态与动态美学：`references/contracts/aesthetic_directing_contract.md`
- 当前 Agent 指令：`references/dispatch/*.md`
- 增量校验与修复范围：`scripts/validate_main_shot_incremental.py`、`scripts/incremental_validation.py`
- 运行状态与门禁：`scripts/pipeline_state.py`、`scripts/pipeline_templates.py`

旧 Emotion、Camera、Director 或 Composer 独立阶段及其归档指针已从技能表面移除。当前只派发
`scene_lock/master_production/editor_pass2`；专业能力按风险进入 Master 字段，不恢复旧阶段。
历史 `composer` 脚本名与 `.cache/composer/` 路径仅是稳定产物接口，不表示存在独立 Composer Agent。

## 验证

修改技能后运行：

macOS 运行 `python3 scripts/run_regression_suite.py`；Windows 运行
`powershell -ExecutionPolicy Bypass -File scripts/run_skill_tool.ps1 scripts/run_regression_suite.py`。两端必须执行同一回归套件。

真实源文使用 `test_source_smoke.py`；真实已完成运行使用 `test_completed_e2e_run.py`；真实成片
A/B 只用 `validate_visual_ab_review.py`。benchmark fixture 只证明机制可复跑，不代表真实 SLO。

Windows 只把短参数与路径传给 `scripts/run_skill_tool.ps1`；macOS 使用当前 `python3` 解释器直接
运行脚本。两端都不要把 JSON、提示词或多行文本拼入 shell 命令。
