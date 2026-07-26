# Runtime Brief

Use this file as the low-token execution contract for normal generation.

## One-pass workflow

1. Extract source beats: scene, visible characters, dialogue/OS/system/OV, action, prop/clothing changes, crowd beats, memory/flashback beats.
2. Build one compact episode state line for cross-scene clothing, props, injuries, and UI. Track only a state change that must survive a scene boundary.
3. Mark flagship beats before splitting: recognition, reveal, pressure stare, protection, cover story, comedic derailment, system burst, prop ownership change, emotional refusal, exit, flashback trigger. For each, internally write `观众开场认知 -> 可见线索 -> 情绪转折 -> 观众终场认知/状态`. One `S场景-节拍` group may carry only one resulting recognition. Separate groups when a scene changes from arrival to accusation, from accusation to confession, or from confession to relation redefinition. Spend camera energy here; do not average every line or output this internal contract.
4. Select scene/space patterns only as candidates. Verify source evidence before using; if the source conflicts or lacks required anchors, fall back to generic space locking.
5. Build scene locks before shots: fixed anchors, physical slots, screen zones, facing/eyelines, movement lanes, active props, allowed changes.
6. Choose each shot by function: establish, dialogue, reaction, prop transfer, pressure, comedy pause, movement, flashback insert, return.
7. Write every story beat as a visible group: `#### S1-01｜镜头组总时长：7.5s` with one group-level `【出现人物】`, followed directly by consecutive child blocks numbered `【镜号】1/2/...`. The group total is the sum of all child-shot durations in that group. Do not add `分镜1` headings. Each child is a separately generated Jimeng prompt with four fields: `【镜号】`, `【画面描述｜直接复制】`, `【表演与声音】`, `【状态继承】`. The direct prompt must stand alone with the global locks. Add optional controls only where the child is genuinely complex.
8. Before saving, run the final audit and fix failures instead of explaining them.

## Direct prompt hard limits

- `【画面描述｜直接复制】` <= 500 Chinese characters; prefer 220-380 when possible.
- It must include, in this priority order: static anchor -> physical topology -> screen/depth/facing/eyeline -> prop state -> main action/emotion -> dialogue/OS/system tone -> camera path/focus -> tail state.
- Do not use loose/meta shorthand in direct prompts: `继承`, `延续上一镜`, `空间保持`, `位置继承`, `物理座位不变`, `剪辑`, `切到`, `反打到`, `下一镜执行`, `脑海浮现`, `后期插入`, `声音语气：`, `表情：`, `动作：`, `情绪：`.
- No ambiguous pronouns for key action/speech/prop ownership. Name the actor.
- OS/system/OV/inner voice are post-production sound or side-safe text by default; visible people stay closed-mouth.
- Do not paste generic prohibitions, repeated acting theory, or production checklists into a direct prompt. Keep those in global locks, negative prompts, or optional production notes.

## Compact delivery rule

Every group always has `【出现人物】` once. Every child always has `【镜号】`, `【画面描述｜直接复制】`, `【表演与声音】`, and `【状态继承】`. Do not repeat the cast field on children.

Add `【空间与道具锁定】` only for multi-person topology or active prop transfer; `【镜头执行】` only for an actual move/focus shift; `【口型分窗】` only for multi-speaker or long/risky visible dialogue; and `【剪辑衔接】` only for a time/place change, flashback, action handoff, prop transfer, or an independent cutaway. Do not emit empty optional fields.

Add `【镜内状态转换】` only when one T2V card must visibly change a carry-over fact before its dialogue or reaction. It is a planning control, not a replacement for the direct prompt.

## Same-card state transition

Treat these as visual states when they change or must survive to the next card: body pose/facing/gaze; hand, prop owner, position, and contact; clothing/accessory/injury; door/window/light/UI; relation distance/barrier; speaking-mouth mode; and the visible result of an event.

For one continuous card, write the direct prompt in this order: `opening state -> one visible transition -> stable end state -> dialogue/reaction -> tail state`. State the same sequence in `【镜内状态转换】` when the card also has visible dialogue or a risky prop/body change. In that field, copy the exact natural-language end and tail sentences into `终态直投句` and `尾帧直投句`; both sentences must appear verbatim in `【画面描述｜直接复制】`. Do not let the old and new states coexist in wording.

Use one high-impact transition at most in a dialogue card. Finish it before the visible mouth starts speaking. Split when the card also contains prop transfer, character crossing, a second state change, or a non-static camera move. A small focus landing may accompany the transition only when it does not hide the action or move to another subject.

Examples:

- Phone call: `A右手手机贴右耳 -> A右拇指按下挂断，手机离开右耳 -> 手机停在A右手腰侧，耳边无手机 -> A转向B开口 -> 尾帧右手仍持手机在腰侧。`
- Prop transfer: `杯子在A右手 -> B右手握住杯身，A松手 -> 杯子稳定在B右手 -> B回应。` If either person also has long dialogue or the camera moves, split it.
- No prop flashing: `道具在A包内/口袋/桌面/右手 -> A的手进入容器或触碰桌面道具 -> 道具完整露出并停到可递交位置 -> B已经面向A且手可到达 -> B接触道具 -> A松手 -> 道具稳定在B手中/桌面B正前方`. If B is behind A, behind another person, side-behind, turned away, or out of reach, use a prior positioning child for B turning/stepping into a reachable face-to-face or side-by-side slot before the transfer. Do not write `A递给B` when their bodies are not yet physically arranged for it.
- Door: `门半开 -> A拉门至关闭并松手 -> 门保持关闭，A转向室内人物开口。`
- Posture: `A站在沙发旁 -> A坐到沙发边缘，双脚落地 -> A坐稳后再回答。`

Never use plot summaries such as `打完电话`, `递给B`, `A离开`, or `门关上` as the only instruction. Name who performs the visible transition, contact/release when relevant, and the final state that the next card inherits.

## Dialogue performance budget

For a dialogue card, allocate generation priority as `visible speaking mouth -> listener response -> camera`. This is a selection rule, not three simultaneous requirements.

- Short single-speaker line: one visible speaking mouth + one low-amplitude listener response; use a fixed frame. A simple camera move is allowed only when the listener stays closed-mouth and nearly still.
- Long single-speaker line (over 5s): choose one of two modes: fixed frame + one small listener response, or one slow push/focus landing + listener only breath/gaze hold. Do not combine long lip-sync, listener hand/body action, and camera movement.
- Speaker handoff or two visible speakers: divide into separate mouth windows, close the first mouth before the second begins, and keep the camera fixed. Put the listener's larger reaction in its own reaction card when it matters.
- If an original line is too long for a stable visible mouth window, split only at a source punctuation/semantic pause; preserve the original wording and order. If it still cannot fit, keep the line as post-production voice with all visible mouths closed.

Write `优先级：口型 > 听者反应 > 运镜` at the start of `【口型分窗】` whenever that field is used. If `【镜头执行】` also contains a move, state which lower-priority element is held still.

## Shot group mode

Use a shot group when one internal story beat needs two or more visible links to create its new audience recognition, or when it is overloaded for one Jimeng prompt. The story beat is an internal parent only: output it only as a compact group ID, not as a master-shot prompt, beat explanation, or duplicate card. The group contains its visible cast and child cards.

Trigger it when a single prompt must do three or more of these: lock space, release/grab/retrieve a prop, reveal phone/card/photo/text, visible dialogue, listener reaction, focus shift, character entry/exit, or emotional turn. Also trigger it when a meaningful line needs a prior physical cue or perception shift to earn its force.

Format: use a group ID with summed duration and a local child number, e.g. `#### S1-03｜镜头组总时长：8s`, then `【镜号】1`, `【镜号】2`, `【镜号】3`. Each child gets four default fields, one main generation task, and its own direct prompt. The next child begins by restating current visible facts; do not write `继承`. Each child must add a new visible fact, not restate the whole beat.

Choose only the roles the source earns; do not force all roles into every group:

- Cue/evidence child: an object, contact, body leak, or relationship change that gives pressure a visible source; normally 1-2.5s and no visible dialogue.
- Perception child: a gaze lift, a simple focus landing, a small push, or a listener's received reaction; normally 1-2.5s and no visible dialogue.
- Information-landing child: the original dialogue, decision, reveal, or changed relation that makes the beat explicit; use real audio duration plus 0.5-1s reaction margin, normally 2.5-6s.
- Relation-result child: return to the two-person or group arrangement only when distance, barrier, ownership, or apparent upper hand has visibly changed; normally 1.5-3s.

Example internal beat, never output: `皇后确认来者身份，表面平静被打破`.

输出子镜头：`A` 手压茶盏、茶水震荡；`B` 从茶盏上摇至双眼、完成锁定；`C` 审视并说出确认台词，留下下一镜要继承的手势/站位。三个子镜头共同完成主节拍，不要求任何一张单独解释完整剧情。

不要只为显得电影化而拆分。仅在拆分能降低提示词密度、改善道具可达性、避免听者僵硬或空间混乱，或让剧情转折按“线索 -> 感知 -> 落点”展开时拆分。

## Mandatory camera and duration contract

Every child direct prompt must contain these five natural-language facts: `景别`、`机位或角度`、`镜头静止或一条明确路径`、`人物身体关系/道具关系`、`本镜唯一落点`。Do not put them in a separate theory field.

- Static is allowed for a long speaking window, but write its framing task, such as `平视双人中景，相机在沈星雨左前方，保留江训的虚化肩线`。Never use `固定中近景` as a default phrase without camera side and relationship task.
- Choose only one camera job per child: establish relation, carry a speaking mouth, receive a reaction, reveal an object, or show a completed state change. A child does not need a move to be cinematic.
- Write body relationship before screen layout. Give each visible named person an anchor: `民警身体面向沈星雨，沈星雨身体面向民警，江训身体朝向柜台、头部偏向沈星雨` is valid; `民警在左、沈星雨在右` or `身体朝左/右` alone is insufficient. If a body and face point differently, state both. Camera side comes last and never substitutes for body orientation.
- Shot-size and angle changes reset orientation. When the next card is a dialogue, reaction, over-shoulder, close-up, or reverse angle after walking/turning/leaving/counter action, its opening prompt must restate who each visible person is fully facing. Default face-to-face dialogue to `A身体面向B，B身体面向A，二人相距...`; use `A身体仍面向出口/柜台，头部转向B` only when avoidance, refusal, blocked movement, or unfinished leaving is the intended visible meaning.
- Strict shot/reverse-shot pairs must stay paired: if shot N says `机位在A肩后，A前景肩线弱虚化，镜头对准B`, shot N+1 must say `机位在B肩后，B前景肩线弱虚化，镜头对准A`. Do not replace the reverse with `B右前方/侧前方` or another loose camera side. Re-state the same face-to-face body relation, distance/barrier, prop holder/position, and background anchor in both cards.
- If a line requires a character to face another person but the prior state has them side-on, behind, or facing a fixed object, split or start the card with: `A身体从...转向B，双脚停稳，A身体面向B后再开口`. Do not let a visible dialogue begin while only the head/eyes have turned.
- If a long speaking line is followed by an exit/turn, end the speaking child in the prior stable relation; use the next child for the turn/exit, then another child for the reply when needed.
- Estimate visible Chinese dialogue at roughly 5.5-6.5 characters per second, then add 0.5-1.0s tail margin. Do not place two visible speakers in the same child unless both lines are short and the handoff itself is the only task.
- Do not use placeholders such as `当前主角` or alternatives such as `A或B`. Name the actual visible subject and one fixed orientation anchor. Do not add off-frame cast merely to satisfy a group-level cast list.
- A hand/object insert names only the visible hands, their owners, the reachable surface, and the prop state. Use `手部特写` or `斜俯拍近景`; never pair `只拍手/卡/台面` with `中景/全景`.

### Camera hierarchy inside one scene

- Open a new location or changed group relation with one relation frame: wide/medium-wide, fixed anchors, every visible person's body-facing anchor, and the camera side.
- Use a medium close-up or over-shoulder frame for a normal reply; use a close-up or a short push only when a face, breath, gaze, or hand detail changes the meaning.
- Use one clearly named move only when the beat changes: `从A的手推近到A的脸`、`从道具上摇到说话者的眼睛`、`沿人物离开方向侧跟两步`。State starting frame, path, and landing frame. Do not write a generic `推拉摇` or combine two paths.
- After an insert, close-up, or two speaker frames, return to a relation frame when distance, facing, barrier, or ownership changes. Do not repeat fixed medium close-ups merely because dialogue continues.

## Director-to-Jimeng translation

Write director intent as visible physical results, not abstract mood.

- Pressure: relation view first, then push/focus to eyes, whole hand, fist, or prop; keep the barrier and body side fixed.
- Awkward comedy: relationship frame + 0.3-0.6s closed-mouth pause + delayed listener micro-reactions.
- Isolation/s疏离: pull back to reveal empty seat, table distance, door gap, or road space.
- Secret/realization: close enough face shot or small push to eyes; include trigger and breath/shoulder/hand change.
- Glamour/public attention: low-risk 15-30° small arc or controlled reveal, never during prop exchange or long lip-sync.
- Flashback/memory: split independent clips; real trigger holds 0.5-0.8s, inserted memory opens with 0.5-1.0s stable anchor; white flash/sound bridge only in QA/sound fields.

Borrow only the useful part of human storyboard examples: beat rhythm and emotional intent. Do not copy vague phrases like `氛围感拉满`, `暗流涌动`, `虚实切换`, `快速闪切`, `画面拉回`, or `定格镜头` into direct prompts; translate them into physical blocking, camera path, focus, and visible performance.

## Dialogue framing rule

Pick the shot size from the visible task, not from a fixed alternating close-up pattern:

- Relationship setup: use a two-person medium shot or over-shoulder medium shot. Name the fixed object between them, left/right or near/far order, body distance, and whether either person moves closer, sits at an edge, or turns away.
- Normal reply, lie, or relaxed response: use a medium close-up that keeps shoulders, one active hand, and nearby space visible. A relaxed person can lean against a sofa arm, sit back, or leave empty space beside the body; do not call this `呼吸感`.
- Pressure, anxiety, secret exposure, or a decision: use a close-up or a slow push from medium close-up to close-up. Name one or two readable changes only, such as a held breath, tightened jaw, gaze fixed on an offscreen door, or lips pausing before speech.
- Evidence or emotional outlet: use an insert or focus landing on a hand releasing a sleeve, a phone turning face-down, a cup held without drinking, a door handle, or another story prop. Return to the face or relation shot after the insert.
- Isolation, avoidance, or dialogue ending: use a medium-wide or wide shot. Name the empty seat, door gap, table distance, frame edge, or departure direction; do not ask a wide shot to show eye detail.

After two or three spoken turns, return to a relation shot whenever body distance, a barrier, prop ownership, or the apparent upper hand has changed. State the visible change rather than `权力反转`: for example, `沈星雨从门框边走到沙发前，沈星洲停在原地，二人之间隔着茶几`.

### Direct-prompt sentence patterns

Use only the pattern that fits the beat; do not concatenate all of them.

- `沙发前的茶几横在两人之间，A坐在画面右侧沙发边缘，B站在画面左侧靠近门框；镜头保持双人中景，A说话时B不动嘴，只把视线从A的脸移到A手中的手机。`
- `镜头从A的中近景缓慢推到近景，A说到关键字前停半秒，呼吸变浅，下颌收紧，视线越过镜头看向门口；A开口，画外B保持安静。`
- `A坐在沙发深处，肩背放松，右手搭在扶手上，身旁留出一人宽的空位；中景保持不动，A抬眼回答，语速平稳。`
- `特写A的右手把手机屏幕扣在茶几上，手指离开手机后停半秒；焦点从手机移到A抬起的脸，A再说下一句。`

## Interaction rhythm and emotional cutaways

Do not cut dialogue in a mechanical A/B pattern. For a sustained exchange, use only the changes the scene earns: relation shot -> speaker -> listener reaction -> changed relation shot. Add an insert only when the omitted face/action makes the current line more legible.

### Cutaway stability rule

Treat a complete object/empty-space cutaway as an independent T2V card by default. State its `独立生成；后期接入上一镜声音` handoff in `【剪辑衔接】`. In its direct prompt, show only the stable result, current location/light, and source-supported object/space state. In `【表演与声音】`, place dialogue, OS, breathing, or sound as post-production; all visible mouths remain closed.

Allow an insert inside the same T2V card only as a continuous focus landing: the opening frame already contains the prop, the camera/focus moves once to that prop, and the clip ends there. It must keep the same location/light, have no hard cut, visible speaking mouth, prop/contact transfer, character crossing, offscreen action that changes a state, or return to another face. Do not ask Jimeng to hard-cut from a face to an empty room and back within one generated clip.

Require a separate card for a full empty-space view, door gap/hallway, empty seat, water ripple after impact, object owner change, offscreen physical action, a dialogue handoff after the insert, or UI whose exact text matters. Restate the object/door/person state in the following relation or character card; do not rely on the model to preserve an inferred unseen action.

- Safe same-clip insert: `A右手已把手机扣在茶几上；镜头从A的手停住半秒，焦点缓慢落到手机边缘，手机保持屏幕朝下，镜头停在手机上结束。` 不在这条内再拍A说话或切回人物。
- Independent object cutaway: `镜头不拍人物，茶几上的手机保持A刚扣下后的屏幕朝下状态，客厅灯光和桌面位置不变。` 在 `【剪辑衔接】` 写 `独立生成；后期接入A停住的呼吸与B的最后半句。`
- Independent empty-space cutaway: `镜头固定在半掩的客厅门缝与门外走廊灯光，门保持未关；客厅内无人入画。` 在 `【剪辑衔接】` 写 `独立生成；后期接入A停住脚步与B从客厅传来的声音。`
- Listener reaction: put the reaction between the line and the reply. Example: `B不立刻回答，近景里B的手从杯壁离开，视线落到桌面两秒后才抬眼开口。`
- Layered relation shot: use one foreground obstruction, one speaking subject, and one relationship anchor in the background. Example: `前景虚化的门框遮住画面左侧，A在中景靠近茶几说话，背景右侧的B停在沙发边不动；两人之间的茶几始终可见。`
- Omitted action: use an independent result card when the unseen action changes a state. Example: `特写门把停在回弹后的稳定位置，门仍半掩；走廊灯光不变。` 在声音字段补 `A松开门把后没有离开，后期加入A压低的呼吸声。`

For a comedic reversal, place a 0.3-0.6s reaction gap before the counter-line, then use a small object, system UI, or listener reaction as the punchline. Do not ask every character, sound, and UI element to move at once.

## Performance rule

单独镜头使用：触发 -> 眼神/眉眼/嘴部/呼吸 -> 手/肩/身体/道具 -> 语速/音量/尾音。子镜头组则把这条链分配到全组，不在每个子镜头重复。

Build the group arc as `pressure leak -> perception shift -> controlled expression/line -> emotional residue`, using only the source-supported stages. A pressure leak can be a prop contact, interrupted action, posture shift, or held breath; perception shift is one readable eye/head/focus change; controlled expression/line is the speaker's chosen mask or release; residue is the final gaze, hand, distance, or prop state. Each child adds one stage, not a full duplicate performance sheet.

Non-speaking visible important characters cannot only be `闭口`: add one low-amplitude reaction caused by the speaker/action, such as gaze follow, slow blink, slight brow/mouth shift, shoulder settling, whole hand touching/leaving a prop. Keep listener motion smaller than speaker motion.

Select micro-actions by emotion function, not by fixed character type. Do not force a queen to tap a cup, a heroine to blink, or a male lead to clench fists unless the source/personality supports it. If the chosen action conflicts with the scene, pick a prop/body action already present in the source.

Write a performance chain only when it changes the image: trigger -> one or two visible face/breath changes -> one body/prop response -> voice result. Vary the chosen detail by person and beat. In a child-shot group, do not repeat a stock eye pause, brow movement, fingertip leak, or generic “紧张” description: later children must advance, contradict, release, or conceal the earlier leak.

## UI and sound rule

For system text, phone screens, payment alerts, or captions, reserve a side-safe zone and keep it away from faces, lips, and active hands. Dense or exact text is post-production by default; the direct prompt should describe only the visible UI presence and character reaction.

When audio layers overlap, prioritize: visible dialogue > key sound effect > OS/system > ambience/music. Write a pause or reaction gap before a comedic reversal instead of making every layer peak at once.

## Continuity rule

State inheritance is the next shot's first frame. If a person sits, leaves, enters, turns, takes, places, wears, hands over, or swaps an item, the next direct prompt starts by restating that visible fact in natural language.

Use a tail-change check before writing shot N+1:

`shot N tail changed what? -> does shot N+1 opening direct prompt restate it? -> can the named character physically reach/move the prop?`

For a same-card transition, run the shorter check before dialogue:

`opening state named? -> one visible change named? -> stable end state named? -> does visible dialogue start only after that end state? -> does the tail repeat the state the next card needs?`

## High-risk split/downgrade rule

If one shot combines three or more of these, split or simplify: multi-person blocking, prop/contact transfer, visible lip-sync, camera movement, character crossing, crowd/cars/doors, flashback/world change.

Do not solve overload by writing a longer prompt.

For clothing or hand-prop transfer, use a visible three-stage chain when the contact matters: current owner releases or presents the item -> receiver contact/placement -> receiver's stable final state. Put each stage in a separate subshot when it also contains dialogue, camera movement, or an emotional turn.
