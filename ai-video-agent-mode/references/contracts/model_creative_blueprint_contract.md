# 模型创作蓝图合同

Orchestrator 是大模型导演创作阶段。工程先生成逐字源文证据：

- `.cache/orchestrator/source_snapshot.json`
- `.cache/orchestrator/source_ledger.json`
- `.cache/orchestrator/creative_blueprint_request.json`

模型读取源文、上述证据和项目配置，在同一次全局导演创作中提交：

- `.cache/orchestrator/shot_plan.draft.json`
- `.cache/orchestrator/scene_locks.draft.json`

## 最高目标

让大模型充分发挥导演与创作能力，以最终画面和观众感受为判断标准。模型负责剧本理解、潜台词、
人物目标与关系、情绪因果、表演、戏剧节拍、拆镜、节奏、站位、机位、景别、焦段、运镜、焦点、
光影、影调、色卡、材质、声音、动作设计、Seedance 语义编译和最终审美判断。

模型可自由决定创作分析过程、字段名称和嵌套结构。`dramatic_design`、`duration_design`、节拍 ledger、
固定权重、固定镜头功能或一节拍一镜都不是必填合同。一个源文单元可被多个镜头引用，一个镜头也可承载
多个节拍；重复、回切、蒙太奇、长镜头和拆镜均由模型决定。

本阶段不是供末端补丁使用的粗略草稿。模型先完成整集导演理解，再把 `shot_plan.draft.json` 与
`scene_locks.draft.json` 作为首轮最终导演候选落盘；提交前自行检查剧情因果、观众信息顺序、人物关系与
情绪推进、镜头组节奏、空间连续、视觉基调和 Seedance 可实现性。该自审是模型的自由导演判断，不要求
自评分、逐项打勾或抄写证据。

`scene_locks.draft.json` 与分镜来自同一次剧情理解。模型为每个分镜使用的场景创作唯一 `scene`、唯一
`space_id` 和至少一项非空创作资产；空间关系、入口出口、光源、影调、色卡、材质、声音、环境运动、
道具活动区及连续性如何组织由模型决定，不设固定创作子字段。工程验证后按字节原样提升为
`.cache/analysis/scene_locks.json`，不再派发独立 Scene Lock Agent。

## 工程证据

`source_ledger.json` 由工程从快照逐行生成，每条包含稳定 `source_id`、`line` 和逐字 `text`。工程不判断
该行是动作、对白、场景标题还是上下文，也不从文本推断剧情功能。

模型在每个子镜的 `source_ids` 中引用支撑该镜的源文行。非空源文行必须至少被一个镜头或对白事件引用；
若某行不进入成片，模型在顶层 `source_exclusions` 中写入 `source_id` 和创作理由。工程只检查 ID 是否存在、
是否遗漏或冲突，不判断理由是否正确。同一 `source_id` 可跨镜重复引用，不设“恰好一次”限制。

每个 `dialogue_events` 记录提供 `source_ids`，且 `text` 必须是对应源文中的逐字连续片段。模型可以按语义句
拆分事件，但不能增删、同义替换或改标点。原文没有的人声、台词、OS、OV 或系统音不得新增。

## 最小机械接口

以下示例只展示工程需要定位的 ID、时长、源文和对白引用。除这些锁定事实外，模型可增加任意创作字段，
所有新增字段必须被后续 packet 和 Editor 上下文完整透传。

```json
{
  "dialogue_map": {"D1": "逐字原文"},
  "dialogue_events": {
    "D1": {
      "ref": "D1",
      "kind": "台词",
      "speaker": "人物名",
      "text": "逐字原文",
      "source_ids": ["SRC000002"]
    }
  },
  "source_exclusions": [
    {"source_id": "SRC000001", "reason": "模型判断的非成片内容理由"}
  ],
  "shots": [
    {
      "shot_id": "S1-01",
      "scene": "模型识别的场景",
      "subshots": [
        {
          "subshot_id": "S1-01-01",
          "duration": 8.0,
          "source_ids": ["SRC000002", "SRC000003"],
          "dialogue_refs": ["D1"]
        }
      ]
    }
  ]
}
```

## 工程门禁

工程只执行 JSON/Schema、机械 ID、源文逐字完整性、对白逐字核对、引用存在、显式覆盖状态、时长上限、
配置锁定、哈希和文件写入。它不得创建或补全剧情节拍，不得自动合并动作或对白，不得选择反应人物、
叙事权重、镜头功能、构图、运镜、光影、情绪、表演或 Seedance 表达。

`build_shotplan.py` 只补机械 ID、锁定确认过的画幅/风格/时长上限并保留模型的全部未知字段。
`preflight_check.py` 只报告可机械证明的问题；任何需要改变创作语义的修复必须返回模型。
`validate_scene_locks.py` 只检查 JSON、唯一 ID、非空创作资产和分镜场景覆盖；工程不得补写 Scene Lock。
