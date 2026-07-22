# Runbook — AI Video Agent Mode Pipeline

本文件定义完整管线操作流程。启动新项目前必须加载。

## Phase 0: 用户确认（逐项向导）

手动再次调用技能默认是一次新的 `full/new` 交付，而不是把上一次不满意的缓存清空后重跑。保留旧 `run_dir` 作审计，创建新的空 `run_dir`；只有用户明确要求继续、审查、导出或单镜修复时才复用已确认的旧运行。

先运行 `route_task.py full --run-dir <new_run_dir> --intent new`。它只能返回第一项 `export_base`。得到该路径前不得创建项目文件；路径确认后运行 `configuration_wizard.py start --run-dir <new_run_dir> --export-base <export_base>`。之后每一轮只展示向导返回的 1–2 项，记录用户本轮答案，再询问下一轮：

1. `export_base`
2. `canvas` + `visual_style`
3. `max_shot_duration` + `target_platform`
4. 文本生成视频 / 图片生成视频 / 参考视频生成视频 + 是否启用原生音频
5. `generation_control.reference_assets` + `storyboard_grid.enabled`

不得把所有基础配置合并成一条问题，也不得因为模板已有默认值跳过任一项。用户答完当前轮才可执行下一轮。最后一轮由向导写入 `confirmation.confirmed_at`、完整 `confirmed_fields`、`confirmed_values` 和 `confirmed_values_sha256`；任一确认值被修改时必须回到对应小批次重新确认。在此之前 `pipeline_runner.py` 必须返回 `needs_user_confirm`。

硬性要求：

- 每次 `full/new` 必须重新询问输出位置。`export/reexport` 仅重新确认本次 Markdown 导出路径；`audit/compose/single-repair/resume` 不重复询问已确认的基础配置。
- 禁止默认当前目录、工作区目录、源文件目录、上次使用目录或自动生成目录。
- 用户只说“随便”“你定”“默认”时不能继续，必须请用户给出明确路径。
- `project_config.json` 的 `export_base` 必须写入用户本次确认的路径。
- 本技能的所有中间 JSON、`.cache`、handoff、review、dispatch、composer、analysis、director、continuity 输出都必须位于用户确认的 `export_base` 下的 `run_dir` 内；`run_dir` 必须是 `export_base` 下的一个项目运行目录，禁止把运行目录建到工作区、源文件目录或临时目录。
- 导出脚本必须使用用户本次确认的 Markdown 输出路径；不得调用会自动推断输出位置的命令。
- Composer、Editor Pass 1、Editor Pass 2、Validate 必须按队列顺序执行；已有旧缓存、旧输出或历史成功状态不构成跳过依据，任一环节未通过都必须停在当前队列，不得直接跳到导出。
- Validate 阶段必须读取并通过 `.cache/review/llm_gate_result.json`；没有 editor_pass2 的复审结果时，validate 视为未完成。

## 管线执行顺序

| Phase | 名称 | 类型 | 并行 | 超时 | 重试 |
|-------|------|------|------|------|------|
| 0 | 用户确认 | 主Agent | - | - | 0 |
| 0.5 | 源规则检测 | 本地脚本+人工核验 | - | - | 0 |
| 1 | Orchestrator | 主Agent | - | - | 0 |
| 1.5/1.6 | 主镜头合并与空间注册 | 本地脚本 | - | - | 0 |
| 2a | 情绪分析 | 子Agent | 与2b并行 | 15min | 初次+最多2次重试 |
| 2b | 场景分析 | 子Agent | 与2a并行 | 15min | 初次+最多2次重试 |
| 2c | 镜头运镜 | 子Agent | 在2a通过后 | 15min | 初次+最多2次重试 |
| 2.5/3 | 三路整合与Director验证 | 本地handler/门禁 | - | - | 0 |
| 5 | 连续性检查 | 本地脚本 | - | - | 0 |
| 6 | Prompt Composer | 子Agent | - | 15min | 初次+最多2次重试 |
| 6a/6b/6c | 合并、运镜诊断与归一化 | 本地脚本 | - | - | 0 |
| 7 | Editor Pass 1 | 本地确定性 QA + 自动精准修复路由 | - | - | 1轮精准修复 |
| 8 | Editor Pass 2 | LLM 语义 QA + 修复路由 | - | 10min | 初次+最多2次重试 |
| 8.5 | 九宫格剧情包（可选） | 本地派生脚本 | - | - | 0 |
| 9 | 最终验证 | 脚本+LLM混合门禁 | - | - | 0 |
| 10 | 导出 | 本地脚本 | - | - | 0 |

## 子Agent派发边界

只允许以下阶段派发子Agent：

- `emotion_analysis`
- `scene_analysis`
- `camera_movement`
- `prompt_composer`
- `editor_pass2`

以下阶段必须由主Agent或本地脚本/handler执行，不得 spawn 子Agent：

- `user_confirm`
- `orchestrator`
- `qa_integration`
- `director`
- `continuity`
- `editor_pass1`
- `validate`
- `export`

Phase 2a 情绪与 2b 场景可并行派发；2c 运镜必须在情绪产物已通过后再派发，因为它要读取 `performance_chain` 决定景别、反打、移镜与落幅。禁止依赖 `pipeline_runner.py` 的 `batch_spawn` 作为真实派发动作。使用阶段专属批量和超时：

| Phase | 单批上限 | wait_agent 超时 |
|-------|----------|-----------------|
| emotion_analysis | 20 | 900s |
| scene_analysis | 24 | 900s |
| camera_movement | 24 | 900s |
| prompt_composer | 6 | 900s |

第三次超时或第三次校验失败后不得强制推进；必须 blocking 并等待用户或人工确认处理。

## 关键变化

1. Phase 2a/2b 通过独立 dispatch packet 并行下发；Phase 2c 在已验证的情绪链基础上单独下发
2. 子 Agent 超时自动重派，最多2次重试；连续失败后 blocking 等用户确认
3. 增量重试：只传失败子镜头 + 当前仍失败的问题
4. 100% 通过率门禁：不允许带问题推进
5. 插件式处理器注册：新增分析阶段不需要改核心文件
6. 混合门禁：脚本负责机械违规，LLM负责语义穿帮与表演合理性

## 混合门禁数据流

```
gate_check.py / hybrid_gate.py
  ├─ validate_prompt_package.py：台词边界、OV/OS口型、full_prompt长度
  ├─ continuity_check.py：相邻镜头越轴、空间跳变
  ├─ enhance_performance.py：景别可见性、表演细节风险
  └─ 生成 .cache/review/llm_gate_review.md

Editor/QA LLM
  └─ 写入 .cache/review/llm_gate_result.json
      ├─ pass: true/false
      ├─ blocking: [...]
      ├─ warnings: [...]
      └─ repair_targets: [{subshot_id, send_back_to, reason}]
```

LLM 复审必须基于脚本输出和原始 shot_plan/director/prompt 文件。不得在 LLM 审查阶段新增台词或直接改写最终包；只输出审查结果和退回目标。确定性 QA 先自动为失败子镜生成 Composer 精准修复 packet；语义 QA 的 repair_targets 按职责退回 emotion/scene/camera/Composer，修复合并后必须从确定性 QA 重新开始，不得跳过第二次审查。

## 可选九宫格剧情包

Phase 0 必须记录 `storyboard_grid.enabled`。用户明确不需要时设为 `false`；状态机直接跳过 `grid_storyboard`，不得创建 `.cache/grid_storyboard/`、不得向 Markdown/XLSX 增加九宫格内容、不得改变 `generation_control.mode`。

启用时，`grid_storyboard` 位于 `editor_pass2` 与 `validate` 之间，读取已通过语义复审的提示词包、shot plan、director 输出和三份合同。它按连续主镜自动筛选值得视觉预演的链，输出 `.cache/grid_storyboard/packages.json`。该阶段不投喂视频模型、不产生图片、不要求用户回传图片；最终导出仅追加九宫格总图生图提示词、负面词和 P01-P09 节拍。

如果脚本门禁已经存在 blocking，先修脚本问题，不启动 LLM 语义复审。只有脚本 blocking 清零后，LLM 才审查空间观感、表演合理性、角色动机和多镜头情绪连续性。

## 前置门禁

Phase 2a/2b/2c 派发前必须先运行 `preflight_check.py`。它检查：

- `subshot_id` 是否缺失或重复
- `base_action` / `characters` 是否缺失或是否有可替代的非人物镜头说明
- `dialogue_refs` 是否都存在于 `dialogue_map`
- 对话和动作时长是否足够

`characters` 允许为空，但仅限明确的非人物镜头：空镜、背景、环境、物件/道具特写、插入镜头、转场镜头。此类镜头应在 `shot_type` / `visual_type` / `purpose` 或 `base_action` 中明确写出 `empty/background/object/environment/establishing/transition` 或中文等价描述。含 `dialogue_refs` 或明显人物动作的镜头仍必须填写 characters。

`base_action` 也允许为空，但仅限 `non_character_confirmed=true` 的无人物、无台词、无动作非动作镜头，例如纯空镜、纯环境、黑场、静帧、物件插入。此类镜头必须提供 `visual_intent` / `image_subject` / `atmosphere` 之一，让下游知道要渲染什么。有人物或台词的镜头仍必须填写 `base_action`。

preflight 有 blocking 时，不派发 emotion/scene/camera 子Agent，先回到 Orchestrator 修复 shot_plan。

## 落盘节流执行规则

为减少重复上下文、token 消耗和 Windows PowerShell 行内命令长度风险，派发子Agent时必须使用 `dispatch_cache.py` 当次返回的 `.cache/dispatch/*_{dispatch8}_packet.json` 与对应唯一 sidecar 文件：

- 主 Agent 调用 `dispatch_cache.py` 生成 `dispatch_packets`，每个 batch 一个 packet。
- Composer 未显式传 `batch_size` 时把普通镜自适应平衡为4–6个 subshot/批；同一主镜、显式连续互动链或打斗 sequence 不拆开。高演绎、多人关系和复杂连续链保持小批，可用槽位允许时批次并行。
- 批次以复杂度预算而非纯数量切分：普通动作镜保持原有基准规模；对白、多人、`motivated_sequence` 自动缩小；已确认的环境/物件镜可在不跳过任何场景、镜头、Composer 或 QA 门禁的前提下合并更多项。
- 环境/物件镜不调用人物情绪 Agent，但仍调用场景与镜头 Agent，并继续经过 Composer、连续性、双层 QA、最终验证和导出门禁。任何生成模型都不得跳过质量合同或门禁。
- 每组 packet 同目录生成带 dispatch group 后缀的唯一 `*_constraints.md`，保存该阶段必须遵守的格式约束快照。
- Composer 每组 dispatch 同时生成 `*_scene_locks.json`，每批生成 `*_scaffold.json`；Agent 从骨架开始，只填写四段提示词和语义 QA，不改写锁定字段。
- `send_back` 重试时 packet 只包含仍失败的子镜头，并重新运行 `dispatch_cache.py` 取得新 packet/batch 路径；禁止覆盖旧 baseline。
- 主Agent给子Agent的消息只应包含：技能名、packet 路径、constraints 路径、`_batch_output_path`、批次范围、当前失败原因。
- spawn 返回 Agent ID 后立即运行 `register_dispatch_agent.py <packet> <agent_id>`；多批并行时每个 packet 分别注册，禁止只保存 Phase 级最后一个 Agent ID。
- 子Agent必须从 `packet.items`、scaffold、scene lock、handoff 与 `constraints_path` 完成当前批次；`source_path` 仅在这些紧凑输入无法回答某个具体字段时按需读取，禁止默认加载完整源文件。仍须写入 packet 的 `_batch_output_path`。
- 子Agent禁止写公共 `output_path`；公共输出只由主 Agent 合并脚本写入。
- 已通过镜头不再重复发送；只允许读取 `.cache/handoff/{role}_handoff.json` 中的短摘要恢复连续性。
- 每个通过阶段在 `.cache/stage_summary/<phase>.json` 写入 elapsed/retry/timeout 数据。使用真实项目后以这些数据调节复杂度预算，不以主观估计增加复杂镜批量。
- Composer batch 完成后立即运行校验；失败时调用 `prepare_composer_retry.py <run_dir> <batch>`。脚本封存失败哈希，为同批通过镜记录 partial provenance，只生成失败镜的新 packet；封存后的原 batch 不得原地修改或重新签名，合并时只由新 batch 局部替换同名 `subshot_id`。
- 禁止把完整 `shot_plan.json`、完整 `format_constraints.md`、完整负面提示词库或大段脚本内容放进 `powershell -Command` / `pwsh -Command` / `python -c` / `node -e` 的行内字符串；需要执行的内容必须先落盘为脚本或 packet，再以文件路径调用。
- Windows / PowerShell 环境执行脚本时优先使用 `py -3` 或已知解释器绝对路径；同样只传文件路径，不把 packet、JSON、Markdown、constraints 或 review sidecar 直接塞进命令行。

推荐派发文本格式：

```text
请读取 dispatch packet：<dispatch_cache.py 当次返回的完整路径>
请读取 constraints sidecar：<packet.constraints_path>
只处理 packet.items 中列出的子镜头，输出写入 packet._batch_output_path。
不要在回复中粘贴完整 shot_plan 或已通过镜头，只报告写入完成和关键阻塞问题。
```

## 增量重试数据流

```
主Agent收到 failed 动作
  └─ 管线引擎标记通过的子镜头为 passed
  └─ get_failed_subshots() 只返回仍失败的子镜头
  └─ 每个失败子镜头附带 `.cache/handoff/*_handoff.json` 中的恢复摘要
  └─ send_back 动作只包含失败子镜头（含修正信息 + handoff）
  └─ 子Agent只收到需要修正的部分
```

## Handoff 恢复记忆数据流

```
子Agent输出 JSON
  └─ agent_handoff.py 从输出提取 per-subshot 摘要
      └─ 写入 .cache/handoff/{role}_handoff.json

失败/超时/recover
  └─ get_failed_subshots(role)
      └─ 返回 subshot_id + issues + handoff
          └─ 新Agent基于 handoff 恢复决策上下文
```

handoff 只保存决策摘要、连续性锚点、不可改边界，不保存大段完整提示词。正式内容仍以 `shot_plan.json`、三路 analysis JSON、`director_pass.json`、`.cache/composer/merged.prompt_package.json` 为准。
