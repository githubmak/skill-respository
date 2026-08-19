---
name: jimeng-dialogue-performance-storyboard
description: 将剧本、小说片段或对白戏导演化为即梦 Seedance AI 漫剧/短剧分镜，可按任务范围输出完整双文件、单镜头提示词、镜头修复、机位/表演审核或场景资产提示词。适用于需要强化剧情节奏、人物表演、对白演绎、可实现摄影、光影声音和跨镜连续性的分镜任务。
---

# 即梦 AI 漫剧/短剧导演分镜

把用户提供的剧情导演化为可拍、可生成、情绪有因果、画面有节奏的分镜。模型自行运用已有的编剧、导演、摄影、表演、灯光、声音和剪辑知识；本技能只规定会改变结果的边界、最低质量合同、按需路由和交付格式。

普通任务完整读取本文件和 [references/production-contract.md](references/production-contract.md)，不要预加载其他参考。

## 输入与边界

正式交付需要剧本或目标片段、画幅、视觉风格和全剧母色卡。只有人物身份/关系、因果顺序、地点切换、台词归属、能力规则、伤势胜负、结果结局或片段边界不清时集中提问；其他视觉未知按剧情建立最小可拍空间。

- 不改人物、身份、性格、关系、知情、事件顺序、因果、能力、伤势、关键动作、胜负、结果和结局。
- 锁定台词、OS、OV 的归属、事实载荷、核心意图和关键顺序；OS、OV 默认逐字保留。
- 可删除同义重复或用原文已建立且说话者已知的证据强化台词；不得新增秘密、罪名、承诺、关系、结论或事件。
- 资产图锁定人物身份、服装、道具、材质、固有色和场景拓扑；环境影调不得给资产改色。
- 不输出俯视调度图。每个场景输出一组不含人物的场景资产图正向提示词与负向约束。
- 不考虑本地化、投放数据或数据回流，只完成分镜脚本和直投提示词层面的导演设计。

## 默认工作流

1. 锁定原文事实、人物知情、台词载荷、起始状态和不可改变的结果。
2. 根据剧情自行设计观众问题、刺激、升级、策略变化、兑现、余波和尾钩；没有剧情依据时不强造反转、金句、特效或炫技。
3. 建立场景空间、实体光源、人物与摄影机可达区域、关系轴和场景资产图提示词。
4. 从同一份内部镜头蓝图联合设计表演、摄影、光影、声音、时长、动作和连续性；不要先写标签式草稿再补形容词。
5. 按任务范围交付：完整项目默认连续编译导演审核版和 Seedance 独立直投版；单镜头生成、镜头修复、机位/表演审核或场景资产提示词任务只输出对应结果，不强制生成无关文件。完整双文件的镜号、顺序、时长、台词、关键动作、结果和起落状态一致。
6. 仅对完整双文件运行交付验证器；只局部修复报错镜头或章节，不重新导演整集。

## 必须成立

- 每镜有明确剧情职责、起幅、变化、结果和可持续落幅；没有新信息、关系、动作结果或情绪变化的镜头合并。
- 情绪不能压成“紧张地说”“错愕地看”等标签。关键转变必须呈现刺激、人物认知、第一冲动、控制或泄漏、新行动、反馈和镜尾残留；节拍数量由剧情和时长决定，不套固定模板。
- 对白必须与表演握手：说前准备、说中关键词或语义转折、说后余波；受话者不能提前知道尚未说出的内容，口型只属于说话者。
- 动作按真实物理顺序写清预备、路径、接触、受力、结果和保持；不存在的阶段删除，不为填格式虚构动作。
- 摄影机必须处于空间中可到达的位置，交代机位侧别、高度、朝向、景别、焦段、轴线、运动路径、停止点和终幅可见范围。炫技必须服务剧情读取，不能破坏空间或人物可见性。
- 时间线从 `0.0秒` 连续覆盖到镜尾。每段写具名主体、触发或进入基线、可见/可听过程和停止/保持状态。
- 前镜落幅与后镜起幅在人物位置、朝向、视线、重心、动作接点、道具控制者、光源方向和声音接点上连续；直投每镜仍须自足，不能写“同上”或“沿用上一镜”。
- 光影优先来自场景中可解释的实体光源、自然光或合理反射；有明确叙事目的且不破坏空间逻辑时，可加入克制的电影化轮廓光、填充光或曝光塑形，并保持方向、强度和跨镜连续。面部可读、肤色自然，材质保持真实响应。
- 声音按剧情需要选择人物台词、动作拟音、环境、空间方向、声音桥和音乐；台词优先，声音不抢关键读取。不存在的 OS、OV 或特效零提及；音乐在用户授权或项目风格允许且有叙事职责时可以设计。
- 每个时间窗保持一个主首读点，并允许服务主读点的次级信息。若台词、复杂动作、多人反应、运镜或特效互相争夺注意力，再改为串行时间窗、内部有因切点或相邻镜头。

## 创作自治

- 除母色卡输入门、不可改事实、人物知情与台词归属、资产边界、空间可达、物理因果、口型归属、跨镜连续、时长覆盖和直投语义纯净度外，其余镜头数量、景别变化、节拍结构、动作数量、情绪载体、运镜、光影、音乐、插切、蒙太奇、特效层数与表现强度由模型按剧情收益自行决定。
- 参考文件中的数量、百分比、时长区间、候选方案和常见结构默认是启发式参考，不是配额、上限或必经流程；只有明确标注为事实/安全/物理/平台/交付硬约束的条目才强制执行。
- 允许安静、静止、留白、反高潮、重复母题、长镜头、快速剪辑、复杂调度或非常规构图，只要它们有清楚的剧情职责、可读结果和可实现路径。不要为了命中术语、字段或结构而添加原本不需要的反转、动作、微表情、旁观反应、光效、音乐或镜头。
- 当多种方案都成立时，模型可直接选择最符合人物、空间、节奏和情绪收益的一种，不必输出或内部穷举固定数量的候选；用户指定的创作方向优先于经验模板，但不得突破上述硬约束。

## 按需参考

只在满足条件时完整读取相应文件并避免无效重复；长任务、上下文压缩或出现事实/规则矛盾时可重新读取相关文件：

- 有场景图、人物图、道具图、多视图、PDF 或资产文件夹：[references/visual-input-governance.md](references/visual-input-governance.md)。
- 用户提供参考拍摄手法：[references/shooting-method-reference.md](references/shooting-method-reference.md)。
- 复杂心理反转、多人对白传播，或已出现表演压平问题：[references/ai-manga-dramatic-direction-engine.md](references/ai-manga-dramatic-direction-engine.md)。
- 台词、动作、反应存在明显时长竞争或高负载长镜：[references/ai-manga-duration-budget.md](references/ai-manga-duration-budget.md)。
- 需要精确光影曲线、滤镜后期、复杂材质或特效受光：[references/cinematic-lighting-color-bible.md](references/cinematic-lighting-color-bible.md)。
- 原始剧情缺少短剧留存结构，或题材奇观需要专项推导：[references/genre-story-spectacle-engine.md](references/genre-story-spectacle-engine.md)。
- 重动作、打斗、VFX、蒙太奇或特殊剪辑：[references/spectacle-action-vfx-montage.md](references/spectacle-action-vfx-montage.md)。
- 关键道具换手、开合、显隐、破损或控制权变化：[references/entity-prop-continuity.md](references/entity-prop-continuity.md)。
- 原文明确标注转场：[references/transition-shot-grammar.md](references/transition-shot-grammar.md)。
- 已决定使用全景、远景或空镜但其职责不清：[references/wide-empty-shot-grammar.md](references/wide-empty-shot-grammar.md)。
- 空间遮挡存在歧义或直投出现特定构图故障：[references/on-demand-storyboard-reference.md](references/on-demand-storyboard-reference.md)。

[references/seedance-dual-delivery-contract.md](references/seedance-dual-delivery-contract.md) 是完整交付规范的深度维护参考，[references/non-regression-baseline.md](references/non-regression-baseline.md) 仅用于修改技能和回归检查；普通生成不读取这两个文件。

## 交付

完整项目严格按 [references/production-contract.md](references/production-contract.md) 输出；局部任务只返回用户请求的交付物：

1. `作品名_导演审核版.md`
2. `作品名_Seedance独立直投版.md`

交付前运行：

```bash
python scripts/validate_seedance_delivery.py <作品名_Seedance独立直投版.md> --source <源剧本> --director <作品名_导演审核版.md>
```

验证失败只修复命中的格式、事实、表演最低结构、可见性、时间窗、道具或连续性错误。验证器不替代导演判断，也不对创意强度、镜头审美或情绪感染力打分。
