---
name: storyboard-to-nine-panel-pipeline
description: Bridge and orchestrate full outputs from split-script-to-storyboard into batch nine-panel storyboards. Explicit slash commands include /九宫格, /九宫格剧情包, /剧情九宫格, /批量九宫格, /分镜转九宫格, /剧情包转九宫格, and /剧情包. Use when the user asks for 剧情包, 九宫格剧情节拍包, 分镜转九宫格, batch-convert 分镜脚本 to 剧情九宫格, or feed those beat bundles into nine-panel-video-storyboard. Preserve the original script, outline, dialogue, OV, narration, and OS while only reasonably splitting shots or adding visible details implied by the source.
---

# Storyboard To Nine Panel Pipeline

## Core Use

Convert `$split-script-to-storyboard` output into multiple compact story beat bundles, then use `$nine-panel-video-storyboard` on each bundle to produce strict 9-panel JSON storyboards.

Bridge/orchestration skill — do not replace either source skill. Preserve detailed shot-table information while adapting it into narrative nine-panel grid structure.

Automatically pass through emotion-analysis performance data when source contains speaking characters, reactions, emotional turns, OV/OS: `触发原因→核心情绪→外化控制(6部位)→表演支点`.

## Required Skill Order

1. Raw script/prose/dialogue/novel/outline → use `$split-script-to-storyboard` first, complete shot table.
2. Existing shot table → parse directly, do not regenerate.
3. Build intermediate beat bundles from shot table.
4. For each beat bundle, use `$nine-panel-video-storyboard` in narrative mode (unless user explicitly asks for single-shot keyframe grid).

> 📖 Bundle schema details → [references/beat-bundle-schema.md](references/beat-bundle-schema.md)
> 📖 Bundle director standards (5 skill packs, conflict mapping, pipeline validation) → [references/bundle-director-standards.md](references/bundle-director-standards.md)

---

## Source Fidelity Contract

- Only perform reasonable shot splitting, beat grouping, panel expansion, AI formatting. Don't arbitrarily alter script.
- Preserve source plot, outline, timeline, causality, character relationships, dialogue, OV, narration, OS.
- Don't delete required OV/dialogue/OS. Long lines → distribute across bundles/panels preserving wording.
- Reasonable completion only within provided outline: visible gestures, blocking, eyelines, prop handling, reactions, sound cues, transitions, spatial continuity.
- Don't invent new plot events, characters, backstory, clues, or flashbacks.
- Record any merging/splitting/inference in bundle notes or `must_not_change`/handoff constraints.

---

## Bundle Splitting Rules

Split by these boundaries (in order):
1. Scene marker (场次 S01, S02, location/time change)
2. Major conflict turn (accusation, command, threat, reveal, interruption, chase, capture, reversal, decision, consequence)
3. Key prop state change (cup lifted/lowered, letter revealed, door opened, weapon drawn, sleeve grabbed, body dragged)
4. Character arrangement change (entrance, exit, kneeling, standing, blocking, dragging, facing away, locking eyes)
5. Emotional turn with visible evidence (shock, concealment, anger, fear, resignation, coldness, defiance)

A normal bundle covers 3-8 original shots. Dense scene = several bundles. Single shot = one bundle only if it contains complete visible event chain.

---

## Beat Bundle Construction

For each bundle, extract only details needed for 9-panel story grid:
- Source scene and shot numbers
- One-sentence source summary
- Stable character, costume, prop, and location anchors
- Nine visible story beats
- All required dialogue, OV, voiceover, narration, OS that must survive
- Natural performance notes for major emotions/spoken lines
- Camera and style hints worth preserving
- Explicit warnings against repetition or progressive zoom-only panels

Default `visible_story_beats` arc:
1. Establish space and power relationship
2. Introduce main subject or action
3. Show inciting gesture, line, disturbance, or prop
4. Reveal opposing character, witness, or consequence
5. Change key prop/detail state
6. Show reaction close-up or emotional concealment
7. Escalate conflict or interrupt action
8. Show decision, reversal, or consequence
9. End on hook, freeze-frame, exit, or unresolved image

---

## Nine-Panel Handoff Prompt

When invoking `$nine-panel-video-storyboard`, pass:
```text
Use nine-panel-ai-video-storyboard mode. Do not convert this into a progressive zoom grid.
Bundle ID: <bundle_id>
Source shots: <source_shots>
Source summary: <source_summary>
Continuity anchors: <characters, costume, space, props>
Visible story beats: <exact 9 beats>
Dialogue/OV/VO/OS constraints: <must keep exactly, distribute only if needed, or null>
Natural emotion performance constraints: <emotion cause + facial control + body action + speaking tone for each major reaction/spoken line>
Camera/style hints from source: <only useful hints>
Must not change: <script facts, outline, dialogue, OV, OS, identity, costume, space, prop logic, timeline>
```

If bundle comes from Seedance/video prompt column, extract underlying event first. Phrases like `slow push-in` don't force single-shot mode when story action exists.

---

## Output Shape

```json
{
 "pipeline_type": "split-storyboard-to-nine-panel-batch",
 "source": "split-script-to-storyboard",
 "bundle_count": 0,
 "bundles": [{
   "bundle_id": "S01-B01",
   "source_scene": "S01",
   "source_shots": ["S01-001", "S01-002"],
   "beat_bundle": {},
   "nine_panel_storyboard": {}
 }]
}
```

Each `nine_panel_storyboard` must be valid output from `$nine-panel-video-storyboard` and contain exactly 9 panels.

---

## Quality Checks

- Every source shot assigned to a bundle, or intentionally omitted with reason
- Every bundle contains a visible story event, not only atmosphere or camera direction
- Every bundle can support exactly 9 distinct panels
- No final grid is merely 9 zoom levels of the same moment
- Original script facts, outline, dialogue, OV, OS, identity, costume, spatial layout, prop logic, timeline continuity survive
- Major emotional turns/spoken lines keep natural performance constraints
- Adjacent final panels vary action, prop state, eyeline, framing, or camera relation
- Every final panel includes keys required by `$nine-panel-video-storyboard`

---

## If Source Is Too Long

Process in batches by scene. Output bundle IDs predictably (`S01-B01`, `S01-B02`, `S02-B01`). If content exceeds response budget, finish current scene cleanly and ask user to continue with next scene.

---

## 剧情包模块化设计

**核心规则**：
- 每批剧情包装为五大子技能包：人物资产/场景光影/运镜规则/转场衔接/节奏剪辑
- 冲突节点优先分配到 Panel 03-06；单包至少含1个冲突节点；无冲突过渡包连续不超过2个
- 邻包衔接：前包 Panel 09末帧=后包 Panel 01参考图源，光色K值偏差≤200K
- bundle新增字段：bundle_hierarchy/conflict_node_mapping/character_asset_ids/adjacent_bundle_anchor/action_vector_continuity

> 📖 完整五大子技能包结构、冲突节点标记分发、连贯性校验5维规则、扩展字段schema → `references/bundle-director-standards.md`
