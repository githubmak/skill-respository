---
name: overhead-trajectory-map
description: Generate AI-ready top-down orthographic scene trajectory maps from a storyboard shot, script beat, shot table row, or AI video prompt. Explicit slash commands include /俯视, /俯视轨迹, /轨迹俯视图, /俯视轨迹图, /上帝视角, /上帝视角调度图, /人物运动轨迹, /摄像机运动轨迹, /镜头轨迹图, /人物布局图, /调度图, /调度俯视图, and /AI视频调度图. Use when the user asks for 俯视, 俯视轨迹图, 轨迹俯视图, 上帝视角, 上帝视角调度图, 调度图, 人物布局图, 人物运动轨迹, 摄像机运动轨迹, blocking diagram, overhead map, camera path reference, AI视频角色位置统一调度参考图, or wants a prompt/spec that creates a realistic vertical top-down scene base with colored dashed character routes, white camera rails, start/end position circles, fixed spatial anchors, and side legend labels.
---

# Overhead Trajectory Map

## Core Use

Turn one storyboard shot or scene beat into a top-down orthographic trajectory reference map for AI video continuity.

---

## Input Handling

Accept any of these as source: a storyboard row, a shot/beat paragraph, an AI video prompt, or multiple adjacent shots (sequence map only when user asks).

If the source lacks exact placement, infer a readable staging layout from story logic and label it as `合理推断`. Do not invent new plot events or characters.

---

## Workflow

1. **Extract scene anchors**: Identify location type, floor-plan shape, entrances/exits, walls, buildings, counters, tables, stalls, throne/dais, vehicles, trees, props, obstacles, and empty movement lanes. Convert to strict vertical plan: no horizon, no oblique bird's-eye angle.

2. **Extract moving agents**: List every visible/offscreen-relevant character, animal, vehicle, crowd group, or moving object. Give each a stable label and color: `人物1 蓝色虚线`, `人物2 黄色虚线`, `人物3 红色虚线`, `群演 灰色点线`. Mark start with circle+S, end with circle+E; use arrows along the path.

3. **Extract camera movement**: Translate shot's camera move into a top-down camera path using this mandatory mapping:

| 运镜类型 | 俯视图表示 | 说明 |
|---|---|---|
| 推镜 (Push-In / Dolly In) | 白色直线轨道 + 箭头指向主体，CAM S → CAM E | 轨道长度对应推进距离 |
| 拉镜 (Pull-Out / Dolly Out) | 白色直线轨道 + 箭头远离主体 | 从主体近处向后拉远 |
| 横移 (Truck / Crab) | 白色水平直线轨道 + 箭头 | 标注左/右方向 |
| 跟拍 (Follow / Tracking) | 白色轨道紧随人物路线，保持固定偏移 | 与被跟人物路线平行 |
| 环绕 (Orbit / Arc) | 白色弧线围绕主体，标注顺/逆时针 | 标注弧半径和角度范围 |
| 升降 (Boom / Crane) | 白色轨道 + ↑升/↓降标注 | 轨道+箭头+文字标注垂直运动 |
| 手持微震 (Handheld / Shake) | 白色轨道 + 锯齿抖动标注线 | 微震是叠加效果——主轨仍按运镜类型绘制 |
| 摇镜 (Pan / Tilt) | 固定机位 + 白色扇形视锥 | 机位不移动，仅旋转 |
| 固定 (Locked-Off / Static) | 固定机位点 + 白色视锥 | 仅当确认无任何相机运动时使用 |

**关键铁律**：只要运镜描述中出现"推/拉/横移/跟拍/环绕/升降/手持"中的任何一个，就必须画白色轨道。固定机位+视锥 ONLY for 纯摇镜 or 纯固定。

4. **Design the overhead map**: Keep a complete realistic scene base visible underneath annotations. Preserve fixed spatial anchors for AI video continuity reuse. Keep annotation lines layered and readable. Use side legend text to explain color meanings, line styles, markers, and camera rail.

5. **Return an AI-ready result**: Default to Chinese output. Include layout summary, trajectory table, and one master image prompt. Add negative prompt preventing oblique views, cluttered labels, missing scene base, cropped space, and confusing route colors.

---

## Required Output

```markdown
## 轨迹俯视图方案｜镜号/场景名

### 场景空间锚点
- 地点：
- 固定锚点：
- 可通行动线：
- 禁止穿越区域：

### 人物与摄像机调度
| 对象 | 颜色/线型 | 起点 | 终点 | 运动轨迹 | 调度目的 |
|---|---|---|---|---|---|

### 俯视图AI生图提示词
[完整提示词]

### 负面提示词
[negative prompt]

### 执行备注
[合理推断、简化、遮挡处理、图例位置等]
```

---

## Quality Rules

- 必须指定 `垂直正交纯上帝俯视图`, `无倾斜镜头`, `orthographic top-down plan view`, `no perspective horizon`
- 必须包含 realistic full scene base（非 blank schematic unless user asks）
- 必须包含 colored dashed character trajectories + white solid camera track（when camera motion exists）
- 必须包含 start/end circles for each moving subject
- 必须包含 overhead full-body silhouettes or simplified top-down human figures
- 必须包含 fixed buildings, stalls, furniture, doors, props, or terrain anchors
- 必须包含 side legend explaining each route without covering the main scene
- 标签clean, large enough, separated from route intersections
- 不改变 story action——only translate existing staging into readable top-down plan

---

## Embedded Visual Spec

### Image Grammar
- Vertical orthographic top-down view, pure god-view plan, no perspective tilt
- Full realistic scene base: architecture, floor texture, stalls, furniture, props, doors, walls, vehicles, trees, terrain
- Top-down full-body silhouettes or simplified overhead human figures
- Colored dashed lines for character movement. White solid line for camera movement
- Arrowheads showing direction. Circular start/end markers for each moving subject
- Side legend outside or along least important edge

### Line System
- 人物1: blue dashed route, blue `S1` and `E1` circles
- 人物2: yellow dashed route, yellow `S2` and `E2` circles
- 人物3: red dashed route, red `S3` and `E3` circles
- 群演/人群: gray dotted route or translucent group zone
- 摄像机: white solid rail with `CAM S` and `CAM E`
- Fixed props: thin black or dark-gray labels
- Forbidden zones: translucent red hatch only when useful
- FOV: faint white wedge if camera direction matters

### Prompt Pattern
```
垂直正交纯上帝俯视图，orthographic top-down plan view, no perspective horizon, complete realistic [scene/location] base map, [fixed spatial anchors], overhead full-body silhouettes of [characters], [character 1] marked with blue dashed movement trajectory from S1 to E1, circular start and end markers, arrowheads along the path, [character 2] marked with yellow dashed movement trajectory from S2 to E2, [camera movement] shown as a white solid camera rail from CAM S to CAM E with arrowheads, side legend explaining blue/yellow/white route meanings, layered production blocking annotations, clean readable Chinese labels, annotations do not cover important scene anchors, realistic ground texture, fixed building/stall/prop layout, AI video continuity reference map
```

### Negative Prompt Pattern
```
倾斜俯拍, oblique aerial view, perspective horizon, first-person view, front-facing character portrait, blank diagram, empty floor plan, missing realistic scene base, cropped scene, unreadable labels, overlapping labels, cluttered arrows, same color paths, missing start markers, missing end markers, missing camera rail, decorative infographic only, no spatial anchors, route lines covering key props, inconsistent scale
```

### Layout Reasoning Rules
- Keep scene north-up unless source defines more important orientation
- Place entrances/exits on map edges when possible
- Place power centers (throne/daïs/altar/desk/gate/stall) as fixed anchors before placing characters
- Draw routes around obstacles unless script says crosses/jumps/crashes/breaks
- Curved paths for chase/avoidance/hesitation/following; straight paths for formal approach/command/attack/confrontation
- Short route segments for subtle body shifts; don't exaggerate small gestures
- Offset dashed lines + numbered arrows for crossing paths
- Camera following character: keep white rail near but not on top of colored route
- Push-in must have white solid rail with arrowhead toward subject — NEVER fixed position+view wedge
- Handheld shake = overlay on primary rail — never drop the rail
- Orbit = white arc around subject + clockwise/counterclockwise label
- Locked-off/static = camera point + view wedge instead of rail

> 📖 完整视觉规范展开 + 更多提示词示例 → [references/visual-spec.md](references/visual-spec.md)
