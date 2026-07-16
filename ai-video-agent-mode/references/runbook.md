# Runbook — AI Video Agent Mode Pipeline

本文件定义完整 8 阶段管线操作流程。启动新项目前必须加载。

## 项目目录结构

```
{project_dir}/
├── source.{docx|txt|md}          # 源文件
├── project_config.json            # 项目配置
├── _run_{timestamp}/
│   ├── .cache/
│   │   ├── orchestrator/
│   │   │   └── shot_plan.json
│   │   ├── director/
│   │   │   └── {shot_id}.director_packet.json
│   │   ├── continuity/
│   │   │   └── report.json
│   │   ├── composer/
│   │   │   └── {shot_id}.prompt_package.json
│   │   ├── editor/
│   │   │   └── merged.json
│   │   └── qa/
│   │       └── report.json
│   └── export/
│       ├── prompt_package.xlsx
│       └── prompts/
│           └── {shot_id}.md
```

## 管线执行顺序（严格顺序，不可跳过）

### Phase 1: Orchestration
- **工具**: 主Agent + `scripts/extract_source_text.py`
- **输入**: 源文件 + `project_config.json`
- **输出**: `.cache/orchestrator/shot_plan.json`
- **内容**: 读取源文本，拆分为镜头列表。每镜含 shot_id、subshot_id、duration、base_action、characters、dialogue_refs
- **手続**: 加载 `delegation_matrix.md` + `agent_protocol.md` 为 Phase 2 做准备

### Phase 2: Director Enhancement
- **工具**: 子Agent（并行 4-6 个），每 Agent 处理一个镜头包
- **输入**: `shot_plan.json` 中一个镜头包的数据
- **输出**: `.cache/director/{shot_id}.director_packet.json`
- **内容**: Director Agent 填充全量导演数据。子Agent 系统提示词从 `references/agents/02_director_enhancement_agent.md` 读取
- **校验**: `scripts/validator/field_types.py` + `scripts/validator/quality.py quality_check_director()`
- **失败处理**: 校验不通过则重派该镜 Director Agent

### Phase 3: Continuity Check（不可跳过）
- **工具**: `scripts/continuity_check.py --live`
- **输入**: `shot_plan.json` + 所有 `director_pass.json`
- **输出**: `.cache/continuity/report.json`
- **检查项**: 画风、服装、空间、轴线、情绪连续性
- **修复**: 发现问题回 Phase 2 重派 Director，不可静默修复

### Phase 4: Prompt Composition
- **工具**: 子Agent（全量），每镜一个
- **输入**: `director_pass.json`
- **输出**: `.cache/composer/{shot_id}.prompt_package.json`
- **内容**: 生成 4 种提示词: AI图片提示词、AI视频运动提示词、Seedance参考、完整视频生成
- **校验**: `quality_check_prompt()` — full_prompt >= 500 chars
- **失败处理**: 校验不通过重派

### Phase 5: Editor Pass 1
- **工具**: `scripts/merge_prompts.py`
- **输入**: 所有 composer 输出
- **输出**: `.cache/editor/merged.json`（含 merged_full_prompts）
- **内容**: 合并各镜提示词为完整包，按镜头顺序排列

### Phase 6: Editor Pass 2
- **工具**: LLM 评审（直接调用 editor_pass2_prompt()）
- **输入**: `merged.json`
- **输出**: 评审意见 + 修正版 `merged.json`
- **评审维度**: 提示词完整性、画风一致性、人物统一、运镜逻辑、平台适配

### Phase 7: Final Validation（不可跳过）
- **工具**: `scripts/validate_prompt_package.py`
- **输入**: `merged.json` + `project_config.json`
- **输出**: 验证报告
- **检查项**: JSON 结构、必填字段、时长总和、跨镜一致性

### Phase 8: Export（不可跳过）
- **工具**: `scripts/export_workbook.py` + `scripts/export/markdown.py`
- **输入**: `merged.json` + `shot_plan.json`
- **输出**: `export/prompt_package.xlsx` + `export/prompts/{shot_id}.md`
- **格式**: 加载 `export_spec.md`

## 铁律

1. **禁手动绕道**: 主Agent不可手动创建/复制下游文件绕过上游阶段。
2. **不可跳过**: Phase 3、5、6、7、8 不可跳过。Phase 2/4 失败需重派。
3. **6要素**: 每子镜头段提示词必须含 景别、机位、运镜、可见人物、动作+灯光、台词/OS。
