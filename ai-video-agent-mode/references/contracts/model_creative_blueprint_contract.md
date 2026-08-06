# 模型创作蓝图合同

Orchestrator 是模型创作阶段，不是本地分镜算法。工程层先产出
`.cache/orchestrator/source_snapshot.json` 和
`.cache/orchestrator/creative_blueprint_request.json`，然后暂停并返回
`creative_authoring_required`。当前主模型读取源文、快照、项目配置和本合同后，创作以下三个文件：

- `.cache/orchestrator/shot_plan.draft.json`
- `.cache/orchestrator/source_ledger.json`
- `.cache/orchestrator/dramatic_beat_ledger.json`

## 模型职责

模型负责理解剧情和潜台词，识别人物目标、关系与情绪变化，决定场景和戏剧节拍，完成拆镜、
反应归属、叙事权重、镜头功能、覆盖角色、时长策略及视觉标点。模型必须保留源文事实和逐字台词，
每个主镜只服务一个 `narrative_beat_id`，每镜不超过用户确认的 `max_shot_duration`。

`source_ledger.json` 由模型给每个需要进入成片的源文单元分配稳定 `source_id`，并记录源快照中的
`line`、逐字 `text`，再标记 `type=action|dialogue|scene_header|context`。工程层会核对行号与全文，
模型不能改写 ledger 原文。`type=action|dialogue` 的单元必须被
`dramatic_beat_ledger.json` 中至少一个节拍引用。`dramatic_beat_ledger.json` 的每个 `beat_id`
必须唯一归属于 `shot_plan.draft.json` 中一个现存 `subshot_id`。

每个 `dialogue_events` 记录还必须提供 `source_ids`。工程层要求 `text` 是这些源文行中的逐字连续片段；
允许模型按完整语义句拆成多个事件，但不允许增删、同义替换或改标点。

## 工程职责

工程层只做源文件读取、逐行快照、哈希、JSON/Schema、ID 唯一性、时长测量、逐字台词、引用覆盖、
配置锁定和文件写入。工程层不得创建或补全剧情节拍，不得自动合并动作/对白，不得选择反应人物、
叙事权重、镜头功能、景别、焦段、构图、运镜、光影、情绪或表演。

模型提交后，`build_shotplan.py` 只允许补机械 ID、锁定确认过的画幅/风格/时长上限并拒绝非法引用。
`preflight_check.py` 可以阻断错误，但语义修复必须返回模型处理，不能由脚本改写为可通过版本。

## 最小 `shot_plan.draft.json` 形状

```json
{
  "project_name": "",
  "canvas": "16:9",
  "visual_style": "用户确认风格",
  "max_shot_duration": 15,
  "scenes": [{"id": "SC01", "name": "场景名"}],
  "dialogue_map": {"D1": "逐字原文"},
  "dialogue_events": {
    "D1": {"ref": "D1", "kind": "台词", "speaker": "人物名", "text": "逐字原文", "source_ids": ["SRC0001"]}
  },
  "shots": [{
    "shot_id": "S1-01",
    "scene": "场景名",
    "core_action": "模型创作的本镜剧情动作",
    "subshots": [{
      "subshot_id": "S1-01-01",
      "duration": 8.0,
      "characters": ["人物名"],
      "dialogue_refs": ["D1"],
      "base_action": "本镜可见动作与反应",
      "source_ids": ["SRC0001"],
      "dramatic_design": {
        "shot_function": "dialogue",
        "coverage_role": "relationship_blocking",
        "narrative_weight": "high",
        "information_gain": "本镜唯一新增信息",
        "reaction_ownership": "承担反应的人物",
        "narrative_beat_id": "B001",
        "dramatic_beat_ids": ["B001"],
        "visual_punctuation": []
      },
      "duration_design": {
        "duration_strategy": "pack_toward_limit",
        "justified_content_duration": 8.0,
        "utilization_ratio": 0.533,
        "duration_rationale": "continuous_interaction",
        "dramatic_beats": ["B001"]
      }
    }]
  }]
}
```

示例只说明字段结构，不提供创意默认值；不得把其中的角色、权重、镜头功能或时长迁移到真实项目。
