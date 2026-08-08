---
name: ai-video-agent-mode
description: >
  将剧本、分镜或场景转换为可直接投喂即梦 T2V 的提示词包，提供剧情节拍、表演、
  连续性、静态关键帧美学、动态运动美学、动作预算、风险审查与 Markdown/XLSX 导出。
  适用于剧本转 AI 视频提示词、即梦 T2V、跨镜连续、画面美术指导和低抽卡风险控制。
---

# AI Video Agent Mode

把源文转换为可审查、可恢复、可导出的即梦 T2V 提示词包。主流程生成提示词与制作元数据；
用户提供真实成片并明确要求复核时，才运行独立的视频指标或 A/B 校准。工程层不要求模型填写
自评分或逐字段证据抄录；可执行性由确定性 validator 和 Editor 语义复审共同判断。

## 最高优先级：模型创作主权

先读取 `references/creative_engineering_boundary.md`，并让它高于字段合同、验证规则、性能目标和导出便利性：

- 大模型负责剧情、潜台词、人物关系、情绪、表演、拆镜、调度、构图、运镜、光影、声音、语义精炼和审美复审。
- 工程代码只负责文件、Schema、计数、逐字事实、哈希、调度、恢复、排版和导出。
- 工程层只可拒绝能机械证明的不合法状态，例如缺字段、超时长、台词不一致、版本缺失或文件损坏；
  不得以“平淡、不够电影感、运镜不合理、Seedance不理解”等语义结论阻断创作。
- 需要改变语义时返回 `CREATIVE_REWRITE_REQUIRED`，由大模型在锁定事实内完成修订。
- 所有修改先说明根因和所有权；禁止按项目、角色、镜号或单次错误文本打补丁。

## 执行

1. 先读取创作/工程边界，再按平台运行路由：Windows 使用
   `powershell -ExecutionPolicy Bypass -File scripts/run_skill_tool.ps1 scripts/route_task.py <route> --run-dir <run_dir> --intent <intent>`；
   macOS 使用 `python3 scripts/route_task.py <route> --run-dir <run_dir> --intent <intent>`。
2. 只读取返回的 `context_plan.read_first`；只有当前错误或任务明确命中时，才读取
   `read_on_demand`。`run_only` 中的脚本直接运行，不预读源码。
3. 新任务默认使用 `full --intent new` 和新的空 `run_dir`。只有用户明确要求续跑时使用
   `full --intent resume`。完整配置与源文件已一次提供时，优先使用 `--auto-start`；它不得跳过
   任何阶段、provenance、validator 或导出门禁。
   相同源文和创作配置默认允许 `verified` 跨运行复用：只有源文 SHA-256、创作配置、Shot Plan、
   Scene Lock、提示词/管线/创作合同、逐镜输出哈希、Editor 全镜通过结果和最终验证回执全部一致时，
   才能原样复用模型创作，并为新运行写独立 reuse provenance；任一项变化立即回退模型创作。
   用户明确要求重新创作时设置 `reuse_policy=fresh`，不得用缓存覆盖新模型草案或 Editor 定点返修。
4. 配置确认后，只循环调用 `workflow_supervisor.py`。首次进入 Orchestrator 时，supervisor 只做源文
   快照和机械门禁；若返回 `creative_authoring_required`，主模型必须读取该请求和源文，创作
   `shot_plan.draft.json` 与 `scene_locks.draft.json` 后再继续调用 supervisor。前者负责全局导演蓝图，
   后者在同一次剧本理解中锁定场景空间、光源、影调、色卡和连续性。逐行 `source_ledger.json` 由工程根据源文快照自动生成；
   模型只在分镜草案中引用这些 ID，并自由决定节拍、拆镜和覆盖关系。
   先完成整集导演理解，再把两份草案作为首轮最终导演候选落盘；不要把粗稿留给 Editor 补写。按 request 的
   `checkpoint_policy.progress_command` 在每个已完成场景组后记录机械内容增长；这不是创意评分。
   `creative_authoring_stalled` 表示 5 分钟无首个内容检查点或已有进度后 3 分钟无增长，宿主必须报告并重启
   当前创作执行，不能静默等待。不得调用本地关键词分镜生成器代替模型创作。
   `waiting_for_workers` 是内部等待状态，只有路由明确返回 `needs_user_confirm=true` 时才提问；宿主必须
   每 10 秒或 worker 状态变化后立即继续轮询 supervisor，不能把等待状态当作静默暂停。
5. supervisor 返回 `host_dispatch_required` 时，按 `references/agent_protocol.md` 处理 `worker_leases`：
   每个租约只 spawn 一个长驻 Agent，先登记全部 packet；每个 packet 真正开始前再启动其绝对计时并记录存活心跳。
   在每个主镜/Editor 场景窗口完成后原子落盘当前集合、记录内容进度，
   等待完整 batch、记录 provenance，然后立即继续 supervisor。普通心跳不能代替内容增长：5 分钟无首个
   非空检查点或已有产出后 3 分钟无增长时定点重派。
   packet 的绝对超时不会被心跳延长；到期后必须中断旧 worker，并使用 supervisor 生成的新 UUID packet
   重派。初始尝试加两次重派仍失败时立即熔断并报告。
6. Agent 只能写 `packet._batch_output_path`。Master Production 必须把每个主镜第一次落盘内容作为可直接交付
   的最终候选，并在内部完成自由导演自审，不输出自评分或逐字段证据。每完成一个主镜运行 packet 的
   `checkpoint_command_template`，在同一次确定性调用中完成字段校验与内容进度记录；批次结束仍运行完整
   `local_validation_command`。
   合并必须使用 provenance 门禁。局部失败按 `字段 → 主镜 → pair/window → scene` 升级，合格主镜可由
   partial provenance 保留，未解决主镜自动定点重试；确定性字段错误按机械范围修正，无法归属镜头的全局
   合同错误禁止 partial 复用。任何增量通过都不能替代最终全量 Validate。
7. Editor 只做独立验收：失败时输出 `creative_cause`、`affected_shot_ids` 和模型决定的
   `return_to_phase: orchestrator | master_production`，不得返回替代提示词或字段补丁。全局理解问题重新创作
   Director Blueprint，单镜实现问题由 Master 整镜重做；工程只按模型显式路由。同一责任阶段与同一
   `creative_cause` 最多重写两轮，第三次立即熔断。Editor 按连续场景窗口复审，输出的
   `reviewed_shot_ids` 必须逐字覆盖输入 `shot_ids`，最终覆盖全集后才允许 Validate。
8. Validate 全部通过后，才调用 `export_with_validation.py` 写入配置中已确认的交付路径；导出目标由确认过的
   `seedance_target: auto | 2.0 | 2.5 | both` 决定。`auto` 生成一份 dual-safe 文件，`2.0`/`2.5`
   生成单一优化文件，`both` 从同一份合同原子生成两份可独立投喂 Markdown 和一个非投喂索引。
9. 从首次初始化运行状态起计算 90 分钟硬截止。超过截止必须立即停止；预测门禁只允许机器合同声明的
   120 秒调度不确定性带，它不得延长硬截止。按剩余未验证批次、最多三个 worker 和阶段预算确认已无法
   按时完成时，停止派发，写 `.cache/control/fuse_report.json` 并向用户报告；禁止静默续跑。最终 Export
   验证通过后必须持久化 `pipeline_status=completed`，耗时使用最终阶段真实完成时间，不使用后续查询时间。
10. Validate 通过后调用 `verified_reuse.py publish` 登记当前运行。复用索引使用独立于交付目录的稳定缓存根，
    只保存哈希、路径和验证身份；发布失败会阻断 Validate，不能静默失去后续复用。
    不改写提示词；阶段报告必须分别记录状态初始化后的管线墙钟、至少一个 worker 活跃的并集时间、Agent
    阶段空转时间、复用阶段数和复用条目数。真实端到端基准另记配置确认与进程启动在内的外部墙钟；
    后续 worker 注册不得覆盖阶段首次启动时间。

## 上下文预算

正常运行不得预读完整的 `references/format_constraints.md` 或
`references/production_quality_knowledge.md`。阶段约束已由 `dispatch_cache.py` 选择并写入
`packet.constraints_path`，Master Production 的锁定字段已写入 scaffold。

| 情况 | 最小读取 |
|---|---|
| 新运行 | route 输出、`stage_gates.md` |
| 续跑 | route 输出、`.cache/pipeline_state.json` 与当前阶段已验证产物 |
| Agent 派发 | packet、`constraints_path`、对应 scaffold/cache、`agent_protocol.md` |
| 单镜修复 | packet、`retry_context_path`、validator 点名字段 |
| 审查 | 先运行 validator；再按 `contracts/contract_index.md` 读取命中的一个合同切片 |
| 导出 | 直接运行导出脚本；仅在诊断格式时读取 `export_spec.md` |
| 修改技能合同 | 才读取完整字段合同、知识库、schema、validator、Golden 与一致性检查 |

不得为“更保险”同时加载全部合同。先依赖结构化 packet、scaffold、stage summary 和 validator；
只有这些信息不足以解释一个具体失败时，再打开对应权威段落。

## 不可破坏约束

- 仅支持即梦 `t2v`。禁止 I2V、R2V、参考素材槽位或动作素材路径；三状态关键帧只是前期参考。
- `seedance_target` 只由工程层记录和选择输出文件。模型直接创作目标版本的 `seedance_prompt`；`both`
  由模型分别创作 `seedance_prompt_variants["2.0"]` 与 `["2.5"]`。工程层不得推导版本差异、改写光影或拼接动作语句。
- 台词、OS、OV、系统音按 `ref/kind/speaker/text` 逐字锁定；OS/OV/系统音无口型。系统音属于
  非实体声源，不进入可见人物锁；无源文不得新增人声。
- 一个主镜可承载一个或多个戏剧节拍，一个源文单元可跨镜复用。是否回切、重复、蒙太奇、拆镜或长镜头
  由大模型根据观众感受和 Seedance 表达决定；工程只检查总时长与引用存在。
- Scene Lock 与 `scene_tone_palette` 都是模型创作资产。工程只冻结文件版本并提供差异事实；Master 和 Editor
  负责判断每镜如何继承、变化和最终呈现，工程不得把场景色卡复制成不可改写的镜头语义。
- `full_prompt` 只写当前可见、可执行画面事实。QA、负面词、工程数据、风险与分析标签留在独立字段。
- 生产脚本不得按固定镜号、角色名、项目文件名或某一剧情道具执行定点分支；实体、场景、光源和活动道具从当前源文、配置与 Scene Lock 开放提取。测试夹具可使用虚构样例，但不得进入路由或运行时判断。
- 最终 Markdown 原样排版模型创作的 Seedance 提示词、导演卡、负面词与逐字台词。制作质量总结如需交付，
  也必须来自模型 Editor；Export 不生成 grounding 报告，不靠关键词判断创作意图是否已经“落地”。
- 模型可自由决定创作过程、分析维度和表达结构，包括是否使用 `visual_bible`、三状态关键帧、
  终帧合同、摄影变化计划、重复构图、固定机位或复杂运动。双人关系、门槛拓扑、人物比例、道具接触等
  专业知识是模型可调用的导演工具，不是工程模板或字段配额；是否采用及如何表达由剧情、情绪、观众感受、
  Seedance 能力和最终审美共同决定。
- `seedance_prompt` 与 `director_card` 都由模型完整创作。Export 只原样选择字段、计算字符数和排版；超过
  700/500 字或字段缺失时返回 `CREATIVE_REWRITE_REQUIRED`，不得组装、去重、截断、删句或补写。
- 批次只按条目数、显式连续链 ID 和实际上下文大小划分；工程代码不得从剧情词语推断镜头复杂度、
  风险类型或应采用的专项创作合同。
- 模型创作对象通过 Orchestrator、packet、scaffold 和 Editor 上下文时必须完整透传，包括未来新增的未知字段；
  工程不得用字段白名单压缩创作上下文，也不得自动注入 `editorial_mode`、节拍归属或镜头组织方式。
- 只有用户提供真实候选并明确要求视觉复核时才记录候选评分；不得用 Golden 或提示词推测成片。
- 成片复核必须同时检查动作语义、门槛拓扑、人物面向/视线、纵深比例/遮挡、构图运镜因果、光源连续、伪文字和音轨有效性；FFmpeg/FFprobe 技术指标通过不代表语义通过。
- Seedance 版本的摄影、光影、动作复杂度和表达方式由模型结合当前平台能力进行语义编译和最终审美判断；
  工程配置只声明目标版本，不携带创作模板。
- Windows 与 macOS 必须执行同一合同和验证门槛：状态写入使用跨平台锁，packet 中的本地命令使用
  当前 Python 解释器；真实视频校准统一使用 FFmpeg/FFprobe 指标后端，不得按平台跳过指标或降低阈值。
- Validate 通过后写入包含提示词包、配置、分镜计划、Editor 复审、审计产物和验证代码摘要的验证收据。
  Export 仅在全部摘要仍一致时复用该结果；旧运行、缺收据或任一输入/代码变化时自动执行原完整门禁。
  每份临时导出 Markdown 始终重新执行最终交付校验。

## 权威来源

- 机器阶段、版本、执行者、产物、超时与批次：`scripts/contract_registry.py`
- 创作/工程所有权：`references/creative_engineering_boundary.md`、`scripts/creative_engineering_boundary.py`
- 路由上下文清单：`scripts/route_task.py`；说明版：`references/ROUTES.md`
- 字段与验证规则：`references/format_constraints.md`
- 低耗合同定位：`references/contracts/contract_index.md`
- 画面/连续性知识候选池：`references/production_quality_knowledge.md`
- 静态与动态美学：`references/contracts/aesthetic_directing_contract.md`
- 当前 Agent 指令：`references/dispatch/*.md`
- 增量校验与修复范围：`scripts/validate_main_shot_incremental.py`、`scripts/incremental_validation.py`
- 运行状态与门禁：`scripts/pipeline_state.py`、`scripts/pipeline_templates.py`

当前只派发 `master_production/editor_pass2`；全局导演模型一次创作分镜与 Scene Lock，专业能力由模型按剧情需要自由调用。
`.cache/composer/` 只是稳定产物接口，不表示存在独立 Composer Agent。

## 验证

修改技能后运行：

macOS 运行 `python3 scripts/run_regression_suite.py`；Windows 运行
`powershell -ExecutionPolicy Bypass -File scripts/run_skill_tool.ps1 scripts/run_regression_suite.py`。两端必须执行同一回归套件。

真实源文使用 `test_source_smoke.py`；真实已完成运行使用 `test_completed_e2e_run.py`；真实成片
A/B 只用 `validate_visual_ab_review.py`。benchmark fixture 只证明机制可复跑，不代表真实 SLO。

Windows 只把短参数与路径传给 `scripts/run_skill_tool.ps1`；macOS 使用当前 `python3` 解释器直接
运行脚本。两端都不要把 JSON、提示词或多行文本拼入 shell 命令。
