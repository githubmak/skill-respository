# 运行手册

1. 先运行 `scripts/source_gate.py --source ... --run-dir ...`，处理 `blocking`；`advisories` 进入回执，不因缺少场景标题、服装细节或光影描述而阻断。源文回执按哈希缓存，未变化时续跑复用。
2. 生成并验证镜头计划；同时写入 `scene_motion_plan.json`，提前分配跨镜动静职责、响应预算和稳定终态要求。弱动力源只告警，允许镜头保持稳定。
3. 每个场景派发一个 Scene Lock 任务；先消费项目级 profile 回执，存在逐场覆盖时只读取当前场景回执。
4. Scene Lock 完成后本地生成 `scene_texture_plan.json`。按主镜派发 Master Production 任务；Composer scaffold 预填场级 `video_texture_contract`，并通过其中的 motion/texture plan 路径读取当前镜头底图，不把完整计划复制进 packet。
5. 先运行确定性审查，再并行派发 Editor Pass 2 场景窗口复审。
6. 只修复 validator 点名的字段，并只作用于受影响的主镜任务；修复后重复该窗口复审。
7. 只有所有窗口都清空问题后，才允许导出。

Packet 上限为 12,000 字符。只能在主镜或场景窗口边界拆分；绝不能截断台词。
