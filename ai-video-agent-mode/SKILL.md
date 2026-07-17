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

## 管线执行阶段（严格顺序,不可跳过）

### Phase 0: 用户确认（每次启动必走）
启动管线前先向用户确认以下 4 项，用户回复后填入 project_config.json：

| 确认项 | 格式 | 示例 |
|--------|------|------|
| 画布/画幅 | 选择: 9:16 / 16:9 / 1:1 | `16:9` |
| 视觉风格 | 用户输入文字 | `现代都市/冷幽默` |
| 单条视频最大时长 | 选择: 5/8/10/15/18/20/25/30 秒 | `15` |
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

如果 packet 存在，主Agent必须优先让子Agent读 packet；只有 packet 缺失或损坏时，才回退到直接下发最小必要镜头数据。

### 管线阶段顺序

Phase 0:  用户确认                           → project_config.json
Phase 1:  Orchestrator (本地)               → shot_plan.json
Phase 2a: 情绪分析 子Agent ($emotion-analysis)  → emotion_output.json
Phase 2b: 场景分析 子Agent ($frames-analysis)   → scene_output.json
Phase 2c: 镜头运镜 子Agent ($camera-analysis)   → camera_output.json
Phase 3:  QA/整合 (本地+handler)            → director_pass.json
Phase 4:  Director 质量验证 (本地门禁)       → 校验通过才继续
Phase 5:  连续性检查 (不可跳过)               → continuity_check.py
Phase 6:  Prompt Composer (全走子Agent·自动调用质感参考指南)  → prompt_package.json → 校验失败重派
Phase 7:  Editor Pass 1 (不可跳过)            → merge_prompts.py
Phase 8:  Editor Pass 2 表演增强\+LLM评审 \(不可跳过\)     → enhance_performance.py + hybrid_gate.py + LLM review
Phase 9:  最终验证 (不可跳过)                 → validate_prompt_package.py + hybrid_gate.py
Phase 10: 导出 (不可跳过)                    → export_workbook.py → Excel+Markdown

### Phase 2a/2b/2c 并行下发

管线识别到 emotion_analysis 作为分析组首阶段时，返回 `batch_spawn` 动作，
同时列出 emotion_analysis、scene_analysis、camera_movement 三个角色。
主Agent应并行 spawn 三个子Agent，等待所有输出就绪后再进入 Phase 3。

### 分批派发规则（超时防护）

子Agent按技能复杂度设定不同的单批上限和超时时间。**主Agent必须严格遵守，这是防止超时的核心门禁。**

| 技能 | 单批上限 | wait_agent 超时 | 原因 |
|------|---------|----------------|------|
| emotion-analysis（情绪） | 15 镜 | 900s（15min） | 每镜需生成大量自由文本（面部四维+因果链+心理流+语调标注） |
| frames-analysis（场景） | 20 镜 | 600s（10min） | 结构化填空为主，画面模板可复用 |
| camera-analysis（运镜） | 25 镜 | 600s（10min） | 定量参数为主，负载最轻 |

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


- emotion-analysis 子Agent必须读取 `references/dynamic_performance_reference.md` 中的面部表情与台词语气同步章节，将可见的微表情、语气和生理时序按剧情改写后写入情绪分析输出

- frames-analysis 子Agent必须读取 `references/dynamic_performance_reference.md` 中的光影色调与肢体动作章节，将情绪匹配的光影方案和动作约束按场景改写后写入场景分析输出
- camera-analysis 子Agent必须读取 `references/dynamic_performance_reference.md` 中的运镜景别与肢体动作章节，将情绪匹配的运镜方案、物理法则和可见性判断写入运镜分析输出

### 子Agent重试与超时

- 子Agent最多重试 4 次（共 5 次尝试）
- 每阶段超时时间按技能复杂度设定（参见上方"分批派发规则"表格），不可统一用默认值
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
Phase 3:  QA/整合 子Agent ($content-review)    → director_pass.json
Phase 4:  连续性检查 (不可跳过)               → continuity_check.py --live
Phase 5:  Prompt Composer (全走子Agent)       → prompt_package.json → 校验失败重派
Phase 6:  Editor Pass 1 (不可跳过·自动调用质感参考指南)  → merge_prompts.py
Phase 7:  Editor Pass 2 LLM评审 (不可跳过·自动调用质感参考指南)  → hybrid_gate.py → editor_pass2_prompt()
Phase 8:  最终验证 (不可跳过)                 → validate_prompt_package.py + hybrid_gate.py
Phase 9:  导出 (不可跳过)                    → export_workbook.py → Excel+Markdown
```


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

## 动作与运镜描述规范

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
