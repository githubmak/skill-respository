# xlsx与数据结构

## 路径契约

用户必须在任务开始时提供最终导出目录 `export_dir`。所有文件写入均限定在该目录：

- 最终xlsx：`{export_dir}/`
- 单镜成品：`{export_dir}/prompts/`
- 分析JSON、切片、预览、校验结果与日志：`{export_dir}/.split-storyboard-cache/`

禁止使用技能目录、系统临时目录、默认桌面或当前工作区作为隐式回退路径。调用生成脚本时必须显式传入 `--output-dir "{export_dir}"`。

## 五个工作表

1. `视觉规范表`：全剧规范库、角色库、场景库、光影策略
2. `分镜表`：每行一个主叙事单元；含时长、组织模式、景别/运镜摘要、构图、表演、动作、台词、光影、子分镜、校验
3. `子画面表`：按时间顺序列子镜头/阶段与关键帧
4. `单镜提示词`：当前场景前缀、时间化动态提示词、专项负面和完整拼接
5. `完整拼接`：只收录复检通过的可直接投喂提示词

## 主镜头字段

```json
{
  "id": "S1-01",
  "scene": "场景名",
  "duration": 10.0,
  "organization_mode": "连续运镜/连续变景别/明确剪切/组合",
  "characters_present": "人物A：入画；人物B：画外右侧发声",
  "shot_size": "近景→特写",
  "camera_movement": "稳定后拉；匹配剪切；连续上移轻推",
  "composition": "...",
  "expression": "...",
  "action": "...",
  "dialogue": "逐句台词与计算时长",
  "audio": "环境音/动作音时间窗与层级",
  "lighting_enhancement": "当前场景光影",
  "scene_fixed_prefix": "仅当前场景与当前出场人物",
  "shot_dynamic_prompt": "时间化执行提示词",
  "special_negatives": "本镜专项风险",
  "validation_status": "通过",
  "validation_notes": "实际核对与修复摘要",
  "full_prompt": "人工整合复检版",
  "subframes": []
}
```

## 子镜头/阶段字段

```json
{
  "id": "S1-01-1",
  "label": "子镜头1/阶段A",
  "frame_role": "建立/动作/细节/反应/口播/落幅",
  "time_start": 0.0,
  "time_end": 3.5,
  "transition_in": "起始/连续/硬切/匹配剪切/视线剪切/叠化",
  "shot_size": "近景",
  "camera": "平视，稳定后拉",
  "composition": "...",
  "expression": "...",
  "action": "...",
  "dialogue": "...",
  "speech_pace": "normal/fast/slow",
  "performance_padding": 0.5,
  "lighting": "...",
  "continuity_anchor": "切前状态→切后继承状态"
}
```

生成脚本若没有独立列，必须把 `organization_mode` 与 `characters_present` 放入动态提示词，把时间字段写入子分镜文本，不得丢失。

## 通过门槛

- 主时长等于子时间窗合计
- 台词在实际时间窗内并有表演余量
- 原文账本无遗漏
- 人物位置、面向、视线、动作目标、轴线无冲突
- 剪切/连续变景别关系明确
- 当前场景光影连续
- `full_prompt` 非机械拼接
- `validation_notes` 说明实际修复；不得只写“已优化”
