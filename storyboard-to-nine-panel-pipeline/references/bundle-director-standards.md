# 剧情包模块化导演设计规范（剧情包标准化分层）

本技能作为bridge层，负责将分镜输出转化为标准化剧情包，必须遵循以下模块化设计规范。

## 剧情包五大可复用子技能包结构

将分镜表内容按以下五大模块提取并打包，确保每批剧情包可直接喂入`$nine-panel-video-storyboard`：

| 子技能包 | 源数据（来自分镜表） | 剧情包输出格式 | 复用规则 |
|---|---|---|---|
| 人物资产模块 | 角色ID、服装版本、姿态控制源ID、3D数字人动作/微表情、IP-Adapter权重 | 角色一致性锚定卡：多视图参考图ID + 微表情层级 + 服装版本映射 | 跨剧情包共享基础角色资产，每换场景只更新服装版本 |
| 场景光影模块 | 光影参考图ID、叙事层级、景别、场景空间描述 | 场景光影参数卡：GS底模参考 + 主光色温K值 + LUT色卡ID + 景深区间 | 同场景跨剧情包共享，不同场景分段切换时标注场景切换点 |
| 运镜规则模块 | 运镜详述、镜头角度/焦段、运镜量化参数 | 运镜指令卡：推拉速度值 + 环绕半径 + 跟拍偏移 + 焦点距离 | 按叙事类型（对话/动作/情绪）预设调用，同一剧情包内运镜风格统一 |
| 转场衔接模块 | 转场类型、衔接前置帧、12帧缓冲范围、动作匹配标记 | 转场参数卡：转场类型 + 溶解时长 + 遮挡元素ID + 帧锚定重叠区间 | 按冲突等级自动匹配转场类型，硬切默认、遮挡转场仅用于场景切换 |
| 节奏剪辑模块 | 节奏权重、镜长、BPM关联、冲突节点 | 节奏剪辑参数卡：镜长分配公式 + BPM绑定规则 + 景别梯度切换序列 | 按快节奏/慢情绪段落切换剪辑模板，冲突节点自动出节奏重音 |

## 冲突节点标记与分发机制

**剧情包内冲突节点标记**：在从分镜表生成beat bundle时，提取并保留冲突节点信息：

- 所有剧情转折点、反转点、钩子点关联原始镜头ID
- 在bundle结构中增加 `conflict_nodes` 字段，标记每个冲突节点对应的九宫格面板编号
- 冲突节点按类型匹配转场逻辑：钩子→硬切+音效冲击；反转→慢镜头+溶解过渡；决策→定格+呼吸留白

**剧情包间衔接锚定**：
- 相邻剧情节包的末帧/首帧共享同一锚定帧（前包Panel 09画面 = 后包Panel 01参考图源）
- 在bundle结构中增加 `adjacent_bundle_anchor` 字段，指向相邻包的衔接帧ID
- 空间坐标连续性：打包时检查相邻包的光影参数K值偏差≤200K、场景底模ID一致

**冲突节点在九宫格中的分发规则**：
- 单剧情包内至少包含1个冲突节点
- 冲突节点优先分配到Panel 03–06（核心叙事区域）
- 冲突节点对应的九宫格面板自动标注一级优先级（核心层）
- 无冲突的过渡包最多连续2个（2包后必须插入核心冲突包）

## 剧情包管线连贯性校验（打包前Validate）

在生成beat bundle并喂入`$nine-panel-video-storyboard`前，执行以下自动化校验：

| 校验维度 | 规则 | 通过条件 |
|---|---|---|
| 人物一致性 | 同角色在不同包中的角色ID、服装版本、微表情层级一致 | 无冲突包间偏差 |
| 空间连续性 | 相邻包的光影参数K值偏差、场景底模ID一致 | K值≤200K偏差，底模ID相同 |
| 动作连贯性 | 跨包人物运动矢量方向、行进速度连续 | 运动方向偏差≤30°，速度偏差≤20% |
| 冲突分布 | 连续无冲突包不超过2个 | 每3包内至少1个含冲突节点 |
| 帧锚定连续性 | 前包末帧=后包首帧参考图 | 锚定帧ID可追溯 |

校验不通过时，在beat bundle备注中标注警告信息，并在输出JSON的 `quality_warnings` 数组中记录。

## 剧情包扩展字段（handoff prompt新增）

在标准handoff prompt基础上，增加以下字段用于三层技能联动：

| 扩展字段 | 类型 | 填写规则 |
|---|---|---|
| bundle_hierarchy | string | core_layer/transition_layer/decoration_layer，按剧情分层优先级匹配 |
| conflict_node_mapping | array | [{beat_index: 1-9, conflict_type: 钩子/冲突/反转/决策/余韵, source_shot_id}] |
| character_asset_ids | object | {角色ID: {costume_version, pose_source_id, lighting_ref_id}} |
| adjacent_bundle_anchor | object | {prev_bundle_id, prev_last_shot_id, anchor_type: 末帧复用/动作匹配/空间过渡} |
| action_vector_continuity | array | [{character_id, motion_direction, motion_speed, source_shot_range}] |

## 输出格式扩展

更新输出JSON schema，在顶层增加剧情包管线所需字段：

```json
{
  "pipeline_type": "split-storyboard-to-nine-panel-batch",
  "source": "split-script-to-storyboard",
  "bundle_count": 0,
  "total_shot_count": 0,
  "bundles": [
    {
      "bundle_id": "S01-B01",
      "source_scene": "S01",
      "source_shots": ["S01-001", "S01-002"],
      "bundle_hierarchy": "core_layer",
      "conflict_nodes": [],
      "character_asset_ids": {},
      "adjacent_bundle_anchor": {},
      "action_vector_continuity": [],
      "beat_bundle": {},
      "nine_panel_storyboard": {},
      "quality_warnings": []
    }
  ]
}
```

## 校验规则扩展

在原有Quality Checks基础上增加：

- 每个bundle的 `bundle_hierarchy` 与其内部conflict_nodes数量匹配（core_layer至少含1个冲突节点）
- 相邻bundle的character_asset_ids中的角色ID和服装版本一致
- 相邻bundle的action_vector_continuity中的运动方向偏差≤30°
- 无冲突节点（decoration_layer）的bundle连续不超过2个
- 所有bundle的adjacent_bundle_anchor形成可追溯的锚定链（首包→末包闭环）
