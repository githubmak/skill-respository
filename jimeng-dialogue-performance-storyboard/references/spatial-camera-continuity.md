# Spatial, Camera, and Continuity Rules

## Spatial locking

Space locking must include relational blocking, not only screen sides.

Use this priority order for multi-character or prop-heavy shots:

1. Static scene anchors: 1-2 unmoving references that frame perspective, such as `同一张长桌横贯画面下半区，桌沿与画框平行，远处窗口固定在背景中线`.
2. Physical slots: assign stable story-world slots before screen zones, such as `桌内侧左座`, `桌内侧右邻座`, `桌对面左站位`, `桌对面右座`, `门内侧`, `车外侧`, `床左沿`.
3. Screen zones: assign characters to `画面左1/3`, `画面中区`, `画面右后1/4`, plus foreground/midground/background and visible share.
4. Relational blocking: state who is across from, beside, behind, or diagonally facing whom, including distance and barrier/contact object.
5. Facing and eyeline: state `朝左/朝右/朝左前/背向镜头`, and the eyeline target.
6. Prop lock: active props get independent positions and owners; props do not automatically follow the nearest person unless stated.

Write at least:

- static scene anchor or fixed background anchor;
- physical slot or movement lane when available;
- people count;
- coordinate basis: `画面左/中/右` for screen geography, or explicit `在A的右侧/桌对面/身后` for character-relative geography;
- left/center/right screen zone and approximate share when useful;
- foreground/midground/background;
- front/back relation;
- facing, back-facing, or diagonal-facing relation;
- eyeline target;
- approximate distance;
- barrier/contact object such as table, door, car, counter, bike, bed, wall;
- active prop position and owner;
- scene anchor.

Use phrases like:

- `隔餐桌正对`
- `右后侧半身距离`
- `左前方背向镜头`
- `车门夹在二人之间`
- `手机在A右手靠近B胸前`

Avoid only `A左、B右`.

Avoid ambiguous shorthand such as `右侧近景`, `左前景朝右`, or `空间延续` unless the sentence states whether this is screen geography or character-relative geography.

Line-art-grade seated/table version: `同一张长桌横贯画面下半区，桌沿与画框平行；A坐桌内侧左座、画面中右，B坐同一条桌边的右邻座、画面右侧，二人肩线同排相距半身；C在桌对面左站位；本镜拍B近景，所以A只作为画面左前景弱虚化肩线。`

For line-art or layout prompts, include:

- fixed object shape and frame share, such as `长桌横贯画面下半区，占画面45%`;
- physical slots, such as `桌内侧左座 / 同桌边右邻座 / 桌对面左站位`;
- same-side or opposite-side relation, such as `二人肩线同排，不隔桌`;
- screen zones, such as `A画面中右，B画面右侧`;
- facing and eyeline, such as `B身体微转朝A`;
- empty slots and props, such as `桌对面左站位空出，道具X停在B正前方`.

## Scene state table and shot changes

Build one observable state table for every location before writing individual shots. Its row must contain:

- two or three fixed objects and their relative positions;
- each character's physical slot, screen left/centre/right zone, depth, body direction, eye-line, and movement lane;
- empty areas that must remain empty;
- each active prop's owner, hand/table/contact point, and current state;
- the visible light source and the facts allowed to change in this scene.

Treat this row as the scene's only source of truth. Each shot must declare its opening facts in `【空间锁定】`, then write only the changed facts to `【状态继承】`. Before the next shot, compare the new opening with the prior tail and the scene table. A camera change may alter what occupies foreground or background, but cannot silently change a seat, facing direction, hand, prop owner, or walking lane.

Use natural, drawable descriptions only: `摄影机靠近窗边拍摄，画面左前景保留A的右肩，B在画面右侧看向A，文件柜留在B身后右侧`. Do not use abstract film-school position terms.

## Spatial quantification

- Avoid vague `前景保留肩线 / 背景低幅人流`.
- Quantify area and blur:
  - `前景：画面右侧1/4，B左肩弱虚化遮挡，占画面15%`
  - `中景：A清晰中近景，占画面60%，焦点在双眼`
  - `背景：橱窗与远处3-5名模糊行人，占画面25%，重度虚化`
- A character cannot be both foreground blur and midground main performer in the same shot.
- Background extras need count, zone, direction, blur, and focus behavior:
  `背景远处3-5名模糊行人沿步行街同向慢走，不正对镜头、不抢焦、不做可读对白。`

## High-risk anti-weak constraints

Replace weak shorthand with concrete contracts:

- Static anchors: never start a complex table/room/crowd shot with only people. Begin with 1-2 fixed objects that do not move, such as table edge, doorframe, window, counter, sofa, bed, wall lamp, hallway line, or car door.
- Multi-character blocking: never write only `A左、B右` or `三人不换位`. Write `画面左1/3为A`, `A站在B桌对面约1米`, `C坐在B的右后侧半身距离斜看A`, and name the barrier/contact object.
- Coordinate basis: never write bare `左侧/右侧/前面/后面`. Write `画面左侧`, `A的右侧`, `桌对面`, `镜头前景`, or `背景窗口前` so the model knows the reference frame.
- Screen layer is not relationship. `前景/中景/背景` only describes camera depth; it must not change story blocking. If two characters are seated beside each other, do not turn one into `桌对面` just because they appear in foreground. Write `同侧邻座/右侧半身距离/肩线前景遮挡` plus the true table-side relation.
- Canonical blocking must stay canonical. If characters do not physically move between shots, reuse the same physical-slot phrase every time, such as `A桌内侧左座，B同一条桌边右邻座，二人肩线同排相距半身`; do not alternate between `右侧`, `右后`, `左邻位`, or `斜对` unless the character actually changes seat or body angle.
- Separate camera side from physical slot. Write the camera-side change without continuity shorthand: `本镜从B侧拍近景，A只作为画面左前景肩线；A坐桌内侧左座，B坐同桌边右邻座`. Never let camera-side wording imply a new seat.
- Use empty-slot and lane locks when helpful: `角色C离开后桌对面左站位空出`, `左后出口为离场通道`, `新道具仍在桌对面右座正前方`.
- Prop contact/transfer: never write only `拿起/递给/放下/接住`. Write start anchor, hand, contact point, path, release/new holder, and tail state.
- Prop lock: never let props inherit by implication. Write `道具X固定在角色B面前桌面中线偏右，距离桌沿约一掌，不跟随角色C移动`.
- Walking/entry/exit: never write only `走来/离开/入画`. Write screen direction, depth path, displacement, speed, foot contact, and tail frame.
- Camera movement: never write only `推近/拉远/环绕/跟拍/两人轮流被拍`. Write start frame, trigger, physical path, distance/angle, focus target, stop point, and preserved spatial anchor.
- Crowd/background: do not write `无清晰口型/无清晰人脸/无口型`. Write `背景人物在远处虚化区低幅活动，不正对镜头、不抢焦、不做可读对白`; if crowd dialogue exists, send it to post-production sound.
- Non-speaking important characters: do not write only `闭口`. Write `闭口 + delayed micro-reaction`.
- Clothing/body-state continuity: do not write only `衣服不变/状态不重置`. Write the visible locked item and body state.
- Position carryover: do not write only `延续上一镜/空间保持/继承`. Restate the current visible facts: screen side, physical slot, front/back layer, facing/eyeline, distance/barrier, prop owner, and camera landing.
- Next-shot first frame: treat `状态继承` as the next shot's fixed first frame. The next direct prompt must restate essential tail facts before new action begins.

## Prop and tail-state

- Every active prop needs a starting anchor before it moves: holder, hand/side, pocket/bag/table position, contact point.
- Prop transfer must show start position, contact, movement path, release/new holder, final untouched state, and the next shot's first-frame visible restatement. Do not rely on the word `继承` to carry prop ownership or position.
- Two-prop exchange is higher risk than one-prop transfer. Never compress it into `A把X给B、把Y拿回` or two simultaneous hand verbs. Write it as a staged physical sequence: `X起点 + Y起点 -> 角色A用哪只手接触X哪一边 -> X沿什么路径到角色B正前方/手中 -> 角色A松手 -> 角色A再接触Y -> Y沿什么路径回到角色A正前方/手中 -> 角色A松手 -> 尾帧X/Y各自停在新位置，双手离开`. If the prop must not return, state `松手后不再拿回`.
- Tail-state must be physical, not only emotional.

Weak: `角色B兴奋`

Strong: `角色B右手道具停在胸前，嘴角轻上扬，视线落到道具上，身体仍靠近角色A`

## Cross-scene handoff and continuity

When adjacent editorial shots change time, location, age, wardrobe, or world state, do not try to inherit physical geography across the boundary. Instead, lock two separate states:

1. **Outgoing state:** the trigger/return clip holds a concrete pose, eyeline, and prop state for 0.5-0.8s at its tail. This is the editable outgoing handle.
2. **Incoming state:** the inserted clip begins with its own static scene anchor, locked character positions, and a 0.5-1.0s stable hold before dialogue or decisive action. This is the editable incoming handle.
3. **Editorial bridge:** white flash, dissolve, blur, speed ramp, and J/L audio are post-production operations recorded in QA/sound fields; they are not physical actions for the image model to generate.

For a flashback trigger motivated by an object, show the eye-line landing on that exact object before the outgoing hold. For a flashback return, establish the present-day prop and pose before OS/dialogue begins. This preserves causal continuity while avoiding impossible cross-location morphs.

## Ordinary cut handoff

Use `【剪辑衔接】` for every neighbouring pair, including shots in the same place:

- **Same moment, new view:** the outgoing clip holds 0.3-0.6s on a readable pose, prop contact, or movement phase. The incoming clip starts from the same facts before adding new motion. Keep shared ambience continuous.
- **Action continues:** record the direction, body phase, prop contact, camera speed, and exit/entry side. Do not restart the action from its preparation pose.
- **Reaction or object cut:** the outgoing action lands first; the incoming reaction begins after the trigger. Repeat the exact prop state and fixed objects that make the causal connection readable.
- **Changed place/time:** use the dedicated independent handoff rule. Do not attempt to make a person, room, or camera position transform inside one generated clip.

If the next clip will be generated from a reference image, label that image's responsibility in the handoff record: outgoing last usable frame, incoming first composition, character identity, or movement reference. This makes manual compositing and one-pass image-to-video generation traceable.

## Camera rules

- Do not use abstract film-school position jargon as final prompt language. State visible results instead: left/right, foreground/background, front/back relation, facing direction, eye-line, distance/barrier object, camera-side scene anchor, and visible background anchor.
- Fixed camera is for lip-sync, prop contact, crowd/person-count locking, vehicle/door precision, or deliberate emotional stillness.
- Close-up is for line landing, concealed emotion leak, prop/contact reveal, or power shift. Specify crop and focus.
- Push in for pressure, exposure, relationship tightening, or a line landing.
- Pull out for abandonment, isolation, failed connection, absurdity, or relation break.
- Follow for movement; do not overtake or orbit.
- Turn the camera or shift focus only to reveal a subject, eye-line target, or prop ownership.
- Avoid vague `连续变景别`: if one generated clip, translate to a physical path; if hard cuts are needed, split into separate shots.

Camera language pattern:

`[起幅景别/机位高度/镜头距离] + [固定物/物理槽位/屏幕位置/前后层级/朝向/视线/间隔物或接触物/道具] + [0.0-X秒先稳定] + [触发台词/动作] + [摄影机路径/方向/位移/角度/速度] + [焦点对象/是否转焦] + [落幅景别/人物尾帧可见事实]`

## 双人肩后构图

In `【画面描述｜直接复制】`, do not write `剪辑`, `切到`, `反打到`, or `下一镜执行`.

Write each two-person view as a visible foreground-shoulder composition:

- `摄影机在A肩后，A前景肩线弱虚化占画面1/5，镜头对准B，B清晰；A与B隔桌约1米，B朝A说/听/反应。`
- Paired shot: `摄影机在B肩后，B前景肩线弱虚化占画面1/5，镜头对准A，A清晰；A与B隔同一桌约1米。`

Pairs must preserve:

- same screen geography;
- front/back relation;
- barrier/contact object;
- eyeline direction;
- shared background anchor;
- shoulder-line owner and screen share;
- listener reaction timing.

## Camera trigger matrix

- Establishing/wide: new location, new group relation, changed blocking, or object geography.
- Medium/two-shot: relationship negotiation, lie/cover-up, physical distance, or shared reaction.
- Close-up: line landing, hidden emotion leak, tiny face/finger movement, prop/contact reveal.
- Insert/cutaway: phone, ring, contract, wound, door handle, clothing, money, text, ownership/status change.
- Push-in: pressure rises, secret exposed, relationship tightens, OS realization sharpens.
- Pull-out: isolation, failed connection, comedic awkwardness, power loss, emotional emptiness.
- Side follow/tracking: walk, escape, chase, escort, crossing a space.
- Turn the camera: reveal an eye-line target, entrance, height difference, sign, door, or held prop.
- Change focus once: shift attention between face and prop/listener/background clue; only one focus change per shot.
- Foreground-shoulder pair: dialogue exchange, received information, listener reaction, power shift, or emotional answer.
- Montage: time compression, repeated attempts, memory fragments, systemic information, comedic rapid contrast; treat as separate short shots.
- Orbit/arc: relationship reversal, dizziness, glamorous reveal, public pressure, surreal dislocation; low-risk shots only, 15-45 degrees.
- Low-amplitude hand-held feel: panic, danger, drunkenness, chase, or a view as if seen by the character; low amplitude only.
- Static hold: lie being held, shock freeze, emotional restraint, precision lip-sync, high-risk continuity.
