# QA/Integration Handler (Phase 3)

## 角色定义

Phase 3 是本地 handler，不 spawn 子Agent。它只负责把 Phase 2a/2b/2c 的三个分析输出按 `subshot_id` 确定性整合为 `director_pass.json`。

## 输入

- `.cache/analysis/emotion_output.json`
- `.cache/analysis/scene_output.json`
- `.cache/analysis/camera_output.json`
- `.cache/orchestrator/shot_plan.json`
- `project_config.json`

## 工作流

1. 读取三个分析输出的 `items[]`。
2. 按 `subshot_id` 一一对齐；`shot_id` 只用于分组。
3. 从 `shot_plan.dialogue_map` / `subshot.dialogue_refs` 恢复原始台词、OV、OS。
4. 生成扁平 `director_pass.json`，供 `prompt_composer` 子Agent继续成稿。
5. 不新增、删除、改写台词；不手改三个分析输出。

## 输出格式

```json
{
  "items": [
    {
      "shot_id": "S1-01",
      "subshot_id": "S1-01-01",
      "scene": "场景名",
      "duration": 3.0,
      "shot_size": "中近景",
      "camera_position": "自然语言机位",
      "camera": "自然语言运镜",
      "axis_space": "轴线与空间",
      "visible_characters": "可见人物",
      "character_action": "动作过程",
      "dialogue_audio": "原始台词/OV/OS与口型说明",
      "dialogue_refs": ["D-01"],
      "dialogue_raw_text": "原文",
      "lighting": "光照",
      "char_entry_exit": "出入画",
      "axis_start": "起始轴线",
      "axis_end": "结束轴线",
      "movement_type": "固定",
      "movement_detail": "运镜细节",
      "end_state": "落幅状态",
      "full_prompt": ""
    }
  ],
  "merged_full_prompts": []
}
```

## 约束

- QA 语义判断不在本地整合阶段直接修文案；只由后续 QA/Editor 输出 `repair_targets` 打回对应子Agent。
- 本地 handler 只保证数据可信、字段归一、来源可追溯。
