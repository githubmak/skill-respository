# Export Spec — 导出格式规范

Phase 8 导出前加载。

## Excel Workbook（export_workbook.py）

文件: `prompt_package.xlsx` 或主Agent传入的用户导出路径文件名。

### Mode C v4 分栏结构

| Sheet | 内容 | 列 |
|-------|------|----|
| 分镜总表 | 所有子镜头摘要 | 镜头编号, 子镜头, 时长, 景别, 机位, 运镜, 可见人物, 灯光, 落幅 |
| 模型提示词 | 只含四段可执行提示词 | 镜头编号, 子镜头, 模型提示词 |
| 生成控制 | T2V/I2V/R2V、音频能力、真实参考资产 | 镜头编号, 子镜头, generation_control |
| QA与动作预算 | 戏剧目标、主次角色、动作预算、起终态、表演合同、连续性合同、抽卡控制 | 镜头编号, 子镜头, qa_metadata |
| 九宫格剧情分镜图 | 按场景组织 9-panel blocks | 分镜编号, 镜头1, 镜头2, 镜头3 |
| 四宫格关键帧展开 | 主镜头最多四格展开 | 主镜头, 关键帧1, 关键帧2, 关键帧3, 关键帧4 |
| 负面提示词 | 逐子镜头负面提示词 | 镜头编号, 子镜头, 负面提示词 |

## Markdown Export（export_with_validation.py）

Markdown 只导出直接投喂和人工操作所需内容，禁止出现 QA 元数据、`qa_metadata`、生成控制、`generation_control`：

```
# {project_name} AI视频提示词包 — Mode C v4

#### 子镜头 {subshot_id}｜{duration}秒

**模型提示词**
{full_prompt}

**负面提示词**
{negative_prompt}

**台词/OS/OV表演**
| 引用 | 类型 | 人物 | 逐字原文 | 时间窗 | 神态 | 身体状态 | 语气 | 口型同步 |
```

## 文件命名约定

- Excel: `prompt_package.xlsx`
- Markdown: 主Agent传入的用户确认路径。
- 以上文件只能写入用户本次明确确认并记录在 `project_config.json` 的 `export_base`。缺失时 blocking，不允许回退到 run_dir、当前目录或源文件目录。
