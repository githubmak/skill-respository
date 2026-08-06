# 多人站位面向线稿

本文件只处理俯视站位、身体面向、场景边界、实体遮挡和摄影机视锥。`scene_contract.json -> blocking spec -> SVG/PNG -> 直接提示词` 单向派生；不得先写提示词再凭文字猜坐标。SVG供工程核对，同源PNG作即梦空间参考；姓名、箭头、CAM和视锥都是控制标注，不是最终画面元素，也不约束人物造型、表演、光影或美术风格。

## 触发与顺序

- `off`：不生成；`auto`：两人及以上清晰互动镜头组生成；`required`：所有两人及以上同框镜头组生成。命中后失败阻塞交付。
- 先完成关系投影、导演镜头类型选型和文字空间合同，再建立JSON；线稿通过后才编译提示词。
- 同一物理站位可复用规格，但每个正式镜头组单独导出。一个稳定状态/机位一个面板，每个面板恰好一台实际机位，不画运动轨迹。
- 正反打用同一 `blocking_id` 的两个面板：人物坐标、身体面向、锚点、实体障碍、边界和通道完全相同，只更换前景人物与摄影机。

## 镜头与几何门禁

导演先比较 `侧面双人关系镜 | A肩后看B | B肩后看A`。关系镜建立距离、隔物和出口；肩后镜突出施压、接收或反应。镜头类型与机位坐标都属于导演判断，脚本只验证或拒绝已选坐标。

- `shot_type=relationship`：显式写机位坐标、方向、视场和实际入镜 `subjects`。
- `shot_type=over_shoulder`：写前景、目标、导演选定的 `x/y/facing_deg` 和 `axis_side`；脚本只校验近肩距离、轴侧、遮挡与视场，不替导演求机位。正反打保持同一 `axis_side`。
- 人物必须真实面对对方；`正面可见` 不等于面向镜头。摄影机只能改变投影，不能改变人物站位、门内外或真实体型。
- 摄影机须有站立空间；前景肩线只擦过视线边缘，不能贴后脑或挡住目标；声明主体完整落入视锥并留边。
- 家具等不可穿越物写 `solid=true`；墙/隔断写 `blocks_view=true`，门洞/窗口用 `openings`。人物、机位不得与实体重叠，视线不得穿墙或家具，跨墙拍摄只能通过声明通道。

## JSON规格

坐标均为画布归一化值 `0-1`；`facing_deg` 为屏幕坐标：`0=向右、90=向下、180=向左、270=向上`。以下示例表示沈青乔在门外、卫景耘在屋内，双方相向；同一站位完成一组近肩正反打：

```json
{
  "shot_group": "S1-04",
  "scene": "门口",
  "states": [
    {
      "blocking_id": "B1",
      "label": "卫景耘肩后看沈青乔",
      "anchors": [
        {"label": "屋内边桌", "shape": "rect", "x": 0.78, "y": 0.20, "width": 0.18, "height": 0.10, "solid": true}
      ],
      "boundaries": [
        {"label": "门墙", "side_a": "门外", "side_b": "屋内", "x1": 0.50, "y1": 0.0, "x2": 0.50, "y2": 1.0, "blocks_view": true,
         "openings": [{"start": 0.40, "end": 0.60, "label": "门洞"}]}
      ],
      "characters": [
        {"name": "沈青乔", "x": 0.30, "y": 0.50, "facing_deg": 0},
        {"name": "卫景耘", "x": 0.70, "y": 0.50, "facing_deg": 180}
      ],
      "cameras": [
        {"label": "CAM-A", "shot_type": "over_shoulder", "x": 0.82, "y": 0.56, "facing_deg": 174, "foreground_character": "卫景耘", "target_character": "沈青乔", "axis_side": "positive"}
      ]
    },
    {
      "blocking_id": "B1",
      "label": "沈青乔肩后看卫景耘",
      "reuse_blocking": true,
      "cameras": [
        {"label": "CAM-B", "shot_type": "over_shoulder", "x": 0.18, "y": 0.56, "facing_deg": 6, "foreground_character": "沈青乔", "target_character": "卫景耘", "axis_side": "positive"}
      ]
    }
  ]
}
```

首个状态至少写一个真实固定锚点、两名具名人物和一台机位。后续同 `blocking_id` 的正反打面板用 `reuse_blocking=true` 确定性复用人物、面向、锚点、障碍、边界和通道，不得同时覆盖这些字段。`anchors.shape` 只用 `rect|ellipse|line`。双侧边界必须写 `side_a/side_b`；`openings.start/end` 是沿边界起点至终点的比例。近肩默认只校验目标；关系镜默认校验全员，也可用 `subjects` 限定真实入镜者。渲染器自动标注机位为正向/斜向并校验完整视场。

## 导出与使用

```bash
python3 scripts/render_blocking_reference.py <spec.json> --storyboard <计划中的Markdown路径> --png --replace --compact --report <reports>/<镜头组>.blocking.json
```

- 脚本只在 Markdown 父目录下的 `staging/blocking/` 同源输出精确命名的 `S1-04.svg` 与 `S1-04.png`；`--replace` 只重生成当前镜头号文件，不生成 `-v2/-v3`。脚本发现参数、边界净距、视锥或标签碰撞错误时只返回事实，不自动移动人物、摄影机或标签。模型完成创意修订并通过 `blocking_repair_preflight.py` 后重渲染；真实画面 PASS 再用 `promote_blocking_reference.py` 提升。
- PNG作为即梦空间控制参考时，直接提示词仍须重写当前人数、站位、身体面向、门内外、机位和真实背景，并说明图中文字/箭头/CAM/视锥仅供空间控制、成片不出现。
- 最终交付列出两类文件路径；不得把SVG源码、JSON或线稿解释写入即梦直接提示词。
