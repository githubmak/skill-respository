# Export Spec

Export 只处理确定性映射，不创作、不精炼、不解释模型文本。

## 输入映射

- `auto|2.0|2.5`：读取对应镜头的模型字段 `seedance_prompt`；若模型同时提供目标版本变体，按确认目标选择该变体。
- `both`：分别读取 `seedance_prompt_variants["2.0"]` 与 `["2.5"]`。
- 导演卡：逐字读取 `director_card`。
- 负面词：逐字读取 `negative_prompt`。
- 台词表：逐字读取 `qa_metadata.dialogue_events[].ref/kind/speaker/text`，并与源文账本核对。

任何创作字段缺失或 Seedance/导演卡超过700/500字时返回 `CREATIVE_REWRITE_REQUIRED`。Export 不得
从 `full_prompt`、Scene Lock 或 QA 字段拼接正文，不得去重、压缩、截断、替换光影词或生成关键帧。

## 文件

- Markdown 路径必须来自 `project_config.json.delivery.markdown_path`。
- Excel 与 Markdown 同目录、同 stem，扩展名 `.xlsx`。
- 单目标另可生成同名 `.concise.md` 与 `.engineering.md`。
- `both` 输出 `*_Seedance2.0.md`、`*_Seedance2.5.md` 和 `00_双版本索引.md`。

版本索引只记录目标到文件的对应关系。它不能声明或制造两版在光影、动作、机位、节奏和风格上的区别。

## 排版验证

导出后的确定性检查只验证：镜号和顺序、时长显示、所选模型提示词与导演卡逐字符存在、逐字台词存在、
XLSX 存在、文件名与目标版本相符、哈希和 staging 状态有效。Markdown 的审美和 Seedance 语义由此前的
模型 Editor 审核，导出脚本不得再次用关键词或正则评分。
