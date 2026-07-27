---
name: storyboard-to-nine-panel-pipeline
description: Bridge and orchestrate full outputs from split-script-to-storyboard into batch nine-panel storyboards. Explicit slash commands include /九宫格, /九宫格剧情包, /剧情九宫格, /批量九宫格, /分镜转九宫格, /剧情包转九宫格, and /剧情包. Use when the user asks for 剧情包, 九宫格剧情节拍包, 分镜转九宫格, batch-convert 分镜脚本 to 剧情九宫格, or feed those beat bundles into nine-panel-video-storyboard. Preserve the original script, outline, dialogue, OV, narration, and OS while only reasonably splitting shots or adding visible details implied by the source.
---

# Storyboard To Nine Panel Pipeline

## Core Use

Convert `$split-script-to-storyboard` output into multiple compact story beat bundles, then use `$nine-panel-video-storyboard` on each bundle to produce strict 9-panel JSON storyboards.

Bridge/orchestration skill — do not replace either source skill. Preserve detailed shot-table information while adapting it into narrative nine-panel grid structure.

Automatically pass through emotion-analysis performance data when source contains speaking characters, reactions, emotional turns, OV/OS: `触发原因→核心情绪→外化控制(6部位)→表演支点`.

每个剧情包对应且只对应一条生成视频：它包含按时间排序的 `1-9` 个静态关键画面，九宫格是优先上限而不是强制凑满。只有在源分镜能支持九个不重复、可见推进的画面时才输出九格；否则输出真实的 `1-8` 格，并说明无法继续扩展的原因。为兼容既有桥接接口，内部仍使用 `video_segments` 数组，但它必须且只能有一个元素，覆盖该包实际输出的全部 Panel，时长为 `4.0-15.0` 秒。

## Required Skill Order

1. Raw script/prose/dialogue/novel/outline → use `$split-script-to-storyboard` first, complete shot table.
2. Existing shot table → parse directly, do not regenerate.
3. Build intermediate beat bundles from shot table.
4. For each beat bundle, use `$nine-panel-video-storyboard` in narrative mode (unless user explicitly asks for single-shot keyframe grid).

> 📖 Bundle schema details → [references/beat-bundle-schema.md](references/beat-bundle-schema.md)
> 📖 Bundle director standards (5 skill packs, conflict mapping, pipeline validation) → [references/bundle-director-standards.md](references/bundle-director-standards.md)

## AI Video Agent Mode Input Adapter

When the source is an already-approved `$ai-video-agent-mode` package, treat it as an authoritative upstream contract, not as raw material for another analysis pass. Accept its existing packet interface without renaming or deleting fields:

```json
{
  "contract_version": "jimeng-t2v-v1",
  "shots": [{
    "shot_id": "S1-01",
    "subshot_id": "S1-01-01",
    "duration": 6.0,
    "full_prompt": "",
    "negative_prompt": "{{NEGATIVE_PROMPT_AUTO_INJECT}}",
    "qa_metadata": {},
    "generation_control": {}
  }]
}
```

- Preserve `contract_version`, `shot_id`, `subshot_id`, `duration`, `full_prompt`, `negative_prompt`, `qa_metadata`, and `generation_control` byte-for-byte in `upstream_source_packet`. Do not regenerate or overwrite approved upstream prompts, contracts, dialogue text, timing, camera instructions, or model controls.
- Consume, rather than re-analyze, these existing facts: `qa_metadata.dialogue_events` for dialogue/OS/OV and delivery; `performance_contract` or `performance_causality` for emotion and body performance; `continuity_contract` for start/end/carryover state; `camera_beat_map` and `full_prompt` for camera; `scene_lock` or source spatial fields for positions, lighting, props, and ambience.
- A detailed source `full_prompt` may contain dialogue, delivery, lip-sync, performance, framing, camera, spatial blocking, audio, ambience, and prop states in one description. Normalize these into bundle fields only for indexing and handoff; the original source text remains the authority and is retained unchanged.
- Only create a patch when a required field is absent, a 4-15 second bundle boundary must be documented, or two approved source shots need an explicit cross-bundle carryover. A patch must name the source field, reason, and affected `panel_id`/`segment_id`; it must never silently replace upstream content.
- Keep `$ai-video-agent-mode` generation mode and platform constraints intact. This pipeline may create static-composition and cross-segment metadata, but it must not insert I2V/R2V/reference-frame fields into the upstream T2V `full_prompt` or `generation_control`.

---

## Source Fidelity Contract

- Only perform reasonable shot splitting, beat grouping, panel expansion, AI formatting. Don't arbitrarily alter script.
- Preserve source plot, outline, timeline, causality, character relationships, dialogue, OV, narration, OS.
- Don't delete required OV/dialogue/OS. Long lines → distribute across bundles/panels preserving wording.
- Long dialogue may cross adjacent剧情包 only at a natural semantic pause, breath, punctuation boundary, or visible performance turn. Preserve wording and meaning; never solve a duration limit by rushing, deleting, or rewriting required dialogue.
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

A bundle is defined by one coherent visible event chain that can be performed as one `4.0-15.0` second video. It may cover part of one source shot or several source shots; do not use a fixed source-shot count.

Create the next bundle before the current bundle exceeds 15 seconds, or when it would contain a second independent dramatic goal, a second main action chain, a second emotional conclusion, or a repeated attention handoff. Cut long dialogue only at a semantic/performance boundary. The next bundle's Panel 01 must inherit the previous bundle's actual final rendered frame.

## Video Segment Rules

- A bundle has exactly one `video_segment`; it is the actual generation unit, not a ninth-story-beat substitute.
- Its `panel_ids` are the complete ordered list of the actual `1-9` output panels, and `duration_seconds` must be in the inclusive range `4.0-15.0`. This is a hard production constraint.
- Prefer nine distinct temporal targets, but never add repeated poses, empty zooms, or invented plot merely to reach nine. Panel 01 is the opening state, the final actual panel is the final state, and only the panels between them are evolving core keyframes. Do not put a second video segment inside the bundle.
- If a source event cannot be spoken and performed naturally inside 15 seconds, split it into the next bundle at a sentence boundary, punctuation pause, turn of address, prop-state change, completed gesture, reaction hold, or shot transition. Do not merge unrelated beats merely to meet a duration.
- `end_frame_anchor` is the actual last rendered frame. It must match the final actual Panel, which is reached `0.3-0.5` seconds before the end and naturally held. The next bundle reproduces it in Panel 01 and holds it for `0.3-0.5` seconds before new motion unless a hard cut is explicitly required.
- Duration includes dialogue, performance pauses, motion, and the end hold. Do not use a uniform speaking rate as a substitute for performance timing.
- For AI Video Agent Mode input, the sole segment carries `source_shot_refs` and `dialogue_fragment_refs`. These point to the preserved `shot_id`/dialogue event and exact original character span; they do not rewrite the source dialogue.

---

## Beat Bundle Construction

For each bundle, extract only details needed for a 1-9 panel story grid:
- Source scene and shot numbers
- One-sentence source summary
- Stable character, costume, prop, and location anchors
- Nine visible story beats
- Per-panel static composition: framing, camera relation, foreground/midground/background, subject screen position, pose/expression, prop state, light, frozen key moment, `static_frame_role`, and `target_timestamp_seconds`
- Per-panel video beat: one visible action chain, one AI-safe camera motion, locked elements, the resulting end state, exact dialogue/OS placement, delivery tone and pause timing, spatial blocking/eyelines, and sound cues
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

For each panel, distinguish the still from the motion: `static_composition` is the image-generation target; `video_description` describes how the single bundle video moves from this panel state to the next. The video description must explicitly include `dialogue_and_tone`, `camera_motion`, `spatial_blocking`, `audio_sfx`, and `generation_constraints`. A panel must advance a visible variable, but it never independently implies a separate video file or fixed duration.

Set the frame roles in this fixed order according to actual `panel_count`:
- Panel 01: `start_reference`, the opening composition and first-generation reference.
- When `panel_count >= 3`, Panel 02 through the penultimate panel: `core_keyframe`, internal high-information states reached in sequence.
- The final actual panel: `end_target`, the composition reached by the final `0.3-0.5s` natural hold and equal to the actual rendered end frame.
- When `panel_count = 1`, Panel 01 is `start_reference_and_end_target`: the same locked composition is both first frame and end target. When `panel_count = 2`, there are no core keyframes.

The sole `video_segment` must contain one `frame_plan` entry per actual panel and an `end_frame_plan` with `mode: match_panel_static`, referencing the final actual panel, with a `0.3-0.5` second natural hold. `continue_after_core_keyframe` is not permitted in this mode.

User-facing Markdown must use Chinese labels only: `起始参考关键帧` for `start_reference`, `核心关键帧` for `core_keyframe`, and `末帧目标关键帧` for `end_target`. The English field names and enum values are internal schema aliases and must not be exposed as the only explanation in a user deliverable.

---

## Nine-Panel Handoff Prompt

When invoking `$nine-panel-video-storyboard`, pass:
```text
Use nine-panel-ai-video-storyboard mode. Do not convert this into a progressive zoom grid.
Bundle ID: <bundle_id>
Source shots: <source_shots>
Source summary: <source_summary>
Continuity anchors: <characters, costume, space, props>
Visible story beats: <actual 1-9 beats; explain reduction_reason whenever fewer than 9>
Panel production requirements: <for every panel: static_composition + static_frame_role + target_timestamp_seconds + video_description + dialogue_and_tone + camera_motion + spatial_blocking + audio_sfx + generation_constraints + start_state + end_state>
Single video plan: <one segment only, actual Panel 01-last, duration_seconds 4.0-15.0, one frame_plan entry per panel, final-panel end_frame_plan, exact dialogue allocation, bundle cut reason, start/end frame anchors>
Dialogue/OV/VO/OS constraints: <must keep exactly, distribute only if needed, or null>
Natural emotion performance constraints: <emotion cause + facial control + body action + speaking tone for each major reaction/spoken line>
Camera/style hints from source: <only useful hints>
Must not change: <script facts, outline, dialogue, OV, OS, identity, costume, space, prop logic, timeline>
Bundle extensions: <bundle_hierarchy, conflict_node_mapping, character_asset_ids, adjacent_bundle_anchor, action_vector_continuity>
Upstream package preservation: <preserved ai-video-agent-mode source packet fields and any explicit patch records>
```

If bundle comes from Seedance/video prompt column, extract underlying event first. Phrases like `slow push-in` don't force single-shot mode when story action exists.

---

## Output Shape

```json
{
 "pipeline_type": "split-storyboard-to-nine-panel-batch",
 "source": "split-script-to-storyboard",
 "upstream_contract": {
   "source_type": "ai-video-agent-mode or shot-table",
   "contract_version": "jimeng-t2v-v1 or null",
   "preservation_policy": "retain approved source packet unchanged",
   "upstream_source_packet": {}
 },
 "bundle_count": 0,
 "bundles": [{
   "bundle_id": "S01-B01",
   "source_scene": "S01",
   "source_shots": ["S01-001", "S01-002"],
   "bundle_hierarchy": "core_layer",
   "conflict_nodes": [],
   "character_asset_ids": {},
   "adjacent_bundle_anchor": {},
   "action_vector_continuity": [],
   "beat_bundle": {
     "panel_count": 9,
     "reduction_reason": null,
     "visible_story_beats": [],
     "panels": [{
       "panel_id": "01",
       "static_composition": "single-frame composition for image generation",
       "static_frame_role": "Panel 01=start_reference; middle panels=core_keyframe; final panel=end_target",
       "target_timestamp_seconds": 0.0,
       "video_description": "visible action chain",
       "dialogue_and_tone": "exact dialogue/OS, speaker, timing, delivery tone, pauses, and mouth-state rules",
       "camera_motion": "one AI-safe camera movement with timing",
       "spatial_blocking": "screen positions, facing, eyelines, distance, foreground/background layering",
       "audio_sfx": "dialogue/OS, ambience, matched action sound, and volume priority",
       "generation_constraints": "locked identity, costume, props, lighting, non-speakers closed-mouth",
       "start_state": "inherited or established visible state",
       "end_state": "visible state handed to the next panel"
     }],
     "video_segments": [{
       "segment_id": "S01-B01-V01",
       "panel_ids": ["01", "02", "03", "04", "05", "06", "07", "08", "09"],
       "duration_seconds": 12.0,
       "frame_plan": [
         {"panel_id": "01", "role": "start_reference", "target_timestamp_seconds": 0.0},
         {"panel_id": "02", "role": "core_keyframe", "target_timestamp_seconds": 1.4},
         {"panel_id": "03", "role": "core_keyframe", "target_timestamp_seconds": 2.8},
         {"panel_id": "04", "role": "core_keyframe", "target_timestamp_seconds": 4.2},
         {"panel_id": "05", "role": "core_keyframe", "target_timestamp_seconds": 5.6},
         {"panel_id": "06", "role": "core_keyframe", "target_timestamp_seconds": 7.0},
         {"panel_id": "07", "role": "core_keyframe", "target_timestamp_seconds": 8.4},
         {"panel_id": "08", "role": "core_keyframe", "target_timestamp_seconds": 9.8},
         {"panel_id": "09", "role": "end_target", "target_timestamp_seconds": 11.6}
       ],
       "end_frame_plan": {"mode": "match_panel_static", "panel_id": "09", "natural_hold_seconds": 0.4},
       "source_shot_refs": ["S01-001"],
       "dialogue_fragment_refs": [{"shot_id": "S01-001", "dialogue_event_ref": "D1", "exact_text_span": ""}],
       "dialogue_exact": "required text assigned to this segment, or null",
       "cut_reason": "semantic/performance boundary",
       "start_frame_anchor": {},
       "end_frame_anchor": {}
     }]
   },
   "upstream_patch_records": [],
   "nine_panel_storyboard": {}
 }]
}
```

Each `nine_panel_storyboard` must be valid output from `$nine-panel-video-storyboard` and contain the same actual `panel_count` (`1-9`) as its beat bundle.

---

## Quality Checks

- Every source shot assigned to a bundle, or intentionally omitted with reason
- Every bundle contains a visible story event, not only atmosphere or camera direction
- Every bundle uses the maximum meaningful number of distinct panels from 1 through 9; `panel_count < 9` requires a concrete `reduction_reason` showing why further visible expansion would repeat, invent, or distort the source
- Every panel contains a static composition plus complete video fields: dialogue/tone, camera motion, spatial blocking, audio/SFX, generation constraints, and distinct start/end state where motion occurs
- Panel 01 is `start_reference`, the final actual panel is `end_target`, and only the intermediate panels are `core_keyframe`; a one-panel package explicitly uses `start_reference_and_end_target`; all have valid increasing target timestamps inside the sole segment
- The sole segment declares one `frame_plan` entry per actual panel and an `end_frame_plan` that uses `match_panel_static` on the final actual panel
- Every bundle has exactly one `video_segment`, it covers every actual Panel 01-last, has an explicit duration, and satisfies `4.0 <= duration_seconds <= 15.0`
- AI Video Agent Mode input preserves all required upstream packet fields unchanged; every derived panel/segment cites its `source_shot_refs`, and every non-source addition is recorded in `upstream_patch_records`
- Every required dialogue/OV/OS fragment is assigned exactly once to its bundle, or is explicitly marked as intentional overlap/reprise with a reason
- Every bundle boundary occurs at a documented semantic or performance cut point; no required dialogue is silently dropped or accelerated to fit
- Each next bundle's Panel 01 and `start_frame_anchor` match the previous bundle's final actual Panel and final rendered `end_frame_anchor`, including pose, expression, hands, props, eyeline, light, and camera relation
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
- 当输出满 9 格时，冲突节点优先分配到 Panel 03-06；少格包将冲突节点置于中部实际 Panel。单包至少含1个冲突节点；无冲突过渡包连续不超过2个
- 邻包衔接：前包唯一视频的最终实际 Panel 渲染末帧=后包唯一视频的 Panel 01 首帧参考图源，光色K值偏差≤200K
- bundle新增字段：bundle_hierarchy/conflict_node_mapping/character_asset_ids/adjacent_bundle_anchor/action_vector_continuity

> 📖 完整五大子技能包结构、冲突节点标记分发、连贯性校验5维规则、扩展字段schema → `references/bundle-director-standards.md`
