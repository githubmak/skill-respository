# Contract Index

`creative_engineering_boundary.md` 始终优先。只在当前模型创作任务命中时读取一个参考切片；参考文件向模型
提供创作知识，不构成工程 validator 的关键词规则。

| 模型任务 | 读取 |
|---|---|
| Seedance 最终提示词与导演卡 | `direct_copy_contract.md` |
| 剧本、潜台词、表演与角色关系 | `source_basemap_contract.md` |
| 构图、机位、运镜、焦点、光影、影调与动态美学 | `aesthetic_directing_contract.md` |
| 材质、空间、道具、透视、光源与生成风险 | `visual_quality_contract.md` |

工程实现只定位到：

| 确定性问题 | 实现 |
|---|---|
| JSON、ID、覆盖、时长、逐字台词、T2V 结构、版本字段 | `validate_deterministic_package.py` |
| Scene Lock 文件结构与唯一 ID | `validate_scene_locks.py` |
| provenance、hash、staging、超时、重派与熔断 | `record_batch_provenance.py`、`pipeline_deadline.py`、`workflow_supervisor.py` |
| 原样版本选择与 Markdown/XLSX 排版 | `export_with_validation.py`、`check_export.py` |

“是否有创意、是否平淡、运镜是否有因果、表演是否自然、光影是否漂亮、Seedance 是否理解、最终审美是否
成立”没有 Python validator 入口，统一由 Editor 模型复审。
