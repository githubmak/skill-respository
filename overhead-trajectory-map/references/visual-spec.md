# Visual Specification

Use this reference when generating a full prompt or detailed layout for a trajectory overhead map.

## Image Grammar

The image must read as a production blocking reference, not as a beauty still.

Required visual structure:

- Vertical orthographic top-down view, pure god-view plan, no perspective tilt.
- Full realistic scene base: architecture, floor texture, stalls, furniture, props, doors, walls, vehicles, trees, terrain, or palace structures.
- Top-down full-body silhouettes or simplified overhead human figures at start/end positions.
- Colored dashed lines for character movement.
- White solid line for camera movement.
- Arrowheads showing direction of travel.
- Circular start and end markers for each moving subject.
- Side legend outside or along the least important edge of the scene.
- Annotation layers clear enough to guide AI video generation.

## Recommended Line System

- 人物1: blue dashed route, blue `S1` and `E1` circles.
- 人物2: yellow dashed route, yellow `S2` and `E2` circles.
- 人物3: red dashed route, red `S3` and `E3` circles.
- 群演/人群: gray dotted route or translucent group zone.
- 摄像机: white solid rail with `CAM S` and `CAM E`.
- Fixed props/anchors: thin black or dark-gray labels.
- Forbidden/blocked zones: translucent red hatch only when useful.
- Field of view: faint white wedge if the camera direction matters.

## Prompt Pattern

Use this structure and fill only what the source supports:

```text
垂直正交纯上帝俯视图，orthographic top-down plan view, no perspective horizon, complete realistic [scene/location] base map, [fixed spatial anchors], overhead full-body silhouettes of [characters], [character 1] marked with blue dashed movement trajectory from S1 to E1, circular start and end markers, arrowheads along the path, [character 2] marked with yellow dashed movement trajectory from S2 to E2, [camera movement] shown as a white solid camera rail from CAM S to CAM E with arrowheads, side legend explaining blue/yellow/white route meanings, layered production blocking annotations, clean readable Chinese labels, annotations do not cover important scene anchors, realistic ground texture, fixed building/stall/prop layout, AI video continuity reference map
```

## Negative Prompt Pattern

```text
倾斜俯拍, oblique aerial view, perspective horizon, first-person view, front-facing character portrait, blank diagram, empty floor plan, missing realistic scene base, cropped scene, unreadable labels, overlapping labels, cluttered arrows, same color paths, missing start markers, missing end markers, missing camera rail, decorative infographic only, no spatial anchors, route lines covering key props, inconsistent scale
```

## Layout Reasoning Rules

- Keep the scene north-up unless the source defines a more important orientation.
- Place entrances and exits on map edges when possible.
- Place power centers such as throne, dais, altar, office desk, gate, or market stall as fixed anchors before placing characters.
- Draw routes around obstacles unless the script says a character crosses, jumps, crashes through, or breaks them.
- Use curved paths for chase, avoidance, hesitation, or following action; use straight paths for formal approach, command, attack, or direct confrontation.
- Use short route segments for subtle body shifts; avoid exaggerating a small gesture into a long walk.
- If multiple characters cross paths, offset dashed lines slightly and use numbered arrows.
- If the camera follows a character, keep the white rail near but not on top of that character's colored route.
- If the shot is a push-in (dolly-in), draw a white solid rail with arrowhead toward the subject — mandatory rail, not optional. Push-in physically moves the camera, so a fixed position is NEVER correct.
- Handheld shake is an overlay on the primary movement rail — never drop the rail because of handheld. Draw the main trajectory as white solid, then annotate ±Xpx vibration marks alongside.
- If the shot is an orbit, draw a white arc around the subject and label clockwise/counterclockwise.
- If the shot is locked-off (static, no movement at all, or pure pan/tilt rotation), draw a camera point and view wedge instead of a rail.
