# Export Spec — 导出格式规范

Phase 8 导出前加载。

## Excel Workbook（export_workbook.py）

文件: `prompt_package.xlsx`

### 目标 8 Sheet 结构

| Sheet | 内容 | 列 |
|-------|------|----|
| 分镜总表 | 所有子镜头摘要 | 镜头编号, 子镜头编号, 场景, 时长, 景别, 动作概述 |
| 完整提示词 | 合并后的全量提示词 | 镜头编号, 完整提示词 |
| 镜头数据 | 每镜完整数据 | 游标卡尺, 机位, 运镜, 构图 ... |
| 人物调度 | 角色出场时间线 | 角色名, 出场镜号, 服装版本, 情绪状态 |
| 台词表 | 每镜台词/OS/OV | 镜号, 类型(对话/OS/OV), 内容 |
| 音效表 | 音效与音乐设计 | 镜号, 音效类型, 描述, 时间点 |
| 风险检查 | QA 发现的问题 | 镜号, 风险等级, 问题描述, 修改建议 |
| 项目配置 | 项目全局参数 | 参数名, 值 |

### 当前实现（最小版本）

当前 `export_workbook.py` 生成 2 个 sheet：分镜总表 + 完整提示词。后续可按需扩展至 8 sheet。

## Markdown Export（export/markdown.py）

每个镜头生成一个 .md 文件：

```
export/prompts/{shot_id}.md

# {shot_id}

**Duration**: {duration}s

{full_prompt}
```

## 文件命名约定

- Excel: `prompt_package.xlsx`
- Markdown 目录: `prompts/`
- 单镜文件: `{shot_id}.md`（如 `S1-01.md`）
- 以上文件均写入 `export/` 子目录
