# Editor Pass 2 Semantic Review Contract

只审查 `packet.items` 中的有界场景窗口。先读 `pre_editor_gate_path` 与
`emotion_camera_audit_path`；本地确定性格式、枚举和字段类型已经检查，不要重复改写。

逐窗口检查：源文事实与唯一剧情节拍、上一/当前/下一镜连续性、人物动机与可见表演、说话者口型与
听者闭口反应、OS/OV 无口型、道具归属和受力物理、构图/运镜因果、切点信息收益、多人注意力、
动作与镜头竞争、静态记忆帧和动态起承落。`light` 仍审当前镜与承接；`high` 审完整窗口。

输出顶层只能是：

```json
{"windows":[{"window_id":"W001","pass":true,"blocking":[],"repair_targets":[]}]}
```

每个输入窗口按原顺序输出一次。`window_id` 逐字继承；`pass` 必须是布尔值；`blocking` 只写具体
语义问题；`repair_targets` 只写最早负责的最小字段，格式为
`{"shot_id":"S1","field_path":"qa_metadata.continuity_contract.end_anchor"}`。
存在 blocking 时 `pass=false`；通过时两个数组都为空。不要返回完整提示词、`items`、分析散文、
纯格式问题或未被源文支持的新事实。
