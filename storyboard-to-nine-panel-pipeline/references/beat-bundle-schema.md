# Beat Bundle Schema

Use this reference when converting `$split-script-to-storyboard` outputs into intermediate beat bundles.

## Required Object

```json
{
  "bundle_id": "S01-B01",
  "source_scene": "S01",
  "source_shots": ["S01-001", "S01-002", "S01-003"],
  "bundle_title": "short Chinese or English title",
  "source_summary": "one visible-event sentence",
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
  "dialogue_or_vo": "required dialogue, voiceover, OS, or null",
  "camera_style_hints": "lens, angle, rhythm, lighting, transition hints worth preserving",
  "must_not_change": "identity, costume, spatial logic, prop continuity, timeline constraints"
}
```

## Bundle Criteria

A good bundle has:

- One dramatic event or one coherent conflict segment.
- A beginning, turn, and ending image.
- At least five visible changes across the nine beats.
- Stable continuity anchors from the original shot table.
- Clear enough information for `$nine-panel-video-storyboard` to create exactly 9 panels without inventing unrelated action.

## Compression Rules

When the source table is very detailed:

- Merge repeated close-ups into one reaction or detail beat.
- Preserve only camera details that affect story readability or AI generation.
- Keep essential dialogue/VO, but do not let voiceover replace visible action.
- Convert abstract emotion into visible evidence: hands, posture, eye line, distance, prop handling, lighting change.

## Expansion Rules

When the source table is sparse:

- Use the nine-panel minimum arc from SKILL.md.
- Add only logical intermediate beats implied by the source.
- Mark any deliberate blank only when the source truly cannot support nine meaningful panels.

## Repetition Guard

Reject or revise a bundle if its beats can only produce:

- Same subject, same posture, same background, progressively closer.
- Three consecutive panels with no prop, eyeline, position, or action change.
- Camera instructions without story movement.
