# Validation Checklist

Run `scripts/validate_storyboard.py <output.md>` first. Use this checklist only for the compact manual pass after script validation.

## Structure

- The file uses the current compact `output-template.md` structure only; do not accept legacy headings, draft-table layouts, or compatibility aliases.
- Every `#### S场景-节拍` group has one group-level `【出现人物】`, followed directly by one or more locally numbered `【镜号】1/2/...` children. Each child has the four default fields; optional fields appear only where their corresponding generation risk exists.
- Every shot is `<=15s`.
- Group-level `【出现人物】` lists only visible people/groups, one per line. Do not list OS/system voices or mentioned/offscreen characters, and do not repeat this field inside child cards.
- `【画面描述｜直接复制】` is `<=500` Chinese characters and can stand alone as the Jimeng positive prompt.
- `## 通用负面提示词｜直接复制` includes the baseline identity/stability and anti-stiffness terms.

## Source fidelity

- Every original dialogue, OS, OV, system line, inner monologue, action beat, crowd beat, narration, flashback marker, prop/clothing change, and reaction beat is checked internally. It appears in `附录｜原文保留检查` only when that appendix is required.
- Plot-driving non-dialogue beats appear in direct prompts or explicit post-production handling, not only vague QA notes.
- Original wording is preserved unless the user permits changes.
- Cross-scene clothing, prop, injury, and UI changes appear once in the episode state line and are restated as current visible facts after each change.
- 每个重要剧情转折均在内部检查为 `观众开场认知 -> 可见线索 -> 情绪转折 -> 观众终场认知/状态`。这个母节拍不输出为镜头卡，由子镜头共同完成。

## Direct-prompt safety

- No direct prompt contains shorthand/meta terms: `继承`, `延续上一镜`, `空间保持`, `位置继承`, `物理座位不变`, `剪辑`, `切到`, `反打到`, `下一镜执行`, `脑海浮现`, `后期插入`, `声音语气：`, `表情：`, `动作：`, `情绪：`, `左外`.
- Each complex shot starts with a static anchor and states physical topology before screen composition.
- Spatial language names its basis: screen side, character-relative side, table/door/car side, foreground/background.
- Important pronouns are resolved: actor, speaker, prop owner, mover, receiver, and listener are named.

## Space, props, and continuity

- Scene state tables, position/camera-side tables, and prop tables use the same vocabulary as direct prompts.
- Any scene pattern used has source evidence for its fixed anchors, entrances/exits, physical slots, barrier, and props. If not, the prompt falls back to generic space locking.
- Same-side pairs stay one group before screen layering; opposite-side characters stay across the barrier and never insert between them.
- Oblique shots name near-end/far-end order without changing physical seats.
- Active props have start point, contact hand/edge, path, release/new holder, and tail rest position.
- A character only moves a prop within visible reach, or the reach path is staged first.
- Every person/prop/clothing/door/window state change is restated as current visible fact at the next shot opening.
- Each same-card state change has one declared opening state, one visible transition, and one stable end state before dialogue/reaction. The old and new states are never described as simultaneous.
- When `【镜内状态转换】` exists, its `终态直投句` and `尾帧直投句` both appear verbatim in `【画面描述｜直接复制】`; a state table or production note alone does not count.
- A dialogue card contains at most one high-impact state change. If it also needs transfer, crossing, another change, or a non-static camera move, it is split.
- Phone-call changes state the active hand and ear explicitly: call pose -> hang-up contact -> phone leaves ear -> final hand/table/pocket position -> ear clear -> dialogue. The next shot begins from that final position.

## Performance, sound, and lip-sync

- Each important emotion has trigger -> visible face/body/prop leak -> voice tone.
- 子镜头组中的每张卡只贡献一个新的剧情/表演阶段：线索或压力泄露 -> 感知变化 -> 信息落点 -> 余波结果；不重复完整情绪链，也不在每张卡复述同一种泛化微动作。
- Micro-actions are chosen by emotion function and current source props/body state, not by hard-coded character type; repeated leaks are varied when possible.
- Non-speaking visible important characters have closed mouths plus a delayed low-amplitude reaction.
- Dialogue/OS/system/OV lines include timing, pace, volume, pause/tail tone, motive, and mouth/post-production rule.
- One visible mouth speaks per window; speaker handoff has mouth close and a short reaction gap.
- Every `【口型分窗】` begins with `优先级：口型 > 听者反应 > 运镜`. Long dialogue uses either fixed frame plus one small listener response, or one slow camera move plus a listener held to breath/gaze; it never combines long lip-sync, visible listener action, and a moving camera.
- OS/system/OV/inner voice do not drive visible mouth movement.
- UI, phone, payment, or system overlays reserve a safe zone away from faces and active hands; dense text is assigned to post-production unless generation is explicitly required.
- Overlapping sound follows the stated priority: visible dialogue > key sound effect > OS/system > ambience/music.

## Camera and transitions

- Shot size matches readable action. Micro eye/hand/prop details require close-up/insert or timed push/focus landing.
- `#### S场景-节拍` 只是组容器，不输出主镜头提示词。每个本组内的 `【镜号】1/2/...` 都有独立时长且只承担一个主要任务，共同完成该节拍所需的线索、感知变化和/或信息落点；子镜头不得引入无关的新剧情转折。
- 重跑时只以原文和当前技能为输入，不读取或给旧分镜批量补前缀。每条镜头从可见主体、身体朝向锚点、站位、景别、机位、镜头状态和唯一落点重新设计。
- Dialogue framing serves a visible task: relation shots state distance/barrier/approach or retreat; medium close-ups retain the needed shoulder/hand/space information; close-ups name only readable face or breath changes; wide shots use distance or environment rather than eye detail.
- After two or three spoken turns, the sequence returns to a relation shot when distance, a barrier, prop ownership, or the apparent upper hand changes. The prompt states the new visible arrangement instead of an abstract power label.
- Object or empty-space cutaways are source-connected: they show a changed prop, an empty seat, a door gap, a phone, or another current relationship-bearing detail. Generic scenery is not used to fill time.
- A full object/empty-space/result cutaway is an independent T2V card by default and has `【剪辑衔接】` stating independent generation, post-production sound bridge, and the anchor state on either side.
- An insert may remain in one T2V card only when it is a single continuous focus landing on a prop already visible in the opening frame; it has no hard cut, visible speaking mouth, prop/contact transfer, character crossing, offscreen state change, or return to another face.
- At an emotional peak, an omitted action with an implied transfer, impact, or changed character state is an independent result card. It states the visible result, puts offscreen action/sound in post-production, and never relies on abstract words such as `留白`, `意象`, or `日漫感`.
- Fixed camera is not used for subtle medium/wide micro-actions unless stillness/contact precision is the point.
- Camera moves state opening hold, path, distance/angle/speed, focus target, landing frame, and unchanged slots.
- 每个场景先有一条关系景，再按台词、反应、物件或动作选择中近景、特写或明确的单一路径运镜；连续对白不得机械复用固定中近景。人物身体面向必须指向人物或固定物，头部/视线与身体不同才单独说明；画面左右与机位侧不能替代朝向。
- 切换景别、正反打、肩后镜头、从行走/出门/柜台/车窗/道具动作进入对白时，新镜必须重新声明完整身体朝向。普通面对面对话应写为双方身体面向对方；若只写头部/视线转向对方，必须有明确剧情理由：回避、拒绝、离开、被挡住或仍在执行上一动作。
- 正反打必须成对保轴：`A肩后拍B` 的下一条反打写 `B肩后拍A`，不可写成 `B右前方/侧前方` 这类松散机位；两条都重复同一距离、隔物/无隔物、道具位置、前景肩线比例和背景锚点。
- High-risk overload is split or simplified instead of solved by longer prompts.
- Flashback/memory/montage with visible action uses independent clips: trigger tail hold, inserted scene head hold, return hold. White flashes/dissolves/sound bridges stay in QA/sound fields.
- Background/crowd is positively controlled: count/zone/blur/movement/no readable dialogue; avoid broad negative phrases like `无清晰口型/无清晰人脸/无口型`.
