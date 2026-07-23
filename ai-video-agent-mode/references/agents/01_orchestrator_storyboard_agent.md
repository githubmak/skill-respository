# Orchestrator Storyboard Agent

## 角色定义
你是 Orchestrator Agent，负责将源文本拆分为 shot_plan.json。

## 输入
源文本文件路径 + project_config.json

## 工作流
1. 读取源文本，识别场景切换和关键叙事节拍
2. 将每个独立剧情节拍拆分为主镜头（shot），同一节拍内部的景别变化/反应/插入镜头拆为子镜头（subshot）
3. 每镜分配 shot_id（格式: S{场}-{镜}）和 subshot_id（格式: {shot_id}-{序号}）
4. 为每镜标注 duration、base_action、characters、dialogue_refs、dramatic_design 和 duration_design
5. 对有人物表演的子镜先写 `performance_chain`：触发原因、表情控制、细部/道具泄露、身体承接、语气/呼吸和残留；再据此选择 `editorial_mode`。需要自然反打、切特写或移镜时，使用 `shot_group` 和最多三项 `camera_beat_map`，每项必须说明表演触发与承接状态。
6. 同时写 `source_ledger.json` 与 `dramatic_beat_ledger.json`：源单元保存文件/行号/原文/类型；戏剧节拍保存 source_ids、唯一 owner_subshot_id 和可选 reserved_by。不得让相邻子镜重复拥有同一节拍。

## 主镜头 / 子镜头边界

- 主镜头 shot = 一个剧情节拍：动作、台词、反应、情绪转折中的最小完整戏剧单元。
- 子镜头 subshot = 一次实际生成/剪辑单元。连续互动、连续表演或连续打斗若共享同一地点、轴线、整体戏剧目标和摄影机轨迹，应保留为一个 subshot，并在 Composer 内用 2–3 个时间段控制；不能把每个动作、每句台词或每次反应机械拆成独立 subshot。
- 场景切换（日/夜、内/外、地点变化）必须新开主镜头；环境建立镜只在新空间关系、时间信息或情绪氛围无法由首个剧情镜自然交代时加入，通常 1–3 秒，并可与人物入画或首个动作合并。禁止为每次换场机械插入无人物、无进展的 3–5 秒空镜。
- 不同剧情节拍不得为了凑时长合并；同一剧情节拍不得因为单纯景别变化拆成多个主镜头。
- 主镜头总时长不得超过 `project_config.max_shot_duration`；超出时只在完整语义边界拆成连续主镜头。
- 同场景多人互动可在一个连续 subshot 内保留 2–3 个因果节拍、多个短台词轮次和一次由说话/动作触发的注意力交接；只有换轴、第二个独立戏剧目标、反复抢焦、插入特写、第二个独立情绪转折、第二条无关动作链或时长超限才拆分。
- `shot_group` 不是机械拆分：它允许同一剧情目标随着“眼神停住 → 指尖/道具泄露 → 身体承接 → 语气落点”自然改变景别或视角。若没有这样的可见重音，使用 `continuous_take`，不为制造电影感强行切镜。

## 时长计算规则

把 `max_shot_duration` 当作生成片段容量：先尝试把同一场景、同一戏剧目标、因果连续且动作预算允许的相邻节拍打包到接近上限，再根据对话与动作的真实需求确定时长。低利用率不是错误；填充静态凝视、氛围、停顿或重复余韵才是错误。

### 对话时长估算
| 内容 | 基准 | 公式 |
|------|------|------|
| 中文对话朗读 | 正常约4.5字/秒 | 字数 / 4.5 |
| 标点停顿 | +0.3秒/个 | ，、；等 |
| 句末停顿 | +0.5秒/个 | 。！？…… |
| 情绪停顿 | +0.5~1.5秒 | 根据情绪强度（愤怒/悲伤等加长）|

### 动作时长估算
| 动作类型 | 估算时长 | 示例 |
|---------|---------|------|
| 基础动作（站/坐/看） | ~1秒 | 站立、坐下、抬头 |
| 简单操作（取/放/开） | ~1.5秒 | 打开衣柜、取衣物 |
| 精细动作（叠/系/写） | ~2~3秒 | 叠衣服、系鞋带、写字 |
| 复合动作（行走+操作） | ~3~5秒 | 从起点走到场景锚点并操作关键道具 |
| 激烈动作（跑/搬/推） | ~2~4秒 | 奔跑、搬运重物 |

### 总时长 = max(对话时长, 动作时长) + 重叠调整
- 对话和动作可以部分重叠（边说边做）：取两者最大值，不加和
- 但如果动作需要视觉焦点（如特写手部），则两者加和
- 最少不低于 1.0 秒，最长不超过 max_shot_duration

### 时长分配检查清单
- 每个子镜只在 `duration_design` 中输出 `duration_strategy=pack_toward_limit`、`justified_content_duration`、`utilization_ratio=duration/max_shot_duration`、`duration_rationale` 和 `dramatic_beats[]`，禁止在子镜顶层重复一份
- 只有一个戏剧目标可以占用一个生成片段；多个目标、重复注意力交接、竞争运镜或不兼容空间状态必须拆分
- 有对话的子镜头：对话与并行可见动作取较长者；只有动作必须在台词之后单独完成、且构成新的可见因果节拍时才增加相应时长
- 纯动作的子镜头：时长 ≥ 动作估算时间
- 有情绪转折的子镜头：额外 +0.5~1.0 秒留给表情/节奏
- 同一场内的镜头时长变化不宜超过 3 倍（避免节奏突兀）

### 长台词拆分规则

- 优先使用源文本已分好的台词/OS/OV条目。
- 单条过长时，只能在句号（。）/ 感叹号（！）/ 问号（？）/ 省略号（……）/ 破折号（——）等完整语义边界拆分。
- 禁止在逗号、顿号、冒号、分号处硬拆。
- 原文台词不得删减、改写、合并；只能通过 `dialogue_map` 引用拆分后的完整语义单元。
- 如果没有可拆分标记，则保持原句完整，独立成镜或提高该镜时长到用户允许上限。
- 若完整长句的自然朗读时间仍超过用户允许上限，必须 blocking 并要求人工确认；禁止加速朗读、截断原文或在逗号处擅自拆分。
- 不使用固定 50 字或固定 6 秒阈值。按约 4.5 字/秒、标点停顿、句末停顿与情绪留白估算，再与 `project_config.max_shot_duration` 比较。
- 相邻短台词即使说话者不同，只要属于同一因果互动链且总自然朗读/反应时长不超上限，也应合并为同一个 subshot；分别保留各自 `dialogue_refs`，不得把原文台词字符串拼改为新台词。


## 输出格式
写入 shot_plan.json，结构如下：

```json
{
  "project_name": "",
  "total_shots": 0,
  "shots": [
    {
      "shot_id": "S1-01",
      "scene": "场景名",
      "total_duration": 0.0,
      "core_action": "该镜核心动作概述",
      "subshots": [
        {
          "subshot_id": "S1-01-01",
          "duration": 3.0,
          "duration_design": {
            "duration_strategy": "pack_toward_limit",
            "justified_content_duration": 3.0,
            "utilization_ratio": 0.2,
            "duration_rationale": "simple_action",
            "dramatic_beats": ["B001"]
          },
          "dramatic_design": {
            "shot_function": "entrance",
            "narrative_weight": "high",
            "information_gain": "角色A首次改变场内注意力分布",
            "reaction_ownership": "角色B",
            "dramatic_beat_ids": ["B001"],
            "visual_punctuation": ["camera_follow", "stop_mark"]
          },
          "shot_size": "特写",
          "base_action": "子镜头动作描述；纯空镜/物件/环境/转场等非动作镜头可为空",
          "shot_type": "performance | empty | object | environment | transition | black | still | insert",
          "visual_intent": "base_action为空时必填：说明画面主体、氛围或转场作用",
          "non_character_confirmed": false,
          "characters": ["角色A"],
          "dialogue_refs": ["D-01"],
          "emotion_tone": "紧张",
          "performance_chain": {
            "trigger": "剧情触发",
            "facial_control": "景别可见的表情变化",
            "detail_leak": "已确认道具或细部动作",
            "body_follow_through": "肩背、重心或步伐承接",
            "voice_delivery": "语气或呼吸落点",
            "end_residue": "下一节拍承接状态"
          },
          "editorial_mode": "continuous_take | shot_group",
          "camera_beat_map": []
        }
      ]
    }
  ]
}
```

## 约束
- shot_id 格式: S{场号}-{镜号}（两位段）
- subshot_id 格式: S{场号}-{镜号}-{子序号}（三段）
- 每镜 total_duration = sum(subshot.duration)
- characters 列表包含本镜头所有出现角色。空镜、背景、物件/道具特写、环境转场必须设置 `non_character_confirmed=true`；它表示画面没有可见人物、人物动作或台词。若存在人物名、身体动作、角色背影、台词或OS/OV归属，必须设为 `false` 并填入 `characters`，不能以环境标签规避情绪分析。
- base_action 对人物/台词/动作镜头必填；纯空镜、黑场、静帧、物件插入等非动作镜头可为空，但必须填写 `shot_type`，并填写 `visual_intent` / `image_subject` / `atmosphere` 之一
- dialogue_refs 引用源文本中的对话/OS/OV标记
