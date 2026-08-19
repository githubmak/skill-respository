# 按需空间与排错参考

本文件不是生成模板，只在空间/遮挡仍有歧义或 Seedance 输出出现具体故障时读取。常规景别、运镜、表演、色卡、节奏、连续性和交付规则使用主流程中的权威参考，不在这里重复。

## 读取路由

- 桌边、门口、柜台、车内、多人物同框或遮挡复杂：读“高风险空间与遮挡”。
- 已有生成结果出现身份、左右、动作、焦点、光影或口型故障：读“专项排错”。
- 文字无法消除平面站位/轴线歧义：读“二维空间参考图”。

## 高风险空间与遮挡

先按 [visual-input-governance.md](visual-input-governance.md) 的场景空间模型确认：

`固定锚点 -> 人物物理槽位/朝向 -> 画面侧与纵深 -> 距离/隔物 -> 道具归属 -> 可通行路径 -> 关系轴/屏幕侧`

重点检查：

- **桌边/柜台**：内外侧、可触达范围、桌面道具、坐站高度和桌沿遮挡。坐姿人物不承担桌下鞋面或完整全身读取。
- **门口/走廊**：门内外、门扇开合区、门槛、出口方向和进出路径闭合；“门边”不能替代具体内外侧。
- **车内/车外**：前后排、方向盘、安全带、车门/车窗开合、人物内外状态；门框与玻璃均按真实遮挡处理。
- **多人同框**：每人活动槽位、直接听者、旁观者任务、主读点和错峰反应；不得用全员同亮度/同幅度解决关系读取。
- **前景遮挡**：门框、肩背、车门、家具和道具占据真实画面面积；若吞掉口型、手部接触、证据或主反应，改位置、景别或通过切镜准入拆镜。

只有人物真实转身/换位、镜内坐站、道具拿放/交接、实体越轴过渡或明确转场才能改变世界状态。换景别、换机位或“镜头切到”只能改变观看角度，不能让人物/道具瞬移、换手或无因换向。

前镜尾帧与后镜起态至少复述当前景别可见且最易漂移的 2-4 项：屏幕侧/朝向、姿态/重心、道具归属、未完成动作方向、接触、声音或关系余势。禁止只写“延续上一镜/状态不变”。

## 专项排错

- **身份/人脸漂移**：减少同框近似人物；确认全局人脸模板只出现一次，逐镜自足写人数、身份、服装职责与画面位置。
- **空间左右翻转**：回到固定锚点、关系轴、屏幕侧和机位参照；确认越轴由真实过渡承担。
- **动作无法完成**：检查准备态、单一方向、路径、接触点、受力、遮挡和共同终点；负载过高再拆镜。
- **道具复制/换手**：回查 [entity-prop-continuity.md](entity-prop-continuity.md) 的首次建立、控制者、位置、手别和镜尾结算。
- **焦点跳动**：减少同等重要主体，只保留一次有触发的焦点交接并写保持到尾帧。
- **光影闪烁/黑脸**：回到场景实体光源、受光面、遮挡、反射材质、白平衡和当前景别人脸保护。
- **口型/声音错配**：明确现场说话者、画外对白、OS/OV、声音传播范围和关键词后的获准反应者。
- **运动不停/穿物**：缩短或改向路径，写停止触发与具体终幅；不依赖“电影感、稳定、不要穿模”等抽象限制。

提示词先写身份、当前空间、主因果动作和口型归属，再写摄影机、焦点、光影和材质。摄影机、人物、手部和道具使用不同具名主语；左右注明是画面侧、人物自身手别还是从固定地点向外看的方向。

## 二维空间参考图

只在平面站位、轴线、实体边界、摄影机视锥或简化路径仍有高风险歧义时使用：

- `scripts/render_blocking_reference.py`
- `scripts/promote_blocking_reference.py`

二维图只证明平面位置、躯干朝向、实体边界、关系轴、摄影机位置、视锥与简化运动路径；不证明头部视线、坐站高度、手部接触、真实遮挡、外貌、材质、光影或最终景别。

JSON spec 至少包含一个 `states`。每个 state 需要 `blocking_id`、不少于两名 `characters`、按需的 `anchors/boundaries`，且只能有一个 camera。人物和摄影机用 0-1 归一化平面坐标；camera 需要 `x`、`y`、`facing_deg`、`subjects`，可选 `shot_type=relationship|over_shoulder`、`fov_deg` 和 `path`。path 必须含 `mode`、终点、`trigger` 和 `dramatic_gain`。

```bash
python3 scripts/render_blocking_reference.py spec.json --output-dir staging/blocking --png --replace --compact --report reports/blocking.render.json
python3 scripts/promote_blocking_reference.py record --render-report reports/blocking.render.json --decision PASS --review reports/blocking.review.json --compact --report reports/blocking.record.json
python3 scripts/promote_blocking_reference.py promote --review reports/blocking.review.json --delivery-dir approved-jimeng-2d --compact --report reports/blocking.promote.json
```

几何校验通过不等于可交付。必须用视觉能力检查姓名、平面位置、躯干方向、机位、视锥、边界和标签可读性；图文冲突时先重设计分镜，不用文字强压参考图。
