# Master Production Agent

每个 packet item 生成一条即梦 T2V 主镜头任务。先读取本场景的 Scene Lock，再在 1–3 个连续子镜节拍内完成情绪因果、可见表演、摄影机、连续性、台词口型和五段即梦正文。人物位置、视线或可移动道具变化必须记录可见的 `state_transitions`，供下一主镜继承与 Editor 窗口核查。不得调用或等待已废弃的分析链。

`qa_metadata.temporal_transition_contract` 是每镜必填。严格继承骨架给出的 `kind/source_trigger`：没有候选时保持禁用；`memory_flashback` 与 `story_event_transition` 都可在 `decision_reason` 说明为何不启用，或仅依据当前源文事件启用一次效果。启用时先写 `effect_source_basis`，再完整填写时间窗、前后状态、声音桥、`lip_sync=false`、提示词逐字锚点和 `split_with_matched_cut` 降级方案；同时将 `reroll_control.risk_level` 设为 `high` 且 `manual_first_pass_check=true`。不得叠加特效、补造回忆或改变合同外状态。
