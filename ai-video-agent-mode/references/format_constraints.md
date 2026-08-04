# Format Constraints — Current Contract

本文件是 AI Video Agent Mode 的唯一权威数据契约。主 `SKILL.md`、Agent 指令、验证器、归一化与导出脚本必须服从本文件。

正常运行不要全量加载本文件。先运行 `route_task.py`，由 dispatch sidecar 选择当前阶段段落；
审查只按 `contracts/contract_index.md` 定位命中切片。只有修改字段、schema 或 validator 时才通读。

## §0 — Prompt-Only And Project Isolation

本管线只输出提示词和结构化制作元数据，不生成、读取、观看或评价图片/视频。任何“成片效果”判断只能写成提示词层面的预期与风险，不得声称已经完成视觉验收。

技能目录只保存 schema、算法、枚举、验证器和中性占位符。项目名、人物名、题材、服装、灯光、场景细节和剧情事实只允许出现在运行目录的 `project_config.json`、project bible、`source_ledger.json`、`scene_locks.json`、`dramatic_beat_ledger.json`、`shot_plan.json` 与 `prompt_package.json`。示例只能使用 `角色A/角色B/场景A/关键道具` 等中性占位符。

## Retired Contracts

旧 Emotion、Scene、Camera、Director 独立产物合同已移除；历史语义由 Git 历史保留，当前运行只接受 §B–§E。历史 `composer` 脚本名与 `.cache/composer/` 路径仅是稳定产物接口，不表示存在独立 Composer Agent。

## §B — Master Production 批次输出

### B0. 即梦投喂视图与注意力预算

`full_prompt` 是可验证的规范正文，保留 B2 的五段标签；Export 必须从它派生一份无标签的 `画面描述｜直接复制`。后者是用户复制进即梦正文框的唯一推荐正向提示词，严格保持五段内容原有顺序、时间窗、原文台词和声音边界，不新增第二份提示词事实。规范正文允许为了验证写“落幅/下一镜承接”，但直接投喂视图不得保留“上一镜、继承、尾帧、剪辑、切到、反打到、当前主角/当前对话者”等元叙述；导出层会把它们转为“当前起幅/落幅保持/画面主体”等当前可见事实。审阅性空话必须由 Master Production 和 Editor Pass 2 在规范正文阶段删除，而不是在导出时进行不可靠的语义改写。

`画面描述｜直接复制` 开头优先使用 `scene_tone_palette.visual_scene_prefix` 组成压缩视觉场景前缀：画幅/视觉风格 + 本镜固定空间锚点 + 本镜影调光线。导出块必须控制在 700 中文字符以内，并清晰包含画幅、影调、色卡/视觉场景前缀、画面主体、运镜状态、光影描述和 1–2 个具体质感锚点：光源方向/色温/受光关系，以及脸、手、道具、浅阴影、反光、背景虚化或剧情相关材质。前台导演精修层可将合规正文润成即梦友好导演卡，但不得新增第二套事实；推荐顺序为：画幅/风格 → 场景色卡/影调 → 主体位置与可见人数 → 表演/台词/听者反应 → 运镜路径或稳定状态 → 光影材质 → 落幅。对白镜必须消费 `dialogue_performance_kernel` 的可见部分：台词功能、说话者口型、关键词重音、听者低幅反应、句末闭口、余波落幅。`emotion_residue_contract` 只作为元数据记录触发前状态、泄露部位、压抑/释放方式和尾帧残留；direct-copy 必须改写成当前可见落幅，不写“尾帧/继承”。若项目目标是写实/实拍/电影剧照，不得只写“动态漫电影感”；必须启用或等价满足 `cinematic_image_contract`：构图锚点、焦平面/景深、曝光黑位、色彩分离、空气层、真实材质、非完美瑕疵/随机性和记忆帧。尤其雨、水面、霓虹、旧墙、玻璃、皮肤和布料不能写成完美镜面、塑料表面、均匀雨线、过曝灯管或虚拟摄影棚感。若目标是整条视频质感提升，使用 `video_texture_contract` 约束全片影像基调、曝光、材质运动、空气层运动、镜头稳定和跨镜继承；导出层只压缩其中一条短句进入 direct-copy，避免把单帧图片提示词的高密度细节复制到每个视频镜头。高风险镜才追加 `本镜必要约束｜直接复制` 与 `本镜补充负面提示词｜直接复制`；普通镜只输出直投正文和常规负面词，避免提示词臃肿。

导出必须通过 `direct_prompt_compiler.py` 按“视觉前缀→空间→连续性→表演→光影→视频质感→电影质感”编译：跨段精确去重，只按完整句删除辅助质感，不得从句中截断。空间、连续性、表演、光影和原生音频台词属于受保护事实；辅助句压缩后仍超过 700 字，或必须删除受保护事实才能达标时，Export 阻断并退回 Master Production 重写。

完整直投正文之外必须从同一 segments 编译 `【导演卡｜直接复制｜≤500字】`。导演卡只能删除完整辅助质感句，不得删除 visual_prefix/space/continuity/performance/light、终端稳定事实、锁定台词或 `must_render`；导演卡不设最低字数，为满足500字必须删除受保护事实时阻断回修。默认另导出 `.concise.md` 简洁交付视图和 `.engineering.md` 工程审查视图；前者只含导演卡与负面词，后者保留句级 source ID/Scene Lock/合同溯源、动作失败评分和压缩差异，不得投喂模型。

每场必须先冻结 `camera_variation_plan`，为每镜分配一个由空间和剧情支持的构图骨架与一个固定/单一路径运镜；连续三镜不得重复同一“景别+角度+构图+运镜”组合，除非明确写出情绪冻结理由。每镜必须填写 `terminal_frame_contract`，并把最后20%的可见人数、最终槽位、人物边界与脸/手/肢体分离、道具归属、支撑接触、摄影机停稳、光线曝光锁定和不新增/不重复主体转译进 `full_prompt`；不得只留在 QA、负面词或工程视图。

逐镜 `【本镜制作控制】` 与 `画面描述｜直接复制` 必须通过跨字段 grounding 门禁。画面质感、光效与曝光、动态美学、表演与情绪、穿帮控制、可见的降抽卡动作限制，以及启用蒙太奇/时空转场后的可见结果，必须分别能在直投正文中找到语义证据；风险级别、人工检查、失败后拆镜/重试、后期文字和工程审查不投喂模型。Export 将七维 grounding 报告写入编译报告，任何适用维度 `grounded=false` 时阻断导出并点名维度。

### B0.1 制作智能合同

- `prop_lifecycle_contract`：活动道具的用途、可见面、起始位置、接触者、接触方式、运动路径、终点、终点方向、下一镜状态必须齐全，并把可见面/接触/路径/终态转译到正文。
- `perspective_scale_contract`：多人纵深或沿景深移动时，写明各主体深度、共同支撑平面、消失/遮挡证据、近大远小投影、真实体型和头身/骨架比例不变、道具相对身体比例不变、画面占比连续变化及稳定备选。真实身高不得随远近改变，摄影机变焦不得冒充人物位移。
- `lighting_topology_contract`：动机光源、方向、色温范围、面部独立主/补光、环境层、阴影曝光、丁达尔/雾/烟/雨/水波体积边界和混合色温冲突处理必须明确；环境综合色和纹理不得污染脸部。
- `visible_emotion_state`：跨镜记录触发、表情泄露、身体承接、声音/呼吸变化、余波与强度变化，作为下一镜可消费状态，不进入直投正文。
- `production_intelligence.py` 生成视觉先验风险、多人注意力预算、动作失败预测、联合曲线、句级溯源和字段修复前后 diff；这些是确定性 QA 侧车，不增加 Agent 调用。

制作质量知识以 `references/production_quality_knowledge.md` 为候选池。它必须被转译为当前项目事实，而不是原样套模板：Scene Lock 生成本场专属 `space_id / space_master_sentence / entrance_exit / prop_activity_zone / tone_palette / light_texture_purpose / visual_scene_prefix`，以及风景身份、构图系统、自然运动、环境故事弧、揭示顺序、光候演进和镜头呼吸；Master Production 只消费这些事实和 packet items。每个场景的完整色卡应覆盖剧情情绪功能、主色/辅助色/点缀色、色温范围、主光方向、阴影颜色、对比度、饱和度、肤色保护、材质反光、允许变化和禁止偏色；单镜只写压缩色卡前缀和一个光影落点，不逐镜堆满全片美术表。角色表演基线必须转译为当前角色的常态控制方式、优先泄露部位、默认动作幅度、爆发阈值和禁用表演习惯；情绪微表演链也必须转译为当前角色、台词、景别、服装和道具的可见证据，不能原样复制词库。特殊视角运动语法只提供镜头与主体关系的候选结构，必须改写为当前空间、主体、障碍、人物顺序和落幅，不能照搬任何示例的地球、跑车、剑客、医院或城市。

每个子镜的注意力预算固定为：一个实焦主体、一个主动作或状态变化、一个可读表演证据、一个落幅承接。优先语序为“主体与屏幕位置 → 触发动作 → 当前景别可见的表情/身体 → 声音或口型 → 必要稳定约束”。人物情绪镜的可读表演证据应压缩为 3–5 个微动作，至少覆盖眉眼/嘴角/下颌、手指/道具/袖口、肩颈/重心、呼吸/停顿、视线落点中的三类。同主镜已锁定的画幅、风格、服装、光源、空间结构和通用禁令不得在每段复述；只有发生变化或影响本段执行时才再出现。

复杂度分档只减少内部合同和可选审查字段，不减少 `画面描述｜直接复制` 的核心信息。light 镜仍必须落地视觉场景前缀、具体构图骨架、景别/机位、人物位置与面向、台词或声音文本、说话者表演、听者/环境反应、镜头状态、光影/材质落点和最后20%终端状态；不设最低字数，短镜按必要语义完整度通过。standard/high 镜优先拆镜，不通过删掉空间、台词、道具归属、光影或终端状态来压缩。

禁止保留不产生可见结果的导演话术，例如“建立空间”“体现关系”“提升质感”“增强感染力”“保证质量”“整体层次分明”。以可见动作、焦点、景深、光线、声音或终态替代。字数软区间用于诊断而非填充；实际时长只由连续对白、互动、动作或揭示的可见节拍证明。

提示词质量先过第一层“不穿帮硬门槛”：人物位置、身体面向、道具归属、口型、落幅承接、单镜不过载、状态变化中间态必须稳定。任一项不稳，优先拆镜、补定位镜头、减少入画人物、降低运镜或退回连续性/空间合同。通过硬门槛后才进入第二层“创作表现权重”：剧情节拍与观众认知 > 非台词张力点 > 情绪表演张力 × 景别运镜匹配度 > 声音氛围和装饰细节。关键台词后优先给被击中者余波或关系定格；不得为了镜头变化、氛围或装饰牺牲剧情认知、空间连续、道具归属和口型。

Master Production 写镜前先建立本镜 `source_constraint_basemap`：空间与入口出口、人物朝向、状态/道具、物理反推、张弛功能、情绪钩子、角色表演基线、多人体反应、影调光影、声音/口型、屏幕文字策略和可选的特殊视角运动锁；再按适用性填写角色行动、关系情绪弧、序列导演、剪辑切点与提示词信息预算合同。它们都是防返工底图，不投喂模型；`full_prompt` 只消费其中能被即梦看见的事实。Scene Lock 可提供 `space_id / space_master_sentence / entrance_exit / prop_activity_zone / tone_palette / light_texture_purpose` 与七项风景导演扁平字段；同一地点跨镜必须复用同一个空间ID、主锁定句、入口出口和道具活动区，不能因新镜头重新开局、重排左右或重置道具。

人物一致性从“可见人数闸门”开始。多人、画外声或同场人物多于本镜实际入画人物时，Master 必须在 `performance_priority` 与 `full_prompt` 中区分清晰入画、肩线/背影/倒影/虚化入画和纯画外声；肩线、背影、倒影、虚化人影都计入可见人物，纯画外声不计入。不可见人物不得作为视觉朝向目标；若 B 不入画，禁止写 A 看向/面向/对着 B，应写 A 视线落向画外声源或固定空间锚点，并在稳定约束中声明 B 不入画。

最终提示词采用“主镜头状态机 → 子镜头状态机”装配，不按灵感散写。`主镜头连续规则` 只写全局不可变状态和唯一戏剧问题，固定顺序为：单一剧情问题 → 情绪/冲突触发 → 空间状态总锁 → 道具生命周期总锁 → 运镜响应原则 → 本镜禁止变化项。`子镜头组` 的每个时间窗固定顺序为：承接上一落幅 → 人物位置/朝向/视线 → 道具位置/朝向/接触状态 → 唯一触发/动作 → 情绪可见证据 → 镜头响应 → 结束状态/下一镜继承 → 禁止变化项。字段名仍使用英文 snake_case；中文标签只用于提示词正文分段和人工审阅。

空间锁定优先使用屏幕坐标、景深层级、朝向、视线和接触点：画面左/中/右、画面左前/右前/中后、前景/中景/后景、身体朝向画面左/右/前侧、视线落向某人或某道具、脚底/椅面/桌沿/门框/阴影接触。多人镜必须先锁定 A左、B右、C中后方等可视关系，再写禁止穿越线；不得只写“对面、旁边、后面、附近、远处、面对彼此”。人物朝向与摄影机方向分离，除非源文授权，不写角色直视镜头。

关键道具必须作为生命周期状态写入提示词：起始位置 → 朝向 → 归属 → 接触状态 → 可移动条件 → 结束位置 → 下一镜继承。若本段不改变道具，也必须说明“仍在……，未被触碰/仍由某人握住/仍压在某处”；若本段改变道具，必须写“谁在几秒处用哪只手从哪里拿起/放下/递给，落幅位于哪里”。禁止无可见动作依据让道具从桌面、地面、包内或画面外闪现到角色手中。

物品转移、人物转向、视线转移、重心移动和站位变化必须有中间态承接，不能从起态直接跳到终态。道具转移按“起始位置 → 手/身体接近 → 接触 → 拿起/递出/放下 → 对方接住或物体落定 → 落幅归属”组织；人物转向按“视线先变 → 头部微转 → 肩线/重心跟随 → 身体朝向完成 → 视线落定”组织。每项变化必须写入 `continuity_contract.state_transitions[]` 的 `from_state/intermediate_state/to_state/cause/time_range`，且 `intermediate_state` 必须在 `子镜头组` 中能找到可见动作证据。

人物镜的情感传递采用单一共情锚点：角色此刻在护住、害怕、忍住、失去或被刺中的一件具体事，并用一个当前景别可见的证据承载。表演顺序固定为“压住的起态 → 触发时点 → 身体先泄露 → 面部/视线跟上 → 声音落点 → 不复位残留”；一个人物在一个时间段至多一个主情绪转折，支持角色至多一次因果反应，背景不分配独立情绪任务。

每个时间段的画面层级固定为三层以内：实焦主体为第一层；前景肩线、手部、已确认道具或遮挡为可选第二层；空间和低幅背景为第三层。光线只服务实焦主体与一个真实接触点。影调先由场景的 `tone_palette/light_texture_purpose` 统一，再在单镜转译为 1–2 个可见锚点：光源方向/色温、脸/手/道具受光面、浅阴影/反光、背景虚化或剧情相关材质。不得为“电影感”同时堆叠多色轮廓光、雾气、反射、景深跳变和复杂运镜。

镜头语言可使用组件化知识储备，但每个子镜最多一个组件，并必须服务本镜唯一任务：听者被击中、关系拉开、手部情绪泄露、递物防闪现、正反打保轴、手机消息浮层、口型交接、结果物件/空镜缓冲、行走转对白等。组件必须改写成本镜人物、道具、空间、台词和落幅状态；禁止把组件当通用装饰或在同一子镜堆叠多个组件。

下一时间段或下一镜必须从上一段的可见落幅状态起演，继承姿态、视线、道具接触、重心、屏幕左右、焦点关系与同源光；只有源文可见动作或已声明的硬切/走位可改变状态。人物名称相同不构成连续性证据。

对手戏允许使用“心理距离景别反差”，但只能由源文中的不对等压力触发：焦虑、急迫、求回应、被压迫或失控的一方可用更窄景别、背景压缩、手部/呼吸细节和轻微推近；松弛、掌控、拒绝接招或旁观的一方可用中景/宽景、稳定机位、桌面/门框/屏风等空间留白保持呼吸感。该策略必须服务一个剧情节拍和一个注意力中心，不得变成“每轮对话一近一宽”的固定公式。

插入镜头是主叙事镜头中的短暂辅助画面：局部特写、道具/手部细节、空镜、反应镜、环境残留或时空意象，再回到主线。它只能服务当前 `narrative_beat_id`，用于补充关键信息、标记伏笔、放大一个情绪泄露、切割长对话节奏、缓冲转场或保留环境残压；不能替代主线人物表演，也不能承载第二个剧情节拍。

AI 漫剧互动戏的插入镜以稳定优先：已确认道具特写、环境残留最稳；手部/衣角/杯沿/文件等局部中高稳定；半脸/眼神特写只给关键破防；多人反应镜、连续快切、回忆/幻想插入为高风险。高风险插入如果包含新事件、新时空、新反应结论、第二次注意力交接或需要回切，应拆成下一主镜；回忆/幻想优先使用 `temporal_transition_contract` 或独立主镜。

插入镜必须带来新的可见信息、道具状态变化、关系压力或情绪残留，并继承同一场景锚点、光源、轴线、左右站位、道具位置和插入前后的动作状态。无信息增量的装饰空镜、频繁人物脸部特写、未确认道具、改变空间关系或画质/光源割裂的插入镜属于抽卡风险。

### B1. 顶层与 shot 结构

`risk_tier`、`risk_reasons`、`batch_capacity` 与 `review_scope` 仅存在于 dispatch packet；Editor review window 对应使用 `review_tier`、`risk_reasons` 与 `review_scope`。它们只决定批大小与可读上下文，不是 Master Production 输出字段，不得写入 `full_prompt`、`qa_metadata`、`negative_prompt` 或 `generation_control`。`light` 只代表可缩窄审查上下文，绝不代表免除 Agent 复审、三份合同、确定性验证或最终导出验证。`creative_profile` 是创作自由度档位，只能为 `safe/balanced/expressive`：safe 优先低风险直投稳定，balanced 默认启用前台导演精修、对白表演核和 1–2 个质感锚点，expressive 只在低风险或用户明确要求风格化时扩大构图/特殊视角/速度曲线；任何档位都不得降低 direct-copy 密度、T2V-only、源文保真、provenance、validator、golden 或规则一致性。

风险专项字段以派发 scaffold 的字段存在性为唯一运行开关：scaffold 缺席即不适用，Master Production 不得补回空对象、`none` 或其他占位符；scaffold 已提供则必须完整填写并通过对应 validator。省略风险专项字段绝不降低 direct-copy、连续性、口型、静态/动态美学、provenance、确定性验证或导出门槛。

Master Production batch 只输出：

```json
{
  "shots": [
    {
      "shot_id": "S1-01",
      "subshot_id": "S1-01-01",
      "duration": 5.0,
      "full_prompt": "",
      "negative_prompt": "{{NEGATIVE_PROMPT_AUTO_INJECT}}",
      "qa_metadata": {
        "dramatic_goal": "",
        "dramatic_design": {
          "shot_function": "establish | reveal | entrance | reaction | confrontation | transition | action | dialogue | object",
          "narrative_weight": "low | medium | high | critical",
          "information_gain": "本镜新增的唯一信息或关系变化",
          "reaction_ownership": "本镜拥有的反应人物；无则为空",
          "narrative_beat_id": "B001",
          "dramatic_beat_ids": ["B001"],
          "visual_punctuation": ["camera_follow", "stop_mark"]
        },
        "story_punch_contract": {
          "audience_question": "观众这一镜开始被迫追问的具体问题",
          "character_pressure": "角色此刻在怕、忍、隐瞒、试探或想护住什么",
          "visible_pressure_object": "本镜可见的戏剧压力物、动作中断、视线错位或关系距离；无则写none并说明",
          "dramatic_turn": "这一镜结束时观众认知或人物关系发生的唯一变化",
          "picture_punctuation": "本镜最有戏的一个静态画面标点，如未打开的药瓶、停在门把的手、第一次移开的视线",
          "composition_priority": "唯一构图戏眼：主体位置、前中后景、留白/遮挡/距离或焦点关系",
          "camera_motivation": "唯一运镜或固定策略，以及它响应的表演、台词、道具或空间触发",
          "end_residue": "落幅不复位的姿态、视线、道具、距离、呼吸或威胁状态"
        },
        "duration_design": {
          "duration_strategy": "pack_toward_limit",
          "justified_content_duration": 5.0,
          "utilization_ratio": 0.5,
          "duration_rationale": "simple_action | continuous_dialogue | continuous_interaction | continuous_action | sustained_reveal",
          "dramatic_beats": ["B001"]
        },
        "editorial_mode": "continuous_take | shot_group",
        "emotion_driver": {
          "trigger": "源文支持的情绪触发点、动作触发点或可见自主起势",
          "start_state": "人物起幅情绪/身体状态",
          "visible_leak": "身体、手部、道具或姿态先泄露的可见证据",
          "face_or_eyeline": "当前景别可见的表情、视线或不可见时的N/A说明",
          "voice_or_breath": "呼吸、语气、气口或无声时的可见呼吸控制",
          "end_residue": "本镜落幅不复位的情绪、姿态、视线或道具残留",
          "tension_intent": "neutral | latent | rising | peak | release",
          "empathy_anchor": "观众能读懂角色此刻在怕、忍、护住或失去什么"
        },
        "camera_beat_map": [
          {
            "time_range": "0.0-1.2秒",
            "focus_owner": "角色A | 角色B | object | environment",
            "focus_subject": "承担本节拍的人物、手部、道具或关系",
            "framing": "景别与实焦主体",
            "trigger": "触发本子镜切换的emotion_driver表演重音、道具状态变化或台词落点",
            "camera_response": "hold | push_in | pull_back | reframe | rack_focus | hard_cut | cut_detail | follow",
            "camera_position": "机位位置、高度、前景肩膀/遮挡和空间锚点",
            "camera_movement": "固定、极慢推近、拉远、单向重构图、拉焦、硬切或跟随之一；无则写固定",
            "transition_type": "continuous | hard_cut | motivated_insert | reframe | hold",
            "screen_lock": "画面左右、前中后景、实焦/虚焦关系",
            "axis_relation": "相对既有轴线的同侧/反打关系与左右位置",
            "axis_carryover": "切换前后必须继承的轴线、朝向和左右关系",
            "carryover": "切换后必须继承的状态",
            "end_frame": "本子镜落幅交给下一段的姿态、视线、道具和焦点状态",
            "insert_function": "仅插入镜填写：信息补充 | 情绪放大 | 节奏切割 | 视线引导 | 转场缓冲 | 环境残压",
            "new_information": "仅插入镜填写：新增信息、状态变化、关系压力或情绪残留"
          }
        ],
        "sequence_context": {},
        "viewpoint": "objective",
        "visual_hierarchy": "",
        "entry_strategy": "none",
        "reveal_strategy": "direct",
        "focus_strategy": "single_plane",
        "temporal_transition_contract": {
          "enabled": false,
          "kind": "none | memory_flashback | story_event_transition",
          "source_trigger": "源文逐字触发依据；none时为空",
          "decision_reason": "候选未启用时的源文依据；启用时的选择依据",
          "time_range": "0.0-0.0秒；启用时必须为有效窗口",
          "effect": "启用时根据当前事件配置的唯一视觉效果",
          "effect_source_basis": "该效果如何来自当前源文事件",
          "from_state": "转场前锁定的时空/人物状态",
          "to_state": "转场后锁定的时空/人物状态",
          "audio_bridge": "与提示词逐字一致的声音桥",
          "lip_sync": false,
          "prompt_anchor": "与提示词逐字一致的单一视觉效果锚点",
          "fallback": "split_with_matched_cut"
        },
        "quality_contract": {
          "profile": "environment | object | action | dialogue | dramatic",
          "required_analysis": ["scene", "camera"],
          "required_evidence": ["该类型必须在成片提示词中可见的质量证据"]
        },
        "quality_evidence": {"每项required_evidence": {"section": "主体与空间锁定|主镜头连续规则|子镜头组|光照、声音与稳定约束", "fragment": "该段中逐字存在的可见证据"}},
        "ai_model_readiness_score": {
          "scene_space": {"score": 1, "reason": "场景空间、屏幕坐标、景深层级和人物朝向的可执行依据或风险"},
          "continuity_risk": {"score": 1, "reason": "人物位置、身体面向、口型、落幅继承的穿帮风险"},
          "emotion_readability": {"score": 1, "reason": "情绪是否能从当前景别的可见证据读出"},
          "tension_pressure": {"score": 1, "reason": "冲突、压迫、信息差或代价是否有可见触发与残留"},
          "camera_emotion_fit": {"score": 1, "reason": "运镜是否由情绪、视线、台词落点或道具状态触发"},
          "prop_continuity": {"score": 1, "reason": "关键道具起点、朝向、归属、接触、终点和下一镜继承是否清楚"},
          "visual_beauty": {"score": 1, "reason": "构图层级、光源、遮挡或景别选择如何服务本镜"},
          "overall": {"score": 1, "weakest_point": "本镜最可能导致T2V抽卡或成片平淡的单一点", "first_pass_check": "人工首轮应优先检查的画面状态"}
        },
        "pressure_release_design": {
          "pressure_source": "压力来自谁想完成什么、被什么阻挡、代价如何逼近",
          "pressure_object": "本镜唯一压力物或压力机制，如已确认药瓶、门外脚步、倒计时、封条、门把、屏幕亮起；无则写none并说明",
          "escalation_steps": [
            {
              "time_range": "1.0-2.0秒",
              "visible_change": "压力升级的可见变化，如拇指停在瓶盖边缘、封条裂口露出、脚步声逼近、视线第一次离开道具",
              "audience_question": "观众此刻被迫追问的问题"
            }
          ],
          "release_trigger": "释放或打断压迫的可见触发，如瓶盖被拧开/被脚步声打断/角色移开视线/硬切到门口",
          "release_mode": "action_completion | interrupted_release | attention_shift | cost_reveal | delayed_release | split_release | release | none",
          "release_result": "释放后的可见终态，不是情绪词；例如药瓶仍在手中未开、A视线转向门口、门外脚步成为下一镜压力",
          "split_threshold": "若同镜同时包含第二个动作目标、第二次注意力交接或拿药+转向门口等双状态变化，拆成下一主镜"
        },
        "performance_priority": {
          "primary": "角色A",
          "supporting": ["角色B"],
          "background": []
        },
        "action_budget": {
          "primary_action_count": 1,
          "emotion_turn_count": 1,
          "supporting_reaction_count": 1,
          "physical_camera_move_count": 1,
          "editorial_response_count": 0
        },
        "start_state": "",
        "end_state": "",
        "performance_causality": {
          "tension_intent": "latent",
          "trigger": "",
          "response_order": [],
          "physical_logic": "",
          "motion_boundary": "",
          "hold_strategy": "",
          "end_residue": ""
        },
        "performance_contract": {
          "tension_intent": "latent",
          "trigger_event": "",
          "trigger_time": "1.2秒",
          "inner_emotion": "角色未说出的具体内在需要、恐惧或矛盾；仅作推导",
          "display_intent": "角色主动展示给对手看的外在态度或控制策略；仅作推导",
          "mask_leak": "内外差异从手、眼、下颌、呼吸、道具或重心泄露的一个可见证据",
          "start_intensity": 1,
          "end_intensity": 3,
          "emotion_delta": 2,
          "primary_expression": "",
          "primary_body_action": "",
          "eye_focus": "",
          "reaction_delay": "",
          "voice_or_breath_control": "",
          "viewer_empathy_anchor": "",
          "readable_image_moment": "",
          "visual_progression": "",
          "suppression_or_release": "",
          "camera_pressure": "",
          "scene_pressure": "",
          "end_residue": ""
        },
        "continuity_contract": {
          "start_anchor": "",
          "end_anchor": "",
          "position_continuity": "",
          "eyeline_continuity": "",
          "prop_state": "",
          "lighting_continuity": "",
          "next_carryover": "",
          "state_change": false,
          "state_transitions": [
            {
              "subject": "发生变化的人物、视线、重心或道具",
              "from_state": "变化前的可见状态",
              "intermediate_state": "从起态到终态之间的可见承接，如手伸向、指尖接触、头部半转、肩线跟随",
              "to_state": "变化后的可见状态",
              "cause": "触发变化的可见动作、接触、人物走位或明确转场",
              "time_range": "1.2-2.0秒"
            }
          ]
        },
        "reroll_control": {
          "risk_level": "medium",
          "identity_anchor": "",
          "motion_anchor": "",
          "scene_anchor": "",
          "camera_anchor": "",
          "risk_reason": "",
          "mitigation_steps": [],
          "manual_first_pass_check": false
        },
        "listener_reaction_plan": {
          "speaker": "角色A",
          "listener": "角色B",
          "trigger": "角色A说到关键事实后的0.2秒",
          "time_range": "1.4-2.2秒",
          "visual_evidence": "角色B先把视线从角色A嘴角移到其眼睛，拇指在已确认的杯沿轻收一次",
          "motion_limit": "只允许一次低幅手指收紧，不起身、不转向抢画面",
          "lip_sync": false,
          "end_residue": "角色B口型闭合，手仍停在杯沿，视线留在角色A方向"
        },
        "dialogue_events": [
          {
            "ref": "D1",
            "kind": "台词",
            "speaker": "角色A",
            "text": "原始台词逐字保留",
            "time_range": "0.8-2.6秒",
            "speaker_visibility": "visible",
            "facial_state": "",
            "body_state": "",
            "delivery": "",
            "breath_pause_plan": "",
            "line_function": "probe | pressure | deny | verify | interrupt | farewell | conceal | reveal | plead | deflect | reconcile | narrate | warn | challenge | answer | confess",
            "subtext": "本句没有明说的具体意图、防御或关系动作，不得复述原台词",
            "stress_words": ["逐字来自原台词的1-3个词组"],
            "subtext_visible_evidence": "潜台词转译出的手眼、呼吸、道具、距离或听者反应；不可见且无承接人物时说明N/A",
            "turn_relation": "initiate | respond | deflect | interrupt | withdraw | bridge | continue",
            "conversation_mode": "clean_turn | overlap | interrupted | unfinished | self_correction | non_answer | source_supported_other",
            "response_latency": "0.3秒；立即；或无延迟",
            "overlap_or_interrupt_window": "clean_turn写none；其它模式写源文支持的具体时间窗",
            "conversation_source_basis": "引用源文中抢话、停句、打断、自我修正或答非所问的原句/动作依据",
            "lip_sync": true
          }
        ],
        "dialogue_refs": ["D1"]
      },
      "generation_control": {
        "mode": "t2v",
        "audio_enabled": true
      }
    }
  ]
}
```

- batch 顶层不能出现 `items` 或其他键。
- 每个 dispatch subshot 恰好输出一次，顺序一致。
- 输出必须以 dispatch 的 `composer_scaffold_path` 为骨架；`shot_id/subshot_id/duration/negative_prompt/qa_metadata.dialogue_refs/qa_metadata.dialogue_events[].ref|kind|speaker|text/generation_control` 是确定性锁定字段，Agent 不得改写。
- 相同场景的画幅、风格、服装、共享光源与空间锚点只从 `scene_lock_cache_path` 读取一次；各镜通过 `scene_lock_ref` 引用，不重复推导场景不变项。
- `mode` 必须固定为 `t2v`，且 `generation_control` 不得出现素材、路径或引用字段。
- `temporal_transition_contract` 是每镜必填合同。它只能消费派发骨架中的源文候选：没有候选时 `kind=none` 且不得启用；`memory_flashback` 只适用于明确回忆且存在可拍过去事实；`story_event_transition` 只适用于源文事件确实造成场景、意识、时空或人物状态切换。候选并不强制特效，Master 可以在 `decision_reason` 说明为何正常切换更忠实。启用时必须先写 `effect_source_basis`，再根据当前事件配置一个且仅一个效果；它不得来自固定白名单、通用模板或无关风格。合同还必须有不超时的时间窗、前后状态、声音桥、`lip_sync=false`、逐字出现在 `full_prompt` 的 `prompt_anchor` 与降级方案；不得叠加效果、虚构回忆事实。所有已启用的合同一律 `high` 抽卡风险且 `manual_first_pass_check=true`。

### B2. full_prompt 五段

`full_prompt` 必须且只能包含：

1. `生成规格：...`
2. `主体与空间锁定：...`
3. `主镜头连续规则：...`
4. `子镜头组：...`
5. `光照、声音与稳定约束：...`

段间恰好一个空行。禁止旧版八字段、模板编号、自包含验证、负面词、QA 结论和工程字段。

#### 主体与空间锁定

- 以 `{canvas}画幅，{visual_style}` 开头。
- `主体与空间锁定` 不得出现图片、视频、素材槽位或外部引用标记。人物一致性只能依靠固定身份锚点、服装、屏幕左右、朝向、场景锚点和上一子镜终态。
- `{canvas}` 与 `{visual_style}` 只能来自当前项目配置或 scene lock cache；不得沿用任何示例的项目限定词。
- 只写本镜必须锁定的主体、服装、站位、朝向、场景接触和身份连续性。
- 场景不变项只写一次，不重复灯光和动作过程。
- 有人物时提供一项真实场景接触：脚底/椅面/桌沿/道具/接触阴影/前景遮挡/环境反射。
- 多人、画外人物或本场人物多于本镜可见人物时，段首必须先写当前可见人数闸门：本镜画面内可见人数、清晰主体、肩线/背影/倒影/虚化人物、画外声音分别是谁。`performance_priority` 的 primary/supporting/background 必须与该可见人数完全一致；画外声、OS/OV、非实体声音只进入 `dialogue_events.speaker_visibility`，不进入可见表演分区。
- 物理槽位先于屏幕左右：先写柜台内侧/外侧、桌同侧/对侧、车门内外、床/沙发/吊椅支撑点、门口/走廊动线等关系坐标，再写画面左/中/右和前中后景。禁止只用“A左B右、面对彼此、旁边、后面、附近”替代可画出的拓扑。
- 系统声、系统提示或悬浮文字只允许作为画外声、界面层或侧边安全区彩色悬浮文字出现；不得实体入画、遮挡人物脸部、压住口型或破坏主表演焦点。手机聊天消息、来电名称、通知弹窗等 UI 文字若由 AI 直接生成，必须声明独立二维浮层、安全区、不属于手机屏幕、不贴手机背面、不跟随手机透视中的至少两项；若无法稳定表达，则把具体文字留到后期文字表，不进入 `full_prompt`。
- 既定室内/酒店等空间必须保持结构、入口方向、主要物件与屏幕左右关系稳定；“不穿越空间、不改变空间结构”只作为低优先级稳定约束，不能覆盖已声明的走位、硬切、重构图或跟随路径。
- 三人或多人镜必须写成可执行屏幕坐标。例如：角色A在画面左侧中景，身体朝向画面右侧；角色B在画面右侧中景，身体朝向画面左侧；角色C在画面中间偏后景，站在桌子后方，身体朝向画面前侧略偏左。三人形成 A左、B右、C中后方 的三角关系；C不穿过A与B之间的屏幕空间线。该模板只迁移空间语法，不迁移具体场景和人物关系。

#### 主镜头连续规则

使用顺序：

```text
时长：5.0秒。景别：中近景。焦距：50mm。机位：……。轴线：……。主要运镜：固定，落幅时轻微收紧构图……。
```

- 段内必须先写单一剧情问题与触发，再写空间/道具总锁，最后写运镜响应与禁止变化项。运镜必须是对情绪、道具、视线、台词或动作落点的响应，不能先于触发出现。
- `continuous_take` 使用一种主要运镜、任一时刻一个注意力中心、一个落幅；必须写清固定机位的允许运动或唯一已授权运动，禁止未声明的摇移、跟拍、变焦或拉焦。同一互动链允许一次由台词/动作触发的 `A→B` 注意力交接。`shot_group` 可在同一剧情目标内由表演链重音带出自然景别变化、反打或移镜；每个内部节拍仍只有一个主体，并沿用同一人物、道具、轴线与光源状态。
- 禁止只写“聚焦甲/聚焦乙”或“保持虚化”；必须写可见构图权重、前后景谁实焦/谁轻度虚焦或焦外、焦点是否稳定、摄影机方向与最终双人或关系落幅。
- 稳定控制优先级固定为：本段戏剧主体与实焦 > 已声明运镜/切换 > 空间结构与屏幕左右连续 > 通用固定机位/轻微推近控制。不得让通用的“固定、微推、不摇移”否定已声明的硬切、重构图、跟随或焦点转移。
- 数值只保留 1–2 个决定性锚点；不堆 mm、度、速度和距离。
- `dramatic_goal` 留在 QA 元数据，不重复写入模型提示词。
- Master 必须落实 `viewpoint/visual_hierarchy/entry_strategy/reveal_strategy/focus_strategy`。人物跟随属于合法单一运镜；采用跟随时，以起幅、路径和落幅锁定空间，不得同时声称固定机位或固定框景全程不变。

#### 子镜头组

- `continuous_take` 使用 1 个从 `0.0` 覆盖到镜头总时长的连续时间段；`shot_group` 使用 2–3 个连续小数秒时间段。两种模式都不得断档、重叠或倒置。
- 每个时间窗必须按“承接上一落幅 → 人物位置/朝向/视线 → 道具位置/朝向/接触状态 → 唯一触发/动作 → 情绪可见证据 → 镜头响应 → 结束状态/下一镜继承 → 禁止变化项”组织；禁止把空间、道具、情绪和运镜混成一句无法追踪状态变化的形容词堆叠。
- 面向短视频生成平台时，段内语序优先为：景别可见主体 → 触发动作 → 表情控制 → 肢体承接 → 语气/呼吸/口型 → 必要动态稳定约束。该语序必须嵌入现有五段结构，不新增“动态约束”独立段落。
- 每段按 `可见触发 → 主角身体反应 → 对手必要反应 → 镜头落点` 写。
- 每段只保留一个实焦主体。若该段的画面证据是主角的眼神、手部或关键道具，则这些可成为同一近距离焦平面的实焦；若该段承担另一人物的揭示，则该人物为实焦，主角只能作为轻度虚焦的前景或背景空间锚点。背景人物以焦外、不出现可辨认五官、不抢焦点控制，禁止要求所有人物同时清晰。
- `shot_group` 的切换在对应时间段内写明转场类型与触发。使用硬切时，写“于 X.X 秒由〔具体视线/动作/台词〕触发无转场硬切”，随后立刻写切后景别、实焦主体、屏幕位置、轴线和承接状态；不得用“明确剪切”代替这些事实。
- 插入镜作为 `shot_group` 子镜时必须写清插入功能：`信息补充 / 情绪放大 / 节奏切割 / 视线引导 / 转场缓冲 / 环境残压` 中的一项，并在该段正文中落地具体新信息或状态变化。3–6 秒主镜最多 1 次插入；6–10 秒最多 2 次；10–15 秒仍受 3 个子镜总量限制。插入镜不得连续使用人物脸部大特写，不得无触发切入静态空镜。
- 凡出现躺、伏、靠、抱、扶、摔倒、翻身、坐起、起身、披衣、开门、下车、递给、收起、离开、手机响、屏幕显示、人群围观等概括动作，必须在时间窗中翻译为 `起点 → 支撑/接触/方向 → 可见转换 → 稳定终态 → 下一镜继承`。支撑姿态要写头部、肩背、腰臀、双腿、双脚、支撑点、接触点和非接触边界；道具/衣物/门车门/UI 要写起点、接触者、方向、移动路径、松手或终态。
- 每个人物镜必须有一个观众可直接读懂的共情锚点和画面可读瞬间：先明确角色此刻被什么刺中、想护住什么、怕失去什么或正在忍住什么，再落成一个可见证据。共情锚点不能是“观众共情、感染力强、情绪到位”等结果词。
- 现代都市剧情人物镜默认表演克制：不用夸张瞪眼、扭曲表情或大幅肢体动作；以当前景别可见的眼神停留、呼吸变化、手部/关键道具力度、肩背姿态和重心微调承载情绪。原文明确要求夸张喜剧、惊吓或肢体爆发时，以原文事件为准。
- 画面可读瞬间只选 1 个主证据并贯穿时间轴，如手停住、视线避开、肩背收紧、呼吸断半拍、道具状态改变或空间距离被压缩；不得为了画面感堆叠过多表情/肢体细节。
- 先按原剧情选择 `neutral / latent / rising / peak / release` 张力意图；不得默认把每镜都做成高张力，也不得用增加动作数量替代张力设计。
- 每镜还要在 `tension_curve_role` 或 `source_constraint_basemap.tension_curve_role` 中标记铺垫、升压、峰值、释放或缓冲。相邻镜头不得连续用强推近、强表情、强停顿堆高压；强张力后必须给短余波、关系缓冲或明确的悬置理由。轻对白也要保留一个非台词张力点，例如手停在杯沿、视线没有接住、道具未被交出或空间距离被压缩。
- 触发发生在时间段内部时必须写明确时点；角色反应要区分直接感知触发与观察他人后再反应，禁止无依据的多人同步启动。
- 突发、短促、立即类动作应在所属时间段前部完成接触点、转折点或制动点，并为受力、回稳和终态残留保留时间；原文明确缓慢动作时除外。
- 接触、阻挡、受力或截停的结果必须匹配接触点、支撑关系、受力方向和重心。杠杆不足时写提示、警告或角色主动收住，不得写成不可信的强制位移。
- 中断动作必须分别写清被取消的主运动与仍允许的残余运动；后段相似方向动作必须以幅度、身体部位或目的区分，禁止完整重做已被截停的动作。
- 长停顿占镜头超过约三分之一或持续超过 1.5 秒时，只保留 1–2 个景别可见的生命迹象，或给出有意静止的剧情理由；不得用密集微动作破坏静止状态。
- 3–6 秒镜头：主动作≤1、情绪转折≤1、对手反应≤1、主要运镜≤1。
- 6–10 秒镜头：主动作≤2、情绪转折≤1、对手反应总数≤2、主要运镜≤1。
- 10–15 秒连续互动：允许 2–3 个因果相接的内部节拍、多个短台词轮次和一次因果注意力交接。`continuous_take` 保持一条摄影机轨迹；`shot_group` 可由表演重音带出 1–3 个自然景别/视角变化。两者都只能服务一个整体戏剧目标；第二个独立戏剧目标、无触发的反复抢焦或无关动作链必须拆镜。
- 时长服务于可见事件，不服务于氛围填充。单一微表情、一次视线变化、静态压场、群体凝视或落幅余韵默认不得超过 `project_config.max_static_shot_duration`（默认 6 秒）。落幅残留是承接下一镜的终态，不是额外延时。
- Orchestrator 只能把同一 `narrative_beat_id` 内因果连续的可见片段打包到平台上限内，再以内容所需时长落定，不强行补满。每镜记录 `duration_strategy=pack_toward_limit`、`justified_content_duration`、`utilization_ratio`、`duration_rationale` 与 `dramatic_beats[]`。超过静态上限时，rationale 仅允许 `continuous_dialogue / continuous_interaction / continuous_action / sustained_reveal`；6–10 秒至少 2 个可见因果片段，10–15 秒至少 3 个。不得以“压迫感、静默、停顿、余韵、保持状态”作为理由。
- Orchestrator 不得只识别带 `△/动作：` 前缀的动作；同一源文中的普通无前缀剧本动作、起幅状态、声音触发、道具变化和台词后反应也必须进入 `source_ledger` 与 `dramatic_beat_ledger`。Preflight 要求每个 `type=action/dialogue` 的 source ID 被一个计划节拍引用，缺失时报 `SOURCE_UNIT_UNASSIGNED`，防止解析成功但漏拍源文。相邻低风险起幅状态、声音触发和台词后反应可在同场景、同一叙事目标且总时长不超限时与对白/OV合并；强动作、第二动作链、不同场景或超时必须保留独立镜头。
- OV 说话者是声音来源，不得写入 subshot `characters/visible_characters`；若同镜有源文支持的闭口承接人物，只锁这些实际入画人物。纯 OV 镜允许可见人物列表为空。OS 可按源文把内心声归属者锁为闭口可见人物，但仍不得驱动口型。
- 有意静止仍可用于屏息、庄重或对峙，但必须在短镜内完成；若静止本身构成持续事件，`dramatic_beats[]` 必须写出期间发生的可见信息变化，而非重复“人物保持不动”。
- 打斗镜优先作为一个不切镜的连续动作链：≤6 秒最多 1 个接触节拍、6–10 秒最多 2 个、10–15 秒最多 3 个；所有节拍必须因果相接并共享同一主要摄影机轨迹。攻防双方之间的因果注意力传递不算独立换焦；换轴、切到独立主编舞链/戏剧焦点、换场景、第二条无关动作链或超过 15 秒才拆片段。
- 打斗镜按平台稳定性控制速度、幅度、接触节拍和镜头抖动；当动作复杂度超过单条可稳定生成范围时，必须在 `fight_continuity` 中锁定连续片段，或拆成下一生成片段。
- background 只写群体低幅连续状态，不逐人分配动作。
- 每个台词/OS/OV/系统音事件按 `qa_metadata.dialogue_events` 执行；`ref/kind/speaker/text` 不得改写，语气控制不得通过改标点或增删文字污染原文。
- `audio_enabled=true` 时，原文必须逐字且只出现一次，并且只放在子镜头组。统一格式为 `{人物}（台词/OS/OV/系统音）: "{原文}"`，必须使用半角冒号、一个空格和英文双引号包裹原文；同一事件紧接人物神态、身体状态、说话语气、气口和口型边界。系统音的说话者为源文设备/系统标签，`speaker_visibility=nonphysical`、`lip_sync=false`，不进入可见人物锁。
- `audio_enabled=false` 时，原文不得进入 `full_prompt`；子镜头组仍写可见人物的神态、身体状态及台词口型边界，原文和配音控制保留在 `qa_metadata.dialogue_events` 与制作表。
- 可见台词人物按原文同步口型；可见OS/OV人物口型闭合。画外或非实体发声者不驱动任何可见角色口型；非说话 focus 角色口型闭合，背景统一无同步口型。
- 每条台词 `time_range` 必须容纳按本镜 `delivery` 语速、原文字符与标点、`breath_pause_plan` 句前/中段气口和句末收气计算的自然表演时长。两个 `speaker_visibility=visible` 且 `lip_sync=true` 的时间窗不得重叠；可见对白必须同时写口型同步和句末闭口/口型闭合落幅。容量不足时按源文可拆分句或拆主镜，不得删词、改标点、省略气口或强制超常快语速。
- 终态必须是画面可见状态并能承接下一镜，同时保留上一事件造成的姿态、接触、重心、视线、呼吸、道具或空间距离残留；除非剧情明确复位，不得落成“无事发生”。需要戏剧停顿时，最后短时间窗保持镜头稳定、人物动作自然减缓并留下 1–2 个可见生命迹象；除非源文明确要求，禁止“画面定格/冻结”或人为慢动作，以免卡帧、拖影或肢体僵硬。

#### 光照、声音与稳定约束

- 光源方向、色温、软硬和人物/环境同源关系保持跨镜连续。
- 光线风格服从当前剧本和项目配置；不得把任何示例的光线、空间、节奏或色调作为默认光声方案。
- 未指定更强题材调性时，现代都市关系镜保持精致都市剧情感与克制的社交压迫或尴尬感；不得自动渲染为惊悚、强暧昧或夸张喜剧。只有源文明确建立对应关系和强度时才提高其权重。
- `audio_enabled=true`：写关键环境声、声音同步关系及必要声部层级；原始台词/OV/OS已在子镜头组逐字出现，本段不得重复。原文台词、OS 或 OV 为前景主声，关键动作声为次级同步声，环境声为低频底噪；音效最多保留 1–2 个叙事事件，且不得覆盖原文人声或凭空新增人声。
- `audio_enabled=false`：只写光照；台词与音频计划留在 `qa_metadata`/制作表，不占模型提示词。

### B3. 表演角色优先级

- `primary`：唯一主表演者，获得完整起始—触发—泄露—终态链。
- `supporting`：只对主事件做一次因果反应，不发起竞争动作。
- `background`：保持空间连续、低幅活动、无同步口型，不逐人写微表情。
- 每个可见角色必须且只能被分配到一个层级。

### B4. 动作预算与长度

- 长度是信息密度诊断，不是审美配额：环境/物件 200–700 字；3–6 秒简单动作 300–900 字；3–6 秒对白/情绪 400–1100 字；6–10 秒表演 500–1400 字；重要出场/关系建立 600–1600 字；10–15 秒互动 800–2000 字；复杂连续动作 900–2200 字。
- 上述范围全部是 soft guidance。只有 `project_config.prompt_limits.hard_max_chars` 或平台适配配置明确给出硬上限时，超过该值才 blocking。
- 不因软区间溢出单独拆镜。拆镜理由只允许：多个戏剧目标、动作预算溢出、重复注意力交接、竞争运镜、不可兼容空间状态或平台硬上限溢出。
- 不能通过增加背景微动作、光学数字、重复状态或 QA 文案凑字数。
- `duration_design` 只属于 Orchestrator 时长门禁和 QA，不得写入 `full_prompt`；其节拍必须能被 Master Production 时间轴追溯。

### B5. 景别可见性

- 大远景/全景：走位、重心、轮廓、衣摆、人与空间关系；禁止瞳孔、虹膜、眼睑、鼻翼、唇线和咬肌细节。
- 中景：肩线、重心、手臂、头部转向、可见呼吸；禁止瞳孔、虹膜、鼻翼和眼神光细节。
- 中近景：视线、手、肩颈、呼吸、口型。
- 特写/大特写：眼周、嘴角、下颌、口型；避免大幅位移和竞争运镜。

### B6. negative_prompt

- Master 精确输出 `{{NEGATIVE_PROMPT_AUTO_INJECT}}`。
- `full_prompt` 中不能出现负面提示词标题或占位符。
- 归一化脚本按普通、多人、对白、参考驱动和打斗上下文注入精简词组；通用负面词覆盖肢体、手部、五官、身份漂移、帧间闪烁、光影突变、物体消失、穿插、口型、水印和画风突变等崩坏维度。
- 负面词只写不希望出现的概念，不写“禁止……”式正向命令。

### B6.1 当前镜头剧情关键帧与自动空间分镜图导出

Export 可从已验证的主镜、连续性合同和 `static_aesthetic_contract` 自动派生“当前镜头剧情关键帧”提示词。它是一张静态生图提示词，只锁定当前主镜最关键的单一剧情瞬间：观众认知落点、人物关系、关键道具归属、情绪证据、镜头构图和尾帧残留。它不属于 `full_prompt`、`negative_prompt` 或 `generation_control`，不改变 T2V 契约，也不要求 T2V 使用图片参考；不得写成九宫格、P01-P09、多格分镜、首尾帧、I2V 或参考素材槽位。关键帧先消费视觉意图、构图层级、动机光、色彩分离、焦平面、空气层和记忆帧，再编译本帧人物身份、道具、功能面、支撑与透视硬事实；不得把内部校验术语直接当作画面描述。

Export 也可从已验证的主镜和连续性合同自动派生“人物站位空间分镜图”提示词。只有当人物/道具状态变化、服装/道具交接、多人左右站位、可见走位、硬切/重构图/跟拍或多层景深关系提高位置穿帮风险时导出。每个被选中的主镜导出：一条垂直正交俯视空间调度图提示词、一条横向人物站位姿态参考图提示词和一条分镜图负面词。两条提示词必须复用本镜可见的场景锚点、人物、左右、朝向、道具和摄影机关系；信息缺失可标为合理空间推断，但不得新增剧情人物、道具或动作。Markdown 将它们置于对应主镜的即梦操作卡后，供用户结合场景图和人物图生成辅助图。

### B7. qa_metadata

- 只用于制作和验证，不投喂视频模型。
- `dramatic_goal` 必须是本镜具体目标。
- `dramatic_design` 必须包含镜头功能、叙事权重、唯一信息增量、反应归属、唯一 `narrative_beat_id`、本节拍内部 `dramatic_beat_ids` 与 `visual_punctuation`。每个 beat ID 必须在 `dramatic_beat_ledger.json` 中唯一归属于当前子镜，且新生成的 shot plan 应让同一主镜内的 beat ID 共享同一个 `narrative_beat_id`。`dramatic_beat_ids` 和 `duration_design.dramatic_beats` 只证明该单一剧情节拍的起势、承接、转折或落幅；若出现新的事件目标、主动作链、反应归属、情绪结论、第二次人物注意力交接或需要回切的独立反打，必须拆成下一主镜。high/critical 重要出场的 `visual_punctuation` 必须从 `occlusion_reveal / low_angle_scale / foreground_reaction / camera_follow / light_reveal / stop_mark / rack_focus` 中选 1–2 项；其他镜可为空。
- `story_punch_contract` 是防止“合规但平”的轻量戏眼合同。人物、对白、道具变化、`rising/peak` 或高叙事权重镜必须填写：观众问题、人物压力、可见压力物、剧情转折、画面标点、唯一构图优先级、运镜动机和尾帧残留。`composition_priority` 必须写主体与前中后景、画面位置、留白、遮挡、距离或焦点关系；`camera_motivation` 必须写唯一运镜/固定策略及其响应的表演、台词、道具或空间因果。它不允许新增剧情设定；所有字段必须来自源文、`dramatic_design`、`emotion_driver`、`performance_contract` 或 `continuity_contract`，并把可见部分落到 `full_prompt`。环境/纯物件低风险镜的 scaffold 不提供此字段，输出必须省略。
- `duration_design` 必须逐字继承 Orchestrator 的时长策略和依据；低利用率本身不是错误，缺少内容依据或用静态余韵填充才是错误。
- `source_constraint_basemap` 是生成前底图，可包含 `space_basis/state_prop_basis/character_orientation_basis/tension_curve_role/sound_lip_sync_basis/screen_text_policy/single_shot_risk/visible_people_gate/performance_baseline_lock/emotion_micro_chain/dialogue_performance_kernel/emotion_residue_contract/physical_structure_chain/shot_component_choice/viewpoint_motion_lock/premium_director_polish/creative_profile`。它用于减少返工和帮助 Editor 复核，不能作为模型提示词正文输出。`visible_people_gate` 写本镜可见人数、清晰/肩线/虚化/画外分类；`performance_baseline_lock` 写主要人物的常态控制方式、优先泄露部位、默认动作幅度、爆发阈值和禁用表演习惯；`emotion_micro_chain` 写本镜情绪触发后选择的 3–5 个微动作；`dialogue_performance_kernel` 写台词功能、说话者口型、关键词重音、听者低幅反应、句末闭口和余波落幅，无对白写 none；`emotion_residue_contract` 写触发前状态、泄露部位、压抑/释放方式和尾帧残留，无情绪承接写 none；`physical_structure_chain` 写本镜所有概括动作的起点、接触、转换和终态；`shot_component_choice` 写本镜采用的唯一镜头组件或明确写 none；`viewpoint_motion_lock` 在使用特殊视角时写摄影机绑定关系、相对高度/距离、唯一主路径、速度曲线、至多一次焦点交接、稳定落幅和降级/拆镜阈值，不使用时写 none；`premium_director_polish` 写即梦友好卡的前台精修目标，不新增模型事实；`creative_profile` 只能为 safe、balanced 或 expressive，且不得降低任何质量门槛。
- `scene_tone_palette` 必须包含 `space_id/space_master_sentence/tone_palette/light_texture_purpose/visual_scene_prefix`，并逐字承接 Scene Lock 的六项生活化景深事实：`foreground_layer/midground_layer/background_layer/genre_visual_signature/lived_in_detail/depth_focus_policy`，以及七项风景导演事实：`landscape_identity/landscape_composition/natural_motion_system/environment_story_arc/reveal_order/light_weather_progression/breathing_policy`。前景写靠近镜头的框景、局部遮挡或轻虚化材质；中景写人物活动区、接触面和关键道具；后景写纵深结构、出口或低幅环境；题材视觉气味必须转成建筑、陈设、天气、时代、职业或光色证据；生活痕迹只选1–2项真实磨损、使用状态或自然活动；景深策略明确实焦层、焦外层、遮挡和空气透视。风景身份统一地域、季节、时段、地貌/建筑、植被水体与人类痕迹；风景构图锁定主形体、地平线或空间分割、引导线、视觉重心和留白；自然运动写风、叶、草、水、云雾、雨雪与人群的统一方向及不同响应速度；环境弧写起态→剧情触发后的变化→余波；揭示顺序写先看见→后发现→最终停留；光候演进只允许有因果的时段/天气/光线变化；呼吸策略分配建立镜、人物镜与缓冲镜的信息密度。正文仍只落实前中后景中至少两层、题材或生活痕迹一项、虚实主次一项，并按环境镜至少两项、人物镜至少一项消费风景身份/构图/自然运动/揭示/光候事实，不得逐镜复制全部场景资产。推荐额外包含制作级色卡扁平字段：`mood_function/main_color/support_color/accent_color/color_temperature_range/key_light_direction/shadow_color/contrast/saturation/skin_tone_protection/material_reflection/allowed_variation/forbidden_color_pollution`。
- `character_scene_objective_contract` 是人物戏剧行动合同，人物表演镜必须填写：`focus_character/scene_objective/stakes/obstacle/active_tactic/visible_tactic_evidence/tactic_shift/knowledge_gap/power_state_change/end_action_state`。`scene_objective` 写角色本场要从对方或环境获得的具体结果；`active_tactic` 写角色正在采取的关系动作；`tactic_shift` 写失败/触发后改用的策略，若不切换则写明维持原因；`knowledge_gap` 写人物之间知道、误判或隐瞒的差异；`power_state_change` 写本镜前后谁占主动。目标、代价、信息差和权力分析不进入正文，只有可见策略证据与行动落幅必须逐字或等价落实。
- `relationship_emotion_arc` 是对手戏关系弧合同，关系参与者超过一人时填写：`participants/start_relation_state/conflicting_wants/emotional_misalignment/turn_trigger/power_shift/end_relation_state/shared_residue`。它必须回答双方要什么、情绪为何错位、哪个可见触发改变权力、关系在落幅形成什么新状态；不得用两个独立的 emotion delta 代替关系变化。`turn_trigger` 和 `shared_residue` 必须落实到当前动作、距离、道具、声音或落幅。
- `sequence_directing_plan` 每镜必填：`scene_visual_argument/sequence_position/distance_lens_stage/composition_motif_state/rule_break_or_hold/blocking_camera_coordination/environment_beat/handoff`。`sequence_position` 只允许 `establish/hold/escalate/break/release/resolve`；同场镜头应形成建立→保持/推进→破格→释放/解决的视觉句子。构图母题、联合调度与环境节拍至少两项落实到正文，避免每镜各自“有动机”却没有整场镜头语法。
- `cut_decision_contract` 每镜必填：`cut_mode/trigger/pre_cut_hold/information_gain/sound_strategy/economy_reason/fallback`。`cut_mode` 只允许 `hold/action/reaction/dialogue/sound/delayed/match/scene_transition`；非 hold 必须由正文中可见动作、反应、声音或台词落点触发，并说明切后新增信息；hold 必须说明连续保持带来的叙事收益。该合同只用于剪辑决策，不得把“切到/剪辑/反打”等元叙述写进 direct-copy。
- `prompt_information_budget` 每镜必填：`profile/primary_render_task/must_render/supporting_visual/metadata_only/visual_enhancer_limit/compression_rule`。`profile` 只允许 `environment/object/action/dialogue/dramatic`，`visual_enhancer_limit` 只能为1或2。`must_render` 中以分号/竖线/换行分隔的每项硬事实都必须落实到 `full_prompt`，不能用命中其中一项冒充完整；`metadata_only` 不得原样泄漏，`compression_rule` 必须明确整句删除与保留顺序。先保护源文、口型、动作终态、空间与唯一主任务，再按镜型选择辅助风景/表演/材质；导演分析、关系判断、知识差、分值与风险结论只留元数据。新增合同不得成为延长直投正文或挤压人物、台词、关键道具的理由。
- `sound_directing_plan` 每镜必填：`primary_source/source_direction_distance/room_environment_response/foreground_background_priority/silence_or_drop/lead_lag_strategy/cut_support`。原生音频关闭时保留为配音/后期元数据，不强行进入 T2V 正文；开启时至少一项方向距离、房间响应、静音或声音先入/延后退出必须落实到声音段。对白优先，环境声与音乐按情绪和切点 ducking；不得用抽象“高级氛围音乐”代替空间声源和声画因果。
- `character_voice_lock` 是角色声音锁定字段，可按项目或镜头保存稳定声音依据：`character/timbre/pitch/speed/volume/articulation/breath_texture/ending_habit/emotion_ceiling/forbidden_voice_shift`。单镜 `dialogue_events.delivery` 只写本镜因情绪产生的语速、音量、气口、停顿、咬字或尾音微调；不得每镜重新发明人物声音。没有原生音频时仍可保留为配音制作元数据，但不得进入 T2V 正文制造口型。失望无奈、伤心怨恨、悲伤痛苦等情绪若伴随台词，声音只做轻声、短促、发紧、气口或尾音变化，并必须和闭口/开口边界一致。
- `screen_text_policy` 可包含 `mode/text_refs/render_rule/safe_area/perspective_rule`。当 mode 为 AI 生成 UI 文字时，`full_prompt` 必须写清独立二维浮层、安全区或透视隔离；当 mode 为后期叠字时，具体文字不得进入模型正文。
- `tension_curve_role` 标记本镜在连续张弛曲线中的功能：setup/rise/peak/release/buffer 或中文等价描述。它不强制每镜高张力，只帮助防止连续镜头都强推、强表情或强停顿。
- `cinematic_image_contract` 是写实影像/高质感镜头的正式合同，可包含 `composition_anchor/lens_depth/exposure_contrast/color_separation/atmosphere_layer/material_detail/imperfection_map/realism_risk/signature_frame`。它不是堆“电影感、高级感、真实感”，而是把画面质感拆成可见证据：前景遮挡或引导线、焦平面和焦外层、不过曝亮部与保留黑位的暗部、冷暖或局部强调色分离、雨雾尘/水汽等空气层、墙皮/皮肤/衣料/金属/玻璃/水渍等材质，以及划痕、磨损、不均匀反光、断续水痕等非完美随机性。`realism_risk` 用来列出本镜最容易生成的 AI 味，例如镜面水面、塑料墙、均匀雨线、过度霓虹、过曝灯管、虚拟摄影棚感；这些风险不得作为正向画面描述出现。
- `video_texture_contract` 是整条视频/同一场景的运动质感合同，可包含 `look_profile/exposure_policy/material_motion_policy/atmosphere_motion_policy/camera_stability_policy/continuity_carryover/risk_controls`。它解决的不是“单帧是否好看”，而是视频播放时光色、黑位、材质反光、雨雾尘运动、镜头运动和跨镜质感是否稳定。`risk_controls` 可列出镜面水面、塑料墙、均匀雨线、过曝灯管、贴图跳变、廉价CG感等风险；这些风险不得作为 `full_prompt` 正向描述出现。启用后每镜只落地 1–2 个运动质感锚点，例如灯不过曝、积水碎反光随涟漪断续移动、雨雾贴地缓慢扩散、镜头固定或低幅缓慢运动、跨镜保持同一光色与黑位。
- `visual_bible` 是项目/场景级审美事实源，包含 `visual_thesis/palette_system/light_motivation/contrast_exposure/composition_grammar/material_world/atmosphere_rule/imperfection_policy/reference_policy/continuity_lock`。它先于单镜构图，不替代 Scene Lock；同一场景跨镜复用视觉论点、色彩职责、动机光、曝光基准、构图家族和材质响应。单镜只消费当前任务需要的一个视觉论点、一个构图决策、一个光影决策和1–2个质感锚点，不得复制全量视觉圣经。
- `static_aesthetic_contract` 用于每个主镜的代表性记忆帧；复杂/高风险镜再据此导出三状态关键帧。字段包含 `visual_intent/composition_hierarchy/light_design/color_grade/lens_rendering/depth_atmosphere/material_anchor/signature_frame/aesthetic_exclusions`。每句光影设计都要说明光源、方向、受光面与阴影后果；焦段、色温、景深要有可见结果；第一视觉落点只能有一个，第二视觉层最多一个。它先生成好看的静态构图，再与人物、道具、功能面、透视和支撑硬事实合并，不能用内部合同词替代具体可见关系。
- `dynamic_aesthetic_contract` 用于 T2V 状态转换，包含 `motion_thesis/start_state/trigger/primary_subject_motion/secondary_environment_motion/camera_path/focus_behavior/material_motion/atmosphere_motion/tempo_easing/end_state/stability_fallback`。每镜最多一个主要人物动作、一个摄影机路径或固定机位、一条因果响应链和一次焦点交接；低风险镜的响应链最多包含两个共享动力源的低幅响应，长对白、多人、道具转移、复杂支撑或腾空镜只保留一个响应，不得形成第二独立动作链。非刻意静止镜的 `primary_subject_motion` 必须是身体/视线/重心/道具可执行动作，并写先后、延迟、余波、减速或稳定落幅之一。摄影机路径必须有剧情动机、起幅、触发、缓急、停点和不漂移锚点。导出编译器会保护一条动态主链和一个静态光影/材质锚点；预算不足时阻断，不静默删除。失稳时先去掉摄影机运动，再去掉第二响应和次要环境运动，不得删除剧情节拍或物理终态。
- `aesthetic_priority` 每镜必填：`visual_thesis/primary_eye_target/secondary_visual_layer/must_preserve/degrade_first`。它与 `prompt_information_budget` 一起决定 direct-copy 取舍：先保硬事实、唯一视觉论点和第一视觉落点，再压缩重复技术词与次要环境层。不得因为合同完整而生成均匀照明、平均构图、多个抢焦点或没有记忆帧的安全画面。
- `editorial_mode` 必须从锁定 shot plan 逐字继承；它决定本镜执行一条连续轨迹，或一组由表演重音触发的镜头响应。
- `camera_beat_map` 与 `sequence_context` 也必须从锁定 shot plan 逐字继承。前者不得由 Master Production 重新发明；后者要求连续拆分从上一段状态起演而非重置。
- `shot_group` 的每个镜头节拍都写明 `time_range/focus_owner/focus_subject/framing/trigger/camera_response/camera_position/camera_movement/transition_type/screen_lock/axis_relation/axis_carryover/carryover/end_frame`；Master Production 将这些信息落到主镜头连续规则与子镜头组，不增加未声明的切换。子镜组是同一 `narrative_beat_id` 的视觉覆盖，不能把两个可独立复述的剧情动作或动作—反应结论并成一个主镜。
- `quality_contract` 由子镜类型确定并从锁定 shot plan 继承。它适用于任何生成模型：环境镜也必须证明叙事功能、视觉锚点、空间光线和转场承接；物件镜证明道具状态与焦点；人物镜证明对应的动作、台词或表演因果。不得因为某项分析被跳过而省略合同要求。
- `ai_model_readiness_score` 是风险触发的 AI 视频大模型可执行性自检，不投喂模型。多人、道具/站位变化、`shot_group`、长台词、`rising/peak` 或高抽卡镜必须逐项给 1–10 整数分；环境、物件、单人稳定低风险镜的 scaffold 不提供此字段，输出必须省略。风险层级只能由 packet 中已锁定的源镜事实计算，绝不能因 Agent 写入的 `qa_metadata` 在回验时升级，保证派发提示和验证门禁一致。启用时用一句具体可见依据或风险解释：场景空间、穿帮风险、情绪可读、张力压迫、运镜服务情绪、道具连续、画面美感、overall。不得全部给 9 分以上，也不得只写“很好、稳定、清晰、有张力、画面好看”等空泛好评。`overall.weakest_point` 必须指出本镜最可能失败的一项，`overall.first_pass_check` 必须写人工首轮优先检查什么，例如人物左右是否镜像、药瓶是否仍在桌角、非说话人口型是否闭合、运镜是否越过轴线或落幅是否继承上一状态。
- `pressure_release_design` 是压迫感制造与释放合同，不投喂模型但必须落地到 `full_prompt`。`rising/peak` 人物镜必须填写：压力来源、唯一压力物或压力机制、1–2 个可见升级点、释放触发、释放方式、释放结果和拆镜阈值。制造压迫时只选一个主压力物，优先使用源文已有道具、门、声音、倒计时、距离或未完成动作；若把普通道具升级为叙事压力物，必须是可见且低抽卡的状态变化，如封条裂口、瓶盖未拧开、杯沿将落未落、屏幕亮起，不得新增无来源的复杂设定。释放压迫不是“气氛缓和”，而是动作完成、被打断、注意力转移、代价揭示、延迟悬置或拆到下一镜。若同一主镜同时需要“拿起道具”和“转向新威胁/门口”，优先按 `split_release` 拆成连续两镜：第一镜完成道具状态转移，第二镜继承落幅后处理转向或新威胁。
- `performance_priority` 覆盖全部可见人物且不能重叠。
- `performance_priority` 只能来自当前镜头的 `visible_characters`：`primary + supporting + background` 的并集必须等于本镜可见人物集合，且三层之间不得重叠。禁止把同场景但本镜不可见的人、画外说话者、上一镜人物或全角色名单写入优先级；画外/非实体声音只进入 `dialogue_events.speaker_visibility`，不进入可见表演优先级。
- 动作/关系阻挡镜的 `coverage_role=relationship_blocking` 或 `movement_transition` 时，不得默认写“中景/中近景固定机位”糊弄稳定性；若确实固定，`full_prompt` 必须给出屏幕左右、前景肩线/遮挡或场景锚点，以及固定机位为何服务接触点、受力方向或终态残留。
- `pressure_release_design.release_trigger` 必须落成 `full_prompt` 中可看/可听/可承接的具体触发物：如手腕被挡住、脚步制动、文件袋压低、门缝停住、呼吸断半拍、道具落到谁手里或落幅空间距离变化；不得只写“压力释放、气氛缓和、节奏放松”。
- `action_budget` 使用非负整数并满足 B4 上限。
- `start_state` / `end_state` 写可见状态。
- `dialogue_refs` 与锁定 shot plan 完全一致。
- `dialogue_events` 与 `dialogue_refs` 按相同顺序一一对应；无台词/OS/OV/系统音时输出空数组。每项结构固定：

```json
{
  "ref": "D1",
  "kind": "台词 | OS | OV | 系统音",
  "speaker": "原文人物或声音归属者",
  "text": "逐字逐标点原文",
  "time_range": "0.8-2.6秒",
  "speaker_visibility": "visible | offscreen | nonphysical",
  "facial_state": "发声时间窗内、当前景别可见的具体神态",
  "body_state": "发声时间窗内的肩颈、手、重心、站姿或道具接触",
  "delivery": "语速、音量/气息、停顿/咬字/尾音控制",
  "breath_pause_plan": "句前0.2秒吸气；必要时在原文分句/转折后停0.2秒；句末0.3秒收气。短句可写无中段气口，但起句与句末不可省略",
  "line_function": "probe | pressure | deny | verify | interrupt | farewell | conceal | reveal | plead | deflect | reconcile | narrate | warn | challenge | answer | confess",
  "subtext": "本句未明说的具体意图、防御或关系动作，不得复述原台词",
  "stress_words": ["逐字来自原台词的1-3个词组"],
  "subtext_visible_evidence": "潜台词转译出的手眼、呼吸、道具、距离或听者反应",
  "turn_relation": "initiate | respond | deflect | interrupt | withdraw | bridge | continue",
  "lip_sync": true
}
```

- `ref/kind/speaker/text` 是确定性锁定字段；Master 不得改变顺序、人物、类型、文字或标点。
- `time_range` 必须位于本镜时长内。`facial_state/body_state/delivery` 必须非空；可见人物的神态与身体状态必须落实到子镜头组。
- `dialogue_timing.py` 是对白自然时长与口型窗计算的机器唯一来源；Orchestrator、Composer validator、全集导演审计和 Export 检查必须消费同一计算，不得各自维护语速常量。
- `speaker_visibility=visible` 时人物必须在本镜可见；`offscreen/nonphysical` 时 `facial_state/body_state` 明确写 `N/A` 及不可见原因，不伪造表演。
- 可见台词人物 `lip_sync=true`；OS、OV、画外人物和非实体声音一律 `lip_sync=false`。
- `delivery` 至少覆盖语速、音量/气息、停顿/咬字/尾音中的两项；只写“紧张地、悲伤地、愤怒地、自然地”不合格。`breath_pause_plan` 必须有带秒数的句前气口和句末收气；含多个分句、转折或情绪折点的原文还必须写中段气口，短句可明确无中段气口。气口为自然呼吸与情绪节奏服务，不能机械地逐标点等长停顿。
- 每句先用 `line_function/subtext/turn_relation` 判断它在对话轮次中的作用，再从原文选 1–3 个 `stress_words`；每个重音词必须逐字来自原台词，`delivery` 必须说明其音量、气息、咬字、停顿或尾音说法。`subtext` 不得复述原文，`subtext_visible_evidence` 必须把潜台词转译为说话者/听者的手眼、呼吸、道具、距离或延迟反应并落实到子镜头组；有可见承接人物时不得写 N/A。
- `line_function/subtext/turn_relation` 是内部导演元数据，不得直接拼入 `full_prompt` 或 `画面描述｜直接复制`。正文只接收原文台词、重音说法、可见潜台词证据、口型边界和听者承接，防止提示词字段堆积。
- 有可见物理角色时必须增加 `performance_causality`；无可见物理角色的环境镜可省略：

```json
{
  "tension_intent": "neutral | latent | rising | peak | release",
  "trigger": "本镜可感知的事件、台词、动作、物件变化，或由可见起势承载的自主意图",
  "response_order": ["感知或起势", "身体反应", "必要的对手反应", "回稳或落幅"],
  "physical_logic": "接触点、支撑、受力、重心与结果的关系；无物理阻断时明确为自主改变动作",
  "motion_boundary": "被取消或完成的主运动，以及后续仍允许的残余运动",
  "hold_strategy": "长停顿采用的少量生命迹象或有意静止理由；无长停顿时明确写无",
  "end_residue": "上一事件在落幅仍可见的持续状态"
}
```

- `tension_intent` 只能五选一，描述本镜功能而非统一追求高强度。
- `response_order` 必须是非空有序数组；只记录景别可见、对戏剧目标必要的阶段，不为凑数增加微动作。
- 其余字段必须是非空可执行说明，不得只写“紧张、震惊、停住、自然反应、保持状态”等抽象结果。
- `performance_causality` 是 QA/导演元数据，不得拼入 `full_prompt`；Master 根据它把必要的可见结果落实到子镜头组，Editor Pass 2 复核语义真实性。
- 有可见物理角色时必须增加 `performance_contract`，它是“人物表情 + 身体动作 + 运镜压力 + 场景压力”的统一张力骨架，必须先于 `full_prompt` 生成：

```json
{
  "tension_intent": "neutral | latent | rising | peak | release",
  "trigger_event": "本镜触发张力的台词、动作、物件变化或自主起势",
  "trigger_time": "1.2秒；无明确时点时写无明确时点/N/A",
  "inner_emotion": "角色没有说出的具体需要、恐惧或矛盾；仅作推导",
  "display_intent": "角色主动展示给对手看的态度或控制策略；仅作推导",
  "mask_leak": "内在情绪突破外在展示时，从手、眼、下颌、呼吸、道具或重心泄露的一个可见证据",
  "start_intensity": 1,
  "end_intensity": 3,
  "emotion_delta": 2,
  "primary_expression": "当前景别可见的面部控制，不写抽象情绪词",
  "primary_body_action": "肩颈、手、重心、步伐、接触点或呼吸的第一身体反应",
  "eye_focus": "视线方向、停留对象、闪避/锁定/回收",
  "reaction_delay": "反应延迟、停顿或无延迟理由",
  "voice_or_breath_control": "无对白时写呼吸/吞咽/停顿；有对白时写句前停顿、音量、语速、气息、咬字或尾音控制",
  "viewer_empathy_anchor": "观众能立刻读懂的角色处境、软肋、顾虑、保护对象或被刺中的原因，不写效果词",
  "readable_image_moment": "承载共情锚点的单一可见画面证据，必须能在子镜头组中找到",
  "suppression_or_release": "压住、泄露、爆开或回收的可见方式",
  "camera_pressure": "运镜、焦点、构图权重如何服务张力",
  "scene_pressure": "光源、遮挡、空间距离、环境声或道具如何加压",
  "end_residue": "落幅仍可见的姿态、呼吸、视线、距离、接触或道具残留"
}
```

- `performance_contract` 先用 `inner_emotion` 与 `display_intent` 建立内外差，再由 `mask_leak` 指定一个可见泄露点；`start_intensity/end_intensity` 只能是 0–5 整数，`emotion_delta=end_intensity-start_intensity`。这些心理分析词与数字只用于导演推导和全集曲线审计，不得进入模型正文。`mask_leak`、表情、身体、视线、呼吸/语气、观众共情锚点、画面可读瞬间、`visual_progression`、压制/释放、运镜压力、场景压力和落幅残留必须落实进 `full_prompt` 对应段落；只写“紧张、震惊、自然反应、有张力、表情细腻、感染力强、观众共情”等抽象词不合格。`visual_progression` 写起幅→可见变化→落幅，或在有意静止时写静止理由→低幅生命迹象→落幅；它不要求每镜切换景别或移动摄影机，但禁止用“固定机位/稳定”代替人物与画面的真实推进。
- 当对手戏使用心理距离景别反差时，`camera_pressure` 必须写明谁被画面收窄、谁保留空间呼吸，以及触发依据；`scene_pressure` 必须写明桌面、门框、屏风、光线、道具或人物距离如何加压。若使用道具/环境插入镜，`visual_progression` 必须说明它带来的新信息或状态变化，`continuity_contract.prop_state/next_carryover` 必须继承该状态；不得把装饰性空镜当作张力证据。
- `expectation_anchor` 是按需字段：仅当期待/等待会改变本镜焦点、切镜或下一镜连续性时增加。先写 `semantic_mode` 与 `source_interpretation`，以说明它是字面人物行为、借物拟人、需求/缺失还是象征意象；不得让登记类型替代语义判断。锚点可以是实体对象、人物动作、事件、空间位置或其他可见状态；无候选时省略该字段，不用填 `N/A`。有期待锚点时，必须在子镜头组落地锚点、进展事件、期待主体回反应和终态：

```json
{
  "applicable": true,
  "semantic_mode": "literal_agent",
  "anchor_type": "object",
  "anchor": "信纸",
  "expecting_subject": "角色A",
  "source_interpretation": "角色A正在看着角色B书写的信纸，属于字面人物的可见等待",
  "start_state": "角色A的视线停在角色B笔下的信纸上，信纸仍在书桌中央",
  "progress_event": "2.8秒笔尖停住后继续落下，信纸新增一行可见笔迹",
  "detail_cut_rule": "仅由笔尖停顿触发一次信纸特写；对象静止时不切镜",
  "return_reaction": "细节镜后切回角色A，角色A手指收紧且视线仍挂在信纸方向",
  "end_state": "信纸仍未递出，角色A保持前倾等待姿态"
}
```

- 锚点细节镜或关系重构只能由 `progress_event` 触发，不得因锚点静止或为了增加景别变化而切镜。若 `detail_cut_rule` 使用特写，后续时间窗必须回到 `expecting_character` 的可见反应；锚点未兑现时，`end_state`、`continuity_contract.prop_state` 与 `next_carryover` 必须共同保留未完成状态。当前构图已能读清锚点进展与反应时，`detail_cut_rule` 可明确写“不切景别，保持同镜头”。
- 有可见物理角色时必须增加 `continuity_contract`：

```json
{
  "start_anchor": "本镜起始位置、姿态、视线、道具和光源状态",
  "end_anchor": "本镜终止位置、姿态、视线、道具和光源状态",
  "position_continuity": "人物和摄影机相对位置如何承接上一镜/进入下一镜",
  "eyeline_continuity": "视线对象和屏幕方向如何连续",
  "prop_state": "关键道具、伤势、破坏、接触状态",
  "lighting_continuity": "光源方向、色温、阴影关系",
  "next_carryover": "下一镜必须继承的画面残留"
}
```

- `end_anchor` 与 `next_carryover` 必须能在模型提示词中找到可见落幅，不得只存在于 QA 字段。
- 若人物位置、身体朝向、视线、重心或可移动道具发生变化，必须设置 `state_change=true`，并在 `state_transitions[]` 为每项变化写 `subject/from_state/intermediate_state/to_state/cause/time_range`。`intermediate_state` 必须是本镜可见动作承接：道具写手靠近、接触、拿起、递出、接住或放下；人物转向写视线先变、头部半转、肩线/重心跟随、身体朝向完成。`cause` 必须是本镜可见动作、接触、人物走位或明确转场；否则阻断，禁止无解释换位、道具闪现、转身跳变或道具复位。
- 外套、手机、武器、门、领口、伤势等道具/状态发生转移时，必须在 `prop_state` 写清“从谁/哪里 → 到谁/哪里 → 结束状态”，并在 `next_carryover` 写下一镜继承状态；禁止外套、遮挡、伤势或道具复位。
- 人物正在看、读、玩、点击或操作手机/平板/电脑屏幕、书页/文件/照片、表盘、镜面或仪表盘时，必须增加 `prop_functional_surface_contract`：`applicable/prop/functional_surface/user/user_view_relation/camera_half_space/camera_visible_surface/grip_contact/interaction_evidence/content_visibility/orientation_lock/fallback_shot`。`content_visibility` 只允许 `hidden/partial/readable/post_overlay/not_applicable`。正文必须落实功能面朝使用者、摄影机可见面、握持/接触、操作证据和方向稳定终态；`hidden/post_overlay` 时以背壳/背面/侧边/边框朝摄影机等正向事实锁定，不得写成屏幕朝观众且内容清晰可读。`partial/readable` 必须使用肩后、过肩、俯拍、斜上方或摄影机与使用者同侧机位；需要人物正面表演和屏幕内容同时清楚时优先拆镜。普通静置和递交不触发。
- 清晰人物表演镜必须增加 `skin_tone_protection_contract`：`applicable/subjects/protection_mode/source_allowed_skin_marks/skin_tone_baseline/face_light_and_exposure/face_fill_shadow_policy/environment_color_boundary/texture_atmosphere_boundary/continuity_lock/fallback`。`protection_mode` 只允许 `natural_protected/motivated_color_cast/source_authorized_marks/silhouette`。正文必须落实自然肤色基准、独立脸部主光与曝光、中性补光托住眼窝鼻翼下颌、环境色作用边界、纹理/空气介质深度边界；冷青、冷绿和霓虹默认只在背景、衣物边缘或轮廓反光，墙痕、水渍、灰尘、雾粒与体积光束默认只在环境或中后景。源文明示的伤痕、妆容、泪痕和污迹必须写入 `source_allowed_skin_marks`；有动机偏色仍需中性肤色参照区，剪影必须有源文或镜头功能依据。该合同只保留在 QA，直投正文只写可见光色、曝光和空间边界，不泄漏字段名。
- 有可见人物时必须增加 `reroll_control`：

```json
{
  "risk_level": "low | medium | high",
  "identity_anchor": "角色身份、脸部气质、站姿或关系锚点；不得新增服装设计",
  "motion_anchor": "动作路径、接触点、幅度、速度或停顿锚点",
  "scene_anchor": "固定空间、光源、道具、遮挡或接触阴影锚点",
  "camera_anchor": "景别、焦距、机位、轴线、落幅和唯一运镜锚点",
  "risk_reason": "抽卡风险来自身份、动作、多人关系、口型、参考缺失还是复杂空间",
  "mitigation_steps": ["至少两条具体缓解策略"],
  "manual_first_pass_check": true
}
```

- T2V 人物镜不得把风险标为 `low`。T2V 的 `rising/peak` 人物镜必须标记 `manual_first_pass_check=true`，并用身份、服装、屏幕左右、场景、动作或镜头降负载等策略降低抽卡；不得要求或伪造外部素材。
- 使用心理距离景别反差、人物脸部特写、shot_group 插入镜或道具/环境细节切镜时，`reroll_control.risk_reason` 必须包含对应风险来源，`mitigation_steps` 至少写明两项稳定措施：复用身份/服装锚点、固定屏幕左右、继承同一光源与轴线、优先手部/道具而非脸部大特写、限制为一次动机切换、或把第二个反应节拍拆到下一主镜。
- 使用插入镜时，`reroll_control.mitigation_steps` 还必须覆盖插入前后承接：锁定插入前落幅、插入主体、插入后回到的主线人物/道具状态和声音桥。若插入镜为回忆/幻想/时空意象而未启用 `temporal_transition_contract` 或独立主镜，应标为 blocking。
- 连续互动发生注意力交接时增加 `attention_handoff`；无交接时可省略：

```json
{
  "mode": "causal_handoff",
  "count": 1,
  "strategy": "rack_focus | single_reframe | actor_blocking",
  "from": "甲",
  "to": "乙",
  "trigger": "乙开始回答",
  "end_composition": "双人关系构图，乙保持主要视觉权重"
}
```

- `count` 只能为 1；`strategy` 三选一。`rack_focus` 要求物理机位固定，`single_reframe` 禁止再叠加拉焦/变焦，`actor_blocking` 要求摄影机固定或仅同向轻微收束。
- 当可见台词人物与可见 supporting 人物同框时，必须增加 `listener_reaction_plan`。它只指定一名倾听者、一条由说话/动作触发的低幅反应和闭口落幅：`speaker/listener/trigger/time_range/visual_evidence/motion_limit/lip_sync/end_residue` 均必填。`lip_sync=false`；`visual_evidence`、`motion_limit`、`end_residue` 必须逐字落在子镜头组，且子镜头组明确倾听者口型闭合。听者最多一次眼神、呼吸、手指、肩背、重心或已确认道具反应；不得新增台词、大幅走位、同步口型或第二条情绪爆发。剧情要求僵住时，`motion_limit` 说明原因并保留 1–2 个生命迹象。打斗、追逐、推搡、控制与救援镜不填本字段，改由 `fight_continuity` 写双方“动作→受力/判断→结果”的连续反应链；非主攻方必须格挡、闪避、回稳、主动收住或准备反制，不能作为静止倾听者。
- 打斗上下文必须增加 `fight_continuity`：

```json
{
  "mode": "continuous_take",
  "sequence_id": "FIGHT-01",
  "clip_id": "FIGHT-01-C01",
  "participants": ["甲", "乙"],
  "contact_beats": [
    {
      "time_range": "2.0-5.0秒",
      "attacker": "甲",
      "defender": "乙",
      "attack_path": "甲由画左横挥至画右",
      "contact_point": "乙左前臂格挡点",
      "force_direction": "乙受力向画面右后方",
      "result": "刀停在乙左肩外侧，乙重心落到右后脚"
    }
  ],
  "start_lock": {
    "positions": "甲画左、乙画右，相距1.2米",
    "stance_weight": "甲右脚前；乙重心居中",
    "weapon_prop_state": "甲右手持刀；乙空手",
    "injury_damage_state": "双方无新增伤势，场景未破坏",
    "screen_direction": "甲由画左攻向画右",
    "axis_side": "摄影机位于人物连线南侧"
  },
  "end_lock": {
    "positions": "甲画中左、乙画右后，相距0.8米",
    "stance_weight": "甲重心前压；乙重心落到右后脚",
    "weapon_prop_state": "刀停在乙左肩外侧；乙左臂格挡",
    "injury_damage_state": "双方无新增伤势，场景未破坏",
    "screen_direction": "动作惯性继续指向画右",
    "axis_side": "摄影机仍位于人物连线南侧"
  }
}
```

- 同一 `sequence_id` 的下一生成片段，其 `start_lock` 必须与上一片段 `end_lock` 完全相同。

## §C — Merged Prompt Package

```json
{
  "contract_version": "<PROMPT_CONTRACT_VERSION>",
  "shots": []
}
```

- `shots` 是提示词包唯一权威数组。禁止在同一包中复制为 `items` 或派生 `merged_full_prompts`。
- `contract_version` 的当前精确值只从 `scripts/contract_registry.py` 读取；本示例不复制版本字面量。
- 主镜头聚合只允许在导出时临时计算，不得持久化第二份提示词事实。
- `normalize_prompt_package.py` 只规范当前契约，不负责旧版迁移。

## §D — Export Separation

Markdown 只导出可直接投喂和人工操作所需内容：

1. 模型提示词 `full_prompt`；
2. 独立负面提示词 `negative_prompt`；
3. 台词/OS/OV/系统音制作信息：引用、类型、人物或非实体声源、逐字原文、时间窗、发声时神态、身体状态、语气与口型边界。

XLSX/缓存保留 QA/导演元数据、`generation_control`、表演合同、连续性合同和抽卡风险控制，供制作复核与二次生成使用。

不得把负面词、QA/导演元数据、生成控制或工程字段拼回 `full_prompt` 冒充一条“更完整”的模型提示词。

## §E — Encoding And File Rules

- JSON 使用 UTF-8 无 BOM；读取时用 `utf-8-sig` 防御 BOM。
- 禁止尾随逗号、单引号 JSON、中文结构键。
- batch 文件必须带批次后缀。
- 公共输出只由主 Agent 的合并/归一化脚本写入。
