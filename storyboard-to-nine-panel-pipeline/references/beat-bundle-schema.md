# Beat Bundle Schema

Use this reference when converting `$split-script-to-storyboard` outputs into intermediate beat bundles.

## Required Object

```json
{
  "bundle_id": "S01-B01",
  "source_scene": "S01",
  "source_shots": ["S01-001", "S01-002", "S01-003"],
  "upstream_source_refs": [{"shot_id": "S01-001", "subshot_id": "S01-001-01"}],
  "bundle_title": "short Chinese or English title",
  "source_summary": "one visible-event sentence",
  "panel_count": 9,
  "reduction_reason": null,
  "continuity_anchors": {
    "characters": "stable identity, position, posture, relationship distance",
    "costume": "stable costume, hairstyle, makeup, jewelry, wounds, age state",
    "space": "location, screen geography, doors, dais, table, light direction",
    "props": "key objects and their current states"
  },
  "visible_story_beats": [
    "beat 01",
    "beat 02",
    "beat 03",
    "beat 04",
    "beat 05",
    "beat 06",
    "beat 07",
    "beat 08",
    "beat 09"
  ],
  "panels": [
    {
      "panel_id": "01",
      "static_composition": "framing, camera relation, foreground/midground/background, screen position, pose/expression, prop state, lighting, frozen key moment",
      "static_frame_role": "01=start_reference; intermediate=core_keyframe; final=end_target",
      "target_timestamp_seconds": 0.0,
      "video_description": "one visible action chain and timing within the sole bundle video",
      "dialogue_and_tone": "exact dialogue/OS, speaker, timing, delivery tone, pauses, and mouth-state rules",
      "camera_motion": "one AI-safe camera movement with timing",
      "spatial_blocking": "screen positions, facing, eyelines, distance, foreground/background layering",
      "audio_sfx": "dialogue/OS, ambience, matched action sound, and volume priority",
      "generation_constraints": "identity, costume, prop, lighting, non-speaker mouth and motion locks",
      "start_state": "visible state at the beginning of this panel beat",
      "end_state": "visible state delivered to the next panel beat"
    }
  ],
  "video_segments": [
    {
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
      "dialogue_exact": "exact assigned dialogue/OV/OS, or null",
      "cut_reason": "bundle ends at a semantic pause, performance turn, prop-state change, or shot transition",
      "start_frame_anchor": "inherited/established first rendered-frame state",
      "end_frame_anchor": "final rendered-frame state inherited by the next bundle",
      "next_bundle_hold_seconds": 0.3
    }
  ],
  "dialogue_or_vo": "required dialogue, voiceover, OS, or null",
  "camera_style_hints": "lens, angle, rhythm, lighting, transition hints worth preserving",
  "must_not_change": "identity, costume, spatial logic, prop continuity, timeline constraints"
}
```

## Upstream Contract Preservation

When the input originates from `$ai-video-agent-mode`, preserve its `contract_version` and every source-shot field (`shot_id`, `subshot_id`, `duration`, `full_prompt`, `negative_prompt`, `qa_metadata`, `generation_control`) unchanged in the pipeline-level `upstream_source_packet`.

- `upstream_source_refs` identifies the packet entries that own this bundle.
- `source_shot_refs` and `dialogue_fragment_refs` make every segment traceable back to the original prompt and dialogue event.
- Any normalization needed for nine-panel indexing is a non-destructive projection. Any actual addition must be captured as an explicit patch record with source, reason, and affected panel/segment.

## Single-Video Contract

- A panel is a narrative and static-image anchor. It is not an independent video clip.
- Every bundle has exactly one `video_segment`, which is the actual generation unit. `video_segments` remains an array solely for bridge compatibility and must contain exactly one item.
- `panel_count` must be an integer from `1` through `9`; `reduction_reason` is `null` only at 9, otherwise it must concretely explain why another visible panel would repeat, invent, or distort the source.
- The sole segment's `panel_ids` must be exactly `01` through the actual final Panel, in order, and its explicit `duration_seconds` must be from `4.0` through `15.0`, inclusive.
- Preserve long dialogue verbatim across adjacent bundles. Cut only at a natural semantic/performance boundary and document `cut_reason`.
- `end_frame_anchor` must match the final actual Panel and describe the final rendered frame. The following bundle's Panel 01 and `start_frame_anchor` reproduce that state and hold for `0.3-0.5s` before new motion unless the documented transition is a hard cut.
- `static_frame_role` is fixed by actual count: Panel 01=`start_reference`; intermediate panels=`core_keyframe`; final panel=`end_target`. At count 1, Panel 01=`start_reference_and_end_target`; at count 2, no core keyframe exists.
- `frame_plan` has exactly `panel_count` entries with increasing timestamps. `end_frame_plan.mode` must be `match_panel_static`, reference the final actual Panel, and hold naturally for `0.3-0.5s`. `continue_after_core_keyframe` is invalid.

## Bundle Criteria

A good bundle has:

- One dramatic event or one coherent conflict segment.
- A beginning, turn, and ending image.
- At least five visible changes across the nine beats.
- Stable continuity anchors from the original shot table.
- Clear enough information for `$nine-panel-video-storyboard` to create the maximum meaningful 1-9 panels without inventing unrelated action.
- A complete `panels` list whose length equals `panel_count`, and a single compliant 4-15 second `video_segment` plan before generation begins.

## Compression Rules

When the source table is very detailed:

- Merge repeated close-ups into one reaction or detail beat.
- Preserve only camera details that affect story readability or AI generation.
- Keep essential dialogue/VO, but do not let voiceover replace visible action.
- Convert abstract emotion into visible evidence: hands, posture, eye line, distance, prop handling, lighting change.

## Expansion Rules

When the source table is sparse:

- Use as much of the nine-panel arc from SKILL.md as the source supports.
- Add only logical intermediate beats implied by the source.
- When the source cannot support further meaningful panels, stop at the actual count and fill `reduction_reason`; never output deliberate blank panels.

## Repetition Guard

Reject or revise a bundle if its beats can only produce:

- Same subject, same posture, same background, progressively closer.
- Three consecutive panels with no prop, eyeline, position, or action change.
- Camera instructions without story movement.
