---
name: jimeng-dialogue-performance-storyboard
description: 将剧本、小说片段、分场稿或对白戏转换为可直接投喂即梦 Seedance 的正式分镜 Markdown，并为两人及以上互动镜头组导出具名人物、身体面向、场景边界、实体遮挡和近肩摄影机视锥的俯视SVG/PNG空间参考图。适用于对白表演、情感关系、喜剧、悬疑、轻度惊惧、无台词因果、时间压缩蒙太奇和非战斗行动；原样保留台词与 OS/OV/系统音，控制单镜不超过15秒，先完成创意发散和导演审美选型，再以同一内部场景合同编译表演、空间、构图、运镜、光影、连续性、关键帧与生成风险，并执行增量校验、完整校验、设计复核和真实画面复核。不用于其他视频平台、纯剧本改写、内容合规审核、纯打斗/武器设计、九宫格生图或纯配音分析。
---

# 即梦剧情表演分镜

## 最高优先级：创意主权与工程边界

- 大模型独占所有会改变观众感受和成片表达的决策：源文理解、因果、拆镜、表演、情绪、调度、机位、运镜、焦点、光影叙事、色卡和最终提示词语言。
- 脚本只做无审美增益的确定性工程：标签归一化、结构/参数校验、轴线/遮挡/碰撞计算、字段对账、长度预算、排版、staging、哈希、审核状态和文件提升；只能返回错误事实与可行域。
- 脚本不得自动换演法、选机位、扩大 FOV、拆镜、改光影、降级固定镜头或重写提示词。工程失败必须返回导演层由大模型重选；任何维护若违反本边界，即使测试通过也不得合并。

## 输入

唯一硬必填是可完整读取的源文本或源文件。导出目录和视觉风格可选；其余默认 `画幅=16:9`、`seedance_target=auto`、`创作档位=balanced`、`visual_review=auto`、`blocking_reference=auto`。可选值与特殊适配见 [task-adaptation-contract.md](references/task-adaptation-contract.md)。

目标固定为即梦及 Seedance。除源文不可读，或歧义会改变人物身份、剧情事实和关键动作因果外，不阻塞式追问。纯打斗、九宫格、改写、合规和纯配音任务不进入本流程，也不调用其他本地技能替代。

macOS 使用 `python3 <skill_root>/scripts/<script.py> <args...>`；Windows 使用 `powershell -ExecutionPolicy Bypass -File <skill_root>/scripts/run_skill_tool.ps1 <script.py> <args...>`。平台差异不得跳过任何门禁。`route_task.py` 返回的 `skill_root` 是唯一脚本根路径，避免误调用工作区中的旧版校验器。

## 路由

先解析技能目录为 `<skill_root>`，运行 `<skill_root>/scripts/route_task.py <generate|audit|video-review> --compact --report <reports>/route.json`；生成任务附 `--source <源文路径>`。旧的非紧凑路由入口已禁用。只读取返回的 `read_first`，再读取命中的 `read_on_demand`，不要预载全部资料。常规生成必须先读：

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

1. 运行 `scripts/source_gate.py --source <源文路径> --compact --report <reports>/source-gate.json` 并通读完整源文；冻结人物、台词/OS/OV/系统音、事件因果、场景、道具归属、起止状态和跨场关键状态。拆镜前另建内部“源文事实清单”，锁定原文动作、道具、人数、终态和称谓；该清单不投喂，也不替代导演选型。
2. 按 [runtime-core.md](references/runtime-core.md) 先完成创意发散、导演选型和不可降级视觉核心，再在风险适配前设计场景摄影机运动弧：观众起始位置、各节拍视觉任务、静止/运动转换、强弱峰值和结束距离。不得让门禁提前把方案收敛为安全中景、通用微表情、默认固定或机械微推。
3. 按观众认知拆镜头组并完成导演选型后，建立非投喂 `scene_contract.json`，写入场景级 `tone_card`、`camera_strategy` 与逐镜 `camera` 的 `visual_task/shot_size/composition/mode/trigger/path/dramatic_gain/end_frame`。`tone_card` 必须冻结主/辅/点缀色、色温、主光、阴影色、对比度/饱和度、背景亮度、肤色保护、材质锚点、允许变化和禁止偏色；可另列 18% 中性灰、伽马、黑白位、D65/Rec.709 等全局校色基线。每条直接提示词前 220 字必须压缩复写主色、色温、主光、阴影色和肤色保护，不能只把色卡写在全局或场景表。所有非静止镜头另须写 `camera.motion_ownership.camera_path/focus_path/actor_path/prop_path/terminal_state`：五个字段分别具名摄影机、焦点、人物/手部、道具及落幅主体；无转焦、无人物动作或无道具路径也必须在对应字段明确写出，不得省略后让模型推断。水面、湿鳞、玻璃、金属、泪珠等反射主体成为焦点时，逐镜追加 `lighting.source_entities/transport_path/material_response/luminance_order/dark_region`；摄影机路径、焦点转换、人物动作和道具状态不能共用一条“从A到B”路径，容器内道具被用作构图或转焦起点时，`prop_path` 必须冻结其容器、运动状态与终态。先运行 `scripts/scene_contract.py <contract> --strict-completeness --compact --report <reports>/contract.preflight.json`，通过后再用 `route_task.py generate --source <源文> --contract <contract> --compact --report <reports>/route.contract.json` 二阶段路由。逐镜生成前运行 `contract_compile.py --shot-id <shot_id>`；其输出只是非投喂工程对账表，只能原样排列大模型已经选定的事实并检查预算，不得生成或重写创意。合同字段优先使用最终提示词中的可见事实原句；重复 JSON 键必须报错，不得静默覆盖。严格门禁拒绝高风险场景的 `performance:null`、风格词伪装成 `core_fact`、缺失 `blocking_id`/保护事实/摄影机收益或 `tone_card`。两镜以上场景不得全场静止；静止只可作为局部情绪手段，至少一镜必须有由人物、道具、声音或信息变化触发且有剧情收益的运镜。合同只冻结已选事实、表演载荷、摄影机设计、空间ID、影调和不可降级视觉核心，不能替导演选择演法或镜头类型。
机位坐标属于导演选择，必须由大模型显式写入空间规格；`auto_position` 禁用。脚本只能校验导演已选坐标并返回净距、轴侧、遮挡、视场等错误事实与可行域。
4. 命中空间参考时，在正式提示词前运行 `render_blocking_reference.py`；它只把同源 SVG/PNG 写入计划稿父目录下的 `staging/blocking/`。双人关系默认相向；有意看向道具或别处时显式写 `facing_mode: independent`。脚本只验证参数范围、人物/边界净距、轴线、遮挡、路径、视场和标签碰撞，不自动移动人物或摄影机。模型提交修订前先运行 `blocking_repair_preflight.py`，非法候选不计修复次数。真实画面审核后用 `promote_blocking_reference.py record/promote` 提升，未获几何与视觉双 PASS 的图不得进入正式目录。
5. 按 [runtime-core.md](references/runtime-core.md) 由大模型完成表演 IR、情绪因果链（触发 -> 目标/策略 -> 身体泄露 -> 听者策略变化 -> 句末残留）、受保护可见载荷、直接提示词与制作控制。`prompt_preflight.py` 和 `creative_preflight.py` 只报告，不改写创意。出现“摄影机跟随手指从叶片落到人物脸”等多运动主体歧义时，必须返回导演层，由大模型分别重写摄影机、焦点、人物和道具。每完成一个子镜头运行 `incremental_validate.py`；第一镜还必须立即运行带 `--storyboard` 的严格合同恢复，通过后才能继续本场，禁止整场生成后集中补丁。
6. 严格使用当前模板导出；`both` 从同一事实合同生成 2.0、2.5 两份主文件和不可投喂索引。
7. 保存后运行 `scripts/validate_storyboard.py --compact --report <reports>/storyboard.json --shadow-report --seedance-target <目标> <output.md>`、`scripts/scene_contract.py <contract> --storyboard <output.md> --strict-completeness --compact --report <reports>/contract.json`、`scripts/prompt_preflight.py <output.md> --compact --report <reports>/prompt.final.json` 和 `scripts/creative_preflight.py <output.md> --compact --report <reports>/creative.final.json`；后两个脚本默认严格阻断会污染终态判断或把镜头退化成通用拍法的结果。逐镜通过不能替代完整文件、跨场和双版本校验。完整 JSON 只读文件中的错误摘要和相关镜头，不把整份报告重新放入上下文。
8. 工程校验通过后必须读取并执行 [review-pipeline.md](references/review-pipeline.md)。设计复核不可关闭；关键帧/视频先做真实画面复核，再创建并验证 manifest。正式层全部 Markdown、SVG、PNG 和视频都必须登记；`reports/` 与 `staging/` 不计交付库存。设计或视觉为 `REVISE/NOT_RUN` 时不得标记 `FINAL`。修订按 `field -> shot -> pair -> window -> scene` 最小升级；脚本只验证修改范围，不产生创意修复。

## 执行效率与上下文预算

- 源文闸门按源文 SHA-256 缓存；源文未变时不得重复通读、重复路由或重复生成风险报告。
- 每次只恢复一个场景或镜头组的上下文。压缩后仅恢复：当前版本、已通过门禁、剩余问题、下一步动作。
- 增量校验使用 `--current-shot --compact --report`，只处理当前镜头、相邻连续性、五镜签名窗口和三镜镜头组窗口；场景/文件边界仍必须运行完整校验。
- 路由、合同、预检和完整校验的详细 JSON 写入报告目录；终端只显示状态、范围、计数和有限错误摘要。
- 所有主流程 CLI 均强制 `--compact --report`；缺少任一参数直接失败，不得使用旧的完整 stdout 入口。
- 线稿和 PNG 先看缩略图/contact sheet；只有发现疑似朝向、遮挡、比例或排版问题时才读取原尺寸图。不得批量加载整集原尺寸 PNG。
- 视觉复核前运行 `scripts/image_review_prep.py <delivery_dir> --output-dir <reports>/thumbnails --max-size 320 --compact --report <reports>/image-review-prep.json`；缩略图未发现疑点时不得读取原尺寸 PNG，发现疑点时只读取对应镜头。
- 修改按镜头 ID 定位；禁止全局替换、整文件重写和重复控制句。两次同级修复仍失败时升级到拆镜、重选机位或合同层。
- 每次候选修订提交前运行 `scripts/repair_scope.py <previous.md> <candidate.md> --target-shot <shot_id> --scope <field|shot|pair|window> --compact --report <reports>/<shot_id>.repair.json`；出现全局或组级变化时必须显式升级为 `scene` 并记录原因，不能把整文件改动伪装成局部修复。
- 每轮记录耗时、输入/输出 token（或估算值）、修改镜头数和错误类别；超过预算先暂停并恢复最小上下文，不牺牲创意、审美、表演或真实视觉复核。

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
