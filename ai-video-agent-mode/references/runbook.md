# Runbook — AI Video Agent Mode Pipeline

本文件定义完整管线操作流程。启动新项目前必须加载。

## Phase 0: 用户确认（每次启动必走）

主 Agent 必须先询问用户本次输出文件位置/输出目录，并等待用户给出明确路径后才能创建 `project_config.json` 或任何项目文件。

硬性要求：

- 每次新项目、重新导出、继续旧项目但要生成新交付物时，都必须重新询问输出位置。
- 禁止默认当前目录、工作区目录、源文件目录、上次使用目录或自动生成目录。
- 用户只说“随便”“你定”“默认”时不能继续，必须请用户给出明确路径。
- `project_config.json` 的 `export_base` 必须写入用户本次确认的路径。
- 导出脚本必须使用用户本次确认的 Markdown 输出路径；不得调用会自动推断输出位置的命令。

## 管线执行顺序

| Phase | 名称 | 类型 | 并行 | 超时 | 重试 |
|-------|------|------|------|------|------|
| 0 | 用户确认 | 主Agent | - | - | 0 |
| 1 | Orchestrator | 主Agent | - | - | 0 |
| 2a | 情绪分析 | 子Agent | 与2b/2c并行 | 5min | 4次 |
| 2b | 场景分析 | 子Agent | 与2a/2c并行 | 5min | 4次 |
| 2c | 镜头运镜 | 子Agent | 与2a/2b并行 | 5min | 4次 |
| 3 | QA/整合 | 本地handler | - | - | 0 |
| 4 | Director验证 | 门禁 | - | - | 4次 |
| 5 | 连续性检查 | 本地脚本 | - | - | 0 |
| 6 | Prompt Composer | 子Agent | - | 5min | 4次 |
| 6b | 运镜强制注入 | 本地脚本（强制） | - | - | 0 |
| 7 | Editor Pass 1 | 本地合并 | - | - | 0 |
| 8 | Editor Pass 2 | 脚本+LLM混合门禁 | - | - | 0 |
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

Phase 2a/2b/2c 必须由主 Agent 显式创建 dispatch packets，并通过正式子 Agent 工具并行派发。禁止依赖 `pipeline_runner.py` 的 `batch_spawn` 作为真实派发动作。使用阶段专属批量和超时：

| Phase | 单批上限 | wait_agent 超时 |
|-------|----------|-----------------|
| emotion_analysis | 15 | 900s |
| scene_analysis | 20 | 600s |
| camera_movement | 25 | 600s |

超时三次后不得强制推进；必须 blocking 并等待用户或人工确认处理。

## 关键变化

1. Phase 2a/2b/2c 通过独立 dispatch packet 并行下发
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

LLM 复审必须基于脚本输出和原始 shot_plan/director/prompt 文件。不得在 LLM 审查阶段新增台词或直接改写最终包；只输出审查结果和退回目标。

如果脚本门禁已经存在 blocking，先修脚本问题，不启动 LLM 语义复审。只有脚本 blocking 清零后，LLM 才审查空间观感、表演合理性、角色动机和多镜头情绪连续性。

## 前置门禁

Phase 2a/2b/2c 派发前必须先运行 `preflight_check.py`。它检查：

- `subshot_id` 是否缺失或重复
- `base_action` / `characters` 是否缺失或是否有可替代的非人物镜头说明
- `dialogue_refs` 是否都存在于 `dialogue_map`
- 对话和动作时长是否足够

`characters` 允许为空，但仅限明确的非人物镜头：空镜、背景、环境、物件/道具特写、插入镜头、转场镜头。此类镜头应在 `shot_type` / `visual_type` / `purpose` 或 `base_action` 中明确写出 `empty/background/object/environment/establishing/transition` 或中文等价描述。含 `dialogue_refs` 或明显人物动作的镜头仍必须填写 characters。

`base_action` 也允许为空，但仅限无人物、无台词、无动作的非动作镜头，例如纯空镜、纯环境、黑场、静帧、物件插入。此类镜头必须提供 `visual_intent` / `image_subject` / `atmosphere` 之一，让下游知道要渲染什么。有人物或台词的镜头仍必须填写 `base_action`。

preflight 有 blocking 时，不派发 emotion/scene/camera 子Agent，先回到 Orchestrator 修复 shot_plan。

## 落盘节流执行规则

为减少重复上下文、token 消耗和 Windows PowerShell 行内命令长度风险，派发子Agent时必须使用 `dispatch_cache.py` 当次返回的 `.cache/dispatch/*_{dispatch8}_packet.json` 与对应唯一 sidecar 文件：

- 主 Agent 调用 `dispatch_cache.py` 生成 `dispatch_packets`，每个 batch 一个 packet。
- Composer 未显式传 `batch_size` 时把普通镜自适应平衡为2–4个 subshot/批，避免4+1尾批；同一主镜、显式连续互动链或打斗 sequence 不拆开，可用槽位允许时批次并行。
- 每组 packet 同目录生成带 dispatch group 后缀的唯一 `*_constraints.md`，保存该阶段必须遵守的格式约束快照。
- Composer 每组 dispatch 同时生成 `*_scene_locks.json`，每批生成 `*_scaffold.json`；Agent 从骨架开始，只填写四段提示词和语义 QA，不改写锁定字段。
- `send_back` 重试时 packet 只包含仍失败的子镜头，并重新运行 `dispatch_cache.py` 取得新 packet/batch 路径；禁止覆盖旧 baseline。
- 主Agent给子Agent的消息只应包含：技能名、packet 路径、constraints 路径、`_batch_output_path`、批次范围、当前失败原因。
- spawn 返回 Agent ID 后立即运行 `register_dispatch_agent.py <packet> <agent_id>`；多批并行时每个 packet 分别注册，禁止只保存 Phase 级最后一个 Agent ID。
- 子Agent必须从 packet 的 `source_path` 读取完整上下文，从 packet 的 `constraints_path` 读取完整约束，从 `items` 确定本批处理范围，并写入 packet 的 `_batch_output_path`。
- 子Agent禁止写公共 `output_path`；公共输出只由主 Agent 合并脚本写入。
- 已通过镜头不再重复发送；只允许读取 `.cache/handoff/{role}_handoff.json` 中的短摘要恢复连续性。
- Composer batch 完成后立即运行校验；失败时调用 `prepare_composer_retry.py <run_dir> <batch>`。脚本封存失败哈希，为同批通过镜记录 partial provenance，只生成失败镜的新 packet；封存后的原 batch 不得原地修改或重新签名，合并时只由新 batch 局部替换同名 `subshot_id`。
- 禁止把完整 `shot_plan.json`、完整 `format_constraints.md`、完整负面提示词库或大段脚本内容放进 `powershell -Command` / `pwsh -Command` / `python -c` / `node -e` 的行内字符串；需要执行的内容必须先落盘为脚本或 packet，再以文件路径调用。

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
