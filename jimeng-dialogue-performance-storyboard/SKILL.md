---
name: jimeng-dialogue-performance-storyboard
description: 将剧本、小说片段、分场稿、对白戏或多类型剧情转换为可直接投喂即梦（Seedance 视频模型）的正式分镜 Markdown。适用于对白表演、情感关系、喜剧错位、悬疑揭示、轻度惊惧、无台词视觉叙事、时间压缩蒙太奇和非战斗行动，以及内联文本或本地文件、单场或多场、短片段或长篇分批任务；原样保留台词，控制单镜不超过15秒，设计表演与口型/OS/OV，维持人物/空间/道具连续性，生成关键帧和负面提示词，并拦截负向概念泄漏、错误场景先验、肤色污染、透视比例和屏幕朝向等生成 bug。导出目录、视觉风格和画幅可由用户指定，也可安全补足。不用于其他视频平台适配、只做剧本改写、内容合规审核、纯打斗或武器动作设计、九宫格生图、纯配音分析的任务。
---

# 即梦剧情表演分镜

## 输入

唯一硬必填是可完整读取的源文本或源文件。导出目录、视觉风格和画幅均可选；缺失时按 [task-adaptation-contract.md](references/task-adaptation-contract.md) 补足。目标固定为即梦平台及其 Seedance 视频模型，不生成其他平台版本。

除源文缺失/不可读，或歧义会改变人物身份、剧情事实和关键动作因果外，不阻塞式追问。纯打斗/武器动作、九宫格、剧本改写、合规审核和纯配音任务不进入本流程，也不调用其他本地技能替代。

## 引用路由

常规生成只读四个文件：

1. [task-adaptation-contract.md](references/task-adaptation-contract.md)：输入、默认值、长文本和交付。
2. [runtime-brief.md](references/runtime-brief.md)：唯一执行顺序和取舍。
3. [generation-risk-guards.md](references/generation-risk-guards.md)：隐性提示词、手机、肤色、体积光、透视和画外人物闸门。
4. [output-template.md](references/output-template.md)：唯一输出结构和字段顺序。

只在触发时追加一个或少量专项引用：

- 非默认剧情类型：喜剧、悬疑、亲密关系、画外威胁、无台词因果、时间压缩蒙太奇或非战斗行动，读 [narrative-mode-routing.md](references/narrative-mode-routing.md)。
- 对白/表演：情绪弱、节拍平、关键反应或口型交接复杂，读 [prompt-performance-rules.md](references/prompt-performance-rules.md)；主要人物表演风格漂移时再读 [performance-baseline-library.md](references/performance-baseline-library.md)。
- 视觉质感：画面塑料、平、廉价，或用户要求构图、焦段、材质、胶片感，读 [visual-attraction-rules.md](references/visual-attraction-rules.md)；需要类型化色卡案例再读 [color-palette-library.md](references/color-palette-library.md)；明确需要环绕、多莉变焦、闯入式镜头、时间错位或日漫式切空再读 [cinematic-grammar-library.md](references/cinematic-grammar-library.md)。
- 场景预设：常见现代场景缺少可用锚点时读 [scene-preset-library.md](references/scene-preset-library.md)；陌生题材直接从源文建空间，不加载预设。
- 空间机位：多人轴线、柜台/桌/车/门口、跨文件同地复现或正反打风险，读 [spatial-camera-continuity.md](references/spatial-camera-continuity.md)。
- 物理结构：躺/坐/抱/扶/摔/起身、道具/衣物转移、门车门、手机/UI、人群或窄空间移动，读 [physical-structure-continuity.md](references/physical-structure-continuity.md)。
- 拍法参考：需要现成调度模式或同类镜头反复失败时，读 [shot-patterns.md](references/shot-patterns.md)，不得原样套用。
- 维护与复核：修改技能时读 [regression-cases.md](references/regression-cases.md)；校验通过后仍有复杂物理/空间歧义时读 [validation-checklist.md](references/validation-checklist.md)。

同一规则只按最窄触发加载。不要因为“想提高质量”同时读取全部视觉、空间和表演库。

## 执行

1. 通读完整源文，冻结场景文件清单、人物/声音/表演基线、空间索引、影调索引和跨场景关键状态线。
2. 按观众认知拆镜头组；每组只完成一个新认知，并分配铺垫、升压、峰值、释放或缓冲。
3. 为每个子镜头确定唯一任务、复杂度和空间/状态/镜头/表演四系统底图；高风险任务过载时先拆镜。
4. 应用生成风险闸门，再按当前事实写可独立投喂的正向提示词。
5. 严格使用当前输出模板；多场景默认分文件，共用冻结的全局索引。
6. 保存后运行 `scripts/validate_storyboard.py --shadow-report <output.md>`，修复全部硬错误后交付。

## 硬约束

- 原样保留所有台词、OS、OV、系统音、内心独白及其标点；可见台词进入直接提示词并驱动正确口型，OS/OV/系统音进入直接提示词但画内人物闭口并有可见反应。
- 每个子镜头 `<=15s`；`【画面描述｜直接复制】` `<=500` 中文字符，普通剧情/对白当前仍以180字为硬门槛。影子字数建议只用于校准，不降低输出质量。
- 每个子镜头包含四个基础字段；可选字段只在真实降低风险时添加，不输出空字段。关键帧字段必须成对出现。
- 直接提示词必须写视觉场景前缀、可见人数/主体、空间和身体面向、道具/支撑状态、景别机位、固定或单一路径、表演/声音、光影材质、可见变化或明确保持、稳定结束状态。
- 下一镜开头重写上一镜结束后的当前可见事实；不依赖即梦跨镜记忆，不在直接提示词写 `上一镜、继承、延续、尾帧、切到、反打到、后期插入`。
- 清晰入画人物必须有主表演、受击/观察反应或低幅活体状态；无反应容量者降为肩线、弱虚化或画外。
- 道具、衣物、朝向、人体支撑、门车门、手机/UI和空间穿越发生变化时，写清起点、接触/支撑、可见转换和稳定终态；一镜不承担三项以上高风险任务。
- 光影必须落到光源方向、受光面、浅阴影、背景控制或剧情材质；环境色不得覆盖脸和活动手，体积光不得遮挡五官。
- 任何负向具体视觉概念先改写成目标身份、服装、地点和道具事实；操作型手机固定屏幕朝使用者、镜头只见背面或斜侧边缘。
- 不用机械校验句补字段；缺失项必须改写成真实画面事实。

只使用当前模板和当前字段。修订现有分镜时，对受影响场景整体重写并重新验证，不维护字段别名、转换层或历史分支。
