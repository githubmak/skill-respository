# 输出合同

本文件服从 `creative_engineering_boundary.md`。字段结构用于交接和排版，不规定导演如何创作，代码不得
用关键词、正则、固定摄影模板或字段评分判断内容是否有创意、是否好看或是否能被 Seedance 理解。

## 模型创作输出

Master Production 每个主镜输出一条 `shots[]`。模型负责决定并创作：

- `full_prompt`：模型的完整导演表达，不限定内部段落模板。
- `seedance_prompt`：面向已确认目标版本的最终 Seedance 语义编译，最多700字。
- `seedance_prompt_variants`：仅 `seedance_target=both` 必填，含模型分别创作的 `2.0` 与 `2.5`。
- `director_card`：模型创作的简洁导演卡，最多500字。
- `negative_prompt`：模型基于本镜生成风险创作，不由脚本关键词注入。
- `qa_metadata`：模型按本镜需要组织的导演分析与制作合同。剧情理解、情绪因果、表演、站位、机位、
  运镜、焦点、光影、影调、色卡、动作、声音、节奏、连续性解决和最终审美都属于模型。

推荐模型在需要时使用既有创作字段，例如 `dramatic_design`、`performance_contract`、
`continuity_contract`、`scene_tone_palette`、`visual_bible`、`static_aesthetic_contract`、
`dynamic_aesthetic_contract`、`camera_beat_map`。这些是创作思考工具，不是工程评分表；模型可根据镜头
复杂度选择深度，确定性 validator 不因某个创作子字段缺席而判定画面质量失败。

Scene Lock 也是模型创作资产。工程保存其文件版本和引用；Master 与 Editor 决定本镜如何继承、变化和
表达，不要求镜头色卡与 Scene Lock 逐字一致。

## 工程锁定字段

工程只锁定能够从配置或源文逐字证明的内容：

- `shot_id`、`subshot_id`、`source_subshot_ids`
- `duration`，必须为正数且单镜不超过15秒，并与确认的分镜计划相符
- `generation_control.mode=t2v` 与布尔值 `audio_enabled`
- `qa_metadata.dialogue_refs`
- `qa_metadata.dialogue_events[].ref/kind/speaker/text`
- 项目画幅、目标平台、`seedance_target`、文件路径、文件名和版本映射

`dialogue_events` 的表演字段仍由模型创作；只有 `ref/kind/speaker/text` 与源文逐字核对。台词、OS、OV、
系统音不得改字；OS/OV/系统音不做口型。工程不根据文本关键词推断说话方式、情绪或镜头表现。

## 确定性门禁

`validate_deterministic_package.py` 只允许阻断以下可机械证明的问题：

- JSON 无法读取、顶层结构错误、合同版本错误
- ID 缺失或重复、镜头或源子镜覆盖缺失/重复/乱序
- 时长非法、超过15秒或与确认计划不一致
- 必要交付字段缺失或类型错误
- 台词引用、类型、说话者或文本与源文账本不一致
- T2V 生成控制结构错误或出现参考资产槽位
- 已确认 Seedance 目标没有相应模型提示词
- Seedance 提示词超过700字、导演卡超过500字
- Editor 尚未明确通过或仍存在 blocking
- provenance、哈希、staging、目录、文件名、版本或导出排版不一致

缺少或超长的创作字段返回 `CREATIVE_REWRITE_REQUIRED`。工程不得补写、组装、压缩、精确去重、截断、
换词或删除创作文本。

以下结论永远不能由确定性脚本给出：情绪是否成立、表演是否自然、构图是否高级、运镜是否有动机、镜头
是否平淡、节奏是否抓人、光影是否漂亮、色卡是否有效、连续性该如何解决、Seedance 是否能理解、最终
画面是否达到审美目标。这些由 Editor 模型结合源文和完整上下文复审。

## Editor 复审

Editor 必须独立阅读源文事实、Scene Lock、相邻镜头和 Master 完整创作，不依赖工程启发式报告。至少判断：

- 剧本理解、人物目标、关系变化、潜台词和情绪因果是否准确
- 表演、动作、台词节奏、站位和空间关系能否让观众读懂
- 拆镜、时长分配、镜头组节奏、机位、景别、焦段、运镜和焦点是否服务戏剧
- 光源、光影、影调、色卡、材质、声音与转场是否形成目标观感
- 跨镜人物、道具、轴线、视线、动作起终态和情绪余波如何连续
- 对目标 Seedance 版本的语义编译是否清楚、可执行，并保留导演意图
- 最终画面预期是否达到本项目的审美标准

Editor 若不通过，返回具体 `blocking` 和最早负责的模型创作字段；不得要求工程脚本改写语义。

## 导出

Export 只做：读取确认配置、选择 `seedance_prompt` 或对应版本变体、验证非空与字符数、逐字核对台词、
写 Markdown/XLSX、生成文件名和哈希。选中的提示词与导演卡必须逐字符保持模型原文。

`seedance_target=auto|2.0|2.5` 输出一份投喂文件；`both` 输出两份投喂文件和一个版本索引。版本索引只说明
文件对应关系，不描述或生成摄影、光影、动作和风格差异。

## 运行可靠性

每个 worker 只写 packet 指定输出路径并记录 provenance。packet 绝对超时不可被心跳延长；初次加两次
重派仍失败则熔断。全流程自状态初始化起90分钟硬截止，超过或预测无法按时完成时写结构化报告并停止。
这些机制只管理执行，不降低模型创作上下文、分析深度或 Editor 审美标准。
