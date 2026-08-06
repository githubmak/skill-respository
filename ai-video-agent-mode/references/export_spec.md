# Export Spec — 导出格式规范

Export 阶段导出前加载。

## Excel Workbook（export_with_validation.py）

文件名与用户确认的 Markdown 文件同名，仅扩展名改为 `.xlsx`。

### 提示词包分栏结构

| Sheet | 内容 | 列 |
|-------|------|----|
| AI视频模型提示词 | 模型直接投喂与生成控制 | 主镜头, 子镜头, 时长, 画面描述｜直接复制, 负面提示词, 生成模式, 原生音频 |
| QA与表演预算 | 内部质量合同与动作预算 | 戏剧目标, 角色场景目标/策略, 关系情绪弧, 序列导演计划, 剪辑切点, 提示词信息预算, 声音导演计划, 道具功能面合同, 肤色保护合同, 镜头功能, 叙事权重, 信息增量, 反应归属, 节拍ID, 时长策略, 容量利用率, 角色优先级, 动作预算, 起终态, 表演因果, 表演张力合同, 戏眼合同, 连续性合同, 抽卡控制, 台词引用, 注意力交接, 打斗连续性 |
| 台词与OS表演 | 原文与配音/表演执行 | 引用, 类型, 人物, 逐字原文, 时间窗, 可见性, 台词功能, 潜台词, 原文重音词, 潜台词可见证据, 轮次关系, 会话模式, 响应延迟, 抢话/打断窗口, 会话源文依据, 神态, 身体状态, 语气与停顿, 口型同步, 原生音频；Validate另核对自然时长容量与可见口型窗互斥 |
| 导演连续性 | 运镜和跨镜承接 | 景别, 机位, 运镜, 视点, 画面层级, 入场策略, 揭示策略, 焦点策略, 镜头模式, 表演链, 镜头执行节拍, 序列承接, 轴线, 灯光, 落幅 |
| 关键帧流水线 | 起始/戏眼/结束三状态关键帧 | 主镜头, 子镜头, 优先级, 触发原因, 帧类型, 时间, 关键帧生图提示词, 即梦视频提示｜配合关键帧, 人物/道具状态差异, 连续性检查, T2V事实一致性, 负面提示词 |

## Markdown Export（export_with_validation.py）

Markdown 只导出直接投喂和人工操作所需内容，禁止出现 QA 元数据、`qa_metadata`、生成控制、`generation_control`：

`画面描述｜直接复制` 由 `direct_prompt_compiler.py` 从模型创作的规范五段提示词结构化组装。它只做精确去重并保护空间、连续性、表演、光影和台词事实；无法无损压缩时超过700字返回 `CREATIVE_REWRITE_REQUIRED`，停止导出并回到模型阶段，不允许工程层选择性删句或截断后继续交付。
成功导出后将每镜段落顺序、字数、精确去重数、整句省略项和受保护台词写入 `.cache/export/direct_prompt_compile_report.json`；该报告只用于 QA 追溯，不进入 Markdown/XLSX 的即梦正文。

```
# {project_name} 即梦投喂分镜

## 使用说明
## 全局锁定
## 制作质量总控
## 通用负面提示词｜直接复制
## 场景状态表
## 分镜投喂卡

#### {shot_id}｜镜头组总时长：{duration}s

【出现人物】
{visible_people}

【镜号】
1，{duration}s，{普通|复杂}。

【画面参数】
画幅：{aspect_ratio}；风格：{style}；影调：{tone_palette}；色卡：{visual_scene_prefix}

【画面描述｜直接复制】
{direct_copy_prompt}

【运镜描述】
{camera_description}

【光影描述】
{lighting_description}

【负面提示词｜直接复制】
{negative_prompt}

【表演与声音】
{dialogue_or_sound_table}

【状态继承】
{state_carryover}

【剪辑衔接】
{transition_prompt}

【本镜制作控制】
画面质感：{visual_quality_execution}
光效与曝光：{lighting_and_exposure_execution}
动态美学：{dynamic_aesthetic_execution}
表演与情绪：{performance_and_emotion_execution}
穿帮控制：{continuity_and_physical_execution}
抽卡策略：{reroll_execution}
蒙太奇与剪辑：{montage_and_cut_execution}

【本镜必要约束｜直接复制】
{high_risk_constraint_block}

【本镜补充负面提示词｜直接复制】
{high_risk_negative_block}
```

`## 制作质量总控` 与 `【本镜制作控制】` 是用户可见的人工执行信息，不是 raw `qa_metadata`，也不直接粘贴进即梦正文。前者汇总全片画面、光效、动态、表演、剪辑和风险基线；后者必须把本镜合同转译为上述七行，不能只写“已检查/按合同执行”。

导出同时生成逐镜 `production_control_grounding` 报告：七个维度分别记录是否适用、候选可见事实和已落地事实。适用的可见维度未进入 `【画面描述｜直接复制】` 时必须阻断；风险等级、人工检查、失败重试、后期与拆镜决定不参与画面 grounding，也不得被复制进模型正文。

复杂/高风险镜使用与 Jimeng 相同的最终字段 `【关键帧生图提示】` 和 `【即梦视频提示｜配合关键帧】`。前者依次包含起始状态关键帧、戏眼关键帧、结束状态关键帧；后者按时间段连接三帧。随后输出人物/道具状态差异表、关键帧连续性检查和关键帧/T2V事实一致性检查。它们是前期稳定参考，不是九宫格、P01-P09、多格漫画、I2V 声明或已上传的首尾帧槽位。

成功导出通常还会在确认目录生成同名 `.concise.md` 与 `.engineering.md`。当
`seedance_target=both` 时，主交付改为两份独立可投喂 Markdown（`*_Seedance2.0.md`、
`*_Seedance2.5.md`）和一份 `00_双版本索引.md`；索引只用于比较，不投喂。两版来自同一镜头、台词、
人物、空间、道具与时长合同，差异仅限模型适配的光影精度与动态复杂度措辞。XLSX 仍从同一 canonical
package 写出，便于逐镜核对。

下一镜转场提示词由导出脚本根据当前镜 `continuity_contract.next_carryover/end_anchor` 与下一镜 `continuity_contract.start_anchor` 自动生成，只用于连续生成和剪辑操作，不写入 `full_prompt`，不得新增剧情、服装、对白或人物动作。最后一镜写 `无，段落结束。`

镜头执行节拍来自锁定 shot plan 的 `camera_beat_map`：展示时间窗、表演触发、视觉主体与落幅、镜头响应和承接状态，用于人工复核或平台分段执行；不是 QA 元数据，不投喂为额外模型段落。没有动态节拍时明确写“连续镜头，无额外切换”。

`画面描述｜直接复制` 是唯一推荐复制到即梦正文框的正向提示词。它从规范 `full_prompt` 派生，开头优先使用压缩 `视觉场景前缀`，并控制在 700 中文字符以内。该块不得保留“上一镜、继承、尾帧、剪辑、切到、反打到、当前主角”等元叙述，也不得出现 `line_function/subtext/turn_relation/conversation_mode/response_latency/overlap_or_interrupt_window/conversation_source_basis/inner_emotion/display_intent/emotion_delta/scene_objective/active_tactic/knowledge_gap/power_state_change/sequence_directing_plan/cut_decision_contract/prompt_information_budget` 等内部分析标签、枚举值或强度数字。对白、情绪、角色行动、关系、镜头段落与剪辑判断必须先转译为原文重音说法、可见停顿/抢话/收句、手眼/呼吸/道具/距离证据、听者反应、构图、运镜响应、环境节拍和落幅；同时清晰包含画幅、影调、色卡/视觉场景前缀、画面主体、运镜状态、光影描述，以及脸、手、道具、反光、浅阴影、背景虚化或剧情相关材质中的可见锚点。风景只按环境镜两项、人物镜一项消费风景身份/构图/自然运动/揭示/光候事实；启用 `video_texture_contract` 时再追加一条压缩视频质感约束，不得把图片级长材质描述逐镜复制。

`prop_functional_surface_contract` 只保留在 XLSX/QA。直投正文不得出现合同字段名，只写功能面朝使用者、摄影机可见的背面/侧边、握持或接触、操作证据和稳定方向；`readable` 内容用肩后/过肩/俯拍/斜上方同侧机位展示。

`skin_tone_protection_contract` 只保留在 XLSX/QA。直投正文不得出现合同字段名，只写自然肤色、脸部独立主光/补光、环境色落点以及墙痕、灰尘、雾粒、体积光束所在的空间层；源文授权的伤痕、妆容、泪痕、污迹和剪影仍按可见事实输出。

多人、画外声或同场人物多于本镜入画人物时，`【出现人物】` 与 `【画面描述｜直接复制】` 必须共同表达可见人数闸门：清晰入画、肩线/背影/倒影/虚化入画与纯画外声音分开写；不入画人物不得作为视觉朝向目标。

`本镜必要约束｜直接复制` 与 `本镜补充负面提示词｜直接复制` 只在高风险镜导出：高抽卡、`shot_group`、道具/身体状态变化、长台词或需要人工首轮验证时出现。普通镜不强制输出，避免把低风险镜头拖成臃肿提示词。

## 文件命名约定

- Markdown: 使用配置确认阶段一次确认并锁定在 `project_config.json` 的 `delivery.markdown_path`。
- Seedance 目标：配置确认阶段填写 `seedance_target`，可选 `auto`、`2.0`、`2.5`、`both`；
  `both` 的触发点就是这一次确认，不在导出阶段二次询问。
- Excel: 与 Markdown 同目录、同文件名，扩展名为 `.xlsx`。
- 简洁视图：同名 `.concise.md`；工程审查视图：同名 `.engineering.md`。
- `both` 主 Markdown：配置路径的 stem 加 `_Seedance2.0.md` 和 `_Seedance2.5.md`；索引固定为
  `00_双版本索引.md`。
- 以上文件只能写入用户本次明确确认并记录在 `project_config.json` 的 `export_base`。缺失时 blocking，不允许回退到 run_dir、当前目录或源文件目录。
