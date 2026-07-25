---
name: jimeng-dialogue-performance-storyboard
description: Convert a supplied script or novel scene into a Jimeng/Seedance-ready formal storyboard Markdown in one pass. Use when the user provides a script/scene and only specifies export directory, visual style, and aspect ratio. Directly exports a fixed production template with a global lock-frame template, concise per-shot final prompts, original dialogue injected into performance timing, quantified spatial layers, emotion-driven acting, natural-language camera placement and foreground-shoulder timing, continuity state packages, and no-more-than-15-second shots; no compact draft and no second optimization pass.
---

# Jimeng Dialogue Performance Storyboard

## Required inputs

Ask only for missing required inputs:

- `export_dir`
- `style`
- `aspect_ratio`
- source text/file

Do not ask for extra format choices unless the source is absent or unreadable.

## Mandatory reference loading

For normal script-to-storyboard generation, read these files before drafting shots:

1. [references/stable-shot-contract.md](references/stable-shot-contract.md) — five-module hard contract for stable shots: pre-storyboard planning, quantified prompt constraints, camera blocking, listener micro-reactions, and flashback/post handles.
2. [references/output-template.md](references/output-template.md) — final Markdown structure, global lock-frame, fixed shot card, negative prompt.
3. [references/prompt-performance-rules.md](references/prompt-performance-rules.md) — direct-copy prompt style, original-dialogue preservation, emotion/action/voice rules.
4. [references/spatial-camera-continuity.md](references/spatial-camera-continuity.md) — spatial locking, props, listener reactions, visible camera placement, two-person shoulder-visible compositions, high-risk anti-weak constraints.
5. [references/validation-checklist.md](references/validation-checklist.md) — final checks before saving.

For skill maintenance only, load the specific reference being edited plus this `SKILL.md`; load all references before changing cross-cutting rules.

## Hard defaults

- Export one final Markdown directly to `export_dir`; do not output a draft table first.
- Preserve all original dialogue, OS, OV, system, inner monologue, punctuation, quotes, ellipses, odd spacing, and typo names exactly unless the user permits edits.
- Keep every shot `<=15s`. Estimate duration as `max(visible action, real/TTS audio) + 0.5-1.5s reaction margin`.
- If identity, multi-person blocking, physical contact/prop transfer, visible lip-sync, and camera movement contain three or more high-risk items in one shot, downgrade the camera/action or split the shot. Do not solve structural overload by writing a longer prompt.
- OS/OV/system/inner lines, phone text, UI text, and dense captions are post-production audio/overlays by default; visible mouths stay closed.
- For any cross-time, cross-space, memory, imagination, montage, or dream boundary, generate the two sides as independent clips. Reserve a stable 0.5-0.8s tail handle in the trigger/return shot and a stable 0.5-1.0s head handle in the inserted shot before dialogue; put white flashes, dissolves, and J/L sound bridges in QA/post-production notes, never ask the model to morph locations.
- Do not reference or reuse other local skills.
- Ask no extra questions for missing visual details. Infer from source context, style, genre, and scene logic; record material assumptions in `使用说明`.

## Core workflow

1. Read the source and identify scenes, speakers, OS/OV/system lines, narration/action beats, props, clothing/body state, and crowd/background beats.
2. Build global locks: style/aspect, character identity, clothing/body state, scene anchors, background behavior, common negative prompt, and a scene state table. The table is the single source of truth for each location's fixed objects, character physical slots, visible left/centre/right arrangement, facing direction, movement lanes, prop owners, light, and allowed changes.
3. Create shot cards directly in the fixed template. Before splitting, decide the visual unit of the beat: if the same space, same emotional cause, same speaking window, and same physical relationship can be preserved, prefer one internally staged shot with a clear opening hold, bounded push/turn/focus, readable micro-action landing, and tail state. Split only when speaker handoff, time/place change, subject priority, prop/contact overload, or camera view change would otherwise make the prompt unstable. At every cross-time or cross-space boundary, design the trigger tail, independent inserted-shot head, and post-production bridge as separate deliverables. At every ordinary cut, define a usable outgoing hold and incoming hold before writing the new action.
4. For each shot, write `【画面描述｜直接复制】` as the actual Jimeng feed prompt, not a director note. It must include the core space/action/emotion/voice/camera/state information in one readable paragraph.
5. Fill per-shot visible cast and QA fields: `出现人物`, `校验记录`, `空间锁定`, `摄影设计`, `运镜时机`, `表演轴`, `声音轴`, `口型分窗`, `状态继承`, `剪辑衔接`, `必要约束`.
6. Create `原文保留检查表` for all source beats, not only dialogue.
7. Validate, save the `.md` under `export_dir`, and report the path plus a compact validation summary.

## Non-negotiable output behavior

- `【画面描述｜直接复制】` must stay `<=500` Chinese characters. Treat 500 as a ceiling, not a target; prefer the shortest natural-language prompt that preserves identity, space, action, performance, camera, voice, and tail state.
- Direct prompts must not contain loose labels such as `声音语气：`, `表情：`, `动作：`, `表演增强：`, or `情绪：`.
- Direct prompts must not contain editing/meta words such as `剪辑`, `切到`, `反打到`, or `下一镜执行`. Two-person shot intent must be written as visible foreground shoulder, subject position, facing direction, and background anchor.
- Multi-character scenes must lock static scene anchors first, then screen zones, front/back, facing/back-facing/diagonal-facing, eyeline, distance/barrier object, prop ownership, and tail state.
- All spatial words must name their coordinate basis: prefer `画面左/中/右/前景/中景/背景`; if using character-relative position, write `在A的右侧/桌对面/身后半身距离` and pair it with a screen zone.
- For seated/table/vehicle/door scenes, assign physical slots in global tables and reuse them in every shot. Lock real-world topology before screen composition: same-side neighbours must be written as one same-side group with internal left/right seats and the coordinate basis for those seats, e.g. `以二人坐在桌内侧、面朝餐桌对面的身体左右为基准`. Then add shared table/seat/door boundary, distance, facing, and `不隔桌/不面对面`; opposite-side characters must be written as separated by the table/door/aisle and must not be placed between same-side neighbours. Camera framing may change, physical slots must not.
- State inheritance is the next shot's first-frame lock. The next shot's direct prompt must absorb the previous tail state's key physical facts before starting new action.
- State inheritance must be semanticized into the next shot's `【画面描述｜直接复制】`: restate visible character slots, screen side, facing/eyeline, prop positions/owners, and any likely visible foreground/background characters before the new action begins.
- Direct prompts must not use `继承`, `延续上一镜`, `空间保持`, `位置继承`, or `物理座位不变` as shorthand. Rewrite them as current-frame physical facts: who is in which slot, which prop is at which location, and what is visibly fixed.
- Every spoken line must have a mouth-window record: one visible speaker, exact start/end time, the original words, intra-line pause/weight, the moment the mouth closes, and the listener's delayed reaction. Do not switch visible speakers without a closed-mouth handoff; genuine overlapping dialogue is post-production audio by default.
- Every adjacent pair must have a cut-handoff record. For a direct continuation, hold a usable 0.3-0.6s physical outgoing state and begin the next clip from the same physical facts; for a change of place/time, use the longer independent handoff rule. The handoff record states picture cut type in natural language, outgoing/incoming holds, movement direction or pause state, shared sound, and any required reference frame.
- The scene state table is authoritative: each shot must state which facts it reads from the table and which facts it changes. A new scene view must restate fixed objects, each visible character's physical slot, screen zone, facing, eye-line, distance/barrier, movement lane, and active prop owner in natural language. Never use abstract film-school position terms in a direct prompt.
- Flashback, memory, imagination, original-plot preview, or montage beats that contain plot-critical visible action must be split into independent short shots. Do not rely on `脑海浮现` or `后期插入` inside a real-time reaction shot to generate concrete action.
- Cross-scene continuity is not generated by a single morphing prompt: the trigger/return direct prompt must end on a concrete, stable physical state, and the flashback/insert direct prompt must begin with its own stable scene anchor before any spoken line. White flashes, dissolves, speed ramps, and sound bridges belong only in QA or post-production instructions.
- `【必要约束｜可追加】` must not use broad phrases like `无清晰口型`, `无清晰人脸`, `无清晰面部`, or `无口型`; use positive crowd/background control instead.
- Non-speaking visible important characters require delayed micro-reactions, not only `闭口`.
- Shot size, character occupancy, and performance detail must match. Do not place fingertip/fist/eye-detail acting in a wide or crowded medium frame. Do not split a continuous emotional beat merely to show a micro-action; first consider an internal camera path: relation view -> controlled push/focus to the micro-action -> emotional tail frame.

## Output location

Save the final Markdown in the user-provided `export_dir`. If the Codex environment also needs a user-facing copy, place it under the current task’s `outputs/` folder and mention only that output copy in the final response.
