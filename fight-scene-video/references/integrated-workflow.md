# Integrated Fight Workflow

Use this route for a full fight design. The fight director is the source of truth. Pass concise, locked facts downstream and merge only the fields assigned below.

## State Packet

Before calling a specialist, prepare this packet for the current coverage unit:

```text
scene_lock: fixed anchors, surfaces, light source, legal routes, danger zones
fight_beat: dramatic goal, attacker intent, defender response, changed spatial state
action_vector: start posture -> action path -> contact/near-miss -> force direction -> end posture
ability_lock: declared ability source, effect path, tactical consequence, residue
state_in: character position/body/facing/prop/emotion/screen side; prior camera axis
coverage_role: establish/threat/commitment/reversal/contact/consequence/aftermath
timing: duration, in-cut trigger, out-cut trigger
```

## Specialist Handoffs

### Natural Emotion Performance

Request only visible combat performance: focus, breath, eye line, muscle preparation, hesitation, pain suppression, panic, recovery, or control. Feed back `performance_anchor`. Do not ask it to add dialogue or a separate emotional subplot.

### Frames Analysis

Request the foreground/midground/background arrangement, material response, fixed lighting, character blocking, and action vector. Feed back `frame_lock`: light direction, material terms, spatial layers, position anchors, and end-frame vector. For 3D CG, keep the confirmed 3D CG look; do not inherit its genre-specific default styling.

### Camera Analysis

Request a single shot only. Feed `coverage_role`, `frame_lock`, action vector, axis side, 16:9 format, entry and exit cut triggers. Feed back `camera_lock`: size, angle, lens intent, main move, start/end composition, axis relation, and cut requirement. One camera move per generated clip; rhythm emerges from the sequence of clips.

### Overhead Trajectory Map

Give it only the approved positions, routes, prop lifecycle, camera rail, and fixed anchors. Its result is a staging reference, never a license to change the fight.

### Continuity Ledger

Initialize it once using the fight contract's anchors and initial character states. After every coverage unit, send the actual end state. Copy its `COMPACT_STATE` into the next packet. Treat position jump, silent prop change, unexplained axis cross, and unmotivated emotional jump as blocking issues.

### Audio Design

Run after edit timing locks. Pass visual impact points, materials, power effects, cut points, and silence needs. Use sound to reinforce cause and effect: anticipation breath/charge, attack path, contact, material consequence, and aftermath. Do not use music or camera-whooshes to fake missing action clarity.

### Overhead Map and Jimeng Pair

Keep two prompt outputs for each generated coverage shot:

1. Send the approved movement facts to `overhead-trajectory-map`; preserve its complete image positive prompt and negative prompt under `轨迹图生图提示词`.
2. Render or otherwise approve that map, then let `fight-scene-video` directly assemble the locked shot packet into a Jimeng dynamic positive prompt and a separated, shot-specific negative prompt. Preserve both under `即梦视频生成包`. Do not call `ai-prompt-builder`.

Supply character reference, scene reference, and the matching overhead map to the video-generation workflow when the platform supports reference assets. Do not mention the map's colored routes, labels, circles, or legend in the Jimeng prompt. Translate only their semantic facts: positions, direction, distance, movement, camera path, and end state.

## Merge Gate

Before writing the final video prompt, confirm:

1. `performance_anchor` agrees with body state and force direction.
2. `frame_lock` and `camera_lock` use the same screen positions, axis, light, and key material.
3. The overhead route begins at the continuity state and ends at the ledger's end state.
4. Sound cues land on visible causes and preserve the cut's action match or silence.
5. The overhead-map end state, continuity state, and Jimeng prompt end frame match.
6. The final Jimeng prompt retains the fight beat exactly; it contains no analysis labels, colored-map annotations, or specialist-only metadata.
