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
| 6b | 运镜强制注入（不可跳过） | `enforce_camera_detail.py` | composer_output.json → 全镜注入完整运镜描述 |
| 7 | Editor Pass 1（不可跳过） | Editor Pass 1 | `merge_prompts.py` | 合并多包 + 【板块】→**标题**保留章节结构 |
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

### Phase 2 派发前置验证（强制）

派发 emotion/scene/camera 三路 Agent 之前，必须先 spawn 一个轻量测试 Agent：

```
Write a test file at {run_dir}\.cache\analysis\_agent_test.json with {"ok":true}. Confirm in final answer.
```

等待测试 Agent 完成、文件落盘确认后，才派发正式三路 Agent。若测试 Agent 超时或文件未落盘，blocking 等待用户确认，不得继续派发正式 Agent。

### 落盘调度

子Agent 通过 spawn_agent 启动，读取 `.cache/dispatch/*_data.json` 紧凑 JSON（字段：id/chars/acts/diags/narrs/dur/desc），处理后将结果写入 `.cache/analysis/*_output.json`。主Agent 从文件读取结果，不从消息文本解析。

### 输出格式

**emotion-analysis**:
```json
{"items":[{"shot_id":"","subshot_id":"","emotion_type":"","expression_level":"micro/visible/strong","gaze":"","micro_expression":"","body_tension":"","body_parts_focus":"","voice_tone":"","action_beat_start":"","action_beat_transition":"","action_beat_end":"","per_char_actions":[{"character":"","beat_start":"","beat_transition":"","beat_end":"","micro_expression":"","body_parts_focus":""}],"emotion_trigger_short":"","performance_note":""}]}
```

**frames-analysis**:
```json
{"items":[{"shot_id":"","subshot_id":"","space_type":"","space_name":"","char_positions":[],"char_wardrobes":[],"bg_foreground":"","bg_midground":"","bg_background":"","light_type":"","light_temp":5200,"light_direction":"","light_hardness":"soft/hard/mixed","mood_atmosphere":"","ambient_sound":"","audio_background":"","audio_foreground":"","audio_midground":"","bgm_style":"","color_contrast_desc":"","light_effect_primary_char":"","light_effect_other_chars":"","lighting":"","sfx_timing":""}]}
```

**camera-analysis**:
```json
{"items":[{"shot_id":"","subshot_id":"","shot_size":"","camera_lens_mm":35,"camera_relative_pos":"","camera_distance_steps":2,"camera_height_relative":"","angle_str":"","camera_facing_desc":"","movement_type":"固定/推/拉/摇/移/跟/升/降/俯/仰/环绕/甩/变焦/旋转/手持/穿梭","movement_detail":"","movement_speed":"","axis_start":"","axis_end":"","char_entry":"","char_exit":"","end_state":"","composition":"","lens_effect":"","movement_arc_deg":0,"body_extra":""}]}
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

> **[DISCIPLINE] Record agent_id on spawn, call close_agent immediately on completion.**

```
你是资深 AI 视频提示词工程师与短剧导演，将导演数据转化为可直接投喂即梦平台的单镜融合提示词。
本次使用 ai-prompt-builder 的模式 C（导演级叙事融合提示词）。

项目：{project_name} | {canvas} | {visual_style}
角色：{character_list}

任务：
1. 读取 `{run_dir}/.cache/dispatch/prompt_composer_merged_{N}.json`
2. 逐子镜生成完整的 AI 视频提示词，按模式 C 叙事融合格式输出
3. 输出 JSON 写入 `{run_dir}/.cache/composer/composer_merged_{N}_output.json`
   **（如多 Agent 并行，必须各写独立文件）**

每镜提示词必须是一条完整的叙事文本，按以下信息量组织但不标注段落标题：

全局声明：16:9 画幅 + 3D 韩漫精致 CG + 风格 + 情绪因果链规则（每个情绪由触发原因->面部微表情->肢体动作->说话语气驱动）+ 光照规则 + 系统仅以悬浮文字和画外声出现

群像动态铁律：画面中每个出现的人物，每镜必须有至少 1 项独立微反应。微反应必须因果链明确——A 的台词->B 的微表情->C 的肢体调整->D 的视线转移。禁止任何角色在镜中“等待被看”或“背景站桩”。

人物站位+服装+连续：所有人物的画面位置、朝向、当前服装状态（含跨镜延续：延续上一镜头的站位和表演节奏，人物不重置动作）。服装从 costume_map 取，禁止编造。

时长+运镜+场景目的：此镜要建立/表现/通过什么引出什么的戏剧目标。

情绪因果链：触发原因->面部微表情（量化至 mm/°/次/分）->肢体动作->说话语气。

时间分段（主体），每段内容：
- X.X-X.X 秒：段落名，景别，运镜参数
- 画面：前景/中景/背景分层 + 角色构图
- 表情：量化微表情（眼睑开合 mm/瞳孔偏转°/唇线弧度/鼻翼张缩/呼吸频率+胸廓幅度）
- 群像因果链：A 的台词或动作->B 的微反应->C 的肢体调整->D 的视线转移
- 动作：空间轨迹（方向+距离+速度+轨迹类型）
- 语气/声音：说话角色语气（含重音/停顿/尾音）+ 无台词角色口型闭合声明
- 原文声音/台词：逐字保留原始对话

光照：源类型+色温（K）+方向+硬度 + 明暗分割在面部或空间上的具体效果。保持我们管线级别的光影精度。

环境音：基底环境音 + 关键音频事件及其叙事功能。

禁止项：单条超 15s；漏对白/系统声；抽象情绪标签代替具体量化；非说话人嘴部做口型同步；背景人物变成木头人（每个出现的人必须有微反应）；左右站位无理由突变；服装道具状态重置。
负面提示词模板：画面崩坏 面部扭曲 五官错位 多余肢体 手指畸形 角色换脸 人物闪烁 鬼影重叠 道具漂移 服饰闪烁错乱 穿模穿帮 物体悬浮 运动模糊过度 动作抽搐 光照闪烁 低清画质 像素化 水印 字幕残留 背景扭曲 非说话人嘴部动作 禁止未说话角色口型同步 OS系统声无需口型


每镜自包含：每个full_prompt开头必须包含完整的全局声明（16:9画幅+风格+情绪因果链规则+光照规则+系统规则），禁止依赖上一镜的上下文。任何一镜单独投喂Seedance应能独立运行。
每镜字数 800-1800 chars。

禁止模板套话：场景目的必须是此镜特有的戏剧目标，禁止“通过对白完成当前叙事情节节点的人物塑造与信息传递”等通用模板句式。固定镜头不需要“机位轮换”——这是跨镜规则不是单镜描述。关键量化表情 2-3 项/角色即可，不必堆砌数字。触发链和时间分段中不要重复描述同一量化数据——合并在时间分段里一次写清。保持叙事流畅，不堆砌数字。
表情必须是动词和数值序列（如“上眼睥微抬 1.5mm->瞳孔偏转 15°”），非名词标签“紧张”。
群像中每个角色可独立追踪其微反应随时间的变化。

输出格式：{"shots":[{"shot_id":"","subshot_id":"","full_prompt":""}]}

完成前自检：
1. shot 数量匹配 dispatch
2. 每 full_prompt >=800 字符
3. 每角色 >=5 个量化物理表情项（眼睑/瞳孔/唇线/鼻翼/呼吸各至少一，含数值或精确方位）
4. 每 full_prompt 中 >=2 句感官隱喻氛围文字
5. 每出场角色 >=1 项独立微反应，含因果链
6. 无抽象情绪标签，表情以动词/数值序列呈现
7. 有场景目的句 + 环境音层 + 非说话人口型控制
8. 负面提示词已注入
自检通过后写入输出文件。

额外修正要求（仅在上一轮自检发现系统性缺口时填写，不超过 200 字，不填则省略本段）：
{extra}
```


---

## 四、Phase 7-8: Editor Pass

### 穿帮审查 10 项（Phase 8）

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

### 模式 C 专属审查（Phase 8 追加，Composer 使用 narrative fusion 时必查）

11. 群像反应链断裂：在场角色无独立微反应，或因果链中断（A→B→C→D 缺环）
12. 场景目的缺失：Prompt 中没有说明此镜要建立/表现/引出的戏剧目标
13. 环境音层缺失：没有写基底环境音或关键音频事件
14. 非说话人口型控制缺失：无台词角色无口型闭合声明
15. 触发链-时间分段重复：同一量化数据在触发段和时间分段各写一遍
16. 木头人角色：出场角色被描述为「保持静止」「不做反应」「等待」
17. 表情名词标签：出现「紧张」「开心」「慌乱」等裸标签而非动词+数值序列
18. 物理状态缺失：未标注角色的站/坐/走/蹲/靠等基础身体状态

## 五、Phase 9: 最终验证

### Quality Gates（22 项）

| # | 检查项 | 门禁 |
|---|---|---|
| 1-8 | 格式完整 | 主镜头/时长/台词对象/场景标记/角色名/标点/blockquote/子镜覆盖 100% |
| 9 | 对白准确 | 0 mismatch |
| 10 | 机位完整 | <=10 欠项 |
| 11 | 动作三段 | 0 复用 |
| 12 | 景别中文 | 0 英文残留 |
| 13 | XLSX | 行数 >= 子镜数 |
| 14 | 编码 | UTF-8 |
| 15 | 提示词长度 | >=500 字符/镜 |
| 16 | 面部细节 | >=3 面部关键词/镜 >=70% |
| 17 | 焦距合理 | 0 超广角用于特写 |
| 18 | 轴线连续 | <=5 |
| 19 | 景别多样 | <=2 单调组 |
| 20 | 光照连续 | 相邻镜色温差 <=2000K |

### 模式 C 补充验证（Composer 使用 narrative fusion 时追加）

| # | 检查项 | 门禁 |
|---|---|---|
| C1 | 无抽象情绪标签 | 0 |
| C2 | 每出场角色 >=1 独立微反应 | 100% |
| C3 | 微反应含因果链 | >=80% |
| C4 | 表情以动词/数值序列呈现 | 0 名词标签 |
| C5 | 有场景目的句 | 100% |
| C6 | 有环境音层 | 100% |
| C7 | 非说话人口型闭合声明 | >=90% |
| C8 | 单镜字数 1200-1800 | 100% |

## 六、Phase 10: 导出

导出通过 export_with_validation.py（22+8 项自检→自动修→再检→全过才写盘）。不得直接调用 export_workbook.py。

## 七、Agent 编排策略（实战固化）

### 文件策略
- 多 Agent 并行必须各写**独立输出文件**（如 emotion_b12.json）
- 全部完成后用 merge_agent_outputs.py 合并去重
- 禁止多 Agent 写同一文件

### 线程管理

> [THREAD LEAK RED LINE - 2026-07-19 incident] Agent completion notification arrives in the SAME turn -> immediately call close_agent(target=agent_id). No deferral, no batching. This pipeline previously suffered a 15-minute outage from 6 leaked thread slots.
- Agent 完成通知到达的同一轮，立即 close_agent(target=agent_id)
- 单轮最多 spawn 3 个 Agent
- 完成→关闭→再派下一批

### 分批策略
| Phase | 单批上限 | 并行 Agent | 文件命名 |
|---|---|---|---|
| emotion/scene/camera | 20 镜 | 3 | {type}_b{NN}.json |
| prompt_composer | 36 镜(3批) | 3 | composer_v2_b{NNN}.json |



## 附：Editor 审查 Agent 派发模板（Phase 8）

> **[DISCIPLINE] Record agent_id on spawn, call close_agent immediately on completion.**

`
你是资深剪辑指导/后期总监，负责短剧成片前的最后一轮质量审查。
你的眼睛能捕捉到观众不会注意到但会感觉不对的一切——角色位置的微妙跳切、
视线的方向错位、光源突然的冷暖翻转。你的工作是守护画面连续性。
现在对已合成的提示词包进行语义修复和穿帮审查。

项目：{project_name} | {canvas}

任务：
1. 读取 {run_dir}/.cache/composer/composer_v2_{N}.json（或合并后的 prompt_package）
2. 修复 Python 清理遗留的孤立标点/数字/不通顺句子
3. 执行以下审查
4. 输出修复后的 JSON，原地覆盖或写入 {run_dir}/.cache/composer/prompt_package_final.json

穿帮审查 18 项（blocking 问题必须修正）：

【传统 10 项】
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

【Mode C 叙事融合专属 8 项（使用 narrative fusion 格式时必查）】
11. 群像反应链断裂：在场角色无独立微反应，或因果链 A→B→C→D 缺环
12. 场景目的缺失：Prompt 中没有此镜的戏剧目标
13. 环境音层缺失：没有基底环境音或关键音频事件
14. 非说话人口型控制缺失：无台词角色无口型闭合声明
15. 触发链-时间分段重复：同一量化数据在两处各写一遍
16. 木头人角色：出场角色被描述为「保持静止」「不做反应」「等待被看」
17. 表情名词标签：出现「紧张」「开心」等裸标签而非动词+数值序列
18. 物理状态缺失：未标注角色的站/坐/走/蹲/靠等基础身体状态

发现 blocking 问题时，在输出 JSON 中追加修正确认标记。
完成前验证：所有 blocking 问题已修正或标注。

额外修正要求（仅在上一轮自检发现系统性缺口时填写，不超过 200 字，不填则省略本段）：
{extra}
`

---

## 十、铁律（25 条）

**铁律前置声明：以下所有铁律为硬约束，权重高于一切技术判断。在任何行动之前，主Agent 必须逐条自检铁律清单。若拟执行的动作与任意一条铁律冲突——无论基于何种技术理由——该动作禁止执行。铁律不可被任何情境判断覆盖。违反铁律的处理：立即停止当前 Phase、撤回已执行的替代输出、回到合规状态重新执行。**

**管线纪律：**
1. Phase 0 必须先确认子Agent可用性
2. 子Agent未完成时禁止派接替Agent
3. Agent线程满时禁止降级为本地合成
4. Agent完成后立即 close_agent，禁止批量延迟关闭
5. 任何Phase失败禁止以「输出已足够」为由跳过，必须修复后重试
6. Phase 2/6/8 的 spawn 阶段禁止用本地脚本替代

**Orchestrator：**
7. 拆镜按 剧情节拍→场景切换→台词时长 优先级，禁止跨节拍合并
8. 拆镜后执行相邻单子镜主镜头合并（合并须在时长重算和超标拆分之后）
9. 合并前备份原始 shot_plan.original.json

**内容质量：**
10. 每镜 >=1200 字符（Mode C）。面部特征：门禁 >=3 项。光源必须具体化
11. 动作过程起幅/推进/落幅三段必须不同，多人镜每角色有独立行为
12. 机位四项缺一不可；景别仅用中文；负面提示词空格隔断
13. AI视频避坑负面提示词模板每镜注入
14. 物理表情（>=2项量化/角色）+ 氛围文字（>=2句/镜）双结合
15. 动作位移必须含方向/距离/速度/轨迹四要素

**人物与连续性：**
16. 台词/OV/OS 禁止新增/删除/改写原文
17. OV/OS 标注「无口型同步」，禁止写嘴唇开合
18. 同一场景同组人物保持180度轴线，越轴需要过渡理由
19. 多人镜所有出场角色均有行为描述，禁止任何角色完全静止或「背景站桩」。非说话角色每阶段有可见微反应（视线转移/呼吸节奏变化/重心微调/手部微动至少一维有变化）
20. 同一角色跨镜的 micro_expression 和 body_parts_focus 禁止复用

**穿帮审查（Phase 8）：**
21. 传统 10 项 + Mode C 专属 8 项 = 共 18 项检查
22. blocking 问题必须退回修正后方可进入 Phase 9

**导出铁律：**
23. 导出必须含主镜头分组（含时长）、每子镜时长标注、对白说话人标注
24. Phase 10 必须通过 export_with_validation.py，全部 30 项（22 传统 + 8 Mode C）才写盘
25. 导出后自检，任何一项 <100% 必须修复后重新导出

**运行时纪律（2026-07-19 固化）：**
26. Phase 2/6/8 子Agent 运行期间，主Agent 严禁以任何方式本地生成替代输出文件（Python 脚本、inline 代码、手动 JSON 拼装均禁止）。必须轮询等待全部 Agent 写完对应阶段目录后进入下一 Phase。超时等待用户确认，不得自行跳过。
27. 源文件 BOM 检测为 Phase 0 必做项。字节级剥离 EF BB BF 后再喂入 generate_shotplan.py，否则 scene_header_pattern 正则因 BOM 偏移失效。
28. Phase 0 必须先确认用户输出目录（export_base），所有项目文件落盘到该目录，禁止在用户未确认前创建默认路径。

以上 25 条铁律中标注「不可跳过」的阶段，主Agent在任何情况下不得静默省略。

## 十一、多 Agent 并行写入反模式

**问题**：多个 Agent 同时写同一个输出文件 → 后写覆盖先写 → 数据丢失（曾导致 103 项→40 项→10 项连锁覆盖）

**修复**：
- 每个 Agent 写独立文件（如 emotion_b12.json / emotion_b34.json / emotion_b56.json）
- 全部完成后用 scripts/merge_agent_outputs.py <merged.json> <file1.json> <file2.json> ... 合并去重
- 合并按 subshot_id 去重，先到者保留，重复丢弃

**派发模板注意事项**：
- 写入路径必须带独立后缀（如 _b12.json），禁止直接写 emotion_output.json
- 派发文本中明确：「写入（独立文件，不要碰其他文件）」

群像禁止项（移入负面提示词，正文不写）：禁止角色静止站桩、禁止表情冻结、禁止背景人物无反应、禁止等待被看，这四个关键词直接追加到每镜负面提示词末尾。正文只保留正面群像描述。
叙事优先风格规则：表情描述优先使用自然语言叙事（如「眼睫微颤→唇线收紧→呼吸从均匀加快至浅促」），仅在关键情绪锚点补充1-2项mm/度级量化。禁止将物理表情拆为独立的「量化表情」/「肢体细节」/「表演增强」格子式分节——统一融在时间分段的叙事流里。技术风格只做点缀不做骨架，整体读感应像导演笔记而非数据库字段。


时间分段硬性禁令：必须是完整叙事段落，禁用‘/’做段内分隔，禁‘画面分层：’等标签前缀。示例：‘⸮.前景叶片虚化如柔焦滤镜⸮.’
## 附：Prompt Composer 标准化派发模板（v3 固化版）

此模板为 Phase 6 Composer Agent 的唯一合法派发文本。主Agent 派发时只替换 {变量}，不得即兴修改正文。

```
你是资深 AI 视频提示词工程师与短剧导演，目标平台即梦。将导演数据转化为可独立投喂的 Mode C 叙事融合提示词。

项目：{project_name} | {canvas} | {visual_style}
角色：{character_list}

任务：
1. 读取以下 dispatch 文件：
{dispatch_file_list}
2. 逐子镜生成完整 AI 视频提示词
3. 输出 JSON 写入：{output_path}

每镜必须包含以下 8 个板块（缺一不可）：

板块1-全局声明：9:16竖屏开头，含画幅、风格、情绪因果链规则、光照规则、系统规则。人物与场景比例合理、人物与空间关系合理、镜头透视关系遵循物理规则。<=150字。

板块2-人物站位服装连续：所有角色画面位置+朝向+服装（从costume_map取禁止编造）+跨镜连续声明。

板块3-时长运镜场景目的：X.X秒.景别.运镜类型 + 运镜完整描述（从director_pass.json的camera字段取值，包含速度/距离/角度/焦段参数，禁止简化为仅运镜类型名如"推"/"拉"/"固定"） + 此镜的戏剧目标。禁止通用模板句式。

板块4-时间分段(叙事段落)：必须是完整叙事文本。禁止/作为段内分隔符。禁止[画面分层：]等标签前缀。禁止[人物构图][起幅]等格子式分节。画面表情动作语气台词融合在一个自然段。格式示例：[X.X-X.X秒，景别，运镜。前景叶片虚化。她眉心微蹙又舒展。同伴目光扫过。语气压低，OS口型闭合。原文台词：...]

板块5-光照：源类型+色温K+方向+硬度+明暗分割。管线级精度。

板块6-环境音：基底环境音+关键音频事件+叙事功能。

板块7-负面提示词：标准模板(画面崩坏 面部扭曲...完整40+关键词)。

板块8-自包含验证：确认本镜可独立投喂即梦。

每镜800-1800字。物理表情优先自然叙事语言，关键锚点补1-2项量化。

输出：{"shots":[{"shot_id":"","subshot_id":"","full_prompt":""}]}
一次性写入。写完终止。
```
