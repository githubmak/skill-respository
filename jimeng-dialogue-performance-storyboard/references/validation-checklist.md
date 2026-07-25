# Validation Checklist

Before final response, confirm:

1. Every shot is `<=15s`.
2. Every shot is a full card, not a shot table.
3. Every shot has `【画面描述｜直接复制】`, `【校验记录】`, `【空间锁定】`, `【摄影设计】`, `【运镜时机】`, `【表演轴】`, `【声音轴】`, `【口型分窗】`, `【状态继承】`, `【剪辑衔接】`, and `【必要约束｜可追加】`.
4. Per-shot final prompts compress the visible essentials from space, emotion/performance, dialogue/OS/system tone, camera movement, and state inheritance into `【画面描述｜直接复制】`; QA fields are not the only place these appear.
5. If a shot has dialogue/OS/system sound, the direct prompt includes the original line plus key tone controls such as pace, volume, pause, or tail tone.
6. Every direct prompt begins with or clearly contains a compact spatial lock: static scene anchor, screen side with coordinate basis, foreground/midground/background, front/back relation, facing/back-facing/diagonal-facing, eyeline, distance or separation object, active prop position, and scene anchor.
7. For table/room/crowd shots, the direct prompt starts with 1-2 unmoving anchors before people, such as table edge, doorframe, window, counter, sofa, bed, wall lamp, hallway line, or car door.
8. Bare spatial words such as `左侧/右侧/前面/后面` are not used alone in high-risk shots; they are clarified as `画面左侧`, `A的右侧`, `桌对面`, `前景`, or `背景`.
9. Spatial layers are non-contradictory and quantified when foreground/background matters.
10. `【空间锁定】` is not only left/right: it includes at least two relational anchors among front/back, face-to-face/back-to-camera/diagonal-facing, distance, barrier object, contact point, and prop ownership.
11. Active props have starting anchors and physical tail states.
12. Two-prop exchange shots state both props' starting positions, contact hand/edge, movement path, release moment, final positions, and `双手离开/不再拿回` when final ownership matters.
13. State inheritance is treated as the next shot's first-frame lock, and the next direct prompt restates key physical facts instead of only saying `延续上一镜`.
14. If no character physically moves between adjacent shots, the relationship phrase stays identical across shots; only camera screen layer may change. Example: keep `同侧邻位半身距离` consistent and do not rewrite it as `桌对面` or `右后` in the next shot.
15. In seated/table/vehicle/door scenes, physical slots are present in global tables and reflected in risky direct prompts; screen layer changes do not contradict physical slots.
16. Original dialogue/OS/OV/system/inner lines and non-dialogue `△`/narration/action beats are preserved in `原文保留检查表`; no missing source beats.
17. Flashback, memory, imagination, original-plot preview, and montage beats with visible plot action are split into independent short shots; direct prompts do not depend on `脑海浮现/后期插入` to show concrete action.
18. Plot-driving action/reaction beats appear in `【画面描述｜直接复制】`, not only QA fields.
19. Every dialogue/OS/system line has pace, volume, pause/tail tone, emotional motive, and mouth-sync/post-production handling.
20. OS/OV/system/inner lines do not drive visible mouth movement.
21. Non-speaking visible important characters have closed mouths plus delayed micro-reactions.
22. `【必要约束｜可追加】` does not use broad phrases like `无清晰口型`, `无清晰人脸`, `无清晰面部`, or `无口型`.
23. Direct prompts do not contain loose labels such as `声音语气：`, `表情：`, `动作：`, `表演增强：`, or `情绪：`.
24. Direct prompts do not contain editing/meta words such as `剪辑`, `切到`, `反打到`, or `下一镜执行`; two-person shot intent appears as visible foreground shoulder, subject position, facing direction, and background anchor.
25. Direct prompts do not use continuity shorthand such as `继承`, `延续上一镜`, `空间保持`, `位置继承`, or `物理座位不变`; they restate current-frame physical facts.
26. Direct prompts are `<=500` Chinese characters.
27. Direct prompts avoid ambiguous pronouns for key actions, speech, OS/system reactions, prop ownership, and listener feedback.
28. High-risk prop/crowd/vehicle/long-dialogue shots have first-round validation targets.
29. The `.md` is saved under `export_dir`; report the path plus validation summary.
30. Every cross-time/cross-space flashback, dream, imagination, or montage boundary has two independently generated cards: an outgoing stable tail handle (0.5-0.8s) and an incoming stable head handle (0.5-1.0s before dialogue/action).
31. The direct prompts at those boundaries describe only physical holds and their own scene anchors; white flashes, dissolves, speed ramps, and J/L sound bridges appear only in QA/sound/post-production notes.
32. Every visible line has a `【口型分窗】` row with one visible speaker, original words, start/end, mouth-closing boundary, pause/weighted word, and the other visible characters' closed-mouth rule. Speaker changes have a closed-mouth handoff; true overlap is planned as post-production audio.
33. Every neighbouring pair has a `【剪辑衔接】` record. Same-moment cuts preserve a 0.3-0.6s usable outgoing/incoming state; action continuations preserve direction, body phase, prop contact, camera speed, and shared ambience.
34. Each scene has one `场景空间状态表` row listing fixed objects, physical slots, screen zones, facing/eye-lines, movement lanes, empty areas, prop owner/state, light, and allowed changes. Every shot's opening and tail have been compared to that row.
35. Direct prompts use only observable natural language for space and camera placement; they do not rely on abstract film-school position jargon.
