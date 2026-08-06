# Model-Authored Seedance Contract

Master Production 直接创作最终 `seedance_prompt`，不是让 Export 从其他字段派生。模型自行决定叙事、
表演、空间、机位、运镜、焦点、光影、色卡、材质、声音、节奏和终态的组织方式，并对目标 Seedance
版本进行语义编译。

- 单目标：填写 `seedance_prompt`，最多700字。
- 双目标：分别填写 `seedance_prompt_variants["2.0"]` 与 `["2.5"]`，每份最多700字。
- 导演卡：模型另写 `director_card`，最多500字。
- 超限或缺失：由模型重写；工程不得组装、去重、截断、补写或更换词语。
- Editor：独立判断是否准确理解剧本、能否让观众读懂、是否适配 Seedance 以及最终审美是否成立。

工程只验证字段、字符数、版本映射、逐字台词和原样导出。
