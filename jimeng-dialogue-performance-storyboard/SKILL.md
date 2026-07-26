---
name: jimeng-dialogue-performance-storyboard
description: Convert a supplied script, novel scene, or dialogue-heavy beat into a Jimeng/Seedance-ready formal storyboard Markdown in one pass. Use when the user provides source text/file plus export directory, visual style, and aspect ratio, and expects directly usable fixed-template prompts with original dialogue preserved, semantic direct-copy picture descriptions, camera timing, emotion-driven acting, lip-sync/OS handling, prop/spatial continuity, negative prompts, and shots of 15 seconds or less.
---

# Jimeng Dialogue Performance Storyboard

## Required inputs

Ask only for missing required inputs:

- `export_dir`
- `style`
- `aspect_ratio`
- source text/file

Do not ask for extra format choices unless the source is absent or unreadable.

## Token-efficient loading

For normal generation, read only:

1. [references/runtime-brief.md](references/runtime-brief.md) — low-token execution contract.
2. [references/output-template.md](references/output-template.md) — required Markdown structure and field order.

Read [references/shot-patterns.md](references/shot-patterns.md) only when the source contains any of these, or validation flags them:

- multi-person blocking;
- table/vehicle/door/gate/hallway scenes;
- palace/hotel/lobby/street/campus/canteen scenes where a candidate space phrase may help but must be verified against source facts;
- prop transfer, clothing transfer, money/card/phone/plate ownership;
- walking/chase/entry/exit;
- flashback, montage, memory, dream, imagination;
- an overloaded single prompt that combines space setup, prop retrieval/reveal, dialogue, listener reaction, and camera/focus changes;
- a user complaint about spatial ambiguity, camera language, stiff listeners, or weak emotion.

Before saving, run `scripts/validate_storyboard.py <output.md>` for fast structural validation. If it reports issues, fix the named shots. Read [references/validation-checklist.md](references/validation-checklist.md) only for final manual audit or when the script flags ambiguity not covered by simple checks.

This skill targets the current fixed template only. Do not preserve, repair around, or silently accept older output formats. If an older Markdown conflicts with the current contract, regenerate it with the current template instead of adding compatibility branches.

## Hard defaults

- Export one final Markdown directly to `export_dir`; do not output a draft table first.
- Preserve all original dialogue, OS, OV, system, inner monologue, punctuation, quotes, ellipses, odd spacing, and typo names exactly unless the user permits edits.
- Keep every shot `<=15s`; estimate duration as `max(visible action, real/TTS audio) + 0.5-1.5s reaction margin`.
- `【画面描述｜直接复制】` is the final Jimeng positive prompt and must be self-contained with the global locks, semantic, and `<=500` Chinese characters; prefer `220-380` Chinese characters.
- Treat global style/light/background/negative as reusable locks; do not repeat them verbatim in every direct prompt.
- OS/OV/system/inner lines, phone text, UI text, and dense captions are post-production audio/overlays by default; visible mouths stay closed.
- For an episode or multi-scene source, internally maintain a compact key-state line for cross-scene clothing, props, injuries, and UI states. Output it only in the scene state table when it affects later shots.
- Do not reference or reuse other local skills.
- Infer missing visual details from source context, genre, style, and scene logic; record material assumptions in `使用说明`.
- Do not optimize for old generated files. The acceptance target is the current template, current direct-prompt rules, and current validator.

## Core workflow

1. Read the supplied source and extract beats: scene, visible cast, dialogue/OS/system/OV, action, prop/clothing state, crowd/background, memory/flashback boundaries, UI overlays, and sound effects. When regenerating, do not read, transform, prefix, or preserve a prior storyboard; the source text and current skill contract are the only generation inputs.
2. Build a compact episode state line before scene locks: track only cross-scene clothing, props, injuries, UI, and ownership changes. Build scene locks from that line: fixed anchors, physical slots, screen zones, facing/eyelines, movement lanes, active props, allowed changes, forbidden swaps.
3. Build one internal story-beat contract for every meaningful turn: what the viewer does not know at the opening, what visible cue changes that understanding, the emotional turn, and the concrete state at the end. A visible `S场景-节拍` group may contain exactly one such new recognition. If arrival, accusation, confession, relation redefinition, or departure each change what the viewer knows, make separate groups even when they occur in the same location. This contract is never output as a card or pasted into Jimeng; use it only to select child shots that collectively deliver the new recognition.
4. Select any scene phrase only as a candidate. Use it only after confirming the source supports its fixed objects, entrances/exits, character slots, and prop logic; otherwise fall back to generic space locking.
5. Assign each beat a shot function: establish, dialogue, reaction, prop transfer, pressure, comedy pause, movement, flashback insert, return, object insert, or emotional cutaway. When a turn needs two or more visible links to create its recognition, make one visible shot group such as `S1-03`, with children numbered `1/2/3`: one child may show the cue/evidence, one may carry a simple gaze/focus movement, and one may land the dialogue or changed relation. The group is a reading container, not a Jimeng prompt; output no master-shot card. Put the summed child-shot duration beside the group ID, put `【出现人物】` once on the group, then write the actual Jimeng prompts continuously with `【镜号】1/2/3`; do not add `分镜1` headings. The children collectively deliver the internal beat. For dialogue, default to relation, speaker, and listener-reaction frames. Add an object/empty-space cutaway only for a source-supported change, and treat it as a separate T2V card unless it qualifies as an in-place focus landing.
6. Choose camera by function. Every child must state a readable shot size, camera placement/angle, static or one bounded path, and visual landing task in its direct prompt. `固定` is a deliberate choice for stable lip-sync or stillness, never the default; do not default to `中近景固定`. State physical relation separately from screen composition: for every visible named person, name body orientation toward a fixed anchor or another person, then head/eye turn only if it differs, then relative position, then camera side. Do not use a bare `朝左/朝右` as a body direction. Avoid abstract film-school terms in direct prompts.
7. Write compact shot groups in the fixed template. Each group has `【出现人物】` once; every actual child card contains the four default child fields `【镜号】`, `【画面描述｜直接复制】`, `【表演与声音】`, and `【状态继承】`. Add optional fields only when the child genuinely needs them. If one child changes a visible state before dialogue or reaction, design its start, one visible transition, stable end, and tail before writing the prompt. Put essential space, action, emotion, voice, camera, prop state, listener reactions, and tail state inside `【画面描述｜直接复制】`; production notes may expand but cannot replace it. Estimate spoken duration from the original Chinese text before assigning seconds; never shorten a line merely to keep a group compact.
8. For every person/prop position or ownership change, write the new visible fact into the next shot's direct prompt opening.
9. Internally check every dialogue and non-dialogue source beat. Include `原文保留检查` only when the user requests auditability, source fidelity is disputed, or the scene is high risk.
10. Run `scripts/validate_storyboard.py` on the saved Markdown; fix failures by rewriting to the current template, not by weakening rules. For high-risk scenes, add the compact validation appendix and perform a manual audit against `validation-checklist.md`. If useful, also copy to the current task `outputs/` folder.

## Non-negotiable direct-prompt rules

- Start complex shots with a fixed physical anchor: table, doorframe, car door/window, hallway line, counter, bed, sofa, gate pillar, road edge, or background window.
- Lock story topology before screen composition: same-side/opposite-side, beside/across/behind, distance, barrier/contact object, facing, eyeline, active prop owner/state.
- Name coordinate basis: `画面左/右/前景/背景` for screen; `A的右手边/桌对面/身后半身距离` for character relation.
- Do not use direct-prompt shorthand: `继承`, `延续上一镜`, `空间保持`, `位置继承`, `物理座位不变`, `剪辑`, `切到`, `反打到`, `下一镜执行`, `脑海浮现`, `后期插入`, `声音语气：`, `表情：`, `动作：`, `情绪：`.
- Do not list OS/system voices or mentioned-only/offscreen characters under a group-level `【出现人物】`. List only visible people/groups, one per line. A person may remain listed for the whole group even when a particular child only retains their blurred shoulder or offscreen reaction; do not repeat the cast field on children.
- Do not merge a long visible line, a speaker handoff, and a meaningful body/position change into one child. Keep the line on its speaking child; put an exit, turn-away, approach, transfer, or newly exposed relation in the preceding or following child.
- Every direct prompt must naturally include: `景别` + `机位/角度` + `镜头静止或单一路径` + `每个可见人物的身体朝向锚点、必要时的头部/视线转向、相对位置` + `本镜唯一动作/台词落点`. Use `身体面向柜台/面向A/背向入口` rather than a bare `朝左/朝右`; screen left/right alone does not establish body direction or relationship.
- On every shot-size change, reverse angle, over-shoulder shot, or new dialogue card after movement, restate the full body-facing relation from zero. For a face-to-face dialogue landing, the speaker and listener default to `身体面向对方`; do not preserve a prior walking/counter/exit-facing body with only `头部转向对方` unless the story intentionally shows avoidance, refusal, leaving, or being blocked. If a character must turn before speaking or receiving a line, make that turn the visible opening transition and only start dialogue after the body is fully facing the target.
- For strict shot/reverse-shot dialogue, pair the camera wording exactly: `A肩后拍B` must be followed by `B肩后拍A` when the next child is the reverse. Do not drift into `B右前方/侧前方` for the reverse. Both sides must repeat the same face-to-face body orientation, distance/barrier, prop holder/position, and background anchor.
- Write only people, props, and fixed anchors actually visible in this child. A group may list a wider visible cast, but a hand insert must not carry off-frame police, crowd, or listener orientation. Never use placeholders or alternatives such as `当前主角`, `当前对话者`, `或当前对话者`, or `视情况` in a direct prompt.
- Never let props flash into existence or move through impossible body geometry. Before any prop transfer, the direct prompt must show the prop's current owner/container/surface, the hand that retrieves or presents it, the receiver becoming physically reachable, contact, release, and final holder. If the receiver is behind, side-behind, turned away, seated out of reach, or separated by another person/object, first make a separate positioning child where the receiver turns, steps forward, or the giver moves to face them; only then transfer the prop.
- Match shot size to occupancy. A frame limited to hands, a card, a pen, a phone, or a tabletop is `手部特写` or `斜俯拍近景`, never a medium shot. A character cannot keep a wrist restrained while independently signing unless the prompt visibly states how the hand is guided; otherwise end the restraint first and show signing in the next child.
- Treat any visible carry-over fact as a state: body pose/facing/gaze, hand and prop owner/position/contact, clothing/accessories/injury, door/window/light/UI state, relation distance/barrier, speaking-mouth mode, and a plot event's visible result. Track only the states that change or must be visible in the next shot.
- When one T2V card contains a state change, write it in this order: opening state -> one visible transition -> stable end state -> dialogue/reaction -> tail state. Put the stable end state and tail state as exact natural-language sentences inside `【画面描述｜直接复制】`, not only in `【镜内状态转换】` or `【状态继承】`. A state being left and its replacement must never be described as simultaneous. Do not use story summaries such as `打完电话` or `递给B`; write the observable transition and the new stable state.
- Permit at most one high-impact state change in a dialogue card: for example, phone leaves ear, a person sits, a door closes, a coat is put on, or a cup changes owner. Complete the transition before visible dialogue begins. Split the card when it also needs a transfer, crossing, second state change, or non-static camera move.
- For a phone call, name the full chain when it matters: `phone at which ear/hand -> thumb ends call -> phone leaves ear -> final hand/table/pocket position -> ear clear -> dialogue mouth opens`. The following shot must open from that final position, never from the prior calling pose.
- For a long or multi-speaker visible dialogue card, allocate the generation budget in this order: correct speaking mouth -> one listener response -> camera. Keep a long single-speaker line on a fixed frame with one small listener reaction, or use one slow push with the listener motionless except closed-mouth breathing. Split speaker handoff into separate windows; do not combine long lip-sync, a moving listener, and a moving camera in one card.
- Distribute an important emotional turn across its child-shot group instead of repeating a full emotion chain in every card: show one pressure leak or external cue, then one perception change, then the controlled line/reaction and residual state. Each child must reveal a new stage; do not repeat the same eye, jaw, hand, and breath description across adjacent children unless the source deliberately holds it.
- Non-speaking visible important characters need closed-mouth micro-reactions caused by the speaker/action; `闭口` alone is insufficient.
- Micro-actions must match shot size. If the beat depends on eyes, mouth corners, throat, fingertips, fists, chopsticks, card, phone, or plate edge, use close-up/insert or a timed push/focus landing.
- Choose dialogue framing by the visible evidence it needs: use a two-person medium shot to show distance, a door/table/sofa barrier, and who advances or retreats; use a medium close-up for a normal reply with shoulders and active hands; use a close-up for a visible breath, jaw, gaze, or mouth-corner change; use an insert for a hand, phone, clothing, or object that changes the meaning of the line. Return to a relation shot after 2-3 dialogue turns or whenever distance, power, or prop ownership changes.
- Do not describe dialogue framing with abstract labels such as `压迫感`, `呼吸感`, `掌握主动`, or `情绪张力`. Translate them into visible facts: frame edge distance, empty space, body distance, door/table barrier, gaze direction, breath, hand contact, or a camera push/pull.
- An object or empty-space cutaway must carry the current interaction: a phone turned face-down, a hand leaving a sleeve, an empty seat, a door gap, an untouched cup, a lift display, or another source-supported object/space. Generate a full empty-space/object cutaway as a separate T2V card by default and use `【剪辑衔接】` to state the sound bridge; never insert generic scenery merely to break up dialogue.
- Keep an insert in the same T2V card only when it is one continuous focus landing on a prop already visible in the opening frame: same location and light, no hard cut, no visible speaking mouth during the insert, no prop/contact transfer or character crossing, no return to a different face, and only one focus/camera event in the card. Otherwise split it into an independent card.
- For an emotional peak, it is valid to omit the full action only as an independent result card when the unseen action could imply transfer, impact, or a changed character state. State the offscreen actor/action and the visible result clearly; keep all visible mouths closed and use post-production sound. Do not rely on vague words such as `留白`, `意象`, or `日漫感`.
- Split or simplify if one shot combines three or more high-risk tasks: multi-person blocking, prop/contact transfer, visible lip-sync, camera movement, character crossing, crowd/cars/doors, or world/time change.
- Use shot groups for overloaded but continuous beats: each subshot has one main generation task, restates the current physical facts, and preserves original dialogue/OS without changing order.

## Output location

Save the final Markdown in the user-provided `export_dir`. If the Codex environment also needs a user-facing copy, place it under the current task’s `outputs/` folder and mention the copy path in the final response.
