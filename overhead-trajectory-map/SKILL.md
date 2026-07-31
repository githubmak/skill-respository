---
name: overhead-trajectory-map
description: "Generate AI-ready combined trajectory reference sheets from a storyboard shot, script beat, shot table row, or AI video prompt: one image containing a top-down orthographic plan-view trajectory map plus a front/elevation trajectory view. Explicit slash commands include /俯视, /俯视轨迹, /正视轨迹, /轨迹俯视图, /俯视轨迹图, /上帝视角, /上帝视角调度图, /人物运动轨迹, /摄像机运动轨迹, /镜头轨迹图, /人物布局图, /调度图, /调度俯视图, and /AI视频调度图. Use when the user asks for 俯视, 正视, 双视图轨迹图, 俯视+正视轨迹图, 轨迹调度参考图, blocking diagram, overhead map, front-view trajectory, camera path reference, AI视频角色位置统一调度参考图, or wants a prompt/spec that creates one combined reference image with a realistic vertical top-down scene base, a front/elevation height-and-depth view, colored dashed character routes, white camera rails, start/end markers, fixed spatial anchors, height markers, and side legends."
---

# 轨迹调度参考图

## 核心用途

把一个分镜、动作节拍、镜头表行或AI视频提示词，转换成一张“组合式调度参考图”：同一张画布内同时包含 `俯视轨迹图` 和 `正视轨迹图`。

- 俯视图负责锁定平面位置：左右、前后、绕行、追逐、障碍、摄像机水平轨道。
- 正视图负责锁定高度关系：站立/跪倒/腾空/落地、跳跃弧线、上下层、遮挡高度、光束或技能的垂直路径。

默认输出中文。不要改变故事动作，只把已有动作翻译成可读的空间调度图。

---

## 输入处理

接受这些来源：分镜行、镜头/动作段落、AI视频提示词、单镜调度输入，或用户明确要求时的相邻镜头序列图。

如果原文缺少精确位置或高度，从剧情逻辑推断可读调度，并标注 `合理推断`。不得新增剧情事件、角色、道具、技能或镜头。

---

## 工作流

1. **提取场景锚点**：地点、北向、平面形状、入口/出口、墙、柱、楼梯、台阶、门窗、桌椅、摊位、车辆、树、地形、可通行动线、禁入区。俯视图必须是严格垂直正交，无地平线、无倾斜鸟瞰。

2. **提取高度锚点**：地面线、台阶/屋檐/墙顶/楼层/平台高度、人物站立高度、腾空最高点、落点、摔倒高度、武器或技能发射高度、遮挡物高度。正视图必须是正交侧向/正向立面示意，不画透视地平线。

3. **提取移动对象**：列出所有可见或与调度相关的人物、动物、车辆、群体或移动道具。使用稳定标签和颜色：`人物1 蓝色虚线`，`人物2 黄色虚线`，`人物3 红色虚线`，`群演 灰色点线`。起点用 S 圆圈，终点用 E 圆圈，路径加箭头。

4. **提取摄像机运动**：同时翻译到俯视图和正视图。

| 运镜类型 | 俯视图表示 | 正视图表示 |
|---|---|---|
| 推镜 | 白色直线轨道，CAM S -> CAM E，箭头指向主体 | 白色水平/轻微纵深轨道，标出镜头高度不变或变化 |
| 拉镜 | 白色直线轨道，箭头远离主体 | 白色水平/纵深轨道，标出主体变小关系 |
| 横移 | 白色侧向轨道，标注左/右方向 | 白色水平轨道，平行于地面线 |
| 跟拍 | 白色轨道跟随人物路线，保持固定偏移 | 白色轨道跟随人物高度变化或地面移动 |
| 环绕 | 白色弧线绕主体，标注顺/逆时针 | 正视图标注“环绕参考，不表现完整圆周”，只标镜头高度与主体距离 |
| 升降 | 白色轨道 + ↑升/↓降标注 | 白色竖向或斜向轨道，明确 CAM S 高度 -> CAM E 高度 |
| 手持微震 | 先画主轨道，再叠加锯齿微震标注 | 同样保留主轨道，再叠加微震 |
| 摇镜/俯仰 | 固定机位点 + 白色视锥 | 固定机位点 + 视线角度线 |
| 固定 | 固定机位点 + 白色视锥 | 固定机位点 + 视线角度线 |

**铁律**：只要出现推、拉、横移、跟拍、环绕、升降或手持移动，就必须画白色实线摄影机轨道。只有纯摇镜、纯俯仰或纯固定，才允许固定机位点加视锥。

5. **设计组合图版式**：同一张画布分成左右双栏或上下双栏，默认左侧/上半是 `俯视轨迹图`，右侧/下半是 `正视轨迹图`。两栏共享同一套角色颜色、S/E编号、摄像机白线和图例。

6. **返回AI可用结果**：包含空间锚点、人物与摄像机调度表、组合图提示词、负面提示词、执行备注。

---

## 必须输出

```markdown
## 双视图轨迹调度参考图｜镜号/场景名

### 场景空间锚点
- 地点：
- 固定平面锚点：
- 高度/层级锚点：
- 可通行动线：
- 禁止穿越区域：

### 人物与摄像机调度
| 对象 | 颜色/线型 | 俯视起点->终点 | 正视高度/前后关系 | 运动轨迹 | 调度目的 |
|---|---|---|---|---|---|

### 双视图AI生图提示词
[一张组合参考图的完整提示词：同一画布内包含俯视轨迹图 + 正视轨迹图]

### 负面提示词
[negative prompt]

### 执行备注
[合理推断、简化、遮挡处理、图例位置、两视图对应关系]
```

---

## 质量规则

- 必须说明 `一张组合式调度参考图`, `left panel top-down plan view`, `right panel front elevation trajectory view`。
- 俯视栏必须指定 `垂直正交纯上帝俯视图`, `orthographic top-down plan view`, `no perspective horizon`。
- 正视栏必须指定 `正视/侧向正交立面轨迹图`, `orthographic front elevation view`, `no perspective depth distortion`。
- 两栏必须共享同一套角色编号、颜色、S/E起终点、箭头和图例。
- 必须包含 realistic full scene base；俯视栏显示平面建筑/地形/家具，正视栏显示地面线、高度层级、墙/柱/平台/楼梯/遮挡物高度。
- 必须包含 colored dashed character trajectories 和白色实线 camera track（有移动运镜时）。
- 必须包含 start/end circles for each moving subject。
- 必须包含 side legend，不遮挡主调度区域。
- 标签要清楚、足够大，避开路线交叉。
- 不改变 story action，只翻译已有调度。

---

## 视觉规范

### 组合图语法

- One combined production blocking reference sheet, split into two synchronized panels.
- Left panel: vertical orthographic top-down plan view, full realistic scene base, no perspective horizon.
- Right panel: orthographic front elevation trajectory view, ground line, height markers, platform/wall/obstacle height, no perspective distortion.
- Same color system in both panels: blue/yellow/red/gray for characters, white for camera.
- Start/end markers and labels must match across both panels.
- Keep legends outside the main paths or along the least important edge.

### 线条系统

- 人物1：蓝色虚线，蓝色 `S1` 和 `E1` 圆圈。
- 人物2：黄色虚线，黄色 `S2` 和 `E2` 圆圈。
- 人物3：红色虚线，红色 `S3` 和 `E3` 圆圈。
- 群演/人群：灰色点线或半透明群体区域。
- 摄像机：白色实线轨道，标注 `CAM S` 和 `CAM E`。
- 固定道具/锚点：黑色或深灰细标签。
- 禁入区：必要时用半透明红色斜线。
- 俯视FOV：需要时用淡白色视锥。
- 正视高度：用淡灰水平高度线或短刻度标注，如 `地面`, `台阶`, `半空最高点`, `落点`。

### 提示词模板

```text
一张组合式AI视频调度参考图，two-panel production blocking reference sheet, left panel is 垂直正交纯上帝俯视图 / orthographic top-down plan view / no perspective horizon, right panel is 正视正交立面轨迹图 / orthographic front elevation trajectory view / no perspective depth distortion, complete realistic [scene/location] base in both panels, [fixed spatial anchors], [height anchors and ground line], overhead/top-down silhouettes and front-view simplified full-body silhouettes of [characters], 人物1 marked with blue dashed trajectory from S1 to E1 in both panels, 人物2 marked with yellow dashed trajectory from S2 to E2 in both panels, circular start and end markers, arrowheads along each path, [camera movement] shown as a white solid camera rail from CAM S to CAM E in both panels when camera moves, synchronized labels across both panels, side legend explaining blue/yellow/red/gray/white route meanings, clean readable Chinese labels, annotations do not cover important scene anchors, realistic ground texture and fixed prop layout, AI video continuity reference sheet
```

### 负面提示词模板

```text
单独一张俯视图, 单独一张正视图, 两张图分离, 倾斜俯拍, oblique aerial view, perspective horizon, first-person view, front-facing portrait only, blank diagram, empty floor plan, missing realistic scene base, missing front elevation panel, missing top-down panel, cropped scene, unreadable labels, overlapping labels, cluttered arrows, same color paths, inconsistent S/E markers between panels, missing start markers, missing end markers, missing camera rail, decorative infographic only, no spatial anchors, no height markers, route lines covering key props, inconsistent scale
```

### 布局推理规则

- 默认保持场景北向；正视图的观看方向要与镜头轴线或最能解释高度/遮挡的方向一致。
- 入口/出口尽量放在俯视图边缘；正视图对应显示门洞、台阶、平台或墙高。
- 权力中心如王座、祭坛、柜台、门、桥、车辆先作为固定锚点，再摆人物。
- 路径绕过障碍，除非剧本明确跨越、跳过、撞碎或穿过。
- 追逐/闪避/犹豫/跟随用弧线；正式逼近/攻击/对峙用直线。
- 正视图必须标出跳跃、坠落、腾空、跪倒、倒地、台阶上下、光束上下倾角。
- 交叉路径用错位虚线和编号箭头。
- 跟拍时白色轨道贴近但不覆盖人物路径。
- 推镜必须画白色实线轨道，不能用固定机位+视锥代替。
- 手持微震必须叠加在主轨道上，不能丢掉主轨。
- 环绕在俯视图画白色弧线，正视图只标镜头高度、主体距离和“环绕参考”。
- 固定/纯摇镜用机位点+视锥或视线角度线。

> 完整视觉规范和更多示例可参考 [references/visual-spec.md](references/visual-spec.md)；若与本文件冲突，以本文件的“双视图同图”规则优先。
