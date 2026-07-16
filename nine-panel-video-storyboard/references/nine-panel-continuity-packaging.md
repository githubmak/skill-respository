# 剪辑思维连贯控制（九宫格面板衔接规范）

本规范适用于 `nine-panel-ai-video-storyboard` 模式，在九宫格面板间建立剪辑思维层面的连贯控制，确保AI视频生成后无缝衔接。

## 视觉匹配剪辑三大核心标准

**构图匹配** — 相邻面板在构图元素上保持视觉延续：
- 相邻非留白面板的水平线/地平线在同一垂直高度偏差≤5%
- 主体重心坐标在相邻面板间的位移不超过画面宽度的15%
- 画面引导线（视线、门框、道路、建筑线条）方向在跨面板切换时保持延续性
- 在 `visual_description` 中标注主体坐标位置（如"主体位于画幅左侧1/3处"）

**动作匹配** — 相邻面板间动作矢量统一：
- 连续动作跨面板时，切点卡在动作中点/峰值帧
- Panel N的末帧动作方向与Panel N+1的首帧动作方向偏差≤15°
- 跨面板不间断动作（抬手、转身、行走）在相邻面板的 `ai_motion_control` 中标注动作延续方向
- 在 `narrative_tag` 中标注动作匹配标记："动作匹配：抬手→落定"

**光影匹配** — 全九宫格统一色温、曝光、明暗对比：
- 同一场景内所有面板色温偏差≤200K（主光色温K值在 `visual_description` 中统一标注）
- 曝光值偏差≤±0.3EV（可在 `camera_setup` 中以光圈/ISO参考值标示）
- 跨面板不可出现主光源方向突变；若必须变化（情绪转折），在前一Panel末尾标注"辅光渐变为冷调"作为过渡锚定

## 3D数字人专属帧锚定衔接法（跨段生成面板衔接）

**首尾帧强制复用机制**：
- 当九宫格作为剧情包输出到下一段生成时，Panel 09即为该剧情包的末帧锚定帧
- 下一段生成的首帧（下一九宫格的Panel 01）参考图源 = 前段九宫格的Panel 09画面
- 在JSON输出中增加 `bundle_anchors` 字段（见输出扩展字段）

**12帧缓冲规则（跨剧情包衔接）**：
- 相邻剧情包衔接处保持前后各12帧（约0.4s@30fps）的重叠帧
- 重叠区域内的人物姿态、光影、背景不可改变
- 在 `seedance_full_video_prompt` 中标注衔接锚定："首帧参考图来自前包Panel 09末帧"

**深度信息统一（跨Panel深度空间）**：
- 同一剧情包内所有面板基于同一深度空间逻辑
- `visual_description` 中明确标注前景/中景/背景深度层次（如 "前景：左侧门框阴影；中景：主体跪于中央地毯；背景：烛台壁炉暖光"）
- 人物占画幅比例统一标注（特写70–90%、近景40–60%、中景膝盖以上、全景全身）

## 转场分级内置规则（面板间切换准则）

九宫格面板间转场仅使用以下三种类型，禁止花哨特效转场：

| 转场类型 | 九宫格应用场景 | 参数要求 | 标注格式 |
|---|---|---|---|
| 硬切（默认） | 对话接对话、连续动作接动作、情绪递进 | 切点对齐动作峰值帧或台词重音 | `audio_sfx`中标注"硬切" |
| 淡入淡出溶解 | 时空跳转、情绪大转折、场景切换 | 溶解时长0.3–0.6s | `camera_motion`中标注"Dissolve:0.5s" |
| 遮挡转场 | 肢体/道具/门框遮挡镜头完成场景切换 | 遮挡元素占画面≥60%后切换 | `audio_sfx`中标注"遮挡转场：屏风/衣袖/门框" |

## 节奏剪辑量化规则（九宫格时长分配）

当 `total_duration` 已指定时，按以下公式分配九宫格各面板时长：

- 冲突/台词特写面板：4–5s/面板
- 环境铺垫全景面板：6–8s/面板
- 高光慢镜面板：3–6s
- 过渡空镜面板：2–3s
- 快节奏段落：单面板≤4s
- 慢情绪段落：单面板≥6s

无指定时长时，在 `timestamp` 中使用 `null`，在 `seedance_full_video_prompt` 中标注建议时长区间。

## 剧情包封装扩展（输出字段增补）

在标准九宫格JSON输出中，增加以下扩展字段用于剧情包管线流转。当本技能被`$storyboard-to-nine-panel-pipeline`调用时，必须输出这些字段。

**顶层新增字段**：

| 字段名 | 类型 | 说明 | 填写规则 |
|---|---|---|---|
| bundle_id | string | 剧情包唯一标识 | 如 `S01-B01`，来自pipeline传入的bundle_id |
| source_scene | string | 源场景编号 | 来自pipeline传入的source_scene |
| hierarchy_layer | string | 剧情分层层级 | core_layer / transition_layer / decoration_layer，默认core_layer |
| conflict_nodes | array | 冲突节点标记 | [{panel_id, conflict_type: 钩子/冲突/反转/决策/余韵, target_shot_id}] |
| adjacent_bundle_anchor | object | 相邻包衔接锚定 | {prev_bundle_id, prev_last_panel_id: "09", next_bundle_first_ref} |
| quality_warnings | array | 校验警告列表 | [{dimension: "人物一致性"/"空间连续性"/"光影连续性"/"动作连贯性", severity: "warn"/"error", message: ""}] |

**panel内新增字段**：

| 字段名 | 类型 | 说明 | 填写规则 |
|---|---|---|---|
| hierarchy_level | string | 该面板在剧情分层中的层级 | core / transition / decoration，按剧情包整体分层匹配 |
| character_anchor_id | string | 角色资产锚定ID | 如 女主A_v2，用于AI生成时的IP-Adapter权重绑定 |
| costume_version | string | 服装版本号 | 与split-script阶段保持一致 |
| lighting_ref_id | string | 光影参考图ID | 引用场景光影模块的预设LUT色卡编号 |
| motion_match_note | string | 动作匹配标记 | 如 抬手预备→落定/转身起始→完成/行走中→到位 |
| continuity_anchor_link | string | 帧衔接锚定链接 | 如 "前包末帧=Panel 09，本包首帧复用该帧" |

以上扩展字段在标准JSON输出中与现有panel字段并列，不替换现有字段。

## 连贯性故障校验（剧情包内置校验规则）

输出JSON前，对全九宫格执行以下校验（`quality_warnings`数组记录结果）：

| 校验维度 | 规则 | 校验方法 | 警告条件 |
|---|---|---|---|
| 人物一致性 | 全九宫格角色ID不变，服装版本不变，微表情层级匹配 | 检查所有panel的character_anchor_id一致性 | 任一panel的character_anchor_id不同 → warning |
| 空间连续性 | 相邻panel主光色温偏差≤200K，曝光偏差≤±0.3EV | 解析lighting_ref_id和camera_setup中的色温/曝光信息 | 任一相邻panel色温差>200K → warning |
| 动作连贯性 | 跨panel人物运动矢量方向连续，偏差≤15° | 检查motion_match_note中的动作方向 | 动作方向跳变无过渡 → error |
| 景别梯度 | 相邻非留白panel景别至少差一级 | 比对相邻panel的camera_setup景别字段 | 相同景别连续2个panel → warning，连续3个 → error |
| 构图重复 | 无连续3个panel使用相同构图方式 | 比对camera_setup中的构图法关键词 | 3个及以上panel共享同一构图 → warning |
| 帧锚定完整性 | 跨剧情包衔接时锚定帧可追溯 | 检查adjacent_bundle_anchor的prev_last_panel_id | 锚定帧缺失 → error |

`quality_warnings` 示例：
```json
"quality_warnings": [
  {"dimension": "人物一致性", "severity": "warn", "message": "Panel 04的character_anchor_id=女主A_v1，其余panel=女主A_v2，存在服装版本不一致"},
  {"dimension": "景别梯度", "severity": "error", "message": "Panel 05-07连续3个panel均为特写，需调整Panel 06为中近景"}
]
```
