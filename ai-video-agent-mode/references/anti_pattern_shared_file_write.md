# Anti-Pattern: Shared File Write for Parallel Agents

## 问题
多个 Agent 同时写同一个输出文件时，后写入的会覆盖先写入的，导致数据丢失。

## 问题表现
- 先完成的 Agent 数据被后完成的覆盖
- 最终文件只保留了最后写入者的数据
- 103 项 → 40 项 → 10 项（连锁覆盖）

## 正确做法

### 1. 每个 Agent 写独立文件
```
emotion_b12.json  # Agent A: batches 1-2
emotion_b34.json  # Agent B: batches 3-4
emotion_b56.json  # Agent C: batches 5-6
```

### 2. 合并去重
```bash
python3 scripts/merge_agent_outputs.py emotion_output.json emotion_b12.json emotion_b34.json emotion_b56.json
```

`merge_agent_outputs.py` 按 `subshot_id` 去重，自动选择先到者，丢弃重复项。

## 派发模板注意事项
在 spawn_agent 的 task text 中：
- ✅ 写入：`{run_dir}/.cache/analysis/emotion_output_b12.json`
- ❌ 写入：`{run_dir}/.cache/analysis/emotion_output.json`

## 适用阶段
Phase 2 (analysis 三部)、Phase 6 (prompt composer) — 任何需要多 Agent 并行输出的阶段。
