---
name: natural-emotion-performance
description: Naturalize character emotion, dialogue delivery, facial control, and body action for scripts, storyboards, shot tables, nine-panel grids, AI image prompts, and AI video prompts. Use when a scene includes speaking characters, emotional turns, conflict reactions, inner monologue, dialogue/OV/OS placement, or performance notes that must include emotion cause + facial expression control + body action + speaking tone.
---

# Natural Emotion Performance

## Core Rule

For every meaningful emotion or spoken line, build performance from four linked parts:

`发生原因 -> 表情控制 -> 肢体动作 -> 说话语气`

Do not write emotion as a naked label such as "愤怒、悲伤、震惊、冷漠". Convert it into visible and audible performance evidence.

## Four-Part Emotion Unit

Use this compact structure whenever adding or refining performance:

```text
情绪发生原因：角色刚看见/听见/意识到/被迫面对的具体触发。
表情控制：眼神、眉眼、嘴角、呼吸、下颌、泪意、笑意、停顿；写克制幅度。
肢体动作：手、肩、背、步伐、站位、距离、道具处理；写动作大小和节奏。
说话语气：音量、气息、语速、停顿、咬字、尾音、压抑/试探/命令/哽住等听感。
```

For AI video and image prompts, keep inner cause in Chinese planning fields if useful, but convert final visual prompt into visible details only. Do not put invisible psychology into `visual_description`.

## Naturalness Rules

- Tie every emotional shift to an immediate cause: a line, gaze, object, memory trigger, threat, accusation, silence, physical distance change, or status reversal.
- Make expression and body action match social pressure. High-status or calculating characters often suppress face before hands betray them; powerless characters may freeze, shrink back, clutch fabric, or look for exits.
- Use micro-expression before large action: eyelids pause, jaw tightens, fingers press into sleeve, breath catches, then the body moves.
- Let dialogue delivery carry subtext. A character can say polite words with clipped consonants, lowered volume, delayed response, or forced steadiness.
- Avoid making everyone cry, shout, tremble, or glare. Vary emotional leakage by personality, status, and relationship.
- Keep continuity: if a character is kneeling, wounded, holding a cup, or being restrained, their expression, breathing, and speech must respect that physical state.
- For ancient court/power scenes, prefer restrained cruelty, ritualized politeness, lowered eyes, sleeve/tea/step distance, and controlled pauses over modern outbursts unless the script requires loss of control.

## Dialogue Delivery

When a line is present, add a delivery note without rewriting the line:

- `压低声音，尾字收住` for threat, secrecy, or command under restraint.
- `先停半拍再开口，气息发紧` for shock, fear, or forced composure.
- `语速放慢，字字分开` for authority, warning, judgment, or cruelty.
- `声音轻但咬字清楚` for cold anger or deliberate humiliation.
- `尾音发虚，句中断气` for injury, grief, or panic.
- `笑意只到嘴角，眼神不笑` for concealed hostility or false warmth.

Use these as patterns, not fixed phrases. Match them to the line's cause and relationship.

## Shot And Panel Integration

When working inside a shot table or nine-panel grid:

- Add the four-part emotion unit to planning notes, performance notes, or execution notes.
- In visible fields, express emotion through face/body/prop/spacing: `她垂眼看杯沿，指腹压住杯壁，嘴角笑意停在一半`.
- In audio fields, express speech tone: `低声、慢速、尾音压住、句前停半拍`.
- In AI motion control, specify performance amplitude: `only eyelids and fingers move, shoulders held still, freeze after the line`.
- If the source provides only a broad emotion, infer a plausible immediate cause from the same beat and keep it local. Do not invent new backstory.

## Quality Check

Before final output, verify:

- Each major emotional turn has a concrete cause.
- Each speaking beat has a tone note tied to relationship and pressure.
- Expression and body action are visible, specific, and not repetitive.
- Performance does not contradict posture, injury, prop state, blocking, or social rank.
- Final AI prompts do not rely on abstract emotion words alone.


---

> **质量标准**：本技能输出需符合主 SKILL.md（ai-video-agent-mode）的铁律 14（物理表情 + 氛围感双结合）。每镜动作过程段必须同时包含 >=5 项物理表情/角色和 >=2 句氛围文字。
