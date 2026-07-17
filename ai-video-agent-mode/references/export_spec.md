# Export Spec — 导出格式规范

Phase 8 导出前加载。

## Excel Workbook（export_workbook.py）

文件: `prompt_package.xlsx` 或主Agent传入的用户导出路径文件名。

### 当前 7 Sheet 结构

| Sheet | 内容 | 列 |
|-------|------|----|
| 分镜总表 | 所有子镜头摘要 | 镜头编号, 子镜头, 时长, 景别, 机位, 运镜, 可见人物, 灯光, 落幅 |
| 静态分镜提示词 | 单帧图片提示词 | 镜头编号, 子镜头, 单帧图片提示词 |
| 关键帧提示词 | 关键帧提示词 | 镜头编号, 子镜头, 关键帧提示词 |
| 动态视频提示词 | 动态视频提示词 | 镜头编号, 子镜头, 时长, 动态视频提示词 |
| 九宫格剧情分镜图 | 按场景组织 9-panel blocks | 分镜编号, 镜头1, 镜头2, 镜头3 |
| 四宫格关键帧展开 | 主镜头最多四格展开 | 主镜头, 关键帧1, 关键帧2, 关键帧3, 关键帧4 |
| 负面提示词 | 逐子镜头负面提示词 | 镜头编号, 子镜头, 负面提示词 |

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
- 以上文件均写入用户在 `project_config.json` 中指定的 `final_export_dir` / `export_dir` / `export_base`；未指定时才回退到 `<run_dir>/exports`
