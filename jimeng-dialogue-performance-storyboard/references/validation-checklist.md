# Validation Checklist

Before final response, confirm:

1. Every shot is `<=15s`.
2. Every shot is a full card, not a shot table.
3. Every shot has `【出现人物】`, `【画面描述｜直接复制】`, `【校验记录】`, `【空间锁定】`, `【摄影设计】`, `【运镜时机】`, `【表演轴】`, `【声音轴】`, `【口型分窗】`, `【状态继承】`, `【剪辑衔接】`, and `【必要约束｜可追加】`.
4. `【出现人物】` lists every visible named character or visible group one per line, and does not list OS/system voices unless they have visible entity.
5. Per-shot final prompts compress the visible essentials from space, emotion/performance, dialogue/OS/system tone, camera movement, and state inheritance into `【画面描述｜直接复制】`; QA fields are not the only place these appear.
5A. Direct prompts are not lazy shorthand. They must be semantic and self-contained enough to paste into Jimeng: spatial topology, visible reactions, voice tone, camera path, prop/person state, and tail frame are all present when relevant.
6. If a shot has dialogue/OS/system sound, the direct prompt includes the original line plus key tone controls such as pace, volume, pause, or tail tone.
7. Every direct prompt begins with or clearly contains a compact spatial lock: static scene anchor, screen side with coordinate basis, foreground/midground/background, front/back relation, facing/back-facing/diagonal-facing, eyeline, distance or separation object, active prop position, and scene anchor.
8. For table/room/crowd shots, the direct prompt starts with 1-2 unmoving anchors before people, such as table edge, doorframe, window, counter, sofa, bed, wall lamp, hallway line, or car door.
9. Bare spatial words such as `左侧/右侧/前面/后面` are not used alone in high-risk shots; they are clarified as `画面左侧`, `A的右侧`, `桌对面`, `前景`, or `背景`.
10. Spatial layers are non-contradictory and quantified when foreground/background matters.
11. `【空间锁定】` is not only left/right: it includes at least two relational anchors among front/back, face-to-face/back-to-camera/diagonal-facing, distance, barrier object, contact point, and prop ownership.
12. Active props have starting anchors and physical tail states.
13. Two-prop exchange shots state both props' starting positions, contact hand/edge, movement path, release moment, final positions, and `双手离开/不再拿回` when final ownership matters.
14. Any prop moved by a character is visibly within that character's opening reach, or the prompt first stages the reach/contact path; no character moves a prop that is currently on another character's side by implication.
14A. Barrier wording does not accidentally create body crossing: if a character only looks at a table/counter/window prop, the direct prompt says the character stays on their side, keeps the upper body upright, and only the gaze crosses the barrier. If leaning/bending is intended, the direct prompt quantifies the lean angle, foot anchor, hand support/contact point, barrier crossing limit, and tail pose.
15. State inheritance is treated as the next shot's first-frame lock, and the next direct prompt restates key physical facts instead of only saying `延续上一镜`.
15A. If a person or prop changes position/owner/wearing state in one shot, the next shot's direct prompt explicitly restates the changed state before new action begins. A state package alone is insufficient.
16. If no character physically moves between adjacent shots, the relationship phrase stays identical across shots; only camera screen layer may change. Example: keep `同侧邻位半身距离` consistent and do not rewrite it as `桌对面` or `右后` in the next shot.
16A. Same-side seated/standing characters are not split into global screen-left/screen-right extremes or foreground/background depth. The direct prompt first names the same-side group, the coordinate basis for internal left/right, internal seat/order, same-depth or near/far relation, shared side/barrier, distance, and `不隔桌/不面对面/不一前一后`; any foreground shoulder or close-up wording is explicitly camera-side, not a new physical position.
17. In seated/table/vehicle/door scenes, physical slots are present in global tables and reflected in risky direct prompts; screen layer changes do not contradict physical slots.
17A. `人物位置与拍摄侧锁定表`, `场景与道具锁定表`, and `场景空间状态表` use the same topology vocabulary as the shot prompts: fixed anchor first, same-side/opposite-side group, group-internal order, screen zone, facing/eyeline, distance/barrier/contact object, prop reachability, and forbidden swaps.
18. Original dialogue/OS/OV/system/inner lines and non-dialogue `△`/narration/action beats are preserved in `原文保留检查表`; no missing source beats.
19. Flashback, memory, imagination, original-plot preview, and montage beats with visible plot action are split into independent short shots; direct prompts do not depend on `脑海浮现/后期插入` to show concrete action.
20. Plot-driving action/reaction beats appear in `【画面描述｜直接复制】`, not only QA fields.
21. Every dialogue/OS/system line has pace, volume, pause/tail tone, emotional motive, and mouth-sync/post-production handling.
22. OS/OV/system/inner lines do not drive visible mouth movement.
23. Non-speaking visible important characters have closed mouths plus delayed micro-reactions.
23A. Multi-person interaction is not stiff: for each visible important non-speaker, the direct prompt includes an appropriate listener reaction such as gaze follow, blink, brow/mouth shift, shoulder/posture adjustment, or hand/prop micro-action, scaled below the speaker's action.
24. Each important emotional turn in the direct prompt has visible body evidence, not only a label: at least two of eye/brow/mouth/breath/finger/shoulder/posture/prop-contact plus the trigger cause.
24A. Micro-actions match shot size: fingertip/knuckle/pen-tip/chopstick-tip details are only used in close-up or insert shots. Multi-person medium shots use whole-hand, shoulder, torso, or prop-contact actions that remain visible above the table/counter.
24B. A shot with subtle micro-action cannot use a fixed medium/wide camera unless the camera is already close enough to read the detail. Otherwise it must use a time-anchored push/focus landing or enlarge the micro-action.
25. Camera design is moderately cinematic unless high-risk: across a scene, avoid overusing fixed camera; use safe push/pull/turn/focus/side-follow/foreground-shoulder when justified and bounded.
25A. Shot size capacity is realistic: medium close shots do not try to carry a full three-person relation with different body levels. If a standing person, two seated people, table edge, and active props must all be visible, the shot uses a horizontal medium/medium-wide relation view or is split.
25B. If an oblique table shot is used to show an opposite-side character's face, the prompt states camera side/angle, visible face angle, and the same-side seated pair's near-end/far-end order. Do not also claim they are the same distance from camera; oblique shots must say who is closer and who is farther while preserving same-side seating.
25C. If a multi-person medium shot contains a plot-critical hand/fist/plate micro-action or a silent pressure reaction, it either enlarges the action to whole-hand/shoulder/body movement or uses a time-anchored medium-to-close push/focus landing. The landing frame must name the still-valid table/door/prop positions so the camera move does not reshuffle blocking.
25D. Shot splitting preserves emotional continuity. A micro-action in the same emotional beat is not split into a separate isolated card unless it cannot be shown by a safe internal push/focus. Conversely, any direct prompt that contains small face/hand/prop details must have a matching close enough shot size or a time-anchored path that lands close enough.
26. Every camera movement has opening hold, static anchor, physical path, distance/angle/speed, focus target, landing frame, and unchanged character/prop slots.
27. If identity, multi-person blocking, physical contact/prop transfer, visible lip-sync, and camera movement contain three or more high-risk items in one shot, the shot has been downgraded or split.
28. `【必要约束｜可追加】` does not use broad phrases like `无清晰口型`, `无清晰人脸`, `无清晰面部`, or `无口型`.
29. Direct prompts do not contain loose labels such as `声音语气：`, `表情：`, `动作：`, `表演增强：`, or `情绪：`.
30. Direct prompts do not contain editing/meta words such as `剪辑`, `切到`, `反打到`, or `下一镜执行`; two-person shot intent appears as visible foreground shoulder, subject position, facing direction, and background anchor.
31. Direct prompts do not use continuity shorthand such as `继承`, `延续上一镜`, `空间保持`, `位置继承`, or `物理座位不变`; they restate current-frame physical facts.
32. Direct prompts are `<=500` Chinese characters; 500 is a ceiling, not a target.
33. Direct prompts avoid ambiguous pronouns for key actions, speech, OS/system reactions, prop ownership, and listener feedback.
34. High-risk prop/crowd/vehicle/long-dialogue shots have first-round validation targets.
35. The `.md` is saved under `export_dir`; report the path plus validation summary.
36. Every cross-time/cross-space flashback, dream, imagination, or montage boundary has two independently generated cards: an outgoing stable tail handle (0.5-0.8s) and an incoming stable head handle (0.5-1.0s before dialogue/action).
37. The direct prompts at those boundaries describe only physical holds and their own scene anchors; white flashes, dissolves, speed ramps, and J/L sound bridges appear only in QA/sound/post-production notes.
37A. Flashback is not a hard unexplained cut: trigger/insert/return cards include visible stable handles, and `声音轴/剪辑衔接/校验记录` includes a post bridge such as 3-5 white frames, ambience dip, memory ambience prelap, low-saturation texture, edge vignette, or mild handheld feel.
38. Every visible line has a `【口型分窗】` row with one visible speaker, original words, start/end, mouth-closing boundary, pause/weighted word, and the other visible characters' closed-mouth rule. Speaker changes have a closed-mouth handoff; true overlap is planned as post-production audio.
39. Every neighbouring pair has a `【剪辑衔接】` record. Same-moment cuts preserve a 0.3-0.6s usable outgoing/incoming state; action continuations preserve direction, body phase, prop contact, camera speed, and shared ambience.
40. Each scene has one `场景空间状态表` row listing fixed objects, physical slots, screen zones, facing/eye-lines, movement lanes, empty areas, prop owner/state, light, and allowed changes. Every shot's opening and tail have been compared to that row.
41. Direct prompts use only observable natural language for space and camera placement; they do not rely on abstract film-school position jargon.
