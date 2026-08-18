#!/usr/bin/env python3
"""Regression tests for previously fixed storyboard skill failure modes."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR_PATH = SKILL_ROOT / "scripts" / "validate_storyboard_format.py"
SPEC = importlib.util.spec_from_file_location("storyboard_validator", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator: {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


PREFIX = """- 全局风格锁定
  - 用户指定风格：电影写实
  - 剧本推断补全：现代都市；推断依据：室内对白
  - 最终执行风格：现代都市电影写实

- 全局色卡/影调/光影
  - 全局影调：克制
  - 全局色卡：冷白墙面，明黄服装
  - 全局光影：窗光从右侧进入

- Seedance 2.5 专属提示词
  - 正向提示词：人物动作连续，道具状态稳定
  - 负向提示词：禁止穿墙穿物和无因换手

- 人物锚点
  - 宋棠：基准音色：年轻女声；基本性格锚点：窘迫但维持体面
  - 陆夫人：基准音色：沉稳女声；基本性格锚点：从容掌握节奏

- 场景 01｜客厅
  - 场景影调：冷静
  - 场景色卡：冷白与明黄
  - 场景光影：右侧窗光"""


def shot(
    number: int,
    start_state: str,
    visual: str,
    tail: str,
    *,
    start_type: str = "状态接力",
    duration: int = 4,
    setup: str = "宋棠中景，平视，摄影机位于茶几外侧",
    composition: str = "构图：宋棠位于画面右侧；光影：右侧窗光照亮宋棠",
    camera: str = "镜头固定在宋棠中景，焦点落在宋棠面部",
    audio: str = "无",
) -> str:
    return f"""- 镜头 {number:02d}｜{duration}s
  - 起始状态：{start_type}｜{start_state}
  - 景别机位：{setup}
  - 构图/光影：{composition}
  - 画面/表演：{visual}
  - 运镜/焦点：{camera}
  - 特效：无
  - 台词/音效：台词：无；音效：{audio}
  - 尾帧：{tail}"""


def document(*shots: str) -> str:
    return "\n\n".join((PREFIX, *shots))


def opening_shot() -> str:
    return shot(
        1,
        "宋棠站在茶几外侧，茶杯留在杯碟上",
        "宋棠站定，茶杯保持在杯碟上",
        "宋棠站在茶几外侧，茶杯仍在杯碟上",
        start_type="场景起镜",
    )


class SkillSourceBaselineTests(unittest.TestCase):
    def test_core_rules_remain_in_skill_source(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        directing_engine = (
            SKILL_ROOT / "references" / "ai-manga-dramatic-direction-engine.md"
        ).read_text(encoding="utf-8")
        authoritative_source = f"{skill_text}\n{directing_engine}"
        required_markers = (
            "主要反转比较三套",
            "只替换焦段、俯仰、左右、速度形容词",
            "微动作必须同时满足：当前景别可见",
            "每镜先锁定具名拍摄主体归属",
            "画外只描述具名人物",
            "原文每一个明确【转场】",
            "逐场维护人物、实体与道具连续性账本",
            "允许 1—4 个 0.5—3 秒的有职责短镜连打",
            "禁止用同一中景/中近景和缓推覆盖 10 秒以上关键反转",
            "连续摄影运动在一个窗口内保持一条可追踪路径",
            "唯一源头设计",
            "一镜可包含时长能够承载的同因果子动作",
            "每句台词在内部冻结",
            "作品名_导演审核版.md",
            "作品名_Seedance独立直投版.md",
            "不存在的 OS、OV、BGM、特效或本镜特殊约束删除整项",
            "references/ai-manga-dramatic-direction-engine.md",
            "references/cinematic-lighting-color-bible.md",
            "证据化增强",
            "全局摄影圣经",
            "手机端",
            "每个有图场景自动生成对应的 5—8 句客观空间描述",
            "禁止预加载全部参考",
        )
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, authoritative_source)

    def test_non_regression_reference_is_mandatory(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/non-regression-baseline.md", skill_text)
        self.assertIn("references/ai-manga-dramatic-direction-engine.md", skill_text)
        baseline = (SKILL_ROOT / "references" / "non-regression-baseline.md")
        self.assertTrue(baseline.is_file())
        directing_engine = (
            SKILL_ROOT / "references" / "ai-manga-dramatic-direction-engine.md"
        )
        self.assertTrue(directing_engine.is_file())

    def test_single_capability_protocol_requires_coverage_before_shots(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        engine = (
            SKILL_ROOT / "references" / "ai-manga-dramatic-direction-engine.md"
        ).read_text(encoding="utf-8")
        baseline = (
            SKILL_ROOT / "references" / "non-regression-baseline.md"
        ).read_text(encoding="utf-8")

        for marker in (
            "本技能是唯一运行能力入口",
            "自包含的独立技能",
            "单一能力执行协议",
            "能力覆盖账本",
            "核心已读 / 专项命中并完整读取 / 专项不命中并明确删除 / 事实歧义待确认",
            "不得只按用户关键词跳读某一类规则",
            "所有项目必读的核心能力",
            "覆盖确认只作生成闸门",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, skill_text)

        for marker in (
            "能力覆盖与漏读防护",
            "核心能力域必须全部是“已冻结”",
            "专项能力域必须逐项判定",
            "前状态 -> 必要过渡 -> 后状态",
            "人物压力和场景/环境压力",
            "普通场景道具只能承接",
            "没有空白、默认跳过或第二套导演规则覆盖源表",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, engine)

        self.assertNotIn("按命中追加", skill_text)
        self.assertIn("单一能力与防漏读覆盖账本", baseline)
        self.assertLess(
            skill_text.index("能力覆盖账本"),
            skill_text.index("锁定事实、台词载荷、人物知情、关键动作与结果"),
        )

    def test_creative_impact_self_check_is_source_stage_qualitative_only(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        engine = (
            SKILL_ROOT / "references" / "ai-manga-dramatic-direction-engine.md"
        ).read_text(encoding="utf-8")
        contract = (
            SKILL_ROOT / "references" / "seedance-dual-delivery-contract.md"
        ).read_text(encoding="utf-8")
        baseline = (
            SKILL_ROOT / "references" / "non-regression-baseline.md"
        ).read_text(encoding="utf-8")
        validator = (
            SKILL_ROOT / "scripts" / "validate_seedance_delivery.py"
        ).read_text(encoding="utf-8")

        for marker in (
            "创意感染力源头自检",
            "刺激—升级—翻转—释放—尾钩",
            "对说前/说中/说后、口型与声音桥握手",
            "具象机位、轴线与视觉因果握手",
            "只做定性通过/补强",
            "不评分、不统计关键词、不后置返工",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, skill_text + engine)

        for marker in (
            "每场停留、升级、翻转、释放和尾钩的实际承载位置",
            "说前/说中/说后与口型安全",
            "声音桥/环境声接替",
            "插切三态、轴线和视觉因果握手",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, contract)

        self.assertIn("创意感染力源头自检", baseline)
        self.assertNotIn("创意感染力", validator)
        self.assertNotIn("creative-impact", validator)

    def test_six_new_capabilities_are_source_generation_rules(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        directing_engine = (
            SKILL_ROOT / "references" / "ai-manga-dramatic-direction-engine.md"
        ).read_text(encoding="utf-8")

        for marker in (
            "观众情感站位",
            "观众/人物信息差",
            "主辅焦段",
            "摄影机性格",
            "手机端规则",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, directing_engine)
        self.assertIn("证据化增强", directing_engine)
        self.assertIn("不新增证据", skill_text)
        self.assertIn("0—10% 异常/危险/信息缺口", directing_engine)
        self.assertIn("80%—100% 结果兑现与新钩子", directing_engine)
        self.assertLess(
            skill_text.index("冻结叙事立场"),
            skill_text.index("为主要反转比较三套"),
        )

    def test_scene_images_are_automatically_parsed_without_reprompting(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        visual = (
            SKILL_ROOT / "references" / "visual-input-governance.md"
        ).read_text(encoding="utf-8")
        directing_engine = (
            SKILL_ROOT / "references" / "ai-manga-dramatic-direction-engine.md"
        ).read_text(encoding="utf-8")

        for marker in (
            "自动按地点归组",
            "不要求用户重新口述",
            "每个有图场景自动生成对应的 5—8 句客观空间描述",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, skill_text)
        self.assertIn("立即使用可用的图像/文档读取能力自动分析", visual)
        self.assertIn("自动为每个场景生成 5—8 句客观空间描述", visual)
        self.assertIn("输入阶段先冻结客观结构和行动边界", visual)
        self.assertNotIn("自动为每个场景生成 5—8 句", directing_engine)
        self.assertIn("空间模型", skill_text)

    def test_action_vfx_montage_are_source_rules_with_deduplication(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        spectacle_path = (
            SKILL_ROOT / "references" / "spectacle-action-vfx-montage.md"
        )
        spectacle = spectacle_path.read_text(encoding="utf-8")
        contract = (
            SKILL_ROOT / "references" / "seedance-dual-delivery-contract.md"
        ).read_text(encoding="utf-8")
        baseline = (
            SKILL_ROOT / "references" / "non-regression-baseline.md"
        ).read_text(encoding="utf-8")

        for marker in (
            "references/spectacle-action-vfx-montage.md",
            "重动作、VFX、蒙太奇或特殊剪辑",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, skill_text)

        for marker in (
            "爆点去重台账",
            "重动作爆点",
            "条件特效",
            "蒙太奇是剪辑结构，不是一条连续运镜",
            "动作、特效、运镜、多人反应、复杂口型和蒙太奇不能同时争夺主读点",
            "导演版逐场输出“爆点与特殊手法计划”",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, spectacle)

        self.assertIn("### 爆点与特殊手法计划", contract)
        self.assertIn("动作、特效与蒙太奇爆点去重", baseline)

    def test_ai_manga_duration_reference_shooting_and_wide_empty_shots(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        duration = (
            SKILL_ROOT / "references" / "ai-manga-duration-budget.md"
        ).read_text(encoding="utf-8")
        shooting = (
            SKILL_ROOT / "references" / "shooting-method-reference.md"
        ).read_text(encoding="utf-8")
        wide_empty = (
            SKILL_ROOT / "references" / "wide-empty-shot-grammar.md"
        ).read_text(encoding="utf-8")
        contract = (
            SKILL_ROOT / "references" / "seedance-dual-delivery-contract.md"
        ).read_text(encoding="utf-8")

        for marker in (
            "references/ai-manga-duration-budget.md",
            "references/shooting-method-reference.md",
            "references/wide-empty-shot-grammar.md",
            "只迁移观看距离、机位、运动、剪辑",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, skill_text)

        for marker in (
            "T_shot = max(T_speech, T_act) + T_react + T_buf",
            "T_shot = T_act + T_speech + T_react + T_buf",
            "高密度段平均每 2-4 秒出现一次新信息",
            "用户未给总时长时",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, duration)

        for marker in (
            "参考拍摄手法结论",
            "只迁移方法不复制内容",
            "漫画脉冲型",
            "关键节拍的非同构候选中",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, shooting)

        for marker in (
            "全景可以是峰值镜",
            "空镜的七种职责",
            "动作全貌",
            "人物退出后的残留空镜",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, wide_empty)

        self.assertIn("## 时长预算与计算", contract)
        self.assertIn("本场全景/远景分别承担", contract)

    def test_genre_engine_supports_broad_non_homogeneous_spectacle(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        genre_path = SKILL_ROOT / "references" / "genre-story-spectacle-engine.md"
        genre = genre_path.read_text(encoding="utf-8")
        contract = (
            SKILL_ROOT / "references" / "seedance-dual-delivery-contract.md"
        ).read_text(encoding="utf-8")

        self.assertIn("references/genre-story-spectacle-engine.md", skill_text)
        for marker in (
            "主类型",
            "辅助类型",
            "类型承诺",
            "冲突载体",
            "升级单位",
            "核心奇观",
            "结果兑现",
            "打斗",
            "种田",
            "异世界",
            "斗法",
            "都市",
            "古代",
            "言情",
            "宫斗",
            "任何未列类型",
            "不得让所有题材复用",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, genre)
        self.assertIn("## 类型承诺与题材爆点母版", contract)
        self.assertIn("本场类型职责", contract)
        baseline = (
            SKILL_ROOT / "references" / "non-regression-baseline.md"
        ).read_text(encoding="utf-8")
        self.assertIn("题材承诺与非同构爆点", baseline)

    def test_binge_short_drama_quality_is_generated_without_visual_templates(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        engine = (SKILL_ROOT / "references" / "ai-manga-dramatic-direction-engine.md").read_text(encoding="utf-8")
        genre = (SKILL_ROOT / "references" / "genre-story-spectacle-engine.md").read_text(encoding="utf-8")
        duration = (SKILL_ROOT / "references" / "ai-manga-duration-budget.md").read_text(encoding="utf-8")
        lighting = (SKILL_ROOT / "references" / "cinematic-lighting-color-bible.md").read_text(encoding="utf-8")
        spectacle = (SKILL_ROOT / "references" / "spectacle-action-vfx-montage.md").read_text(encoding="utf-8")
        contract = (SKILL_ROOT / "references" / "seedance-dual-delivery-contract.md").read_text(encoding="utf-8")
        baseline = (SKILL_ROOT / "references" / "non-regression-baseline.md").read_text(encoding="utf-8")

        for marker, source in (
            ("题材数量、镜头数量、动作层数、景别变化、炫技次数、特效层数和强度不设全局固定上限", skill_text),
            ("AI 短剧观众收益与留存链", genre),
            ("反差、反差萌与角色传播记忆", genre),
            ("五轨爆款节奏编排", duration),
            ("高级运镜候选生成器", engine),
            ("高级光影候选生成器", lighting),
            ("丁达尔光/体积光束只有同时满足", lighting),
            ("L1 局部显形", spectacle),
            ("爆款观众收益与留存设计", contract),
            ("爆款观众收益与再钩", baseline),
            ("非同构吸睛手法", baseline),
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

        self.assertIn("不得把“推近=紧张、环绕=高级、甩镜=爆点”当默认映射", engine)
        self.assertIn("禁止连续场景都使用同一窗光", lighting)
        self.assertIn("不设固定动作数量上限", engine)

    def test_lighting_bible_and_runtime_routing_preserve_quality(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        lighting = (
            SKILL_ROOT / "references" / "cinematic-lighting-color-bible.md"
        ).read_text(encoding="utf-8")
        contract = (
            SKILL_ROOT / "references" / "seedance-dual-delivery-contract.md"
        ).read_text(encoding="utf-8")
        baseline = (
            SKILL_ROOT / "references" / "non-regression-baseline.md"
        ).read_text(encoding="utf-8")

        for marker in (
            "唯一源头设计",
            "普通项目只读五个核心参考",
            "禁止预加载全部参考",
            "冻结唯一镜头蓝图",
            "不重读全部参考",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, skill_text)

        for marker in (
            "曝光层级",
            "主辅光比",
            "白平衡与色温关系",
            "光影剧情曲线",
            "分场光影继承表",
            "特效光影生命周期",
            "逐镜 `光影/色彩/材质` 只写相对场景方案的实际差量",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, lighting)

        for marker in (
            "### 分场光影继承表",
            "光影变化触发",
            "导演版五字段不复制直投版七字段正文",
            "任何提速不得减少剧情深度、题材广度",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, contract)

        self.assertIn("摄影指导级光影圣经", baseline)
        self.assertIn("运行提速不降级", baseline)

    def test_director_first_pass_precedes_governance(self) -> None:
        directing_engine = (
            SKILL_ROOT / "references" / "ai-manga-dramatic-direction-engine.md"
        ).read_text(encoding="utf-8")
        baseline = (
            SKILL_ROOT / "references" / "non-regression-baseline.md"
        ).read_text(encoding="utf-8")

        for marker in (
            "最强起幅",
            "唯一主体",
            "一个主视觉动词",
            "相邻主反差",
            "六维指纹",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, directing_engine)

        self.assertIn("主要反转必须在拆镜前比较三套非同构候选", directing_engine)
        self.assertIn("不折中拼接候选", directing_engine)
        self.assertIn("导演视觉首稿先于治理规则", baseline)

    def test_source_engine_rejects_isomorphic_camera_and_late_rework(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        engine = (
            SKILL_ROOT / "references" / "ai-manga-dramatic-direction-engine.md"
        ).read_text(encoding="utf-8")

        for marker in (
            "主要反转必须在拆镜前比较三套",
            "六维中有四维相同",
            "微动作必须同时满足",
            "表层语气",
            "现实压力源",
            "不二次拆镜",
            "不重写表演和光影",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, engine)

        self.assertIn("唯一源头设计", skill_text)
        self.assertIn("不重选摄影候选", skill_text)

    def test_creative_quality_is_generated_at_source_not_scanned_later(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        engine = (
            SKILL_ROOT / "references" / "ai-manga-dramatic-direction-engine.md"
        ).read_text(encoding="utf-8")
        baseline = (
            SKILL_ROOT / "references" / "non-regression-baseline.md"
        ).read_text(encoding="utf-8")
        validator = VALIDATOR_PATH.read_text(encoding="utf-8")

        for marker in (
            "首次生成质量决策",
            "不另建创意评分",
            "不得先生成再统计",
            "不在成稿后依据语义标点数",
            "不得无条件禁止快速运动",
            "首次生成必成条件",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, engine)

        self.assertIn("技能不提供创意审核或自动创意返工入口", skill_text)
        self.assertIn("创作质量只在源头生成", baseline)
        self.assertNotIn("conservatism_warnings", validator)
        self.assertNotIn("--creative-review", validator)
        self.assertNotIn("REVIEW:", validator)

    def test_md_gap_controls_are_frozen_in_the_source_blueprint(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        engine = (
            SKILL_ROOT / "references" / "ai-manga-dramatic-direction-engine.md"
        ).read_text(encoding="utf-8")
        duration = (
            SKILL_ROOT / "references" / "ai-manga-duration-budget.md"
        ).read_text(encoding="utf-8")
        lighting = (
            SKILL_ROOT / "references" / "cinematic-lighting-color-bible.md"
        ).read_text(encoding="utf-8")
        delivery = (
            SKILL_ROOT / "references" / "seedance-dual-delivery-contract.md"
        ).read_text(encoding="utf-8")
        visual_input = (
            SKILL_ROOT / "references" / "visual-input-governance.md"
        ).read_text(encoding="utf-8")
        baseline = (
            SKILL_ROOT / "references" / "non-regression-baseline.md"
        ).read_text(encoding="utf-8")
        validator = VALIDATOR_PATH.read_text(encoding="utf-8")

        for marker in (
            "事实/知情/节奏预演表",
            "时间/地点/出场人物",
            "主驱动力与耦合响应预算",
            "同一触发证据、同一观看目标、同一传播方向、同一阶段终态",
            "关系覆盖与回收",
            "返回关系宽镜",
            "高价值插切容量与过载退路",
            "删除次要插切 -> 用连续焦点交接/局部起幅承载",
            "情绪双曲线与性格准入",
            "内在强度 1—10 与外显幅度 0—5 分开",
            "完整表演链与静止锁定",
            "人物性格底色 -> 当前目标 -> 当前危险判断",
            "镜头组覆盖与景别梯度",
            "情绪承受镜",
            "直接切至",
            "台词、动作、反应与摄影必须形成唯一执行顺序",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, engine)

        self.assertIn("主驱动力读取带宽", duration)
        for marker in ("STYLE（", "TONE（", "FILTER BASE（", "MASTER PALETTE（", "SCENE VERSION（", "SHOT DELTA（"):
            with self.subTest(marker=marker):
                self.assertIn(marker, lighting)
        self.assertIn("EFFECT GATE", lighting)
        self.assertIn("风格、影调、场景灯光与景深分层", lighting)
        self.assertIn("滤镜/后期影像执行规则", lighting)
        self.assertIn("场景滤镜/后期影像", lighting)
        self.assertIn("关闭 -> 常驻/前兆 -> 局部激活 -> 衰减 -> 余波", lighting)
        self.assertIn("滤镜不得改变面部基础结构", delivery)
        self.assertIn("条件特效库", lighting)
        self.assertIn("分场事实/知情/状态预演表", delivery)
        self.assertIn("逐时间窗主驱动力及交接触发", delivery)
        self.assertIn("事实歧义暂停门", visual_input)
        self.assertIn("非事实性的视觉未知", skill_text)
        self.assertIn("视觉版本继承", baseline)

        # These controls generate the first blueprint; they must never revive late creative scans.
        self.assertNotIn("conservatism_warnings", validator)
        self.assertNotIn("--creative-review", validator)

    def test_direct_output_uses_continuous_action_timeline_rows(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        engine = (
            SKILL_ROOT / "references" / "ai-manga-dramatic-direction-engine.md"
        ).read_text(encoding="utf-8")
        duration = (
            SKILL_ROOT / "references" / "ai-manga-duration-budget.md"
        ).read_text(encoding="utf-8")
        contract = (
            SKILL_ROOT / "references" / "seedance-dual-delivery-contract.md"
        ).read_text(encoding="utf-8")
        baseline = (
            SKILL_ROOT / "references" / "non-regression-baseline.md"
        ).read_text(encoding="utf-8")

        for marker in (
            "直投动作描述按从 0.0 秒到镜尾的连续时间窗逐段输出",
            "不得把已冻结的动作时间线压缩成无时间顺序的散文段落",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, skill_text)

        for marker in (
            "直投动作时间线编译",
            "0.0—X.X秒｜阶段名",
            "第一行从 `0.0秒` 起",
            "不得缩写成动作清单或无时间标记的散文",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, engine)

        for marker in (
            "直投版统一把上述节点编译成逐行时间窗",
            "最后一行到 `T_shot`",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, duration)

        for marker in (
            "- **画面与表演时间线**：",
            "第一行从 `0.0秒` 开始",
            "每行使用统一结构",
            "具名主体与主驱动力",
            "进入基线 -> 具体刺激 -> 反应延迟/准备",
            "0.0—镜尾｜稳定保持",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, contract)

        self.assertIn("直投动作时间线格式", baseline)

    def test_reference_style_direct_format_and_fixed_prompts_are_permanent(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        governance = (
            SKILL_ROOT / "references" / "visual-input-governance.md"
        ).read_text(encoding="utf-8")
        contract = (
            SKILL_ROOT / "references" / "seedance-dual-delivery-contract.md"
        ).read_text(encoding="utf-8")
        baseline = (
            SKILL_ROOT / "references" / "non-regression-baseline.md"
        ).read_text(encoding="utf-8")
        validator = (
            SKILL_ROOT / "scripts" / "validate_seedance_delivery.py"
        ).read_text(encoding="utf-8")
        validator_literals_joined = validator.replace('"\n    "', "")

        ordered_sections = (
            "## 【项目直投参数】",
            "## 【全局摄影规则】",
            "## 【全局影调】",
            "## 【全局光影】",
            "## 【全局环境色彩】",
            "## 【分场光影继承表】",
            "## 【全局正向提示词】",
            "## 【全局负面提示词】",
        )
        positions = [contract.index(section) for section in ordered_sections]
        self.assertEqual(sorted(positions), positions)

        for marker in (
            "# 场景一｜场景名称·日/夜",
            "### 镜头S1-01｜X秒｜短语描述",
            "- **本镜环境色彩**：",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, contract)

        identity = (
            "人物面部特征严格继承参考图，面部潜变量保持不变，脸型眉眼鼻子嘴唇形态全程固定，"
            "只改变表情肌肉，不改变五官基础形态；禁止重新采样面部基础结构；仅面部肌肉做表情运动，"
            "骨骼五官参数锁定；所有镜头人物面部基准统一"
        )
        cg3d = (
            "3D CG写实电影渲染，人物建模采用高精度次世代角色标准，8K纹理贴图，皮肤细腻完整，"
            "均匀皮肤光照，柔和面部补光，次表面散射皮肤，干净面部光影，皮肤纹理稳定"
        )
        face_negative = (
            "面部斑驳，脸部黑斑，脏色块，皮肤阴影斑块，面部噪点，脸部脏污，"
            "跨镜头人脸不一致，同人物多张脸"
        )
        for source in (contract, baseline, validator_literals_joined):
            for template in (identity, cg3d, face_negative):
                with self.subTest(source_len=len(source), template=template[:12]):
                    self.assertIn(template, source)

        for template in (identity, cg3d, face_negative):
            with self.subTest(template=template[:12]):
                self.assertNotIn(template, governance)
        self.assertIn("本文件不保留第二份模板原文", governance)

        for source in (governance, contract):
            with self.subTest(source_len=len(source)):
                self.assertIn("卡通", source)
                self.assertIn("低多边形", source)
        for source in (governance, contract, baseline):
            with self.subTest(source_len=len(source)):
                self.assertIn("非写实三维", source)
        for source in (contract, baseline):
            with self.subTest(source_len=len(source)):
                self.assertIn("非 3D", source)
        self.assertIn("3D 写实兼容开/关", governance)
        self.assertIn("requires_realistic_3d_template", validator)
        self.assertIn("非 3D 写实项目禁止包含 3D CG 写实渲染模板", validator)

        self.assertIn("项目直投参数 -> 全局摄影/影调（含滤镜/后期影像）/光影/环境色彩", skill_text)
        self.assertIn('"本镜环境色彩"', validator)

    def test_story_impact_gaps_and_call_deduplication_are_source_rules(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        engine = (
            SKILL_ROOT / "references" / "ai-manga-dramatic-direction-engine.md"
        ).read_text(encoding="utf-8")
        contract = (
            SKILL_ROOT / "references" / "seedance-dual-delivery-contract.md"
        ).read_text(encoding="utf-8")
        baseline = (
            SKILL_ROOT / "references" / "non-regression-baseline.md"
        ).read_text(encoding="utf-8")

        for marker in (
            "观众预期/公平线索/兑现/新债",
            "选择代价/见证者",
            "视觉母题/注意力路径",
            "场景节奏波形",
            "提示词压缩层级",
            "创意保真降级",
            "最小执行协议",
            "每个任务只读取一次",
            "只生成一份导演源表",
            "交付验证只运行一次",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, skill_text)

        for marker in (
            "观众预期 -> 可见公平线索 -> 误判窗口 -> 重解释触发",
            "即时收益 -> 不可逆代价",
            "首读 -> 次读 -> 结果确认",
            "视觉母题处于建立、变体升级、反转变体或结果回收",
            "蓄压 -> 加速 -> 屏息/停顿",
            "主承受者、直接受话者、关键旁观者、空间/群体回声",
            "提示词层级/降级顺序",
            "不可删核心",
            "可压缩支撑",
            "可删除装饰",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, engine)

        for marker in (
            "观众预期、公平线索、误判窗口",
            "选择、即时收益、不可逆代价、见证者",
            "视觉母题与节奏波形",
            "首读→次读→结果确认",
            "不可删核心/可压缩支撑/可删除装饰",
            "交付验证失败只回到报错字段",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, contract)

        for marker in (
            "观众预期与公平回收",
            "选择、收益与不可逆代价",
            "视觉句与母题生命周期",
            "节奏波形与声音母题",
            "注意力路径与反应传播",
            "创意保真降级与提示词压缩",
            "单源编译与局部复验",
            "固定模板唯一真源",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, baseline)


class ValidatorRegressionTests(unittest.TestCase):
    def test_single_shot_size_without_fixed_prop_position_is_valid(self) -> None:
        text = document(
            shot(
                1,
                "宋棠站在客厅中央",
                "宋棠抬头看向前方",
                "宋棠保持站姿",
                start_type="场景起镜",
                setup="宋棠中近景，低机位仰拍",
                camera="镜头缓慢向前推进，保持宋棠中近景",
            )
        )
        self.assertEqual([], VALIDATOR.validate(text))

    def test_direct_full_to_closeup_shorthand_is_valid(self) -> None:
        text = document(
            shot(
                1,
                "宋棠站在客厅中央",
                "宋棠抬眼，注意力落向前方",
                "宋棠眼睛停在画面中央",
                start_type="场景起镜",
                setup="宋棠全景转眼部特写，低机位正面",
                camera="从宋棠全身缓慢下摇，最后停在宋棠眼睛",
            )
        )
        framing_errors = [
            error for error in VALIDATOR.validate(text)
            if "景别" in error or "起终幅" in error
        ]
        self.assertEqual([], framing_errors)

    def test_three_shot_sizes_in_one_shot_are_blocked(self) -> None:
        text = document(
            shot(
                1,
                "宋棠站在客厅中央",
                "宋棠向前迈步并抬眼",
                "宋棠眼睛停在画面中央",
                start_type="场景起镜",
                setup="宋棠全景转中景再转眼部特写，低机位正面",
                camera="镜头从宋棠全身推进到上半身，再停在宋棠眼睛",
            )
        )
        self.assertTrue(
            any("出现多个连续景别" in error for error in VALIDATOR.validate(text))
        )

    def test_orbit_changes_direction_not_shot_size(self) -> None:
        text = document(
            shot(
                1,
                "宋棠站在客厅中央",
                "宋棠保持身体朝向，陆夫人留在她对面",
                "宋棠仍处于中景，摄影机停在侧后方",
                start_type="场景起镜",
                setup="宋棠中景，平视正面",
                camera="保持宋棠中景，从正面环绕到侧后方后停止",
            )
        )
        self.assertEqual([], VALIDATOR.validate(text))



    def test_ambiguous_body_closeup_is_blocked(self) -> None:
        text = document(
            shot(
                1,
                "宋棠站在茶几外侧",
                "宋棠收紧鞋尖",
                "鞋面停在画面中央",
                start_type="场景起镜",
                setup="鞋面局部特写，低机位正面",
            )
        )
        self.assertTrue(any("没有写明人物归属" in error for error in VALIDATOR.validate(text)))

    def test_variable_framing_requires_named_start_and_end(self) -> None:
        text = document(
            shot(
                1,
                "宋棠站在茶几外侧",
                "宋棠抬起头",
                "宋棠面部停在画面中",
                start_type="场景起镜",
                camera="从宋棠手部上移，最终定格宋棠面部",
            )
        )
        self.assertTrue(any("唯一的具名起终幅" in error for error in VALIDATOR.validate(text)))

    def test_offscreen_gaze_is_blocked(self) -> None:
        text = document(
            shot(
                1,
                "宋棠站在茶几外侧",
                "陆夫人的打量落在画外，宋棠抬起头",
                "宋棠面部停在画面中",
                start_type="场景起镜",
            )
        )
        self.assertTrue(any("画外可见物" in error for error in VALIDATOR.validate(text)))

    def test_tail_cannot_keep_regions_outside_terminal_closeup(self) -> None:
        text = document(
            shot(
                1,
                "宋棠站在茶几外侧",
                "宋棠维持站姿",
                "宋棠鞋面和兔耳帽同时留在画面中",
                start_type="场景起镜",
                setup="宋棠鞋面局部特写起幅，低机位正面；终幅为宋棠兔耳帽特写",
                camera="从宋棠鞋面上移，最终定格宋棠兔耳帽",
            )
        )
        self.assertTrue(
            any("终点特写与尾帧可见范围冲突" in error for error in VALIDATOR.validate(text))
        )

    def test_prop_cannot_first_appear_in_later_start_state(self) -> None:
        text = document(
            opening_shot(),
            shot(
                2,
                "宋棠右手压住亮起的手机衣袋",
                "宋棠维持站姿",
                "宋棠右手仍压住手机衣袋",
            ),
        )
        self.assertTrue(any("首次出现道具“手机”" in error for error in VALIDATOR.validate(text)))

    def test_prop_introduction_requires_causal_entry(self) -> None:
        text = document(
            opening_shot(),
            shot(
                2,
                "宋棠双手垂在身侧",
                "宋棠低头查看手机屏幕",
                "手机握在宋棠右手中，亮起的屏幕朝向她",
            ),
        )
        self.assertTrue(
            any("没有识别到" in error and "手机" in error for error in VALIDATOR.validate(text))
        )

    def test_prop_change_requires_tail_settlement(self) -> None:
        text = document(
            opening_shot(),
            shot(
                2,
                "宋棠双手垂在身侧",
                "订单提示音响起，宋棠侧袋震动，她从侧袋拿出手机",
                "宋棠低头维持沉默",
                audio="订单提示音",
            ),
        )
        self.assertTrue(any("改变了道具“手机”" in error for error in VALIDATOR.validate(text)))

    def test_prop_state_cannot_jump_between_cuts(self) -> None:
        text = document(
            opening_shot(),
            shot(
                2,
                "宋棠双手垂在身侧",
                "订单提示音响起，宋棠侧袋震动，她发现后伸手压住侧袋",
                "宋棠右手压在仍震动的侧袋，手机没有拿出",
                audio="订单提示音，侧袋持续震动",
            ),
            shot(
                3,
                "宋棠右手拿着手机，亮起的屏幕朝向她",
                "宋棠低头查看屏幕",
                "手机仍握在宋棠右手中，亮起的屏幕朝向她",
            ),
        )
        self.assertTrue(
            any("最终状态冲突" in error and "手机" in error for error in VALIDATOR.validate(text))
        )

    def test_valid_prop_chain_passes(self) -> None:
        text = document(
            opening_shot(),
            shot(
                2,
                "宋棠双手垂在身侧",
                "订单提示音响起，宋棠侧袋震动，她发现后伸手压住侧袋",
                "宋棠右手压在仍震动的侧袋，手机没有拿出",
                audio="订单提示音，侧袋持续震动",
            ),
            shot(
                3,
                "宋棠右手压在仍震动的侧袋，手机没有拿出",
                "宋棠从侧袋拿出手机，屏幕朝向自己",
                "手机握在宋棠右手中，亮起的屏幕朝向她",
                start_type="动作接力",
            ),
        )
        phone_errors = [error for error in VALIDATOR.validate(text) if "手机" in error]
        self.assertEqual([], phone_errors)









if __name__ == "__main__":
    unittest.main(verbosity=2)
