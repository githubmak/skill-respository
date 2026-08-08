# PyVista/VTK 三维骨架人偶空间审核

只在二维站位图不能证明站坐支撑、躯干与头部朝向、左右手接触、道具高度、前后遮挡或实际机位投影时使用。模型先完成全部调度与摄影机创作，再把决定写入数据；Python 工具只验证合同、计算几何、离屏渲染、标注和落盘，不自动摆人、选姿态、改机位或修提示词。每个状态必须显式填写来源 Markdown 镜号 `shot_id`，同一物理状态的第二机位也重复该镜号。

当前默认渲染档为 `proxy_v3_neutral`：使用中性工程材质、无综合色偏的白光和中性灰环境。audit 图保留姓名、身份色、头部朝向楔标、视线与接触；clean 图隐藏头部楔标和审计标注，避免把代理鼻形、PBR材质或戏剧灯光带入 Seedance。人物仍是低模空间代理，只承担空间、机位、姿态和接触职责。

## 状态与复用

- 继续使用 `blocking-facing-reference.md` 的同一份 JSON，只给顶层、人物、锚点和摄影机增加 `mannequin`。
- 人物位置、身体/头部朝向、站坐、视线、左右手目标、锚点尺寸/高度或边界改变，才建立新物理状态。
- 同一镜内的人物物理状态确实发生关键变化且需要参考时，使用相同 `shot_id` 的两个状态并分别填写 `physical_phase=start`、`physical_phase=end`；两者使用不同 `blocking_id`，且至少一项人物位置、身体/头部朝向、视线、站坐或接触必须真实改变。单一静态状态省略该字段或写 `static`。
- 只有摄影机改变时使用相同 `blocking_id` 和 `reuse_blocking=true`。每个镜头必须绑定明确的 `camera_index`，不得把首个机位当作通用默认机位。
- `physical_phase=start|end` 状态不得再包含 camera `path`。人物与摄影机都需要首尾变化时，直接把起点机位写在 start 状态、终点机位写在 end 状态；若中间路径仍决定剧情，优先拆镜或使用用户已有且通过审核的参考视频。
- 相同物理状态按内容哈希去重。多机位共用一份物理场景，但每个机位分别生成 clean 图；没有状态或机位变化的相邻镜复用已审核图片。

最小扩展示例：

```json
{
  "mannequin": {
    "world_width_m": 8,
    "world_depth_m": 6,
    "floor_color": "#26333b",
    "background_color": "#0d151d"
  },
  "states": [{
    "shot_id": "S1-04",
    "blocking_id": "B1",
    "anchors": [{
      "label": "餐桌", "shape": "rect", "x": 0.50, "y": 0.42,
      "width": 0.42, "height": 0.18, "solid": true,
      "mannequin": {"kind": "table", "height_m": 0.76, "color": "#704a30"}
    }],
    "characters": [{
      "name": "阿丰", "x": 0.36, "y": 0.66, "facing_deg": 270,
      "mannequin": {
        "height_m": 1.18, "posture": "standing",
        "head_facing_deg": 285, "identity_color": "#4f9f90",
        "gaze_target": "餐桌",
        "hand_targets": {"right": {"anchor": "餐桌", "height_m": 0.80}}
      }
    }],
    "cameras": [{
      "label": "CAM-A", "x": 0.50, "y": 0.94,
      "facing_deg": 270, "fov_deg": 55,
      "mannequin": {"height_m": 1.35, "look_height_m": 1.05}
    }]
  }]
}
```

人物 `mannequin` 必填 `height_m`、`posture=standing|sitting`、`identity_color`。人物顶层 `facing_deg` 表示双脚/躯干平面朝向；`head_facing_deg` 默认与身体同向，只有头身分离时才单独填写；`gaze_target` 可指人物或锚点。`hand_targets.left/right` 每只手只能指一个 `anchor` 或 `character`，`height_m` 始终表示从地面起算的世界绝对接触高度，不能再叠加锚点 `elevation_m`。目标到肩部超过按人物身高计算的手臂可达范围时硬阻断，不再拉长前臂伪造接触。锚点 `kind` 支持 `box/table/bench/bowl/door/marker`。摄影机可写 `height_m` 与 `look_height_m`。

## 离屏渲染

运行：

```bash
python3 scripts/render_mannequin_reference.py <blocking.json> \
  --storyboard <计划输出.md> --replace --compact \
  --report <reports>/<镜头组>.mannequin.json
```

本机 Python 必须可导入 `vtk`、`pyvista`、`PIL` 与 `numpy`。脚本不联网也不自动安装依赖；缺失时只报告事实。它通过 PyVista/VTK 离屏相机直接在 `staging/mannequin/` 写出 1920×1080、16:9 图片，Pillow 只给 audit 图增加审核文字。同一物理状态每种模式只构建一次场景，多机位复用几何；完全相同的状态/机位/姿态只渲染一次，其余镜号使用同内容硬链接。流程不创建 HTML、HTTP 服务、浏览器任务或 WebGL 运行时。

每个 `camera_index` 都输出：

- `*_审核.jpg`：具名人物、身份色、站坐、面向、视线、接触、锚点、摄影机和状态信息，用于工程核对。
- `*.jpg`：同源低模人物代理的实际透视机位画面，隐藏姓名、网格、视线、摄影机模型和审核文字，可在通过视觉审片后作为空间/动作参考。
- 摄影机有 `path`，或同镜人物使用 `physical_phase=start|end` 时，分别输出 `*_start_审核.jpg`、`*_start.jpg`、`*_end_审核.jpg`、`*_end.jpg`；完全静态状态不加 start/end。

报告中的 `screenshots` 是已经落盘的文件映射，不是待执行截图指令。投喂文件名固定为 `镜头号_即梦_3D_空间关系.jpg`；有摄影机路径时使用 `_start` 与 `_end`，状态与机位索引只保留在报告中。同一物理状态的多个镜号可复用场景，但每个镜号、机位与姿态仍保留可审计映射。

## 真实画面审核与提升

模型必须逐张查看报告映射的 audit 与 clean 图。先核对身份、站坐、身体/头部朝向、视线、左右手接触、锚点高度和边界；再核对实际机位中的人物数量、前后层次、遮挡、可见面、支撑、接触、景别和构图。文件存在、尺寸正确和非空像素不能代替视觉审片。

```bash
python3 scripts/promote_mannequin_reference.py record \
  --render-report <reports>/<镜头组>.mannequin.json \
  --screenshot-dir <输出目录>/staging/mannequin \
  --decision PASS --finding <视觉结论> \
  --review <reports>/<镜头组>.mannequin.review.json \
  --compact --report <reports>/<镜头组>.mannequin.record.json

python3 scripts/promote_mannequin_reference.py promote \
  --review <reports>/<镜头组>.mannequin.review.json \
  --delivery-dir <正式目录>/approved-mannequin \
  --compact --report <reports>/<镜头组>.mannequin.promote.json
```

只有双审 PASS 的 clean 图会被提升。audit 图继续留在 `staging/`。提升后的角色是 `mannequin_spatial_action_reference`；投喂文字同时写明身份色映射和“不参考人物外貌、服装、材质、光影”。

## 创意边界

VTK/Pillow 只执行模型已经明确的数据。不得根据关键词、碰撞报告、构图分数或固定阈值自动选站位、姿态、手部目标、镜头、景别或运镜；客观几何失败返回事实，由模型重新设计。渲染器的稳定输出、状态复用和批量落盘属于工程能力，不缩小模型的创意范围。
