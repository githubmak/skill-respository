---
name: jimeng-dialogue-performance-storyboard
description: 将剧本、小说片段、分场稿或对白戏转换为可直接投喂即梦 Seedance 的正式分镜 Markdown，并为两人及以上互动镜头组导出具名人物、身体面向、场景边界、实体遮挡和近肩摄影机视锥的俯视SVG/PNG空间参考图。适用于对白表演、情感关系、喜剧、悬疑、轻度惊惧、无台词因果、时间压缩蒙太奇和非战斗行动；原样保留台词与 OS/OV/系统音，控制单镜不超过15秒，先完成创意发散和导演审美选型，再以同一内部场景合同编译表演、空间、构图、运镜、光影、连续性、关键帧与生成风险，并执行增量校验、完整校验、设计复核和真实画面复核。不用于其他视频平台、纯剧本改写、内容合规审核、纯打斗/武器设计、九宫格生图或纯配音分析。
---

# 即梦剧情表演分镜

## 输入

唯一硬必填是可完整读取的源文本或源文件。导出目录和视觉风格可选；其余默认 `画幅=16:9`、`seedance_target=auto`、`创作档位=balanced`、`visual_review=auto`、`blocking_reference=auto`。可选值与特殊适配见 [task-adaptation-contract.md](references/task-adaptation-contract.md)。

目标固定为即梦及 Seedance。除源文不可读，或歧义会改变人物身份、剧情事实和关键动作因果外，不阻塞式追问。纯打斗、九宫格、改写、合规和纯配音任务不进入本流程，也不调用其他本地技能替代。

macOS 使用 `python3 <skill_root>/scripts/<script.py> <args...>`；Windows 使用 `powershell -ExecutionPolicy Bypass -File <skill_root>/scripts/run_skill_tool.ps1 <script.py> <args...>`。平台差异不得跳过任何门禁。`route_task.py` 返回的 `skill_root` 是唯一脚本根路径，避免误调用工作区中的旧版校验器。

## 路由

先解析技能目录为 `<skill_root>`，运行 `<skill_root>/scripts/route_task.py <generate|audit|video-review>`；生成任务附 `--source <源文路径>`。只读取返回的 `read_first`，再读取命中的 `read_on_demand`，不要预载全部资料。常规生成必须先读：

1. [runtime-core.md](references/runtime-core.md)：唯一常驻生成合同，保护创意、审美、表演、运镜、空间、状态和不可降级质量。
2. [output-template.md](references/output-template.md)：唯一输出结构和字段顺序。

按风险追加最少引用：

- 剧情模式与信息释放：[narrative-mode-routing.md](references/narrative-mode-routing.md)。
- 对白、情绪、口型和听者反应先读 [prompt-performance-runtime.md](references/prompt-performance-runtime.md)；同类失败重复或专项诊断时再读 [prompt-performance-rules.md](references/prompt-performance-rules.md)，人物基线漂移时读 [performance-baseline-library.md](references/performance-baseline-library.md)。
- 视觉质感和导演表达：[visual-attraction-rules.md](references/visual-attraction-rules.md)；题材 profile、自然动态、色卡或高级运镜分别按需读 [visual-direction-profiles.md](references/visual-direction-profiles.md)、[liveness-motion-grammar.md](references/liveness-motion-grammar.md)、[color-palette-library.md](references/color-palette-library.md)、[cinematic-grammar-library.md](references/cinematic-grammar-library.md)。
- 场景锚点不足：[scene-preset-library.md](references/scene-preset-library.md)。
- 多人、轴线、双侧边界和正反打先读 [spatial-camera-runtime.md](references/spatial-camera-runtime.md) 与 [blocking-facing-reference.md](references/blocking-facing-reference.md)；复杂桌边、纵深、人群或连续失败时再读 [spatial-camera-continuity.md](references/spatial-camera-continuity.md)。
- 姿态、接触、道具/衣物转移、门车门、UI、人群或窄空间：[physical-structure-continuity.md](references/physical-structure-continuity.md) 和路由命中的 [generation-risk-guards.md](references/generation-risk-guards.md)。
- 需要拍法候选或同类镜头持续失败：[shot-patterns.md](references/shot-patterns.md)，只借结构，不复制案例事实。
- 长文本分批、双版本、多场景拆分或特殊交付：[task-adaptation-contract.md](references/task-adaptation-contract.md)。

## 强制流程

1. 运行源文闸门并通读完整源文；冻结人物、台词/OS/OV/系统音、事件因果、场景、道具归属、起止状态和跨场关键状态。拆镜前另建内部“源文事实清单”，锁定原文动作、道具、人数、终态和称谓；该清单不投喂，也不替代导演选型。
2. 按 [runtime-core.md](references/runtime-core.md) 先完成创意发散、导演选型和不可降级视觉核心，再做生成可行性适配；不得让门禁提前把方案收敛为安全中景、通用微表情或机械微推。
3. 按观众认知拆镜头组并完成导演选型后，建立非投喂 `scene_contract.json`，运行 `scripts/scene_contract.py <contract>`，再用 `route_task.py generate --source <源文> --contract <contract>` 二阶段路由。合同字段优先使用最终提示词中的可见事实原句；重复 JSON 键必须报错，不得静默覆盖。合同只冻结已选事实、表演载荷、空间ID和不可降级视觉核心，不能替导演选择演法或镜头类型。
4. 命中空间参考时，在正式提示词前运行 `scripts/render_blocking_reference.py <spec.json> --storyboard <计划中的Markdown路径> --png --replace`。双人 `relationship` 状态默认要求双方相向；若剧情有意让人物看向道具、门外或其他目标，必须显式写 `facing_mode: independent`。脚本自动把同源图片放到Markdown父目录，并以镜头组号精确命名为 `<镜头号>.svg` 与 `<镜头号>.png`；人物、边界、面向、实体遮挡、关系轴、近肩距离、门洞通视和完整视场全部通过后，才能从同一合同编译提示词。
5. 按 [runtime-core.md](references/runtime-core.md) 完成表演 IR、受保护可见载荷和语义门禁，再生成直接提示词与制作控制；编译前运行 `scripts/prompt_preflight.py <draft.md> --advisory` 和 `scripts/creative_preflight.py <draft.md> --advisory`。前者报告易误判措辞，后者检查创意最小载荷（第一焦点、关系/因果、光影职责、摄影机服务和结束余像）；两者都只报告，不改写创意文本。完稿后回译对照 IR。每完成一个子镜头，运行 `scripts/incremental_validate.py <scene_draft.md> --current-shot <Sx-xx-x>`，只修返回的最小范围。
6. 严格使用当前模板导出；`both` 从同一事实合同生成 2.0、2.5 两份主文件和不可投喂索引。
7. 保存后运行 `scripts/validate_storyboard.py --shadow-report --seedance-target <目标> <output.md>`、`scripts/scene_contract.py <contract> --storyboard <output.md>`、`scripts/prompt_preflight.py <output.md>` 和 `scripts/creative_preflight.py <output.md>`；后两个脚本默认严格阻断会污染终态判断或把镜头退化成通用拍法的结果。逐镜通过不能替代完整文件、跨场和双版本校验。
8. 工程校验通过后必须读取并执行 [review-pipeline.md](references/review-pipeline.md)。设计复核不可关闭；有关键帧/视频时按档位追加真实画面复核，最后创建并验证 review manifest。任何修订按 `field -> shot -> pair -> window -> scene` 最小升级并重跑受影响门禁；只有事实合同或空间锁广泛级联错误时才重写场景。

## 不可绕过

- 原样保留人物、事件顺序、因果、台词及标点；每镜 `<=15s`。普通直接提示词 `<=500` 字，复杂镜 `<=650` 字，仅成对关键帧保护的极少数复合镜 `<=700` 字；固定字速只作 shadow 建议。
- 创意胜者的关系几何、第一焦点、策略转折、情绪载体、运镜收益和结束画面是不可降级核心。生成适配只能拆动作、降运动或加关键帧，不能用更平庸的镜头替换。
- 人物位置、身体面向、摄影机可见面、视线、关系轴、边界两侧和真实背景必须闭合；`正面可见` 不等于 `面向镜头`。无可见转换时不得换位、越轴、跨侧或改变正背关系。
- 直接提示词必须独立成立，以当前可见事实开头，只完成一个获准转换，并把最后20%的稳定终态写入正文。`【状态继承】` 只能压缩复写该终态，不得新增事实。
- 关键帧、直接提示词和制作控制必须来自同一事实合同；制作控制不得新增另一套主体、构图、光源、运镜、表演、道具或终态。
- 不以机械校验句、空泛美感词、堆叠运镜或更长提示词修复问题。工程通过不能代替设计审美与真实画面判断，技术指标通过也不能覆盖语义失败。
- 连续两次同级局部修复仍只是在补字段、压缩文字或重复控制句时，必须升级为重新选型、拆镜或重做光影机制；禁止继续堆补丁把创意核心磨平。

## 维护

维护与专项诊断可读 [runtime-brief.md](references/runtime-brief.md)、[validation-checklist.md](references/validation-checklist.md) 和 [regression-cases.md](references/regression-cases.md)，不在常规生成中重复加载。修改后运行 `python3 scripts/run_regression_suite.py` 和系统 `quick_validate.py`；不得只挑单项测试通过。
