# Stable Shot Contract

This is the hard stability contract for Jimeng dialogue/performance storyboards. Apply it before writing any shot card.

## 1. 前期分镜脚本规范

- Treat each shot as a visual-emotional unit. Do not split only because a micro-action exists; first try an internal camera path that keeps the emotional beat continuous.
- Split only for real structural changes: time/place/world change, new speaking subject without a mouth-close handoff, new dominant performer, overloaded prop/contact action, or camera view that cannot preserve the same spatial relationship.
- Every shot must state visible cast only. Do not list OS/system voices or characters that are only mentioned, remembered, or outside frame.
- Build a scene topology before shots: fixed static anchors, physical slots, screen zones, front/back depth, facing/eyeline, barrier/contact objects, movement lanes, empty areas, prop owners, and allowed changes.
- If a person or prop changes position/owner in shot N, shot N+1 direct prompt must restate the new visible position/owner as current-frame fact. Never rely on `继承/延续/保持` shorthand.

## 2. AI 提示词量化约束

- `【画面描述｜直接复制】` is the final positive prompt. It must be one semantic natural-language paragraph, not a table fragment.
- It must include: static anchor, visible character positions, physical topology, facing/eyeline, prop positions, acting trigger, facial/body reaction, dialogue/OS/system tone, camera path, focus landing, and tail state.
- No ambiguous coordinate words: write `画面左侧道路`, `A的右手边`, `桌对面`, `镜头前景`, `背景窗口前`; never bare `左边/右边/前面/后面/左外`.
- No ambiguous pronouns for key actions. Name the actor and prop owner when anyone speaks, moves, holds, receives, pushes, points, pays, signs, or reacts.
- Do not use compressed shorthand in direct prompts: `继承`, `延续上一镜`, `空间保持`, `位置不变`, `画面切到`, `反打到`, `剪辑`, `后期插入`, `脑海浮现`.
- Negative prompt must include both the identity/stability baseline and anti-stiffness terms: `人物僵硬、全身静止、无眨眼、空洞呆滞眼神、面部无任何变化、肢体不动、木偶式静止、死板、定格、面部僵硬`.

## 3. 镜头调度

- Shot size must match action readability:
  - 广中景/中景: location, lanes, group relation, whole-body/whole-hand actions.
  - 中近景: one speaker plus one listener/shoulder reaction, readable face and upper-body acting.
  - 近景/特写/插入: eyes, mouth corners, throat movement, fingers, fists, chopsticks, phone/card/plate ownership.
- A fixed camera is forbidden when the shot relies on subtle face/hand/prop micro-actions unless the shot is already close enough and the fixed frame is explicitly for precision lip-sync or contact. If a medium/wide shot contains micro-actions, use an internal push/focus or enlarge the action.
- Preferred compound pattern: `0.0-0.6秒关系中景锁静物和人物槽位 -> 0.6-X秒沿视线/手臂/桌面轻推0.2-0.4米或转焦一次 -> X-尾秒落到手部/眼神/道具近景并保留原空间关系`.
- For three-person table scenes: establish same-side pair and opposite-side standing person first; keep the table as barrier; do not let the standing person insert between same-side seated characters; if the dramatic beat is the standing person's pressure after another person speaks, start on speaker for lip-sync and land on the standing person's eyes/whole hand/fist after mouth close.
- Do not use hard cuts inside `【画面描述｜直接复制】`. If a true reverse/insert is needed, make a new card with its own visible shoulder/foreground composition and incoming first-frame facts.

## 4. 表演微动作

- Avoid dead listeners. Every visible important non-speaker needs a small, causally triggered reaction in the direct prompt, not only in `表演轴`.
- Speaker is primary; listeners are low-amplitude and do not steal focus. Listener reaction defaults: gaze follows speaker, slow blink, slight brow/mouth/shoulder change, hand rests/touches prop with small movement.
- Quantify listener motion when useful: head turn 5-10°, body/shoulder shift within 15°, single micro-action lasts 1.2-2.5s, no large repeated motions, no looping fidget unless source requires.
- Table-scene listener menu: `视线缓慢跟随说话人`, `自然眨眼`, `手掌轻搭餐盘边`, `整只手离开筷子旁`, `肩背轻僵/下沉`, `嘴唇轻抿`, `眉尾短暂收紧后松开`, `水杯端起1cm停1秒再放下`. Use only one or two per listener per beat.
- Emotion must be written as cause -> facial control -> body/prop action -> voice tone. Example: `听见“骗人”后，沈星雨眼神停半拍，被牵住的右手轻缩、肩背一僵，闭口OS以疑惑低音量响起：“...”`.

## 5. 后期补帧与闪回过渡

- Flashbacks/memories are independently generated clips with post-production transition, not single prompts that morph one location into another.
- Trigger/return clip: end with 0.5-0.8s stable physical handle: held eyeline, still hand, stopped breath/shoulder, or prop contact.
- Inserted flashback clip: begin with 0.5-1.0s stable scene anchor and starting poses before action/dialogue.
- Post bridge belongs in `声音轴/剪辑衔接/校验记录`: 3-5 white frames or short blur flash, present ambience dips, memory ambience enters 0.2s early, optional low-saturation/edge-vignette/mild handheld texture for the flashback clip.
- Direct prompt may say `低饱和闪回质感、边缘轻暗角、轻微手持感`; it must not say `校门变成巷口` or ask the model to animate a location transformation.
