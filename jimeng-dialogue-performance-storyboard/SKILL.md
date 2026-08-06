---
name: jimeng-dialogue-performance-storyboard
description: 将剧本、小说片段或对白戏转换为可直接投喂即梦 Seedance 的正式分镜 Markdown，并在多人互动时生成和审核站位面向工程图。用于对白表演、情感关系、喜剧、悬疑、轻度惊惧、无台词因果、蒙太奇及非战斗行动；保留台词、OS、OV 与系统音原文，设计表演、情绪、调度、摄影机、焦点、光影、影调和色卡，单镜不超过 15 秒，并完成设计审片、真实画面审片和交付校验。不用于其他视频平台、纯剧本改写、内容合规审核、纯打斗、九宫格生图或纯配音分析。
---

# 即梦剧情表演分镜

## 最高优先级

把最终成片质量作为唯一创作目标。大模型负责所有会改变观众体验的决定：理解原文、拆镜与时长分配、节奏、表演、情绪、调度、机位、景别、运镜、焦点、光影、影调、色卡、Seedance 表达和创意修订。工程脚本只核验可客观证明的事实：文件可读性与哈希、原文声音逐字和顺序、编号、时长算术、字段、长度、路径、几何计算、staging、审核状态、提升状态与 manifest。

任何脚本、模板或旧规则若用关键词、评分、配额或词面回收判断创意，要求固定运镜数量、签名镜数量、情绪链格式、色词位置，或自动选择创意修复，均不得进入主流程。工程失败只返回事实；由大模型重新判断如何修正。

## 路由与读取

1. 解析本技能目录为 `<skill_root>`，运行 `python3 <skill_root>/scripts/route_task.py generate --source <源文> --seedance-target auto|2.0|2.5|both --compact --report <reports>/route.json`。
2. 完整读取路由返回的 `read_first`；只在对应问题实际存在时读取 `read_on_demand`。`creative_reference_suggestions` 只提示可能有帮助的创意资料，不是待读清单；`creative_reference_catalog` 是完整创意知识索引。先形成场景理解，再由模型按当前创作难点选择最少的相关资料，禁止自动预载全部建议。
3. 常规生成只常驻读取 [runtime-core.md](references/runtime-core.md) 与 [output-template.md](references/output-template.md)。用户明确提出风格、质感或逐镜视觉要求时，读取目录中的视觉导演与色卡资料；对白、表演、场景材质或复杂调度按当前创作难点选择对应资料。摄影机语法、叙事模式、Seedance 清晰表达案例和真实生成诊断都属于创意目录，不由脚本按关键词替模型选择。Seedance 措辞、复杂焦点/摄影机/道具路径或参考素材职责先读 [seedance-target-adaptation.md](references/seedance-target-adaptation.md)，仍有多主体、时序或终态歧义时再按需读取 [seedance-example-patterns.md](references/seedance-example-patterns.md) 的对应案例；已有真实关键帧或视频失败时再读 [seedance-generation-diagnostics.md](references/seedance-generation-diagnostics.md)。

## 主流程

1. 运行 `source_gate.py` 并完整通读源文。建立一次内部源文事实表，冻结人物、事件顺序、因果、台词/OS/OV/系统音、道具归属和跨场状态；源文哈希未变时复用。
2. 按 `runtime-core.md` 完成导演设计。先理解人物关系与场景节拍，再决定拆镜、表演、调度、摄影机弧、光影和色卡；风险适配只能发生在创意方案之后。内部创作笔记不要求固定字段、固定候选数或输出。
3. 多人互动且空间关系会影响画面时，由大模型选择站位、面向、机位和视场，再运行 `render_blocking_reference.py`。工具只报告碰撞、净距、遮挡、轴侧和视场事实。SVG/PNG 只写入 `staging/blocking/`；未完成几何与真实画面双审核时不得提升、不得作为 Seedance 参考。
4. 使用 `output-template.md` 直接撰写最终 Markdown。每镜只保留一份创意事实源：`【Seedance 直投提示】`。摄影机、焦点、人物/手部和道具各用具名主语分句；每镜独立写出 `色卡`、`影调`、`光影`，使单镜脱离全局段落仍可直接投喂；只写实际发生的路径，不填写无动作占位符。
5. 保存后运行 `validate_delivery.py --source <源文> --storyboard <输出.md> --seedance-target <目标> --compact --report <reports>/delivery.draft.json`。它只做确定性交付校验，不判断创意优劣。失败时只修复客观交付错误，不因门禁改写导演方案。
6. 读取并执行 [review-pipeline.md](references/review-pipeline.md)。由大模型完成源文对照设计审片；存在关键帧、线稿或视频时必须查看真实画面。设计或视觉不通过时，由大模型定位第一层根因并重选、拆镜或重写；需要比较生成变量时只改变一个最可能主因，禁止关键词补丁或无限抽卡循环。
7. 审核通过后创建并验证 manifest；需要的空间图用 `promote_blocking_reference.py` 提升。最后以 `validate_delivery.py ... --final --review-manifest <manifest.json>` 复验。只有审核结论、文件哈希和正式资产状态都有效时标记 `FINAL`。

## 创作与工程边界

- 模型必须主动完成表演、情绪因果、空间关系、摄影机意图、光源逻辑、影调和色卡。场景级视觉方案负责连续性，每镜仍须由模型独立创作可直接投喂的色卡、影调与光影；不规定颜色答案、百分比或固定光型。静止、长镜头、普通切镜、强运镜、留白和简洁表演都可成为正确创作，不设数量配额。
- 时长工具只能给出原文声音字符数、实测音频时长或容量提示；拆在哪里、是否留停顿、是否拆动作与台词由模型决定。
- Seedance 适配只消除指代与路径歧义，不替导演选择机位、焦点或终态。避免“摄影机跟随手指从叶片落到人物脸”这类共享路径句，分别写摄影机、焦点、手指和叶片的实际状态。
- 不生成前置 `scene_contract.json`，不从成稿反向恢复创意合同，不逐镜运行创意正则，不输出七行制作控制，不用重复字段证明同一事实。
- 技能目录不保留旧创意正则、合同恢复、逐镜修复器或其兼容入口。若外部旧文档提到这些工具，视为已废弃，不能恢复到主流程。

## 交付硬事实

原样保留人物身份、事件顺序、因果和全部台词/OS/OV/系统音；每镜 `>0s` 且 `<=15s`。普通直投提示建议不超过 500 字，复杂镜建议不超过 650 字，绝对上限 700 字。两版本必须共享镜号、时长和声音原文。正式目录不得引用 `staging/` 资产，未审核线稿不得进入正式目录或 Seedance 参考位。

修改技能后运行 `python3 scripts/run_regression_suite.py` 与系统 `quick_validate.py`，并用未见过的完整剧本前向测试；成功标准是成片设计质量、语义清晰、声音可执行、审核有效和无循环修补，不是创意正则通过率。
