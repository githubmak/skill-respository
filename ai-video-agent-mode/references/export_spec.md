# Export Spec — 导出格式规范

Phase 10 导出前加载。

## Excel Workbook（export_with_validation.py）

文件名与用户确认的 Markdown 文件同名，仅扩展名改为 `.xlsx`。

### 提示词包分栏结构

| Sheet | 内容 | 列 |
|-------|------|----|
| AI视频模型提示词 | 模型直接投喂与生成控制 | 主镜头, 子镜头, 时长, 模型提示词, 负面提示词, 生成模式, 原生音频 |
| QA与表演预算 | 内部质量合同与动作预算 | 戏剧目标, 镜头功能, 叙事权重, 信息增量, 反应归属, 节拍ID, 时长策略, 容量利用率, 角色优先级, 动作预算, 起终态, 表演因果, 三份合同, 台词引用, 注意力交接, 打斗连续性 |
| 台词与OS表演 | 原文与配音/表演执行 | 引用, 类型, 人物, 逐字原文, 时间窗, 可见性, 神态, 身体状态, 语气与停顿, 口型同步, 原生音频 |
| 导演连续性 | 运镜和跨镜承接 | 景别, 机位, 运镜, 视点, 画面层级, 入场策略, 揭示策略, 焦点策略, 镜头模式, 表演链, 镜头执行节拍, 序列承接, 轴线, 灯光, 落幅 |
| 九宫格剧情分镜图（可选） | 自动命中的连续镜头链 | 分镜编号, 场景, 关联子镜头, 总图提示词, 负面词, P01-P09节拍 |

当 `storyboard_grid.enabled=true` 时，增加 `九宫格剧情分镜图` 工作表，记录自动命中的连续镜头链、九宫格总图生图提示词、负面词与 P01-P09 节拍。关闭时不创建该工作表。

## Markdown Export（export_with_validation.py）

Markdown 只导出直接投喂和人工操作所需内容，禁止出现 QA 元数据、`qa_metadata`、生成控制、`generation_control`：

```
# {project_name} AI视频提示词包

#### 子镜头 {subshot_id}｜{duration}秒

**模型提示词**
{full_prompt}

**负面提示词**
{negative_prompt}

**下一镜转场提示词**
{transition_prompt}

**镜头执行节拍**
| 表演触发 | 镜头响应 | 状态承接 |

**台词/OS/OV表演**
| 引用 | 类型 | 人物 | 逐字原文 | 时间窗 | 神态 | 身体状态 | 语气 | 口型同步 |
```

当 `storyboard_grid.enabled=true` 且自动判断存在命中链时，Markdown 在常规子镜头后追加“自动九宫格剧情包”。该内容只包含总图生图提示词、负面词和九格剧情节拍；不得出现 QA 元数据、生成控制或非 T2V 操作说明。关闭时不得出现该章节。

下一镜转场提示词由导出脚本根据当前镜 `continuity_contract.next_carryover/end_anchor` 与下一镜 `continuity_contract.start_anchor` 自动生成，只用于连续生成和剪辑操作，不写入 `full_prompt`，不得新增剧情、服装、对白或人物动作。最后一镜写 `无，段落结束。`

镜头执行节拍来自 Director 的 `camera_beat_map`：展示时间窗、表演触发、视觉主体与落幅、镜头响应和承接状态，用于人工复核或平台分段执行；不是 QA 元数据，不投喂为额外模型段落。没有动态节拍时明确写“连续镜头，无额外切换”。

## 文件命名约定

- Markdown: 使用 Phase 0 一次确认并锁定在 `project_config.json` 的 `delivery.markdown_path`。
- Excel: 与 Markdown 同目录、同文件名，扩展名为 `.xlsx`。
- 以上文件只能写入用户本次明确确认并记录在 `project_config.json` 的 `export_base`。缺失时 blocking，不允许回退到 run_dir、当前目录或源文件目录。
