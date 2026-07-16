---
name: nine-panel-video-storyboard
description: Professional AI video storyboard skill for converting either (1) a rough scene, plot outline, narrative beat, 九宫格剧情包, or 九宫格据情包 into a strict nine-panel story grid, or (2) a single camera instruction such as a 4-second push-in shot into 9 time-sequenced AI control keyframes with absolute consistency. Use when the user asks for 剧情九宫格, 九宫格分镜, 9镜连续分镜, AI视频分镜九宫格, 九宫格剧情包, 九宫格据情包, 单镜头9宫格关键帧, AI控图级关键帧, single scene to nine panels, or video-generation-ready storyboard JSON with camera setup, AI motion control, English prompts, audio SFX, timestamps, absolute screen coordinates, and narrative tags. Preserve source plot, dialogue, OV, narration, and OS; only reasonably split or visualize beats.
---

# Nine Panel Video Storyboard

## Core Output

Convert input into exactly 9 panel objects. Output valid JSON only unless user explicitly asks for explanation.

## Source Fidelity Rules

- Preserve source script, outline, dialogue, OV, narration, OS. Do not rewrite/delete unless user asks.
- Split into 9 visual panels without changing plot facts, causality, character intent, or ending direction.
- Reasonable completion allowed: visible blocking, gestures, prop state changes, eyelines, reactions, transitions, spatial continuity implied by source.
- Don't invent new events, characters, backstory, clues, or flashbacks not in/implied by source.
- Long OV/dialogue → distribute across adjacent panels preserving wording and meaning.

Choose one mode:
- `nine-panel-ai-video-storyboard`: rough scenes, plot outlines, narrative beats needing 9 continuous shots.
- `single-shot-keyframe-grid`: single camera instruction/keyframe control — one continuous shot like "4.0秒前推镜头".

Default to `nine-panel-ai-video-storyboard` whenever input contains story events, dialogue, multiple characters, conflicts, prop reveals, or scenes from other storyboard skills. Don't switch to `single-shot-keyframe-grid` just because input includes camera phrases like "slow push-in".

Use this top-level shape:
```json
{
 "storyboard_type": "nine-panel-ai-video-storyboard or single-shot-keyframe-grid",
 "source_summary": "one concise sentence",
 "total_duration": "duration in seconds when provided; otherwise null",
 "panels": []
}
```

Each panel must use this exact structure:
```json
{
 "panel_id": "01",
 "timestamp": "00.00s or null",
 "camera_setup": "景别 + 机位角度/焦段 + 构图法",
 "camera_motion": "single AI-safe camera movement",
 "visual_description": "前景 + 中景【主体】 + 背景【环境】, visual only",
 "ai_motion_control": "who can move, who stays still, motion amplitude, freeze timing",
 "ai_prompt_en": "[Shot/Camera], [Subject + Clothing], [Environment/Lighting], [Details/Quality tags], negative prompt: modern objects, deformed limbs, flicker, warped face, extra fingers, clothing distortion, scene flicker, repeated composition, 3D realistic skin, photorealistic texture",
 "seedance_full_video_prompt": "Seedance全能参考提示词：整合画面/景别机位/主体服装/环境光影/动作控制/情绪表演/镜头运动/声音台词/时长定格/负面约束",
 "audio_sfx": "transition sound + ambience + matched action sound",
 "narrative_tag": "dramatic function in the nine-panel structure"
}
```

---

## 九宫格叙事结构（核心约束）

- 3 行分工：第1行(01-03)=铺垫，第2行(04-06)=冲突高潮，第3行(07-09)=结局收束
- 3 列分工：左列(01/04/07)=人物内心，中列(02/05/08)=客观事件，右列(03/06/09)=环境伏笔
- Panel 05 = 全九宫格唯一核心帧，`narrative_tag` 必须标注 `核心定格`
- 9 格共用同一 `character_anchor_id`/`costume_version`/主色调/光源方向/透视高度

> 📖 完整3×3叙事矩阵、Panel 05锚定规则、视觉权重表、景别分配比例、9:16节奏预分配、项目存档导出 → `references/nine-panel-narrative-architecture.md`

---

## Mode A: Narrative Nine-Panel Workflow

1. Identify visible story beats only: place, characters, props, conflict, action, OV/dialogue/OS placement, final image. For every major reaction/spoken line, identify immediate cause → controlled facial detail + body/prop action + voice tone.

2. Compress/expand into 9 shots without changing/deleting required script content.

3. Apply 1-3-3-2 shot-size rhythm: Panel 01=establishing, 02-04=medium development, 05-07=close conflict/detail, 08-09=resolution/freeze.

4. Prevent repetition: never same shot size + camera angle in two consecutive non-blank panels.

5. Enforce "one shot, one motion": each panel gets one camera movement only.

6. Write `visual_description` as pure visual evidence — no thoughts, emotions as abstractions, backstory, themes.

7. Write `ai_motion_control` as production constraints: moving subjects, locked elements, motion range, freeze timing.

8. Write `audio_sfx` including tone when dialogue/OV/OS exists: pause, breath, volume, speed, tremor, command pressure.

9. Write `ai_prompt_en` in English with: `[Shot/Camera], [Subject + Clothing], [Environment/Lighting], [Details/Quality tags], negative prompt: ...`.

10. Write `seedance_full_video_prompt` in Chinese as complete Seedance-ready prompt integrating: 画面描述 + 镜头语言 + 动作控制 + 情绪表演 + 声音台词 + 生成约束.

### Narrative Continuity Rules

Every panel must advance at least one visible variable: subject state, prop state, relationship distance, eyeline, or information state. Do not output 9 zoom levels of the same moment. If three panels in a row keep same character posture/prop state/background/action, revise the middle panel.

Minimum nine-panel story arc:
1. Space and power relationship
2. Main subject/action introduced
3. Inciting line, gesture, or disturbance
4. Opposing character or consequence appears
5. Key prop/detail changes state
6. Reaction close-up or emotional concealment
7. Conflict escalates or action interrupts
8. Decision/reversal
9. Hook/freeze-frame or exit image

### Repetition Guardrails
- Vary framing: wide→medium→medium close→insert→reverse→close
- Vary camera relation: front→3/4 side→over-the-shoulder→high angle→low angle→foreground obstruction→detail insert→empty shot
- Keep identity/costume anchors stable, change visible action and screen composition
- Include panel-specific action words early in prompts
- Add negative: `duplicate composition, same pose every panel, repeated zoom-in sequence`

---

## Mode B: Single-Shot Keyframe Grid

One continuous camera instruction, not a multi-shot scene. 9 panels = time-sequenced keyframes.

### Keyframe Timing
1. Extract total duration. `4.0秒` → `total_duration: "4.0s"`
2. Calculate interval = Total Duration / 8
3. Assign timestamps: Panel 01=0×interval through Panel 09=8×interval
4. No duration → null + progression markers: 0%, 12.5%, 25%, ..., 100%

### Panel 01 Baseline Frame
Exhaustively define all visible constants: character (facial features, makeup, hairstyle, expression, jewelry, posture, body orientation, hands, scars/marks), costume (garment layers, material, embroidery, texture, color, weathering), environment (architecture, props, ground, background, light source, shadow, haze, color temperature), absolute screen coordinates (画幅正中心, 左侧1/3, 右侧1/3, 底部1/3, 顶部1/4, 前景左下角).

### Panels 02-09 Incremental Frames
Force-copy Panel 01 constants. Preserve exact same wording for all constant details. Only these may change: camera progress percentage, tiny subject motion (eyelids lowering 2mm, sleeve swaying, fingers tightening), timestamp.

```
常量复制自Panel 01：<exact Panel 01 character, costume, environment, coordinate wording>
本帧增量：timestamp, camera progress, <only tiny motion state changes>
```

### Single-Shot Consistency Rules
- No changing character identity, age, face shape, makeup, hairstyle, costume, props, light source, weather, architecture, or screen coordinates after Panel 01
- No introducing new objects after Panel 01 unless original instruction describes them entering
- Absolute frame coordinates in every panel
- One camera motion across all 9 panels; only progress percentage changes
- Micro-actions only. Large action → lock camera or convert to small staged increments
- Panel 09 = final locked keyframe with hold/freeze instruction

---

## Camera Rules

AI-safe camera motion only: `Static`, `Slow Push-in`, `Slow Pull-back`, `Slow Lateral Track`, `Gentle Tilt Up`, `Gentle Tilt Down`, `Slow Follow Track`, `Locked-off with subject motion`.

Avoid: combining zoom+rack focus+orbit+handheld+whip pan+large subject action in one panel; shallow rack focus on wide establishing shots; large lateral movement in tight close-ups; rapid camera for delicate facial/hand shots; multiple subjects doing large independent actions at once.

---

## Narrative Tags

Short functional tags: `建立空间`, `引入主体`, `埋设道具`, `产生冲突`, `冲突升级`, `关键动作`, `核心定格`, `反应余波`, `结尾钩子`, `留白`

---

## Blank Panel Rule

If source doesn't support full 9-panel story, keep grid intact. For blank panels:
```json
{"panel_id": "08", "timestamp": null, "camera_setup": "留白", "camera_motion": "Static", "visual_description": "留白：原始内容不足，保留九宫格排版位置。", "ai_motion_control": "No generation required.", "ai_prompt_en": "[Blank Panel], no image generation required, reserved empty grid cell.", "seedance_full_video_prompt": "留白：无需生成视频，保留九宫格排版位置。", "audio_sfx": "静音", "narrative_tag": "留白"}
```

---

## Quality Check

Before responding, verify:
- Exactly 9 panels, `panel_id` from "01" to "09"
- Every panel contains all required keys
- `timestamp` in every panel; exact time for single-shot, null for narrative without duration
- No consecutive non-blank panels repeat both shot size and angle
- Every `camera_motion` is single motion instruction
- Every `visual_description` is visible-only, foreground/midground/background logic
- Every `ai_motion_control` includes moving actor/object, locked elements, amplitude, freeze/hold timing
- Every `ai_prompt_en` includes default 10-item negative prompt
- Every `seedance_full_video_prompt` is complete Seedance-ready (not camera-only note)
- Major speaking/reaction panels have natural performance: emotion cause, expression control, body action, speaking tone
- **Single-shot mode**: Panel 01 exhaustive baseline, Panels 02-09 preserve exact wording, only timestamp/camera progress/micro-action change; absolute screen coordinates in every panel
- **Narrative mode**: Panels not merely progressive zooms; ≥7 of 9 panels have distinct visible action/prop state/eyeline/subject arrangement/camera relation; no 3 consecutive non-blank panels share same primary subject posture, same front-facing angle, and same background arrangement

---

## 剪辑思维连贯控制 & 剧情包封装

**核心摘要**：
- 相邻面板构图匹配（水平线偏差≤5%、主体位移≤15%）、动作匹配（方向偏差≤15°）、光影匹配（色温偏差≤200K）
- 跨剧情包衔接：Panel 09末帧=下一包Panel 01参考图源（12帧缓冲规则）
- 转场仅三类：硬切（默认）、淡入淡出溶解（0.3-0.6s）、遮挡转场（≥60%遮挡）
- 被 `$storyboard-to-nine-panel-pipeline` 调用时需输出 bundle 扩展字段

> 📖 完整剪辑连贯性规则、3D数字人帧锚定、转场分级、节奏剪辑公式、bundle扩展字段、连续性故障验证 → `references/nine-panel-continuity-packaging.md`
