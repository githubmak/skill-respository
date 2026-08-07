# 多人站位面向工程图

本文件说明 `render_blocking_reference.py` 所需的几何规格。是否需要线稿由模型根据空间风险判断，不按人数机械生成。线稿只用于几何审核，不承担创作、美术或 Seedance 参考职责。二维图不能证明站坐支撑、手部接触、道具高度或实际镜头投影；这些问题确实影响成片时，再按需读取 [mannequin-blocking.md](mannequin-blocking.md)，不要逐镜机械生成人偶图。

## 规格原则

- 模型先选人物站位、身体面向、机位、镜头类型、朝向和视场，再填写 JSON；工具不自动选点或移动实体。
- 坐标为画布归一化值 `0-1`；`facing_deg` 为屏幕坐标角度：`0=右、90=下、180=左、270=上`。
- 固定家具用 `solid=true`；墙或隔断用 `blocks_view=true`；门洞和窗口用 `openings` 标出通视区间。
- 每个状态画一台实际机位。正反打可用同一 `blocking_id` 和 `reuse_blocking=true` 复用人物、面向、锚点、障碍、边界与通道，只改变摄影机。
- `shot_type=relationship` 可用 `subjects` 指定实际入镜者；`shot_type=over_shoulder` 填 `foreground_character`、`target_character` 与 `axis_side`。

最小示例：

```json
{
  "shot_group": "S1-04",
  "scene": "门口",
  "states": [{
    "shot_id": "S1-04",
    "blocking_id": "B1",
    "label": "屋内关系镜",
    "anchors": [
      {"label": "木桌", "shape": "rect", "x": 0.76, "y": 0.20, "width": 0.18, "height": 0.10, "solid": true}
    ],
    "boundaries": [{
      "label": "门墙", "side_a": "屋外", "side_b": "屋内",
      "x1": 0.50, "y1": 0.0, "x2": 0.50, "y2": 1.0,
      "blocks_view": true,
      "openings": [{"start": 0.40, "end": 0.60, "label": "门洞"}]
    }],
    "characters": [
      {"name": "人物A", "x": 0.35, "y": 0.50, "facing_deg": 0},
      {"name": "人物B", "x": 0.68, "y": 0.50, "facing_deg": 180}
    ],
    "cameras": [{
      "label": "CAM-A", "shot_type": "relationship",
      "x": 0.25, "y": 0.82, "facing_deg": 315,
      "fov_deg": 48, "subjects": ["人物A", "人物B"], "axis_side": "positive"
    }]
  }]
}
```

按实际项目用具名人物替换示例名，并加入真实锚点。不要为了通过示例而强行使用门墙、关系镜或相同坐标。

## 渲染与审核

```bash
python3 scripts/render_blocking_reference.py <spec.json> --storyboard <计划输出.md> --png --replace --compact --report <reports>/<镜头组>.blocking.json
```

脚本在 Markdown 父目录的 `staging/blocking/` 输出同源 SVG/PNG。失败报告只描述碰撞、净距、遮挡、轴侧、通视、视场或标签错误；模型决定如何修订。提交候选前可运行 `blocking_repair_preflight.py` 核对几何修改范围。

查看 PNG 并确认姓名、方向箭头、机位、视锥、实体与边界清楚后，使用 `promote_blocking_reference.py record` 记录真实画面结论，再用 `promote` 提升。提升后的文件角色仍为 `blocking_geometry_only`，`generation_reference_allowed=false`，不得写入 `【审核后参考素材】`。
