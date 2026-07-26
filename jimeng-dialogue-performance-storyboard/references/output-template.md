# Output Template

## Required Markdown structure

Generate this compact structure only. It separates material the user pastes into Jimeng from production notes that are needed only for complex shots.

```markdown
# [Title] 即梦投喂分镜

## 使用说明
## 全局锁定
## 通用负面提示词｜直接复制
## 场景状态表
## 分镜投喂卡
## 附录｜原文保留检查（按需）
## 附录｜复杂镜头验证（按需）
```

Do not output either appendix for ordinary delivery. Always perform the underlying checks internally.

## Global locks

Create `## 全局锁定` as short reusable blocks:

- `G-style`: aspect ratio, visual style, platform, and quality words.
- `G-character`: stable identity anchors and recurring clothing/body-state facts.
- `G-scene`: 2-3 fixed anchors, light direction, color temperature, and background control for each location.
- `G-state`: a compact current-state rule for recurring props or clothing only when the story needs it.
- `G-ui` (only when needed): the UI type, side-safe zone, face-safe zone, maximum readable text, and whether the UI is post-production rather than generated in-scene.

Do not repeat these blocks in every shot. For one clip, paste `全局锁定 + 【画面描述｜直接复制】 + optional 【必要约束】` into the positive prompt field.

## Negative prompt

Create `## 通用负面提示词｜直接复制` immediately after the global locks. It contains this baseline once:

`五官漂移、换脸、脸型变形、发型错乱、服装变色、手指畸形、肢体穿模、多手多臂、非说话者口型乱动、口型错位、嘴部崩坏、背景重构、人物瞬移、站位互换、道具漂浮穿手、画面跳帧、过度磨皮、模糊失焦、夸张翻白眼、人物僵硬、全身静止、无眨眼、空洞呆滞眼神、面部无任何变化、肢体不动、木偶式静止、死板、定格、面部僵硬`

Add only real shot-specific risks beside an individual shot. Never copy this list into the positive prompt.

## Scene state table

Use one compact row per location or changed state:

`scene/state ID | fixed anchor and light | people topology and screen zones | active prop/clothing owner and position | facts allowed to change`

Only list facts that recur across more than one shot. Do not create separate position, prop, and space tables for the same information.

For multi-scene stories, add a short `### 本集关键状态线` under this section. Track only cross-scene changes, such as `陆序穿着外套 -> 沈星雨披着外套 -> 沈星洲穿着外套`; do not repeat per-shot details already covered by `【状态继承】`.

## Shot group and child cards

`#### S1-01｜镜头组总时长：7.5s` is a human-readable story-beat group, not an additional Jimeng prompt. It represents one concrete change in audience recognition. Put the visible cast once at group level. Sum all child-shot durations in that group and write the total beside the group ID. The consecutive `【镜号】1/2/3` blocks are separately generated Jimeng child shots; each has its own duration and one main task. Do not add `分镜1` headings.

```text
**场景一｜商业街**

#### S1-01｜镜头组总时长：4.5s

【出现人物】
沈星雨
宋南枝

【镜号】
1，2s，普通。

【画面描述｜直接复制】
[Actual Jimeng positive prompt, normally 220-380 Chinese characters and never over 500. It naturally includes: shot size + camera placement/angle + static/one path + body/prop relation + one action or dialogue landing.]

【表演与声音】
[Only this child's new performance stage and sound.]

【状态继承】
[Visible tail facts required by the next child or group.]

【镜号】
2，2.5s，普通。
...
```

Every child contains exactly these four default fields, in this order:

```text
【镜号】
[Group ID-child number]，[duration]s，[普通 / 复杂]。

【画面描述｜直接复制】
[Actual Jimeng positive prompt, normally 220-380 Chinese characters and never over 500.]

【表演与声音】
[Only the active dialogue, OS, OV, system, ambience, or essential reaction: timing, mouth rule, pace, pause/tail tone, and motive. Write only this child's new performance stage, not the full emotional chain again. State sound priority when two or more layers overlap: visible dialogue > key sound effect > OS/system > ambience. Say “无台词” when applicable.]

【状态继承】
[Current visible opening facts for the next shot: position/facing, prop holder, clothing, emotional residue, and next-shot anchor.]
```

Before writing a child, make this internal one-line declaration and then translate it into natural Chinese inside `【画面描述｜直接复制】`:

`可见主体 | 身体朝向锚点 | 头/眼转向（按需） | 相对站位或接触物 | 景别 | 机位侧/角度 | 静止或单一路径 | 本镜唯一落点`

Do not output the declaration itself. A hand/object insert uses only the hands/props actually in frame; a relation frame names every visible person. Never use a fallback subject, conditional orientation, or generic camera phrase.

## Optional fields

Add an optional field only when it prevents a real generation failure. Do not add empty placeholders.

```text
【空间与道具锁定】
[Use for three or more visible people, a table/door/vehicle topology, or any prop transfer. State reachable hand/path/release state.]

【镜头执行】
[Use for a non-static camera move, focus shift, or visual micro-action. State hold, path, focus target, and landing frame.]

【口型分窗】
[Use for two or more visible speakers, dialogue longer than 5 seconds, or a handoff where mouth timing is risky. Start with `优先级：口型 > 听者反应 > 运镜`. Name one visible speaker per window and the mouth-close boundary. If a camera move is also used, state that the listener holds still except breathing/gaze, or remove the move.]

【镜内状态转换】
[Use only when this card visibly changes body pose, hand/prop contact or owner, clothing, door/window/light/UI, relation distance, speaking mode, or event result before dialogue/reaction. State `起始：...；转换：...；终态直投句：...；台词/反应：...；尾帧直投句：...`. The two direct-copy sentences must appear verbatim in `【画面描述｜直接复制】`.]

【剪辑衔接】
[Use for a scene/time change, flashback, continuous prop transfer/action continuity, or an independent object/empty-space/result cutaway. For an independent cutaway, state `独立生成；后期接入...声音` and the preceding/following state anchor.]

【必要约束】
[At most three shot-specific positive constraints or risks.]

【校验记录】
[Use only for complex shots; never paste into Jimeng.]
```

## Direct-copy rules

- The direct prompt must work with the global locks and restate current visible state that changed in the prior shot.
- Prioritize: current static anchor -> every visible person's body orientation toward a person/fixed object -> head/eye turn when different -> relative position/prop relationship -> shot size and camera placement/angle -> static hold or one path -> one main action and visible emotion -> dialogue or post-production voice rule -> tail state. `画面左/右` only supplements the relationship; it cannot replace body direction, distance, barrier, or camera side.
- A new dialogue/reaction card after a shot-size change, reverse angle, over-shoulder, walking beat, exit beat, counter/cabinet/door action, or prop transfer must reopen with complete body-facing facts. For ordinary face-to-face dialogue, write `A身体面向B，B身体面向A` before camera placement. If the prior tail has a character facing a door, road, counter, phone, or third person, the next card must either restate the changed face-to-face body orientation or show a visible turn before the dialogue begins.
- For a paired shot/reverse-shot, preserve the pair literally: the reverse of `机位在A肩后拍B，A前景肩线弱虚化` is `机位在B肩后拍A，B前景肩线弱虚化`, with the same distance/barrier, prop state, and background anchor repeated. Avoid loose reverse wording such as `B右前方` or `侧前方`, because it breaks the axis for AI generation.
- Prop transfer prompts must prevent object flashing and impossible reach: state where the prop starts, whose hand retrieves or presents it, how the receiver is physically reachable, when receiver contact happens, when giver release happens, and where the prop rests at tail. If the receiver starts behind/side-behind/turned away/out of reach, first write a positioning child where the receiver turns or the giver walks to face them; do not combine that reposition, prop retrieval, transfer, and dialogue in one child.
- Every child names a shot size and a camera state. For a static shot, state the camera side/angle and what the frame holds; for a moving shot, state one path and its landing target. Do not output bare `中近景固定` or leave camera information implicit.
- Do not put headings, checklists, prohibitions, or generic acting theory into the direct prompt.
- If a prompt needs more than one main generation task, split it. A subshot must restate its current visible facts rather than say `继承` or `延续上一镜`.
- For a same-card state change, write the direct prompt in time order: start state, one visible change, stable result, then visible dialogue/reaction and tail state. Copy `终态直投句` and `尾帧直投句` from `【镜内状态转换】` verbatim into it. Do not describe a phone as both at an ear and already put away, a door as both open and closed, or a prop as held by two owners without its contact/release sequence.
- For UI, phone text, payment alerts, or system overlays, reserve a side-safe zone and keep it off faces and active hands. Treat dense text as post-production unless the user explicitly needs it generated in-scene.
- For a standalone object/empty-space/result cutaway, add `【剪辑衔接】`. In `【必要约束】`, use only needed constraints such as `本镜无人入画；不生成口型；保持上一镜同场景光线和道具终态`. Do not require a face -> empty space -> face hard cut inside one generated clip.

## Flashback handoff

For memory, dream, montage, or a time/place change, use independent clips. The real-time trigger ends on a 0.5-0.8s stable physical hold; the inserted clip begins with a 0.5-1.0s stable scene anchor. Put only the visible states in the direct prompts; put a dissolve or sound bridge in `【剪辑衔接】`.

## Optional appendices

`附录｜原文保留检查` is a concise source-beat checklist. `附录｜复杂镜头验证` lists only complex shot IDs, first-generation risks, and the required first-pass observation. Neither appendix is part of a normal Jimeng paste workflow.
