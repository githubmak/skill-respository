---
name: fight-scene-video
description: 原创或改编仙侠、西方玄幻、现代科幻、真实格斗等连续打斗分镜，或设计、精修单镜与单生成单元的玄幻画面；在已有剧情的人物、能力规则和结局内设计攻防，交付表演、摄影、VFX、声音及 Seedance 2.5 提示词。用于打斗分镜、单镜斗法、动作设计与战斗镜头。
---

# 打斗与斗法分镜

把明确剧情视为边界，在未定义的攻防过程内进行动作导演、摄影、VFX 与声音设计。目标是让战术、人物情绪、空间受力和视听规模一起推动战局。真人实拍仅作创意预演；实际拍摄由合格动作指导和现场安全团队执行。

## 先选输入模式

- **已有剧情的连续战斗**：用户要求设计一段完整战斗或连续攻防时使用；输入可为剧本、场景或多组连续动作，即使包含法天象地或精彩单镜也不改走单单元。保留已明确的攻击、规避、接触、顺序、伤势、控制权、能力与装备规则、人物性格及结局。若原文只有“激战、苦战、反击、获胜”等概述，可设计具体试探、攻防、调整和直接反应，使人物从既定起态抵达既定结果。读取[整场层次与题材](references/battle-arc-genre.md)。
- **原创连续战斗**：输入仅有题材、交战双方或目标。先以用户事实为先建立最低必要的目标、能力及代价、场地、初始关系和结局；空白可设计，不无因扩写身世、宗门或后续故事。建立后按连续战斗执行，并在 `剧本推断补全` 标明本次原创设定和依据。读取[整场层次与题材](references/battle-arc-genre.md)。
- **单镜或单生成单元玄幻设计**：用户明确只要一个镜头、一个关键片段，或输入已有 `### 生成单元 G…` 时使用；即使提供了完整战斗作为上下文，也只设计指定范围。没有单元标题时，按输入建立必要的 G 编号、承载镜号和自然时长；不凭此补写整场。读取[单生成单元导演与交付](references/single-unit-delivery.md)；其中的结构、时间线和默认 35 秒上限专属于此模式。

三种模式均不得把“更刺激”解释成改写已明确的事件、能力功能、重大伤势、台词或胜负。已写明的动作可补准备、连接、受力、反作用、收势和余波；新增动作只放在未定义过程内。用户指定的风格优先。

## 导演工作顺序

1. 锁定剧情事实、能力规则、结果，以及战场边界、地标、实体障碍、敌我初始关系、武器和道具归属、能力源点。此时不锁死机位、景别、精细走位或路径。
2. 分析每节拍的新威胁、目标、混合情绪、双方观察与反制、战术选择和控制权；为概述性空白补因果成立的攻防。若主能力是宏大奇观，在镜头设计前确定它怎样改变攻防、何时达到规模与亮度峰值、远近环境如何响应及后果怎样影响结局；再把动作、战术、人物、空间、视听和剧情线索推向既定结果。
3. 先定身体先兆、行动、接触或规避、反作用和余波，再联合设计观众需要看懂的事实与应感到的速度、重量或压迫。由此选起幅、观看距离、运镜、焦点、终幅；反向调整调度、动作路径、VFX 纵深、环境与声音。
4. 在内部预演中校正物理、接触状态、多人错峰反应、观看负载、特效主次和镜间连续。若不成立，先改调度、视角、遮挡、焦点、效果纵深或拆镜；不自动退回固定中景。选定方案后编译对应模式的 Markdown。

按需读取，而非把所有参考一并加载：

| 职责 | 何时读取 |
| --- | --- |
| [一次导演预演](references/one-pass-director-previsualization.md) | 连续战斗的情绪、战术、动作、摄影与多人反应；单单元需要复杂攻防时也读取。 |
| [景别与动作信息](references/shot-size-action-information.md)、[运镜语言](references/camera-movement-language.md) | 设计起终幅、动作读取窗口或语义化摄像机行为时。 |
| [高强度表演与摄影](references/high-intensity-performance-camera.md) | 关键节拍需要连续表演、强动势、多阶段运镜或避免保守摘要时。 |
| [视觉母版](references/visual-master.md) | 连续战斗需全局/场景视觉与 Seedance 2.5 提示词时；单单元只有用户同时要求全局方案时读取。 |
| [物理与连续性](references/shot-physical-director.md) | 摄影方案形成后，校正空间、接触、遮挡和镜间状态。 |
| [VFX 物理与观看层级](references/vfx-physics-compositing.md) | 高能术法、巨物、密集粒子或复杂光影需要镜内主次交接时。 |
| [创意质量检查](references/creative-quality-checklist.md) | 冻结前检查场景独特性、高潮、观看收益与重复句式。 |
| [提示词可执行性预检](references/prompt-executability-preflight.md) | 镜头答案确定后、落稿前，排查同镜互斥动作、竞争主读点和身份漂移；有已生成成片时改读反馈诊断。 |
| [连续战斗 Markdown 合同](references/copy-ready-markdown.md) | 连续模式成稿时；其中固定结构、八字段、语义化正文和 30 秒生成段上限是交付依据。 |

专项参考只在对应问题出现时读取：[特殊运镜](references/special-camera-rhetoric.md)、[慢镜与冲击奇观](references/impact-spectacle-slowmotion.md)、[多人动态合并](references/dynamic-merge-stability.md)、[剧情保真与时长](references/script-fidelity-timing-audit.md)、[节奏与物理审计](references/pacing-physical-audit.md)、[生成反馈诊断](references/generation-feedback-loop.md)。仅当方案仍显通用或用户要求对照案例时读取[高表现力参考](references/creative-quality-reference.md)。外部轨迹图、九宫格、XLSX 等其他流水线只有用户要求才启用，不得借此重选剧情、招式或结果。

源剧情或用户要求包含法天象地、法身或巨型法相时，读取[东方斗法原始素材中的法天象地专节](references/historical-technique-materials.md#法天象地巨型法相可选检查坐标)。该参考保留用户先前提供的内容，按已有规则选择可见证据，不把示例里的代价、反噬或出招次序当作默认剧情。

用户明确要求宏大、耀眼或以巨型能力为主视觉时，在冻结前检查[整场规模曲线](references/battle-arc-genre.md)、[主效峰值与读取交接](references/vfx-physics-compositing.md)及[宏大耀眼兑现项](references/creative-quality-checklist.md)：要让主能力至少短时支配画面，并以远近环境后果证明威力；通过观看窗口保持因果清楚，不靠压小主特效解决光污染。

## 交付与校验

默认在对话中交付 Markdown；用户明确要求保存时才写文件。按指定目录保存，否则用当前工作区 `outputs/`；不覆盖源剧本或已有成稿，同名用递增版本。只交最终采用稿，不附内部候选、工程参数或审计表。

连续模式按[连续战斗合同](references/copy-ready-markdown.md)输出全局风格、视觉母版、Seedance 2.5 提示词、场景方案和镜头列表，默认每生成段不超过 30 秒。单生成单元按[单元合同](references/single-unit-delivery.md)输出，默认每单元不超过 35 秒。它们是本技能默认的生成单位上限，不应宣称适用于所有平台；用户指定不同目标时长或已核实的平台规格时按其要求设置上限并校验。若目标平台能力未核实，较长段落只能作为创作时长方案，不能保证可直接投喂。`SKILL_DIR` 必须是本技能目录的绝对路径；交付前可对临时 Markdown 校验：

```bash
python3 "$SKILL_DIR/scripts/validate_storyboard.py" <成品.md> --mode refined  # 连续
python3 "$SKILL_DIR/scripts/validate_storyboard.py" <成品.md> --mode single   # 单生成单元
```

覆盖默认时长时，连续模式追加 `--max-segment-seconds <秒数>`，单元模式追加 `--max-unit-seconds <秒数>`；有明确焦段要求时单元模式追加 `--require-focal-length`。

校验器只验证机器可判定的结构与时长。仍须检查剧情事实、动作因果、情绪、空间、特效层级和连续性；若成稿暴露具体质量缺陷，可重设受影响的节拍，并重新检查相邻镜头和校验格式。不因笼统的“更华丽”无限重写全场。
