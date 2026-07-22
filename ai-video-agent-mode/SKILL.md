---
name: ai-video-agent-mode
description: >
  Contract-driven multi-agent pipeline for converting scripts, storyboards, scenes, keyframes, or
  nine-panel plans into production-ready AI video prompt packages with low reroll
  risk, high-performance tension, action budgets, character priority, multimodal
  T2V/I2V/R2V controls, continuity, semantic review, and validated Markdown/XLSX
  export. Use for agent模式、多agent、剧本转AI视频提示词、专业分镜提示词、降低抽卡率、
  表演增强、关键帧提示词、九宫格剧情分镜图、Seedance/即梦视频生成。
---

# AI Video Agent Mode — Mode C v4

把剧本、分镜或场景素材转换为“模型可执行、跨镜连续、表演有张力、低抽卡”的 AI 视频提示词包。核心方法是合同驱动生成：先建立表演张力、跨镜连续和抽卡风险控制，再写模型提示词。所有字段、模型提示词、动作预算和门禁以 `references/format_constraints.md` 为唯一权威契约。

## 0. 运行铁律

1. 用户再次手动调用本技能时，默认按 `full/new` 处理：创建全新的 `run_dir`，不得清空、覆盖、读取或合并上次运行的缓存；旧运行只保留作审计。只有用户明确说“继续/续跑、审查、导出、单镜修复”时，才允许对应窄路线复用已确认的运行。`full/new` 若指向已有 `project_config.json` 或 `.cache` 的目录必须阻断，要求选择新的 `run_dir`。
2. Phase 0 必须使用 `scripts/resolve_run_mode.py` 和 `scripts/configuration_wizard.py` 逐轮确认基础配置，绝不一次性列出整张配置问卷：第一轮只问 `export_base`；随后每轮只问 1–2 项，固定顺序为“画幅+视觉风格 → 最大时长+目标平台 → 文本/图片/参考视频生成方式+原生音频 → 参考资产+九宫格开关”。用户答完本轮后才提问下一轮。面向用户只使用中文生成方式，向导再确定性写入内部 `t2v/i2v/r2v`。仅当所有字段、确认时间、确认值快照和快照哈希已写入 `project_config.json.confirmation` 时才可启动拆镜。`run_dir` 必须创建在已确认 `export_base` 下，所有 `.json`、`.cache`、dispatch、review、analysis、director、composer 中间文件都随该新 `run_dir` 落盘。
3. 用户明确“不需要九宫格”时，`storyboard_grid.enabled=false`，状态机必须跳过九宫格判断、缓存和导出；未提供资产时不得伪造路径，九宫格开关不得改变当前 `t2v/i2v/r2v` 模式。
4. 派发子 Agent 前运行 `dispatch_cache.py`。spawn 文本只传 packet、constraints、Composer scaffold、scene-lock cache 路径和简短指令。
5. 子 Agent 只写 packet 的 `_batch_output_path`；公共文件由主 Agent 合并。每次初派或重派必须使用 `dispatch_cache.py` 新返回的唯一 packet/batch 路径；禁止复用或覆盖已经验证的 batch。
6. 每次 spawn 返回真实 Agent ID 后，立即运行 `register_dispatch_agent.py <packet> <agent_id>`；Agent 完成后运行 `record_batch_provenance.py <packet>`。只有逐 dispatch 的 agent_id/spawn_time、输出时序、Phase 校验和 SHA-256 全部通过的 batch 才能使用。公共合并必须加 `--require-provenance`。
7. 目标文件存在且 JSON 可解析才算 Agent 完成；不要关闭 running Agent。
8. Phase 2、Phase 6、Phase 8 的语义产出必须由 Agent 完成；格式归一化、合并和验证优先使用脚本。
9. 台词、OV、OS 按 `引用ID—类型—人物—原文` 确定性锁定，逐字逐标点保留；语气、停顿和情绪只写在独立控制字段，不得改写原文。OV/OS 无口型同步；无原文时禁止新增台词、旁白或内心声。
10. 失败阶段必须修复或重派，不能跳过门禁。
11. Composer dispatch 的 constraints sidecar 必须含可迁移的强示例规则；只有当前 packet 缺少某个必要模式时才按需读取 `references/format_example.txt` 或 `references/quality_exemplar/S2-03_high_quality_example.txt`，禁止每批重复全量加载。
12. `full_prompt` 只允许模型可执行内容。工程字段、QA 结论、戏剧分析、负面词和迁移说明必须放在独立 JSON 字段。
13. 恢复旧项目时重新运行 `dispatch_cache.py`；只接受 `contract_version=modec-v4` 的 packet，禁止复用 v4 之前生成的 packet、constraints sidecar 或仍持有旧规则上下文的 Agent。
14. 人物镜必须先完成三份合同再写提示词：`qa_metadata.performance_contract` 绑定表情、身体动作、视线、反应延迟、观众共情锚点、画面可读瞬间、运镜压力、场景压力和落幅残留；`qa_metadata.continuity_contract` 绑定起止状态、位置、视线、道具、光源和下一镜承接；`qa_metadata.reroll_control` 评估 T2V/I2V/R2V 抽卡风险和参考资产需求。缺任一合同不得进入导出。
15. 本技能所有本地命令统一优先使用 `python3`；脚本内部调用其他 Python 脚本时必须使用 `sys.executable`，禁止硬编码 `python`，避免 macOS 环境中先失败再回退。Windows 环境如无 `python3`，优先使用 `py -3` 或已知解释器绝对路径，不要依赖 PowerShell 别名猜测。
16. Composer、Editor Pass 1、Editor Pass 2、Validate 是严格队列中的必经环节；已存在旧输出或缓存不代表可以跳过其中任何一步，缺任一环节或门禁未通过时，禁止直接进入导出。
17. 示例只提供可迁移的生成方法，不提供默认题材审美。禁止把示例中的现代都市、轻喜剧、柔光、酒店、韩漫、特定服装、特定角色关系或特定道具状态自动带入新项目；画幅、题材、节奏、光线、服装和场景必须来自当前剧本、用户配置、项目 bible 或已确认资产。
18. Windows / PowerShell 安全：任何多行 JSON、Markdown、packet、constraints、prompt_package、review sidecar 或大段文本都必须先落盘，再通过文件路径传递；禁止把这些内容拼进 `powershell -Command`、`pwsh -Command`、`python -c`、`node -e` 或 here-string。命令行只保留短参数和路径。
19. 时长由可见剧情节拍决定，不由“氛围、压迫、静默、余韵”填充。单一微表情、一次视线变化、静态压场或群体凝视默认不超过 `max_static_shot_duration`（默认 6 秒）；超时子镜必须在 Phase 1 提供 `duration_rationale` 与有序 `dramatic_beats[]`，并通过 `preflight_check.py`，否则不得派发任何 Agent。
20. 先运行 `scripts/route_task.py` 选择 `full / audit / export / compose / single-repair`，并显式传入 `--intent new/resume/audit/reexport`。`full/new` 先走逐项配置向导；`export` 仅接受已完成 Editor Pass 2 与 Validate 的运行，且只重新确认本次 Markdown 导出路径；纯审查、导出、单镜修复不得默认重跑全管线。
21. 先读 `references/ROUTES.md`，再按路由读取指定契约、packet 与函数片段。不得为路径检查、格式校验或字段搬运加载完整 runbook、完整历史或无关 Python 文件。
22. 表演因果链先于运镜设计。每个人物节拍先确定“触发原因 → 表情控制 → 细部/道具泄露 → 肩背、重心或步伐承接 → 说话语气/呼吸 → 可见残留”；运镜、反打、特写和移镜只能响应这条链中的可见重音，不得先选炫技运镜再反推表演。
23. Director 必须为每个有表演的子镜选择 `editorial_mode`：`continuous_take` 为一条连续摄影轨迹；`motivated_sequence` 为同一剧情目标内由表演重音触发的自然景别/视角变化。后者可有 1–3 个 `camera_beat_map`，每次变化必须写触发、画面主体、镜头响应和承接状态；它不是禁止切换的单镜，也不是无动机的连续变焦。

## 1. 单一数据契约

| 阶段 | 顶层结构 | 关键说明 |
|---|---|---|
| Phase 2 analysis batch/merged | `{"items":[...]}` | emotion/scene/camera 不混用旧结构 |
| Phase 3 director | `{"items":[...],"merged_full_prompts":[]}` | 确定性合并 |
| Phase 6 Composer batch | `{"shots":[...]}` | 每子镜一个 v4 shot |
| Phase 6/7 merged package | `{"contract_version":"modec-v4","items":[...],"shots":[...],"merged_full_prompts":[...]}` | `items` 与 `shots` 内容相同 |
| Phase 10 export | Markdown + XLSX | Markdown 只导出投喂内容、负面词、下一镜转场提示词和台词表演；QA 元数据、生成控制、三份合同保留在 XLSX/缓存 |

Phase 6 每个 shot 必须包含：

```json
{
  "shot_id": "S1-01",
  "subshot_id": "S1-01-01",
  "duration": 5.0,
  "full_prompt": "",
  "negative_prompt": "{{NEGATIVE_PROMPT_AUTO_INJECT}}",
  "qa_metadata": {},
  "generation_control": {}
}
```

详细字段见 `references/format_constraints.md` §B。

## 2. Pipeline

| Phase | 名称 | 执行方式 | 门禁 |
|---|---|---|---|
| 0 | 用户确认 | 逐项生成并确认 `project_config.json` | 每轮仅 1–2 项；确认元数据完整，画幅、风格、最大时长、平台、音频、模式、参考资产、九宫格与导出位置齐全；`run_dir` 已建立且位于 `export_base` 下 |
| 0.5 | 源规则检测 | `detect_source_rules.py` | 人工核验 scene header 与角色列表 |
| 1 | Orchestrator 拆镜 | `generate_shotplan.py` + `build_shotplan.py` | `preflight_check.py` 0 issue |
| 1.5 | 主镜头合并 | 本地脚本 | 备份 `shot_plan.original.json` |
| 1.6 | 空间注册 | `spatial_registry.py` | 每个 subshot 有 `spatial_map` |
| 2a/2b/2c | 情绪/场景/运镜 | Agent batch | `validate_agent_output.py` |
| 2.5 | 三路合并 | `merge_agent_outputs.py` | subshot 覆盖 100% |
| 3 | Director 整合 | `assemble_director.py` | `gate_check.py` + `spatial_lint.py` |
| 5 | 连续性检查 | `continuity_check.py` | blocking 为 0 |
| 6 | Mode C v4 Composer | Agent batch；普通镜自适应2–4个/批，连续链保持同批，可并行 | `validate_composer_output.py` |
| 6a | 合并 | `merge_agent_outputs.py` | v4 双键 package |
| 6b | 运镜合同诊断 | `enforce_camera_detail.py` | 缺失镜头设计退回 Composer；脚本不改写成品提示词 |
| 6c | v3→v4/负面词归一化 | `normalize_prompt_package.py` | 负面词独立注入，不改叙事与台词 |
| 7 | Editor Pass 1 | `merge_prompts.py` | 幂等归并 Composer 批次；主镜头分组完整且无重复 subshot |
| 8 | Editor Pass 2 | Agent 语义审查 | 只修语义穿帮和执行竞争 |
| 8.5 | 九宫格剧情包（可选） | 本地派生脚本 | 仅 `storyboard_grid.enabled=true` 时，从已通过 Editor Pass 2 的 T2V提示词、合同和风险数据自动选关键连续镜头链；关闭时状态机标记 skipped，不落盘 |
| 9 | 最终验证 | `check_export.py` + `validate_modec.py` | v4 检查全部通过 |
| 10 | 导出 | `export_with_validation.py` | 用户确认路径下 Markdown + XLSX 可打开 |

Composer packet 必须使用脚本生成的 `composer_scaffold_path` 锁定 `shot_id/subshot_id/duration/negative_prompt/dialogue_refs/generation_control`，并先填写三份合同再写四段提示词。相同场景的画幅、风格、服装、光源与空间锚点从 `scene_lock_cache_path` 读取一次。每批完成后立即校验；失败时运行 `prepare_composer_retry.py`，它封存失败 batch 哈希、为通过镜记录 partial provenance，并只为失败 `subshot_id` 生成新 dispatch。失败 batch 禁止原地修复或重新签名。

每个已通过阶段自动写入 `.cache/stage_summary/<phase>.json`，只记录已验证产物的路径、哈希、结构、覆盖数量与少量 ID。恢复任务时先读 `pipeline_state.json`、最近阶段摘要和目标 packet；只有需要修复的字段才回读完整产物。第一次重试只回传失败子镜及 validator 原文；第二次重试强制单子镜批次并只修失败字段。每个 retry packet 都携带 `retry_context_path`，不得重新创作已通过镜头。

九宫格剧情包是 T2V 主流程后的可选派生物，不是 I2V/R2V 分支：它不修改 `full_prompt`、`generation_control`、参考资产或已通过的 Editor 结果。启用时只从最终稳定数据中按连续镜头链评分，优先多人关系、可见情绪递进、动作/空间调度、道具状态转移和高抽卡风险；低风险空镜、单一简单动作和纯信息镜不输出。每个命中链导出一条 3×3 总图生图提示词、独立负面提示词与 P01-P09 剧情节拍。用户可自行使用该包生图，但技能不会等待、接收或依赖后续图片。

三份合同不是导出文案，而是生成前的硬骨架：

- `performance_contract`：把人物表情、身体动作、视线、反应延迟、呼吸/语气、观众共情锚点、画面可读瞬间、压制/释放、运镜压力、场景压力和落幅残留合成一条张力链，并落实到 `表演时间轴`、`镜头设计`、`画面锁定/光照与声音`。
- `continuity_contract`：锁定本镜起点、落点、人物位置、视线方向、道具状态、光源关系和下一镜必须继承的残留，防止单镜好看但跨镜断裂。
- `reroll_control`：按身份、动作、场景、运镜、口型和参考资产缺失评估抽卡风险；T2V 人物镜不得标低风险，rising/peak 人物镜必须说明是否需要角色图、首帧、动作参考、九宫格关键帧、I2V 或 R2V。

## 3. Phase 2 质量边界

### 情绪 Agent

- 输出事件触发后的表演因果链，不堆表情词。
- 先判断本镜张力意图是 `neutral / latent / rising / peak / release`；平静、舒缓或信息性交代镜不得被强行提升为高张力。
- 先标记本镜 `primary / supporting / background` 候选。背景角色不强制独立微反应。
- 主角只设计一个主表演事件和一个情绪转折；对手最多一个可见反应。
- 全景/中景使用走位、重心、轮廓和空间压力；不可见的眼部、鼻翼、唇线细节降级。
- “不反应”“压住反应”“停顿”可以是有效表演，前提是有可见终态和剧情原因。
- 明确反应来源：角色是直接感知事件，还是观察到另一角色的反应后才行动；禁止把同一触发写成无次序的多人同步启动。
- 接触、阻挡、受力或截停必须说明可见的物理依据；若动作实际由警告、犹豫或自主判断而停止，就写成角色主动收住，不能伪装成物理制服。
- 每个台词/OS/OV事件必须绑定原文人物；按同一时间窗给出情绪原因、景别可见神态、身体状态和说话语气。不可见或非实体发声者明确写 `N/A` 及原因，不伪造面部表演。

### 场景 Agent

- 同场景固定光源、色温和空间关系继承；景别变化不触发色温变化。
- 人物镜头提供一处真实接触或同源光锚点，不为凑字段重复描写。
- 服装只从已确认设定继承；不得新增颜色、款式、材质、配饰或发型。
- 音频只在 `audio_enabled=true` 时进入模型提示词；否则保留为制作元数据。

### 运镜 Agent

- `continuous_take` 只使用一种主要运镜；同方向的轻微收束可以作为该运镜的落幅，不算第二运镜。`motivated_sequence` 可按 `camera_beat_map` 自然切换景别、反打、推近、移镜或跟随，但每一次切换都必须由表情泄露、道具动作、身体承接或语气落点触发，并继承同一人物、道具、轴线和光源状态。
- 连续互动允许一次由剧情触发的注意力交接。它不等于第二个独立戏剧焦点：任一时刻仍只有一个清晰主体，且镜头整体仍服务同一戏剧目标。
- 注意力交接只选一种主策略：`固定双人构图+一次拉焦`、`一次单向摇/移重构图`、或`演员走位改变画面权重+固定机位`。禁止把推、摇、变焦、拉焦同时叠加。
- 焦距、固定镜头比例和景别梯度都是剧情启发式，不是全片硬配额。
- 不因为相邻镜头景别相同而强行换景别；只有信息层级或戏剧重音变化才换。
- 推镜通常不超过 0.3m/s、拉远通常不超过 0.2m/s；速度只保留一个关键锚点。
- 摄影机位与人物朝向分离；原文未授权时人物不直视镜头。

## 4. Phase 6 Composer — Mode C v4

### 4.1 模型提示词四段

`full_prompt` 必须且只能包含以下四段，段间一个空行：

1. `画面锁定：` 画幅、风格、可见人物、服装、站位、朝向、场景接触与不变项。
2. `镜头设计：` 时长、景别、焦距、机位、轴线，以及连续轨迹或由表演重音触发的镜头组。
3. `表演时间轴：` 2–3 个连续小数秒时间段，写主动作、触发、反应、台词/OS/OV归属、发声时神态/身体/语气、口型和可见终态。
4. `光照与声音：` 固定光源关系和声音同步；不重复表演时间轴中已经逐字出现的台词/OS/OV原文。

禁止在 `full_prompt` 中出现负面提示词、`自包含验证`、QA 结论、工程字段、模板编号或“可独立投喂”等说明。

### 4.2 动作预算

- 3–6 秒：主动作 ≤1、情绪转折 ≤1、对手反应 ≤1；`continuous_take` 主要运镜 ≤1，`motivated_sequence` 最多 1–3 个由表演重音触发的镜头响应。
- 6–10 秒：主动作 ≤2、情绪转折 ≤1、对手反应总数 ≤2；镜头响应数量仍服从所选 `editorial_mode`。
- 10–15 秒连续互动：允许 2–3 个因果相接的内部节拍、多个短台词轮次及一次 `A→B` 注意力交接，但仍保持一个整体戏剧目标和最多一个情绪转折。`continuous_take` 保持一条摄影机轨迹；`motivated_sequence` 只用与内部表演节拍一一对应的自然切换。注意力交接必须由台词/动作触发并在落幅重新建立关系构图；第二个独立戏剧目标、反复抢焦或无关动作链必须拆镜。
- 6 秒以上不是“质感时长”。只有连续对白、连续互动、连续动作或持续揭示过程才可延长；6–10 秒必须有至少 2 个可见因果节拍，10–15 秒必须有至少 3 个。落幅残留通常只占最后一个短时间窗，不能把同一静止状态重复演满镜头。
- 打斗优先单镜连续动作链：同一生成片段只计一个主编舞链，可在 2–3 个连续时间段内完成因果相接的攻防；≤6 秒最多 1 个接触节拍、6–10 秒最多 2 个、10–15 秒最多 3 个。攻防双方在同一链内的因果注意力传递不算换焦点；只有换轴、切到独立主编舞链/戏剧焦点、换场景、第二条无关动作链或超过 15 秒才拆成下一生成片段。
- 背景群体只写低幅连续活动和不抢主动作，不逐人分配微动作。
- 没有审美最低字数。`full_prompt` 少于 120 字视为信息不足，超过 1100 字必须拆镜；常规 3–6 秒镜头以 220–650 字为软目标。

### 4.3 表演张力

优先使用：`起始压住 → 事件触发 → 身体先反应 → 情绪短暂泄露 → 终态残留`。

- Composer 必须先把这条链写入 `performance_contract`，再把可见结果拆进时间轴；禁止先写 prompt 再反向补 QA。
- 张力拉满不是每镜高强度，而是每镜达到自身功能上限：信息镜有暗流，关系镜有压迫，爆点镜有明确触发、反应延迟、身体先动、表情泄露和落幅残留。
- 张力强度服从原剧本，不以“所有镜头都拉满”为目标。低张力镜保持自然流动，高张力镜通过更清晰的因果、反应延迟和终态残留增压，不靠增加动作数量。
- 主角获得完整表演链；对手只获得一次对主事件有因果关系的反应。
- 每个人物镜必须提供一个观众能立即读懂的共情锚点：角色在怕什么、忍什么、失去什么、想护住什么或被什么刺中，并落实为一个景别可见画面瞬间。禁止只写“感染力强、共情感强、观众感动”等效果词。
- 画面感来自可见证据而不是形容词：手停在门把/衣角/手机屏幕，视线避开某人，肩背收紧，呼吸卡住，空间距离被压缩，光线遮住半张脸等。每镜只选 1 个主证据，避免堆满微动作导致抽卡升高。
- 张力来自停顿、方向变化、重心和反应延迟，不来自同时驱动多个面部部位。
- 特写才写眼周、唇线或下颌；中近景写视线、肩颈、手与呼吸；全景写走位、重心、衣摆和空间关系。
- 固定镜头允许克制或近乎静止；只需一个可见生命迹象或有意静止的理由。
- 非说话焦点角色口型闭合；背景群体统一写“无同步口型”，不逐人重复。
- `audio_enabled=true` 时，每条原文只在表演时间轴出现一次，统一写成 `{人物}（台词/OS/OV）` 后接逐字原文，并在同一事件内写神态、身体状态、语气和口型。可见台词人物同步口型；OS/OV、画外或非实体发声者不驱动口型。
- `audio_enabled=false` 时，原文不得进入 `full_prompt`；可见人物的神态、身体与口型边界仍进入表演时间轴，完整原文、人物、类型、时间窗和配音控制保存在 `qa_metadata.dialogue_events` 并单独导出。
- 触发发生在时间段内部时给出明确时点；突发或短促动作应尽早完成接触点、转折点或制动点，把余下时间留给受力、回稳和残留，除非原文要求缓慢完成。
- 中断动作必须区分“被取消的主运动”和“仍被允许的残余运动”。后段若出现相似方向动作，要写清幅度或身体部位差异，避免刚截停又完整重做。
- 接触结果必须匹配接触点、支撑关系、受力方向和角色重心。缺少足够杠杆时，只能产生提示、警告或角色自主收住，不能生成不可信的强制位移。
- 长停顿占镜头超过约三分之一或持续超过 1.5 秒时，只选择 1–2 个景别可见的生命迹象，或明确有意静止的剧情理由；禁止用密集微动作破坏屏息、僵持、庄重或松弛状态。
- 静止理由只证明表演成立，不证明镜头应该变长。若整个镜头没有新的可见信息、关系变化、动作结果或台词推进，应缩短为 2–6 秒；不可用“压迫感、余韵、静默、保持凝视”延长。
- 落幅必须保留上一事件造成的可见残留，如姿态、接触、重心、视线、呼吸、道具或空间距离的持续状态，而不是复位成无事发生。
- 有人物镜头在 `qa_metadata.performance_causality` 中记录张力意图、触发、反应顺序、物理逻辑、运动边界、停顿策略和终态残留；无可见物理角色的环境镜可省略。
- 有人物镜头还必须在 `performance_contract` 中合并表情、身体动作、视线、反应延迟、观众共情锚点、画面可读瞬间、压制/释放、运镜压力、场景压力和落幅残留；这些内容必须能在 `full_prompt` 对应段落中找到。
- 吸收强示例的表演密度：每个情绪按“触发原因 → 表情控制 → 肢体动作 → 呼吸/说话语气”驱动；优先写眼神落点、眉尾/下颌/嘴角的克制变化、呼吸停顿、手指/袖口/领口/外套等道具起势、肩背和步伐承接。必须服从景别可见性，不把这些写成固定清单。
- 吸收示例时只迁移结构优势：因果链、时间段连续、道具状态转移、系统文字安全区、台词口型边界、落幅残留和抽卡控制。不得迁移示例的题材、光源、喜剧节奏、酒店/都市空间、韩漫审美、人物衣着或人物关系，除非当前项目显式要求。
- 外套、领口、手机、武器、伤势等状态转移必须进入 `continuity_contract.prop_state` 与 `next_carryover`，写清从谁到谁、遮挡/接触结果和下一镜继承状态，禁止重置。
- 系统文字只作为侧边安全区彩色悬浮文字或画外声，不实体入画，不遮脸、不遮口型、不抢主动作。

### 4.4 多模态控制

- `t2v`：无参考资产时使用，标记抽卡风险较高。
- `i2v`：角色一致性、服装和首帧站位重要时优先。
- `r2v`：关键表演、复杂动作或摄影路径已有图片/视频/动作参考时优先。
- 图生视频可在 `画面锁定` 开头使用平台支持的参考图标记来锁定人物五官、发型、服饰和身份连续性；该标记必须来自已确认 `reference_assets` 的真实资源或平台槽位，禁止硬编码或伪造。
- `generation_control.reference_assets` 只记录用户已提供或项目已确认的真实路径/资源 ID。
- 九宫格、首尾帧、角色参考图和动作参考必须在导出中分栏，不能伪装成纯文本已锁定能力。
- `reroll_control` 必须明确：身份锚点、动作锚点、场景锚点、镜头锚点、风险来源、至少两条缓解策略，以及是否需要参考资产。未提供资产时只标注需求和风险，不伪造路径。

### 4.4.1 平台执行偏好

- 面向即梦等短视频生成平台时，吸收其有效语序：先给景别/镜头和主体站位，再写触发动作、表情/肢体递进、场景光影，最后补当前镜头必要的动态稳定约束；仍然落在 Mode C v4 四段内，不新增第五段。
- 动态稳定约束只选择当前镜头需要的控制项，如相对位置恒定、互不穿透、光影方向恒定、运动范围可控、镜头平滑、非说话人口型闭合；不得把示例约束整段复制到每条提示词。
- 复杂动作和打斗优先降低抽卡风险：控制速度、幅度、接触节拍和镜头抖动；超出单条可稳定生成的复杂度时拆成连续片段，并用 `fight_continuity.start_lock/end_lock` 承接。

### 4.5 QA 与负面词分离

- `qa_metadata` 保存本镜戏剧目标、角色优先级、动作预算、起始/终态和台词引用；不得拼进 `full_prompt`。
- `qa_metadata.dialogue_events` 必须与 `dialogue_refs` 一一对应。`ref/kind/speaker/text` 由 Phase 1 锁定，Composer 只能填写 `time_range/speaker_visibility/facial_state/body_state/delivery/lip_sync`。
- `facial_state` 写景别可见的眼神、眉眼、嘴角、下颌或呼吸状态；`body_state` 写肩颈、手、重心、站姿或道具接触；`delivery` 至少明确语速、音量/气息、停顿/咬字/尾音中的两项。禁止只写“紧张、悲伤、愤怒、自然地说”。
- 有可见物理角色时，`qa_metadata.performance_causality`、`performance_contract`、`continuity_contract`、`reroll_control` 必须按 `references/format_constraints.md` §B7 填满；它们用于 Composer 自检和 Editor 复核，不投喂视频模型。
- 打斗镜额外保存 `fight_continuity`：连续生成模式、序列/片段 ID、参与者、接触节拍，以及可被下一片段精确继承的 `start_lock/end_lock`。
- Composer 的 `negative_prompt` 只写 `{{NEGATIVE_PROMPT_AUTO_INJECT}}`。
- 归一化脚本按普通、多人、对白、参考驱动、打斗上下文注入精简负面词。
- 平台支持独立负面词栏时分栏投喂；不支持时由平台适配层决定合并，Composer 不自行混写。
- 负面词库只吸收示例中的通用崩坏维度，如肢体、五官、身份漂移、帧间闪烁、光影突变、穿插、口型、水印和画风突变；不得把正向动态约束整段挪进负面词。

## 5. Editor Pass 2

审查并修复：

- 主动作是否唯一、对手反应是否抢戏、背景是否过度活跃；
- 时间段是否从 0.0 连续覆盖到整镜终点；
- 张力意图是否服从原剧情，是否把平静镜误做成高强度，或用动作堆叠代替因果增压；
- 触发时点、感知来源和反应先后是否明确；突发动作是否被不合理拉成长动作；
- 接触、受力、阻挡与截停是否有可信物理依据；心理性或策略性停止是否被误写为机械制服；
- 中断动作与后续残余运动是否边界清楚，是否出现“刚被截停又完整重做”的自相矛盾；
- 长停顿是否只有少量景别可见生命迹象或明确静止理由，落幅是否保留上一事件的可见残留；
- 时长是否被连续对白/互动/动作/揭示过程消耗；是否把同一凝视、静止压场或群体反应在相邻镜重复演绎。无新增信息的延时必须压缩或删除；
- 景别是否能看见所写表演；
- `continuous_take` 是否出现竞争运镜、焦点或动作；`motivated_sequence` 的反打、切特写、移镜或跟随是否各自由表情、细部/道具泄露、身体承接或语气落点触发，并在变化后保留人物、道具、轴线和光源承接；
- 连续互动的注意力交接是否有单一触发、单一策略和明确落幅；只写“聚焦甲/聚焦乙”或同时叠加物理运镜与多次拉焦属于不可执行；
- 人物站位、视线、服装、道具、光源和终态是否跨镜承接；
- 台词/OV/OS 是否逐字保留，非说话角色是否错误同步口型；
- 每条台词/OS/OV是否明确类型、人物和原文；发声时间窗内是否同时存在人物神态、身体状态与说话语气；OS/OV是否保持无口型同步；
- 原生音频开启时原文是否只在表演时间轴出现一次，关闭时是否完全移出模型提示词并保留在独立制作数据；
- I2V/R2V 是否有真实参考资产，引用路径是否来自项目确认；
- `full_prompt` 是否混入 QA、负面词或工程说明。

格式错误交给脚本，不由 Editor 用自由改写方式修复。

## 6. 推荐调用

调用脚本前读取其 `if __name__ == "__main__"` 参数段。

```bash
python3 scripts/validate_agent_output.py <analysis_output.json> analysis
python3 scripts/route_task.py audit --run-dir <run_dir> --intent audit
python3 scripts/write_stage_summary.py <run_dir> <phase> <output_path>
python3 scripts/register_dispatch_agent.py <dispatch_packet.json> <agent_id>
python3 scripts/record_batch_provenance.py <dispatch_packet.json>
python3 scripts/promote_verified_batch.py <single_batch_dispatch_packet.json>
python3 scripts/merge_agent_outputs.py --require-provenance <merged.json> <batch1.json> <batch2.json>
python3 scripts/validate_composer_output.py <composer_batch.json> --run-dir <run_dir>
python3 scripts/prepare_composer_retry.py <run_dir> <failed_composer_batch.json>
python3 scripts/normalize_prompt_package.py <input.prompt_package.json> <output.prompt_package.json>
python3 scripts/validate_modec.py <run_dir>
python3 scripts/check_export.py --quality <run_dir>
python3 scripts/export_with_validation.py <user_confirmed_export_md> <run_dir>
```

## 7. 最终质量标准

- 模型只收到可执行的画面、镜头、表演时间轴和平台适用的光声指令。
- 每子镜有唯一注意力中心、有限动作预算和清晰终态。
- 表演由剧情触发，反应次序、物理机制与运动边界可信，主次分明，克制与爆发有反差。
- 每条台词/OS/OV都有确定人物、逐字原文、发声时间窗、可见神态、身体状态、语气和正确口型边界。
- 张力按剧情意图校准；高张力来自因果效率、反应延迟与终态残留，平静镜不被强行戏剧化。
- 景别、人物、场景、光源、轴线和参考资产跨镜稳定。
- 关键镜优先使用真实多模态参考降低抽卡率。
- 所有硬格式、时间覆盖和动作预算由脚本验证，所有语义穿帮由 Editor 审查。
