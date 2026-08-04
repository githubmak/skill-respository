#!/usr/bin/env python3
"""Regression tests for storyboard validation and shadow semantic profiling."""

import unittest
from pathlib import Path

import validate_storyboard as validator


class SemanticCollisionTests(unittest.TestCase):
    def test_post_audio_requires_label_colon_and_quoted_verbatim_text(self) -> None:
        for malformed in ("OS: 我没事。", "系统音：闸机已锁定。", "OV - 快走。"):
            with self.subTest(malformed=malformed):
                self.assertEqual([malformed], validator.post_audio_format_issues(malformed))
        self.assertEqual([], validator.post_audio_format_issues("沈星雨OS：“我没事。”"))

    def test_os_requires_named_speaker(self) -> None:
        issues = validator.os_speaker_binding_issues("OS：“我没事。”", ["沈星雨"])
        self.assertTrue(any("缺少人物名" in issue for issue in issues), issues)
        self.assertEqual([], validator.os_speaker_binding_issues("沈星雨OS：“我没事。”", ["沈星雨"]))

    def test_os_rejects_pronoun_or_generic_speaker(self) -> None:
        for malformed in ("她OS：“我没事。”", "角色AOS：“我没事。”", "主角OS：“我没事。”"):
            with self.subTest(malformed=malformed):
                issues = validator.os_speaker_binding_issues(malformed, ["沈星雨"])
                self.assertTrue(any("代词或泛称" in issue for issue in issues), issues)

    def test_os_speaker_must_match_voice_lock(self) -> None:
        issues = validator.os_speaker_binding_issues("陌生人OS：“我没事。”", ["沈星雨"])
        self.assertTrue(any("不在本集角色声音锁定表" in issue for issue in issues), issues)

    def test_non_os_post_audio_labels_are_unaffected(self) -> None:
        text = "OV：“快走。” 系统音：“闸机已锁定。” 内心独白：“别回头。” 旁白：“天亮了。”"
        self.assertEqual([], validator.os_speaker_binding_issues(text, ["沈星雨"]))

    def test_voice_lock_names_supports_markdown_table_rows(self) -> None:
        global_section = """本集角色声音锁定表
| 人物 | 声音年龄感 | 音色 |
| --- | --- | --- |
| 沈星雨 | 青年 | 清冷 |
林默 | 中年 | 低沉

状态锁定：手机归沈星雨。
"""
        self.assertEqual(["沈星雨", "林默"], validator.voice_lock_names(global_section))

    def test_validate_child_enforces_os_binding_in_all_sound_fields(self) -> None:
        block = """【镜号】
1，3s，普通。

【画面描述｜直接复制】
16:9，3D写实，蓝灰主色冷白侧光，中景平视固定镜头。沈星雨闭口；OS：“我没事。”

【表演与声音】
她OS：“我没事。”

【状态继承】
沈星雨站位稳定。

【本镜制作控制】
画面质感：脸部冷白侧光和手机反光。
光效与曝光：冷白侧光照亮右脸，浅阴影稳定。
动态美学：固定起幅，呼吸响应，稳定落幅。
表演与情绪：闭口压住情绪，指尖停顿。
穿帮控制：人物站位和手机归属固定。
抽卡策略：低风险，保持单人固定镜头。
蒙太奇与剪辑：非蒙太奇，声音结束后切出。

【口型分窗】
优先级：口型 > 听者反应 > 运镜。陌生人OS：“我没事。”
"""
        issues: list[str] = []
        validator.validate_child(
            "S1-01", 1, "1，3s，普通。", block, ["沈星雨"], issues, ["沈星雨"]
        )
        self.assertTrue(any("【画面描述｜直接复制】 OS说话人绑定失败" in issue for issue in issues), issues)
        self.assertTrue(any("【表演与声音】 OS说话人绑定失败" in issue for issue in issues), issues)
        self.assertTrue(any("【口型分窗】 OS说话人绑定失败" in issue for issue in issues), issues)

    def test_environment_water_ripple_is_not_cutaway(self) -> None:
        prompt = "人物站在溪边，后景溪水泛起细小水纹，镜头固定。"
        self.assertFalse(validator.is_standalone_cutaway(prompt))

    def test_zero_person_water_ripple_is_cutaway(self) -> None:
        prompt = "本镜画面内可见人数：0人。俯视特写，水纹掠过湿石。"
        self.assertTrue(validator.is_standalone_cutaway(prompt))

    def test_character_hiding_behind_shoulder_is_not_reverse_shot(self) -> None:
        prompt = "满满躲在哥哥肩后，只露出半张脸。"
        self.assertFalse(validator.has_reverse_shot(prompt))

    def test_camera_behind_shoulder_is_reverse_shot(self) -> None:
        prompt = "摄影机在沈青乔肩后，前景保留肩线。"
        self.assertTrue(validator.has_reverse_shot(prompt))

    def test_performance_motion_is_not_camera_motion(self) -> None:
        prompt = "阿丰缓慢摇头，眼神移动到鱼篓，固定机位记录表演。"
        self.assertFalse(validator.has_camera_move(prompt))
        self.assertTrue(validator.has_camera_state(prompt))
        self.assertEqual("近景:static", validator.camera_signature("近景，" + prompt))

    def test_static_camera_recording_head_shake_is_not_camera_motion(self) -> None:
        prompt = "镜头固定记录阿丰摇头和眼神移动到鱼篓。"
        self.assertFalse(validator.has_camera_move(prompt))
        self.assertTrue(validator.has_camera_state(prompt))

    def test_camera_push_is_camera_motion(self) -> None:
        prompt = "85mm平视近景，镜头缓慢推近0.2米。"
        self.assertTrue(validator.has_camera_move(prompt))
        self.assertEqual("近景:平视:move", validator.camera_signature(prompt))

    def test_real_camera_move_variants_are_detected(self) -> None:
        prompts = (
            "摄影机平行侧跟0.3米，不超过孩子。",
            "摄影机沿三人中线缓慢拉开0.3米。",
            "镜头小幅右摇20度落到两个孩子。",
            "镜头轻推0.15米停在人物眼神上。",
        )
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assertTrue(validator.has_camera_move(prompt))

    def test_handheld_camera_is_a_camera_state(self) -> None:
        self.assertTrue(validator.has_camera_state("35mm低位机位轻微手持中景。"))
        self.assertTrue(validator.has_camera_state("镜头保持轻微手持感但主体稳定。"))


class SpatialFacingContractTests(unittest.TestCase):
    def test_doorway_back_front_relationship_is_valid(self) -> None:
        prompt = (
            "摄影机位于门外院地，朝屋内拍摄。沈青乔站在门槛外侧前景，背对摄影机，"
            "身体、胸口和脚尖面向卫景耘；卫景耘始终站在门槛内侧后景，身体和正面朝向沈青乔，"
            "正面和双肩可见。二人相互面对。沈青乔背影只遮挡卫景耘左侧下半身，"
            "卫景耘脸、双手和木棍仍可见，中央留出视觉通道。"
        )
        self.assertEqual([], validator.spatial_facing_issues(prompt, ["沈青乔", "卫景耘"]))

    def test_abstract_confrontation_without_reciprocal_facing_fails(self) -> None:
        prompt = "甲在画面左侧，乙在画面右侧，两人对峙并看向镜头。"
        issues = validator.spatial_facing_issues(prompt, ["甲", "乙"])
        self.assertTrue(any("分别写A身体面向B" in issue for issue in issues), issues)
        self.assertTrue(any("不得用面向/正对镜头" in issue for issue in issues), issues)

    def test_source_authorized_fourth_wall_gaze_is_valid(self) -> None:
        prompt = (
            "甲身体、胸口和脚尖面向乙，乙身体、胸口和脚尖面向甲，两人对峙。"
            "源文为打破第四面墙表演，2.0-3.0秒仅甲短暂直视镜头，甲身体仍面向乙；"
            "乙视线始终落在甲身上，3.0秒后甲视线回到乙。"
        )
        self.assertEqual([], validator.spatial_facing_issues(prompt, ["甲", "乙"]))

    def test_authorized_direct_address_rejects_multiple_camera_gazes(self) -> None:
        prompt = (
            "甲身体面向乙，乙身体面向甲，两人对峙。打破第四面墙，2.0-3.0秒甲直视镜头，"
            "乙也直视镜头，两人保持直视镜头到结束。"
        )
        issues = validator.spatial_facing_issues(prompt, ["甲", "乙"])
        self.assertTrue(any("只能有一名人物" in issue for issue in issues), issues)

    def test_authorized_direct_address_requires_end_state(self) -> None:
        prompt = (
            "甲身体面向乙，乙身体面向甲，两人对峙。打破第四面墙，"
            "2.0-3.0秒仅甲短暂直视镜头，甲身体仍面向乙。"
        )
        issues = validator.spatial_facing_issues(prompt, ["甲", "乙"])
        self.assertTrue(any("结束状态" in issue for issue in issues), issues)

    def test_camera_outside_cannot_put_outdoor_night_in_background(self) -> None:
        prompt = (
            "摄影机固定在门槛外侧，沈青乔站在门槛外侧，卫景耘站在门槛内侧，"
            "门外夜光留在背景，两人对望。"
        )
        issues = validator.spatial_facing_issues(prompt, ["沈青乔", "卫景耘"])
        self.assertTrue(any("门外夜色" in issue for issue in issues), issues)

    def test_actor_cannot_face_and_turn_back_to_same_exterior(self) -> None:
        prompt = "沈青乔站在屋内，身体面向门外，同时背对屋外，摄影机固定在屋内。"
        issues = validator.spatial_facing_issues(prompt, ["沈青乔"])
        self.assertTrue(any("同时背对并面向屋外" in issue for issue in issues), issues)

    def test_actor_back_to_camera_cannot_have_front_visible(self) -> None:
        prompt = "摄影机固定在门外朝屋内拍摄，沈青乔站在门槛外侧，背对摄影机，正面和双肩可见。"
        issues = validator.spatial_facing_issues(prompt, ["沈青乔"])
        self.assertTrue(any("背对摄影机却同时声明正面" in issue for issue in issues), issues)

    def test_camera_side_and_visible_plane_must_agree(self) -> None:
        prompt = (
            "摄影机位于门外院地，朝屋内拍摄。沈青乔站在门槛外侧，身体面向卫景耘，正面可见；"
            "卫景耘站在门槛内侧，身体面向沈青乔，正面可见。两人相互面对。"
        )
        issues = validator.spatial_facing_issues(prompt, ["沈青乔", "卫景耘"])
        self.assertTrue(any("与摄影机位于门槛同侧" in issue for issue in issues), issues)

    def test_camera_inside_looking_outside_cannot_put_interior_in_background(self) -> None:
        prompt = "摄影机位于屋内，朝门外拍摄，屋内墙面作为后景，沈青乔站在门槛外侧。"
        issues = validator.spatial_facing_issues(prompt, ["沈青乔"])
        self.assertTrue(any("屋内位于摄影机身后" in issue for issue in issues), issues)

    def test_return_home_requires_threshold_crossing_chain(self) -> None:
        prompt = "沈青乔回家，直接停在门槛内侧。"
        issues = validator.spatial_facing_issues(prompt, ["沈青乔"])
        self.assertTrue(any("完整可见动作链" in issue for issue in issues), issues)

    def test_similar_props_require_visible_distinction(self) -> None:
        issues = validator.spatial_facing_issues("沈青乔和阿丰各提一个竹篮，双竹篮归属固定。", ["沈青乔", "阿丰"])
        self.assertTrue(any("同类道具" in issue for issue in issues), issues)

    def test_camera_signature_distinguishes_angle(self) -> None:
        overhead = validator.camera_signature("俯视近景，镜头固定。")
        oblique = validator.camera_signature("斜俯近景，镜头固定。")
        self.assertNotEqual(overhead, oblique)


class CameraVariationAndTerminalTests(unittest.TestCase):
    def test_cross_group_signature_detects_repeated_composition(self) -> None:
        prompt = "50mm平视中景，前景门框形成框景，镜头固定记录人物。"
        signatures = [validator.group_camera_signature(prompt) for _ in range(3)]
        self.assertTrue(signatures[0])
        self.assertEqual(signatures[0], signatures[1])
        self.assertEqual(signatures[1], signatures[2])

    def test_cross_group_signature_distinguishes_visual_tasks(self) -> None:
        prompts = (
            "35mm斜前方全景，前景门框形成框景，镜头固定。",
            "50mm平视中景，三角关系构图，摄影机横移0.2米。",
            "85mm轻俯近景，中央空位留白，镜头轻推后停稳。",
        )
        signatures = [validator.group_camera_signature(prompt) for prompt in prompts]
        self.assertEqual(3, len(set(signatures)))

    def test_terminal_frame_requires_positive_anti_duplication_facts(self) -> None:
        prompt = (
            "本镜画面内可见人数：2人，角色A在左侧、角色B在右侧。"
            "最后20%摄影机减速停稳，两人脸、手和四肢边界分开，道具仍归角色A，"
            "光线曝光保持，不新增人物，不产生重复人物，保持到结束。"
        )
        self.assertEqual([], validator.terminal_frame_issues(prompt, "S1-03", 1))

    def test_terminal_frame_rejects_unstable_last_shot(self) -> None:
        issues = validator.terminal_frame_issues(
            "本镜画面内可见人数：2人，角色A和角色B继续向门口走。", "S1-03", 1
        )
        self.assertTrue(any("终端稳定事实" in issue for issue in issues), issues)


class TemporalLightingContractTests(unittest.TestCase):
    def test_user_oil_lamp_prompt_fails_without_explicit_time_contract(self) -> None:
        prompt = (
            "16:9，3D精致国风CG，小院屋内暖褐主色，右侧油灯灯光照亮沈青乔主要受光面，"
            "卫景耘侧影留在后景。50mm平视中近景，前景门框构图，摄影机固定；"
            "最后20%摄影机停稳，灯光曝光固定。"
        )
        issues = validator.temporal_lighting_issues(prompt)
        self.assertTrue(any("缺少明确时段" in issue for issue in issues), issues)
        self.assertTrue(any("承担主光" in issue for issue in issues), issues)
        self.assertTrue(any("亮度" in issue for issue in issues), issues)

    def test_complete_night_oil_lamp_contract_passes(self) -> None:
        prompt = (
            "16:9，3D精致国风CG，同一夜晚的小院屋内，门外保持深蓝黑位，天空亮度稳定，"
            "右侧油灯是唯一主光源，暖褐灯光照亮沈青乔右脸。50mm平视中近景，前景门框构图，"
            "摄影机固定；最后20%背景亮度、主光方向、色温和曝光保持到结束。"
        )
        self.assertEqual([], validator.temporal_lighting_issues(prompt))

    def test_adjacent_shots_reject_night_to_day_and_primary_light_change(self) -> None:
        previous = (
            "同一夜晚的小院屋内，门外保持深蓝黑位，右侧油灯是唯一主光源，"
            "最后20%曝光保持到结束。"
        )
        current = (
            "白天的小院屋内，窗外保持明亮，左侧日光是唯一主光源，"
            "最后20%曝光保持到结束。"
        )
        issues = validator.temporal_lighting_continuity_issues(previous, current)
        self.assertTrue(any("时段冲突" in issue for issue in issues), issues)
        self.assertTrue(any("主光源冲突" in issue for issue in issues), issues)

    def test_adjacent_shots_keep_same_night_and_oil_lamp(self) -> None:
        previous = "同一夜晚，门外保持深蓝黑位，右侧油灯是唯一主光源，曝光保持到结束。"
        current = "同一夜晚，门外保持深蓝黑位，右侧油灯仍是主光源，主光方向和曝光保持到结束。"
        self.assertEqual([], validator.temporal_lighting_continuity_issues(previous, current))


class OutputFormatTests(unittest.TestCase):
    @staticmethod
    def _global_scale_fixture(include_positive: bool, include_negative: bool) -> str:
        positive = (
            "- 全局比例与支撑锁定：全程角色骨骼与头身比例恒定，人物真实身高和体型尺寸固定；"
            "四肢长度与关节比例稳定，地平线及消失关系稳定；人物身体主支撑点持续贴合当前承载面，"
            "站立时双脚接地，行走时步态交替接地，坐卧时臀背或躯干贴合承载面，"
            "腾空时保持起跳、空中与落地轨迹连续；"
            "同镜两人身高差、骨架和相对尺寸全程一致，人物画面投影只随物理距离连续变化，"
            "固定距离下画面占比保持稳定。"
        ) if include_positive else ""
        negative = (
            "机械循环动作、无因重复眨眼、无因身体抖动、人物忽高忽低、体型动态变化、腿部拉长缩短、"
            "无因尺度跳变、无因浮空、透视错乱、穿模、肢体畸形、广角畸变"
        ) if include_negative else "机械循环动作、无因重复眨眼、无因身体抖动"
        return (
            "## 使用说明\n\n## 全局锁定\n" + positive + "\n\n"
            "## 制作质量总控\n"
            "画面质感基线：门框构图，人物实焦，木桌保留划痕。\n"
            "光效与曝光连续：左侧窗光照亮人物脸和手，暗部可读。\n"
            "动态美学基线：起幅稳定，动作触发后低幅响应并落幅停稳。\n"
            "表演与情绪基线：听见台词后压住反应，眼神泄露并保留余波。\n"
            "蒙太奇与剪辑基线：动作或反应切点增加新信息，声音自然承接。\n"
            "穿帮与抽卡总控：锁定身份、接触支撑、道具归属、口型和稳定终态。\n\n"
            "## 通用负面提示词｜直接复制\n" + negative + "\n\n"
            "## 场景状态表\n\n## 分镜投喂卡\n"
        )

    def test_global_scale_lock_is_required(self) -> None:
        issues = validator.validate(
            Path("dummy.md"), self._global_scale_fixture(False, True)
        )
        self.assertTrue(any("missing 全局比例与支撑锁定" in issue for issue in issues), issues)

    def test_global_scale_negative_terms_are_required(self) -> None:
        issues = validator.validate(
            Path("dummy.md"), self._global_scale_fixture(True, False)
        )
        self.assertTrue(any("missing scale/perspective risks" in issue for issue in issues), issues)

    def test_complete_global_scale_guards_pass_their_dedicated_gate(self) -> None:
        issues = validator.validate(
            Path("dummy.md"), self._global_scale_fixture(True, True)
        )
        self.assertFalse(any("全局比例与支撑锁定" in issue for issue in issues), issues)
        self.assertFalse(any("scale/perspective risks" in issue for issue in issues), issues)

    def test_shot_quality_control_requires_visible_execution_dimensions(self) -> None:
        control = (
            "画面质感：右侧人物为第一视觉落点，50mm实焦，木桌保留细划痕。\n"
            "光效与曝光：左侧窗光照亮脸和手，阴影保留细节，高光稳定。\n"
            "动态美学：起幅人物压住桌沿，开门声触发抬眼，镜头固定，落幅停稳。\n"
            "表演与情绪：听见开门声触发戒备，对外保持平静，眼神泄露，余波停在门口。\n"
            "穿帮控制：右手持续接触桌沿，双脚接地，道具仍在桌面右侧。\n"
            "抽卡策略：中风险，手部接触与抬眼竞争；固定机位，人工首轮检查。\n"
            "蒙太奇与剪辑：非蒙太奇；保持镜头让抬眼产生信息增量，环境声连续。"
        )
        direct = (
            "16:9写实电影短片，50mm平视近景，人物位于画面右侧实焦，木桌细划痕清楚；"
            "左侧窗光照亮脸和手，阴影保留细节，高光稳定。人物身体面向门口，右手持续接触桌沿，"
            "双脚接地，道具仍在桌面右侧；听见开门声后抬眼，呼吸停顿，眼神停在门口形成余波。"
            "固定机位记录这一低幅反应，落幅停稳。"
        )
        self.assertEqual([], validator.quality_control_issues(control, direct))

    def test_shot_quality_control_rejects_visible_fact_missing_from_direct_prompt(self) -> None:
        control = (
            "画面质感：门框形成前景框景，木桌保留细划痕。\n"
            "光效与曝光：左侧窗光照亮脸和手，阴影可读。\n"
            "动态美学：起幅稳定，开门声触发抬眼，固定机位，落幅停稳。\n"
            "表演与情绪：听见开门声触发戒备，眼神泄露，余波停在门口。\n"
            "穿帮控制：右手接触桌沿，双脚接地，道具仍在桌面右侧。\n"
            "抽卡策略：中风险；固定机位，人工首轮检查。\n"
            "蒙太奇与剪辑：非蒙太奇；保持当前连续镜头。"
        )
        issues = validator.quality_control_issues(
            control, "16:9写实电影短片，人物站在房间中央。"
        )
        for label in ("画面质感", "光效与曝光", "动态美学", "表演与情绪", "穿帮控制"):
            self.assertTrue(any(label in issue and "未转译" in issue for issue in issues), (label, issues))

    def test_shot_quality_control_rejects_internal_placeholders(self) -> None:
        control = "\n".join(f"{label}：已检查，按合同执行。" for label in validator.SHOT_QUALITY_LABELS)
        issues = validator.quality_control_issues(control, "16:9写实电影短片，平视近景，镜头固定。")
        self.assertTrue(any("不能使用内部占位" in issue for issue in issues), issues)

    def test_field_lines_with_markdown_trailing_spaces_remain_parseable(self) -> None:
        block = (
            "【镜号】  \n1，2s，普通。\n\n"
            "【画面描述｜直接复制】  \n正向提示词。\n\n"
            "【表演与声音】  \n无台词。\n\n"
            "【状态继承】  \n人物仍站在原位。"
        )
        children = list(validator.iter_children(block))
        self.assertEqual(1, len(children))
        self.assertEqual("正向提示词。", validator.direct_prompt(children[0].group(0)))
        self.assertEqual("无台词。", validator.extract(children[0].group(0), "【表演与声音】", "【状态继承】"))

    def test_prefixed_group_id_is_not_accepted(self) -> None:
        text = "#### C1-S1-01｜镜头组总时长：2s\n"
        self.assertEqual([], list(validator.iter_groups(text)))
        issues = validator.validate(Path("dummy.md"), text)
        self.assertTrue(any("invalid shot group heading" in issue for issue in issues))

    def test_independent_file_must_start_at_s1_01(self) -> None:
        text = "#### S2-01｜镜头组总时长：2s\n\n【出现人物】\n甲\n"
        issues = validator.validate(Path("dummy.md"), text)
        self.assertTrue(any("首个镜头组必须为S1-01" in issue for issue in issues))

    def test_group_numbering_cannot_skip_or_repeat(self) -> None:
        text = (
            "#### S1-01｜镜头组总时长：2s\n\n【出现人物】\n甲\n\n"
            "#### S1-03｜镜头组总时长：2s\n\n【出现人物】\n甲\n"
        )
        issues = validator.validate(Path("dummy.md"), text)
        self.assertTrue(any("镜头组编号跳号或重复" in issue for issue in issues))

    def test_bundle_requires_identical_project_quality_contracts(self) -> None:
        shared = (
            "## 全局锁定\n统一人物与空间锁。\n\n"
            "## 制作质量总控\n画面质感基线：自然电影感。\n\n"
            "## 通用负面提示词｜直接复制\n换脸、穿模。\n"
        )
        changed = shared.replace("自然电影感", "高饱和广告感")
        issues = validator.bundle_contract_issues([
            (Path("scene_a.md"), shared),
            (Path("scene_b.md"), changed),
        ])
        self.assertTrue(any("制作质量总控" in issue for issue in issues), issues)


class ShotTypeShadowTests(unittest.TestCase):
    def test_dialogue_performance_classification(self) -> None:
        prompt = "客厅平视近景，镜头固定。沈青乔开口说：“回来。”"
        self.assertEqual("dialogue_performance", validator.detect_shot_type(prompt))

    def test_relationship_classification(self) -> None:
        prompt = "本镜画面内可见人数：2人。沈青乔与阿丰并肩站在溪边，身体面对溪水，镜头固定。"
        self.assertEqual(
            "multi_character_relationship",
            validator.detect_shot_type(prompt, cast_names=["沈青乔", "阿丰"]),
        )

    def test_silent_causal_classification(self) -> None:
        prompt = "她发现水管漏水，转身上前按下阀门，水流逐渐停止，镜头固定。"
        self.assertEqual("silent_causal", validator.detect_shot_type(prompt))

    def test_cutaway_classification(self) -> None:
        prompt = "本镜画面内可见人数：0人。俯视特写，镜头固定，只拍水纹和湿石。"
        self.assertEqual("cutaway_insert", validator.detect_shot_type(prompt))

    def test_montage_classification_precedes_action_risk(self) -> None:
        prompt = "同一工作台时间流逝蒙太奇，她反复拿起工具，半成品逐渐成形。"
        self.assertEqual("montage_fragment", validator.detect_shot_type(prompt))

    def test_montage_rhythm_without_time_change_is_not_time_compression(self) -> None:
        prompt = "她以节制蒙太奇节奏重复捕鱼动作，三条鱼依次落到岸边。"
        self.assertNotEqual("montage_fragment", validator.detect_shot_type(prompt))

    def test_non_combat_action_classification(self) -> None:
        prompt = "她为了寻找出口，沿走廊走到转角，改道抵达楼梯口，镜头固定。"
        self.assertEqual("non_combat_action", validator.detect_shot_type(prompt))

    def test_prop_transfer_is_high_risk_transition(self) -> None:
        prompt = "她从右手递出卡片，对方接触后接过并握住，她再松手。"
        self.assertEqual("high_risk_transition", validator.detect_shot_type(prompt))

    def test_complete_short_silent_shot_is_not_rejected_by_length(self) -> None:
        prompt = (
            "16:9，3D精致CG，旧厨房暖黄窗光照在木纹墙面。平视中景，镜头固定。"
            "她发现水管漏水，身体面向墙角水阀，转身上前按下阀门，水流逐渐停止，地面积水不再扩散。"
            "她确认阀门关闭后仍站在墙边，画面停在水滴停止的新状态。"
        )
        report = validator.build_semantic_report(prompt)
        self.assertEqual("silent_causal", report.shot_type)
        self.assertTrue(report.semantically_complete, report.missing_slots)
        self.assertEqual("short", report.length_guidance)
        self.assertEqual("semantic-complete/short", report.disagreement)

    def test_long_but_incomplete_shot_disagrees_with_semantics(self) -> None:
        prompt = "人物站在客厅。" * 30
        report = validator.build_semantic_report(prompt)
        self.assertFalse(report.semantically_complete)
        self.assertNotEqual("short", report.length_guidance)
        self.assertEqual("semantic-incomplete/despite-length", report.disagreement)

    def test_cutaway_profile_uses_short_guidance_without_a_minimum_gate(self) -> None:
        prompt = "本镜画面内可见人数：0人。空镜只拍水纹。"
        report = validator.build_semantic_report(prompt)
        self.assertEqual((90, 220), (report.recommended_min, report.recommended_max))
        self.assertEqual("short", report.length_guidance)
        self.assertFalse(validator.has_visible_person(prompt))

    def test_phone_semantics_require_purpose_and_orientation(self) -> None:
        prompt = "16:9，3D CG，客厅暖光，平视中景，镜头固定。她拿着手机，画面停在她低头的姿态。"
        report = validator.build_semantic_report(prompt)
        self.assertIn("手机用途", report.missing_slots)
        self.assertIn("手机屏幕朝向", report.missing_slots)

    def test_phone_operation_evidence_satisfies_purpose_shadow_slot(self) -> None:
        prompt = (
            "16:9，3D CG，客厅暖光，平视中景，镜头固定。她双手横持手机，双拇指连续点击，"
            "屏幕朝向本人，手机背面朝向镜头，目光停在屏幕上，手机高度和朝向保持稳定。"
        )
        report = validator.build_semantic_report(prompt)
        self.assertNotIn("手机用途", report.missing_slots)
        self.assertNotIn("手机屏幕朝向", report.missing_slots)
        self.assertNotIn("结束稳定状态", report.missing_slots)

    def test_natural_end_state_phrases_are_detected(self) -> None:
        self.assertTrue(validator.has_end_state("她说完闭口，右手落回身侧，目光停在听者脸上。"))

    def test_phone_ui_priming_in_negative_field_is_rejected(self) -> None:
        direct = (
            "她双手横持手机玩手机游戏，屏幕朝向本人，手机背面朝向镜头，双拇指连续点击，"
            "结束时手机高度和朝向保持稳定。"
        )
        state = "手机仍在她双手胸前，屏幕朝向本人。"
        issues = validator.phone_operation_issues(
            direct,
            state,
            "",
            "屏幕乱字、游戏界面露出、手指畸形",
            "",
            "",
        )
        self.assertTrue(any("本镜补充负面提示词" in issue and "游戏界面" in issue for issue in issues))

    def test_phone_ui_priming_is_rejected_in_every_direct_feed_field(self) -> None:
        direct = (
            "她双手横持手机玩手机游戏，屏幕朝向本人，手机背面朝向镜头，双拇指连续点击，"
            "结束时手机高度和朝向保持稳定。"
        )
        state = "手机仍在她双手胸前，屏幕朝向本人。"
        variants = (
            (direct + "游戏角色保持不可见。", "", "", "", "", "画面描述"),
            (direct, "无HUD。", "", "", "", "本镜必要约束"),
            (direct, "", "游戏界面露出", "", "", "本镜补充负面提示词"),
            (direct, "", "", "首帧无技能栏。", "", "关键帧生图提示"),
            (direct, "", "", "", "全程不出现小地图。", "即梦视频提示"),
        )
        for prompt, necessary, negative, keyframe_image, keyframe_video, field_name in variants:
            with self.subTest(field_name=field_name):
                issues = validator.phone_operation_issues(
                    prompt,
                    state,
                    necessary,
                    negative,
                    keyframe_image,
                    keyframe_video,
                )
                self.assertTrue(any(field_name in issue for issue in issues), issues)

    def test_phone_negative_field_allows_only_non_semantic_artifacts(self) -> None:
        direct = (
            "她双手横持手机玩手机游戏，屏幕朝向本人，手机背面朝向镜头，双拇指连续点击，"
            "结束时手机高度和朝向保持稳定。"
        )
        state = "手机仍在她双手胸前，屏幕朝向本人。"
        issues = validator.phone_operation_issues(
            direct,
            state,
            "",
            "手机翻面、屏幕乱字、手机高度跳变、手机漂浮穿手、手指畸形、握持穿模",
            "",
            "",
        )
        self.assertEqual([], issues)

    def test_exact_ai_bubble_text_requires_explicit_opt_in(self) -> None:
        direct = (
            "16:9，3D自然电影CG，客厅窗光落在木纹桌面，桌面保留低亮反光。"
            "她身体面向手机，双手横持手机停在胸前，屏幕朝向本人，手机背面朝向镜头；"
            "画面右侧安全区出现单条独立二维绿色聊天气泡浮层，气泡内写：“明天见”。"
            "平视中近景，镜头固定，画面停在她看向手机的姿态。"
        )
        block = (
            "【镜号】\n1，3s，复杂。\n\n"
            f"【画面描述｜直接复制】\n{direct}\n\n"
            "【表演与声音】\n无台词。\n\n"
            "【状态继承】\n手机仍在她双手胸前，屏幕朝向本人。\n\n"
            "【本镜制作控制】\n"
            "画面质感：木纹低亮反光。\n光效与曝光：窗光落在桌面并保持稳定。\n"
            "动态美学：稳定起幅，手机提示触发视线，尾部停稳。\n"
            "表演与情绪：提示触发她抬眼，手指泄露停顿，余波停在手机。\n"
            "穿帮控制：手机背面朝镜头。\n抽卡策略：高风险，文字默认后期。\n"
            "蒙太奇与剪辑：非蒙太奇，保持连续。\n\n"
            "【本镜必要约束｜直接复制】\n气泡不属于手机，不贴手机。\n\n"
            "【本镜补充负面提示词｜直接复制】\n聊天气泡贴手机。"
        )
        issues: list[str] = []
        validator.validate_child("S1-01", 1, "1，3s，复杂。", block, ["她"], issues)
        self.assertTrue(any("精确UI默认后期叠加" in issue for issue in issues), issues)

    def test_keyframe_pair_counts_as_one_optional_function(self) -> None:
        block = (
            "【关键帧生图提示】\n首帧：人物站定。\n\n"
            "【即梦视频提示｜配合关键帧】\n人物抬手。\n\n"
            "【本镜必要约束｜直接复制】\n人物保持原位。"
        )
        self.assertEqual(2, validator.optional_function_count(block))

    def test_passive_water_change_does_not_create_silent_causality(self) -> None:
        prompt = "她用粗布擦过脸颊，水珠被带走一部分，摄影机固定记录动作。"
        self.assertNotEqual("silent_causal", validator.detect_shot_type(prompt))

    def test_high_risk_transition_reports_missing_chain(self) -> None:
        prompt = "16:9，3D CG，客厅暖光，平视中景，镜头固定。她递出卡片，画面停在两人之间。"
        report = validator.build_semantic_report(prompt, cast_names=["她", "对方"])
        self.assertEqual("high_risk_transition", report.shot_type)
        self.assertIn("起点到终态转换链", report.missing_slots)
        self.assertIn("道具接触", report.missing_slots)
        self.assertIn("原持有人释放", report.missing_slots)

    def test_cutaway_validation_does_not_require_body_facing(self) -> None:
        block = (
            "【镜号】\n1，2s，普通。\n\n"
            "【画面描述｜直接复制】\n"
            "16:9，3D自然电影CG，旧厨房暖黄窗光落在木纹桌面，木纹反光很弱。"
            "本镜画面内可见人数：0人，空镜只拍桌面杯水，俯视特写，镜头固定，杯子居中；"
            "门外脚步声停下后水纹扩散一次再减弱，画面停在平静杯面。\n\n"
            "【表演与声音】\n无台词，保留门外脚步声。\n\n"
            "【状态继承】\n杯子仍在桌面中央，水面恢复平静。\n\n"
            "【剪辑衔接】\n独立生成；用门外脚步声作为声桥。"
        )
        issues: list[str] = []
        validator.validate_child("S1-01", 1, "1，2s，普通。", block, [], issues)
        self.assertFalse(any("body-facing" in issue for issue in issues), issues)
        self.assertFalse(any("semantic contract incomplete" in issue for issue in issues), issues)

    def test_full_child_validation_accepts_semantically_complete_short_prompt(self) -> None:
        direct = (
            "16:9，3D自然电影CG，旧厨房暖黄窗光照在木纹墙面。平视中景，镜头固定。"
            "她发现水管漏水，身体面向墙角水阀，转身按下阀门，水流停止；"
            "她仍站在墙边，画面停在不再扩散的积水。"
        )
        self.assertLess(validator.compact_len(direct), 180)
        block = (
            "【镜号】\n1，3s，普通。\n\n"
            f"【画面描述｜直接复制】\n{direct}\n\n"
            "【表演与声音】\n无台词。\n\n"
            "【状态继承】\n她仍面向关闭的水阀，积水不再扩散。\n\n"
            "【本镜制作控制】\n"
            "画面质感：旧墙木纹受窗光，积水是唯一视觉落点。\n"
            "光效与曝光：左侧窗光照在墙面，暗部保持可读并稳定。\n"
            "动态美学：稳定起幅，漏水触发按阀，水流停止后落幅停稳。\n"
            "表演与情绪：发现漏水触发她转身，肩背泄露紧张，余波停在水阀。\n"
            "穿帮控制：右手接触水阀，双脚接地，积水边界稳定。\n"
            "抽卡策略：低风险，固定机位并只保留一次转身按阀。\n"
            "蒙太奇与剪辑：非蒙太奇，完整保留原因到结果。"
        )
        issues: list[str] = []
        validator.validate_child("S1-01", 1, "1，3s，普通。", block, ["她"], issues)
        self.assertFalse(any("semantic contract incomplete" in issue for issue in issues), issues)
        self.assertFalse(any("too thin" in issue for issue in issues), issues)

    @staticmethod
    def _liveness_group(prompts: list[str]) -> str:
        children = []
        for index, prompt in enumerate(prompts, start=1):
            children.append(
                f"【镜号】\n{index}，3s，普通。\n\n"
                "【画面描述｜直接复制】\n"
                f"16:9，现代自然剧情，客厅窗侧柔光。平视近景，{prompt}。"
                "人物完成当前动作后停稳，目光落在对话者脸上。\n\n"
                "【表演与声音】\n无台词。\n\n"
                "【状态继承】\n人物位置保持稳定。\n"
            )
        text = (
            "#### S1-01｜镜头组总时长：9s\n\n"
            "【出现人物】\n甲\n\n"
            + "\n".join(children)
        )
        return text

    def test_shadow_groups_paraphrased_liveness_devices(self) -> None:
        text = self._liveness_group(["镜头缓慢推近", "摄影机轻推0.2米", "镜头小幅推进后停稳"])

        diagnostics = validator.shadow_validate(Path("dummy.md"), text)

        self.assertTrue(
            any("liveness_family_repeat=camera_push/3" in diagnostic for diagnostic in diagnostics),
            diagnostics,
        )

    def test_shadow_does_not_report_two_matches_or_distinct_causal_motion(self) -> None:
        text = self._liveness_group([
            "镜头缓慢推近",
            "摄影机轻推0.2米",
            "镜头固定，杯底落桌后水纹扩散两次再减弱",
        ])

        diagnostics = validator.shadow_validate(Path("dummy.md"), text)

        self.assertFalse(any("liveness_family_repeat=" in item for item in diagnostics), diagnostics)

    def test_character_light_push_is_not_camera_push(self) -> None:
        text = self._liveness_group(["她轻推木门", "她轻推杯子", "她轻推对方手背"])

        diagnostics = validator.shadow_validate(Path("dummy.md"), text)

        self.assertFalse(any("camera_push" in item for item in diagnostics), diagnostics)

    def test_shadow_groups_other_paraphrased_liveness_families(self) -> None:
        cases = {
            "generic_eye": ["人物轻微眨眼", "人物眼睫轻颤", "人物眼皮微动"],
            "generic_brow": ["人物微微皱眉", "人物轻蹙眉", "人物眉心微收"],
            "idle_fabric": ["衣摆轻动", "衣袖轻摆", "衣角轻晃"],
            "generic_haze": ["后景薄雾", "背景轻雾", "雾气缓慢流动"],
        }
        for family, prompts in cases.items():
            with self.subTest(family=family):
                diagnostics = validator.shadow_validate(
                    Path("dummy.md"), self._liveness_group(prompts)
                )
                self.assertTrue(
                    any(f"liveness_family_repeat={family}/3" in item for item in diagnostics),
                    diagnostics,
                )

    def test_liveness_reference_is_routed_without_new_output_fields(self) -> None:
        root = Path(__file__).resolve().parents[1]
        grammar = (root / "references" / "liveness-motion-grammar.md").read_text(encoding="utf-8")
        runtime = (root / "references" / "runtime-brief.md").read_text(encoding="utf-8")
        visual = (root / "references" / "visual-attraction-rules.md").read_text(encoding="utf-8")
        self.assertIn("动力源 | 起始静止锚点 | 主体触发", grammar)
        self.assertIn("liveness-motion-grammar.md", runtime)
        self.assertIn("liveness-motion-grammar.md", visual)
        self.assertIn("不增加模板字段", grammar)

    def test_visual_profile_uses_evidence_scoring_and_conservative_fallback(self) -> None:
        root = Path(__file__).resolve().parents[1]
        profiles = (root / "references" / "visual-direction-profiles.md").read_text(encoding="utf-8")
        for routing_fact in (
            "多证据自动适配",
            "evidence_score",
            "narrative_modifier",
            "period_court_cinematic",
            "rural_lived_in_naturalism",
            "现代夜景不自动加入霓虹",
            "低置信回到通用电影化默认",
        ):
            self.assertIn(routing_fact, profiles)


if __name__ == "__main__":
    unittest.main()
