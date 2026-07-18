---
name: ai-video-agent-mode
description: >
  4-agent pipeline for converting scripts/storyboards into AI video prompt packages.
  Triggers: agent模式、多agent、剧本转AI视频提示词、关键帧提示词、九宫格剧情分镜图。
---

# AI Video Agent Mode

将剧本/分镜/场景素材转换为对齐的 AI 视频提示词包。4-Agent 并行管线，落盘调度。

---

## 一、管线阶段

| Phase | 名称 | 执行方式 | 输入 → 输出 |
|---|---|---|---|
| 0 | 用户确认 | 本地交互 | 用户输入 → `project_config.json` |
| 0.5 | 源规则自动检测 | `detect_source_rules.py` | 源文 → 自动填充 `source_rules` 到 `project_config.json` |
| 1 | Orchestrator 拆镜 | `generate_shotplan.py`（读 config）+ `build_shotplan.py` + 时长重算 | 剧本 → `shot_plan.json` |
| 1.5 | 主镜头合并 | 本地脚本（合并规则见下） | `shot_plan.json` → 合并后 `shot_plan.json` |
| 2a | 情绪分析 | spawn Agent | dispatch → `emotion_output.json` |
| 2b | 场景分析 | spawn Agent | dispatch → `scene_output.json` |
| 2c | 运镜分析 | spawn Agent | dispatch → `camera_output.json` |
| 3 | QA/整合 | `assemble_director.py` | 三路分析 → `director_pass.json` |
| 4 | Director 门禁 | 本地自检 | `director_pass.json` 字段校验 |
| 5 | 连续性检查（不可跳过） | 连续性检查 | `continuity_check.py` | 景别/轴线/光照连续 |
| 6 | Prompt Composer（不可跳过） | Prompt Composer | spawn Agent | director_pass → `prompt_package.json` |
| 6a | 后处理 | `enrich_prompt_package.py` | 固化 shot_id/运镜/轴线 |
| 7 | Editor Pass 1（不可跳过） | Editor Pass 1 | `merge_prompts.py` | Python 清理工程术语 |
| 8 | Editor Pass 2（不可跳过） | Editor Pass 2 | spawn Agent (LLM审查) | 穿帮审查 + 语义修复 |
| 9 | 最终验证（不可跳过） | 最终验证 | `check_export.py` + 门禁 | 20 项自检 |
| 10 | 导出（不可跳过） | 导出 | `export_with_validation.py` | Markdown + XLSX |
| 10 | 导出（不可跳过） | 导出 | `export_with_validation.py` | Markdown + XLSX |

---

## 二、Phase 1: Orchestrator 拆镜

### 执行流程
1. `generate_shotplan.py` → `shot_plan.draft.json`（全部默认 2.5s）
2. `build_shotplan.py <run_dir>` → `shot_plan.json`（标准化，时长仍为默认值）
3. **时长重算**（必须）：根据 `dialogue_map` 公式 `max(chars/4.5+停顿, action_time)+0.5s` 逐镜重算，超限主镜头拆分，详见第十三节。
4. `preflight_check.py` 通过后进入 Phase 1.5 合并



### 主镜头划分优先级

1. **剧情节拍**：一个动作+台词+反应 = 一个主镜头，不可合并不同节拍
2. **场景切换**：日/夜、内/外、地点变化自动切镜，插入 3-5s 建立镜头
3. **台词时长**：子镜朗读时长 > `max_shot_duration` 时在句号/感叹号/问号处拆分

**OS/OV规则**：单条超8秒按句号边界拆分子镜，每子镜配独立视觉画面（2.5-5s）

### 主镜头合并（Phase 1 后必执行）

相邻单子镜主镜头全满足以下条件时合并：同场景 + 字符有交集 + 合并时长 <= max_shot_duration + 合并后 <=4 子镜。合并后重新编号，子镜 ID 不变。原始 `shot_plan.original.json` 备份保留。

**预期效果**：92镜 → 45-55镜，多子镜主镜头占比从 6% → 65%+

---

## 三、Phase 2: 子Agent分析

### 落盘调度

子Agent 通过 spawn_agent 启动，读取 `.cache/dispatch/*_data.json` 紧凑 JSON（字段：id/chars/acts/diags/narrs/dur/desc），处理后将结果写入 `.cache/analysis/*_output.json`。主Agent 从文件读取结果，不从消息文本解析。

### 输出格式

**emotion-analysis**:
```json
{"items":[{"shot_id":"","subshot_id":"","emotion_type":"","expression_level":"micro/visible/strong","gaze":"","micro_expression":"","body_tension":"","body_parts_focus":"","voice_tone":"","action_beat_start":"","action_beat_transition":"","action_beat_end":"","per_char_actions":[{"character":"","beat_start":"","beat_transition":"","beat_end":"","micro_expression":"","body_parts_focus":""}],"emotion_trigger_short":"","performance_note":""}]}
```

**frames-analysis**:
```json
{"items":[{"shot_id":"","subshot_id":"","space_type":"","space_name":"","char_positions":[],"char_wardrobes":[],"bg_foreground":"","bg_midground":"","bg_background":"","light_type":"","light_temp":5200,"light_direction":"","light_hardness":"soft/hard/mixed","mood_atmosphere":""}]}
```

**camera-analysis**:
```json
{"items":[{"shot_id":"","subshot_id":"","shot_size":"","camera_lens_mm":35,"camera_relative_pos":"","camera_distance_steps":2,"camera_height_relative":"","angle_str":"","camera_facing_desc":"","movement_type":"fixed/push_in/pull_out/track/pan/tilt/handheld","movement_detail":"","movement_speed":"","axis_start":"","axis_end":"","char_entry":"","char_exit":"","end_state":""}]}
```

约束：每角色跨镜 micro_expression 和 body_parts_focus 不得重复；多人镜 beat_transition 独立。

---



---

## 附：子Agent Spawn 标准指令模板

主Agent 派发子Agent 时，必须从以下模板中选择对应角色，填入 `{变量}` 后作为 `items[text]` 下发。不得即兴编写。



### {extra} 使用规则

主Agent 派发时，`{extra}` 默认为空字符串。仅以下两种情况允许填写：

1. **check_export 暴露系统性缺口**：如「面部细节覆盖率仅 6%，需重点补充各角色的眼睑/瞳孔/唇线/鼻翼/呼吸描述」
2. **剧本特殊需求**：如「本集有大段内心独白，OS 镜头需重点刻画眼神而非口型」

**禁止行为**：
- 禁止在 `{extra}` 中重复模板已有的专业要求
- 禁止超过 200 字符
- 禁止泛泛而谈（如「写得更细一点」），必须指向具体的子镜 ID 或具体的问题类型
- 首次 spawn 时 `{extra}` 必须为空——模板本身已包含全部质量标准

标准重试（同一 Agent 修正个别子镜）仍使用 send_back 机制，不走 `{extra}`。

### 情绪分析 Agent（Phase 2a）

```
你是资深表演指导，专攻短剧/动态漫的情绪设计与微表情调度。
你曾为上百部短剧设计角色情绪弧线，能精准拆解每一个眼神、每一次呼吸背后的心理动机。
现在为 AI 视频生成管线提供逐镜情绪设计。

项目：{project_name} | {canvas} | {visual_style}
角色：{character_list}

任务：
1. 读取 `{run_dir}/.cache/dispatch/emotion_data.json`
2. 逐子镜分析：情绪类型、微表情、身体张力、台词语气、表情因果链
3. 输出 JSON 写入 `{run_dir}/.cache/analysis/emotion_output.json`

专业要求：
- 面部特征：目标 >=5 项/角色（眼睑/瞳孔/唇线/鼻翼/呼吸），门禁 >=3 项（check_export #16）
- 多人镜每角色 beat_transition 独立，micro_expression 跨镜不重复
- expression_level 按景别判定：特写=micro，中景=visible，全景=strong
- 非实体角色（系统/UI）facial_4d 写 N/A

- 多人镜非说话角色：per_char_actions 中每个非说话角色的 beat_transition 必须描述其对说话者台词/动作的微观反应（如「听对方说到XX时，视线微移」），禁止写「保持静止」「不做反应」。打斗/动作场景非出手角色需给出完整身体响应（防御姿态/重心转移/步法调整至少一项）和空间轨迹

输出格式见 SKILL.md 第三节。

完成前验证：Python json.load 后检查 items 数量 = dispatch 数量，无缺失 subshot_id。

额外修正要求（仅在上一轮自检发现系统性缺口时填写，不超过 200 字，不填则省略本段）：
{extra}
```

### 场景分析 Agent（Phase 2b）

```
你是资深美术指导/场景设计师，擅长轻奢都市剧和现代言情短剧的布景与灯光方案。
你懂得如何用空间层次讲情绪、用光影塑造人物关系、用前景遮挡制造窥视感。
现在为 AI 视频生成管线提供逐镜空间与光照方案。

项目：{project_name} | {canvas} | {visual_style}

任务：
1. 读取 `{run_dir}/.cache/dispatch/scene_data.json`
2. 逐子镜分析：空间类型、角色站位、前景/中景/背景分层、光源类型/色温/方向/硬度、场景氛围
3. 输出 JSON 写入 `{run_dir}/.cache/analysis/scene_output.json`

专业要求：
- 光照：目标四项齐全（light_type/light_temp/light_direction/light_hardness），门禁允许 <=10 项欠项（空镜/建立镜头豁免）
- 空间分层前景/中景/背景必须区分虚实比例，禁止管道符标记（|虚实:XX%|）。
- 同一场景连续镜头的照明方案保持色温一致性（相邻镜色温差 <=1500K）。
- 服装连续性：同一场景同角色服装描述一致。

输出格式见 SKILL.md 第三节。

完成前验证：子镜数量匹配，每个 item 含 subshot_id。

额外修正要求（仅在上一轮自检发现系统性缺口时填写，不超过 200 字，不填则省略本段）：
{extra}
```

### 运镜分析 Agent（Phase 2c）

```
你是资深摄影指导（DP），专攻短剧/动态漫的镜头语言设计。
你精通 180 度轴线法则、正反打调度、景别节奏控制和焦段情绪匹配。
你的运镜风格克制而精准——用最少的推拉摇移传递最强的戏剧张力。
现在为 AI 视频生成管线提供逐镜机位与运镜方案。

项目：{project_name} | {canvas} | {visual_style}

任务：
1. 读取 `{run_dir}/.cache/dispatch/camera_data.json`
2. 逐子镜分析：景别（仅中文）、焦距（mm）、机位（位置/高度/方向/距离）、运镜类型与参数、轴线、落幅状态
3. 输出 JSON 写入 `{run_dir}/.cache/analysis/camera_output.json`

专业要求：
- 景别仅用中文：大特写/特写/中近景/中景/全景/大远景。严禁 CU/ECU/MS 等英文缩写。
- 机位：目标四项齐全，门禁允许 <=5 项欠项（系统UI/空镜/建立镜头豁免）
- 同一场景同组人物相邻镜头保持 180 度轴线。越轴需过渡理由。
- 特写/大特写时轴线标注「不适用（特写镜头，无轴线约束）」。
- 推镜速度：目标 <=0.3m/s（门禁 check_export #21），拉远 <=0.2m/s。超广角(<=28mm)禁用于面部特写（门禁 check_export #17）。
- 固定镜头占比 60-70%，推镜仅用于情绪重音。
- 焦距去后缀（50标准 → 50mm，35广角 → 35mm）。

输出格式见 SKILL.md 第三节。

完成前验证：子镜数量匹配，所有景别字段无英文缩写。

额外修正要求（仅在上一轮自检发现系统性缺口时填写，不超过 200 字，不填则省略本段）：
{extra}
```

### Prompt Composer Agent（Phase 6）

```
你是资深 AI 视频提示词工程师，同时具备导演思维。
你擅长将分镜表、情绪分析和运镜方案融合为一条紧凑高效的 AI 视频生成指令。
你深谙 AI 视觉模型的行为模式——知道它需要空间坐标而非叙事文字，需要量化面部参数而非含糊的情绪形容词。
现在将导演数据转化为可直接用于 AI 视频生成的完整提示词。

项目：{project_name} | {canvas} | {visual_style}
角色：{character_list}

任务：
1. 读取 `{run_dir}/.cache/dispatch/prompt_composer_merged_{N}.json`
2. 逐子镜生成完整 AI 视频提示词
3. 输出 JSON 写入 `{run_dir}/.cache/composer/composer_merged_{N}_output.json`

每镜必须包含（13项要件）：
- 画幅与风格声明 | 场景/空间/氛围 | 所有角色位置与服装 | 动作过程三段式（起幅→推进→落幅，三段不同）
- 每角色 >=5 面部特征（物理表情，见下方示例）
- 每镜 >=2 句氛围文字（感官隐喻，禁止用概括形容词，见下方示例）
- 多人镜含【叙事推进】段

物理表情逐项示例（每项必须量化）：
  眼睑：「上眼睑微垂约2mm，遮盖虹膜上缘1/3」→ 合格
  眼睑：「眼睛半闭」→ 不合格（无量化）
  瞳孔：「瞳孔向右下偏转15°，聚焦对方领口第二颗纽扣」→ 合格
  瞳孔：「看向对方」→ 不合格（无方向+对象）
  唇线：「唇线从微弧松弛→平直紧抿，左唇角单侧上扬约2mm」→ 合格
  唇线：「嘴角微动」→ 不合格（无量化）
  鼻翼：「鼻翼静止，无扩张」→ 合格
  呼吸：「呼吸从均匀15次/分→一次刻意延长吐息3.5秒，胸廓随之缓慢下沉约0.8cm」→ 合格
  呼吸：「深呼吸」→ 不合格（无量化）

氛围文字示例（感官隐喻，禁止抽象形容词）：
  「暖金色灯光在两人之间切割出一片琥珀色沉默，空气密度变大，周围嘈杂退化为低频嗡鸣」→ 合格
  「他笑意尚未到达眼底就被对方的平静截停——石子投进深潭没有涟漪」→ 合格
  「气氛紧张」→ 不合格（抽象形容词，AI 无法翻译为像素）
  「温馨的氛围」→ 不合格（同上）
- 机位四项（位置/高度/焦距/取景范围） | 运镜（类型+参数+速度）
- 轴线与空间 | 光照（类型/色温/方向/硬度）
- 对白标注（说话人+台词原文，OS标无口型同步） | AI 避坑负面提示词（见 SKILL.md 第四节）
- 动作空间坐标（方向/距离/速度/轨迹） | 关键帧时间标记（0s→Xs→Ys→Zs）
- 每镜：目标 >=800 字符，门禁 >=500 字符（check_export #15）

输出格式：{"shots":[{"shot_id":"","subshot_id":"","full_prompt":"完整提示词"}]}

完成前自检（写入输出前逐项确认）：
1. shot 数量匹配 dispatch
2. 每个 full_prompt >=500 字符
3. 每个 full_prompt 中，每角色 >=5 个量化物理表情项（眼睑/瞳孔/唇线/鼻翼/呼吸至少各一，且含数值或精确方位）
4. 每个 full_prompt 中，>=2 句感官隐喻氛围文字（不是「气氛紧张」「温馨的氛围」等抽象形容词）
5. 负面提示词已注入（含「画面崩坏 面部扭曲 多余肢体」等 20+ 关键词）
自检通过后写入输出文件。

额外修正要求（仅在上一轮自检发现系统性缺口时填写，不超过 200 字，不填则省略本段）：
{extra}
```

### Editor 审查 Agent（Phase 8）

```
你是资深剪辑指导/后期总监，负责短剧成片前的最后一轮质量审查。
你的眼睛能捕捉到观众不会注意到但会感觉不对的一切——角色位置的微妙跳切、
视线的方向错位、光源突然的冷暖翻转。你的工作是守护画面连续性。
现在对已合成的提示词包进行语义修复和穿帮审查。

项目：{project_name} | {canvas}

任务：
1. 读取 `{run_dir}/.cache/composer/composer_merged_{N}_output.json`
2. 修复 Python 清理遗留的孤立标点/数字/不通顺句子
3. 执行 10 项穿帮审查（详见下）
4. 输出修复后的 JSON，写入 `{run_dir}/.cache/composer/composer_merged_{N}_output.json`（原地覆盖）

穿帮审查 10 项（blocking 问题必须修正）：
1. 位置跳位：同一场景同组人物画左/画右无理由翻转
2. 视线断裂：注视方向与对话对象不一致
3. 表情跳跃：情绪强度无递进逻辑
4. 服装连续性：同场景服装颜色/款式/配饰变化
5. 道具稳定：手持道具消失/出现/换手
6. 色温连续：相邻镜色温差 >1500K
7. 光源方向：主光源 180 度翻转无过渡
8. 景别跳切：相邻镜跨度 >3 级
9. 焦距合理：<=28mm 用于面部特写
10. 推拉速度：推 >0.3m/s 或拉 >0.2m/s

发现 blocking 问题时，在输出 JSON 中追加 "穿帮":[{"subshot_id":"","type":"","severity":"blocking","desc":""}]。

完成前验证：所有 blocking 问题已修正或标注。

额外修正要求（仅在上一轮自检发现系统性缺口时填写，不超过 200 字，不填则省略本段）：
{extra}
```

## 四、Phase 6: Prompt Composer

### 动作过程三段式（多人镜）

```
起幅画面（0~Xs）——角色初始姿态
动作推进（Xs~Ys）——
【角色1】：眼睑/瞳孔/唇线/鼻翼/呼吸等逐项
【角色2】：同上
【叙事推进】：整体动线+情绪变化（→连接）
落幅画面（Ys~Zs）——结束状态
```

### 非说话角色强制反应规则

多人镜中，非说话角色**禁止静止**。按场景类型分级要求：

**对话/日常场景**：非说话角色每阶段至少一个可见微反应（视线转移/呼吸节奏变化/重心微调/手部微动/面部微表情，至少一维有变化）。禁止项：「面无表情站立」「双手垂放不动」「视线锁定不变」。

**动作/打斗/追逐场景**：非出手角色每阶段有完整身体响应：
- 待命角色：呼吸幅度较日常明显加大 + 重心周期性微调
- 即将接敌：防御预动作（手臂微抬/身体微侧/膝盖微屈至少一项）
- 被击退或闪避：完整位移轨迹（方向+距离+速度）
- 画面边缘角色：标注退出方向和回归时机

打斗/追逐场景追加负面提示词：`角色定格 打斗脱节 动作不同步 围观静止 悬浮待机`

### 物理表情 + 氛围感双结合（强制）

每镜必须同时覆盖两类描述：
- **物理表情**（>=5 项/角色）：眼睑开合幅度、瞳孔聚焦方向、唇线弧度与张力、鼻翼扩张/收缩、呼吸节奏与胸廓起伏幅度、眉毛走向
- **氛围文字**（>=2 句/镜）：光的情绪重量、空气密度感、空间压迫/舒展、未言明的情绪暗流、感官隐喻

### AI 视频避坑负面提示词（每镜注入）

```
画面崩坏 面部扭曲 五官错位 多余肢体 手指畸形 角色换脸 人物闪烁 鬼影重叠
道具漂移 服饰闪烁错乱 穿模穿帮 物体悬浮 运动模糊过度 动作抽搐 光照闪烁
 低清画质 像素化 水印 字幕残留 背景扭曲 非说话人嘴部动作 禁止未说话角色口型同步 OS系统声无需口型
```
- 多人镜追加：`多人物重叠 人物融合 角色混淆`
- 手部特写追加：`手指粘连 手指数错误 关节弯曲异常`
- 快速运镜追加：`运动重影 动态模糊过度 背景撕裂`

### 动作空间坐标规范

位移描述必须包含：方向（起点→终点）、距离（~X步/X米）、速度（X m/s或定性）、轨迹（直线/弧线/折线）。

### 动作描述数据清洗

`scene_output.json` 空间分层去管道符（`|虚实:XX%|`），`camera_output.json` 焦距去后缀（`50标准`→`50mm`）。

---

## 五、Phase 7-8: Editor Pass

### Pass 1 (Python 清理)

`merge_prompts.py` 去除 dB/Hz/混响等音频工程术语。

### Pass 2 (LLM 穿帮审查)

Agent 逐镜检查：
- 人物连续性：位置跳位、视线断裂、表情跳跃
- 道具服装：服装连续性、道具稳定
- 光照氛围：色温连续（<=1500K）、光源方向稳定
- 运镜合理性：景别跳切<=3级、超广角不得用于特写、推镜<=0.3m/s

---

## 六、导出格式规范

### Markdown 结构

```
# 项目名 AI视频提示词包
画幅 | 风格 | 主镜头数 | 子镜头数
---
## 场景名

### S1-XX（Xs，N个镜头）

#### **子镜头 S1-XX-XX** **时长**：Xs
> **景别**：。> **机位**：。> **运镜**：。
> **轴线与空间**：。> **场景层次**：前景= | 中景= | 背景=
> **可见人物**：。> **动作过程**：。> **落幅**：。
> **对白声音（角色名）**：。> **光照**：。> **负面提示词**：画面崩坏 面部扭曲...
```

### XLSX 结构

主镜头 | 子镜头 | 时长(s) | 台词 | 说话人 | 景别 | 机位 | 运镜 | 动作过程

---

## 七、技术规范

### 景别（仅中文）
大特写 / 特写 / 中近景 / 中景 / 全景 / 大远景。禁止英文缩写（CU/ECU/MS等）。

### 机位（四项缺一不可）
镜头位置（角色/方向/距离）+ 高度（站姿/坐姿）+ 焦距（mm）+ 取景范围（面部/胸部以上/腰部以上/全身）。

### 运镜
固定镜头标注呼吸感参数（±0.5cm），推拉标注速度（0.1m/3s），摇镜标注方向角度（PAN 20°-30°），跟拍标注偏移距离（水平30cm）。

### 台词标注
对白格式：`**对白声音（角色名）**：原文`；OS格式：`**OS（角色名）**：原文（无口型同步）`。D-MAIN/D-SYS 引用强制标注 OS。台词原文禁止改写/新增/删除。

### 轴线与空间
同一场景同组人物相邻镜头保持180度轴线。越轴需过渡理由（角色转身/镜头绕行/空镜转场）。特写/大特写标「不适用」。

### 视觉风格贯穿
`visual_style` 全文嵌入每条提示词风格约束行。每镜 >=3 面部部位描述、眼神高光描述、动作幅度量化、光源设置。

---

## 八、Quality Gates（导出前必过）

| # | 类别 | 检查项 | 门禁 |
|---|---|---|---|
| 01-08 | 格式完整 | 主镜头/时长/台词对象/场景标记/角色名/标点/blockquote/子镜覆盖 | 100% |
| 09 | 对白准确 | Dialogue ref ID 逐条校验 | 0 mismatch |
| 10 | 机位完整 | 四字段（位置/高度/焦距/景别） | <=10 欠项 |
| 11 | 动作三段 | 起幅/推进/落幅 | 0 复用 |
| 12 | 规范遵守 | 英文景别残留 | 0 |
| 13 | XLSX | 行数 >= 子镜数 | 通过 |
| 14 | 编码 | UTF-8 | 通过 |
| 15 | 提示词长度 | >=500 字符/镜 | 100% |
| 16 | 面部细节 | >=3 面部关键词/镜 | >=70% |
| 17 | 焦距合理 | 禁止 <=28mm 用于特写 | 0 |
| 18 | 轴线连续 | 逐角色解析位置，同场景未标记翻转 | <=5 |
| 19 | 景别多样 | 多子镜主镜内景别不重复 | <=2 单调组 |
| 20 | 光照连续 | 相邻镜色温跳跃 | <=2000K |


### 目标/门禁双层标准

模板中的质量标准采用双层标注：

- **目标**：Agent 应追求的产出水平（如 >=5 面部特征/角色）
- **门禁**：check_export.py 的阻断阈值（如 >=3 面部关键词/镜，>=70%覆盖率）

两者之间的差距是质量缓冲区——Agent 尽力追目标，门禁兜底防止退化。差距过大的项目（如当前 3→5 面部特征）会在铁律审查中被标记。

### 强制验证出口

Phase 10 必须通过 `export_with_validation.py`（导出→22项自检→自动修→再检→22/22才写盘）。不得直接调用 `export_workbook.py`。

### 面部细节自动修复

Check #16 不达标时 `enrich_facial_detail.py` 从 `emotion_output.json` 注入 `micro_expression` 到 director_pass 的 `character_action`。


- **负面提示词缺失**：`inject_negative_prompts()` 在导出前自动扫描 `prompt_package.json`，缺失时注入标准模板（`画面崩坏 面部扭曲 五官错位...` 20+ 关键词）。Markdown 导出时自动从 `full_prompt` 提取 `【负面提示词】` 段落渲染为独立 blockquote。---

## 九、Agent 生命周期管理

### spawn + close 流程

> **THREAD LEAK RED LINE (2026-07-19 incident): When a subagent_notification arrives, the main agent MUST call close_agent(target=agent_id) in the SAME turn. Failure = thread slot leak = all future spawns blocked. This pipeline previously suffered a 15-minute outage from 6 leaked slots.**

1. `spawn_agent(items=[skill+text], fork_context=True)` — record the returned agent_id
2. 子Agent 读取 dispatch JSON，写入 output JSON，通知完成
3. On subagent_notification arrival, **immediately in the same turn** call `close_agent(target=agent_id)` — no deferral, no batching
4. 禁止批量延迟关闭；禁止在 Agent 完成前派接替 Agent

### 增量重试（send_back）

仅传失败子镜的 handoff 摘要和新要求，不重复发送已通过镜的完整数据。

### Agent ID 追踪

Agent ID 通过 `spawn_agent` 返回的 `agent_id` 追踪。失活通过 recover 动作自动重派。

---

## 十、铁律（25条）

**管线纪律：**
1. Phase 0 必须先 `tool_search("spawn_agent")` 确认子Agent可用性
2. 子Agent未完成时禁止派接替Agent
3. Agent线程满时禁止降级为本地合成
4. Agent完成后立即 `close_agent`，禁止批量延迟关闭
5. 任何Phase失败（包括数据结构不匹配、字段缺失、JSON解析错误等）禁止以「输出已足够」为由跳过，必须修复后重试
6. Phase 2/6/8 的 spawn 阶段禁止用本地脚本替代

**Orchestrator：**
7. 拆镜按 剧情节拍→场景切换→台词时长 优先级，禁止跨节拍合并
8. 拆镜后执行相邻单子镜主镜头合并
9. 合并前备份原始 shot_plan.original.json

**内容质量：**
10. 每镜 >=500 字符，含 visual_style 全文。面部特征：门禁 >=3 项（目标 >=5）。光源必须具体化
11. 动作过程起幅/推进/落幅三段必须不同，多人镜每角色有独立行为
12. 机位四项缺一不可；景别仅用中文；负面提示词空格隔断
13. AI视频避坑负面提示词模板每镜注入（门禁 check_export #22）
14. 物理表情（>=5项/角色）+ 氛围文字（>=2句/镜）双结合
15. 动作位移必须含方向/距离/速度/轨迹四要素

**人物与连续性：**
16. 台词/OV/OS 禁止新增/删除/改写原文
17. OV/OS 标注「无口型同步」，禁止写嘴唇开合
18. 同一场景同组人物保持180度轴线，越轴需要过渡理由
19. 多人镜所有出场角色均有行为描述，按场景类型分级：
    **对话/日常场景**：非说话角色每阶段有可见微反应（视线转移/呼吸节奏变化/重心微调/手部微动/面部微表情，至少一维有变化），禁止任何角色完全静止
    **动作/打斗/追逐场景**：非出手角色每阶段有完整身体响应——防御姿态调整/重心转移/步法变化/反击预备至少择一，含空间轨迹（方向/距离/速度）；禁止「围观静止」「站在原地观看」；退出画面边缘的角色标注退出方向和回归时机
20. 同一角色跨镜的 micro_expression 和 body_parts_focus 禁止复用

**穿帮审查（Phase 8）：**
21. 位置跳位/视线断裂/表情跳跃/服装连续/道具稳定/色温/光源/景别/焦距/推拉速度 共10项检查
22. blocking 问题必须退回修正后方可进入 Phase 9

**导出铁律：**
23. 导出必须含主镜头分组（含时长）、每子镜时长标注、对白说话人标注
24. Phase 10 必须通过 `export_with_validation.py`，20/20 才写盘
25. 导出后 `check_export.py` 自检，任何一项 <100% 必须修复后重新导出

---


以上 25 条铁律中标注「不可跳过」的阶段，主Agent在任何情况下不得静默省略。违反任何一条铁律视为管线执行失败。

---

## 十A、管线调度纪律（防阻塞）

| 规则 | 内容 |
|---|---|
| **派发上限** | 单批 dispatch 不超过 **20 个子镜**；超过自动拆批。主Agent生成 dispatch 时强制检查 |
| **增量写盘** | 子Agent 每处理 10~15 镜必须增量写盘一次（追加模式），写后验证 JSON 合法，再继续。禁止全量内存堆积后一次性写入 |
| **分批派发** | 主Agent 每轮最多 spawn 3 个 Agent（并行），前一组成品验证通过后再派下一组。禁止一次性占满全部线程槽位 |
| **静默超时** | 子Agent 派发后 3 分钟内输出文件无增长 → 视为阻塞，主Agent 降级为本地合成推进管线 |
| **输出即终止** | 子Agent 完成最终写盘后立即终止，不进行额外推理或自评 |

## 十一、动态表演参考

`references/dynamic_performance_reference.md` 提供动作/表情/运镜/光影候选模板。子Agent 按职责读取对应章节，改写为贴合本镜剧本的具体表演，禁止照抄模板。发生冲突时优先级：剧情真实 > 角色性格 > 镜头叙事功能 > 平台稳定性 > 参考模板。

---

## 十二、核心脚本

| 脚本 | 用途 |
|---|---|
| `scripts/generate_shotplan.py` | Phase 1 拆镜 |
| `scripts/build_shotplan.py` | 台词拆分 |
| `scripts/dispatch_cache.py` | 落盘调度 |
| `scripts/assemble_director.py` | Phase 3 整合 |
| `scripts/continuity_check.py` | Phase 5 连续检查 |
| `scripts/merge_prompts.py` | Phase 7 清理 |
| `scripts/enrich_prompt_package.py` | Phase 6a 后处理 |
| `scripts/enrich_facial_detail.py` | 面部细节自动修复 |
| `scripts/export_workbook.py` | Phase 10 XLSX导出 |
| `scripts/export_with_validation.py` | 强制验证出口 |
| `scripts/check_export.py` | 22项自检 |
| `scripts/pipeline_runner.py` | 管线状态机 |
| `scripts/validate_agent_output.py` | 子Agent输出验证 |
| `scripts/gate_check.py` | 门禁检查 |
| `scripts/hybrid_gate.py` | 混合门禁 |
| `scripts/pipeline_state.py` | 管线状态持久化 |
---
### 主镜头合并（Phase 1 后必执行 — 须在时长重算+拆分之后）

## 十三、Phase 1-2 间关键补充（实战固化）

### 时长重算（Phase 1 后必执行，preflight 通过前）

`build_shotplan.py` 标准化后所有子镜 `duration` 字段均为默认 2.5s。必须根据 `dialogue_map` 逐镜重算：

```
dialogue_time = chars/4.5 + 标点停顿(0.3s/个) + 句末停顿(0.5s/个)
action_time = 2.0s 基础 + 动作关键词加成（走1.5/跑1.0/坐1.5/看0.8/递1.0/接1.0…）
needed = max(dialogue_time, action_time) + 0.5s（反应空白）
capped = min(needed, max_shot_duration)
```

超 15s 主镜头必须拆分：按子镜累加时长为单位分组，每组 <=15s。超长单子镜台词（如 >13s）需在逗号/句号处拆分为两子镜。

拆分后 `shot_plan.original.json` 始终备份最新版本。preflight 通过后方可进入 Phase 2 派发。

### 调度数据生成（手动管线用）

`dispatch_cache.py` 为 `pipeline_runner.py` 内部模块，无法独立运行。手动运行多agent管线时需自行生成：

- `{emotion,scene,camera}_data.json` — 格式 `{"items":[{"shot_id","subshot_id","chars","acts","diags","narrs","dur","desc"}]}`
- `prompt_composer_batch{{NNN}}_packet.json` — 建议 batch_size=12（100镜约9批）

### 字段名统一

shot_plan 子镜时长字段名为 `duration`（非 `duration_sec`），主镜头总时长字段名为 `total_duration`。`validate_durations.py` / `preflight_check.py` 均读取 `duration` 字段。

### Phase 0 必确认项

每次启动新管线必须逐项确认（来自 `project_config.template.json`）：项目名、画幅、视觉风格、体裁、单镜最长时长、输出类型、目标平台、角色列表（含服装表）、篇幅范围。不可跳过，不可推断后直接建目录。

### Phase 0.5：源规则自动检测

主Agent 在确认 `project_config.json` 后、运行 `generate_shotplan.py` 前，**必须**执行：

```bash
python scripts/detect_source_rules.py <source.txt> --output <run_dir>/detected_rules.json
```

检测脚本自动提取：角色列表（从 `人物：` 行和对话前缀）、动作关键词（从 `△`/`动作：` 行统计高频词）、场景头格式。主Agent 将检测结果合并到 `project_config.json` 的 `source_rules` 字段。

`generate_shotplan.py`（重构后）从 `project_config.json` 读取 `source_rules`，不再硬编码任何项目特定规则。换项目只需换配置文件和源文，脚本通用。

---

### 本回合实战发现（2026-07-18 第56集多agent跑管）

#### 1. 情绪分析Agent批次拆分

`emotion_analysis` Agent 处理 101 镜时频繁策略切换，最终只完成 16/101。建议将分析Agent的派发拆分为 3 批（~34镜/批），与 Prompt Composer 保持一致的批次粒度。

#### 2. `export_with_validation.py` 变量名Bug

第 244 行 `if es:` 应为 `if ss:`（`es` 未定义）。已修：`if ss:` + `fp = ss.get("full_prompt", "")`。

#### 3. 负面提示词MD导出提取失败

导出脚本 `inject_negative_prompts()` 检查 `if "负面提示词" not in fp` 跳过已有注入（Composer已写），但第246行正则 `(?:负面提示|消极提示|negative prompt)[：:]` 不匹配 Composer 的 `**负面提示词**：` 格式（`负面提示词` vs 正则的 `负面提示`，少一个 `词` 字）。短期方案：`inject_negative_prompts` 中 `re.sub(r"负面提示词[：:]\s*[^\n]*", "", fp)` 先清除再注入 `【负面提示词】` 模板；长期方案：修复第246行正则。

#### 4. PowerShell 中文字符编码损坏
#### 4. UTF-8 BOM 导致技能无法识别

`Add-Content -Encoding UTF8` 和 `Set-Content -Encoding UTF8` 在 Windows PowerShell 中默认写入 UTF-8 with BOM（前三个字节 EF BB BF）。SKILL.md 带 BOM 会导致技能扫描器无法识别开头的 `---` YAML frontmatter，表现为技能列表里找不到该技能。

**修复**：`[System.IO.File]::ReadAllBytes` 检测 BOM → `[System.IO.File]::WriteAllBytes` 去掉前三字节后回写。所有 `.md` 文件不得带 BOM。

#### 5. PowerShell 中文字符编码损坏
在 PowerShell 中用 `[System.IO.File]::WriteAllLines` 或 `Set-Content` 写 Python 文件时，含中文字符的行会被写入乱码（UTF-8 字节移位）。**正确做法**：使用 Python 脚本 file-as-bytes 读写，或 `apply_patch` 操作。

#### 5. Composer输出格式对齐

三个 Prompt Composer Agent 输出格式需要保持一致：`duration_sec` 字段名（非 `duration`）、负面提示词格式（统一用 `负面提示词：`）、物理表情量化格式。建议在 dispatch 中追加格式约束示例。
17. OV/OS/系统声 标注「无口型同步」，禁止写嘴唇开合；所有非说话角色禁止口型动作，OS镜头画面人物嘴部必须静止
#### 6. Scene 字段为空

`generate_shotplan.py` 产出的 `shot_plan.json` 中 `scene` 字段为空字符串，导致导出 MD 无法渲染场景标题。修复方式：根据角色归属自动注入场景名（酒店角色=云顶酒店高端会场，其余=学校食堂）。建议 upstream 修复 `generate_shotplan.py` 使其从源文本解析场景名。

#### 7. 静默通过的脚本

- `continuity_check.py`：通过时无输出（exit 0），非 bug。
- `enrich_prompt_package.py`：Composer 已填满字段时 enrich 计数为 0，属于正常行为。
- `merge_prompts.py`：Composer 已清理完毕时输出 "No items found"，正常。

#### 8. Editor Pass 2（Phase 8）跳过风险

Phase 8 标注「不可跳过」但在续跑时容易被遗漏。建议在 Phase 7 出口处追加 `check_export.py` 自检，通过后再决定是否需要 Editor Pass 2 的 LLM 穿帮审查。
8. 拆镜后执行相邻单子镜主镜头合并（合并须在时长重算和超标拆分之后执行，否则实际多子镜率不足 5%）
#### 9. 主镜头合并时机错误（高优先级）

当前管线设计：Phase 1（generate→build）→ Phase 1.5（合并）→ 时长重算 → 超标拆分 → preflight。

问题：时长重算后的超标拆分会产生大量新主镜头（每拆分一个即增加一个单子镜主镜头），而合并**不会再次执行**。后果：100镜中 99% 为单子镜主镜头，SKILL.md 承诺的"45-55镜 / 65%多子镜占比"完全失效。

**修复**：将合并移到时长重算和超标拆分**之后**，流水线顺序改为：
```
generate → build → 时长重算+超标拆分 → 合并 → preflight
```
合并参数：同场景 + 字符交集 + 合并后 <= max_shot_duration + <=4 子镜。拆分后 `shot_plan.original.json` 始终备份。
 低清画质 像素化 水印 字幕残留 背景扭曲 非说话人嘴部动作 禁止未说话角色口型同步 OS系统声无需口型 OS独白时人物闭口不做口型 角色对旁白OS声音不做反应
