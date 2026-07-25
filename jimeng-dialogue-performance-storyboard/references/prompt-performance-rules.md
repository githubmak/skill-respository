# Prompt and Performance Rules

## Source fidelity

Do not preserve only dialogue. Every source paragraph or beat, including `△` action description, narration, reaction, scene heading, flashback marker, OS/inner monologue, system line, crowd reaction, and prop/state change, must have a shot landing.

- Create `## 原文保留检查表` covering all source beats, not only spoken lines.
- Columns: source index, original text excerpt, type, target shot, handling method.
- Handling method must be one of: `直接入画面描述`, `压缩入画面描述`, `进入声音轴`, `进入状态继承`, `后期蒙太奇/字幕`, or `合并到相邻镜`.
- Plot-driving non-dialogue beats must appear in `【画面描述｜直接复制】`, not only in QA fields.
- Do not replace concrete source beats with vague wording such as `三人反应停住`, `气氛变化`, `众人议论`, or `关系尴尬` unless the visible action is also written.

## Direct prompt style

`【画面描述｜直接复制】` is the final Jimeng feed prompt, not a director note.

- Keep it `<=500` Chinese characters.
- Use one readable narrative paragraph.
- The paragraph must be semantic natural language, not a compressed state table. Avoid unclear coordinate fragments such as `A右、B左、道具不变`. Write drawable relations in full sentences: who sits/stands where, beside/across/behind whom, which direction they face, what object separates them, and where each active prop visibly rests.
- Do not be lazy or under-specified. The direct prompt must be rich enough to generate the clip by itself: space, state, performance, voice, camera, reactions, and tail must be inside the paragraph. QA fields can expand them, but cannot be the only place they appear.
- Put shot-specific identity/position/action/lip-sync/prop/camera information before style polish.
- Include the minimum visible anchors when pasted alone: static scene anchor, subject screen zone, coordinate basis, front/back layer, facing relation, eyeline, distance/barrier object, active prop, core action, visible emotion leak, original dialogue or post-audio handling with tone, camera path, and tail state.
- At the start of a continuation shot, translate the previous shot's tail state into current visible facts inside the direct prompt: likely visible characters, their screen zones/physical slots/facing, and prop positions/owners. Do not leave these facts only in `【状态继承】`.
- For table/room/crowd shots, begin with an unmoving spatial anchor before people: table edge, doorframe, window, counter, sofa, bed, wall lamp, hallway line, vehicle door, or other fixed object that frames perspective.
- Spatial words must be unambiguous: use `画面左/右/中/前景/背景` for screen position; use `在A的右侧/桌对面/身后半身距离` only for relationship position, and ideally pair both in one phrase.
- Group-internal left/right must name its basis. Do not write only `组内左座/右座`. Write `以二人坐在桌内侧、面朝餐桌对面的身体左右为基准，A在B左手边，B在A右手边`; then separately state screen near/far or foreground/background if the camera is oblique.
- Do not convert camera depth into story position: `左前景` means the subject is closer to camera, not necessarily across the table. Preserve source relationship first, then describe screen layer.
- For stable seated scenes, include the physical topology phrase in the direct prompt when there is risk of swapping: `A和B是桌内侧同排双人组；以二人坐在桌内侧、面朝餐桌对面的身体左右为基准，A在B左手边，B在A右手边；二人椅背在同一条平行画框的水平深度线、肩线平齐、到镜头距离一致，相距半身，桌沿在二人身前，不隔桌、不面对面、不一前一后；C在餐桌对面，与双人组隔桌，不插入A和B之间`.
- In direct prompts, do not write `继承`, `延续上一镜`, `空间保持`, `位置继承`, or `物理座位不变`. These are QA concepts. Replace with visible facts such as `A和B是同侧邻位双人组，A在组内左位，B在组内右位，道具X停在B正前方`.
- Do not write trailing labels such as `声音语气：`, `表情：`, `动作：`, `表演增强：`, or `情绪：`. Rewrite them as embodied narrative.
- Do not write editing/meta words such as `剪辑`, `切到`, `反打到`, or `下一镜执行`. Two-person shot intent must appear as a visible foreground shoulder, subject position, facing direction, and background anchor.
- Do not use `脑海浮现`, `原剧情闪过`, or `后期插入` to carry plot-critical visible action inside another shot. If the viewer must see the action, split it into an independent flashback/montage shot with its own scene anchor, characters, action, and tail state.
- If any visible important listener is present during another character's dialogue or OS, the direct prompt must give that listener a causally triggered low-amplitude reaction: gaze follow, blink, brow/mouth change, shoulder/hand/prop micro-action, or posture change. `闭口` alone is invalid for important listeners.

Recommended flow:

`[时长/画幅/镜头方式] + [静物锚点/物理槽位/画面分区] + [隔物/同侧/桌对面关系] + [触发原因] + [眼神/眉尾/嘴角/呼吸] + [手/肩背/步伐/道具动作] + [对白/OS/系统声处理与语气] + [摄影机物理路径/焦点/落幅] + [尾帧可见事实]`

Weak: `她说：“...”；声音语气：语速轻快、尾音上扬。`

Strong: `说话者眼睛一亮、身体微前倾，以轻快语速、尾音上扬说：“...”。`

Weak: `A皱眉，脑海浮现B被多人围住，C报警并挺身而出。`

Strong split:

- `现实反应镜：A站在固定场景物右侧看向B远去方向，皱眉，闭口思考。`
- `闪回镜：独立新场景，B被3名路人从三侧围住，C在右后举手机报警并上前半步。`
- `回到现实镜：A回神，抬眼寻找C。`

## Flashback transition handoff

Treat a flashback as one continuous editorial beat built from independent generation clips, not as a single clip that transforms its setting.

- **Trigger/return clip:** end on a concrete 0.5-0.8s stable visual handle, such as a gaze stopping on a prop, a hand holding still, or a breath/shoulder settling. The direct prompt must describe only that physical hold; it must not say `闪白进入回忆`, `淡出`, or ask the model to transform the set.
- **Inserted clip:** open on a 0.5-1.0s stable establishing handle: fixed scene anchor, characters already in their starting poses, and no visible dialogue before the new world is readable. Start lip-sync only after this handle.
- **Post-production bridge:** write the exact white-flash/dissolve duration and J/L sound bridge in `【声音轴】` or `【校验记录】`. A practical default is 3-5 white frames, real-world ambience fading under the flash, and memory ambience entering 0.2s before the inserted image.
- **Return:** apply the same rule in reverse. The last memory clip ends on a stable pose; the present clip begins with its present-day anchor and an initial silent hold before OS or dialogue.

Weak: `现实场景里A看着B离开，尾端闪白变成回忆场景。`

Strong pair:

- `现实触发镜：B离开后，A视线从出口落到正前方道具，右手悬停，尾0.6秒保持静止。`
- `回忆起幅镜：回忆道具横在画面下半区，B在左侧做准备动作、A在右侧站定，前0.7秒二人闭口不动，随后A开始说原文。`

Weak: `B右侧近景，A左前景朝右，C左后虚化。`

Strong: `同一张长桌横贯画面下半区，桌沿与画框平行；A和B是桌内侧同排双人组，双人组位于画面中右区域，以二人面朝隔物对面的身体左右为基准，A在B左手边、B在A右手边，二人椅背在同一水平深度线、肩线平齐、到镜头距离一致，不隔桌、不面对面、不一前一后；本镜从B侧拍近景，A只作为组内同排前景肩线弱虚化；C在餐桌对面，与双人组隔桌，不插入二人之间。`

## Emotion and acting

Every emotion must be driven by:

`触发原因 -> 表情控制 -> 肢体动作 -> 说话语气`

If no emotion is explicit, infer it from immediate goal, obstacle, relationship, and previous residue. Express it through visible micro-action and voice tone, not labels.

Useful visible leaks: eye pause, brow-tail pressure, mouth-corner control, breath hold, shoulder tension, finger pause, grip tightening, small step, clothing/prop contact.

For every important beat, the direct prompt should contain a compact performance chain in natural language:

`because/after trigger + eyes/brow/mouth/breath + fingers/shoulders/body/prop + voice pace/volume/tail tone + listener delayed reaction`.

Weak: `A很生气，B尴尬。`

Strong: `听见“没关系”后，A眼神停半拍、下颌线绷紧，垂在裤侧的右手攥紧又松开；B夹在中间，筷子停在餐盘上方，肩背轻僵但闭口。`

Do not let performance live only in `【表演轴】`. The direct prompt must show at least two visible micro-expression/body clues for the main emotional turn and one delayed listener micro-reaction when another important character is visible.

## Action and performance density

Every direct prompt must contain at least one visible performance leak and one physical action or stillness contract.

- Treat a shot as one **visual-emotional unit**, not one sentence of text. If a micro-action belongs to the same emotional beat and the same physical relationship, do not automatically split it out. Use an internally staged camera path such as `关系中景起幅 -> 轻推/转焦到可读手部或眼神 -> 尾帧回到情绪状态` so the beat stays continuous.
- Split only when the shot would otherwise contain too many competing tasks: visible speaker handoff without mouth-close gap, time/place/world change, a new subject becoming the main performer, two or more prop transfers, physical contact plus camera movement plus long dialogue, or a micro-action hidden below frame that cannot be reached by a safe push/focus.
- Choose shot size from the action's required pixel share before writing the prompt. Broad blocking and group relation need wide/medium; dialogue and face reaction need medium close/close-up; fingertip/phone/card/plate ownership needs close-up or a timed push/focus landing. If the prompt contains `眼神细变、嘴角、喉间、手指、拳头、筷子、银行卡、餐盘边缘`, the shot must either start already close enough or move there with time anchors.
- Fixed camera is invalid for a shot whose dramatic information depends on subtle hand/finger/eye/prop details unless the shot is already a close-up/insert and the fixed frame is for precise lip-sync or contact. In medium/wide frames, use a push/focus landing or enlarge the action to whole hand/shoulder/body movement.
- Replace emotion labels with body evidence: not `慌乱`, but `眼睫颤一下、指节压住领口、肩膀微缩`.
- Strengthen important emotional turns with at least two facial/body details: eye movement, brow-tail pressure, mouth-corner control, breath, shoulder, finger, posture, step, clothing/prop contact.
- Put the trigger before the reaction: `听见关键词后，听者延迟半拍抬眼，指尖停在道具边`.
- Match micro-action to shot size. A multi-person medium shot can show a whole hand, shoulder, or body recoil, but not reliable fingertip details. If the beat depends on `指尖`, `指节`, `戒指`, `签字笔尖`, `筷子尖`, or a hand disappearing below a table, use a hand/prop close-up or enlarge the action to `整只手离开道具、退回桌沿内侧`.
- If a medium shot must first establish multiple people but the emotional reveal is in a hand/fist/plate reaction, write a continuous internal camera path: first lock the spatial anchor and slots, then push/shift focus to the close readable detail, then state where the other characters remain. This is preferred over leaving the whole beat in a static medium frame.
- Limit action budget: one main action plus one listener micro-reaction per beat. If there are two hand actions, a speaker change, and camera movement, split or simplify.
- State the action path and result: `右手把道具沿桌面推到角色B当前座位正前方，手离开道具边`.
- Separate gaze from body movement. Do not write `角色越过桌面/越过柜台看道具` unless the body should lean or cross the barrier. If only the gaze crosses a barrier, write `角色站直留在隔物对面，上半身不前压，视线越过桌沿/柜台边缘落到道具`. If leaning is intentional, make it a quantified body contract: `角色脚步留在原位，上半身向前倾约10-15度，单手/双手撑在桌沿，胸口不越过桌面中线，视线落到道具，尾帧保持前倾但不穿桌`.
- Do not move a prop that is not at the mover's current opening position. If `道具Y` ended the previous shot at `角色B正前方`, the next direct prompt must not say `角色A把道具Y挪回` unless it first places `角色A` within reach and shows the reach/contact path.
- For exchanging two props, stage the action instead of writing one simultaneous sentence: first state both props' starting positions, then move prop X to its new owner/place and release it, then move prop Y to its new owner/place and release it, then state the tail frame. Add `双手离开` or `不再拿回` when the final ownership matters.
- Stillness is also action: write `尾0.6秒筷子悬在餐盘上方、眼神停在桌面` instead of vague `保持`.

## Camera execution strength

Camera wording in direct prompts must be physical and readable by an image/video model.

- Fixed camera: say why visually, e.g. `摄影机固定，焦点锁手腕和银行卡接触点`.
- Push/pull: write path and distance, e.g. `摄影机沿直线缓慢推近0.3米，焦点锁主体双眼`.
- Follow: write lane and speed, e.g. `摄影机胸高沿餐桌右侧平行侧跟1米，不超过人物`.
- Foreground-shoulder view: write camera owner, shoulder share, subject, barrier, and shared anchor.
- Avoid camera words that imply editing or model-invisible logic: do not put `镜头语言表达压迫`, `正反打`, `沿轴线`, or `连续变景别` in direct prompts.

## Dialogue and timing

- Preserve original words exactly.
- Short Mandarin line estimate: roughly 4-6 Chinese characters/second, then add reaction margin.
- For 2-4 character lines, lip-sync window is usually 0.4-0.9s; after the line, write `说完即闭口`.
- Long lines must be split if real/TTS audio plus reaction margin exceeds 15s.
- Only one visible mouth speaks in a shot unless overlap is explicitly required; true overlap goes to post-production.
- Every dialogue/OS/system line must have pace, volume, pause/tail tone, emotional motive, and mouth-sync/post-production handling.
- OS/OV/system/inner monologue/phone text/UI text/dense captions are post-production audio/overlays by default; visible mouths stay closed.

## Mouth windows and speaking handoff

`【口型分窗】` is mandatory whenever there is visible dialogue. It is a QA/timing record, not a loose prompt label. One row is required for every speaking window:

`D1｜visible speaker｜original words｜start-end｜opening pose → mouth closes｜pause and weighted word｜other visible people closed-mouth rule｜listener reaction after the trigger`

- One window has one visible speaker. The speaker's face and mouth must be readable; if that cannot be kept stable, move the line to post-production audio or split the shot.
- Start a new visible speaker only after the previous speaker has finished, closed their mouth, and left a short reaction gap. Use a 0.2-0.4s gap as a planning target unless the source explicitly requires an interruption.
- Mark meaningful punctuation in natural language: a short comma pause, a held ellipsis, a question rising at the end, or a word that receives weight. Do not force every punctuation mark into the same duration; fit it to natural speech and real/TTS audio.
- For interruption, write the exact cut-off word, the first speaker's mouth-closing moment, the second speaker's start time, and the frozen/changed hand gesture. For true overlap, preserve one visible mouth and place the second voice in post-production.
- Split a line before it overloads the image: speaker change, emotion turn, action turn, camera view change, strong pause, or a line that leaves too little time for an opening pose, readable speech, mouth close, and listener reaction are all valid split points. Duration alone is not the only criterion.

OS/system pattern:

`角色A闭口，OS以偏快语速、低音量、尾音心虚收住响起：“原文”。`

If visible system text is requested:

`系统文字仅在侧边安全区作彩色悬浮字幕，不遮脸、不遮手、不生成系统实体。`

## Listener reactions

Do not solve non-speaking characters by writing only `闭口`.

- Reaction timing: start 0.2-0.6s after the speaker's trigger word or after the line lands.
- Reaction budget: one micro-action per listener per beat.
- Motion scale: listeners move less than the speaker. Keep head turns around 5-10°, shoulders/body shifts under 15°, single micro-action 1.2-2.5s, slow natural blink, no repeated fidget unless source requires.
- Reaction cause: state what they react to, such as `听见“帅哥”后`, `被当众点名后`, `看到餐盘被推走后`.
- Mouth rule: non-speakers stay closed-mouth unless they have their own dialogue window.
- Focus rule: listener reactions support the main speaker and must not steal focus.

Example:

`角色B说话时，角色A延迟半拍抬眼，整只手停在自己道具边、肩背轻僵但闭口；角色C视线从A移到B，下颌轻收不说话。`
