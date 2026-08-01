# Static And Dynamic Aesthetic Directing Contract

## Contents

- [Scope](#scope)
- [Visual Bible](#visual-bible)
- [Static Frame](#static-frame)
- [Moving Shot](#moving-shot)
- [Aesthetic Review](#aesthetic-review)
- [Failure Controls](#failure-controls)

## Scope

This contract is an internal handoff inside `Master Production`; it is not a new runtime
stage and does not change the T2V-only contract. It prevents continuity rules from replacing
visual direction. Every shot must carry a visual intention, then translate that intention into
visible light, composition, material, and motion evidence.

When the user requests a more beautiful, lively, modern-drama, ancient-game, wuxia, or anti-AI
look, or the source has strong genre evidence, read `../visual-direction-profiles.md`. Resolve one
profile before the Visual Bible, then translate it into scene-specific facts. Style words inside
source dialogue do not activate a profile.

When the user explicitly requests lively/natural motion, a previous output looks mechanical, or
the scene has a usable physical driver, also read `../liveness-motion-grammar.md`. Fold its scene
rhythm, causal chain, phase offsets, and semantic de-duplication into the existing dynamic fields;
do not add schema fields or internal labels to direct-copy text.

Do not use this contract to add adjectives to `full_prompt`. Keep the structured contract in
`qa_metadata`; compile only the few visible facts that serve the current shot into direct-copy
text. Preserve source facts, provenance, validators, and the 700-character hard limit.

## Visual Bible

Create one project/scene visual bible before composing shots. It is the stable source for:

`visual_thesis | palette_system | light_motivation | contrast_exposure |
composition_grammar | material_world | atmosphere_rule | imperfection_policy |
reference_policy | continuity_lock`

Rules:

- `visual_thesis` is one sentence describing what the audience should feel and where the eye
  should settle. Do not write only “电影感/高级感/质感好”.
- `palette_system` assigns a dominant, supporting, and accent color; each color has a screen
  location and a reason to be present. Do not use a color merely because the scene is dramatic.
- `light_motivation` names the physical source, direction, softness, and the surfaces it reaches.
  Kelvin values are secondary evidence, never a substitute for light placement.
- `contrast_exposure` fixes face exposure, shadow density, highlight protection, and the intended
  contrast range. A “clean black” must still retain readable shadow detail.
- `composition_grammar` selects one primary spatial skeleton per scene: doorway, table axis,
  corridor vanishing line, window division, central void, or another source-supported shape.
- `material_world` chooses two or three recurring material responses. Skin, cloth, paper, wood,
  glass, and metal must not all share the same specular response.
- `atmosphere_rule` limits air, haze, rain, dust, and particles to a motivated depth layer and
  a consistent direction. Never add fog or bloom as a generic beauty filter.
- `imperfection_policy` chooses one or two natural irregularities, such as uneven glass marks,
  worn table edges, fabric creases, or broken reflections. It must not become clutter.
- `reference_policy` records whether a style, character, lighting, or composition reference is
  available. References may guide appearance but cannot override source facts.
- `continuity_lock` records the elements that must persist across shots: palette logic, key-light
  direction, exposure baseline, material response, and the scene's composition family.

The visual bible is not copied wholesale into every shot. A shot consumes one thesis fragment,
one composition decision, one light decision, and one or two material/atmosphere anchors.

## Static Frame

For a keyframe, fill `static_aesthetic_contract` with:

`visual_intent | composition_hierarchy | light_design | color_grade | lens_rendering |
depth_atmosphere | material_anchor | signature_frame | aesthetic_exclusions`

Use the following order while composing:

1. State the visual intent and the single audience eye path.
2. Place the primary subject, secondary reaction layer, and background depth anchor.
3. Describe the motivated key/fill/rim relationship and where the light stops.
4. Add lens behavior, focus plane, exposure, and color separation.
5. Add one or two material imperfections that make the world believable.
6. Append hard identity, prop, screen-facing, and physical-continuity facts.

Static-frame rules:

- There is one primary focal subject and at most one secondary visual emphasis. Do not make the
  face, hands, prop, background light, and text all compete for first attention.
- Every lighting statement must name a source, direction, receiving surface, and shadow result.
  “Warm cinematic light” alone is invalid.
- Use a concrete visual consequence for every lens parameter. A 50mm lens must support the stated
  distance and spatial relationship; it is not a quality adjective.
- Keep color effects local. Neon, firelight, moonlight, and practicals may reach the background,
  clothing edge, hair, or a motivated face region, but must leave a readable skin reference.
- State one signature frame: the still image a viewer should remember after the shot. This keeps
  technical constraints from flattening the composition.
- `aesthetic_exclusions` is short and scene-specific. Do not paste a large generic negative list
  into the positive prompt or let negative terms introduce concepts the source never contains.

## Moving Shot

For a T2V shot, fill `dynamic_aesthetic_contract` with:

`motion_thesis | start_state | trigger | primary_subject_motion | secondary_environment_motion |
camera_path | focus_behavior | material_motion | atmosphere_motion | tempo_easing |
end_state | stability_fallback`

Stage motion in three beats:

1. **Start:** establish a readable pose, camera relation, light state, and focus state.
2. **Change:** one source-triggered action or emotional turn changes the visual relationship.
3. **End:** settle on a stable physical and emotional state that can be inherited by the next shot.

Dynamic motion budget:

- one primary subject action;
- one camera path or a deliberate locked camera;
- one causal response chain with at most two low-amplitude, source-coupled responses in low-risk
  shots; keep only one response for long dialogue, multi-character, prop-transfer, complex-support,
  or airborne shots;
- at most one focus handoff;
- no second independent action chain inside the same shot.

Camera movement must have a visual reason: push for pressure or recognition, pull for isolation or
relationship failure, lateral move for a revealed spatial relation, or pan/tilt for a source-driven
target. Specify start, trigger, path, easing, stop, and the anchor that must not drift.

Material motion must respond to the same physical cause as the subject: fabric follows the body,
paper reacts to the hand, reflections shift with the camera, and dust/rain follows wind or impact.
Do not animate every layer at once. The stability fallback removes the camera move first, then the
secondary environment motion, while preserving the story beat and final state.

When a visual profile is active, derive `secondary_environment_motion`, `material_motion`, and
`atmosphere_motion` from its scene-life contract. Preserve one static anchor and use different
response delays across foreground, subject, and background; do not repeat the same slow push,
blink, haze, or fabric movement across adjacent shots.

Across adjacent shots, assign only the needed roles from `hold → initiate → propagate → payoff →
recover`. A peak needs a lower-energy neighbor. Treat paraphrases such as slow push/light push,
small blink/eyelid flutter, and light haze/volumetric ray as the same motion family.

## Aesthetic Review

Export an aesthetic review checklist with every package. The skill does not call, watch, or score
generated media by default and must never fabricate render evidence. Only when the user supplies
real candidates and explicitly requests visual review may the review record `candidate_id`,
`visual_score`, `fact_score`, `motion_score`, `failed_dimensions`, and `reroll_decision`.

Static review dimensions:

- focal hierarchy and composition;
- light direction, contrast, and face exposure;
- color separation and palette continuity;
- depth, atmosphere, and material response;
- signature-frame memorability;
- hard-fact accuracy.

Dynamic review dimensions:

- start/change/end readability;
- motion motivation and easing;
- camera stability and spatial continuity;
- material and atmosphere response;
- identity, anatomy, and prop stability;
- visual payoff at the end state.

Deterministic validation treats the contracts as visible evidence, not descriptive metadata:
`palette_system` assigns at least two color responsibilities and screen locations;
`light_motivation/light_design` state source, direction, receiving surface, and shadow result;
`material_world` distinguishes at least two material families and their response;
`imperfection_policy` keeps one motivated irregularity. In moving shots, at least two of trigger,
primary motion, and stable end state, plus one causal response or deliberate hold, must reach the
model prompt. Non-hold motion must also contain an executable body/eye/weight action and a temporal
cue such as first, later, delayed response, aftershock, deceleration, or stable landing. The export
compiler protects one compact `start → trigger → action → response → end` sentence and one static
light/color/material anchor; it fails rather than silently dropping either when the prompt budget is
too small. Across one scene, three repeated paraphrases from the same liveness family warn and four
fail the episode director audit; four consecutive shots with no semantic motion or performance
change raise a dead-motion warning.

When real review evidence exists, reroll after revising the aesthetic contract if the frame is
factually correct but visually flat, evenly lit, generic, or has no readable focal hierarchy.
Repair hard facts before rerolling when the visual idea is strong but identity, geometry, lip sync,
or prop state is wrong. A high-quality output must pass both gates; do not trade aesthetic score
for continuity score or vice versa.

## Failure Controls

- Do not turn every contract field into a sentence in `full_prompt`; use the information budget.
- Do not use “高级、电影、大片、真实、细腻” as standalone evidence.
- Do not combine multiple color temperatures, fog layers, flares, reflections, camera paths, and
  focus changes unless the source gives each one a job.
- Do not use camera movement to hide missing blocking or handoff geometry.
- Do not let a static keyframe contract prescribe a long dynamic action; keyframes lock states,
  while `dynamic_aesthetic_contract` controls the transition between them.
- Do not make continuity synonymous with total stillness. Keep identity, geometry, prop state,
  light direction, and the end state stable while allowing one motivated residual motion.
- When aesthetic and hard-fact requirements conflict, split the shot or use the stability fallback;
  never silently drop a source fact.
