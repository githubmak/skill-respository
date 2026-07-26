# 当前流程门禁

| Phase | Input | Output | Gate |
|---|---|---|---|
| Scene Lock | 镜头计划 | `scene_locks.json` | 每个场景一条不可变记录；空间、人物位置、道具、服装、光源类型/方向/色温和声音政策完整 |
| Master Production | 镜头计划 + 场景锁定 | 主镜 `shots[]` | 每个主镜一条 T2V 任务；内部 1–3 个连续节拍；三份合同和五段即梦正文全部通过 |
| Editor Pass 2 | 提示词包 | 场景窗口复审 | 每个窗口包含上一镜/当前镜/下一镜摘要；所有 blocking 问题都通过按字段修复的主镜补丁解决 |
| Validate | 最终包 | 报告 | 确定性、语义、导出和 token 预算门禁全部通过 |

当前契约不再承认旧版 analysis、Director 或 Composer 独立阶段。
