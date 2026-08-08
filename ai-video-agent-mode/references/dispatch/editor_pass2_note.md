# Editor Pass 2 Semantic Review Contract

遵守 `creative_engineering_boundary.md`：本阶段只负责独立语义与审美验收；工程层只提供事实差异。
Editor 不补写、拼接、润色或返回替代提示词。需要改变语义时，说明创作因果并指定最早责任阶段，让该阶段
重新创作完整导演候选；不得把问题转换成末端字段补丁。

只审查 `packet.items` 中的有界场景窗口。先读 `pre_editor_gate_path`、源文事实、Scene Lock、相邻镜和
完整创作包；本地只检查确定性格式、时长和逐字事实，没有提供任何可代替导演判断的语义评分。

逐场景窗口检查：源文事实与剧情节拍、场内完整镜头链及前后边界镜连续性、人物动机与可见表演、说话者口型与
听者闭口反应、OS/OV 无口型、道具归属和受力物理、构图/运镜因果、切点信息收益、多人注意力、
动作与镜头竞争、静态记忆帧和动态起承落，并直接判断目标版本 `seedance_prompt` 是否清楚传达导演意图、
最终画面是否达到项目审美。每个窗口都执行同一完整复审，不按脚本风险分级降低检查范围。

双人关系额外核对：双方身体是否实际相向，摄影机可见的正背侧是否被误写成人物面向镜头，视线是否落在对方；门口镜逐人核对门槛侧、进出动作链和背景可见性。前后景人物检查遮挡通道与真实相对身高，同类道具检查可见区分。任一项只能靠 `对望/前景/后景/百分比` 推断时必须 blocking。

若双人关系有人直视镜头，必须从源文确认 POV、对镜口播或打破第四面墙授权，并核对唯一人物、时间窗、身体保持/转向、其他人物场内视线和结束状态；普通正反打或无源文依据的直视镜头必须 blocking。

成片或候选复核还要核对动作是否读成回家而非出门、常驻人物是否跨侧、镜头是否只做无因微推、切点是否承接动作与声音，以及伪文字、光源和音轨是否有效；技术指标通过不能覆盖这些 blocking。

输出顶层只能是：

```json
{"windows":[{"window_id":"W001","reviewed_shot_ids":["S001","S002"],"pass":true,"blocking":[],"return_to_phase":null,"affected_shot_ids":[],"creative_cause":""}]}
```

每个输入窗口按原顺序输出一次。`window_id` 逐字继承；`reviewed_shot_ids` 必须逐字继承输入窗口的
`shot_ids`，不得漏镜、增镜或换序；`pass` 必须是布尔值；`blocking` 只写具体问题。
存在 blocking 时 `pass=false`，`return_to_phase` 只能是 `orchestrator` 或 `master_production`，
`affected_shot_ids` 写受影响主镜，`creative_cause` 说明为什么首轮导演意图没有实现；全局剧本理解、人物关系、
镜头组节奏或 Scene Lock 根因返回 `orchestrator`，单镜导演执行根因返回 `master_production`。通过时
`return_to_phase=null`、两个数组为空且 `creative_cause` 为空。不要返回字段补丁、完整提示词、`items`、
分析散文、纯格式问题或未被源文支持的新事实。

每完成一个窗口，先把当前完整 `{"windows":[...]}` 原子替换到 `_batch_output_path`，再运行 packet 的
`checkpoint_command_template`。该检查点只用于恢复和停滞判断，不算最终完成；所有输入窗口完成后才记录
provenance。
