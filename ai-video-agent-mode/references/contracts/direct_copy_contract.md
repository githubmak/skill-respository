# Direct-Copy Contract Slice

权威来源仍是 `references/format_constraints.md` §B0/§B2/§B6。本文件只作为快速定位切片。

`画面描述｜直接复制` 必须：

- 从 `full_prompt` 派生，不新增第二套提示词事实。
- 保留五段内容原有顺序、时间窗、原文台词和声音边界。
- 移除“上一镜、继承、尾帧、剪辑、切到、反打到、当前主角、当前对话者”等元叙述，改写为当前可见事实。
- 开头优先使用 `scene_tone_palette.visual_scene_prefix`：画幅/视觉风格 + 本镜固定空间锚点 + 本镜影调光线。
- 控制在 700 中文字符以内；light 镜也不得低质缩水，普通剧情镜低于 180 中文字符应升级或重写。
- 必含画幅、影调、色卡/视觉前缀、画面主体、运镜状态、光影描述和 1–2 个具体质感锚点。
- 推荐使用即梦友好导演卡顺序：画幅/风格 → 场景色卡/影调 → 主体位置与可见人数 → 表演/台词/听者反应 → 运镜路径或稳定状态 → 光影材质 → 落幅。
- 对白镜必须显式落地 `dialogue_performance_kernel` 的可见部分：1–3 个逐字原文重音词及说法、潜台词转译后的手眼/道具/距离证据、说话者口型、听者低幅反应、句末闭口与余波落幅；OS/OV/画外声只写闭口承接。
- 禁止把 `line_function/subtext/turn_relation/inner_emotion/display_intent/emotion_delta` 等分析标签、枚举名或强度数字写进直投正文。它们必须先转译成可见动作、构图、声音、运镜响应或落幅。
- 人物/对白镜应只保留一个构图戏眼和一个有因果的运镜/固定策略；不得堆叠多个“高级”构图、运镜和表情指令争抢同一时间窗。
- 高风险镜才追加 `本镜必要约束｜直接复制` 与 `本镜补充负面提示词｜直接复制`。

导出统一由 `scripts/direct_prompt_compiler.py` 结构化编译，顺序固定为：
`visual_prefix → space → continuity → performance → light → video_texture → cinematic`。
编译器跨段精确去重，只删除完整辅助句，不截断句子；空间、连续性、表演、光影和原生音频台词均为受保护事实。辅助质感句压缩后仍超过 700 字，或压缩必须删除受保护事实时，Export 必须阻断并退回 Master Production 重写，不得静默裁切。
