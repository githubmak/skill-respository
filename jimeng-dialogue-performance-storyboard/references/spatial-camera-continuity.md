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

Never use ambiguous shorthand such as `右侧近景`, `左前景朝右`, or `空间延续` as the whole spatial lock. If a screen layer is needed, pair it with the full physical topology: same-side/opposite-side group, group-internal order, facing, distance, barrier/contact object, and prop position.

Line-art-grade seated/table version: `同一张长桌横贯画面下半区，桌沿与画框平行；A和B是桌内侧同排双人组；以二人坐在桌内侧、面朝餐桌对面的身体左右为基准，A在B左手边，B在A右手边；二人椅背在同一条平行画框的水平深度线、肩线平齐、到镜头距离一致，相距半身，桌沿在二人身前，不隔桌、不面对面、不一前一后；C在餐桌对面，与双人组隔桌，不插入A和B之间；本镜从B侧拍近景，A只作为组内同排前景肩线弱虚化。`

For line-art or layout prompts, include:

- fixed object shape and frame share, such as `长桌横贯画面下半区，占画面45%`;
- physical slots and topology groups with coordinate basis, such as `A和B为桌内侧同排双人组 / 以二人面朝餐桌对面的身体左右为基准 / A在B左手边 / B在A右手边 / C桌对面左站位`;
- same-side or opposite-side relation, such as `二人肩线并排，桌沿在二人身前，不隔桌、不面对面；C与双人组隔桌`;
- same-depth relation for front-facing same-side seats, such as `二人椅背在同一条平行画框的水平深度线、到镜头距离一致，不一前一后`;
- near/far relation for oblique same-side seats, such as `斜切机位从A这一端拍摄，A是组内近端，B是组内远端；二人仍同侧邻座，不隔桌、不面对面、不换位`;
- screen zones after topology, such as `双人组位于画面中右区域，B为清晰主体，A只占组内前景肩线`;
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
- Space locks must be line-art clear. Each risky shot must state static anchor -> physical topology -> screen zone -> front/back depth -> facing/eyeline -> distance/barrier/contact object -> active prop owner/state. If any of these are implied rather than stated, rewrite the prompt.
- Multi-character blocking: never write only `A左、B右` or `三人不换位`. Write `画面左1/3为A`, `A站在B桌对面约1米`, `C坐在B的右后侧半身距离斜看A`, and name the barrier/contact object.
- Coordinate basis: never write bare `左侧/右侧/前面/后面`. Write `画面左侧`, `A的右侧`, `桌对面`, `镜头前景`, or `背景窗口前` so the model knows the reference frame.
- Screen layer is not relationship. `前景/中景/背景` only describes camera depth; it must not change story blocking. If two characters are seated beside each other, do not turn one into `桌对面` just because they appear in foreground. Write `同侧邻座/右侧半身距离/肩线前景遮挡` plus the true table-side relation.
- Same-row table characters must be declared as a **same-side group** before any third-person opposite-side blocking. Prefer group-internal positions with an explicit coordinate basis and same-depth/near-far locks over global left/right extremes: `A和B是桌内侧同排双人组；以二人坐在桌内侧、面朝餐桌对面的身体左右为基准，A在B左手边，B在A右手边；二人椅背在同一条平行画框的水平深度线、肩线平齐、到镜头距离一致，相距半身，桌沿在二人身前，不隔桌、不面对面、不一前一后`. If character C stands across the table, add `C在餐桌对面，与双人组隔桌，不插入A和B之间`. Do not write only `A画面左侧、B画面右侧`; that can make the model separate them or turn them face-to-face.
- Canonical blocking must stay canonical. If characters do not physically move between shots, reuse the same physical-topology phrase every time, such as `A和B是桌内侧同排双人组，以二人面朝隔物对面的身体左右为基准，A在B左手边、B在A右手边，二人椅背同一水平深度线、到镜头距离一致、不一前一后`; do not alternate between `右侧`, `右后`, `左邻位`, or `斜对` unless the character actually changes seat or body angle.
- Separate camera side from physical slot. Write the camera-side change without continuity shorthand: `本镜从B侧拍近景，B清晰，A只作为组内同排前景肩线弱虚化；A和B仍是同侧邻座，不隔桌、不面对面`. Never let camera-side wording imply a new seat.
- Use empty-slot and lane locks when helpful: `角色C离开后桌对面左站位空出`, `左后出口为离场通道`, `新道具仍在桌对面右座正前方`.
- Prop contact/transfer: never write only `拿起/递给/放下/接住`. Write start anchor, hand, contact point, path, release/new holder, and tail state.
- Prop reachability: before writing any character moving a prop, confirm the prop is visibly within that character's current hand reach at the shot opening. If the prop is on another character's side, in another slot, or already transferred away, do not let the character move it; write a reaction to the prop instead, or first stage a believable reach path.
- Prop lock: never let props inherit by implication. Write `道具X固定在角色B面前桌面中线偏右，距离桌沿约一掌，不跟随角色C移动`.
- Prop/person relocation carryover is mandatory. If a shot ends with a person seated, standing, leaving, entering, taking, placing, wearing, handing over, or swapping an item, the next shot's direct prompt must start by restating that new physical state. `上一镜/继承/仍然` without visible facts is invalid.
- Barrier language: verbs like `越过桌面`, `探过柜台`, or `压到车窗里` imply body movement across the barrier. If the body must stay put, write `站直/坐直留在隔物本侧`, `肩背不前压`, and only allow `视线越过桌沿/柜台边缘/车窗线`. If the character must bend or lean, specify body angle, foot anchor, hand support/contact point, whether the torso crosses the barrier line, and final pose; never let `越过` carry all of that by itself.
- Walking/entry/exit: never write only `走来/离开/入画`. Write screen direction, depth path, displacement, speed, foot contact, and tail frame.
- Camera movement: never write only `推近/拉远/环绕/跟拍/两人轮流被拍`. Write start frame, trigger, physical path, distance/angle, focus target, stop point, and preserved spatial anchor.
- Continuous camera movement is allowed and often useful, but must be described as one physical path with time anchors: opening hold, start time, end time, path, distance/angle, focus transition, landing frame, and which spatial locks remain unchanged. Do not use vague `连续运镜` without this contract.
- Crowd/background: do not write `无清晰口型/无清晰人脸/无口型`. Write `背景人物在远处虚化区低幅活动，不正对镜头、不抢焦、不做可读对白`; if crowd dialogue exists, send it to post-production sound.
- Non-speaking important characters: do not write only `闭口`. Write `闭口 + delayed micro-reaction`.
- Multi-person interaction must feel alive. During one speaker's line, visible listeners get low-amplitude simultaneous interaction: gaze follows speaker, blink, subtle brow/mouth/shoulder change, hand on table/prop, or small posture adjustment. The reaction must be in `【画面描述｜直接复制】`, not only in QA.
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
- Decide shot size by **occupancy and readable action**, not by habit. A safe planning rule: wide/广中景 establishes place and movement lanes; medium/中景 carries 2-3 bodies and gross actions; medium close/中近景 carries one speaker plus one listener shoulder/reaction; close-up/近景 or insert carries eye/mouth/hand/prop micro-actions. If the requested acting detail would occupy less than roughly 15-20% of frame, the camera must push/focus closer or the action must be enlarged.
- Avoid both extremes: do not leave micro-actions inside a distant relation frame, and do not fragment one continuous emotional beat into many isolated inserts. When the relationship must remain readable, use a compound shot: `0.0-0.6秒关系中景锁位；0.6-X秒沿视线/手臂/桌面轻推0.2-0.4米或转焦一次；X-尾秒落到手部/眼神/道具近景并保留原人物位置`.
- Shot size must match the number and body levels of visible characters. A medium close shot can safely carry one main face plus one foreground shoulder or blur, but not a full three-person relationship with one standing and two seated characters. For `one standing + two seated + table/props`, use `横向中景`, `三人桌边中景`, or split into a relation-establishing medium shot plus a close-up/foreground-shoulder reaction shot.
- Micro-actions need enough pixel share. In a three-person medium table shot, use readable actions like `整只手离开筷子旁`, `肩背后缩`, or `手掌退到桌沿内侧`; do not rely on `指尖从餐盘旁收回到膝上`, because the table may hide the end position. Use a hand/prop close-up if the fingertip action is plot-critical.
- Medium-to-close is valid for readable micro-action when the opening must first lock space. Pattern: `前0.5-0.8秒三人/双人中景锁静物锚点和槽位；随后摄影机沿桌面/手臂方向直线推近0.2-0.4米到手部或道具近景；原压迫角色保留在边缘弱虚化，空间关系不重排`. Use only one push or one focus change unless split.
- If a shot contains `one standing character + two seated same-side characters + table props + silent pressure reaction`, do not rely on a plain medium shot for fingertip/fist/plate beats. Use one of two safe forms: (1) relation shot first, then straight tabletop push to the relevant hand/plate; (2) oblique medium shot first, then small push or single focus change to the standing character's face and visible whole hand/fist. The direct prompt must state that the standing character remains across the barrier and does not insert between the seated pair.
- When the dramatic beat is a silent reactor rather than the speaker, the camera may start on the speaker for lip-sync but must land on the reactor after the line: write the exact line window, the mouth close, then `摄影机沿桌沿/人物视线小幅移动或推近到反应者的眼神/整只手/肩背`, with the original speaker kept as edge/foreground/weak blur. Do not ask a medium shot to show a hidden fingertip or below-table hand.
- Default camera design is moderately cinematic, not mostly static. Use fixed camera only for high-risk moments: precise lip-sync, prop exchange/contact, crowd/person-count locking, vehicle/door precision, or deliberate emotional stillness.
- Vary camera grammar when safe: establishing geography, medium relation views, foreground-shoulder dialogue views, controlled push/pull for emotional turns, insert/turn/focus for prop reveals, and side-follow for movement.
- Camera movement cannot change story blocking. Before any push, pull, turn, follow, arc, or focus change, restate fixed objects, physical slots, screen zones, facing, barrier object, and active prop positions; after movement, state the landing frame and tail positions.
- Hold the opening composition still for 0.3-0.8s before movement so identity, slots, and props lock first.
- Close-up is for line landing, concealed emotion leak, prop/contact reveal, or power shift. Specify crop and focus; keep other important characters as shoulder/edge/blur only if their physical slots remain clear.
- Push in for pressure, exposure, relationship tightening, OS realization, or a line landing. Keep it straight and small by default: 0.2-0.5m, one subject, fixed background anchor.
- Pull out for abandonment, isolation, failed connection, absurdity, or relation break. Keep the same table/door/road anchor visible while emotional distance grows.
- Follow for movement; write the lane and speed. Do not overtake, circle, cross in front of the character, or let the camera make a walking character switch sides.
- Turn the camera or shift focus only to reveal a subject, eye-line target, or prop ownership. Use one camera turn or one focus change per shot unless the shot is split.
- Small arc/orbit is allowed only for low-risk emotional reversal or glamorous/public-pressure reveal: 15-30 degrees by default, never during prop exchange, dense crowd, or visible long lip-sync; preserve the same fixed background anchor.
- Avoid vague `连续变景别`: if one generated clip, translate to a physical path; if hard cuts are needed, split into separate shots.

Camera language pattern:

`[起幅景别/机位高度/镜头距离] + [固定物/物理槽位/屏幕位置/前后层级/朝向/视线/间隔物或接触物/道具] + [0.0-X秒先稳定] + [触发台词/动作] + [摄影机路径/方向/位移/角度/速度] + [焦点对象/是否转焦] + [落幅景别/人物尾帧可见事实]`

Safe cinematic movement patterns:

- Push-in: `前0.5秒固定餐桌/门框/车窗锚点，A在画面右侧固定槽位；听见关键词后，摄影机沿直线推近0.3米到A近景，背景锚点仍在同一侧，B只保留前景肩线，尾帧A眼神停住。`
- Medium-to-hand close-up: `前0.8秒固定长桌和人物槽位；随后摄影机沿桌面直线推近0.25米到A正前方道具与右手近景，B留在边缘弱虚化，A整只手离开道具并退到桌沿内侧。`
- Pull-out: `A说完后闭口，摄影机沿原方向后退0.4米，露出A与B之间的桌面/门框距离，二人座位不动，尾帧保留空位或隔物。`
- Side-follow: `摄影机胸高沿人物行走同侧平行跟拍0.8米，不超过人物；人物从画面右向左小步移动，脚掌贴地，背景店招/门框从右向左滑过。`
- Camera turn: `摄影机从A脸小幅左摇20度到A视线目标B，A保持画面右前肩线，B在画面左侧入清晰焦点，二人中间隔桌/门/车门不变。`
- Focus change: `前1秒焦点在A眼睛，A看向手中道具；1.2秒焦点用0.3秒从A眼睛转到道具边缘，之后保持在道具，不再乱焦。`
- Foreground-shoulder dialogue: `摄影机在A肩后，A肩线弱虚化占画面1/5，B清晰说话；A和B隔桌/门/半身距离，B说完后A闭口微反应。`
- Low-risk arc: `固定桌沿/车门为锚点，摄影机围绕A小幅弧移20度，A始终在同一物理槽位，B只从背景边缘变为侧面弱虚化，不交换左右。`
- Oblique table relation shot: `摄影机在餐桌对面偏A这一端约25-35度斜向拍过桌面，C三分之二侧脸清晰；A和B作为同侧双人组，A是组内近端，B是组内远端，二人仍同侧邻座、不隔桌、不面对面、不换位；镜头不沿长桌纵深方向拍成左右分裂。`
- Relation-to-reaction compound shot: `前0.6秒中景锁住A、B、隔物和背景锚点；B说完或关键动作落下后，摄影机沿A视线直线推近0.3米到A近景，B只留边缘弱虚化；尾帧A眼神/肩线/整只手反应清楚，二人位置不重排。`
- Relation-to-prop compound shot: `前0.6秒中景锁住人物和道具起点；随后摄影机沿桌面或手臂方向推近0.25米到道具/手部近景，焦点只转一次；尾帧道具最终位置和相关人物边缘位置同时可读。`

Unsafe movement defaults:

- Do not use orbit/arc when people are exchanging props, grabbing wrists, entering vehicles, signing, eating with hands, or speaking long visible dialogue.
- Do not combine more than one of: camera move, prop transfer, speaker change, focus change, character crossing. Split instead.
- Do not let camera movement replace physical action. If a person enters, exits, sits, stands, hands over, or turns, describe the body path separately from the camera path.

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

## Fixed-camera prohibition for micro-actions

Do not write a medium/wide fixed shot if the prompt asks the viewer to read subtle details such as fingertips, knuckles, chopstick tips, eye glints, throat movement, small mouth-corner shifts, card edges, plate edges, or a hand moving under/near the table. Use one of:

- close enough starting shot;
- relation-to-reaction compound shot;
- relation-to-prop compound shot;
- enlarge the acting detail to whole-hand, shoulder, torso, or clear prop-contact movement.

Fixed camera is allowed only when the shot is already close/insert, or when stillness itself is the dramatic point and the direct prompt states the stillness as performance.
