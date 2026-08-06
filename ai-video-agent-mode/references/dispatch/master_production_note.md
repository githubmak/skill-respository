# Master Production Creative Contract

`creative_engineering_boundary.md` 是最高合同。本阶段由大模型承担完整导演责任：理解剧本与潜台词，决定
情绪因果、表演、拆镜、节奏、站位、机位、景别、焦段、运镜、焦点、光影、影调、色卡、材质、动作、
声音、连续性解决、Seedance 语义编译和最终审美。工程数据只提供源文事实和交付边界，不能替代这些判断。

读取 `packet.items`、模型创作的 Scene Lock、相邻镜上下文、源文快照、工程逐行台账和项目配置。每个主镜输出一条完整记录到
`packet._batch_output_path`，顶层为 `{"shots":[...]}`。保留 scaffold 锁定的 ID、时长、逐字台词事实和
T2V 控制；其余内容均由模型创作。不要把 scaffold 空字段当成创作模板。

模型可按当前剧情自由选择分析方法和导演工具。既有美学、表演、空间、连续性和生成稳定性参考是专业知识库，
不是必填清单；不得为了填满字段而制造无关动作、运镜、情绪变化或画面细节，也不得为了所谓镜头多样性破坏
更合适的固定机位、重复构图、留白或长停顿。判断标准是观众如何理解和感受这一镜，以及目标 Seedance 版本
能否保留导演意图。

必须由模型直接创作：

- `full_prompt`：完整导演表达，内部结构由模型决定。
- `seedance_prompt`：目标版本的最终 Seedance 语义编译，不超过700字。
- `seedance_prompt_variants["2.0"]` 与 `["2.5"]`：仅目标为 `both` 时分别创作，不得由脚本互相改写。
- `director_card`：模型的最终导演卡，不超过500字。
- `negative_prompt`：根据本镜真实生成风险创作，不从关键词库自动注入。
- `qa_metadata`：模型认为有助于创作、连续性和 Editor 复审的分析资产；除逐字台词事实外不设固定子字段。

原文没有的人物、剧情事件、人声台词、OS、OV 或系统音不得新增；对白事实不得改字。若单镜超过15秒，或
当前镜容纳不下模型认为必要的独立节拍，由模型重新拆镜或重写节奏，工程只报告数值问题。任何字符超限、字段
缺失或 Editor blocking 都返回模型修订，Normalizer、Merge、Validator 和 Export 不会删句、拼接或补写。

每镜完成后运行 `incremental_validation_command`，批次完成后运行完整 `local_validation_command`。这些命令
只核对结构、时长、源文和逐字事实；它们通过不代表创作质量通过。最终语义、Seedance 适配和审美由模型
Editor 使用完整未截断上下文独立判断。
