---
name: fight-scene-video
description: Design style-specific fictional fight scenes as production-ready action beats, impact choreography, shot-by-shot blocking, overhead trajectory-map inputs, and AI video prompts. Use when the user asks for fight choreography, combat scene design, martial-arts or xianxia action, realistic hand-to-hand impact, action-storyboard planning, combat blocking, a fight scene trajectory map, or an AI-video-ready duel, chase, superhero, fantasy, or animated action sequence.
---

# Fight Scene Video

Turn a premise, scene, screenplay excerpt, or existing storyboard into a coherent fictional action sequence that can be generated one shot at a time. Produce a fighting design and generation package; do not claim to execute a real stunt or validate an actual generated video.

## Operating Rules

- Preserve the supplied characters, outcome, weapons, powers, setting, and plot. Mark any placement or action inferred from incomplete source as `合理推断`.
- Design for screen readability, not real-world combat instruction. Describe impact with cinematic result, reaction, and spatial consequence; do not provide real-world training, injury, or weapon-use instruction.
- Treat every generated video clip as one visual cause-and-effect unit. Split when a new attack chain, focal character, power reversal, major prop state, or camera axis is needed.
- Fix the scene north direction, character labels, screen sides, prop ownership, and light anchors before designing shots. Carry each shot's end state into the next shot's start state.
- Derive the action language from the chosen style and location before writing any moves. A fight that would play unchanged in another genre or location has failed the design.
- Design editorial rhythm separately from camera movement. A stable single generated clip may use one primary move, while the completed fight must use a purposeful sequence of shot sizes, angles, cut triggers, and aftermath holds.
- For practical live action, require a qualified stunt coordinator and use the output only as a creative previsualization brief.

## Required Input

Extract these fields from the request. Ask only for a missing field that materially changes the scene; otherwise use a conservative `合理推断`.

| Field | Need |
|---|---|
| Dramatic goal | Why this fight happens and the required outcome or interruption |
| Characters | Labels, fighting style, capability gap, weapons/powers, injury limits |
| Location | Fixed anchors, entrances, obstacles, breakable or forbidden areas |
| Duration | Total target duration and target clip length |
| Visual target | Platform/model, style, aspect ratio, reference-image availability |

## Workflow

## Integrated Production Route

Use the following route when the user needs a complete fight package. Skip only the specialist whose output the user explicitly does not need. Read [references/integrated-workflow.md](references/integrated-workflow.md) before dispatching other skills.

`fight-scene-video` owns story facts, action beats, ability limits, impact logic, and the final decision on every shot. Specialist skills may refine only their assigned fields; they must not invent a new attack, effect, character, prop, power, or outcome.

| Order | Specialist | Receives | Returns to this skill |
|---:|---|---|---|
| 1 | `natural-emotion-performance` | beat trigger, power relation, body state, dialogue if any | visible intent, fear/control leakage, breath, posture, reaction amplitude |
| 2 | `frames-analysis` | scene lock, character positions, action beat, previous visual state | foreground/midground/background, material, light lock, composition, action vectors |
| 3 | `camera-analysis` | coverage role, action vector, frame lock, axis, prior/end state, 16:9 requirement | shot size, angle, lens intent, one primary move, cut and axis plan |
| 4 | `overhead-trajectory-map` | approved movement and camera facts only | top-down map brief and map-generation prompt |
| 5 | `continuity-ledger` | every shot's actual end state and camera state | compact carryover state and continuity warnings |
| 6 | `audio-design` | locked picture, impact timing, scene material, cut points | foley, silence, music pulse, transition sound, and sound bridges |

Run Steps 1-3 per coverage unit, Step 4 for every moving or multi-character shot, Step 5 after every shot, and Step 6 after picture timing locks. This skill itself assembles the final Jimeng prompt from the approved locks. Do not generate final video prompts until any continuity warning is resolved or explicitly accepted as a deliberate break.

### 1. Lock the Fight Contract

Write a compact contract before choreography:

```text
Conflict: [who wants what; what prevents it]
Outcome: [win / escape / interruption / unresolved]
Capability rule: [one concise advantage and limitation per side]
Space lock: [north-up anchors, routes, prohibited zones]
Continuity lock: [starting sides, props, damage, light, wet/dry or debris state]
```

Do not solve the scene through unexplained skill, a new weapon, a new power, or an offscreen helper.

### 2. Lock the Style and Impact Language

Before action beats, write a `style action diagnosis` with these five fields:

| Field | Decide |
|---|---|
| Movement engine | Weighty pressure, elegant flow, explosive bursts, aerial control, or an unstable hybrid |
| Contact grammar | Heavy collision, redirection, evasive near-miss, weapon clash, or effect-to-effect impact |
| Energy/effect grammar | None, restrained residue, visible technique path, or large-scale spatial consequence |
| Scene participation | Which anchors provide cover, footing, verticality, breakage, danger, or a forced route |
| Camera rhythm | Establish threat, isolate commitment, reveal reversal, hold impact, then retain consequence |

Read [references/style-action-language.md](references/style-action-language.md) for the matching genre rules and [references/camera-rhythm.md](references/camera-rhythm.md) for coverage design. Never use generic phrases such as `打斗激烈` or `拳拳到肉` without writing the visible mechanism that creates the feeling.

### 3. Design Cause-and-Effect Action Beats

Build the scene as 3 to 6 action beats: `pressure -> response -> changed spatial state`. Every beat must visibly change distance, balance, cover, weapon ownership, route access, or power balance.

Use the budget and stability rules in [references/action-budget.md](references/action-budget.md). Prefer a distinctive reaction or environment consequence over adding another strike. Keep simultaneous multi-person contact, complex grappling, rapid weapon handoffs, and repeated impacts out of one AI-video clip.

For a contact or effect impact, explicitly write: `anticipation -> committed path -> contact/near-miss -> force transfer -> recovery or displacement`. The reaction must differ by character and location: a heavy fighter braces, a light fighter redirects, loose rubble scatters, a steel surface rings, and an xianxia barrier ripples or fractures. Do not let the target merely slide backward without a cause.

### 4. Convert Beats into Generateable Shots

First turn every action beat into a coverage rhythm: `spatial setup -> commitment -> reversal or contact -> impact evidence -> aftermath`. Use 4-7 coverage units for a 12-20 second fight; combine units only when a continuous camera path makes the causal relation clearer.

Give each generated shot one dramatic purpose and one primary camera response. State `start lock`, `action chain`, `end lock`, and `next-shot carryover`.

For each shot, include:

| Field | Requirement |
|---|---|
| Duration | Usually 3-6 seconds; use 7-8 seconds only for a clearly readable continuous move |
| Focus | One primary subject or a stable two-person composition |
| Action chain | Setup, one decisive action, visible response, settled end state |
| Screen/axis lock | Screen left/right, facing direction, and camera-side constraint |
| Prop state | Owner, orientation, contact state, and final position |
| Camera | Static, one push/pull, one track, one lateral move, or one orbit; state the trigger |
| Coverage role | Establish space, threat, action commitment, reversal, contact, impact consequence, or aftermath |
| Cut logic | The visible action, eyeline, obstruction, sound, or impact frame that motivates entry and exit |
| Shot design | Shot size, angle, lens intent, axis side, and focal subject |
| Impact or effect | Anticipation, path, contact/near-miss, force transfer, reaction, and scene residue |
| Risk | Identity, limb, contact, occlusion, environment, or motion risk and simplification |

If the source requires an extended exchange, split at a reaction, an obstacle, a contact break, or an action match point. Do not hide a discontinuity behind an arbitrary fast cut.

For AI video, select one delivery mode before writing prompts:

- `editorial sequence` (default for a fight): generate 2-4 second coverage shots separately, then cut them in editing. This is the preferred mode for strong rhythm and reliable impacts.
- `continuous take`: keep one camera path and one action chain in a 4-8 second clip. Use only when the uninterrupted route itself is the attraction.
- `shot group`: allow at most two internally connected views in one clip, joined by a named action or obstruction match. Do not use it for repeated reversals or rapid coverage.

### 5. Produce an Overhead Map Brief Per Shot

For every moving-camera or multi-character shot, invoke `overhead-trajectory-map` with the exact movement facts below. A sequence-level map is optional and never replaces individual shot maps.

```text
/俯视轨迹图

镜号：[ID]｜[short title]
地点与固定锚点：[north-up layout, entrances, obstacles, prohibited zones]
人物1 [label]：蓝色虚线；S1=[start]；路径=[only this shot's route]；E1=[end]。
人物2 [label]：黄色虚线；S2=[start]；路径=[only this shot's route]；E2=[end]。
关键道具：[start owner/location -> end owner/location]。
摄像机：[CAM S -> CAM E, one authorized movement, focus and direction]。
请保持前镜继承状态：[screen sides, facing, light, damage/debris state]。
输出真实完整场景底图、垂直正交纯上帝俯视图、角色起终点圆圈、彩色虚线路径、白色实线摄影机轨道、侧边图例；不得新增角色或动作。
```

When any push, pull, lateral move, follow, orbit, crane, or handheld movement exists, require a white camera rail. Use a fixed camera point and field-of-view wedge only for a fully static shot or a pure pan/tilt.

### 6. Write the Video Prompt

Each generated coverage shot has two mandatory, paired prompts:

1. `轨迹图生图提示词`: copy the complete positive and negative prompt produced by `overhead-trajectory-map` to generate the top-down reference map.
2. `即梦动态视频提示词`: after the map is approved, assemble the locked scene, character, movement, camera, performance, continuity, and sound facts using the protocol below. Deliver its final positive prompt and its separated video negative prompt.

Use the approved map as a staging reference asset together with the character and scene reference assets. Write the video prompt for the actual on-screen view, never as a description of colored map lines, `S/E` markers, `CAM` rails, or legends. The map constrains positions, routes, and camera path; it must not appear inside the final video.

#### Jimeng Action Prompt Assembly Protocol

This skill writes the prompt directly. Do **not** call `ai-prompt-builder`, inherit its defaults, or use its `动态漫` / `国漫古风` / `60帧` language unless the user explicitly requested those properties.

Write concise Chinese prose in this exact semantic order. Keep only details that are visible in this shot; default target is 180-420 Chinese characters, and split the shot rather than exceed 550.

```text
[format + duration + declared visual style].
[immutable character identities, wardrobe, body condition, and start positions].
[location anchors, light direction, and current material/debris condition].
[shot size, camera angle/lens intent, axis side, one primary camera move, and its trigger].
[one complete action chain: intent -> anticipation -> committed path -> contact or near-miss -> force transfer -> distinct reaction -> environmental/effect residue -> settled end frame].
[visible performance control: gaze, breath, posture, face, recovery; only what the framing can show].
Maintain [screen direction, prop ownership, effect rule, and end state]; no extra characters, powers, weapons, actions, cuts, or camera moves.
```

Assembly rules:

- State the visual style from the fight contract, never a genre default. For 3D CG, name rendering/material/light qualities appropriate to this fight; for xianxia, specify declared technique paths and controlled residue; for realistic hand-to-hand, prioritize balance break, contact surface, recoil, and weight transfer.
- One prompt contains one primary camera move and one decisive action chain. A pan/tilt may accompany a locked camera only when it follows the same subject and does not create a second move.
- Translate maps into screen facts only: start/end positions, route, facing, distance, and camera path. Never include map colors, line types, labels, markers, arrows, rails, legends, or "top-down map" language.
- Do not ask the model to render dialogue, subtitles, captions, sound effects, frame rate, resolution, or invisible analysis terms. Keep spoken dialogue and final audio notes outside the visual prompt.
- Include a power only as `declared source -> visible path -> tactical consequence -> residue`. Invisibility and time control need a visible reveal cue or environmental consequence that makes the reversal readable.
- The positive prompt must end with the exact, settled visual state that is handed to the next shot. It is the authoritative prompt-level continuity record.

Write a separate negative prompt with 6-12 shot-specific failure constraints. Start with the most damaging risks: identity drift, mirrored positions, extra limbs, limb intersection, unreadable contact, duplicated/missing prop, ability misuse, unintended teleporting, extra people, unintended cuts, camera drift, flicker, and scene/lighting changes. Do not put positive instructions in this field.

Keep the action sequence ordered and physical: position -> intent -> anticipation -> decisive action -> contact/near-miss -> force transfer -> reaction -> environment residue -> end frame -> camera response.

```text
[format, duration, style]. [immutable character and wardrobe anchors].
[location anchors and light]. [opening positions and eyelines].
[one readable action chain with a visible response and settled final state].
[style-specific force, effect, or material response].
[one camera movement and its trigger].
Maintain [screen sides, prop state, scene condition]; no extra characters, actions, weapons, or camera movements.
```

Add a short negative prompt that targets the shot's actual failures, for example: mirrored screen positions, extra limbs, weapon duplication, unmotivated camera drift, implausible teleporting, new props, unreadable contact, or unplanned cuts.

### 7. Run the Continuity and Impact Gate

Before delivering, verify every adjacent pair:

1. Previous `end lock` exactly supplies the next `start lock`.
2. Character position, facing direction, line of action, weapon/prop owner, damage, debris, and light state agree.
3. The next shot begins with a visible carryover: action match, eyeline, spatial route, prop state, sound bridge, or emotional residue.
4. Each video clip stays within its action budget and uses no more than one primary camera move.
5. Each impact has a readable cause, contact/near-miss, force direction, character-specific reaction, and material or effect consequence.
6. Effects obey the selected style: they originate from a declared ability or object, follow a visible path, alter a route/defense/space, and leave a matching residue. Decorative effects fail this gate.
7. The scene anchor changes the tactical choice. If a beat works identically in an empty room, replace or remove it.
8. Every cut changes the viewer's access to information: space, attack line, commitment, reversal, contact, or consequence. Cuts made only to create speed fail this gate.
9. The camera plan has an intentional size and angle gradient. Do not repeat the same medium side view for three coverage units without a narrative reason.
10. The overhead-map end state, the Jimeng prompt's end frame, and the continuity-ledger end state agree on each character's position, facing, body state, prop state, and camera axis. Any mismatch blocks delivery.

## Required Delivery Format

```markdown
## 打斗戏视频设计｜[scene name]

### 打斗合同
[conflict, outcome, capability, space, continuity]

### 风格动作诊断
| 运动引擎 | 接触语法 | 特效语法 | 场景参与 | 镜头节奏 |
|---|---|---|---|---|

### 动作节拍
| 节拍 | 压力/动作 | 对方回应 | 空间或权力变化 |
|---|---|---|---|

### 镜头节奏表
| 时间 | 覆盖职责 | 景别/角度/焦点 | 运镜 | 入点与切点 |
|---:|---|---|---|---|

### 分镜与连续性台账
| 镜号 | 时长 | 覆盖职责 | 起幅锁定 | 动作链与受力 | 摄影机设计 | 落幅锁定 |
|---|---:|---|---|---|---|---|

### 轨迹图制作包
#### [镜号]
[complete overhead-trajectory-map input]

### 轨迹图生图提示词
#### [镜号]
**正向提示词：** [complete prompt returned by overhead-trajectory-map]
**负面提示词：** [complete negative prompt returned by overhead-trajectory-map]

### 即梦视频生成包
#### [镜号]｜[duration]
**参考素材：** [角色设定图 / 场景图 / 本镜轨迹图；轨迹图仅作走位和运镜参考]
**即梦动态视频提示词：** [prompt directly assembled by this skill from the approved locks]
**即梦负面提示词：** [shot-specific separated negative prompt]
**生成风险与降级：** [one concise fallback]

### 跨技能制作交接
| 镜号 | 表演锚点 | 画面/材质锚点 | 摄影机锚点 | 轨迹图 | 连续性状态 | 声音桥 |
|---|---|---|---|---|---|---|

### 连续性检查
[pass/fix list]
```

Use `ai-video-agent-mode` only when the user needs a broader project pipeline, batch QA, or export. Use this skill first when the core task is designing the fight itself, then hand the resulting shot package to the broader pipeline if needed.
