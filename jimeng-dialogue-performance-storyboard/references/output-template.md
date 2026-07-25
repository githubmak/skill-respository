# Output Template

## Required Markdown structure

```markdown
# [Title] 即梦正式投喂分镜（固定模板正式版）

## 使用说明
## 全局锁帧模板
## 负面提示词｜直接复制
## 角色锁定表
## 人物位置与拍摄侧锁定表
## 场景与道具锁定表
## 场景空间状态表
## 分镜正式投喂表
## 高风险镜头首轮验证表
## 原文保留检查表
## 跨镜状态继承
## 交付前验证
```

## Global lock-frame template

Create `## 全局锁帧模板` as short reusable blocks:

- `G-style`: aspect ratio, visual style, platform, quality words.
- `G-character`: identity anchors and fixed clothing/body-state for recurring characters.
- `G-scene`: 2-3 fixed scene anchors per location; main light direction and color temperature.
- `G-background`: background extras count, position, blur level, movement direction, and no-focus/no-readable-dialogue rules.
- `G-common-negative`: inject the fixed baseline negative prompt exactly, then add only shot-specific risks when needed.

Do not repeat these blocks verbatim inside every shot.

## Negative prompt

Create `## 负面提示词｜直接复制` immediately after `## 全局锁帧模板`, containing exactly:

`五官漂移、换脸、脸型变形、发型错乱、服装变色、手指畸形、肢体穿模、多手多臂、非说话者口型乱动、口型错位、嘴部崩坏、背景重构、人物瞬移、站位互换、道具漂浮穿手、画面跳帧、过度磨皮、模糊失焦、夸张翻白眼`

## Fixed shot card

Every shot must use this field order:

```text
#### [Shot ID]

【镜号】
[Shot ID]，[duration]s，[main generation risk / first validation target]。

【画面描述｜直接复制】
[Actual Jimeng feed prompt, <=500 Chinese characters.]

【校验记录】
[Director/QA note. Do not paste into Jimeng.]

【空间锁定】
[People count / left-center-right / foreground-midground-background / facing relation / eyeline / distance / barrier or contact object / prop ownership / scene anchor.]

【摄影设计】
[Shot size + camera height + lens feel + subject distance + one camera path + direction + speed/amplitude + focus rule + occlusion rule + landing frame.]

【运镜时机】
[Time-coded trigger for holding still, moving straight nearer/farther, following a person, turning the camera to reveal something, changing focus once, a close view, shooting past a visible foreground shoulder, or a fixed frame.]

【表演轴】
[Emotion causality and time-coded acting beats.]

【声音轴】
[All dialogue, OS, OV, system, crowd, ambience with timing, mouth rule, pace, volume, pause/tail tone, motive.]

【口型分窗】
[For every spoken window: ID / visible speaker / original words / start-end / mouth-open and mouth-close boundary / punctuation pause and weighted word / other visible characters closed-mouth rule / listener delayed reaction. If there is no visible dialogue, explicitly state that no person speaks and name any post-production voice.]

【状态继承】
[Character position/facing / prop position/holder / camera landing / light / emotional residue / next-shot anchor.]

【剪辑衔接】
[Natural-language cut plan: direct continuation / changed camera view / changed time or place; outgoing stable hold / incoming stable hold / movement phase or pause state / shared ambience or dialogue tail / reference-frame requirement. For the last shot, state the final usable hold and that the sequence ends.]

【必要约束｜可追加】
[3-6 shot-specific risks or positive constraints only.]
```

## Direct-copy usage

- Positive prompt for one clip: `全局锁帧模板 + 【画面描述｜直接复制】 + 【必要约束｜可追加】`.
- Negative prompt for one clip: `负面提示词｜直接复制 + shot-specific negative risks from 必要约束`.
- QA fields are production contracts; their core information must already be compressed into `【画面描述｜直接复制】`.

## Cross-scene flashback handoff

For a memory, dream, imagination, montage, or time/place change, deliver at least two independently generated cards rather than one morphing card:

- The real-time trigger or return card ends with a 0.5-0.8s stable physical tail: a held eyeline, pose, prop contact, or fixed expression. Put that visible state in the direct prompt.
- The inserted card opens with a 0.5-1.0s stable scene-establishing head before dialogue or a new decisive action. Put its static anchor, character pose, and silence/closed-mouth rule in the direct prompt.
- Record the white flash, dissolve, match cut, or J/L sound bridge only in `【声音轴】` / `【校验记录】` as post-production execution. Do not ask the generator to turn one location into the other.

## Scene state table

Before shot cards, create one row per scene. Use only observable natural language:

`scene ID | fixed objects and their relative positions | character physical slots | screen left/centre/right and depth | facing and eye-lines | movement lanes and empty areas | prop owner/state | light source | facts that may change`.

Each shot reads its opening facts from this table and writes only its changes to `【状态继承】`. If a new camera view is used, restate the visible facts; never replace them with abstract position jargon.
