---
name: ai-video-agent-mode
description: >
  Use this skill when the user asks for a reusable/system-level 4-agent workflow
  for converting scripts, storyboards, scenes, or docx/txt/md source material
  into aligned AI video prompt packages. Triggers include agent模式, 4-agent,
  多agent, 剧本转AI视频提示词, 关键帧提示词, 静态分镜提示词, 动态视频提示词,
  完整提示词, 九宫格剧情分镜图, 四宫格关键帧展开, and requests that require
  canvas/style/duration/export-dir gates, one-to-one subshot/keyframe/motion
  correspondence, main-shot merged full prompts, and staged QA.
---

# AI Video Agent Mode

Use this skill as the top-level coordinator for commercial AI-video prompt production.

## 主镜头划分优先级（Orchestrator 拆镜时按此顺序决定是否拆分）

Orchestrator 将剧本拆为 shot_plan.json 时，主镜头的划分必须按以下优先级自上而下执行，**不得跳过**：

**概念边界：**
- **主镜头 shot**：一个完整剧情节拍，必须能独立表达一个动作/台词/反应/情绪变化单元，并且总时长不得超过用户在 Phase 0 输入的 `project_config.max_shot_duration`。
- **子镜头 subshot**：主镜头内部的可视化执行单元，用于同一节拍内的景别变化、插入特写、反应镜头、手机屏幕/物件镜头、OS承接等。
- 不得因为一次推拉、一次景别变化或一个表情补充就拆成新主镜头；只有剧情节拍、场景或时长约束触发时才拆主镜头。
- 不得为了凑满时长把不同剧情节拍合并到同一主镜头。

**第一优先：剧情节拍**
一个主镜头对应一个独立的剧情节拍（一个动作 + 台词 + 反应的最小戏剧单元）。
- 每个剧情节拍包括：一个动作发生、一段对话完成、一个情绪转折或一个角色反应
- 不同的节拍必须拆成不同的主镜头，不得为了凑满用户输入的最大时长而把两个节拍塞进同一主镜头
- 示例：「向云初撞上江训」是一个节拍 → 单独一个主镜头；「系统上线激动大喊」是另一个节拍 → 另一个主镜头

**第二优先：场景切换**
场景切换（日/夜、内/外、地点变化）是硬性分割点，自动产生新的主镜头。

**第三优先：台词时长**
如果一个剧情节拍内的所有子镜头台词朗读时长总和 > `project_config.max_shot_duration`，则在句子边界拆分：
1. 先把长段台词在句号（。）/ 感叹号（！）/ 问号（？）/ 省略号（……）处切分成更短的最小语义单元（存入 dialogue_map）
2. 把这些单元分配到两个或多个子镜头中，每个子镜头配对应的动作/反应
3. 如果拆分后单个子镜头的时长仍 > `project_config.max_shot_duration`，则拆成两个主镜头，前一镜头结束时后一镜头对应角色的准备/反应状态作为承接

**禁止行为：**
- 禁止因时长不足把两个不相干的节拍合并到一个主镜头
- 禁止剪短台词原文来凑时长
- 禁止在逗号、顿号、冒号等句内停顿处拆分台词

**计算公式（子镜头时长）：**
有效语速 = 4.5 × 情绪系数
台词朗读时间 = ∑(每段台词字数) / 有效语速 + 标点停顿
如果对话和动作同时发生（边说边做），子镜头时长 = max(台词朗读时间, 动作耗时) + 反应空白(0.5s)
如果动作需要独立视觉焦点（如特写手部），子镜头时长 = 台词朗读时间 + 动作耗时 + 反应空白(0.5s)

## 管线执行阶段（严格顺序,不可跳过）

### Phase 0: 用户确认（每次启动必走）
启动管线前先向用户确认以下 4 项，用户回复后填入 project_config.json：

| 确认项 | 格式 | 示例 |
|--------|------|------|
| 画布/画幅 | 选择: 9:16 / 16:9 / 1:1 | `16:9` |
| 视觉风格 | 用户输入文字 | `现代都市/冷幽默` |
| 单条视频最大时长 | 用户输入或选择: 5/8/10/15/18/20/25/30 秒 | `15` |
| 最终存放位置 | 用户输入目录路径 | `C:\path\to\export` |

若用户重复输入（修改上面任何一项），用 `_run_{timestamp}` 形式创建新文件夹，将本次输出放进去。
旧输出保留不删除，防止覆盖。

### 运行缓存位置

技能目录只保存源码、参考和模板，不保存运行缓存。运行时必须把 Python 缓存放到本次导出目录下的 `.cache/pycache`，不得写入技能源码目录。

主Agent执行本技能的 Python 脚本前，必须把 `PYTHONPYCACHEPREFIX` 指向本次导出目录下的 `.cache/pycache`，例如：

```powershell
$env:PYTHONPYCACHEPREFIX = "C:\path\to\export\.cache\pycache"
```

`__pycache__` 和 `*.pyc` 属于临时运行产物，不得留在 `~/.codex/skills/ai-video-agent-mode` 内。

脚本入口也会通过 `scripts/pycache_policy.py` 强制设置 `sys.pycache_prefix`。如果调用方忘记设置环境变量，脚本会先阻止源码目录写入 bytecode，并在拿到 `run_dir` / 输出路径后自动把缓存导向 `<run_dir>\.cache\pycache`。

### 落盘节流与上下文复用

为减少运行时间和 token 消耗，管线默认采用“文件路径派发 + 增量摘要重试”：

1. `pipeline_runner.py` 返回 `batch_spawn` / `spawn` / `send_back` 时，会生成 `.cache/dispatch/{phase}_packet.json`。
2. 主Agent派发子Agent时，只传 packet 路径、输出路径、失败子镜头ID和修正要求；不要复制完整 `shot_plan.json`、完整剧本文本或已通过镜头正文。
3. 子Agent必须读取 packet 中的 `source_path`，只处理 `items` 列出的子镜头，并把结果写入 packet 中的 `output_path`。
4. 已通过镜头只通过 `.cache/handoff/{role}_handoff.json` 传递短摘要，禁止在重试消息中重复发送完整提示词。
5. 大文件职责边界：
   - `.cache/orchestrator/shot_plan.json`：唯一拆镜源。
   - `.cache/dispatch/*_packet.json`：子Agent本批任务入口。
   - `.cache/analysis/*.json`：三路分析结果。
   - `.cache/handoff/*_handoff.json`：短摘要恢复记忆。
   - `.cache/review/*`：脚本门禁与LLM审查结果。
### 落盘调度优化（数据文件+子Agent文件读写）

从 2026-07-17 起，子Agent采用**落盘调度**代替全量文本嵌入：

#### 原理
子Agent通过 spawn_agent 启动后，可以使用 shell_command 读取和写入本地文件。
利用这一能力，将镜头数据写入紧凑 JSON 文件再派发，取代将全部数据嵌入 spawn message。

#### 优势对比
| 对比项 | 传统方式（全量嵌入） | 落盘调度方式 |
|--------|-------------------|------------|
| spawn message 大小 | ~2000 tokens | ~200 tokens |
| 数据格式 | 文本中混合 JSON | 纯 JSON 文件 |
| 子Agent解析成本 | 需从文本拆JSON | 直接 json.load() |
| 批量处理 | 需分批 send_input | 一次读完整个文件 |
| 重试效率 | 需重发完整数据 | 文件不动，只发失败shot_id |

#### 调度流程

Phase 1（Orchestrator 本地）：
  拆镜 → shot_plan.json

Pre-Dispatch（Orchestrator 本地）：
  → 为每个子Agent生成紧凑 JSON：emotion_data.json / scene_data.json / camera_data.json
  → 写入 .cache/dispatch/{phase}_data.json
  → 每个JSON只包含该子Agent需要的字段，字段名用缩写（id/chars/acts/diags/narrs/dur/desc）

Phase 2a/2b/2c（并行 spawn 子Agent）：
  → spawn_agent 的 task 中写：
    "读取 {export_root}\.cache\dispatch\{phase}_data.json 处理所有镜头
     输出 JSON 写入 C:\path\to\.cache\analysis\{phase}_output.json
     格式要求见子Agent输出JSON格式规范"
  → 子Agent用 python -c "import json; json.load(open(path))" 读取
  → 处理后用 json.dump() 写入输出文件
  → 最后在主Agent的完成消息中回传 "已完成 N 镜，输出到 {path}"

#### 紧凑JSON格式约定

字段名缩写规则（所有子Agent通用）：
- id → shot_id
- chars → characters（数组）
- acts → actions（数组）
- diags → dialogues（数组，每元素含 char/text/tone）
- narrs → narrations（数组，每元素含 ch/t）
- dur → duration（数字）
- desc → description（字符串）

各子Agent dispatch 文件只包含该子Agent所需的字段：
- emotion_data.json: id, chars, acts, diags, narrs, desc, dur
- scene_data.json: id, chars, acts, desc
- camera_data.json: id, chars, desc, dur, acts

示例 emotion_data.json：
```json
[
  {"id":"S1-01","chars":["沈星雨","宋南枝"],"acts":["...走路..."],"diags":[],"narrs":[{"ch":"沈星雨","t":"说起沈星州..."}],"desc":"...","dur":8},
  {"id":"S1-02","chars":["沈星雨","宋南枝","江训"],"acts":["...江训闯入...","...偷拍..."],"diags":[{"ch":"宋南枝","t":"那不是江训么？","tone":"凑在沈星雨耳边小声嘀咕"}],"narrs":[{"ch":"沈星雨","t":"啧，就是这种劲儿劲儿的样子"}],"desc":"...","dur":10}
]
```

#### 子Agent操作指令模板

子Agent收到 spawn 后的标准读取-处理-写入流程：

```python
import json, sys

# 读取数据
try:
    with open("<dispatch_path>", "r", encoding="utf-8") as f:
        shots = json.load(f)
except Exception as e:
    print(f"ERROR: cannot read dispatch file: {e}")
    sys.exit(1)

# 逐镜分析
output = {"shots": []}
for s in shots:
    analysis = {
        "shot_id": s["id"],
        # ... 按输出格式规范填充各字段
    }
    output["shots"].append(analysis)

# 写入输出
with open("<output_path>", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
# 格式校验
with open("<output_path>", "r", encoding="utf-8") as f:
    verify = json.load(f)
if len(verify.get("shots", verify.get("analyses", verify.get("analysis", [])))) != len(shots):
    raise RuntimeError(f"Output shot count mismatch: expected {len(shots)}, got {len(verify)}")

print(f"完成 {len(shots)} 镜分析，输出到 <output_path>")
```

主Agent通过 wait_agent 拿到子Agent的完成消息后，
用相同方式读取 `<output_path>` 获取分析结果，
无需从消息文本中解析 JSON。


如果 packet 存在，主Agent必须优先让子Agent读 packet；只有 packet 缺失或损坏时，才回退到直接下发最小必要镜头数据。

### 管线阶段顺序

Phase 0:  用户确认                           → project_config.json
Phase 1:  Orchestrator (本地)               → shot_plan.json
Phase 2a: 情绪分析 子Agent ($emotion-analysis)  → emotion_output.json
Phase 2b: 场景分析 子Agent ($frames-analysis)   → scene_output.json
Phase 2c: 镜头运镜 子Agent ($camera-analysis)   → camera_output.json
Phase 3:  QA/整合 (本地 handler，不 spawn)    → director_pass.json
Phase 4:  Director 质量验证 (本地门禁)       → 校验通过才继续
Phase 5:  连续性检查 (不可跳过)               → continuity_check.py
Phase 6:  Prompt Composer 子Agent             → prompt_package.json → 校验失败重派
Phase 7:  Editor Pass 1 (不可跳过)            → merge_prompts.py
Phase 8:  Editor Pass 2 子Agent+LLM评审 \(不可跳过\)       → review/llm_gate_result.json
Phase 9:  最终验证 (不可跳过·含语义校验)                 → pipeline.py --validate + validate_prompt_package.py + hybrid_gate.py
Phase 10: 导出 (不可跳过)                    → export_workbook.py → 写入用户确认的导出目录

### Phase 2a/2b/2c 并行下发

管线识别到 emotion_analysis 作为分析组首阶段时，返回 `batch_spawn` 动作，
同时列出 emotion_analysis、scene_analysis、camera_movement 三个角色。
主Agent应并行 spawn 三个子Agent，等待所有输出就绪后再进入 Phase 3。

### 分批派发规则（超时防护）

子Agent按技能复杂度设定不同的单批上限和超时时间。**主Agent必须严格遵守，这是防止超时的核心门禁。**

| 技能 | 单批上限 | wait_agent 超时 | 原因 |
|------|---------|----------------|------|
| emotion-analysis（情绪） | 20 个子镜头 | 900s（15min） | 每镜需生成大量自由文本，≤10个子镜头可降至600s |
| frames-analysis（场景） | 25 个子镜头 | 600s（10min） | 结构化为主含空间分层+光影，≤10个子镜头可降至300s |
| camera-analysis（运镜） | 30 个子镜头 | 600s（10min） | 定量参数为主，≤10个子镜头可降至300s |

超出单批上限时，主Agent按以下模式分批投递，所有批次写入同一 JSON 文件（增量追加模式）：

\\\
spawn_agent(items=[skill, text_首批])   # 首批含技能加载
wait_agent(agent_id, timeout=900s)      # 等待首批完成
send_input(target=agent_id, message=二批) # 后续批次
wait_agent(agent_id, timeout=900s)
send_input(target=agent_id, message=三批)
wait_agent(agent_id, timeout=900s)
\\\

**关键规则：**
- spawn_agent 的任务描述中一次性给出该子Agent负责的全部镜头列表（含批次信息）
- 但首批仅下发单批上限以内的镜头数据
- wait_agent 的超时时间必须使用上表对应技能的数值，不可统一用默认值
- send_input 的 message 末尾必须明确已通过镜头数 + 剩余批次数
- send_input 的 message 末尾必须明确已通过镜头数 + 剩余批次数

### 独立调度规则（减少串行等待时间）

主Agent在派发子Agent批次时，不必等待所有三个子Agent完成再发下一批。

**独立调度规则：**
每个子Agent独立完成一批后，立即发下一批，不等其他子Agent。

正确做法（推荐）：
```
# camera 第1批先完成
send_input(target=avicenna, message="第2批...")  # 不等 emotion
send_input(target=confucius, message="第2批...")  # 不等 emotion
# emotion 完成后
send_input(target=bohr, message="第2批...")
```

错误做法（禁止）：
```
wait_agent(bohr, confucius, avicenna)  # 等最慢的
send_input(bohr, "第2批...")            # camera 空等 7 分钟
send_input(confucius, "第2批...")
send_input(avicenna, "第2批...")
```

**预嵌入数据规则（落盘优先·嵌入后备）：**

默认方式：通过 dispatch 文件传递数据（推荐）：
  send_input 的 message 中写 "读取 {export_root}\.cache\dispatch\{phase}_data.json"
  子Agent用 json.load(open(path)) 读取紧凑JSON，无需从文本解析。
  dispatch 文件由 generate_dispatches(export_root, shot_plan) 在 spawn 前生成。
  字段名使用缩写（id/chars/acts/diags/narrs/dur/desc），文件比 shot_plan.json 小约60%。

后备方式：dispatch 文件不存在时，直接嵌入本批镜头完整字段数据：
  send_input 的 message 中嵌入该批镜头的全部字段数据（shot_id, characters, actions, 
  dialogues（含 tone）, narrations, description, duration）。
  子Agent收到消息后直接处理，无需读取文件。

两种方式互斥：dispatch 文件存在时优先用文件，不存在时才嵌入。

示例：
```
第N批：以下为本批 N 个镜头的完整数据（已嵌入，无需读取 shot_plan.json）：
[
  {"shot_id":"S1-XX","description":"...","characters":["..."],"duration":4,"dialogues":[{"character":"...","text":"...","tone":"..."}],"narrations":[{"character":"...","text":"..."}],"actions":["..."]},
  ...
]

输出必须按照 "### 子Agent输出JSON格式规范" 中的字段定义，一个 subshot_id 对应一个输出元素，
确保所有字段类型和键名严格匹配，主Agent会在 merge 阶段直接读取。
'''


- emotion-analysis 子Agent必须读取 `references/dynamic_performance_reference.md` 中的面部表情与台词语气同步章节，将可见的微表情、语气和生理时序按剧情改写后写入情绪分析输出

- frames-analysis 子Agent必须读取 `references/dynamic_performance_reference.md` 中的光影色调与肢体动作章节，将情绪匹配的光影方案和动作约束按场景改写后写入场景分析输出
- camera-analysis 子Agent必须读取 `references/dynamic_performance_reference.md` 中的运镜景别与肢体动作章节，将情绪匹配的运镜方案、物理法则和可见性判断写入运镜分析输出

### 子Agent重试与超时

- 子Agent最多重试 4 次（共 5 次尝试），每次重试使用 send_back 只传本批仍失败的 shot_id
- 每阶段超时时间按技能复杂度设定（参见上方"分批派发规则"表格）。超时后主Agent应：1) send_input 询问状态；2) 如3次无响应则重新spawn
- 超时后自动重派，连续超时 3 次后强制推进
- Agent 失活（10 分钟无响应）自动触发 recover 动作 → 重派新 Agent

### 增量重试（减少全量复制）

验证失败时，只将失败的子镜头 + 修正要求发回子Agent：

```python
{
  "action": "send_back",
  "shots": [          # 仅包含仍失败的子镜头
    {"subshot_id": "S1-01-01", "issues": [...]}
  ],
  "passed_count": 5   # 已通过的子镜头数量（不包含在shots中）
}
```

修正消息中只包含本轮仍失败的问题，之前已修正的 issuse 不再重复发送。

### 100% 通过率门禁

所有阶段必须通过质量门禁才能继续推进，不允许带问彔继续：
- 内容质量校验（字段长度、格式规范性）
- 污染检测（禁止 XYZ 坐标/工程术语/JSON 嵌套）
- Bypass 检测（输出文件必须由子Agent创建，主Agent不得代写）
- 时间戳校验（输出修改时间必须在子Agent派发之后）
- 混合门禁：脚本先检测确定性违规，再由 LLM 审查语义穿帮、表演合理性和剧情一致性

任何 blocking 级别的问题都会触发重试，不会降级跳过。

### 混合门禁执行规则

脚本门禁负责确定性问题：字段缺失、污染词、台词增删改、OV/OS口型同步、景别可见性、无解释越轴、输出绕过。LLM门禁负责语义问题：表演是否符合场景、角色动机是否被动作改写、相邻镜头空间是否观感穿帮、情绪/灯光/运镜是否一致。

执行顺序：
1. Phase 2 派发前先运行 `preflight_check.py`；若 shot_plan 有硬错误，不派发任何子Agent。
2. 运行 `gate_check.py` 或 `hybrid_gate.py`，生成 `.cache/review/llm_gate_review.md`。
3. 若脚本门禁已有 blocking，先退回对应阶段修复，不启动 LLM 语义复审。
4. 脚本 blocking 清零后，Editor/QA LLM 读取 review packet，只审查脚本无法可靠判断的语义问题。
5. LLM 将结果写入 `.cache/review/llm_gate_result.json`。
6. 若 `blocking` 非空或 `pass=false`，按 `repair_targets[].send_back_to` 退回对应子Agent；不得由主Agent直接手改下游结果。

LLM审查必须引用具体 `subshot_id` 和失败原因，不能只写泛泛建议。

```
Phase 0:  用户确认                           → project_config.json
Phase 1:  Orchestrator (本地)               → shot_plan.json
Phase 2a: 情绪分析 子Agent ($emotion-analysis)  → emotion_output.json
Phase 2b: 场景分析 子Agent ($frames-analysis)   → scene_output.json
Phase 2c: 镜头运镜 子Agent ($camera-analysis)   → camera_output.json
Phase 3:  QA/整合 本地 handler                → director_pass.json
Phase 4:  Director 质量验证 (本地门禁)         → 校验通过才继续
Phase 5:  连续性检查 (不可跳过)               → continuity_check.py
Phase 6:  Prompt Composer 子Agent             → prompt_package.json → 校验失败重派
Phase 7:  Editor Pass 1 (不可跳过)            → merge_prompts.py
Phase 8:  Editor Pass 2 子Agent/LLM评审        → review/llm_gate_result.json
Phase 9:  最终验证 (不可跳过·含语义校验)       → validate_prompt_package.py + hybrid_gate.py
Phase 10: 导出 (不可跳过)                    → export_workbook.py
```



### Phase 1 拆镜解析规则

Orchestrator 在拆镜时必须按以下优先级自动区分动作与台词：

1. **动作标记前缀优先**：段落以 `△`、`动作：`、`字幕：` 或 `△闪回` 开头 → 标记为动作描述，`description` 字段写入去除前缀后的文本。**不解析台词。**
2. **冒号检测**：段落包含 `：` → 检查冒号前方的文本是否在 `project_config.character_list`、源文本角色表、已出现说话人集合或本段上下文实体中
   - 是角色名 → 解析为台词，`dialogue` 写入冒号后方文本
   - 不是角色名（如"动作"、"字幕"、"旁白"、"画外音"）→ 标记为动作描述，不解析台词
3. **口语特征二次校验**：已解析为台词的文本，执行二次校验——是否含有口语特征词（`我`/`你`/`啦`/`啊`/`吗`/`吧`/`了`/`！`/`？`/`「」` /`~`）
   - 含口语特征 → 保留为台词
   - 不含口语特征且为第三人称叙事（含`打量`/`看向`/`走向`/`走过`/`站在`/`坐着`/`路过`等动作词，且语法主语不是第一人称）→ 改为动作描述，`dialogue` 清空，文本追加到 `description`
4. **OS/内心独白检测**：段落包含 `（OS）` 或 `（内心独白）` → 文本写入 `narration` 数组，不写入 `dialogue`




### 对话时长约束（Orchestrator 拆镜时必须计算）

### dialogue_map 解析规则（pipeline.py clean() 必须遵守）
shot_plan.json 中台词的存储格式为 subshots[].dialogue_refs（字符串索引数组）+ 顶层 dialogue_map（索引到原文字典）。
pipeline.py clean() 读取台词时，不得依赖 s.dialogues 或 s.dialogue 等扁平字段——
shot 层级不存在这些字段。clean() 必须：
1. 从 shot_plan 根层读取 dialogue_map
2. 遍历每个 shot 的 subshots，收集 subshot.dialogue_refs
3. 用 dialogue_map[ref] 解析原文
4. 从 subshot.characters 取说话人，按 角色 原文 格式填入 dia 字段
5. 以 [character:角色名,text:原文] 格式填入 narr 字段
注意：同一 shot 内有多段分属不同角色的台词时，每段前标注对应的说话角色，不可全部归给第一个角色。


Orchestrator 为每个子镜头分配 duration 时，必须按台词量验证时长是否足够。

**台词语速基准：**
- 正常语速：**4.5 字/秒**
- 情绪系数调整：
  - 情绪偏快（激动/兴奋/慌乱）→ ×1.1~1.2
  - 情绪正常（平静/叙述）→ ×1.0
  - 情绪偏慢（迟疑/压抑/嘲讽/威胁）→ ×0.8~0.9

**计算公式：**
`
有效语速 = 4.5 × 情绪系数
台词所需时长 = ⌈∑(每段台词字数) / 有效语速⌉
子镜头总时长 = max(台词时长, 动作时长) + 反应空白(0.5s)  —— 对话与动作重叠时取最大值
子镜头总时长 = 台词时长 + 动作时长 + 0.5s  —— 动作需独立视觉焦点时（特写手部等）
`

**验证与拆分规则：**
- 每个 shot_plan.dialogues[] 条目已经是剧本的最小语义单元，优先按条目拆分
- 如果单条 dialogue 本身的台词时长就超了子镜头配额：
  1. 先在句号（。）/ 感叹号（！）/ 问号（？）/ 省略号（……）处拆分为更短的 dialogue 条目
  2. 如果拆分后仍超出用户输入的 `project_config.max_shot_duration`，则将该 dialogue 独立成一个新主镜头
- **拆分点优先级**（仅适用于存在自然断句的长段落）：
  1. 剧本段落分割（每段本身就是独立台词单元）—— 最优先
  2. 句号（。）/ 感叹号（！）/ 问号（？）—— 完整语义边界
  3. 省略号（……）/ 破折号（——）—— 语气中断边界
- **禁止拆分点**：逗号（，）、顿号（、）、冒号（：）、分号（；）—— 这些是同一语义单元内部的停顿，拆开会破坏语句连贯性
- 如果整条台词没有任何可拆分标记（无 。！？……——），则该条台词不可拆分，只能通过加长子镜头时长或独立成组来解决
- 台词原文不允许删减、修改，只能按完整语义单元拆分到不同子镜头
- 拆分后的新主镜头之间用"角色准备/反应 + 承接动作"连接，不使用硬切或黑场

**示例：**
`
子镜头 S3-02-01 原设计：
  碰撞动作约 2s
  系统台词①「啊啊女主出现了！男女主线终于要展开了啊！」18字 × 1.2 = 3.3s
  系统台词②「幸好幸好，虽然男主被你包养过，但男女主线还是正常在走。」25字 × 1.2 = 4.6s
  剩余空间 = 15 - max(2, 3.3+4.6) - 0.5 = 15 - 7.9 - 0.5 = 6.6s
  还在配额内，可以放在同一个主镜头。

  如果系统台词还有第三段且超出用户输入的最大时长：
  在句号处分隔 → 系统①② 放在前一主镜头，系统③独立成新主镜头+沈星雨沉默反应
`



### 镜头时长预算与 shot_plan 规范化

Orchestrator 先根据用户源文本生成 `<run_dir>\.cache\orchestrator\shot_plan.draft.json`，再用 `scripts/build_shotplan.py` 做机械规范化和引用校验。`build_shotplan.py` 不生成剧情内容，不写死角色/场景/项目名。

**预算规则：**
- 每个主镜头先按剧情节拍生成，再检查 `total_duration <= project_config.max_shot_duration`
- 若单个剧情节拍超出上限，只能按完整语义边界拆成多个连续主镜头，不得把台词删减或改写
- 若同一节拍内有多个视觉焦点，保留为同一主镜头下的多个 subshot
- 反应空白 0.5s 仅在整个 batch 提交时加一次，不在每个 ref 上单独加
- 台词时长累加是 ∑(每条台词的 _estimate_dialogue_seconds)，动作时长取 batch 内最大值
- nd(batch) = max(∑dialogue, action) + 0.5
- 切分新主镜头之间用"角色准备/反应 + 承接动作"连接

**使用方法：**
```powershell
$env:PYTHONPYCACHEPREFIX = "<run_dir>\.cache\pycache"
python scripts/build_shotplan.py <run_dir> [<run_dir>\.cache\orchestrator\shot_plan.draft.json]
```

它只规范化主Agent Orchestrator 已经根据用户源文件生成的 draft，并输出 `<run_dir>\.cache\orchestrator\shot_plan.json`。

### 上下文与批量管理

- 单次子Agent处理的 subshots 上限按技能复杂度设定（参见"分批派发规则"表格），超出时按分批投递模式 send_input
- send_back 时若原 Agent 已失活，改为重新 spawn_agent 并附带已通过的上下文摘要
- 所有子Agent输出文件采用增量追加模式：分批写入同一 JSON 文件

## 核心脚本

- scripts/pipeline_templates.py — 子Agent派发模板 + 字段类型校验 + 质量门槛
- scripts/template_prompt.py — 本地模板提示词生成
- scripts/continuity_check.py — 连续性检查
- scripts/export_workbook.py — Excel 8 sheet + Markdown 导出
- scripts/validator/ — 字段类型、质量校验
- scripts/export/markdown.py — Markdown 导出
- scripts/enhance_performance.py — 表演物理化增强引擎
- scripts/hybrid_gate.py — 脚本确定性门禁 + LLM语义复审包生成
- scripts/preflight_check.py — Phase 2 派发前的 shot_plan 前置硬门禁
- scripts/agent_handoff.py — 子Agent可恢复记忆/handoff 摘要读写
- scripts/handler_registry.py — 阶段处理器插件注册框架

## Agent 拆分原则

当前拆分说明见 `references/agent_split_review.md`。默认保留 Orchestrator、Emotion Analysis、Scene Analysis、Camera Movement、QA/Integration、Prompt Composer、QA Review/Editor 七类职责边界。新增 Agent 前必须确认它不会拆散强耦合判断：表情与语气、灯光与空间、运镜与轴线不应被无必要拆开。

## 提示词格式化标准

### 格式模板（每镜必须使用此结构）

### 镜头N（对应子镜头 {ref_id}）：
- **景别**：{中文景别}。
- **机位**：镜头位于{角色}{方向}约{距离}，{姿态}高度，{焦距}焦距，{取景范围}取景{留白备注}。
- **运镜**：{运镜类型}，{参数描述（方向/速度/幅度）}。
轴线与空间：{轴线关系}。空间：前景={}；中景={}；背景={}。
- **可见人物**：{角色列表}。
动作过程：起幅画面：{起始状态——与动作推进不同}；动作推进：{动作变化+对话传递+表情演化}，多人镜时非说话角色也须有行为描述；落幅画面：{结束状态，自然承接下一子镜头}。
- **台词**：{说话人}：「{台词原文}」
- **画外声音/OS**：{说话人}（内心独白）：「{OS原文}」

### 负面提示词
> 画面崩坏 面部扭曲 多余肢体 手指畸形 道具漂移 服饰闪烁错乱 穿模穿帮 字幕水印 低清画质 塑料质感

### 禁止写法
- 禁止标签堆砌：`[景别]MS [机位]平视 [运镜]固定` 等重复性方括号标签
- 禁止机械拼接：直接将子Agent分析字段用方括号包起来
- 禁止省略视觉风格：每条提示词必须从 project_config.json 的 visual_style 字段全文嵌入

### 必须要求
- 自然语言段落：每个维度自然写入描述段落，不使用标签前缀
- 风格约束全文嵌入：在每镜"风格约束"行嵌入 Phase 0 确认的完整 visual_style
- 细腻度：每镜提示词 ≥ 500 字符（不含镜头ID和分隔线）
- 每镜必须含：至少3个面部特征 + 具体光源设置（方向/色温/光质）+ 场景空间结构 + 角色姿态



### 分析字段 → 提示词字段映射表（Phase 6 核心执行规则）

主Agent在合并提示词时，必须按以下映射将三个子Agent的输出写入对应字段。

**emotion_output.json 字段映射（数据结构：shots[]，字段在顶层）：**
| 子Agent输出字段 | 写入提示词位置 | 特殊说明 |
|----------------|--------------|---------|
| `shots[].emotion_level` | 动作过程→情绪等级 | 单人镜直接取值，多人镜同上 |
| `shots[].facial_4d` | 动作过程→表演控制 | **注意数据结构**：单人镜时facial_4d的键名为"眼神/嘴角/呼吸/面肌"；多人镜时facial_4d的键名为**角色名**，取值后再取"眼神/嘴角/呼吸/面肌" |
| `shots[].expression_causality` | 动作过程→因果链 | 可能为字符串或字典（多人镜时以角色名为键），主Agent需做类型判断 |
| `shots[].surface_vs_deep` | 动作过程→表层≠底层 | 直接写入 |
| `shots[].pause_annotations` | 台词字段→停顿 | 有台词镜头必写 |
| `shots[].intonation` | 台词字段→语调 | 有台词镜头必写 |

**scene_output.json 字段映射（数据结构：analyses[]，键名为中文）：**
| 子Agent输出字段 | 写入提示词位置 | 特殊说明 |
|----------------|--------------|---------|
| `analyses[].空间分层.前景/中景/背景` | 轴线与空间→空间 | 写入"前景=...；中景=...；背景=..." |
| `analyses[].构图` | 机位补充 | 可选写入 |
| `analyses[].光影设计` | 光照字段 | 提取主光源方向/色温/光质/情绪光影类别/轮廓光，写入"光照：..." |
| `analyses[].场景氛围` | 动作过程→氛围前缀 | 写入角色描述前，作为"暮色冷蓝光中——"氛围前缀（无硬编码，直接取原文） |
| `analyses[].色彩基调` | 时间标签推断 | 用于推断场景时间（"冷蓝"→暮色、"暖橘"→落日），不做提示词直接输出 |

**camera_output.json 字段映射（数据结构：analysis[]，键名为英文，值为字符串）：**
| 子Agent输出字段 | 写入提示词位置 | 特殊说明 |
|----------------|--------------|---------|
| `analysis[].shot_size` | 景别 | 值为字符串（如"中景"），直接写入；如为字典取`.层级` |
| `analysis[].angle` | 机位 | 值为字符串（如"平视"），直接写入 |
| `analysis[].movement` | 运镜 | 值为字符串（如"固定镜头"），直接写入 |
| `analysis[].focal_length` | 机位补充 | 可选写入 |
| `analysis[].axis_rule` | 轴线与空间 | 必填。子Agent必须产出，clean()必须提取并传递至export() |

**数据访问路径总结（三个子Agent输出结构统一）：**
1. emotion_output.json → `d["items"]` → 数组，每元素必须有 `shot_id` + `subshot_id`
2. scene_output.json → `d["items"]` → 数组，每元素必须有 `shot_id` + `subshot_id`
3. camera_output.json → `d["items"]` → 数组，每元素必须有 `shot_id` + `subshot_id`
4. 主Agent和本地整合只能按 `subshot_id` 做一一对齐，`shot_id` 仅用于分组和合并主镜头提示词


### 子Agent输出JSON格式规范（Phase 2 spawn时必须包含）

主Agent在 spawn_agent 的 items[text] 中必须按以下格式要求嵌入输出规范。

**emotion-analysis 子Agent输出格式：**
```json
{
  "items": [
    {
      "shot_id": "S1-01",
      "subshot_id": "S1-01-01",
      "emotion_type": "中文情绪类型",
      "expression_level": "micro/visible/strong",
      "gaze": "视线方向与可见性",
      "micro_expression": "可见微表情",
      "body_tension": "身体张力",
      "body_parts_focus": "可见身体部位动作",
      "voice_tone": "台词/OV/OS语气；无台词写 none_无台词",
      "action_beat_start": "起幅状态",
      "action_beat_transition": "动作推进",
      "action_beat_end": "落幅状态",
      "emotion_trigger_short": "触发事件",
      "performance_note": "表演注意"
    }
  ]
}
```

**frames-analysis 子Agent输出格式：**
```json
{
  "items": [
    {
      "shot_id": "S1-01",
      "subshot_id": "S1-01-01",
      "space_type": "内/外/转场/物件等",
      "space_name": "场景名称",
      "char_positions": ["角色站位/坐位/视线"],
      "char_wardrobes": ["角色服装与外观连续性"],
      "bg_foreground": "前景",
      "bg_midground": "中景",
      "bg_background": "背景",
      "light_type": "主光源类型",
      "light_temp": 5200,
      "light_direction": "光源方向",
      "light_hardness": "soft/hard/mixed",
      "mood_atmosphere": "场景氛围"
    }
  ]
}
```

**camera-analysis 子Agent输出格式：**
```json
{
  "items": [
    {
      "shot_id": "S1-01",
      "subshot_id": "S1-01-01",
      "shot_size": "中文景别（全景/中景/中近景/特写/大特写）",
      "camera_lens_mm": 35,
      "camera_relative_pos": "相对主体位置",
      "camera_distance_steps": 2,
      "camera_height_relative": "齐眼/略高/略低",
      "angle_str": "平视/俯视/仰视/偏侧",
      "camera_facing_desc": "镜头朝向",
      "movement_type": "fixed/push_in/pull_out/track/pan/tilt/handheld",
      "movement_detail": "运镜参数",
      "movement_speed": "速度",
      "axis_start": "起始轴线",
      "axis_end": "结束轴线",
      "char_entry": "入画",
      "char_exit": "出画",
      "end_state": "落幅状态"
    }
  ]
}
```

**各子Agent必须遵守：**
- `shot_id` 和 `subshot_id` 必须匹配 shot_plan.json，一一对应，不可缺失
- 所有字段值使用自然语言描述，禁止纯标签堆砌
- 多人镜时 `facial_4d` 的键名使用角色名（如"沈星雨"），值取"眼神/嘴角/呼吸/面肌"
- 单人镜时 `facial_4d` 的键名直接写"眼神/嘴角/呼吸/面肌"
- 非实体角色（系统/UI等）在 `facial_4d` 中写 "N/A"
- "空间分层"中的管道符标记（`|虚实:XX%|`）属于工程残留，不应输出

## 动作与运镜描述规范


### 数据清洗规则（Phase 6 合并时必须执行）
### 数据清洗规则（Phase 6 合并时必须执行）

### AI渲染避坑规则（Phase 6 合并时检查）

1. **非物理角色过滤**：`characters` 列表中带 `（消息）`、`（UI语音）`、`（特效）` 后缀的角色，在生成机位描述时**不作为镜头主体**。机位应指向持有手机的物理人物，或使用"手机屏幕特写"等描述。
2. **轴线动态规则**：景别为"特写"、"大特写"、"近景"时，轴线描述应省略或写"不适用（特写镜头，无轴线约束）"。轴线信息只在"中景"及以上景别的双人/多人镜头中写入。
3. **占位文本过滤**：`expression_causality` 中如包含 `→→`、`正在待机→`、`...→` 等模式，该字段无效，跳过不写入提示词。
4. **手机屏幕+人脸分离原则**：同一镜头内，手机屏幕文字与人物面部表情不应同时作为视觉焦点。需要在特写镜头中看清文字的，中景镜头只展示"手机亮起+人物反应"，文字内容交给下一镜的特写处理。
5. **轴线的承上启下**：手机屏幕特写/插入镜头不传递前一镜的轴线信息，轴线在特写镜头中重置。


以下为子Agent输出数据中常见的"工程残留"，合并到提示词前必须清理：

**scene_output.json 空间分层清洗：**
- `前景/中景/背景` 的值可能包含 `|虚实:XX%|叙事功能:XX` 等管道符标记（由 frames-analysis 子Agent产出）
- **清洗规则**：合并时只保留管道符 `|` 前的纯文本内容，删除 `|虚实:`、`|叙事功能:`、`|占画面比例:` 等工程标签
- 示例：`虚化林荫树叶与零星行人背影|虚实:虚化65%|叙事功能:建立` → `虚化林荫树叶与零星行人背影`

**camera_output.json 焦距清洗：**

pipeline.py clean() 台词解析规则：
- 必须从 shot_plan.json 顶层读取 dialogue_map，不得依赖 shot 级 dialogues 字段
- 遍历 shot.subshots[].dialogue_refs，用 dialogue_map[ref] 获取原文
- dia 字段格式：角色 原文，换行用换行符隔开，同镜多段台词各自标注对应角色
- narr 字段格式：[character:角色名,text:原文]，仅含 OS/内心独白类 refs（D-MAIN-* 及类似）
- 说话角色优先使用 subshot.characters[0]，不可回退到 shot 级 intonation 字段（后者只含主角色名）

pipeline.py clean() 动作三段式构建规则：
- beat_start：从 emotion 子Agent 的 facial_4d 字典提取所有角色的初始面部状态，合并为起幅描述
- beat_end：从 facial_4d 字典的角色收束状态或从 action_beat_end 字段提取
- 若 facial_4d 字典包含多人，每角色的状态都写入，不可只写第一个角色
- export() 中 beat_start 为空时回退到 facial_4d 初始描述的模板化渲染（禁止输出空字段）

- `focal_length` 的值可能包含"标准"、"广角"等描述性后缀（如 `50标准`、`35广角`）
- **清洗规则**：只保留数字部分 + "mm"，删除"标准"、"广角"、"长焦"等后缀
- 示例：`50标准` → `50mm`，`35广角` → `35mm`

**emotion_output.json 因果链清洗：**
- `expression_causality` 的值可能为字典（多人镜时以角色名为键）或字符串
- **清洗规则**：如为字典，转为 `角色名：因果描述 | 角色名：因果描述` 格式；如为字符串直接使用


### `base_action` 可空规则

`base_action` 对人物、台词、动作表演镜头必填。仅纯空镜、环境、黑场、静帧、物件/道具插入、转场等非动作镜头可以为空。

当 `base_action` 为空时，子镜头必须同时满足：
- `characters` 为空
- `dialogue_refs` 为空
- `shot_type` / `visual_type` / `purpose` 明确标记为 `empty/background/object/environment/establishing/transition/black/still/insert` 或中文等价
- `visual_intent` / `image_subject` / `atmosphere` 至少填写一项，作为下游渲染锚点

不满足上述条件时，`preflight_check.py` 会报 `BASE_ACTION_MISSING`，不得派发 Phase 2 子Agent。

### 机位描述规则
每条机位描述必须包含以下四项，缺一不可：
- **镜头位置**：相对角色方向（正面/偏左/偏右/正侧）+ 距离（约X步/约X米）
- **镜头高度**：含角色姿态（如"平视高度（坐姿/站姿）"）
- **焦距**：具体mm数值（如"50mm焦距"）
- **取景范围**：中文景别定性（如"面部取景"、"胸部以上"、"腰部以上"、"膝部以上"、"全身"、"双人同框"）

### 景别使用规则
仅允许使用中文景别名称，禁止使用英文缩写：

| 英文 | 中文 |
|------|------|
| ECU | 大特写 |
| CU | 特写 |
| MCU | 中近景 |
| MS | 中景 |
| FS/LS | 全景 |
| ELS | 大远景 |

### 运镜描述规则
- 固定镜头：必须描述呼吸感/晃动参数（如"极轻微呼吸感手持晃动±0.5cm"）
- 推拉镜头：必须标速度（如"匀速缓慢前推约0.1m/3s"）
- 摇镜/横移：必须标方向和角度（如"跟随人物转身PAN约20°-30°"）
- 跟拍：必须标偏移距离（如"与主体保持水平距离30cm同步位移"）

### 动作过程描述规则

**三段必须不同，禁止复用同一描述文本：**

| 段落 | 描述内容 | 示例 |
|------|---------|------|
| 起幅画面 | 动作开始前的静止姿态——位置、朝向、初始表情 | 沈星雨静坐沙发中央，视线投向虚空系统UI方向，面部无表情呈放空态 |
| 动作推进 | 动作发生过程——动作顺序+对话传递+表情变化过程 | 她抬眸看向沈星洲方向，眉眼弯起乖巧弧度，以软糯语气说出"哥哥我先去休息啦"，随后自然起身 |
| 落幅画面 | 动作结束后状态——停留时长+承接方向 | 说完后略作停顿，转身步伐轻快走向楼梯方向 |

**多人镜必须：**
- 说话角色描述其动作+对话+表情变化
- 非说话角色在该镜中须有至少一个行为/反应描述（如"沈星洲在对面微微颔首回应，目光温和"）

### 台词标注规则
- 每条台词前标注说话人，格式：说话人 + 「 + 台词内容 + 」
- OS格式：说话人 + （内心独白）+ 「 + OS内容 + 」
- 消息类对话（微信等）标注消息来源方（如"江驯"、"陆序"）
- 台词、OV、OS必须来自原始 `dialogue_map` / `dialogue_refs`，禁止新增、删除、合并、改写原文台词。
- 可以增加无声动作、反应、停顿、视线、呼吸、走位来做剧情演绎，但这些新增内容不得变成新台词、字幕、旁白或内心独白。
- OV/OS 是画外音或内心声，必须标注"无口型同步/不驱动嘴部开合"；禁止写成角色开口说出、嘴唇同步、口型匹配。

### 相邻镜头轴线连续规则
- 同一场景、同一组人物的相邻镜头必须保持180度轴线，角色画面左右、视线方向、面朝对象和出入画方向要能自然承接。
- 若剧情需要越轴，必须有明确过渡理由：角色转身、镜头绕行、角色穿越轴线、空镜转场或动作方向反转，并写入 `repair_notes` / `movement_detail`。
- 没有过渡理由的左↔右互换、视线方向反跳、角色位置突变视为 blocking，退回 camera-analysis 或 QA/Integration 修正。

### 负面提示词格式规则
- 各条目之间使用空格隔断
- 禁止无分隔的全串粘连
- 标准格式：画面崩坏 面部扭曲 多余肢体 手指畸形 道具漂移 服饰闪烁错乱 穿模穿帮 字幕水印 低清画质 塑料质感

## 视觉风格贯穿规则

Phase 0 用户确认的 visual_style 字段必须贯穿管线全部阶段，不允许在任何环节丢失或省略：

1. **Phase 0**（用户确认）：visual_style 存入 project_config.json
2. **Phase 1**（Orchestrator 拆镜）：visual_style 写入 shot_plan.json 顶层字段，每镜继承基准风格
3. **Phase 2**（子Agent分析）：visual_style 随 items[text] 传入每个子Agent，作为场景设计的硬约束
4. **Phase 6**（提示词合并）：visual_style 全文嵌入每条提示词的"风格约束"行，逐镜追加该镜特定的细节补充
5. **Phase 8**（最终验证）：检查每条提示词是否包含 visual_style 全文，缺失即不合格

### 角色质感描述规范
因 visual_style 可能包含"精致角色建模、表情肌细腻、眼神高光清楚、动作幅度自然、电影级柔光"等要求，提示词中必须：

- **表情肌细腻** → 每镜至少描述3个面部部位的具体状态（眼睑/瞳孔/眉毛/嘴角/下颌/鼻翼等）
- **眼神高光清楚** → 每镜描述眼球表面反射、瞳孔高光位置、眼周光晕
- **动作幅度自然** → 描述动作的速度和幅度（如"肩部微动0.5cm"而非"动了一下"）
- **电影级柔光** → 描述光的漫射程度、阴影柔化、光比（如"面部光比1:2，阴影无硬边"）

- **多人镜动作完整性** → 2人及以上同框时，每镜动作过程必须描述所有出场角色的行为，不能只写说话人忽略聆听者。非说话角色至少有一个面部或肢体反应（如"沈星洲在对面微微颔首回应，目光温和"）。

## 铁律

8. 每镜提示词 ≥ 500 字符，必须包含 visual_style 全文、至少3个面部特征描述、具体光源设置。低于标准视为细腻度不达标，退回重写。

9. 动作过程起幅/推进/落幅三段必须不同，禁止复用同一描述文本。多人镜中所有出场角色在动作推进段均须有行为描述（说话角色+非说话角色各至少一个行为）。
10. 机位描述必须包含镜头位置（角色/方向/距离）、高度（姿态）、焦距、取景范围四项，缺一不可。景别使用中文名称（大特写/特写/中近景/中景/全景/大远景），禁止英文缩写。负面提示词使用空格隔断。

### 子Agent技能加载方式

启动分析类子Agent时，用 spawn_agent 的 items 参数传技能文件路径，不继承会话上下文：

```python
spawn_agent(
  agent_type="worker",
  items=[
    {"type": "skill", "name": "emotion-analysis", "path": "~/.codex/skills/emotion-analysis/SKILL.md"},
    {"type": "text", "text": "任务描述..."}
  ]
)
```

注意：
1. items 和 message 不能同时用，任务描述放在 items 中的 type="text" 项
2. type="skill" 必须带 path 字段指向对应 SKILL.md
3. items 数组顺序无影响，子Agent同时加载技能指令和任务描述

### 增量重试（send_back）

send_back 时只传当前仍失败的问题和子镜头：

```python
send_input(
  target=agent_id,
  message="需要修正的子镜头（已通过的5个不再列出）：
          - S1-01-01: char_count问题...
          - S1-01-03: 灯光描述不足..."
)
```

注意：不要重复发送已通过的子镜头数据或已修正的问题。

### Agent ID 追踪

每次 spawn_agent 返回的 agent_id 通过 agent_registry.py 记录到 .cache/agents.json，
后续用 send_input 在同一上下文中继续对话。失活通过 recover 动作自动重派新Agent。

### 子Agent Handoff 记忆

每个子Agent输出后，主Agent必须生成或更新 `.cache/handoff/{role}_handoff.json`。handoff 记录每个 `subshot_id` 的决策摘要、连续性锚点、未决问题和不可改边界，用于 agent 失活、上下文溢出或增量重试时恢复记忆。

失败重派时，send_back 必须携带对应失败子镜头的 handoff 摘要；新子Agent先读取 handoff，再修正当前问题，不能重新发明已通过镜头。


## 动态表演与镜头参考源（子Agent按需调用）

详细素材库已整理到 `references/dynamic_performance_reference.md`。主Agent在 Phase 2、Phase 6、Phase 7 必须把该 reference 作为子Agent参考源下发或明确要求读取，但不得要求子Agent逐条照抄。

### 调用原则

1. 先读剧本上下文，再选参考：根据每个子镜头的剧情功能、角色关系、情绪转折、台词语气、景别、时长和前后镜连续性，选择参考源中的相关条目。
2. 参考只提供候选动作、表情、运镜、光影和语气方向；最终输出必须改写成贴合本镜头人物和剧情的具体表演，不复制参考句。
3. 发生冲突时按优先级处理：剧情真实 > 角色性格 > 镜头叙事功能 > 平台稳定性 > 参考模板。
4. 若参考模板与剧本冲突，必须写明实际选择的剧情原因，并以剧本逻辑为准。
5. 每个子Agent只读取与自己职责相关的章节，避免把无关素材塞进输出。

### 子Agent参考分配

| 阶段 | 子Agent | 必读参考章节 | 输出要求 |
|------|---------|--------------|----------|
| Phase 2a | emotion-analysis | `0. 使用边界`、`1. 动态选择协议`、`面部表情控制`、`台词语气与表情动作同步` | 提炼微表情、视线、语气和情绪触发；按景别判断细节是否可见 |
| Phase 2b | frames-analysis | `0. 使用边界`、`1. 动态选择协议`、`肢体动作映射`、`光影色调与情绪匹配` | 选择空间、灯光、色彩和动作约束；确保光影服务情绪和连续性 |
| Phase 2c | camera-analysis | `0. 使用边界`、`1. 动态选择协议`、`运镜节奏与情绪匹配`、`肢体动作映射` | 根据叙事功能选择景别、焦距、机位、运动速度和轴线 |
| Phase 6 | Prompt Composer | 全文按需检索 | 把三类分析融合成自然语言提示词，不拼贴模板 |
| Phase 7/8 | QA / Editor | `调用方式`、`质量审查` | 检查五维一致性、景别可见性、模板照抄和剧情矛盾 |

### 禁止行为

- 禁止把 reference 中的成品短句原样批量粘贴到每个镜头。
- 禁止同一种情绪在连续镜头里重复同一套表情、动作、运镜。
- 禁止为了套模板改写原始剧情、台词、角色动机。
- 禁止在全景/远景里堆写瞳孔、眼神光、鼻翼等不可见微表情。
- 禁止把参考源中的平台术语、工程术语或分析过程泄露到最终提示词。
- 禁止新增、删除、改写台词/OV/OS；新增表演只能是无声动作和视觉反应。
- 禁止让 OV/OS 触发口型、嘴唇开合、唇齿同步或角色开口说话。

### 插件式阶段处理器注册

新增分析阶段不需要修改 pipeline_runner.py 核心文件：

```python
from handler_registry import register_handler

@register_handler("audio_analysis")
def handle_audio_analysis(run_dir):
    """自定义音频分析阶段处理逻辑。"""
    ...
```

同时需在 GATES 和 PHASE_ORDER 中加入新阶段配置。




### Rule 13b — Pass 2: Editor LLM Review (Editor Agent LLM审查)

After Python Pass 1 (merge_prompts.py) removes clear engineering terms from merged_full_prompts,
the Editor Agent MUST run an LLM review:

**审查指令** (每次执行):
```
你正在审查一段AI视频提示词，它已被Python初步清理（移除了dB、Hz、电平、混响时间等音频工程术语）。
请执行以下操作：
1. 语义修复：工程术语被移除后是否有句子不完整或不通顺？修复。
2. 误删恢复：是否有不应该被删除的表演描述被误删？从原文恢复。
3. 连贯性检查：清理后的提示词语义是否连贯？如不连贯，重新组织。
4. 残留清理：是否有Python遗留的或清理后残留的无用内容(如孤立逗号/数字)？移除或修复。
5. 最终确认：清理后的提示词是否可以直接用于AI视频生成？确认。
输出：只输出修复后的完整提示词文本，不输出分析过程。
```

**管线路径**: merge_prompts.py (Python Pass 1) → Editor Agent LLM (Pass 2) → validate_prompt_package.py
