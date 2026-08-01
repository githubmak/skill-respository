"""Shared current prompt-contract helpers.

The model-facing prompt is intentionally small. Production metadata, negative
prompts, and validation traces live in sibling JSON fields and are never mixed
into ``full_prompt``.
"""

from __future__ import annotations

import re

from dialogue_timing import analyze_dialogue_timing


# 即梦正文只使用可见、可执行的描述。子镜头置于同一个生成任务内，
# 用明确的时间窗、左右关系和前景肩膀描述正反打，绝不泄漏内部轴线术语。
PROMPT_LABELS = ["生成规格", "主体与空间锁定", "主镜头连续规则", "子镜头组", "光照、声音与稳定约束"]
LEGACY_LABELS = [
    "全局声明",
    "人物站位与服装连续",
    "时长运镜场景目的",
    "时间分段叙事",
    "光照方案",
    "环境音设计",
    "负面提示词",
    "自包含验证",
]

FORBIDDEN_MODEL_TERMS = [
    "project_config",
    "costume_map",
    "dialogue_map",
    "dispatch packet",
    "packet",
    "source_path",
    "run_dir",
    "_batch_output_path",
    "output_path",
    "subshot_id",
    "auto补全",
    "自包含验证",
    "提示词自动注入",
    "管线级",
    "QA通过",
    "校验通过",
    "轴线",
    "同侧轴线",
    "180度轴线",
    "越轴",
    "正轴机位",
    "OTS",
    "反打",
]

DIRECT_FEED_META_TERMS = (
    "延续上一镜", "上一镜", "尾帧", "位置不变", "剪辑", "切到", "反打到",
    "后期插入", "脑海浮现", "当前主角", "当前对话者", "继承",
    "line_function", "subtext", "turn_relation", "inner_emotion", "display_intent",
    "mask_leak", "start_intensity", "end_intensity", "emotion_delta",
    "composition_priority", "camera_motivation",
    "scene_objective", "active_tactic", "knowledge_gap", "power_state_change",
    "relationship_emotion_arc", "sequence_directing_plan", "cut_decision_contract",
    "prompt_information_budget", "environment_story_arc", "breathing_policy",
    "sound_directing_plan", "sound_perspective", "lead_lag_strategy",
    "conversation_mode", "response_latency", "overlap_or_interrupt_window",
    "conversation_source_basis",
    "prop_functional_surface_contract", "functional_surface", "user_view_relation",
    "camera_half_space", "camera_visible_surface", "grip_contact", "interaction_evidence",
    "content_visibility", "orientation_lock", "fallback_shot",
    "skin_tone_protection_contract", "protection_mode", "source_allowed_skin_marks",
    "skin_tone_baseline", "face_light_and_exposure", "face_fill_shadow_policy",
    "environment_color_boundary", "texture_atmosphere_boundary", "continuity_lock",
    "face_key_light", "face_fill_light", "skin_color_cast_boundary", "skin_texture_boundary",
    "prop_lifecycle_contract", "perspective_scale_contract", "lighting_topology_contract",
    "projection_scale_rule", "body_ratio_lock", "motion_scaling", "prop_scale_lock",
    "motivated_source", "face_light_layer", "environment_light_layer", "volume_light_boundary",
    "台词功能：", "潜台词：", "轮次关系：", "内在情绪：", "对外展示：",
    "面具泄露：", "情绪变化量：", "构图优先级：", "运镜动机：",
    "场景目标：", "行动策略：", "信息差：", "权力变化：", "镜头段落意图：",
    "会话模式：", "响应延迟：", "抢话窗口：", "打断窗口：", "会话源文依据：",
)

TIME_RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)秒")
JIMENG_CHILD_SHOT_RE = re.compile(
    r"【镜头\d+｜(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)秒(?:｜[^】]+)?】([^【]+)"
)

WIDE_INVISIBLE_CUES = [
    "瞳孔", "虹膜", "眼睑", "鼻翼", "唇线", "眼神光", "眼轮匝肌", "咬肌",
]
MEDIUM_INVISIBLE_CUES = ["瞳孔", "虹膜", "鼻翼", "眼神光", "眼轮匝肌"]
FIGHT_LOCK_FIELDS = [
    "positions",
    "stance_weight",
    "weapon_prop_state",
    "injury_damage_state",
    "screen_direction",
    "axis_side",
]
ATTENTION_HANDOFF_STRATEGIES = {"rack_focus", "single_reframe", "actor_blocking"}
TENSION_INTENTS = {"neutral", "latent", "rising", "peak", "release"}
TENSION_CURVE_ROLES = {
    "setup", "rise", "rising", "peak", "release", "buffer",
    "铺垫", "升压", "峰值", "释放", "缓冲",
}
TENSION_CURVE_ROLE_ALIASES = {
    "setup": "setup",
    "铺垫": "setup",
    "rise": "rise",
    "rising": "rise",
    "升压": "rise",
    "peak": "peak",
    "峰值": "peak",
    "release": "release",
    "释放": "release",
    "buffer": "buffer",
    "缓冲": "buffer",
}
SPEECH_KINDS = {"台词", "OS", "OV"}
SPEAKER_VISIBILITIES = {"visible", "offscreen", "nonphysical"}
REROLL_RISK_LEVELS = {"low", "medium", "high"}
SCREEN_TEXT_POLICY_MODES = {"none", "post", "ai_overlay", "ai_generated", "ai_ui"}
TEMPORAL_TRANSITION_KINDS = {"none", "memory_flashback", "story_event_transition"}
INSERT_FUNCTIONS = ("信息补充", "情绪放大", "节奏切割", "视线引导", "转场缓冲", "环境残压")
INSERT_TERMS = (
    "插入镜", "插入镜头", "切入", "切到", "局部特写", "细节特写", "道具特写",
    "手部特写", "空镜", "环境残留", "环境残压", "反应镜", "回忆", "幻想", "闪回", "时空意象",
)
FACE_CLOSEUP_RE = re.compile(r"(?:脸部|面部|半脸|眼神|眼睛|眼眶|唇线|下颌).{0,8}(?:大特写|特写)|(?:大特写|特写).{0,8}(?:脸部|面部|半脸|眼神|眼睛|眼眶|唇线|下颌)")
TEMPORAL_INSERT_RE = re.compile(r"(?:插入镜|切入|切到|插入).{0,24}(?:回忆|幻想|闪回|时空意象)|(?:回忆|幻想|闪回|时空意象).{0,24}(?:插入镜|切入|切到|插入)")
DECORATIVE_INSERT_RE = re.compile(r"(?:无意义|装饰性|纯氛围|静态氛围|无关|好看|丰富画面)")
GENERIC_PERFORMANCE_TERMS = {
    "紧张", "震惊", "愤怒", "悲伤", "害怕", "自然", "自然反应", "有张力",
    "情绪复杂", "表情细腻", "保持状态", "微微变化", "很强烈",
    "感染力强", "观众共情", "共情感强", "画面感强", "情绪到位", "内心张力拉满",
}
READINESS_DIMENSIONS = {
    "scene_space": "场景空间",
    "continuity_risk": "穿帮风险",
    "emotion_readability": "情绪可读",
    "tension_pressure": "张力压迫",
    "camera_emotion_fit": "运镜服务情绪",
    "prop_continuity": "道具连续",
    "visual_beauty": "画面美感",
}
READINESS_GENERIC_TERMS = {
    "很好", "优秀", "合格", "稳定", "清晰", "有张力", "很有张力", "画面好看",
    "空间清楚", "道具稳定", "情绪到位", "无明显问题", "整体不错", "执行性强",
}
PRESSURE_RELEASE_MODES = {
    "action_completion",
    "interrupted_release",
    "attention_shift",
    "cost_reveal",
    "delayed_release",
    "split_release",
    "release",
    "none",
}
STORY_PUNCH_FIELDS = (
    "audience_question",
    "character_pressure",
    "visible_pressure_object",
    "dramatic_turn",
    "picture_punctuation",
    "composition_priority",
    "camera_motivation",
    "end_residue",
)
CHARACTER_SCENE_OBJECTIVE_FIELDS = (
    "focus_character", "scene_objective", "stakes", "obstacle", "active_tactic",
    "visible_tactic_evidence", "tactic_shift", "knowledge_gap",
    "power_state_change", "end_action_state",
)
RELATIONSHIP_EMOTION_ARC_FIELDS = (
    "participants", "start_relation_state", "conflicting_wants",
    "emotional_misalignment", "turn_trigger", "power_shift",
    "end_relation_state", "shared_residue",
)
SEQUENCE_DIRECTING_PLAN_FIELDS = (
    "scene_visual_argument", "sequence_position", "distance_lens_stage",
    "composition_motif_state", "rule_break_or_hold",
    "blocking_camera_coordination", "environment_beat", "handoff",
)
SEQUENCE_POSITIONS = {"establish", "hold", "escalate", "break", "release", "resolve"}
CUT_DECISION_FIELDS = (
    "cut_mode", "trigger", "pre_cut_hold", "information_gain",
    "sound_strategy", "economy_reason", "fallback",
)
CUT_MODES = {"hold", "action", "reaction", "dialogue", "sound", "delayed", "match", "scene_transition"}
PROMPT_INFORMATION_BUDGET_FIELDS = (
    "profile", "primary_render_task", "must_render", "supporting_visual",
    "metadata_only", "compression_rule",
)
PROMPT_INFORMATION_PROFILES = {"environment", "object", "action", "dialogue", "dramatic"}
SOUND_DIRECTING_PLAN_FIELDS = (
    "primary_source", "source_direction_distance", "room_environment_response",
    "foreground_background_priority", "silence_or_drop", "lead_lag_strategy",
    "cut_support",
)
DIALOGUE_LINE_FUNCTIONS = {
    "probe", "pressure", "deny", "verify", "interrupt", "farewell",
    "conceal", "reveal", "plead", "deflect", "reconcile", "narrate",
    "warn", "challenge", "answer", "confess",
}
DIALOGUE_TURN_RELATIONS = {
    "initiate", "respond", "deflect", "interrupt", "withdraw", "bridge", "continue",
}
CONVERSATION_MODES = {
    "clean_turn", "overlap", "interrupted", "unfinished",
    "self_correction", "non_answer", "source_supported_other",
}
STORY_PUNCH_GENERIC_RE = re.compile(
    r"气氛|氛围|情绪变化|表情变化|表情复杂|微表情|很紧张|更紧张|有戏|戏剧性|压迫感|张力感|"
    r"保持状态|自然反应|若有所思|意味深长|沉默不语|看着对方|对视|凝视"
)
STORY_PUNCH_SPIKE_RE = re.compile(
    r"停半拍|反应延迟|迟疑|犹豫|卡住|收住|"
    r"未[^，。；;]{0,12}(?:拧开|递出|放下|说完|完成|落下|碰到|交出|拿走)|"
    r"悬停|停在[^，。；;]{0,16}(?:边缘|杯沿|瓶盖|门把|屏幕|封条)|"
    r"封条|瓶盖|杯沿|药瓶|钥匙|门把|亮屏|屏幕[^，。；;]{0,12}消息|"
    r"视线[^，。；;]{0,16}(?:移开|错开|避开|滑到|停在|转向|留在)|"
    r"打断|脚步[^，。；;]{0,16}逼近|门外|来电|铃声|推门|"
    r"仍[^，。；;]{0,16}(?:握|停|看|攥|按|贴|悬)|没有复位|下一镜继承[^，。；;]{0,20}(?:手中|桌面|门口|视线|道具|药瓶|手机|钥匙)"
)

ABSTRACT_VISUAL_TERMS = (
    "电影感", "高级感", "大片感", "质感很好", "细腻质感", "光影高级",
    "视觉冲击", "高级质感", "真实感", "精致感",
)
LIGHT_SOURCE_RE = re.compile(
    r"顶光|侧光|窗光|背光|逆光|补光|自然光|店铺光|灯箱|路灯|顶灯|"
    r"冷白灯|暖灯|面光|灯光|光源|主光|轮廓光|冷白光|暖光|中性光|\d{4}K|受光"
)
VISIBLE_TEXTURE_ANCHOR_RE = re.compile(
    r"脸侧|脸部|手背|手指|指尖|手腕|道具|卡面|屏幕|手机|银行卡|纸面|衣料|"
    r"玻璃|金属|桌面|墙面|地面|门框|柜台|反光|高光|阴影|浅阴影|虚化|背景"
)
CINEMATIC_IMAGE_CONTRACT_FIELDS = (
    "composition_anchor",
    "lens_depth",
    "exposure_contrast",
    "color_separation",
    "atmosphere_layer",
    "material_detail",
    "imperfection_map",
    "realism_risk",
    "signature_frame",
)
VIDEO_TEXTURE_CONTRACT_FIELDS = (
    "look_profile",
    "exposure_policy",
    "material_motion_policy",
    "atmosphere_motion_policy",
    "camera_stability_policy",
    "continuity_carryover",
    "risk_controls",
)
VISUAL_BIBLE_FIELDS = (
    "visual_thesis", "palette_system", "light_motivation", "contrast_exposure",
    "composition_grammar", "material_world", "atmosphere_rule", "imperfection_policy",
    "reference_policy", "continuity_lock",
)
STATIC_AESTHETIC_CONTRACT_FIELDS = (
    "visual_intent", "composition_hierarchy", "light_design", "color_grade",
    "lens_rendering", "depth_atmosphere", "material_anchor", "signature_frame",
    "aesthetic_exclusions",
)
DYNAMIC_AESTHETIC_CONTRACT_FIELDS = (
    "motion_thesis", "start_state", "trigger", "primary_subject_motion",
    "secondary_environment_motion", "camera_path", "focus_behavior", "material_motion",
    "atmosphere_motion", "tempo_easing", "end_state", "stability_fallback",
)
AESTHETIC_PRIORITY_FIELDS = (
    "visual_thesis", "primary_eye_target", "secondary_visual_layer",
    "must_preserve", "degrade_first",
)
CINEMATIC_COMPOSITION_RE = re.compile(r"前景|遮挡|门框|窗框|框景|引导线|留白|低机位|高机位|俯拍|仰拍|非对称|纵深")
CINEMATIC_DEPTH_RE = re.compile(r"焦平面|景深|焦外|虚化|远端|背景压缩|空气透视|雾化|前景虚|后景虚|浅景深")
CINEMATIC_EXPOSURE_RE = re.compile(r"暗部|黑位|不过曝|高光|低照度|曝光|主光|辅光|阴影|受光面|反差")
CINEMATIC_COLOR_RE = re.compile(r"冷暖|冷白|暖黄|红光|蓝黑|青灰|低饱和|局部强调色|色彩分离|主体.*背景.*分离")
CINEMATIC_ATMOSPHERE_RE = re.compile(r"雨|雾|尘|水汽|烟|颗粒|空气|逆光|飘浮|湿气|霾")
CINEMATIC_MATERIAL_RE = re.compile(r"墙皮|墙面|地面|瓷砖|水泥|玻璃|金属|纸面|衣料|木纹|水渍|污渍|划痕|裂纹|起皮|磨损|灰尘|粗糙")
CINEMATIC_IMPERFECTION_RE = re.compile(r"不均匀|不规则|断续|细碎|污渍|划痕|磨损|起皮|裂纹|水渍|灰尘|颗粒|粗糙|残缺|暗斑|旧痕")
LIGHT_DIRECTION_RE = re.compile(r"左|右|前|后|上|下|侧|顶部|窗外|门外|逆向|斜向")
LIGHT_RECEIVER_RE = re.compile(r"脸|面部|眼窝|手|衣|发|墙|地|桌|门|道具|纸|木|玻璃|金属|水面")
SHADOW_RESULT_RE = re.compile(r"阴影|暗部|黑位|明暗|高光|轮廓|反差|衰减")
MATERIAL_RESPONSE_RE = re.compile(r"反光|高光|吸光|透光|漫反射|粗糙|纹理|磨损|褶皱|划痕|起皮|水渍|颗粒|湿润|干涩")
MOTION_PHASE_RE = re.compile(r"先(?:发生|触发|移动|抬|转|落)|随后|稍后|稍晚|之后|延迟|余波|回收|减速|停稳|最终|落幅|起幅")
MOTION_ACTION_RE = re.compile(r"抬|转|移|走|跑|靠近|退|伸|握|抓|放|接|压|起身|坐|躺|呼吸|视线|目光|重心|肩|下颌|停住|站稳|摆动|流动")
MATERIAL_FAMILY_PATTERNS = (
    re.compile(r"皮肤|肤质|脸颊|手背"),
    re.compile(r"衣料|布料|衣袖|衣摆|丝绸|棉麻|皮革"),
    re.compile(r"木纹|木门|木桌|纸面|书页|信封"),
    re.compile(r"玻璃|镜面|水面|积水"),
    re.compile(r"金属|刀剑|杯沿|门把|栏杆"),
    re.compile(r"墙面|墙皮|石板|水泥|瓷砖|地面"),
)
AI_REALISM_RISK_RE = re.compile(
    r"镜面水面|水面像镜子|镜子般反射|塑料质感|塑料墙|过度干净|过于干净|无瑕|"
    r"过度霓虹|霓虹堆叠|赛博炫光|CG感|渲染感|3D渲染|游戏场景|虚拟摄影棚|"
    r"雨线均匀|均匀雨线|灯光过曝|过曝灯管"
)
REALISM_POSITIVE_STYLE_RE = re.compile(r"写实|实拍|电影剧照|实拍短片|纪实|胶片|摄影机|镜头")
CG_STYLE_DRIFT_RE = re.compile(r"动态漫|漫画|二次元|赛博|超现实|概念图")
VIDEO_TEXTURE_LOOK_RE = re.compile(r"写实|实拍|电影剧照|影视级|高端3D|PBR|物理|低饱和|胶片|摄影机|统一")
VIDEO_TEXTURE_EXPOSURE_RE = re.compile(r"不过曝|黑位|暗部|高光|曝光|反差|受光|灯罩|轮廓光|低照度")
VIDEO_TEXTURE_MATERIAL_MOTION_RE = re.compile(r"材质|墙皮|墙面|地面|水面|积水|玻璃|金属|衣料|皮肤|反光|高光|涟漪|划痕|磨损|粗糙|断续|不均匀")
VIDEO_TEXTURE_ATMOSPHERE_MOTION_RE = re.compile(r"雨|雾|尘|水汽|烟|空气|颗粒|飘|扩散|流动|贴地|断续|不均匀")
VIDEO_TEXTURE_CAMERA_STABILITY_RE = re.compile(r"固定|低幅|缓慢|稳定|不摇晃|不推拉|不变焦|单向|运动预算|镜头")
VIDEO_TEXTURE_CONTINUITY_RE = re.compile(r"跨镜|同一|统一|保持|继承|连续|不跳变|不重置|不换光|不换色")
PHYSICAL_CHAIN_GROUPS = (
    re.compile(r"伸向|靠近|接近|抬手|递出|前移|半转|头部轻转|肩线|重心|脚步"),
    re.compile(r"指尖|接触|触碰|握住|抓住|攥住|接住|扶住|支撑|贴住"),
    re.compile(r"松手|放下|收回|落定|稳定|停在|仍在|落幅|继承|保持"),
)
VISIBLE_GATE_RE = re.compile(r"可见人数|画面内可见人数|本镜画面内可见|本镜只出现|不入画|画外")
VISIBLE_LAYER_RE = re.compile(r"清晰|实焦|肩线|背影|倒影|虚化|画外|不入画")
OFFSCREEN_SOURCE_RE = re.compile(r"画外声源|画外.{0,6}声|门口方向|右侧声源|左侧声源|固定锚点|空间锚点")
AI_SCREEN_TEXT_RE = re.compile(r"聊天消息|绿色气泡|通知弹窗|字幕浮层|UI文字|屏幕文字|来电名称")
AI_SCREEN_TEXT_SAFE_RE = re.compile(r"二维浮层|安全区|不属于手机屏幕|不贴手机背面|不跟随手机透视")

CAMERA_MOVE_PATTERNS = {
    "push": r"推镜|推近|摄影机[^。；]{0,12}推进",
    "pull": r"拉镜|后拉|摄影机[^。；]{0,12}退远",
    "pan": r"摇镜|平摇|横摇|甩镜",
    "slide": r"横移|侧移|轨道移|滑轨|弧移",
    "track": r"跟拍|跟随摄影|摄影机跟随",
    "orbit": r"环绕|绕拍|绕行摄影",
    "vertical": r"升镜|降镜|升降镜头|摄影机[^。；]{0,12}(?:上升|下降)",
    "handheld": r"手持",
    "zoom": r"变焦|焦距[^。；]{0,12}(?:变化|拉长|缩短)",
}
FOCUS_TRANSFER_RE = re.compile(r"拉焦|焦点(?:从|由).{0,24}(?:转|移|交接|落到)|焦点转移|景深(?:从|由).{0,24}(?:转|移)")


def split_sections(text, labels=None):
    """Return exact top-level sections keyed by their Chinese labels."""
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    labels = labels or PROMPT_LABELS
    if not text:
        return {}
    joined = "|".join(re.escape(label) for label in labels)
    matches = list(re.finditer(rf"(?:^|\n\n)({joined})[：:]", text))
    sections = {}
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[start:end].strip()
    return sections


def jimeng_feed_prompt(full_prompt):
    """Return the lean, copy-ready view of a canonical five-section prompt.

    The canonical prompt keeps labels so validators can point to evidence.  The
    platform-facing view removes that editorial scaffolding while preserving the
    execution order, time windows, and every model-facing instruction.
    """
    sections = split_sections(full_prompt, PROMPT_LABELS)
    if list(sections) != PROMPT_LABELS:
        return _clean_direct_feed_prompt(str(full_prompt or "").strip())
    ordered = [sections[label].strip() for label in PROMPT_LABELS]
    return _clean_direct_feed_prompt("\n\n".join(part for part in ordered if part))


def direct_feed_prompt_issues(full_prompt, max_chars=None):
    """Validate the user-copyable Jimeng feed view, not the canonical contract text."""
    feed = jimeng_feed_prompt(full_prompt)
    return direct_copy_prompt_issues(feed, max_chars=max_chars, require_visual_texture=False)


def direct_copy_prompt_issues(feed_prompt, max_chars=700, require_visual_texture=True):
    """Validate the final Markdown block users copy directly into Jimeng.

    This check is intentionally stricter than ``direct_feed_prompt_issues``:
    the canonical five-section prompt may be long and verification-friendly,
    while the exported direct-copy block should be compact, current-visible,
    and grounded in concrete light/material anchors.
    """
    feed = str(feed_prompt or "").strip()
    issues = []
    if not feed:
        return ["画面描述｜直接复制不能为空"]
    if any(label + "：" in feed or label + ":" in feed for label in PROMPT_LABELS):
        issues.append("即梦直接投喂提示词不得保留五段栏目名")
    leaked = [term for term in DIRECT_FEED_META_TERMS if term in feed]
    if leaked:
        issues.append("即梦直接投喂提示词含元叙述/内部分析/剪辑占位词：" + "、".join(leaked[:6]))
    if isinstance(max_chars, (int, float)) and not isinstance(max_chars, bool) and max_chars > 0:
        if len(feed) > int(max_chars):
            issues.append(f"即梦直接投喂提示词{len(feed)}字，超过导出硬上限{int(max_chars)}字")
    if require_visual_texture:
        if not LIGHT_SOURCE_RE.search(feed):
            issues.append("画面描述｜直接复制缺少光源方向/色温/受光关系")
        if not VISIBLE_TEXTURE_ANCHOR_RE.search(feed):
            issues.append("画面描述｜直接复制缺少脸/手/道具受光、阴影/反光、背景虚化或剧情相关材质")
    issues.extend(prompt_redundancy_issues(feed))
    issues.extend(screen_text_policy_issues(feed))
    return issues


def prompt_redundancy_issues(text):
    """Reject repeated executable sentences that spend prompt budget without adding facts."""
    clauses = [
        clause.strip()
        for clause in re.split(r"[。！？；;\n]+", str(text or ""))
        if len(clause.strip()) >= 6
    ]
    seen, repeated = set(), []
    for clause in clauses:
        signature = re.sub(r"[\s，,：:]", "", clause).lower()
        if signature in seen and clause not in repeated:
            repeated.append(clause)
        seen.add(signature)
    return ["直投正文存在重复执行句，浪费提示词预算：" + "、".join(repeated[:3])] if repeated else []


def _clean_direct_feed_prompt(text):
    """Convert verification-friendly carryover language into current visible facts for copy-ready prompts."""
    text = str(text or "").strip()
    replacements = (
        (r"延续上一镜", "当前起幅保持"),
        (r"承接上一镜", "当前起幅保持"),
        (r"上一镜", "当前起幅"),
        (r"尾帧", "落幅"),
        (r"下一镜继承", "落幅保持"),
        (r"由下一镜继承", "落幅保持"),
        (r"并由下一镜继承", "并在落幅保持"),
        (r"位置不变", "位置保持"),
        (r"剪辑", "画面转换"),
        (r"反打到", "转为"),
        (r"切到", "转为"),
        (r"后期插入", "画面内呈现"),
        (r"脑海浮现", "画面呈现主观记忆感"),
        (r"当前主角", "画面主体"),
        (r"当前对话者", "说话人物"),
        (r"继承", "保持"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)
    return text


def timeline_ranges(full_prompt):
    sections = split_sections(full_prompt, PROMPT_LABELS)
    return [(float(a), float(b)) for a, b in TIME_RANGE_RE.findall(sections.get("子镜头组", ""))]


def timeline_issues(full_prompt, duration, tolerance=0.08):
    ranges = timeline_ranges(full_prompt)
    issues = []
    if not ranges:
        return ["子镜头组缺少小数秒时间段"]
    if abs(ranges[0][0]) > tolerance:
        issues.append("时间轴必须从0.0秒开始")
    for idx, (start, end) in enumerate(ranges):
        if start >= end:
            issues.append(f"时间段{idx + 1}起止倒置")
        if idx:
            previous_end = ranges[idx - 1][1]
            if abs(start - previous_end) > tolerance:
                kind = "重叠" if start < previous_end else "断档"
                issues.append(f"时间段{idx}与{idx + 1}{kind}")
    try:
        target = float(duration or 0)
    except (TypeError, ValueError):
        target = 0
    if target <= 0:
        issues.append("镜头时长必须大于0")
    elif abs(ranges[-1][1] - target) > tolerance:
        issues.append(f"时间轴终点{ranges[-1][1]:g}秒与镜头时长{target:g}秒不一致")
    if len(ranges) > 3:
        issues.append("主镜头内子镜头超过3个；应拆成新的主镜头")
    return issues


def jimeng_shot_group_issues(full_prompt, editorial_mode="continuous_take"):
    """Enforce visible, platform-readable child-shot anchors.

    Internal camera/axis data may exist in metadata, but Jimeng sees only
    screen-side, body-facing, foreground/scene anchors, and carryover.
    """
    sections = split_sections(full_prompt, PROMPT_LABELS)
    group = sections.get("子镜头组", "")
    children = list(JIMENG_CHILD_SHOT_RE.finditer(group))
    issues = []
    if editorial_mode == "shot_group":
        if not 2 <= len(children) <= 3:
            issues.append("shot_group必须包含2-3个【镜头N｜起止秒】子镜")
    elif len(children) > 1:
        issues.append("continuous_take不得包含多个子镜头")
    for index, child in enumerate(children, 1):
        body = child.group(3)
        missing = []
        if not re.search(r"画面(?:左|右|中)", body):
            missing.append("屏幕左右")
        if not re.search(r"(?:面向|看向|朝向)", body):
            missing.append("人物朝向")
        if not re.search(r"(?:前景.{0,10}肩|肩.{0,10}前景|场景(?:锚点|内)|背景)", body):
            missing.append("前景肩膀或场景锚点")
        if not re.search(r"(?:落幅|保留|继承|停在)", body):
            missing.append("落幅承接")
        if missing:
            issues.append("子镜%d缺少%s" % (index, "、".join(missing)))
    return issues


def action_budget_limits(duration, is_fight=False, editorial_mode="continuous_take"):
    """Return maximum executable events for one generated clip."""
    try:
        seconds = float(duration or 0)
    except (TypeError, ValueError):
        seconds = 0
    if is_fight:
        contact_limit = 1 if seconds <= 6 else 2 if seconds <= 10 else 3
        return {
            "primary_action_count": 1,  # one uninterrupted causal choreography chain
            "emotion_turn_count": 1,
            "supporting_reaction_count": contact_limit,
            "physical_camera_move_count": 1,
            "editorial_response_count": 0,
        }
    return {
        "primary_action_count": 1 if seconds <= 6 else 2,
        "emotion_turn_count": 1,
        "supporting_reaction_count": 1 if seconds <= 6 else 2,
        "physical_camera_move_count": 1,
        "editorial_response_count": 0 if editorial_mode == "continuous_take" else (2 if seconds <= 6 else 3),
    }


def action_budget_issues(metadata, duration, is_fight=False):
    metadata = metadata if isinstance(metadata, dict) else {}
    budget = metadata.get("action_budget", {})
    if not isinstance(budget, dict):
        return ["qa_metadata.action_budget必须是对象"]
    editorial_mode = metadata.get("editorial_mode", "continuous_take")
    limits = action_budget_limits(duration, is_fight, editorial_mode)
    issues = []
    for key, limit in limits.items():
        value = budget.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            issues.append(f"action_budget.{key}必须是非负整数")
        elif value > limit:
            issues.append(f"action_budget.{key}={value}超过上限{limit}")
    beats = metadata.get("camera_beat_map", [])
    if editorial_mode == "shot_group":
        if not isinstance(beats, list) or not 1 <= len(beats) <= 3:
            issues.append("shot_group必须提供1-3项camera_beat_map")
        elif budget.get("editorial_response_count") != len(beats):
            issues.append("action_budget.editorial_response_count必须等于camera_beat_map数量")
    elif isinstance(beats, list) and beats:
        issues.append("continuous_take不得包含camera_beat_map")
    return issues


def emotion_driver_issues(metadata, full_prompt="", visible_characters=None):
    """Require a concrete upstream emotion driver before camera design."""
    metadata = metadata if isinstance(metadata, dict) else {}
    visible = _string_list(visible_characters or [])
    has_visible = bool(visible)
    driver = metadata.get("emotion_driver")
    if not has_visible and driver in (None, {}):
        return []
    if not isinstance(driver, dict):
        return ["有人物镜头必须提供qa_metadata.emotion_driver"] if has_visible else [
            "qa_metadata.emotion_driver必须是对象"
        ]

    issues = []
    required = (
        "trigger",
        "start_state",
        "visible_leak",
        "face_or_eyeline",
        "voice_or_breath",
        "end_residue",
        "tension_intent",
        "empathy_anchor",
    )
    for field in required:
        value = str(driver.get(field, "") or "").strip()
        if len(value) < 2:
            issues.append(f"emotion_driver.{field}不能为空")
        elif value in GENERIC_PERFORMANCE_TERMS:
            issues.append(f"emotion_driver.{field}过于抽象，必须写可见表演重音")
    if driver.get("tension_intent") not in TENSION_INTENTS:
        issues.append("emotion_driver.tension_intent只允许neutral/latent/rising/peak/release")

    contract = metadata.get("performance_contract", {})
    if isinstance(contract, dict):
        contract_intent = contract.get("tension_intent")
        if contract_intent in TENSION_INTENTS and driver.get("tension_intent") in TENSION_INTENTS:
            if contract_intent != driver.get("tension_intent"):
                issues.append("emotion_driver.tension_intent必须与performance_contract.tension_intent一致")

    timeline = split_sections(full_prompt, PROMPT_LABELS).get("子镜头组", "")
    visible_fields = ("visible_leak", "face_or_eyeline", "voice_or_breath", "end_residue")
    grounded = [
        field for field in visible_fields
        if _fragment_grounded(driver.get(field, ""), timeline)
    ]
    if has_visible and timeline and not grounded:
        issues.append("emotion_driver至少一个可见重音必须落实到子镜头组")
    return issues


def camera_beat_map_issues(metadata):
    """Validate emotion-driven camera beat handoff for shot_group."""
    metadata = metadata if isinstance(metadata, dict) else {}
    beats = metadata.get("camera_beat_map", [])
    if metadata.get("editorial_mode", "continuous_take") != "shot_group":
        return []
    if not isinstance(beats, list):
        return ["camera_beat_map必须是数组"]

    issues = []
    driver = metadata.get("emotion_driver", {})
    driver_text = " ".join(
        str(value or "") for value in driver.values()
    ) if isinstance(driver, dict) else ""
    source_trigger_terms = (
        "道具", "台词", "对白", "声音", "视线", "眼神", "手", "呼吸", "重心",
        "身体", "表情", "肩", "步", "落点", "动作", "受力", "格挡", "闪避",
    )
    allowed_responses = {
        "hold", "push_in", "pull_back", "reframe", "rack_focus",
        "hard_cut", "cut_detail", "follow",
    }
    allowed_transitions = {"continuous", "hard_cut", "motivated_insert", "reframe", "hold"}
    required = (
        "time_range",
        "focus_owner",
        "focus_subject",
        "framing",
        "trigger",
        "camera_response",
        "camera_position",
        "camera_movement",
        "transition_type",
        "screen_lock",
        "axis_relation",
        "axis_carryover",
        "carryover",
        "end_frame",
    )
    for index, beat in enumerate(beats):
        if not isinstance(beat, dict):
            issues.append(f"camera_beat_map[{index}]必须是对象")
            continue
        for field in required:
            if len(str(beat.get(field, "") or "").strip()) < 2:
                issues.append(f"camera_beat_map[{index}].{field}不能为空")
        if not re.fullmatch(r"\d+(?:\.\d+)?-\d+(?:\.\d+)?秒", str(beat.get("time_range", "") or "").strip()):
            issues.append(f"camera_beat_map[{index}].time_range必须是连续小数秒范围")
        response = str(beat.get("camera_response", "") or "").strip()
        if response and response not in allowed_responses:
            issues.append(f"camera_beat_map[{index}].camera_response非法")
        transition = str(beat.get("transition_type", "") or "").strip()
        if transition and transition not in allowed_transitions:
            issues.append(f"camera_beat_map[{index}].transition_type非法")

        trigger = str(beat.get("trigger", "") or "").strip()
        if trigger:
            has_driver_fragment = _shares_meaningful_fragment(trigger, driver_text)
            has_allowed_source = any(term in trigger for term in source_trigger_terms)
            if driver_text and not has_driver_fragment and not has_allowed_source:
                issues.append(f"camera_beat_map[{index}].trigger必须来自emotion_driver、道具状态、视线或台词落点")
    return issues


def prompt_state_machine_issues(metadata, full_prompt="", visible_characters=None):
    """Validate the final prompt is assembled as spatial/prop continuity state, not loose prose."""
    metadata = metadata if isinstance(metadata, dict) else {}
    sections = split_sections(full_prompt, PROMPT_LABELS)
    subject = sections.get("主体与空间锁定", "")
    rules = sections.get("主镜头连续规则", "")
    timeline = sections.get("子镜头组", "")
    issues = []

    visible = _string_list(visible_characters or [])
    spatial_text = "\n".join([subject, rules, timeline])
    screen_terms = ("画面左", "画面右", "画面中", "左侧", "右侧", "中间偏", "前景", "中景", "后景")
    orientation_terms = ("身体朝向", "朝向画面", "面向画面", "视线落", "视线看", "视线指向")
    vague_terms = ("旁边", "对面", "身后", "后面", "附近", "远处")
    if len(visible) >= 3:
        if not any(term in spatial_text for term in screen_terms) or not any(term in spatial_text for term in orientation_terms):
            issues.append("三人或多人镜必须使用画面左/中/右、前景/中景/后景、身体朝向和视线落点锁定空间")
        if any(term in spatial_text for term in vague_terms) and sum(1 for term in screen_terms if term in spatial_text) < 2:
            issues.append("多人空间不能只写旁边/对面/身后/附近/远处，必须补屏幕坐标和景深层级")

    contract = metadata.get("continuity_contract", {})
    prop_state = ""
    if isinstance(contract, dict):
        prop_state = str(contract.get("prop_state", "") or "").strip()
    if prop_state and not _is_no_prop_state(prop_state):
        prop_text = "\n".join([subject, rules, timeline])
        location_terms = (
            "画面左", "画面右", "画面中", "左前", "右前", "中后", "前景", "中景", "后景",
            "桌面", "桌角", "桌边", "椅", "门", "地面", "包内", "手中", "身前", "身侧",
        )
        contact_terms = (
            "未被触碰", "未被任何人接触", "未接触", "接触", "归属", "握住", "拿起", "放下",
            "递给", "压在", "仍在", "仍由", "离开", "瓶口", "朝向", "手中",
        )
        carry_terms = ("落幅", "结束", "下一镜", "继承", "保持", "仍在", "不变化", "不离开")
        if not _fragment_grounded(prop_state, prop_text):
            issues.append("continuity_contract.prop_state必须落实到主体与空间锁定、主镜头连续规则或子镜头组")
        if not any(term in prop_text for term in location_terms):
            issues.append("关键道具必须写清屏幕位置或场景位置，避免模型自动换位")
        if not any(term in prop_text for term in contact_terms):
            issues.append("关键道具必须写清归属和接触状态，例如未接触、仍在桌面、握在谁手中或由谁拿起")
        if not any(term in prop_text for term in carry_terms):
            issues.append("关键道具必须写清落幅或下一镜继承状态，避免道具复位或闪现")
        if re.search(r"(?:突然|直接|已经|瞬间).{0,10}(?:到手|在手中|拿到|出现在手|转到|变成)", prop_text):
            issues.append("关键道具变化不能直接跳到终态，必须写手接近、接触、拿起/递出/接住/落定等中间态")

    if re.search(r"(?:突然|直接|已经|瞬间).{0,10}(?:转身|转向|朝向|站到|换到)", spatial_text):
        issues.append("人物转向或站位变化不能直接跳到终态，必须写视线先变、头部半转、肩线/重心跟随和落幅")

    if timeline:
        for index, match in enumerate(JIMENG_CHILD_SHOT_RE.finditer(timeline), start=1):
            body = match.group(3)
            if len(body.strip()) < 10:
                continue
            has_position = any(term in body for term in ("画面左", "画面右", "画面中", "左侧", "右侧", "前景", "中景", "后景"))
            has_end_state = any(term in body for term in ("落幅", "结束", "下一镜", "继承", "仍", "保持", "停在", "留在"))
            if visible and not has_position:
                issues.append(f"镜头{index}必须写当前实焦主体的屏幕位置或景深层级")
            if not has_end_state:
                issues.append(f"镜头{index}必须写结束状态或下一镜继承，不能只写过程动作")
    return issues


def performance_causality_issues(metadata, visible_characters=None):
    """Validate the structured performance-causality audit for character shots."""
    metadata = metadata if isinstance(metadata, dict) else {}
    causality = metadata.get("performance_causality")
    if visible_characters is None:
        roles = metadata.get("performance_priority", {})
        has_visible = bool(
            isinstance(roles, dict)
            and (
                str(roles.get("primary", "") or "").strip()
                or _string_list(roles.get("supporting", []))
                or _string_list(roles.get("background", []))
            )
        )
    else:
        has_visible = bool([char for char in visible_characters if str(char).strip()])

    if not has_visible and (
        causality is None
        or causality == {}
        or (
            isinstance(causality, dict)
            and not any(
                str(value).strip() if not isinstance(value, list) else bool(value)
                for value in causality.values()
            )
        )
    ):
        return []
    if not isinstance(causality, dict):
        return ["有人物镜头必须提供qa_metadata.performance_causality"] if has_visible else [
            "qa_metadata.performance_causality必须是对象"
        ]

    issues = []
    if causality.get("tension_intent") not in TENSION_INTENTS:
        issues.append("performance_causality.tension_intent只允许neutral/latent/rising/peak/release")
    order = causality.get("response_order")
    if not isinstance(order, list) or not order or any(not str(stage).strip() for stage in order):
        issues.append("performance_causality.response_order必须是非空有序文本数组")
    for field in ("trigger", "physical_logic", "motion_boundary", "hold_strategy", "end_residue"):
        if len(str(causality.get(field, "") or "").strip()) < 2:
            issues.append(f"performance_causality.{field}不能为空")
    return issues


def performance_contract_issues(metadata, full_prompt="", visible_characters=None):
    """Validate the integrated expression/body/camera/scene tension contract."""
    metadata = metadata if isinstance(metadata, dict) else {}
    visible = _string_list(visible_characters or [])
    has_visible = bool(visible)
    contract = metadata.get("performance_contract")
    if not has_visible and contract in (None, {}):
        return []
    if not isinstance(contract, dict):
        return ["有人物镜头必须提供qa_metadata.performance_contract"]

    issues = []
    required = (
        "tension_intent",
        "trigger_event",
        "trigger_time",
        "inner_emotion",
        "display_intent",
        "mask_leak",
        "primary_expression",
        "primary_body_action",
        "eye_focus",
        "reaction_delay",
        "voice_or_breath_control",
        "viewer_empathy_anchor",
        "readable_image_moment",
        "visual_progression",
        "suppression_or_release",
        "camera_pressure",
        "scene_pressure",
        "end_residue",
    )
    for field in required:
        if len(str(contract.get(field, "") or "").strip()) < 2:
            issues.append(f"performance_contract.{field}不能为空")
    if contract.get("tension_intent") not in TENSION_INTENTS:
        issues.append("performance_contract.tension_intent只允许neutral/latent/rising/peak/release")
    intensities = {}
    for field in ("start_intensity", "end_intensity"):
        value = contract.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 5:
            issues.append(f"performance_contract.{field}必须是0-5整数")
        else:
            intensities[field] = value
    delta = contract.get("emotion_delta")
    if not isinstance(delta, int) or isinstance(delta, bool) or not -5 <= delta <= 5:
        issues.append("performance_contract.emotion_delta必须是-5到5整数")
    elif len(intensities) == 2 and delta != intensities["end_intensity"] - intensities["start_intensity"]:
        issues.append("performance_contract.emotion_delta必须等于end_intensity-start_intensity")
    trigger_time = str(contract.get("trigger_time", "") or "")
    if trigger_time and not re.search(r"\d+(?:\.\d+)?秒|无明确时点|N/A", trigger_time):
        issues.append("performance_contract.trigger_time必须写秒点，或明确无明确时点/N/A")
    for field in (
        "inner_emotion",
        "display_intent",
        "mask_leak",
        "primary_expression",
        "primary_body_action",
        "eye_focus",
        "reaction_delay",
        "voice_or_breath_control",
        "viewer_empathy_anchor",
        "readable_image_moment",
        "visual_progression",
        "suppression_or_release",
        "camera_pressure",
        "scene_pressure",
        "end_residue",
    ):
        value = str(contract.get(field, "") or "").strip()
        if value in GENERIC_PERFORMANCE_TERMS or len(value) < 4:
            issues.append(f"performance_contract.{field}过于抽象，必须写景别可见的具体控制")

    sections = split_sections(full_prompt, PROMPT_LABELS)
    timeline = sections.get("子镜头组", "")
    camera_text = sections.get("主镜头连续规则", "") + "\n" + timeline
    scene_text = sections.get("主体与空间锁定", "") + "\n" + sections.get("光照、声音与稳定约束", "")
    for field in (
        "mask_leak",
        "primary_expression",
        "primary_body_action",
        "eye_focus",
        "voice_or_breath_control",
        "viewer_empathy_anchor",
        "readable_image_moment",
        "visual_progression",
        "suppression_or_release",
        "end_residue",
    ):
        if not _fragment_grounded(contract.get(field, ""), timeline):
            issues.append(f"performance_contract.{field}未落实到子镜头组")
    if not _fragment_grounded(contract.get("camera_pressure", ""), camera_text):
        issues.append("performance_contract.camera_pressure未落实到主镜头连续规则或子镜头组")
    if not _fragment_grounded(contract.get("scene_pressure", ""), scene_text):
        issues.append("performance_contract.scene_pressure未落实到主体与空间锁定或光照、声音与稳定约束")
    return issues


def ai_model_readiness_issues(metadata, full_prompt="", visible_characters=None):
    """Require a compact self-score focused on AI video model execution risk."""
    metadata = metadata if isinstance(metadata, dict) else {}
    readiness = metadata.get("ai_model_readiness_score")
    visible = _string_list(visible_characters or [])
    required = _readiness_required(metadata, full_prompt, visible)
    has_content = _readiness_has_content(readiness)
    if not required and not has_content:
        return []
    if not visible and readiness in (None, {}):
        return []
    if required and not has_content:
        return ["高风险或人物复杂镜必须提供qa_metadata.ai_model_readiness_score；低风险镜可省略"]
    if not isinstance(readiness, dict):
        return ["qa_metadata.ai_model_readiness_score必须是对象，用于AI视频大模型可执行性自检"]

    issues = []
    scores = []
    for key, label in READINESS_DIMENSIONS.items():
        entry = readiness.get(key)
        if not isinstance(entry, dict):
            issues.append(f"ai_model_readiness_score.{key}（{label}）必须是对象")
            continue
        score = entry.get("score")
        if not isinstance(score, int) or score < 1 or score > 10:
            issues.append(f"ai_model_readiness_score.{key}.score必须是1-10整数")
        else:
            scores.append(score)
        reason = str(entry.get("reason", "") or "").strip()
        if len(reason) < 8 or reason in READINESS_GENERIC_TERMS:
            issues.append(f"ai_model_readiness_score.{key}.reason必须说明具体可见依据或风险，不能只写空泛好评")

    overall = readiness.get("overall")
    if not isinstance(overall, dict):
        issues.append("ai_model_readiness_score.overall必须是对象")
    else:
        score = overall.get("score")
        if not isinstance(score, int) or score < 1 or score > 10:
            issues.append("ai_model_readiness_score.overall.score必须是1-10整数")
        weakest = str(overall.get("weakest_point", "") or "").strip()
        first_pass = str(overall.get("first_pass_check", "") or "").strip()
        if len(weakest) < 6 or weakest in READINESS_GENERIC_TERMS:
            issues.append("ai_model_readiness_score.overall.weakest_point必须写最弱风险点，不能写空泛好评")
        if len(first_pass) < 6:
            issues.append("ai_model_readiness_score.overall.first_pass_check必须写人工首轮检查点")

    if scores and min(scores) >= 9:
        issues.append("ai_model_readiness_score不得所有核心维度都给9分以上；必须暴露T2V首轮最可能失败的维度")

    sections = split_sections(full_prompt, PROMPT_LABELS)
    prompt_text = "\n".join(sections.values())
    if visible:
        if not any(term in prompt_text for term in ("画面左", "画面右", "画面中", "前景", "中景", "后景")):
            issues.append("ai_model_readiness_score不能替代空间锁定；人物镜full_prompt仍需屏幕坐标或景深层级")
        if not any(term in prompt_text for term in ("落幅", "下一镜", "继承", "仍", "保持", "停在", "留在")):
            issues.append("ai_model_readiness_score不能替代尾帧继承；full_prompt必须写落幅/下一镜承接")
    return issues


def _readiness_required(metadata, full_prompt="", visible=None):
    visible = _string_list(visible or [])
    if not visible:
        return False
    if len(visible) >= 2:
        return True
    if isinstance(metadata.get("dialogue_events"), list) and metadata.get("dialogue_events"):
        return True
    if str(metadata.get("editorial_mode", "")) == "shot_group":
        return True
    contract = metadata.get("continuity_contract", {})
    if isinstance(contract, dict):
        if contract.get("state_change") is True:
            return True
        prop_state = str(contract.get("prop_state", "") or "")
        if prop_state and not _is_no_prop_state(prop_state):
            return True
    tension = ""
    for key in ("performance_contract", "emotion_driver", "performance_causality"):
        value = metadata.get(key, {})
        if isinstance(value, dict) and value.get("tension_intent"):
            tension = value.get("tension_intent")
            break
    if tension in ("rising", "peak"):
        return True
    reroll = metadata.get("reroll_control", {})
    if isinstance(reroll, dict) and reroll.get("risk_level") == "high":
        return True
    return bool(re.search(r"拿起|递给|接住|放下|药瓶|手机|钥匙|刀|枪|门外|脚步|封条|转向|转身|硬切|拉焦", str(full_prompt or "")))


def _readiness_has_content(readiness):
    if not isinstance(readiness, dict):
        return False
    for value in readiness.values():
        if isinstance(value, dict):
            if any(str(child).strip() not in ("", "0", "False", "None", "none", "N/A") for child in value.values()):
                return True
        elif str(value).strip():
            return True
    return False


def pressure_release_issues(metadata, full_prompt="", visible_characters=None):
    """Validate pressure is built and released through executable visible beats."""
    metadata = metadata if isinstance(metadata, dict) else {}
    visible = _string_list(visible_characters or [])
    tension = ""
    if isinstance(metadata.get("performance_contract"), dict):
        tension = metadata.get("performance_contract", {}).get("tension_intent", "")
    if not tension and isinstance(metadata.get("emotion_driver"), dict):
        tension = metadata.get("emotion_driver", {}).get("tension_intent", "")
    if not visible and tension not in ("rising", "peak"):
        return []

    design = metadata.get("pressure_release_design")
    if tension not in ("rising", "peak"):
        return []
    if not isinstance(design, dict):
        return ["rising/peak镜必须提供qa_metadata.pressure_release_design，说明压力如何制造和释放"]

    issues = []
    for field in ("pressure_source", "pressure_object", "release_trigger", "release_mode", "release_result", "split_threshold"):
        if len(str(design.get(field, "") or "").strip()) < 4:
            issues.append(f"pressure_release_design.{field}不能为空或过于空泛")
    mode = str(design.get("release_mode", "") or "").strip()
    if mode and mode not in PRESSURE_RELEASE_MODES:
        issues.append("pressure_release_design.release_mode只允许action_completion/interrupted_release/attention_shift/cost_reveal/delayed_release/split_release/release/none")

    steps = design.get("escalation_steps")
    if not isinstance(steps, list) or not steps:
        issues.append("pressure_release_design.escalation_steps必须至少包含一个可见升级点")
    else:
        if len(steps) > 2:
            issues.append("pressure_release_design.escalation_steps最多2个，避免同镜过载")
        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                issues.append(f"pressure_release_design.escalation_steps[{index}]必须是对象")
                continue
            for field in ("time_range", "visible_change", "audience_question"):
                if len(str(step.get(field, "") or "").strip()) < 3:
                    issues.append(f"pressure_release_design.escalation_steps[{index}].{field}不能为空")

    sections = split_sections(full_prompt, PROMPT_LABELS)
    prompt_text = "\n".join(sections.values())
    grounded_fields = ("pressure_object", "release_trigger", "release_result")
    for field in grounded_fields:
        value = str(design.get(field, "") or "").strip() if isinstance(design, dict) else ""
        if value and value not in ("N/A", "none", "无") and not _fragment_grounded(value, prompt_text):
            issues.append(f"pressure_release_design.{field}必须落实到full_prompt的可见画面、声音或落幅状态")
    if isinstance(steps, list):
        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            visible_change = str(step.get("visible_change", "") or "").strip()
            if visible_change and not _fragment_grounded(visible_change, prompt_text):
                issues.append(f"pressure_release_design.escalation_steps[{index}].visible_change必须落实到full_prompt")
    return issues


def story_punch_issues(metadata, full_prompt="", visible_characters=None):
    """Prevent structurally correct but dramatically flat character shots."""
    metadata = metadata if isinstance(metadata, dict) else {}
    visible = _string_list(visible_characters or [])
    contract = metadata.get("story_punch_contract")
    required = _story_punch_required(metadata, full_prompt, visible)
    if not required and contract in (None, {}):
        return []
    if not isinstance(contract, dict):
        return ["人物、对白、道具变化或高张力镜必须提供qa_metadata.story_punch_contract，防止提示词合规但平淡"]

    issues = []
    for field in STORY_PUNCH_FIELDS:
        value = str(contract.get(field, "") or "").strip()
        if (
            len(value) < 4
            or value in GENERIC_PERFORMANCE_TERMS
            or value in READINESS_GENERIC_TERMS
            or STORY_PUNCH_GENERIC_RE.search(value)
            or any(term in value for term in ABSTRACT_VISUAL_TERMS)
        ):
            issues.append(f"story_punch_contract.{field}必须写当前镜头的具体戏眼，不能写空泛情绪词")

    question = str(contract.get("audience_question", "") or "")
    if not re.search(r"谁|为什么|是否|怎么|何时|会不会|能否|真相|代价|阻挡|隐瞒|想要", question):
        issues.append("story_punch_contract.audience_question必须让观众形成一个具体问题")

    sections = split_sections(full_prompt, PROMPT_LABELS)
    prompt_text = "\n".join(sections.values())
    for field in (
        "visible_pressure_object", "dramatic_turn", "picture_punctuation",
        "composition_priority", "camera_motivation", "end_residue",
    ):
        value = str(contract.get(field, "") or "").strip()
        if value and value not in ("none", "无", "N/A") and not _fragment_grounded(value, prompt_text):
            issues.append(f"story_punch_contract.{field}必须落实到full_prompt的可见动作、道具、构图或落幅残留")

    composition = str(contract.get("composition_priority", "") or "")
    if composition and not re.search(r"画面|前景|中景|后景|三分|中心|中央|留白|遮挡|距离|占比|实焦|虚焦", composition):
        issues.append("story_punch_contract.composition_priority必须写主体与前中后景、画面位置、留白、遮挡、距离或焦点关系")
    camera = str(contract.get("camera_motivation", "") or "")
    if camera and not re.search(r"固定|推近|拉远|横移|跟拍|拉焦|重构图|机位|摄影机", camera):
        issues.append("story_punch_contract.camera_motivation必须写唯一运镜或固定机位策略")
    if camera and not re.search(r"响应|因为|跟随|服务|守住|等待|对应|触发|落点|保持", camera):
        issues.append("story_punch_contract.camera_motivation必须说明镜头为何响应表演、台词、道具或空间关系")

    timeline = sections.get("子镜头组", "")
    has_visible_spike = bool(STORY_PUNCH_SPIKE_RE.search(timeline))
    has_listener_or_dialogue = bool(metadata.get("dialogue_events"))
    if required and not has_visible_spike and has_listener_or_dialogue:
        issues.append("story_punch_contract要求对白/人物镜至少有一个可见戏剧尖刺：反应延迟、未完成动作、道具压力、视线错位、打断或尾帧残留")
    return issues


def _story_punch_required(metadata, full_prompt="", visible=None):
    visible = _string_list(visible or [])
    if len(visible) >= 1:
        return True
    if isinstance(metadata.get("dialogue_events"), list) and metadata.get("dialogue_events"):
        return True
    contract = metadata.get("continuity_contract", {})
    if isinstance(contract, dict) and (contract.get("state_change") is True or contract.get("state_transitions")):
        return True
    tension = ""
    for key in ("performance_contract", "emotion_driver", "performance_causality"):
        value = metadata.get(key, {})
        if isinstance(value, dict) and value.get("tension_intent"):
            tension = value.get("tension_intent")
            break
    if tension in ("rising", "peak"):
        return True
    return bool(re.search(r"质问|拒绝|承认|反转|揭示|威胁|门外|脚步|药瓶|手机|钥匙|停住|打断|转身|递给|接住", str(full_prompt or "")))


def character_scene_objective_issues(metadata, full_prompt="", visible_characters=None, required=True):
    """Require playable objectives and tactics, not only named emotions."""
    metadata = metadata if isinstance(metadata, dict) else {}
    contract = metadata.get("character_scene_objective_contract")
    if not required and contract in (None, {}, ""):
        return []
    if not isinstance(contract, dict):
        return ["人物表演镜必须提供qa_metadata.character_scene_objective_contract"]
    issues = _flat_directing_contract_issues(
        contract, CHARACTER_SCENE_OBJECTIVE_FIELDS, "character_scene_objective_contract"
    )
    visible = _string_list(visible_characters or [])
    focus = str(contract.get("focus_character", "") or "").strip()
    if visible and focus not in visible:
        issues.append("character_scene_objective_contract.focus_character必须是本镜可见人物")
    if str(contract.get("scene_objective", "") or "").strip() in GENERIC_PERFORMANCE_TERMS:
        issues.append("character_scene_objective_contract.scene_objective必须写角色要从对方或环境得到的具体结果")
    tactic_shift = str(contract.get("tactic_shift", "") or "").strip()
    if tactic_shift and not re.search(r"无切换|继续|维持|改用|转为|从.{0,30}到|触发|失败|受阻", tactic_shift):
        issues.append("character_scene_objective_contract.tactic_shift必须写触发后的策略变化，或说明为何维持当前策略")
    power = str(contract.get("power_state_change", "") or "").strip()
    if power and not re.search(r"由|从|转为|变为|维持|仍|上升|下降|夺回|失去|反转|持平", power):
        issues.append("character_scene_objective_contract.power_state_change必须写本镜前后权力状态")
    if full_prompt:
        for field in ("visible_tactic_evidence", "end_action_state"):
            value = str(contract.get(field, "") or "").strip()
            if value and not _fragment_grounded(value, full_prompt):
                issues.append(f"character_scene_objective_contract.{field}必须落实到full_prompt的可见行动")
    return issues


def relationship_emotion_arc_issues(metadata, full_prompt="", required=True):
    """Validate the relationship change that gives micro-emotion dramatic direction."""
    metadata = metadata if isinstance(metadata, dict) else {}
    contract = metadata.get("relationship_emotion_arc")
    if not required and contract in (None, {}, ""):
        return []
    if not isinstance(contract, dict):
        return ["对手戏必须提供qa_metadata.relationship_emotion_arc"]
    issues = _flat_directing_contract_issues(
        contract, RELATIONSHIP_EMOTION_ARC_FIELDS, "relationship_emotion_arc"
    )
    participants = str(contract.get("participants", "") or "")
    if participants and len(re.findall(r"[^、,，/与和\s]+", participants)) < 2:
        issues.append("relationship_emotion_arc.participants必须包含至少两个关系参与者")
    power = str(contract.get("power_shift", "") or "")
    if power and not re.search(r"由|从|转为|变为|维持|反转|夺回|失去|上升|下降|持平", power):
        issues.append("relationship_emotion_arc.power_shift必须写权力关系前后变化")
    if full_prompt:
        for field in ("turn_trigger", "shared_residue"):
            value = str(contract.get(field, "") or "").strip()
            if value and not re.search(r"^(?:无转折|无共同余波|none)[:：]", value, re.I) and not _fragment_grounded(value, full_prompt):
                issues.append(f"relationship_emotion_arc.{field}必须落实到full_prompt的可见关系变化")
    return issues


def sequence_directing_plan_issues(metadata, full_prompt="", required=True):
    """Validate one shot's place inside a scene-wide visual sentence."""
    metadata = metadata if isinstance(metadata, dict) else {}
    contract = metadata.get("sequence_directing_plan")
    if not required and contract in (None, {}, ""):
        return []
    if not isinstance(contract, dict):
        return ["每镜必须提供qa_metadata.sequence_directing_plan"]
    issues = _flat_directing_contract_issues(
        contract, SEQUENCE_DIRECTING_PLAN_FIELDS, "sequence_directing_plan"
    )
    if contract.get("sequence_position") not in SEQUENCE_POSITIONS:
        issues.append("sequence_directing_plan.sequence_position只允许establish/hold/escalate/break/release/resolve")
    if full_prompt:
        grounded = sum(
            _fragment_grounded(str(contract.get(field, "") or ""), full_prompt)
            for field in ("composition_motif_state", "blocking_camera_coordination", "environment_beat")
        )
        if grounded < 2:
            issues.append("sequence_directing_plan的构图母题、联合调度与环境节拍至少两项必须落实到full_prompt")
    return issues


def cut_decision_contract_issues(metadata, full_prompt="", required=True):
    """Require a causal cut or an explicit decision to hold the shot."""
    metadata = metadata if isinstance(metadata, dict) else {}
    contract = metadata.get("cut_decision_contract")
    if not required and contract in (None, {}, ""):
        return []
    if not isinstance(contract, dict):
        return ["每镜必须提供qa_metadata.cut_decision_contract"]
    issues = _flat_directing_contract_issues(contract, CUT_DECISION_FIELDS, "cut_decision_contract")
    mode = str(contract.get("cut_mode", "") or "").strip()
    if mode not in CUT_MODES:
        issues.append("cut_decision_contract.cut_mode无效")
    trigger = str(contract.get("trigger", "") or "").strip()
    if mode != "hold" and full_prompt and trigger and not _fragment_grounded(trigger, full_prompt):
        issues.append("cut_decision_contract.trigger必须来自full_prompt中的动作、反应、声音或台词落点")
    if mode == "hold" and not re.search(r"保持|不切|连续|完整|等待|守住|hold", str(contract.get("economy_reason", "") or ""), re.I):
        issues.append("cut_decision_contract为hold时economy_reason必须说明不切镜的叙事收益")
    return issues


def prompt_information_budget_issues(metadata, full_prompt="", required=True):
    """Keep stronger directing analysis from bloating the platform prompt."""
    metadata = metadata if isinstance(metadata, dict) else {}
    contract = metadata.get("prompt_information_budget")
    if not required and contract in (None, {}, ""):
        return []
    if not isinstance(contract, dict):
        return ["每镜必须提供qa_metadata.prompt_information_budget"]
    issues = _flat_directing_contract_issues(
        contract, PROMPT_INFORMATION_BUDGET_FIELDS, "prompt_information_budget"
    )
    if contract.get("profile") not in PROMPT_INFORMATION_PROFILES:
        issues.append("prompt_information_budget.profile无效")
    limit = contract.get("visual_enhancer_limit")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 2:
        issues.append("prompt_information_budget.visual_enhancer_limit必须是1或2")
    primary_task = str(contract.get("primary_render_task", "") or "").strip()
    must_render = str(contract.get("must_render", "") or "").strip()
    if re.fullmatch(r"(?:完成|呈现|表现|做好|增强)?(?:当前)?(?:主任务|剧情|画面|镜头|电影感|高级感|质感)", primary_task):
        issues.append("prompt_information_budget.primary_render_task不能是空泛目标")
    if full_prompt and must_render:
        missing_units = [
            unit for unit in _budget_units(must_render)
            if not _fragment_grounded(unit, full_prompt)
        ]
        if missing_units:
            issues.append(
                "prompt_information_budget.must_render存在未落实硬事实："
                + "、".join(missing_units[:4])
            )
    metadata_only = str(contract.get("metadata_only", "") or "").strip()
    if full_prompt and len(metadata_only) >= 4 and metadata_only in full_prompt:
        issues.append("prompt_information_budget.metadata_only不得原样泄漏到full_prompt")
    compression = str(contract.get("compression_rule", "") or "").strip()
    if compression and not re.search(r"优先|先删|删除|压缩|整句|保留|不得|不可", compression):
        issues.append("prompt_information_budget.compression_rule必须写清保留或整句删除顺序")
    return issues


def _budget_units(value):
    units = [unit.strip(" -\t") for unit in re.split(r"[；;|\n]+", str(value or ""))]
    return [unit for unit in units if len(unit) >= 3]


def sound_directing_plan_issues(metadata, full_prompt="", audio_enabled=False, required=True):
    """Validate spatial sound perspective without forcing audio into silent T2V jobs."""
    metadata = metadata if isinstance(metadata, dict) else {}
    contract = metadata.get("sound_directing_plan")
    if not required and contract in (None, {}, ""):
        return []
    if not isinstance(contract, dict):
        return ["每镜必须提供qa_metadata.sound_directing_plan"]
    issues = _flat_directing_contract_issues(contract, SOUND_DIRECTING_PLAN_FIELDS, "sound_directing_plan")
    if audio_enabled and full_prompt:
        grounded = sum(
            _fragment_grounded(str(contract.get(field, "") or ""), full_prompt)
            for field in (
                "source_direction_distance", "room_environment_response",
                "silence_or_drop", "lead_lag_strategy",
            )
        )
        if grounded < 1:
            issues.append("原生音频开启时sound_directing_plan至少一项空间声、房间响应、静音或声画先后必须落实到full_prompt")
    return issues


def _flat_directing_contract_issues(contract, fields, label):
    issues = []
    for field in fields:
        value = contract.get(field)
        if not isinstance(value, str) or len(value.strip()) < 3:
            issues.append(f"{label}.{field}必须是非空扁平字符串")
        elif len(value) > 220:
            issues.append(f"{label}.{field}过长，应压缩为单句导演判断")
    for field, value in contract.items():
        if isinstance(value, (dict, list)):
            issues.append(f"{label}.{field}必须保持扁平，不能嵌套对象或数组")
    return issues


def listener_reaction_issues(metadata, full_prompt=""):
    """Require one restrained, visible listener response when a speaker has a supporting listener."""
    metadata = metadata if isinstance(metadata, dict) else {}
    if isinstance(metadata.get("fight_continuity"), dict):
        return []
    roles = metadata.get("performance_priority", {}) if isinstance(metadata.get("performance_priority"), dict) else {}
    supporting = _string_list(roles.get("supporting", []))
    events = metadata.get("dialogue_events", []) if isinstance(metadata.get("dialogue_events"), list) else []
    speakers = {
        str(event.get("speaker", "") or "").strip()
        for event in events if isinstance(event, dict)
        and event.get("kind") == "台词" and event.get("speaker_visibility") == "visible"
    }
    listeners = [name for name in supporting if name and name not in speakers]
    if not speakers or not listeners:
        return []
    plan = metadata.get("listener_reaction_plan")
    if not isinstance(plan, dict):
        return ["可见说话者与supporting听者同镜必须提供qa_metadata.listener_reaction_plan"]
    issues = []
    for field in ("speaker", "listener", "trigger", "time_range", "visual_evidence", "motion_limit", "end_residue"):
        if len(str(plan.get(field, "") or "").strip()) < 2:
            issues.append(f"listener_reaction_plan.{field}不能为空")
    if str(plan.get("speaker", "") or "").strip() not in speakers:
        issues.append("listener_reaction_plan.speaker必须是可见台词说话者")
    if str(plan.get("listener", "") or "").strip() not in listeners:
        issues.append("listener_reaction_plan.listener必须是非说话supporting人物")
    if plan.get("lip_sync") is not False:
        issues.append("listener_reaction_plan.lip_sync必须为false")
    if not re.fullmatch(r"\d+(?:\.\d+)?-\d+(?:\.\d+)?秒", str(plan.get("time_range", "") or "").strip()):
        issues.append("listener_reaction_plan.time_range必须是连续小数秒范围")
    timeline = split_sections(full_prompt, PROMPT_LABELS).get("子镜头组", "")
    for field in ("visual_evidence", "motion_limit", "end_residue"):
        if str(plan.get(field, "") or "").strip() and not _fragment_grounded(plan.get(field, ""), timeline):
            issues.append(f"listener_reaction_plan.{field}未落实到子镜头组")
    listener = str(plan.get("listener", "") or "").strip()
    if listener and not re.search(re.escape(listener) + r".{0,24}(?:口型闭合|不动口|无同步口型)", timeline):
        issues.append("listener_reaction_plan倾听者必须在子镜头组明确口型闭合")
    return issues


def shot_group_handoff_issues(metadata):
    """Reject A→B→A or any second person-to-person handoff inside one T2V task."""
    metadata = metadata if isinstance(metadata, dict) else {}
    if metadata.get("editorial_mode", "continuous_take") != "shot_group":
        return []
    beats = metadata.get("camera_beat_map", [])
    if not isinstance(beats, list):
        return []
    owners = []
    for index, beat in enumerate(beats):
        if not isinstance(beat, dict):
            continue
        owner = str(beat.get("focus_owner", "") or "").strip()
        if not owner:
            return [f"camera_beat_map[{index}].focus_owner不能为空"]
        if owner != "object" and (not owners or owners[-1] != owner):
            owners.append(owner)
    if len(owners) > 2:
        return ["同一即梦shot_group出现第二次人物注意力交接（如A→B→A），必须拆为下一条T2V任务"]
    return []


def insert_shot_issues(metadata, full_prompt="", duration=None, visible_characters=None):
    """Validate motivated insert shots without adding a separate required schema."""
    metadata = metadata if isinstance(metadata, dict) else {}
    full_prompt = str(full_prompt or "")
    sections = split_sections(full_prompt, PROMPT_LABELS)
    timeline = sections.get("子镜头组", "")
    beats = metadata.get("camera_beat_map", [])
    beats = beats if isinstance(beats, list) else []
    beat_text = " ".join(
        " ".join(str(value or "") for value in beat.values())
        for beat in beats if isinstance(beat, dict)
    )
    combined = timeline + "\n" + beat_text
    has_insert = any(term in combined for term in INSERT_TERMS) or any(
        isinstance(beat, dict) and str(beat.get("insert_function", "") or "").strip()
        for beat in beats
    )
    if not has_insert:
        return []

    issues = []
    if metadata.get("editorial_mode", "continuous_take") != "shot_group":
        issues.append("插入镜头必须作为shot_group内部子镜，不得混入continuous_take")

    children = [
        match.group(3)
        for match in JIMENG_CHILD_SHOT_RE.finditer(timeline)
        if any(term in match.group(3) for term in INSERT_TERMS)
        or any(function in match.group(3) for function in INSERT_FUNCTIONS)
    ]
    insert_count = len(children)
    try:
        seconds = float(duration or 0)
    except (TypeError, ValueError):
        seconds = 0
    max_insert = 1 if seconds <= 6 else 2 if seconds <= 10 else 3
    if insert_count > max_insert:
        issues.append(f"插入镜头数量{insert_count}超过当前时长上限{max_insert}")

    for index, body in enumerate(children, 1):
        if not any(function in body for function in INSERT_FUNCTIONS):
            issues.append(f"插入镜头{index}必须写清插入功能：{'/'.join(INSERT_FUNCTIONS)}")
        if DECORATIVE_INSERT_RE.search(body):
            issues.append(f"插入镜头{index}出现装饰性/无关动机，必须删除或改为有信息增量的细节")
        if not re.search(r"信息|线索|伏笔|状态|变化|残留|压力|关系|道具|杯|文件|手机|钥匙|伤口|血迹|衣角|门|桌|光|影|声音桥|切回|回到|承接", body):
            issues.append(f"插入镜头{index}缺少新信息、状态变化、关系压力或回到主线承接")
    for first, second in zip(children, children[1:]):
        if FACE_CLOSEUP_RE.search(first) and FACE_CLOSEUP_RE.search(second):
            issues.append("插入镜头不得连续使用人物脸部大特写")

    transition = metadata.get("temporal_transition_contract", {})
    transition_enabled = isinstance(transition, dict) and transition.get("enabled") is True
    if TEMPORAL_INSERT_RE.search(combined) and not transition_enabled:
        issues.append("回忆/幻想/时空意象插入必须启用temporal_transition_contract，或拆为独立主镜")

    visible = _string_list(visible_characters or [])
    reroll = metadata.get("reroll_control", {})
    if visible:
        if not isinstance(reroll, dict):
            issues.append("人物镜使用插入镜时必须提供reroll_control")
        else:
            risk_reason = str(reroll.get("risk_reason", "") or "")
            if not any(token in risk_reason for token in ("插入", "切入", "特写", "空镜", "细节")):
                issues.append("使用插入镜时reroll_control.risk_reason必须包含插入/切入风险来源")
            mitigation = reroll.get("mitigation_steps")
            mitigation_text = "；".join(str(step or "") for step in mitigation if str(step or "").strip()) if isinstance(mitigation, list) else ""
            for label, pattern in (
                ("插入前落幅", r"插入前|切入前|前一子镜|前落幅"),
                ("插入主体", r"插入主体|切入主体|特写主体|细节主体|道具主体"),
                ("回到主线状态", r"切回|回到主线|回到人物|返回主线|插入后"),
                ("声音桥", r"声音桥|音效承接|环境声|对白尾音|旁白延续"),
            ):
                if not re.search(pattern, mitigation_text):
                    issues.append(f"插入镜reroll_control.mitigation_steps缺少{label}稳定措施")
    return issues


def expectation_anchor_issues(metadata, full_prompt=""):
    """Validate visible anticipation anchors without forcing object close-ups."""
    metadata = metadata if isinstance(metadata, dict) else {}
    item = metadata.get("expectation_anchor")
    if item is None:
        return []
    if not isinstance(item, dict):
        return ["qa_metadata.expectation_anchor必须是对象"]
    if not isinstance(item.get("applicable"), bool):
        return ["expectation_anchor.applicable必须是布尔值"]
    fields = ("semantic_mode", "anchor", "expecting_subject", "source_interpretation", "start_state", "progress_event", "detail_cut_rule", "return_reaction", "end_state")
    if not item.get("applicable"):
        return []
    if item.get("anchor_type") not in ("object", "person_action", "event", "space", "custom_visible"):
        return ["expectation_anchor.anchor_type只允许object/person_action/event/space/custom_visible"]
    if item.get("semantic_mode") not in ("literal_agent", "figurative_personification", "need_or_lack", "symbolic_association"):
        return ["expectation_anchor.semantic_mode只允许literal_agent/figurative_personification/need_or_lack/symbolic_association"]
    issues = ["expectation_anchor.%s适用时不能为空" % field for field in fields if len(str(item.get(field, "") or "").strip()) < 2]
    timeline = split_sections(full_prompt, PROMPT_LABELS).get("子镜头组", "")
    for field in ("anchor", "progress_event", "return_reaction", "end_state"):
        if field not in issues and not _fragment_grounded(item.get(field, ""), timeline):
            issues.append("expectation_anchor.%s未落实到子镜头组" % field)
    if item.get("applicable") and "特写" in str(item.get("detail_cut_rule", "")) and not re.search(r"硬切|切到|切回|特写", timeline):
        issues.append("expectation_anchor.detail_cut_rule要求特写但时间轴没有锚点切镜")
    if item.get("semantic_mode") in ("figurative_personification", "symbolic_association") and re.search(r"(?:花|风|月亮|灯光).{0,8}(?:抬头|等待|回头|伸手|说话)", timeline):
        issues.append("expectation_anchor拟人/象征模式不得把环境意象误写为实体角色行动")
    return issues


def state_transition_replay_issues(previous_metadata, previous_prompt, metadata, full_prompt):
    """Reject an adjacent shot that restages an already-carried state change.

    These checks intentionally target source-visible state transitions rather
    than ordinary repeated objects. A phone may remain visible across shots;
    a phone screen may not *become lit* twice without an intervening reset.
    """
    previous_metadata = previous_metadata if isinstance(previous_metadata, dict) else {}
    metadata = metadata if isinstance(metadata, dict) else {}
    previous_continuity = previous_metadata.get("continuity_contract", {})
    current_continuity = metadata.get("continuity_contract", {})
    previous_continuity = previous_continuity if isinstance(previous_continuity, dict) else {}
    current_continuity = current_continuity if isinstance(current_continuity, dict) else {}
    previous = " ".join(str(value or "") for value in (
        previous_prompt, previous_metadata.get("end_state", ""),
        previous_continuity.get("end_anchor", ""), previous_continuity.get("next_carryover", ""),
    ))
    current = " ".join(str(value or "") for value in (
        full_prompt, metadata.get("start_state", ""), current_continuity.get("start_anchor", ""),
    ))
    phone_carried = "手机" in previous and any(token in previous for token in ("亮屏", "屏幕亮", "来电", "来电界面"))
    phone_replayed = "手机" in current and any(token in current for token in (
        "突然亮起", "屏幕亮起", "亮起或震动", "来电界面出现", "显示来电界面",
    ))
    if phone_carried and phone_replayed:
        return ["上一镜已完成手机亮屏/来电状态，本镜必须继承该状态后继续动作，不能再次演绎亮屏或来电出现"]
    return []


def continuity_contract_issues(metadata, full_prompt="", visible_characters=None):
    """Validate cross-shot continuity anchors for positions, eyelines, props, and light."""
    metadata = metadata if isinstance(metadata, dict) else {}
    visible = _string_list(visible_characters or [])
    contract = metadata.get("continuity_contract")
    if not visible and contract in (None, {}):
        return []
    if not isinstance(contract, dict):
        return ["有人物镜头必须提供qa_metadata.continuity_contract"]
    issues = []
    required = (
        "start_anchor",
        "end_anchor",
        "position_continuity",
        "eyeline_continuity",
        "prop_state",
        "lighting_continuity",
        "next_carryover",
    )
    for field in required:
        if len(str(contract.get(field, "") or "").strip()) < 3:
            issues.append(f"continuity_contract.{field}不能为空")
    if not isinstance(contract.get("state_change", False), bool):
        issues.append("continuity_contract.state_change必须是布尔值")
    transitions = contract.get("state_transitions", [])
    if not isinstance(transitions, list):
        issues.append("continuity_contract.state_transitions必须是数组")
    if contract.get("state_change") and not transitions:
        issues.append("人物位置、视线或可移动道具变化时必须提供state_transitions")
    for index, transition in enumerate(transitions if isinstance(transitions, list) else []):
        if not isinstance(transition, dict):
            issues.append(f"state_transitions[{index}]必须是对象")
            continue
        for field in ("subject", "from_state", "intermediate_state", "to_state", "cause", "time_range"):
            if not str(transition.get(field, "") or "").strip():
                issues.append(f"state_transitions[{index}].{field}不能为空")
        intermediate = str(transition.get("intermediate_state", "") or "").strip()
        for state_field in ("from_state", "to_state"):
            state_value = str(transition.get(state_field, "") or "").strip()
            if state_value and not _fragment_grounded(state_value, full_prompt):
                issues.append(f"state_transitions[{index}].{state_field}必须落实到模型提示词")
        if intermediate and not _fragment_grounded(intermediate, full_prompt):
            issues.append(f"state_transitions[{index}].intermediate_state必须落实到模型提示词中的可见承接动作")
        if intermediate and _looks_like_terminal_state(intermediate):
            issues.append(f"state_transitions[{index}].intermediate_state不能只写终态，必须写手伸向/接触/半转/重心跟随等中间动作")
    if not _fragment_grounded(contract.get("start_anchor", ""), full_prompt):
        issues.append("continuity_contract.start_anchor必须能在模型提示词中找到起幅事实")
    if not _fragment_grounded(contract.get("end_anchor", ""), full_prompt):
        issues.append("continuity_contract.end_anchor必须能在模型提示词中找到可见落幅")
    if not _fragment_grounded(contract.get("next_carryover", ""), full_prompt):
        issues.append("continuity_contract.next_carryover必须落实为可承接的画面残留")
    for field in ("position_continuity", "eyeline_continuity", "lighting_continuity"):
        value = str(contract.get(field, "") or "").strip()
        if value and not _fragment_grounded(value, full_prompt):
            issues.append(f"continuity_contract.{field}必须落实到模型提示词中的可见事实")
    prop_state = str(contract.get("prop_state", "") or "").strip()
    if prop_state and not _is_no_prop_state(prop_state) and not _fragment_grounded(prop_state, full_prompt):
        issues.append("continuity_contract.prop_state必须落实到模型提示词中的可见事实")
    return issues


def reroll_control_issues(metadata, generation_control=None, visible_characters=None):
    """Validate reroll-risk acknowledgement and mitigation before export."""
    metadata = metadata if isinstance(metadata, dict) else {}
    visible = _string_list(visible_characters or [])
    control = generation_control if isinstance(generation_control, dict) else {}
    reroll = metadata.get("reroll_control")
    if not visible and reroll in (None, {}):
        return []
    if not isinstance(reroll, dict):
        return ["有人物镜头必须提供qa_metadata.reroll_control"]

    issues = []
    risk = reroll.get("risk_level")
    if risk not in REROLL_RISK_LEVELS:
        issues.append("reroll_control.risk_level只允许low/medium/high")
    for field in ("identity_anchor", "motion_anchor", "scene_anchor", "camera_anchor", "risk_reason"):
        if len(str(reroll.get(field, "") or "").strip()) < 4:
            issues.append(f"reroll_control.{field}不能为空或过于空泛")
    mitigation = reroll.get("mitigation_steps")
    if not isinstance(mitigation, list) or len([step for step in mitigation if str(step).strip()]) < 2:
        issues.append("reroll_control.mitigation_steps至少需要两条具体降抽卡策略")
    if not isinstance(reroll.get("manual_first_pass_check"), bool):
        issues.append("reroll_control.manual_first_pass_check必须是布尔值")

    mode = control.get("mode")
    tension = (
        metadata.get("performance_contract", {}).get("tension_intent")
        if isinstance(metadata.get("performance_contract"), dict)
        else metadata.get("performance_causality", {}).get("tension_intent")
        if isinstance(metadata.get("performance_causality"), dict)
        else ""
    )
    if visible and mode == "t2v" and risk == "low":
        issues.append("T2V人物镜不得把reroll_control.risk_level标为low")
    if mode != "t2v":
        issues.append("reroll_control只支持T2V generation_control")
    if visible and tension in ("rising", "peak") and reroll.get("manual_first_pass_check") is not True:
        issues.append("T2V rising/peak人物镜必须标记manual_first_pass_check=true")
    return issues


def temporal_transition_contract_issues(metadata, full_prompt="", duration=None, expected_contract=None):
    """Validate the source-grounded, single-effect in-model transition contract."""
    metadata = metadata if isinstance(metadata, dict) else {}
    expected = expected_contract if isinstance(expected_contract, dict) else {}
    contract = metadata.get("temporal_transition_contract")
    candidate_kind = expected.get("kind", "none")
    candidate_trigger = str(expected.get("source_trigger", "") or "").strip()
    if not isinstance(contract, dict):
        return ["qa_metadata.temporal_transition_contract必须是对象"]
    issues = []
    enabled = contract.get("enabled")
    if not isinstance(enabled, bool):
        return ["temporal_transition_contract.enabled必须是布尔值"]
    if contract.get("kind") not in TEMPORAL_TRANSITION_KINDS:
        issues.append("temporal_transition_contract.kind无效")
        return issues
    if contract.get("kind") != candidate_kind:
        issues.append("temporal_transition_contract.kind必须继承源文候选类型")
    if candidate_trigger and str(contract.get("source_trigger", "") or "").strip() != candidate_trigger:
        issues.append("temporal_transition_contract.source_trigger必须逐字继承源文候选")
    if not enabled:
        if candidate_kind != "none" and len(str(contract.get("decision_reason", "") or "").strip()) < 6:
            issues.append("未启用的时空转场候选必须记录不转场的源文依据")
        return issues
    if candidate_kind == "none":
        issues.append("无源文时空触发时不得启用特效转场")
        return issues
    effect = contract.get("effect")
    if not isinstance(effect, str) or len(effect.strip()) < 3 or any(mark in effect for mark in ("、", ",", "+", "/")):
        issues.append("temporal_transition_contract.effect必须是唯一视觉效果")
    for field in ("time_range", "effect_source_basis", "from_state", "to_state", "audio_bridge", "prompt_anchor", "fallback"):
        if len(str(contract.get(field, "") or "").strip()) < 3:
            issues.append(f"temporal_transition_contract.{field}启用时不能为空")
    if contract.get("lip_sync") is not False:
        issues.append("时空/特效转场必须明确lip_sync=false")
    prompt_anchor = str(contract.get("prompt_anchor", "") or "").strip()
    if prompt_anchor and not _fragment_grounded(prompt_anchor, full_prompt):
        issues.append("temporal_transition_contract.prompt_anchor必须逐字出现在模型提示词")
    audio_bridge = str(contract.get("audio_bridge", "") or "").strip()
    if audio_bridge and not _fragment_grounded(audio_bridge, full_prompt):
        issues.append("temporal_transition_contract.audio_bridge必须逐字出现在模型提示词")
    parsed = _parse_second_range(contract.get("time_range"))
    if parsed is None:
        issues.append("temporal_transition_contract.time_range必须为0.0-1.0秒格式")
    elif duration is not None and parsed[1] > float(duration) + 1e-6:
        issues.append("temporal_transition_contract.time_range不得超出主镜时长")
    reroll = metadata.get("reroll_control", {})
    if not isinstance(reroll, dict) or reroll.get("risk_level") != "high":
        issues.append("启用时空/特效转场必须标为high reroll risk")
    elif reroll.get("manual_first_pass_check") is not True:
        issues.append("启用时空/特效转场必须manual_first_pass_check=true")
    return issues


def _parse_second_range(value):
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*秒\s*", str(value or ""))
    if not match:
        return None
    start, end = float(match.group(1)), float(match.group(2))
    return (start, end) if start < end else None


def dialogue_event_issues(
    metadata,
    expected_events=None,
    visible_characters=None,
    full_prompt="",
    audio_enabled=None,
    duration=None,
):
    """Validate dialogue/OS/OV identity, timing, performance, and prompt placement."""
    metadata = metadata if isinstance(metadata, dict) else {}
    refs = _string_list(metadata.get("dialogue_refs", []))
    events = metadata.get("dialogue_events")
    if not refs and events in (None, []):
        return []
    if not isinstance(events, list):
        return ["qa_metadata.dialogue_events必须是数组"]

    issues = []
    event_refs = [str(event.get("ref", "") or "").strip() for event in events if isinstance(event, dict)]
    if len(event_refs) != len(events):
        issues.append("dialogue_events每项必须是对象")
    if event_refs != refs:
        issues.append("dialogue_events必须按dialogue_refs顺序一一覆盖")

    expected_was_provided = expected_events is not None
    expected = expected_events if isinstance(expected_events, list) else []
    expected_identity = [
        (
            str(event.get("ref", "") or ""),
            str(event.get("kind", "") or ""),
            str(event.get("speaker", "") or ""),
            str(event.get("text", "") or ""),
        )
        for event in expected if isinstance(event, dict)
    ]
    actual_identity = [
        (
            str(event.get("ref", "") or ""),
            str(event.get("kind", "") or ""),
            str(event.get("speaker", "") or ""),
            str(event.get("text", "") or ""),
        )
        for event in events if isinstance(event, dict)
    ]
    if expected_was_provided and refs and not expected:
        issues.append("Director缺少锁定的dialogue_events源记录")
    elif expected and actual_identity != expected_identity:
        issues.append("dialogue_events的ref/kind/speaker/text与Director原文不一致")

    sections = split_sections(full_prompt, PROMPT_LABELS)
    timeline = sections.get("子镜头组", "")
    visible = set(_string_list(visible_characters or [])) if visible_characters is not None else set()
    try:
        total_duration = float(duration or 0)
    except (TypeError, ValueError):
        total_duration = 0

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        prefix = f"dialogue_events[{index}]"
        ref = str(event.get("ref", "") or "").strip()
        kind = str(event.get("kind", "") or "").strip()
        speaker = str(event.get("speaker", "") or "").strip()
        line = str(event.get("text", "") or "")
        visibility = str(event.get("speaker_visibility", "") or "").strip()
        facial = str(event.get("facial_state", "") or "").strip()
        body = str(event.get("body_state", "") or "").strip()
        delivery = str(event.get("delivery", "") or "").strip()
        breath_pause_plan = str(event.get("breath_pause_plan", "") or "").strip()
        lip_sync = event.get("lip_sync")
        line_function = str(event.get("line_function", "") or "").strip()
        subtext = str(event.get("subtext", "") or "").strip()
        stress_words = event.get("stress_words")
        subtext_evidence = str(event.get("subtext_visible_evidence", "") or "").strip()
        turn_relation = str(event.get("turn_relation", "") or "").strip()
        conversation_mode = str(event.get("conversation_mode", "") or "").strip()
        response_latency = str(event.get("response_latency", "") or "").strip()
        overlap_window = str(event.get("overlap_or_interrupt_window", "") or "").strip()
        conversation_source_basis = str(event.get("conversation_source_basis", "") or "").strip()

        if not ref:
            issues.append(f"{prefix}.ref不能为空")
        if kind not in SPEECH_KINDS:
            issues.append(f"{prefix}.kind只允许台词/OS/OV")
        if not speaker:
            issues.append(f"{prefix}.speaker不能为空")
        if not line:
            issues.append(f"{prefix}.text不能为空")
        if visibility not in SPEAKER_VISIBILITIES:
            issues.append(f"{prefix}.speaker_visibility只允许visible/offscreen/nonphysical")
        if len(facial) < 2:
            issues.append(f"{prefix}.facial_state不能为空")
        if len(body) < 2:
            issues.append(f"{prefix}.body_state不能为空")
        if len(delivery) < 2:
            issues.append(f"{prefix}.delivery不能为空")
        if len(breath_pause_plan) < 6:
            issues.append(f"{prefix}.breath_pause_plan不能为空")
        elif not re.search(r"(?:句前|开口前|起句).{0,12}\d+(?:\.\d+)?秒", breath_pause_plan):
            issues.append(f"{prefix}.breath_pause_plan缺少带秒数的起句气口")
        elif not re.search(r"(?:句末|尾音|收气|落点).{0,12}\d+(?:\.\d+)?秒", breath_pause_plan):
            issues.append(f"{prefix}.breath_pause_plan缺少带秒数的句末收气")
        elif len(re.findall(r"[，、；：！？…]", line)) >= 2 and not re.search(r"(?:中段|分句|转折|[，、；：！？…]后).{0,18}\d+(?:\.\d+)?秒|无中段气口", breath_pause_plan):
            issues.append(f"{prefix}.breath_pause_plan缺少分句/转折气口，或未明确无中段气口")
        if line_function not in DIALOGUE_LINE_FUNCTIONS:
            issues.append(f"{prefix}.line_function无效")
        if len(subtext) < 4 or subtext in GENERIC_PERFORMANCE_TERMS:
            issues.append(f"{prefix}.subtext必须写本句未明说的具体意图或防御")
        elif _signature_text(subtext) == _signature_text(line):
            issues.append(f"{prefix}.subtext不能复述原台词")
        if not isinstance(stress_words, list) or not 1 <= len(stress_words) <= 3:
            issues.append(f"{prefix}.stress_words必须包含1-3个原文词组")
        else:
            for word in stress_words:
                word = str(word or "").strip()
                if not word or word not in line:
                    issues.append(f"{prefix}.stress_words必须逐字来自原台词")
                elif word not in delivery:
                    issues.append(f"{prefix}.delivery必须说明重音词“{word}”的说法")
        if turn_relation not in DIALOGUE_TURN_RELATIONS:
            issues.append(f"{prefix}.turn_relation无效")
        if len(subtext_evidence) < 4:
            issues.append(f"{prefix}.subtext_visible_evidence必须写可见潜台词证据")
        if conversation_mode:
            if conversation_mode not in CONVERSATION_MODES:
                issues.append(f"{prefix}.conversation_mode无效")
            if not re.search(r"\d+(?:\.\d+)?秒|立即|无延迟|none", response_latency, re.I):
                issues.append(f"{prefix}.response_latency必须写秒数或明确无延迟")
            if len(conversation_source_basis) < 4:
                issues.append(f"{prefix}.conversation_source_basis必须写源文依据")
            if conversation_mode != "clean_turn" and overlap_window in ("", "none", "N/A"):
                issues.append(f"{prefix}非顺序轮次必须写overlap_or_interrupt_window")

        match = re.fullmatch(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)秒", str(event.get("time_range", "") or "").strip())
        if not match:
            issues.append(f"{prefix}.time_range必须是连续小数秒范围")
        else:
            start, end = float(match.group(1)), float(match.group(2))
            if start >= end or start < 0 or (total_duration > 0 and end > total_duration + 0.08):
                issues.append(f"{prefix}.time_range超出镜头或起止倒置")

        if visibility == "visible":
            if visible and speaker not in visible:
                issues.append(f"{prefix}.speaker标为visible但不在可见人物中")
            if facial and facial not in timeline:
                issues.append(f"{prefix}.facial_state未落实到子镜头组")
            if body and body not in timeline:
                issues.append(f"{prefix}.body_state未落实到子镜头组")
        elif visibility in ("offscreen", "nonphysical"):
            if not facial.startswith("N/A") or not body.startswith("N/A"):
                issues.append(f"{prefix}不可见说话者的facial_state/body_state必须明确写N/A及原因")
        if subtext_evidence and not subtext_evidence.startswith("N/A") and not _fragment_grounded(subtext_evidence, timeline):
            issues.append(f"{prefix}.subtext_visible_evidence未落实到子镜头组")
        if subtext_evidence.startswith("N/A") and visible:
            issues.append(f"{prefix}存在可见承接人物时subtext_visible_evidence不得写N/A")

        expected_lip_sync = kind == "台词" and visibility == "visible"
        if lip_sync is not expected_lip_sync:
            issues.append(f"{prefix}.lip_sync与台词类型或说话者可见性不一致")

        if audio_enabled is True:
            if line and full_prompt.count(line) != 1:
                issues.append(f"{prefix}.text必须逐字且只出现一次")
            label = f"{speaker}（{kind}）"
            if label not in timeline:
                issues.append(f"{prefix}必须在子镜头组明确人物与台词/OS类型")
            quoted_label = f"{speaker}（{kind}）: \"{line}\""
            if line and quoted_label not in timeline:
                issues.append(f"{prefix}必须按半角格式写成 {speaker}（{kind}）: \"逐字原文\"")
            if delivery and delivery not in timeline:
                issues.append(f"{prefix}.delivery未落实到子镜头组")
            if breath_pause_plan and breath_pause_plan not in timeline:
                issues.append(f"{prefix}.breath_pause_plan未落实到子镜头组")
            if expected_lip_sync and "口型" not in timeline:
                issues.append(f"{prefix}可见对白缺少口型同步说明")
            if kind in ("OS", "OV") and not any(token in timeline for token in ("口型闭合", "无口型同步", "不驱动口型")):
                issues.append(f"{prefix}的OS/OV缺少无口型同步说明")
        elif audio_enabled is False and line and line in full_prompt:
            issues.append(f"{prefix}.text在原生音频关闭时不得进入full_prompt")
        if expected_lip_sync and timeline and not any(token in timeline for token in ("句末闭口", "口型闭合", "收口")):
            issues.append(f"{prefix}可见对白缺少句末闭口/口型闭合落幅")
    _timing_records, timing_issues = analyze_dialogue_timing(events, duration)
    issues.extend(timing_issues)
    return issues


def _signature_text(value):
    return re.sub(r"[\s，,。！？；;：:‘’'\"“”]", "", str(value or "")).lower()


def attention_handoff_issues(metadata, full_prompt):
    """Validate an optional, single causal attention handoff."""
    metadata = metadata if isinstance(metadata, dict) else {}
    handoff = metadata.get("attention_handoff")
    if handoff is None:
        return []
    if not isinstance(handoff, dict):
        return ["qa_metadata.attention_handoff必须是对象"]

    issues = []
    if handoff.get("mode") != "causal_handoff":
        issues.append("attention_handoff.mode必须是causal_handoff")
    if handoff.get("count") != 1:
        issues.append("attention_handoff.count必须精确为1")
    strategy = handoff.get("strategy")
    if strategy not in ATTENTION_HANDOFF_STRATEGIES:
        issues.append("attention_handoff.strategy只允许rack_focus/single_reframe/actor_blocking")
    for field in ("from", "to", "trigger", "end_composition"):
        if not str(handoff.get(field, "") or "").strip():
            issues.append(f"attention_handoff.{field}不能为空")
    if str(handoff.get("from", "")).strip() == str(handoff.get("to", "")).strip():
        issues.append("attention_handoff.from与to不能相同")

    roles = metadata.get("performance_priority", {})
    if isinstance(roles, dict):
        assigned = set(
            ([str(roles.get("primary", "")).strip()] if str(roles.get("primary", "")).strip() else [])
            + _string_list(roles.get("supporting", []))
            + _string_list(roles.get("background", []))
        )
        for field in ("from", "to"):
            value = str(handoff.get(field, "") or "").strip()
            if value and value not in assigned:
                issues.append(f"attention_handoff.{field}不在表演优先级角色中")

    design = split_sections(full_prompt, PROMPT_LABELS).get("主镜头连续规则", "")
    moves = camera_move_types(design)
    has_focus_transfer = bool(FOCUS_TRANSFER_RE.search(design))
    if strategy == "rack_focus":
        if moves:
            issues.append("rack_focus策略要求摄影机固定，不能叠加物理运镜或变焦")
        if not has_focus_transfer:
            issues.append("rack_focus策略必须在主镜头连续规则中写一次可执行拉焦")
    elif strategy == "single_reframe":
        if len(moves) != 1 or not (moves & {"pan", "slide", "track", "orbit"}):
            issues.append("single_reframe策略必须且只能使用一次摇/移/跟随/弧移重构图")
        if has_focus_transfer or "zoom" in moves:
            issues.append("single_reframe策略不能叠加拉焦或变焦")
    elif strategy == "actor_blocking":
        if moves or has_focus_transfer:
            issues.append("actor_blocking策略要求机位与焦点稳定，只由演员走位改变画面权重")

    return issues


def camera_competition_issues(full_prompt, editorial_mode="continuous_take"):
    """Reject competing controls in a take, while preserving motivated editorial beats."""
    sections = split_sections(full_prompt, PROMPT_LABELS)
    design = sections.get("主镜头连续规则", "")
    timeline = sections.get("子镜头组", "")
    issues = []
    moves = camera_move_types(design)
    if editorial_mode != "shot_group" and len(moves) > 1:
        issues.append("主镜头连续规则叠加多种主要运镜：" + "/".join(sorted(moves)))
    has_focus_transfer = bool(FOCUS_TRANSFER_RE.search(design))
    if editorial_mode != "shot_group" and has_focus_transfer and moves:
        issues.append("物理运镜/变焦与拉焦同时叠加，形成竞争控制")
    if re.search(r"(?:再|再次|重新).{0,12}(?:拉焦|焦点.{0,6}(?:转|移|回))|[^。；]{0,12}→[^。；]{0,12}→", design + timeline):
        issues.append("同一镜头发生反复注意力抢焦")
    if ("聚焦" in design or "聚焦" in timeline) and not re.search(
        r"三分位|画面(?:左|右|中央|中心)|占画面|前景|中景|后景|拉焦|焦点(?:从|由)|平摇|横摇|横移|侧移|弧移|走位|落幅",
        design + timeline,
    ):
        issues.append("只写聚焦主体但缺少可执行构图、焦点、走位或落幅")
    return issues


COVERAGE_ROLES = {
    "establish_space", "relationship_blocking", "dialogue_performance",
    "reaction", "prop_information", "movement_transition", "power_reversal",
    "environment_bridge",
}


def coverage_role_issues(metadata, full_prompt):
    """Keep the stability fallback from replacing a shot's narrative job."""
    metadata = metadata if isinstance(metadata, dict) else {}
    design = metadata.get("dramatic_design", {})
    design = design if isinstance(design, dict) else {}
    role = str(design.get("coverage_role", "") or "").strip()
    if role not in COVERAGE_ROLES:
        return ["dramatic_design.coverage_role缺失或无效"]
    text = str(full_prompt or "")
    mid_or_medium = "中近景" in text or "中景" in text
    fixed = any(token in text for token in ("固定机位", "机位固定", "固定镜头", "运镜固定"))
    if mid_or_medium and fixed and role not in {"dialogue_performance", "reaction"}:
        return ["coverage_role=%s不能默认使用中景/中近景固定机位" % role]
    return []


def camera_move_types(design):
    design = str(design or "")
    moves = {name for name, pattern in CAMERA_MOVE_PATTERNS.items() if re.search(pattern, design)}
    # “横移跟拍” describes one lateral tracking trajectory, not two competing
    # camera moves. Preserve track as the canonical category.
    if moves.issuperset({"slide", "track"}) and re.search(r"(?:横移|侧移|轨道移|滑轨).{0,6}跟拍", design):
        moves.discard("slide")
    return moves


def fight_continuity_issues(metadata, duration):
    """Validate one continuous-take fight chain and its structured handoff."""
    metadata = metadata if isinstance(metadata, dict) else {}
    continuity = metadata.get("fight_continuity")
    if not isinstance(continuity, dict):
        return ["打斗镜必须提供qa_metadata.fight_continuity"]
    issues = []
    if continuity.get("mode") != "continuous_take":
        issues.append("fight_continuity.mode必须是continuous_take")
    for field in ("sequence_id", "clip_id"):
        if not str(continuity.get(field, "") or "").strip():
            issues.append(f"fight_continuity.{field}不能为空")
    participants = continuity.get("participants")
    if not isinstance(participants, list) or len([p for p in participants if str(p).strip()]) < 2:
        issues.append("fight_continuity.participants必须至少包含两名角色")
    beats = continuity.get("contact_beats")
    if not isinstance(beats, list) or not beats:
        issues.append("fight_continuity.contact_beats必须是非空数组")
        beats = []
    try:
        seconds = float(duration or 0)
    except (TypeError, ValueError):
        seconds = 0
    max_beats = 1 if seconds <= 6 else 2 if seconds <= 10 else 3
    if seconds > 15:
        issues.append("连续打斗生成片段超过15秒；必须拆成可续接片段")
    if len(beats) > max_beats:
        issues.append(f"fight_continuity.contact_beats={len(beats)}超过当前时长上限{max_beats}")
    for index, beat in enumerate(beats):
        if not isinstance(beat, dict):
            issues.append(f"fight_continuity.contact_beats[{index}]必须是对象")
            continue
        for field in (
            "time_range", "attacker", "defender", "attack_path",
            "contact_point", "force_direction", "result",
        ):
            if not str(beat.get(field, "") or "").strip():
                issues.append(f"fight_continuity.contact_beats[{index}].{field}不能为空")
    for lock_name in ("start_lock", "end_lock"):
        lock = continuity.get(lock_name)
        if not isinstance(lock, dict):
            issues.append(f"fight_continuity.{lock_name}必须是对象")
            continue
        for field in FIGHT_LOCK_FIELDS:
            if not str(lock.get(field, "") or "").strip():
                issues.append(f"fight_continuity.{lock_name}.{field}不能为空")
    return issues


def fight_transition_issues(previous_metadata, current_metadata):
    """Require exact end-lock/start-lock inheritance within one fight sequence."""
    previous = previous_metadata.get("fight_continuity", {}) if isinstance(previous_metadata, dict) else {}
    current = current_metadata.get("fight_continuity", {}) if isinstance(current_metadata, dict) else {}
    if not isinstance(previous, dict) or not isinstance(current, dict):
        return []
    previous_sequence = str(previous.get("sequence_id", "") or "")
    current_sequence = str(current.get("sequence_id", "") or "")
    if not previous_sequence or previous_sequence != current_sequence:
        return []
    end_lock = previous.get("end_lock")
    start_lock = current.get("start_lock")
    if isinstance(end_lock, dict) and isinstance(start_lock, dict) and end_lock != start_lock:
        return ["同一打斗序列中，上镜end_lock必须与本镜start_lock完全相同"]
    return []


def role_partition_issues(metadata, visible_characters):
    metadata = metadata if isinstance(metadata, dict) else {}
    roles = metadata.get("performance_priority", {})
    if not isinstance(roles, dict):
        return ["qa_metadata.performance_priority必须是对象"]
    primary = str(roles.get("primary", "") or "").strip()
    supporting = _string_list(roles.get("supporting", []))
    background = _string_list(roles.get("background", []))
    assigned = ([primary] if primary else []) + supporting + background
    issues = []
    if len(assigned) != len(set(assigned)):
        issues.append("角色不能同时属于多个表演优先级")
    visible = [str(char).strip() for char in visible_characters if str(char).strip()]
    if visible and not primary:
        issues.append("有人物镜头必须指定一个primary角色")
    if set(assigned) != set(visible):
        missing = sorted(set(visible) - set(assigned))
        extra = sorted(set(assigned) - set(visible))
        if missing:
            issues.append("未分配表演优先级：" + "、".join(missing))
        if extra:
            issues.append("优先级包含不可见角色：" + "、".join(extra))
    return issues


def visible_people_gate_issues(metadata, full_prompt="", visible_characters=None):
    """Validate the visible-person gate for multi-person/offscreen-risk shots.

    The gate is intentionally risk-triggered rather than universal: ordinary
    stable one-person shots do not need extra boilerplate, while multi-person,
    shoulder-line/blurred-person, or offscreen-voice shots must declare what is
    actually visible so T2V does not hallucinate extra people.
    """
    metadata = metadata if isinstance(metadata, dict) else {}
    visible = _string_list(visible_characters or [])
    full_prompt = str(full_prompt or "")
    events = metadata.get("dialogue_events", []) if isinstance(metadata.get("dialogue_events"), list) else []
    offscreen_speakers = [
        str(event.get("speaker", "") or "").strip()
        for event in events if isinstance(event, dict)
        and str(event.get("speaker_visibility", "") or "").strip() in {"offscreen", "nonphysical"}
    ]
    text_requests_gate = bool(re.search(r"画外|不入画|肩线|背影|倒影|虚化", full_prompt))
    required = len(visible) >= 2 or bool(offscreen_speakers) or text_requests_gate
    if not required:
        return []

    issues = []
    basemap = metadata.get("source_constraint_basemap", {})
    gate = basemap.get("visible_people_gate") if isinstance(basemap, dict) else None
    if gate in (None, "", {}):
        issues.append("多人/画外声/肩线虚化镜必须在source_constraint_basemap.visible_people_gate写本镜可见人数闸门")
    elif isinstance(gate, dict):
        visible_count = gate.get("visible_count")
        if isinstance(visible_count, int) and visible_count != len(visible):
            issues.append("visible_people_gate.visible_count必须等于本镜visible_characters数量")
        gate_text = " ".join(str(value) for value in gate.values())
        if not VISIBLE_LAYER_RE.search(gate_text):
            issues.append("visible_people_gate必须区分清晰、肩线/背影/倒影/虚化或画外")
    elif isinstance(gate, str):
        if not VISIBLE_LAYER_RE.search(gate):
            issues.append("visible_people_gate必须区分清晰、肩线/背影/倒影/虚化或画外")
    else:
        issues.append("visible_people_gate必须是扁平字符串或对象")

    prompt_gate_text = split_sections(full_prompt, PROMPT_LABELS).get("主体与空间锁定", "") + "\n" + full_prompt
    if not VISIBLE_GATE_RE.search(prompt_gate_text):
        issues.append("full_prompt必须写清本镜画面内实际可见人物/画外声音，不能只依赖角色列表")
    for speaker in offscreen_speakers:
        if not speaker:
            continue
        target_re = re.compile(
            r"(?:看向|望向|面向|朝向|对着|盯着|凝视|压向).{0,12}" + re.escape(speaker)
            + r"|" + re.escape(speaker) + r".{0,12}(?:看向|望向|面向|朝向|对着|盯着|凝视|压向)"
        )
        target_match = target_re.search(full_prompt)
        target_phrase = target_match.group(0) if target_match else ""
        if target_match and not (OFFSCREEN_SOURCE_RE.search(target_phrase) or re.search(r"声源|空间锚点|固定锚点|门口方向", target_phrase)):
            issues.append(f"画外/非实体人物{speaker}不得作为看向/面向/对着的视觉目标；改写为画外声源或固定空间锚点")
    return issues


def visibility_issues(full_prompt, shot_size):
    sections = split_sections(full_prompt, PROMPT_LABELS)
    performance = sections.get("子镜头组", "")
    if shot_size in ("全景", "大远景", "远景"):
        cues = WIDE_INVISIBLE_CUES
    elif shot_size == "中景":
        cues = MEDIUM_INVISIBLE_CUES
    else:
        cues = []
    hits = [cue for cue in cues if cue in performance]
    return (["景别不可见细节：" + "、".join(hits)] if hits else [])


def visual_texture_issues(full_prompt):
    """Reject decorative quality words unless they are grounded as visible light/material facts."""
    text = str(full_prompt or "")
    if not any(term in text for term in ABSTRACT_VISUAL_TERMS):
        return []
    sections = split_sections(text, PROMPT_LABELS)
    visible_text = "\n".join(
        sections.get(label, "") for label in ("主体与空间锁定", "子镜头组", "光照、声音与稳定约束")
    ) or text
    has_light_source = bool(LIGHT_SOURCE_RE.search(visible_text))
    has_texture_anchor = bool(VISIBLE_TEXTURE_ANCHOR_RE.search(visible_text))
    if has_light_source and has_texture_anchor:
        return []
    missing = []
    if not has_light_source:
        missing.append("光源方向/色温/受光关系")
    if not has_texture_anchor:
        missing.append("脸/手/道具受光、阴影/反光、背景虚化或剧情相关材质")
    return ["抽象画面质感词必须落成可见执行锚点：" + "、".join(missing)]


def cinematic_realism_prompt_issues(prompt, require_live_action_style=False):
    """Validate film-realism cues beyond generic light/material anchors.

    This is a prompt-level guard for the user's "AI感" complaint.  A prompt can
    be visually stylish yet still look synthetic when it asks for perfect
    reflections, clean procedural surfaces, uniform particles, or unbounded
    neon.  The guard is intentionally concrete: it looks for physically
    inspectable image evidence rather than words like "cinematic".
    """
    text = str(prompt or "").strip()
    if not text:
        return ["写实影像提示词不能为空"]
    issues = []
    evidence = (
        ("构图锚点", CINEMATIC_COMPOSITION_RE),
        ("镜头景深/焦平面", CINEMATIC_DEPTH_RE),
        ("曝光反差/黑位控制", CINEMATIC_EXPOSURE_RE),
        ("色彩分离", CINEMATIC_COLOR_RE),
        ("空气层/环境颗粒", CINEMATIC_ATMOSPHERE_RE),
        ("真实材质细节", CINEMATIC_MATERIAL_RE),
        ("非完美瑕疵/随机性", CINEMATIC_IMPERFECTION_RE),
    )
    for label, pattern in evidence:
        if not pattern.search(text):
            issues.append(f"缺少{label}的可见证据")
    risk_hits = AI_REALISM_RISK_RE.findall(text)
    if risk_hits:
        issues.append("提示词含容易放大AI感/CG感的正向描述：" + "、".join(sorted(set(risk_hits))[:6]))
    if require_live_action_style and not REALISM_POSITIVE_STYLE_RE.search(text):
        issues.append("写实目标应在开头声明写实/实拍/电影剧照/实拍短片，而不是只写风格化电影感")
    if require_live_action_style and CG_STYLE_DRIFT_RE.search(text) and not REALISM_POSITIVE_STYLE_RE.search(text[:80]):
        issues.append("写实目标不应以动态漫/漫画/二次元/赛博等风格词开头；会把模型推向插画或CG质感")
    return issues


def cinematic_image_contract_issues(metadata, full_prompt=""):
    """Validate optional cinematic_image_contract metadata and prompt grounding."""
    metadata = metadata if isinstance(metadata, dict) else {}
    contract = metadata.get("cinematic_image_contract")
    if contract in (None, {}, ""):
        return []
    if not isinstance(contract, dict):
        return ["qa_metadata.cinematic_image_contract必须是对象"]
    issues = []
    for field in CINEMATIC_IMAGE_CONTRACT_FIELDS:
        value = contract.get(field)
        if not isinstance(value, str) or len(value.strip()) < 3:
            issues.append(f"cinematic_image_contract.{field}必须是非空扁平字符串")
        elif len(value) > 180:
            issues.append(f"cinematic_image_contract.{field}过长，应压缩为单句可见证据")
    for field, value in contract.items():
        if isinstance(value, (dict, list)):
            issues.append(f"cinematic_image_contract.{field}必须保持扁平，不能嵌套对象或数组")
    prompt_text = str(full_prompt or "")
    combined = "；".join(
        str(contract.get(field, "") or "")
        for field in CINEMATIC_IMAGE_CONTRACT_FIELDS
        if field != "realism_risk"
    ) + "\n" + prompt_text
    issues.extend(cinematic_realism_prompt_issues(combined, require_live_action_style=False))
    if prompt_text:
        grounding = (
            ("composition_anchor", CINEMATIC_COMPOSITION_RE, "full_prompt缺少构图锚点落地"),
            ("lens_depth", CINEMATIC_DEPTH_RE, "full_prompt缺少景深/焦平面落地"),
            ("exposure_contrast", CINEMATIC_EXPOSURE_RE, "full_prompt缺少曝光/反差落地"),
            ("color_separation", CINEMATIC_COLOR_RE, "full_prompt缺少色彩分离落地"),
            ("atmosphere_layer", CINEMATIC_ATMOSPHERE_RE, "full_prompt缺少空气层/环境颗粒落地"),
            ("material_detail", CINEMATIC_MATERIAL_RE, "full_prompt缺少真实材质落地"),
            ("imperfection_map", CINEMATIC_IMPERFECTION_RE, "full_prompt缺少非完美瑕疵/随机性落地"),
        )
        for _field, pattern, message in grounding:
            if not pattern.search(prompt_text):
                issues.append(message)
    return issues


def video_texture_contract_issues(metadata, full_prompt=""):
    """Validate a moving-image texture contract when supplied.

    ``cinematic_image_contract`` protects a strong frame. This contract protects
    exposure, material response, atmosphere motion, camera restraint, and
    cross-shot carryover across a moving shot or sequence.
    """
    metadata = metadata if isinstance(metadata, dict) else {}
    contract = metadata.get("video_texture_contract")
    if contract in (None, {}, ""):
        return []
    if not isinstance(contract, dict):
        return ["qa_metadata.video_texture_contract必须是对象"]
    issues = []
    for field in VIDEO_TEXTURE_CONTRACT_FIELDS:
        value = contract.get(field)
        if not isinstance(value, str) or len(value.strip()) < 3:
            issues.append(f"video_texture_contract.{field}必须是非空扁平字符串")
        elif len(value) > 180:
            issues.append(f"video_texture_contract.{field}过长，应压缩为单句视频质感规则")
    for field, value in contract.items():
        if isinstance(value, (dict, list)):
            issues.append(f"video_texture_contract.{field}必须保持扁平，不能嵌套对象或数组")

    combined = "；".join(
        str(contract.get(field, "") or "")
        for field in VIDEO_TEXTURE_CONTRACT_FIELDS
        if field != "risk_controls"
    )
    checks = (
        (VIDEO_TEXTURE_LOOK_RE, "缺少全片影像质感/渲染基调"),
        (VIDEO_TEXTURE_EXPOSURE_RE, "缺少视频曝光/黑位/高光持续规则"),
        (VIDEO_TEXTURE_MATERIAL_MOTION_RE, "缺少材质在运动中的可见响应规则"),
        (VIDEO_TEXTURE_ATMOSPHERE_MOTION_RE, "缺少雨雾尘/空气层随时间运动规则"),
        (VIDEO_TEXTURE_CAMERA_STABILITY_RE, "缺少镜头稳定或运动预算规则"),
        (VIDEO_TEXTURE_CONTINUITY_RE, "缺少跨镜质感继承/不跳变规则"),
    )
    for pattern, message in checks:
        if not pattern.search(combined):
            issues.append(message)

    prompt_text = str(full_prompt or "")
    if prompt_text:
        if not VIDEO_TEXTURE_EXPOSURE_RE.search(prompt_text):
            issues.append("full_prompt缺少视频曝光/黑位/高光规则落地")
        if not VIDEO_TEXTURE_MATERIAL_MOTION_RE.search(prompt_text):
            issues.append("full_prompt缺少材质运动/反光响应落地")
        if not VIDEO_TEXTURE_CAMERA_STABILITY_RE.search(prompt_text):
            issues.append("full_prompt缺少镜头稳定或运动预算落地")
        risk_hits = AI_REALISM_RISK_RE.findall(prompt_text)
        if risk_hits:
            issues.append("full_prompt含容易放大AI感/CG感的正向描述：" + "、".join(sorted(set(risk_hits))[:6]))
    return issues


def aesthetic_directing_contract_issues(metadata, full_prompt=""):
    """Validate the new aesthetic handoff without breaking legacy packages.

    Legacy packages that contain none of the aesthetic fields remain valid. New
    Composer scaffolds contain all four fields, so blank or partial completion is
    rejected before merge.
    """
    metadata = metadata if isinstance(metadata, dict) else {}
    specs = (
        ("visual_bible", VISUAL_BIBLE_FIELDS),
        ("static_aesthetic_contract", STATIC_AESTHETIC_CONTRACT_FIELDS),
        ("dynamic_aesthetic_contract", DYNAMIC_AESTHETIC_CONTRACT_FIELDS),
        ("aesthetic_priority", AESTHETIC_PRIORITY_FIELDS),
    )
    if not any(label in metadata for label, _fields in specs):
        return []
    issues = []
    for label, fields in specs:
        contract = metadata.get(label)
        if not isinstance(contract, dict):
            issues.append(f"qa_metadata.{label}必须是对象")
            continue
        issues.extend(_flat_directing_contract_issues(contract, fields, label))

    priority = metadata.get("aesthetic_priority", {})
    if isinstance(priority, dict):
        thesis = str(priority.get("visual_thesis", "") or "").strip()
        target = str(priority.get("primary_eye_target", "") or "").strip()
        if thesis in ABSTRACT_VISUAL_TERMS or target in ABSTRACT_VISUAL_TERMS:
            issues.append("aesthetic_priority必须写具体视觉论点和第一落点，不能只写电影感/高级感")

    bible = metadata.get("visual_bible", {})
    if isinstance(bible, dict):
        palette = str(bible.get("palette_system", "") or "")
        if not (
            len(re.findall(r"主色|辅助色|点缀色|冷|暖|中性|低饱和|高饱和", palette)) >= 2
            and re.search(r"背景|人物|服装|道具|空间|落在|用于", palette)
        ):
            issues.append("visual_bible.palette_system必须说明至少两层色彩职责与画面落点")
        light = str(bible.get("light_motivation", "") or "")
        if not (LIGHT_SOURCE_RE.search(light) and LIGHT_DIRECTION_RE.search(light) and LIGHT_RECEIVER_RE.search(light)):
            issues.append("visual_bible.light_motivation必须包含光源、方向和受光面")
        material = str(bible.get("material_world", "") or "")
        if _material_family_count(material) < 2 or not MATERIAL_RESPONSE_RE.search(material):
            issues.append("visual_bible.material_world必须区分至少两类材质及其反光/粗糙/纹理响应")
        imperfection = str(bible.get("imperfection_policy", "") or "")
        if not CINEMATIC_IMPERFECTION_RE.search(imperfection):
            issues.append("visual_bible.imperfection_policy必须选择一项自然不完美证据")

    dynamic = metadata.get("dynamic_aesthetic_contract", {})
    if isinstance(dynamic, dict):
        camera_path = str(dynamic.get("camera_path", "") or "")
        if camera_path and not re.search(r"固定|机位|推|拉|横移|侧移|摇|俯仰|跟|轨迹|路径|镜头", camera_path):
            issues.append("dynamic_aesthetic_contract.camera_path必须写明确摄影机路径或固定机位")
        fallback = str(dynamic.get("stability_fallback", "") or "")
        if fallback and not re.search(r"固定|取消|删|降低|低幅|保持|拆镜|稳定", fallback):
            issues.append("dynamic_aesthetic_contract.stability_fallback必须给出可执行稳定降级")

    prompt_text = str(full_prompt or "")
    static = metadata.get("static_aesthetic_contract", {})
    if prompt_text and isinstance(static, dict):
        visible_fields = ("composition_hierarchy", "light_design", "material_anchor", "signature_frame")
        grounded = sum(
            _fragment_grounded(str(static.get(field, "") or ""), prompt_text)
            for field in visible_fields
        )
        if grounded < 1:
            issues.append("static_aesthetic_contract至少一项构图/光影/材质/记忆帧必须落实到full_prompt")
        light_design = str(static.get("light_design", "") or "")
        if not (
            LIGHT_SOURCE_RE.search(light_design)
            and LIGHT_DIRECTION_RE.search(light_design)
            and LIGHT_RECEIVER_RE.search(light_design)
            and SHADOW_RESULT_RE.search(light_design)
        ):
            issues.append("static_aesthetic_contract.light_design必须包含光源、方向、受光面和阴影结果")
        color_grade = str(static.get("color_grade", "") or "")
        if not CINEMATIC_COLOR_RE.search(color_grade) or not re.search(r"肤色|皮肤|脸|面部|高光|黑位", color_grade):
            issues.append("static_aesthetic_contract.color_grade必须写色彩分离及肤色/高光/黑位保护")
        material_anchor = str(static.get("material_anchor", "") or "")
        if _material_family_count(material_anchor) < 1 or not MATERIAL_RESPONSE_RE.search(material_anchor):
            issues.append("static_aesthetic_contract.material_anchor必须写剧情材质及其可见响应")
    if prompt_text and isinstance(dynamic, dict):
        dynamic_text = " ".join(str(dynamic.get(field, "") or "") for field in DYNAMIC_AESTHETIC_CONTRACT_FIELDS)
        hold_source = str(dynamic.get("primary_subject_motion", "") or "")
        deliberate_hold = bool(re.search(r"固定|保持静止|无额外|不增加|不动|无运动", hold_source)) and not bool(
            re.search(r"抬|转|移|走|跑|伸|握|抓|放|接|压|起身|坐|躺|重心|摆动|流动", str(dynamic.get("primary_subject_motion", "") or ""))
        )
        grounded_dynamic = sum(
            _motion_fragment_grounded(str(dynamic.get(field, "") or ""), prompt_text)
            for field in ("trigger", "primary_subject_motion", "end_state")
        )
        if grounded_dynamic < (2 if deliberate_hold else 3):
            issues.append(
                "dynamic_aesthetic_contract的触发、主体动作与稳定终态至少%s项必须落实到full_prompt"
                % ("两" if deliberate_hold else "三")
            )
        responses = [
            str(dynamic.get(field, "") or "")
            for field in ("secondary_environment_motion", "material_motion", "atmosphere_motion")
        ]
        response_grounded = any(_fragment_grounded(value, prompt_text) for value in responses)
        response_hold = any(re.search(r"固定|保持|静止|无额外|不增加", value) for value in responses)
        if not response_grounded and not response_hold:
            issues.append("dynamic_aesthetic_contract至少一个因果环境/材质/空气响应必须落实到full_prompt，或明确保持静止")
        if not deliberate_hold:
            primary_motion = str(dynamic.get("primary_subject_motion", "") or "")
            if not MOTION_ACTION_RE.search(primary_motion):
                issues.append("dynamic_aesthetic_contract.primary_subject_motion必须写可执行身体/视线/重心动作")
            if not MOTION_PHASE_RE.search(prompt_text + " " + dynamic_text):
                issues.append("dynamic_aesthetic_contract必须写先后、延迟、余波、减速或稳定落幅等时间节拍")
    return issues


def _motion_fragment_grounded(value, text):
    """Allow a subject to be stated once before a coordinated action phrase."""
    if _fragment_grounded(value, text):
        return True
    fragments = [
        fragment.strip()
        for fragment in re.split(r"[，,、；;]|(?:并且|然后|随后|再|并)", str(value or ""))
        if len(fragment.strip()) >= 4
    ]
    return any(fragment in str(text or "") for fragment in fragments)


def _material_family_count(text):
    value = str(text or "")
    return sum(bool(pattern.search(value)) for pattern in MATERIAL_FAMILY_PATTERNS)


def physical_transition_chain_issues(metadata, full_prompt=""):
    """Require start-contact-move-release/stable chains for state-changing shots."""
    metadata = metadata if isinstance(metadata, dict) else {}
    contract = metadata.get("continuity_contract", {})
    if not isinstance(contract, dict) or not contract.get("state_change"):
        return []
    text = str(full_prompt or "")
    transitions = contract.get("state_transitions", [])
    if not isinstance(transitions, list) or not transitions:
        return ["state_change=true时必须提供state_transitions，并在full_prompt写出中间过渡帧"]
    issues = []
    for index, transition in enumerate(transitions):
        if not isinstance(transition, dict):
            issues.append(f"state_transitions[{index}]必须是对象")
            continue
        subject = str(transition.get("subject", "") or "状态变化")
        intermediate = str(transition.get("intermediate_state", "") or "").strip()
        if not intermediate:
            issues.append(f"state_transitions[{index}].intermediate_state不能为空")
            continue
        if not _fragment_grounded(intermediate, text):
            issues.append(f"state_transitions[{index}].intermediate_state必须落实到full_prompt")
        relevant_text = " ".join([
            subject,
            str(transition.get("from_state", "") or ""),
            intermediate,
            str(transition.get("to_state", "") or ""),
            text,
        ])
        if _needs_physical_chain(relevant_text):
            groups_hit = sum(1 for pattern in PHYSICAL_CHAIN_GROUPS if pattern.search(text))
            if groups_hit < 2:
                issues.append(f"{subject}发生归属/身体/空间变化时，full_prompt必须写出接近/接触/释放或稳定终态中的至少两段")
    if re.search(r"(?:突然|直接|瞬间|已经).{0,12}(?:到手|拿到|出现在|换到|转到|站到|面对)", text):
        issues.append("状态变化不能用突然/直接/瞬间跳到结果，必须写中间过渡链")
    return issues


def screen_text_policy_issues(full_prompt):
    """Require Jimeng-friendly handling when the prompt asks the model to render UI text overlays."""
    text = str(full_prompt or "")
    if not AI_SCREEN_TEXT_RE.search(text):
        return []
    safe_hits = set(AI_SCREEN_TEXT_SAFE_RE.findall(text))
    if len(safe_hits) >= 2:
        return []
    return ["AI生成聊天/通知/UI文字时必须声明独立二维浮层、安全区、不贴手机背面或不跟随手机透视中的至少两项；否则改为后期叠字"]


def source_constraint_basemap_issues(metadata):
    """Validate the pre-generation source basemap absorbed from Jimeng workflow.

    Missing is tolerated for older completed fixtures. Once present, it must be
    compact, structured, and agree with the shot-level tension role.
    """
    metadata = metadata if isinstance(metadata, dict) else {}
    basemap = metadata.get("source_constraint_basemap")
    if basemap in (None, {}, ""):
        return []
    if not isinstance(basemap, dict):
        return ["qa_metadata.source_constraint_basemap必须是对象"]
    issues = []
    required = (
        "space_basis",
        "state_prop_basis",
        "character_orientation_basis",
        "tension_curve_role",
        "sound_lip_sync_basis",
        "screen_text_policy",
        "single_shot_risk",
    )
    for field in required:
        value = basemap.get(field)
        if not isinstance(value, str) or len(value.strip()) < 2:
            issues.append(f"source_constraint_basemap.{field}必须是非空扁平字符串")
    shallow_object_fields = {"visible_people_gate"}
    known_optional_fields = {
        "visible_people_gate",
        "performance_baseline_lock",
        "emotion_micro_chain",
        "dialogue_performance_kernel",
        "emotion_residue_contract",
        "physical_structure_chain",
        "shot_component_choice",
        "viewpoint_motion_lock",
        "premium_director_polish",
        "creative_profile",
    }
    for field, value in basemap.items():
        if field in shallow_object_fields and isinstance(value, dict):
            if any(isinstance(nested, (dict, list)) for nested in value.values()):
                issues.append(f"source_constraint_basemap.{field}必须是浅层对象，不能嵌套对象或数组")
            continue
        if isinstance(value, (dict, list)):
            issues.append(f"source_constraint_basemap.{field}必须保持扁平，不能嵌套对象或数组")
        if field in known_optional_fields and isinstance(value, str) and len(value.strip()) > 180:
            issues.append(f"source_constraint_basemap.{field}应压缩为单句执行底图")
    role = str(basemap.get("tension_curve_role", "") or "").strip()
    if role and role not in TENSION_CURVE_ROLES:
        issues.append("source_constraint_basemap.tension_curve_role只允许铺垫/升压/峰值/释放/缓冲")
    shot_role = str(metadata.get("tension_curve_role", "") or "").strip()
    if role and shot_role and _canonical_tension_curve_role(role) != _canonical_tension_curve_role(shot_role):
        issues.append("source_constraint_basemap.tension_curve_role必须与qa_metadata.tension_curve_role一致")
    creative_profile = str(basemap.get("creative_profile", "") or "").strip()
    if creative_profile and creative_profile not in {"safe", "balanced", "expressive"}:
        issues.append("source_constraint_basemap.creative_profile只能为safe/balanced/expressive")
    return issues


def scene_tone_palette_issues(metadata, full_prompt=""):
    """Validate scene-level space, tone, and lived-in depth metadata."""
    metadata = metadata if isinstance(metadata, dict) else {}
    palette = metadata.get("scene_tone_palette")
    if palette in (None, {}, ""):
        return []
    if not isinstance(palette, dict):
        return ["qa_metadata.scene_tone_palette必须是对象"]
    issues = []
    for field in (
        "space_id",
        "space_master_sentence",
        "tone_palette",
        "light_texture_purpose",
        "visual_scene_prefix",
        "foreground_layer",
        "midground_layer",
        "background_layer",
        "genre_visual_signature",
        "lived_in_detail",
        "depth_focus_policy",
        "landscape_identity",
        "landscape_composition",
        "natural_motion_system",
        "environment_story_arc",
        "reveal_order",
        "light_weather_progression",
        "breathing_policy",
    ):
        value = palette.get(field)
        if not isinstance(value, str) or len(value.strip()) < 2:
            issues.append(f"scene_tone_palette.{field}必须是非空扁平字符串")
        elif isinstance(value, str) and len(value) > 240:
            issues.append(f"scene_tone_palette.{field}过长，应压缩为空间/影调锁定句")
    for field, value in palette.items():
        if isinstance(value, (dict, list)):
            issues.append(f"scene_tone_palette.{field}必须保持扁平，不能嵌套对象或数组")
    if full_prompt:
        grounded_layers = sum(
            1 for field in ("foreground_layer", "midground_layer", "background_layer")
            if _fragment_grounded(str(palette.get(field, "") or ""), full_prompt)
        )
        if grounded_layers < 2:
            issues.append("full_prompt必须落实前景/中景/后景中的至少两层具体场景细节")
        if not any(
            _fragment_grounded(str(palette.get(field, "") or ""), full_prompt)
            for field in ("genre_visual_signature", "lived_in_detail")
        ):
            issues.append("full_prompt必须落实题材视觉气味或生活化使用痕迹")
        if not _fragment_grounded(str(palette.get("depth_focus_policy", "") or ""), full_prompt):
            issues.append("full_prompt必须落实焦平面、遮挡、空气透视或虚实主次控制")
        scenic_fields = (
            "landscape_identity", "landscape_composition", "natural_motion_system",
            "reveal_order", "light_weather_progression",
        )
        scenic_grounded = sum(
            _fragment_grounded(str(palette.get(field, "") or ""), full_prompt)
            for field in scenic_fields
        )
        profile = str((metadata.get("quality_contract", {}) or {}).get("profile", "") or "")
        required_scenic = 2 if profile == "environment" else 1
        if scenic_grounded < required_scenic:
            issues.append(
                "环境镜至少落实两项、人物镜至少落实一项风景身份/构图/自然运动/揭示顺序/光候变化"
            )
    return issues


def screen_text_policy_metadata_issues(metadata, full_prompt=""):
    """Validate the structured UI/screen-text policy and its prompt behavior."""
    metadata = metadata if isinstance(metadata, dict) else {}
    policy = metadata.get("screen_text_policy")
    if policy in (None, {}, ""):
        return []
    if not isinstance(policy, dict):
        return ["qa_metadata.screen_text_policy必须是对象"]
    issues = []
    mode = str(policy.get("mode", "") or "").strip()
    if mode not in SCREEN_TEXT_POLICY_MODES:
        issues.append("screen_text_policy.mode只允许none/post/ai_overlay/ai_generated/ai_ui")
    refs = policy.get("text_refs", [])
    if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
        issues.append("screen_text_policy.text_refs必须是字符串数组")
    for field in ("render_rule", "safe_area", "perspective_rule"):
        value = policy.get(field, "")
        if not isinstance(value, str):
            issues.append(f"screen_text_policy.{field}必须是字符串")
    if mode == "none" and refs:
        issues.append("screen_text_policy.mode=none时text_refs必须为空")
    if mode == "post":
        render_rule = str(policy.get("render_rule", "") or "")
        if not any(token in render_rule for token in ("后期", "字幕表", "文字表", "post")):
            issues.append("screen_text_policy.mode=post时render_rule必须声明后期叠字/文字表")
    if mode in {"ai_overlay", "ai_generated", "ai_ui"}:
        for field in ("render_rule", "safe_area", "perspective_rule"):
            if len(str(policy.get(field, "") or "").strip()) < 2:
                issues.append(f"screen_text_policy.mode={mode}时{field}不能为空")
        issues.extend(screen_text_policy_issues(full_prompt))
    elif AI_SCREEN_TEXT_RE.search(str(full_prompt or "")):
        issues.append("full_prompt要求AI生成屏幕/UI文字，但screen_text_policy.mode未设为ai_overlay/ai_generated/ai_ui")
    return issues


FUNCTIONAL_SURFACE_VISIBILITY_MODES = {
    "hidden", "partial", "readable", "post_overlay", "not_applicable",
}


def prop_functional_surface_contract_issues(metadata, full_prompt="", required=False):
    """Keep an actively used prop face oriented to its user, not the audience."""
    metadata = metadata if isinstance(metadata, dict) else {}
    contract = metadata.get("prop_functional_surface_contract")
    if contract in (None, {}, ""):
        return ["人物使用手机/书页/照片/表盘等功能面道具时必须提供qa_metadata.prop_functional_surface_contract"] if required else []
    if not isinstance(contract, dict):
        return ["qa_metadata.prop_functional_surface_contract必须是对象"]
    if contract.get("applicable") is not True:
        return ["风险触发镜的prop_functional_surface_contract.applicable必须为true"] if required else []

    issues = []
    required_fields = (
        "prop", "functional_surface", "user", "user_view_relation", "camera_half_space",
        "camera_visible_surface", "grip_contact", "interaction_evidence", "orientation_lock",
        "fallback_shot",
    )
    for field in required_fields:
        if len(str(contract.get(field, "") or "").strip()) < 2:
            issues.append(f"prop_functional_surface_contract.{field}不能为空")
    visibility = str(contract.get("content_visibility", "") or "").strip()
    if visibility not in FUNCTIONAL_SURFACE_VISIBILITY_MODES:
        issues.append(
            "prop_functional_surface_contract.content_visibility只允许hidden/partial/readable/post_overlay/not_applicable"
        )
    elif required and visibility == "not_applicable":
        issues.append("风险触发镜的content_visibility不得为not_applicable")

    prompt = str(full_prompt or "")
    for field in (
        "user_view_relation", "camera_visible_surface", "grip_contact",
        "interaction_evidence", "orientation_lock",
    ):
        value = str(contract.get(field, "") or "").strip()
        if value and not _fragment_grounded(value, prompt):
            issues.append(f"prop_functional_surface_contract.{field}必须转译为full_prompt中的可见事实")

    if visibility in {"hidden", "post_overlay"}:
        conflict_patterns = (
            r"(?:手机|平板|电脑|显示器).{0,12}(?:屏幕|正面).{0,10}(?:朝向|正对|转向)(?:镜头|摄影机|观众)",
            r"(?:屏幕|游戏界面|屏幕内容).{0,8}(?:朝向|正对|转向)(?:镜头|摄影机|观众)",
            r"(?:镜头|摄影机|观众).{0,12}(?:清晰看见|清晰看到|清晰显示|可读).{0,8}(?:屏幕|游戏界面|屏幕内容)",
            r"(?:游戏界面|屏幕内容).{0,8}(?:清晰可见|完整可见|清晰可读)",
            r"(?:手机|平板).{0,8}背壳.{0,8}朝向(?:人物|用户|使用者|男孩|女孩|男人|女人)",
        )
        if any(re.search(pattern, prompt) for pattern in conflict_patterns):
            issues.append("隐藏功能面时不得把屏幕/正面翻向镜头或让内容对观众清晰可读")
        visible_surface = str(contract.get("camera_visible_surface", "") or "")
        if not any(term in visible_surface for term in ("背壳", "背面", "侧边", "书背", "封底", "表带", "边框")):
            issues.append("hidden/post_overlay必须写清摄影机实际可见的背壳、背面、侧边或边框")
    elif visibility in {"partial", "readable"}:
        geometry = " ".join((
            prompt,
            str(contract.get("camera_half_space", "") or ""),
            str(contract.get("fallback_shot", "") or ""),
        ))
        if not any(term in geometry for term in ("肩后", "过肩", "俯拍", "斜上方", "同一可见侧", "同侧")):
            issues.append("partial/readable必须使用肩后、过肩、俯拍、斜上方或使用者同侧机位展示功能面")
    return issues


SKIN_TONE_PROTECTION_MODES = {
    "natural_protected", "motivated_color_cast", "source_authorized_marks", "silhouette",
}

ACCIDENTAL_FACE_CONTAMINATION_PATTERNS = (
    r"青绿(?:色)?(?:渗入|覆盖|污染)(?:脸|脸部|面部|皮肤)",
    r"冷绿(?:色)?(?:渗入|覆盖|污染)(?:脸|脸部|面部|皮肤)",
    r"(?:墙面|旧墙|墙体)(?:旧痕|污渍|水渍|斑驳).{0,8}(?:覆盖|附着|映在)(?:脸|脸部|面部|皮肤)",
    r"(?:灰尘|尘粒|雾粒|颗粒).{0,8}(?:覆盖|附着|粘在)(?:脸|脸部|面部|皮肤)",
    r"(?:脸|脸部|面部|皮肤).{0,8}(?:粗糙斑驳|污浊|脏污)",
    r"(?:脸|脸部|面部).{0,8}(?:陷入|压成|变成)(?:死黑|一团黑)",
)


def skin_tone_protection_contract_issues(
    metadata, full_prompt="", visible_characters=None, required=False
):
    """Keep environmental color, texture, haze and beams from dirtying faces."""
    metadata = metadata if isinstance(metadata, dict) else {}
    contract = metadata.get("skin_tone_protection_contract")
    if contract in (None, {}, ""):
        return ["清晰人物镜必须提供qa_metadata.skin_tone_protection_contract"] if required else []
    if not isinstance(contract, dict):
        return ["qa_metadata.skin_tone_protection_contract必须是对象"]
    if contract.get("applicable") is not True:
        return ["人物镜的skin_tone_protection_contract.applicable必须为true"] if required else []

    issues = []
    mode = str(contract.get("protection_mode", "") or "").strip()
    if mode not in SKIN_TONE_PROTECTION_MODES:
        issues.append(
            "skin_tone_protection_contract.protection_mode只允许natural_protected/"
            "motivated_color_cast/source_authorized_marks/silhouette"
        )
    required_fields = (
        "subjects", "source_allowed_skin_marks", "skin_tone_baseline",
        "face_light_and_exposure", "face_fill_shadow_policy",
        "environment_color_boundary", "texture_atmosphere_boundary",
        "continuity_lock", "fallback",
    )
    for field in required_fields:
        if len(str(contract.get(field, "") or "").strip()) < 2:
            issues.append(f"skin_tone_protection_contract.{field}不能为空")

    subjects = str(contract.get("subjects", "") or "")
    visible = _string_list(visible_characters)
    generic_subject_scope = any(
        phrase in subjects for phrase in ("所有清晰入画人物", "全部清晰入画人物", "所有可见人物")
    )
    if visible and not generic_subject_scope:
        missing = [name for name in visible if name not in subjects]
        if missing:
            issues.append("skin_tone_protection_contract.subjects未覆盖清晰入画人物：" + "、".join(missing))

    prompt = str(full_prompt or "")
    for field in (
        "skin_tone_baseline", "face_light_and_exposure", "face_fill_shadow_policy",
        "environment_color_boundary", "texture_atmosphere_boundary",
    ):
        value = str(contract.get(field, "") or "").strip()
        if value and not _fragment_grounded(value, prompt):
            issues.append(f"skin_tone_protection_contract.{field}必须转译为full_prompt中的可见事实")

    allowed_marks = str(contract.get("source_allowed_skin_marks", "") or "").strip().lower()
    has_authorized_marks = allowed_marks not in ("", "none", "无", "无痕迹", "不适用", "n/a")
    if mode == "source_authorized_marks" and not has_authorized_marks:
        issues.append("source_authorized_marks必须填写源文明确允许的伤痕、妆容、泪痕或污迹")
    if mode == "silhouette" and not has_authorized_marks:
        issues.append("silhouette必须在source_allowed_skin_marks中写明源文或镜头功能依据")
    if mode == "motivated_color_cast":
        face_policy = " ".join((
            str(contract.get("face_light_and_exposure", "") or ""),
            str(contract.get("face_fill_shadow_policy", "") or ""), prompt,
        ))
        if not any(term in face_policy for term in ("中性补光", "中性面光", "暖白补光", "自然肤色参照", "中性眼神光")):
            issues.append("motivated_color_cast仍须保留中性面光、补光、眼神光或自然肤色参照区")

    contamination_authorized = mode == "source_authorized_marks" and has_authorized_marks
    if not contamination_authorized and any(
        re.search(pattern, prompt) for pattern in ACCIDENTAL_FACE_CONTAMINATION_PATTERNS
    ):
        issues.append("环境色、墙面纹理、灰尘雾粒或死黑阴影不得迁移到人物脸部")
    return issues


def tension_curve_role_issues(metadata):
    """Validate shot-level tension function for rhythm control."""
    metadata = metadata if isinstance(metadata, dict) else {}
    role = metadata.get("tension_curve_role")
    basemap = metadata.get("source_constraint_basemap", {})
    basemap_role = basemap.get("tension_curve_role") if isinstance(basemap, dict) else ""
    if role in (None, "") and not basemap_role:
        return []
    issues = []
    if not isinstance(role, str) or not role.strip():
        issues.append("qa_metadata.tension_curve_role必须是非空字符串")
    elif role.strip() not in TENSION_CURVE_ROLES:
        issues.append("qa_metadata.tension_curve_role只允许铺垫/升压/峰值/释放/缓冲")
    if basemap_role and role and _canonical_tension_curve_role(basemap_role) != _canonical_tension_curve_role(role):
        issues.append("qa_metadata.tension_curve_role必须与source_constraint_basemap.tension_curve_role一致")
    return issues


def _needs_physical_chain(text):
    return bool(re.search(
        r"手机|银行卡|卡|钥匙|文件|纸|杯|药瓶|门|车门|手腕|手臂|身体|重心|"
        r"递|接|拿|放|抢|夺|扶|抱|靠|转身|转向|起身|坐下|离开|进入|走向|"
        r"归属|转移|持有|控制",
        str(text or ""),
    ))


PROMPT_SOFT_RANGES = {
    "environment": (200, 700),
    "object": (200, 700),
    "simple_action": (300, 900),
    "dialogue_emotion": (400, 1100),
    "performance": (500, 1400),
    "important_entrance": (600, 1600),
    "relationship": (600, 1600),
    "interaction": (800, 2000),
    "complex_action": (900, 2200),
}


def prompt_soft_range(duration, profile=""):
    """Return non-blocking prompt-length guidance for one shot."""
    profile = str(profile or "").strip()
    if profile in PROMPT_SOFT_RANGES:
        return PROMPT_SOFT_RANGES[profile]
    try:
        seconds = float(duration or 0)
    except (TypeError, ValueError):
        seconds = 0
    if seconds > 10:
        return PROMPT_SOFT_RANGES["interaction"]
    if seconds > 6:
        return PROMPT_SOFT_RANGES["performance"]
    return PROMPT_SOFT_RANGES["simple_action"]


def prompt_length_profile(metadata, duration):
    """Derive the soft-range profile from narrative function and duration."""
    metadata = metadata if isinstance(metadata, dict) else {}
    dramatic = metadata.get("dramatic_design", {})
    dramatic = dramatic if isinstance(dramatic, dict) else {}
    function = str(dramatic.get("shot_function", "") or "")
    weight = str(dramatic.get("narrative_weight", "") or "")
    duration_design = metadata.get("duration_design", {})
    duration_design = duration_design if isinstance(duration_design, dict) else {}
    rationale = str(duration_design.get("duration_rationale", "") or "")
    try:
        seconds = float(duration or 0)
    except (TypeError, ValueError):
        seconds = 0
    if function == "entrance" and weight in ("high", "critical"):
        return "important_entrance"
    if function in ("confrontation", "reaction", "reveal") and weight in ("high", "critical"):
        return "relationship"
    if rationale == "continuous_action":
        return "complex_action"
    if seconds > 10:
        return "interaction"
    if seconds > 6:
        return "performance"
    if function in ("dialogue", "reaction", "confrontation"):
        return "dialogue_emotion"
    if function in ("environment", "establish"):
        return "environment"
    if function == "object":
        return "object"
    return "simple_action"


def prompt_length_issues(full_prompt, duration, hard_max_chars=None):
    """Return only runtime hard-limit violations.

    Soft ranges are guidance, never a reason to pad or split a shot. The caller
    must pass a user/platform-confirmed hard cap when one exists.
    """
    length = len(str(full_prompt or ""))
    if isinstance(hard_max_chars, (int, float)) and not isinstance(hard_max_chars, bool):
        if hard_max_chars > 0 and length > int(hard_max_chars):
            return [f"模型提示词{length}字，超过运行时平台硬上限{int(hard_max_chars)}字"]
    return []


def _string_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in re.split(r"[;；,，、/]+", value) if part.strip()]
    return []


def _canonical_tension_curve_role(value):
    return TENSION_CURVE_ROLE_ALIASES.get(str(value or "").strip(), str(value or "").strip())


def _fragment_grounded(value, text):
    """Return true when a concrete phrase from value appears in text."""
    value = str(value or "").strip()
    text = str(text or "")
    if not value:
        return False
    if value in text:
        return True
    fragments = [
        fragment.strip()
        for fragment in re.split(r"[，,；;。！？、\s]+", value)
        if len(fragment.strip()) >= 4 and fragment.strip() not in GENERIC_PERFORMANCE_TERMS
    ]
    return any(fragment in text for fragment in fragments[:4])


def _is_no_prop_state(value):
    text = str(value or "").strip().lower()
    if not text:
        return True
    return any(term in text for term in ("无关键道具", "无道具", "不涉及道具", "n/a", "none"))


def _looks_like_terminal_state(value):
    text = str(value or "").strip()
    if not text:
        return False
    terminal_terms = ("已在", "已经", "完成", "落幅", "最终", "转完", "拿到手", "到手上", "站到", "变成")
    middle_terms = (
        "伸向", "靠近", "接近", "指尖", "接触", "触碰", "拿起", "递出", "递到",
        "接住", "放下", "落定", "半转", "微转", "先转", "头部", "肩线", "重心",
        "跟随", "移向", "过渡", "途中",
    )
    return any(term in text for term in terminal_terms) and not any(term in text for term in middle_terms)


def _shares_meaningful_fragment(value, source_text):
    """Return true when value has a concrete phrase traceable to source_text."""
    value = str(value or "").strip()
    source_text = str(source_text or "")
    if not value or not source_text:
        return False
    if value in source_text or source_text in value:
        return True
    fragments = [
        fragment.strip()
        for fragment in re.split(r"[，,；;。！？、\s]+", value)
        if len(fragment.strip()) >= 4 and fragment.strip() not in GENERIC_PERFORMANCE_TERMS
    ]
    return any(fragment in source_text for fragment in fragments[:4])
