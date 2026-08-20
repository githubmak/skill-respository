#!/usr/bin/env python3
"""Regression tests for the dual-delivery Seedance contract."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR_PATH = SKILL_ROOT / "scripts" / "validate_seedance_delivery.py"
SPEC = importlib.util.spec_from_file_location("seedance_delivery_validator", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator: {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


def direct_document(
    *,
    visual_style: str = "3D CG写实",
    photography: str = (
        "35mm，中全景，平视侧面；摄影机沿文件向左短促横移，再随林岚退向门口让开遮挡，"
        "她停步时立即停稳，景别保持中全景"
    ),
    timeline: str = (
        "\n  - `0.0—0.8秒｜进入基线`：林岚维持克制站姿，周启台词成为当前主驱动力。"
        "\n  - `0.8—1.1秒｜刺激与准备`：周启说到关键词后，林岚延迟0.3秒，右手手指收紧。"
        "\n  - `1.1—2.0秒｜行动与接触`：林岚把文件推向周启一侧，文件沿桌面滑行并停住，纸面摩擦声同步。"
        "\n  - `2.0—2.4秒｜策略行动`：林岚松开文件并侧身退一步，摄影机横移后急停。"
        "\n  - `2.4—3.0秒｜结果确认`：周启延迟确认文件位置，双方关系距离拉开。"
        "\n  - `3.0—4.0秒｜镜尾保持`：双方保持结果，文件停在周启一侧，林岚停在门口附近"
    ),
    extra_fields: str = "",
    global_positive: str | None = None,
    global_negative: str | None = None,
    with_space: bool = False,
) -> str:
    use_realistic_3d = VALIDATOR.requires_realistic_3d_template(visual_style)
    default_positive = (
        "人物面部特征严格继承参考图，面部潜变量保持不变，脸型眉眼鼻子嘴唇形态全程固定，"
        "只改变表情肌肉，不改变五官基础形态；禁止重新采样面部基础结构；仅面部肌肉做表情运动，"
        "骨骼五官参数锁定；所有镜头人物面部基准统一；"
    )
    if use_realistic_3d:
        default_positive += (
            "3D CG写实电影渲染，人物建模采用高精度次世代角色标准，8K纹理贴图，皮肤细腻完整，"
            "均匀皮肤光照，柔和面部补光，次表面散射皮肤，干净面部光影，皮肤纹理稳定；"
        )
    default_positive += "口型与说话者一致，材质和帧间身份稳定"
    positive = default_positive if global_positive is None else global_positive
    default_negative = (
        "面部斑驳，脸部黑斑，脏色块，皮肤阴影斑块，面部噪点，脸部脏污，跨镜头人脸不一致，"
        "同人物多张脸；"
    )
    if use_realistic_3d:
        default_negative += "法线错误，贴图错乱；"
    default_negative += "人体畸变，道具复制，无因换手，摄影机穿墙"
    negative = default_negative if global_negative is None else global_negative
    space = ""
    if with_space:
        space = """
## 【场景空间位置关系】
空间依据：剧本推导。摄影机主要位于室内桌边与门口之间的可通行区域。前景可使用桌沿但不得遮住手部交接。林岚站在桌面右侧，周启站在左侧，两人隔桌相对。门口位于林岚身后，通道保持畅通。侧窗从画面右侧送入柔和天光。两人只允许沿桌边与门口之间移动，保持桌面关系轴，越轴须经正面中性机位。
"""
    return f"""# 示例｜Seedance独立直投版

## 【项目直投参数】
16:9，即梦 Seedance 2.5，{visual_style}，都市情感短剧。

## 【全局摄影规则】
主焦段保持人物关系自然，辅助焦段只在证据特写和空间揭示时使用；摄影机常态克制观察，危机动作才快速跟随并停稳。保持关系轴线，人物真实换位或正面中性镜后才越轴。手机端每个时段只有一个首读点，重要脸和手保持足够主体尺寸并位于中心安全阅读区，下方字幕区域不放唯一证据，复杂背景降低对比和运动幅度。

## 【全局影调】
中低饱和、黑位压实但保留暗部纹理，中间调完整，高光柔和滚降，人物肤色自然可读。

## 【全局光影】
所有场景使用可解释的窗光、顶灯与墙面反射，主光方向稳定，人物运动期间曝光和白平衡连续。

## 【全局环境色彩】
非资产环境以低饱和冷灰蓝和柔和暖白形成冷暖对照，冷色覆盖较大背景，暖色只落在生活灯区；人物服装、家具与道具固有色保持参考图。

## 【分场光影继承表】
| 场景 | 固定环境色彩 | 主光系统 | 影调与连续性 |
| --- | --- | --- | --- |
| 客厅·日 | 低饱和冷灰蓝、柔和暖白 | 右侧窗光、左墙反射 | 中低对比，人物肤色和光向连续 |

## 【全局正向提示词】
{positive}

## 【全局负面提示词】
{negative}

# 场景一｜客厅·日
{space}
## 【场景视觉方案】
- 场景影调：克制的中低对比，人物面部保持自然中间调，背景略低半级形成空间层次。
- 场景环境色彩：低饱和冷灰蓝落在窗外和背景空气，柔和暖白只落在室内灯区，不覆盖资产固有色。
- 场景光影：右侧窗光为主光，左侧墙面产生低强度自然反射，桌面形成连续软阴影。
- 光影变化触发：关键词后林岚退向门口，窗光在她侧脸形成更窄的亮面，停步后稳定。

## 【Seedance完整独立镜头】

### 镜头S1-01｜4秒｜退回文件并拉开距离

- **本镜环境色彩**：低饱和冷灰蓝位于背景，柔和暖白落在人物与桌面反射区，不覆盖人物服装和文件固有色。
- **当前资产与连续性**：林岚站在桌面右侧，右手悬在文件上方；周启站在左侧，文件留在两人之间，门口位于林岚身后；当前道具控制者为林岚，持物手为右手，文件保持平整并可见。
- **起幅状态**：双方隔桌站立，林岚仍维持冷静姿态，文件无人接触，门口路径未被占用。
- **摄影与构图**：{photography}。
- **光影/色彩/材质**：右侧窗光横过桌面，林岚面部按中全景级保护保持自然肤色和暗侧可读，人物移动只连续改变受光面；当前光区为右侧窗光与左墙反射交界，文件纸面和暗木桌材质保持真实摩擦与反射，关键手部受光连续，面部处于可读中间调。
- **画面与表演时间线**：{timeline}。
- **台词与声音层次**：说前周启停住脚步并吸气，林岚保持视线侧避；说中周启：“你一直都知道。”语速平稳，关键词“知道”时重音加重；说后保留尾音和林岚手指张力，受话者延迟0.3秒；仅周启准确口型；纸张摩擦声在近处出现，林岚脚步声来自门口方向，室内底噪在关键词处让位。
- **落幅状态**：文件停在周启一侧但周启尚未触碰，控制者仍为林岚，文件保持平整未开合、未破损；林岚退到门口附近，身体朝出口、头仍侧向周启；摄影机稳定保持两人、文件与出口，面部和纸面材质保持当前光区。{extra_fields}
"""


def director_document(duration: str = "4") -> str:
    return f"""# 示例｜导演审核版

## 项目与事实锁
- 台词事实载荷、文件交接和关系结果不变。

## 叙事立场
- 观众情感站位贴近林岚，观众与周启保持同等信息差；关键词后同步获得信息，信息释放由周启台词触发，关系翻转时切换为客观观察。

## 类型承诺与题材爆点母版
- 主类型为都市情感，辅助类型为言情；类型承诺是通过文件归属与人物退步看清关系破裂；观众核心期待是林岚是否停止退让；冲突载体是文件和门口边界；升级单位是关系暴露与退出距离；核心奇观是文件退回后林岚主动拉开距离；结果兑现是文件归周启一侧、林岚取得离场选择。

## 全局摄影圣经
- 主焦段服务双人关系，辅助焦段服务文件证据；摄影机整体克制，人物摄影区分林岚退让与周启稳定，情境摄影在关键词后由固定转短促横移。保持关系轴线；手机端使用唯一首读点、中心安全阅读区和字幕避让。未提供参考拍摄手法，按剧本、空间与视觉风格推导。

## 全局视觉结论
- 写实三维与克制冷暖关系。曝光层级为人物略亮于背景，关键文件亮度不高于人脸；主辅光比保持清楚方向与可读暗侧；色温由中性窗光和轻暖墙面反射组成；黑位保留暗部纹理，母色卡只约束非资产环境；面部保护按景别执行，材质保持纸张和木桌的真实反射；光影变化曲线从稳定对话到关键词后侧脸亮面收窄，再在退步结果稳定；特效受光本片段不启用；跨场保持肤色、光向和材质逻辑。

### 分场光影继承表
| 场景 | 环境颜色角色 | 主光/方向 | 辅光与背景 | 曝光/光比 | 光影变化触发 | 特效受光 |
| --- | --- | --- | --- | --- | --- | --- |
| 客厅 | 冷灰蓝背景、暖白人物区 | 右侧窗光 | 左墙反射、背景略暗 | 人物略亮、暗侧可读 | 退向门口后侧脸亮面收窄 | 本场不启用 |

## 短剧节奏蓝图
- 关键词命中后立即让策略动作改变关系。

## 整集/目标片段节奏曲线
- 0—10% 建立文件冲突；10%—30% 明确质问目标；30%—60% 用关键词加压；60%—80% 林岚策略改变；80%—100% 文件归属与关系余势落地。

## 时长预算与计算
- 本镜采用并行计算：T_speech=1.6秒，T_act=2.2秒，T_react=0.8秒，T_buf=1.0秒，T_shot=max(T_speech,T_act)+T_react+T_buf=4.0秒；预计总时长4.0秒，与逐镜时长之和一致。

## 人物表演与声音锚点
- 林岚：核心欲望是保留离场选择，核心恐惧是被迫承认关系破裂；压力下使用克制、退让和护住文件的防御策略，身体基线为站稳、视线侧避、手部低幅控制，声线低而平稳。周启：核心欲望是逼出确认，核心恐惧是失去主动权；持续情绪为逼问中的不安，声线平稳但关键词加重。

## 场景一：客厅
### 场景空间与视觉结论
- 空间依据为剧本推导；双方隔桌，门口在林岚身后，摄影机保持桌面关系轴，越轴须经正面中性机位。光影变化触发为林岚退向门口后进入较窄窗光，停步后稳定。

### 场景资产图提示词
- 无人物客厅场景资产图，隔桌关系明确，门口位于桌后右侧，桌面与文件作为固定空间锚点，右侧窗光斜入、左墙有柔和反射，冷灰蓝背景与暖白人物活动区形成层次，写实三维电影质感，竖屏构图安全区，禁止人物、文字、Logo、重复家具和新增出口。

### 爆点与特殊手法计划
- 本场类型职责为兑现；都市情感的类型承诺通过文件控制权与离场选择完成兑现。峰值镜号 S1-01；主机制为文件退回与人物退步形成的重动作爆点；剧情证据来自关键词和文件归属变化；第一读点是手部控制断裂；信息收益是关系主动权改变；与前后稳定段形成静动反差；本场不重复同类机制；人物动作承担高负载，摄影机只做一次横移急停；直投映射进入摄影、表演时间线和声音字段。

### 镜头 S1-01｜{duration}秒｜退回文件并拉开距离
- 剧情/类型职责：策略动作与关系结果，兑现都市情感的关系破裂。
- 表演与导演视觉：关键词刺激后林岚控制断裂，以手指收紧作为微动作，再退回文件；中全景横移并在林岚退到门口时急停，落幅保持退出方向。
- 台词事实映射：原句“你一直都知道。”；处理方式为保留；事实依据是周启已经确认林岚知情；最终执行句“你一直都知道。”；动作功能为证据确认与逼迫回应。
- 连续与声音：文件道具停在周启侧，林岚退到门口，保持桌面轴线；关键词与纸张声错峰，侧脸光影亮面收窄后稳定。
- 直投保护：首读点为手部松开文件；完整保留退回文件和退步动作、文件归属结果、停步终点和窗光变化。
"""


class SkillSourceTests(unittest.TestCase):
    def test_new_authoritative_references_are_required(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (
            SKILL_ROOT / "references" / "production-contract.md"
        ).read_text(encoding="utf-8")
        authoritative_source = f"{skill}\n{contract}"
        for marker in (
            "references/production-contract.md",
            "references/visual-input-governance.md",
            "references/ai-manga-dramatic-direction-engine.md",
            "references/seedance-dual-delivery-contract.md",
            "references/ai-manga-duration-budget.md",
            "references/shooting-method-reference.md",
            "references/wide-empty-shot-grammar.md",
            "刺激进入 -> 确认或误判 -> 第一冲动",
            "摄影机不得穿墙",
            "全局摄影圣经",
            "作品名_导演审核版.md",
            "作品名_Seedance独立直投版.md",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, authoritative_source)
        self.assertIn("本镜特殊正向约束", contract)
        self.assertIn("不写空标签或“无”", contract)

    def test_dual_contract_keeps_optional_story_tools_and_visual_system_fields(self) -> None:
        contract = (
            SKILL_ROOT / "references" / "seedance-dual-delivery-contract.md"
        ).read_text(encoding="utf-8")
        for marker in (
            "## 观众收益与留存设计（按需）",
            "不要求固定五轨结构",
            "不强制两秒公式",
            "不锁定百分比",
            "场景轴/人物轴/光影轴",
            "主要奇观",
            "全景/远景分别承担",
            "条件大气介质",
            "逐时间窗主驱动力及交接触发",
            "## 【关键道具资产提示词】",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, contract)

    def test_bold_camera_is_source_generation_not_optional_review(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (SKILL_ROOT / "references" / "production-contract.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("同一份内部镜头蓝图联合冻结", skill)
        self.assertIn("不重新选择镜头", skill)
        self.assertIn("炫技必须服务剧情读取", skill)
        self.assertIn("摄影机不得穿墙、穿物或从不可达区域拍摄", contract)
        self.assertIn("复杂信息若无法共享观看目标时串行或拆镜", contract)


class DeliveryValidatorTests(unittest.TestCase):
    def test_valid_multi_action_shot_and_pair_pass(self) -> None:
        direct = direct_document(with_space=True)
        self.assertEqual([], VALIDATOR.validate_direct(direct))
        self.assertEqual([], VALIDATOR.validate_director_pair(direct, director_document()))

    def test_internal_palette_code_is_blocked(self) -> None:
        text = direct_document().replace("低饱和冷灰蓝", "G01低饱和冷灰蓝", 1)
        self.assertTrue(any("内部标识" in error for error in VALIDATOR.validate_direct(text)))

    def test_hex_and_local_path_are_blocked(self) -> None:
        text = direct_document().replace(
            "人物服装、家具与道具固有色保持参考图",
            "环境使用#B8C5D6，参考/Volumes/HIKSEMI/scene.png",
        )
        errors = VALIDATOR.validate_direct(text)
        self.assertTrue(any("内部标识" in error for error in errors))

    def test_empty_effect_language_is_blocked(self) -> None:
        text = direct_document().replace("室内底噪在关键词处让位", "特效：无；室内底噪在关键词处让位")
        self.assertTrue(any("零提及" in error for error in VALIDATOR.validate_direct(text)))

    def test_missing_core_field_is_blocked(self) -> None:
        text = re_sub_once(r"(?m)^- \*\*光影/色彩/材质\*\*：[^\n]+\n", "", direct_document())
        self.assertTrue(any("核心字段" in error for error in VALIDATOR.validate_direct(text)))

    def test_timeline_requires_structured_rows(self) -> None:
        errors = VALIDATOR.validate_direct(
            direct_document(timeline="林岚听见关键词后推回文件，再退向门口并保持。")
        )
        self.assertTrue(any("逐行" in error and "阶段名" in error for error in errors))

    def test_timeline_must_be_continuous_and_reach_shot_end(self) -> None:
        timeline = (
            "\n  - `0.0—1.0秒｜起幅`：林岚保持站姿。"
            "\n  - `1.2—3.5秒｜行动`：林岚推回文件后保持。"
        )
        errors = VALIDATOR.validate_direct(direct_document(timeline=timeline))
        self.assertTrue(any("时间窗不连续" in error for error in errors))
        self.assertTrue(any("必须到达镜头总时长" in error for error in errors))

    def test_flat_abstract_emotion_is_rejected(self) -> None:
        timeline = (
            "\n  - `0.0—2.0秒｜情绪`：林岚紧张地看向周启。"
            "\n  - `2.0—4.0秒｜台词`：周启平静地质问并保持。"
        )
        errors = VALIDATOR.validate_direct(direct_document(timeline=timeline))
        self.assertTrue(any("抽象标签" in error for error in errors))

    def test_causal_emotion_chain_is_accepted(self) -> None:
        timeline = (
            "\n  - `0.0—1.0秒｜刺激进入`：林岚看见文件被推回，呼吸停住并保持视线落在纸面。"
            "\n  - `1.0—2.0秒｜认知与泄漏`：林岚意识到周启已经知情，瞳孔轻微收缩，错愕停在眉眼。"
            "\n  - `2.0—3.0秒｜控制与新策略`：林岚确认退路仍在门口，压住第一冲动，手指松开文件后停住。"
            "\n  - `3.0—4.0秒｜镜尾残留`：林岚侧身退开并保持身体朝向出口，目光仍锁定周启。"
        )
        errors = VALIDATOR.validate_direct(
            direct_document(timeline=timeline, with_space=True)
        )
        self.assertEqual([], errors)

    def test_dialogue_requires_performance_chain(self) -> None:
        text = direct_document().replace(
            "说前周启停住脚步并吸气，林岚保持视线侧避；说中周启：“你一直都知道。”语速平稳，关键词“知道”时重音加重；说后保留尾音和林岚手指张力，受话者延迟0.3秒；仅周启准确口型；",
            "周启：“你一直都知道。”语速平稳，重音落在“知道”，仅周启准确口型；",
        )
        errors = VALIDATOR.validate_direct(text)
        self.assertTrue(any("说前/说中/说后" in error for error in errors))

    def test_special_constraint_must_not_repeat_global_template(self) -> None:
        extra = (
            "\n- **本镜特殊正向约束**："
            + VALIDATOR.IDENTITY_TEMPLATE
        )
        errors = VALIDATOR.validate_direct(direct_document(extra_fields=extra))
        self.assertTrue(any("重复了全局固定模板" in error for error in errors))

    def test_missing_identity_template_is_blocked(self) -> None:
        positive = VALIDATOR.CG3D_TEMPLATE + "；口型与说话者一致"
        errors = VALIDATOR.validate_direct(direct_document(global_positive=positive))
        self.assertTrue(any("身份固定模板" in error for error in errors))

    def test_missing_3d_render_template_is_blocked(self) -> None:
        positive = VALIDATOR.IDENTITY_TEMPLATE + "；口型与说话者一致"
        errors = VALIDATOR.validate_direct(direct_document(global_positive=positive))
        self.assertTrue(any("3D CG 写实渲染模板" in error for error in errors))

    def test_non_3d_project_passes_without_3d_templates(self) -> None:
        errors = VALIDATOR.validate_direct(
            direct_document(visual_style="二维手绘动画", with_space=True)
        )
        self.assertEqual([], errors)

    def test_non_3d_project_rejects_3d_templates(self) -> None:
        positive = (
            VALIDATOR.IDENTITY_TEMPLATE
            + "；"
            + VALIDATOR.CG3D_TEMPLATE
            + "；口型与说话者一致"
        )
        negative = (
            VALIDATOR.FACE_NEGATIVE_TEMPLATE
            + "；"
            + VALIDATOR.CG3D_NEGATIVE
            + "；人体畸变"
        )
        errors = VALIDATOR.validate_direct(
            direct_document(
                visual_style="真人实拍感",
                global_positive=positive,
                global_negative=negative,
            )
        )
        self.assertTrue(any("非 3D 写实项目禁止包含 3D CG" in error for error in errors))
        self.assertTrue(any("非 3D 写实项目禁止包含“法线错误" in error for error in errors))

    def test_non_realistic_3d_project_omits_realistic_3d_template(self) -> None:
        errors = VALIDATOR.validate_direct(
            direct_document(visual_style="卡通3D低多边形", with_space=True)
        )
        self.assertEqual([], errors)

    def test_missing_face_negative_template_is_blocked(self) -> None:
        negative = VALIDATOR.CG3D_NEGATIVE + "；人体畸变，道具复制"
        errors = VALIDATOR.validate_direct(direct_document(global_negative=negative))
        self.assertTrue(any("面部稳定负面模板" in error for error in errors))

    def test_duplicate_identity_template_is_blocked(self) -> None:
        positive = (
            VALIDATOR.IDENTITY_TEMPLATE
            + "；"
            + VALIDATOR.CG3D_TEMPLATE
            + "；"
            + VALIDATOR.IDENTITY_TEMPLATE
        )
        errors = VALIDATOR.validate_direct(direct_document(global_positive=positive))
        self.assertTrue(any("身份固定模板" in error for error in errors))

    def test_duplicate_3d_render_template_is_blocked(self) -> None:
        positive = (
            VALIDATOR.IDENTITY_TEMPLATE
            + "；"
            + VALIDATOR.CG3D_TEMPLATE
            + "；"
            + VALIDATOR.CG3D_TEMPLATE
        )
        errors = VALIDATOR.validate_direct(direct_document(global_positive=positive))
        self.assertTrue(any("3D CG 写实渲染模板" in error for error in errors))

    def test_duplicate_face_negative_template_is_blocked(self) -> None:
        negative = (
            VALIDATOR.FACE_NEGATIVE_TEMPLATE
            + "；"
            + VALIDATOR.CG3D_NEGATIVE
            + "；"
            + VALIDATOR.FACE_NEGATIVE_TEMPLATE
        )
        errors = VALIDATOR.validate_direct(direct_document(global_negative=negative))
        self.assertTrue(any("面部稳定负面模板" in error for error in errors))

    def test_three_shot_sizes_require_structure(self) -> None:
        errors = VALIDATOR.validate_direct(
            direct_document(photography="0.0—1.0秒全景起幅，1.0—2.0秒推进到中景，2.0—4.0秒切入眼部特写并停稳")
        )
        self.assertFalse(any("三个以上景别" in error for error in errors))

    def test_unstructured_three_shot_sizes_are_rejected(self) -> None:
        errors = VALIDATOR.validate_direct(
            direct_document(photography="全景、中景、眼部特写，电影感构图")
        )
        self.assertTrue(any("三个以上景别" in error for error in errors))

    def test_stable_emotion_baseline_is_accepted(self) -> None:
        timeline = (
            "\n  - `0.0—2.0秒｜基线`：林岚保持平静姿态，视线停在文件上。"
            "\n  - `2.0—4.0秒｜镜尾保持`：林岚仍维持平静，手指轻压文件边缘。"
        )
        self.assertEqual([], VALIDATOR.validate_direct(direct_document(timeline=timeline, with_space=True)))

    def test_natural_dialogue_chain_is_accepted_without_fixed_labels(self) -> None:
        dialogue = (
            "周启停住脚步，吸气后才开口：“你一直都知道。”"
            "说到“知道”时声线压低，林岚慢半拍收紧手指；话落后尾音留在室内，"
            "双方保持当前距离，仅周启准确口型。"
        )
        text = direct_document().replace(
            "说前周启停住脚步并吸气，林岚保持视线侧避；说中周启：“你一直都知道。”语速平稳，关键词“知道”时重音加重；说后保留尾音和林岚手指张力，受话者延迟0.3秒；仅周启准确口型；",
            dialogue,
        )
        self.assertFalse(any("说前/说中/说后" in error for error in VALIDATOR.validate_direct(text)))

    def test_director_duration_mismatch_is_blocked(self) -> None:
        errors = VALIDATOR.validate_director_pair(direct_document(), director_document("5"))
        self.assertTrue(any("镜号/顺序/时长不一致" in error for error in errors))

    def test_explicit_transition_requires_bridge(self) -> None:
        errors = VALIDATOR.validate_direct(direct_document(), "【转场】\n客厅变为街道。")
        self.assertTrue(any("明确转场" in error for error in errors))

    def test_global_camera_rules_are_required(self) -> None:
        text = re_sub_once(
            r"(?ms)^## 【全局摄影规则】\n.*?(?=^## 【全局影调】)", "", direct_document(with_space=True)
        )
        errors = VALIDATOR.validate_direct(text)
        self.assertTrue(any("全局摄影规则" in error for error in errors))

    def test_global_lighting_bible_is_required(self) -> None:
        text = re_sub_once(
            r"(?ms)^## 【全局光影】\n.*?(?=^## 【全局环境色彩】)",
            "",
            direct_document(with_space=True),
        )
        errors = VALIDATOR.validate_direct(text)
        self.assertTrue(any("全局光影" in error for error in errors))

    def test_scene_space_is_required_without_uploaded_image(self) -> None:
        errors = VALIDATOR.validate_direct(direct_document(with_space=False))
        self.assertTrue(any("无场景图时也必须按剧本推导" in error for error in errors))

    def test_direct_must_not_leak_dialogue_audit(self) -> None:
        text = direct_document(with_space=True).replace(
            "周启：“你一直都知道。”", "原句：你知道；周启：“你一直都知道。”"
        )
        errors = VALIDATOR.validate_direct(text)
        self.assertTrue(any("台词审核信息" in error for error in errors))

    def test_director_requires_narrative_camera_rhythm_and_dialogue_mapping(self) -> None:
        director = director_document().replace("## 叙事立场", "## 叙事结论")
        errors = VALIDATOR.validate_director_pair(direct_document(with_space=True), director)
        self.assertTrue(any("叙事立场" in error for error in errors))

    def test_director_shot_requires_dialogue_fact_mapping(self) -> None:
        director = re_sub_once(r"(?m)^- 台词事实映射：[^\n]+\n", "", director_document())
        errors = VALIDATOR.validate_director_pair(direct_document(with_space=True), director)
        self.assertTrue(any("台词事实映射" in error for error in errors))

    def test_director_scene_spectacle_plan_is_optional(self) -> None:
        director = re_sub_once(
            r"(?ms)^### 爆点与特殊手法计划\n.*?(?=^### 镜头)",
            "",
            director_document(),
        )
        errors = VALIDATOR.validate_director_pair(direct_document(with_space=True), director)
        self.assertFalse(any("爆点与特殊手法计划" in error for error in errors))

    def test_director_scene_requires_scene_asset_prompt(self) -> None:
        director = re_sub_once(
            r"(?ms)^### 场景资产图提示词\n.*?(?=^### 镜头)",
            "",
            director_document(),
        )
        errors = VALIDATOR.validate_director_pair(direct_document(with_space=True), director)
        self.assertTrue(any("场景资产图提示词" in error for error in errors))

    def test_director_requires_duration_budget(self) -> None:
        director = re_sub_once(
            r"(?ms)^## 时长预算与计算\n.*?(?=^## )",
            "",
            director_document(),
        )
        errors = VALIDATOR.validate_director_pair(direct_document(with_space=True), director)
        self.assertTrue(any("时长预算与计算" in error for error in errors))


def re_sub_once(pattern: str, replacement: str, text: str) -> str:
    import re

    return re.sub(pattern, replacement, text, count=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
