#!/usr/bin/env python3
"""Regression tests for storyboard validation and shadow semantic profiling."""

import re
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

    def test_unlisted_negative_visual_prior_is_rejected(self) -> None:
        issues = validator.negative_priming_issues("人物不要厨师帽，背景不是餐厅。")
        self.assertTrue(any("厨师帽" in issue and "餐厅" in issue for issue in issues), issues)

    def test_artifact_negative_controls_are_not_visual_priors(self) -> None:
        text = "不新增人物，不重复主体，避免画面闪烁，人物肢体不穿模。"
        self.assertEqual([], validator.negative_priming_issues(text))
        global_negative = "换脸、穿模、口型错位、背景重构、人物瞬移、模糊失焦、透视错乱、强光晕、过量粒子"
        self.assertEqual([], validator.negative_priming_issues(global_negative, negative_field=True))

    def test_unlisted_concept_in_negative_field_is_rejected(self) -> None:
        issues = validator.negative_priming_issues("换脸、穿模、厨师帽、餐厅", negative_field=True)
        self.assertTrue(any("厨师帽" in issue and "餐厅" in issue for issue in issues), issues)

    def test_explicit_timing_windows_require_full_non_overlapping_coverage(self) -> None:
        valid = "0.0-0.5秒锁位\n0.5-2.5秒台词\n2.5-3.0秒闭口余波"
        self.assertEqual([], validator.explicit_timing_window_issues(valid, 3.0))
        underfill = validator.explicit_timing_window_issues("0.0-1.0秒台词\n1.5-3.0秒余波", 3.0)
        self.assertTrue(any("时间空档" in issue for issue in underfill), underfill)
        overflow = validator.explicit_timing_window_issues("0.0-3.2秒台词", 3.0)
        self.assertTrue(any("越过镜头时长" in issue for issue in overflow), overflow)
        overlap = validator.explicit_timing_window_issues("0.0-2.0秒台词\n1.8-3.0秒反应", 3.0)
        self.assertTrue(any("未声明重叠" in issue for issue in overlap), overlap)

    def test_relative_timing_does_not_trigger_numeric_coverage_gate(self) -> None:
        self.assertEqual([], validator.explicit_timing_window_issues("开口前停半拍，句末留短余波", 3.0))
        self.assertEqual([], validator.explicit_timing_window_issues("句末留0.2-0.4秒停顿", 3.0))

    def test_state_cannot_invent_actor_prop_or_screen_side(self) -> None:
        direct = "甲站在画面左侧，身体面向乙，乙站在画面右侧，身体面向甲。"
        state = "甲站在画面右侧，身体面向乙，右手握住钥匙；丙留在门外侧。"
        issues = validator.state_grounding_issues(direct, state, ["甲", "乙", "丙"])
        self.assertTrue(any("丙" in issue and "人物" in issue for issue in issues), issues)
        self.assertTrue(any("钥匙" in issue for issue in issues), issues)
        self.assertTrue(any("甲" in issue and "画面侧" in issue for issue in issues), issues)

    def test_state_may_repeat_grounded_end_facts(self) -> None:
        direct = (
            "甲站在画面左侧，身体面向乙，从桌面拿起钥匙；最后20%甲右手握住钥匙，"
            "仍停在画面左侧，身体面向乙。"
        )
        state = "甲右手握住钥匙，仍停在画面左侧，身体面向乙。"
        self.assertEqual([], validator.state_grounding_issues(direct, state, ["甲", "乙"]))


class SpatialFacingContractTests(unittest.TestCase):
    def test_each_visible_actor_requires_a_complete_spatial_contract(self) -> None:
        prompt = (
            "摄影机位于长桌南侧，朝桌北侧拍摄，保持在二人关系轴同一侧。"
            "沈青乔站在画面左侧，身体面向卫景耘，侧面可见，视线落在卫景耘脸上；"
            "卫景耘站在画面右侧，闭口不动。"
        )
        issues = validator.spatial_facing_issues(prompt, ["沈青乔", "卫景耘"])
        self.assertTrue(any("卫景耘缺少身体面向" in issue for issue in issues), issues)
        self.assertTrue(any("卫景耘缺少摄影机可见面" in issue for issue in issues), issues)
        self.assertTrue(any("卫景耘缺少视线目标" in issue for issue in issues), issues)

    def test_complete_two_person_spatial_contract_passes(self) -> None:
        prompt = (
            "摄影机位于长桌南侧，朝桌北侧拍摄，保持在沈青乔与卫景耘关系轴同一侧。"
            "沈青乔站在画面左侧，身体面向卫景耘，三分之二侧面可见，视线落在卫景耘脸上；"
            "卫景耘站在画面右侧，身体面向沈青乔，三分之二侧面可见，视线落在沈青乔脸上。"
        )
        self.assertEqual([], validator.spatial_facing_issues(prompt, ["沈青乔", "卫景耘"]))

    def test_doorway_back_front_relationship_is_valid(self) -> None:
        prompt = (
            "摄影机位于门外院地，朝屋内拍摄，保持在沈青乔与卫景耘关系轴同一侧。"
            "沈青乔站在门槛外侧前景，背对摄影机，"
            "身体、胸口和脚尖面向卫景耘；卫景耘始终站在门槛内侧后景，身体和正面朝向沈青乔，"
            "正面和双肩可见。沈青乔视线落在卫景耘脸上，卫景耘视线落在沈青乔脸上。"
            "二人相互面对。沈青乔背影只遮挡卫景耘左侧下半身，"
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
            "摄影机位于二人南侧，朝北拍摄，保持在甲与乙关系轴同一侧。"
            "甲站在画面左侧，身体、胸口和脚尖面向乙，三分之二侧面可见；"
            "乙站在画面右侧，身体、胸口和脚尖面向甲，三分之二侧面可见，两人对峙。"
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

    def test_hatch_boundary_uses_same_side_visible_plane_contract(self) -> None:
        prompt = (
            "摄影机位于舱门外侧，朝舱内拍摄，保持在甲与乙关系轴同一侧。"
            "甲站在舱门外侧，身体、胸口和脚尖面向乙，正面可见，视线落在乙；"
            "乙站在舱门内侧，身体、胸口和脚尖面向甲，正面可见，视线落在甲。两人对峙。"
        )
        issues = validator.spatial_facing_issues(prompt, ["甲", "乙"])
        self.assertTrue(any("舱门同侧" in issue and "正面可见" in issue for issue in issues), issues)
        self.assertFalse(any("门槛同侧" in issue for issue in issues), issues)

    def test_elevator_boundary_requires_each_actor_side(self) -> None:
        prompt = (
            "摄影机位于候梯厅，朝轿厢内拍摄，保持在甲与乙关系轴同一侧。"
            "甲站在候梯厅，身体面向乙，背面可见，视线落在乙；"
            "乙站在画面右侧，身体面向甲，正面可见，视线落在甲。两人对峙。"
        )
        issues = validator.spatial_facing_issues(prompt, ["甲", "乙"])
        self.assertTrue(any("电梯边界关系镜" in issue and "乙" in issue for issue in issues), issues)

    def test_actor_cannot_occupy_both_boundary_sides_without_crossing(self) -> None:
        prompt = (
            "摄影机位于舱门外侧，朝舱内拍摄，保持在甲与乙关系轴同一侧。"
            "甲同时站在舱门内侧和舱门外侧，身体面向乙，侧面可见，视线落在乙；"
            "乙站在舱门内侧，身体面向甲，正面可见，视线落在甲。两人对峙。"
        )
        issues = validator.spatial_facing_issues(prompt, ["甲", "乙"])
        self.assertTrue(any("甲同时位于舱门两侧" in issue for issue in issues), issues)

    def test_actor_cannot_have_mutually_exclusive_screen_or_plane_facts(self) -> None:
        base = "摄影机位于长桌南侧，朝北拍摄，保持在甲与乙关系轴同一侧。"
        tail = "乙站在画面右侧，身体面向甲，侧面可见，视线落在甲。两人对峙。"
        plane = base + "甲站在画面左侧，身体面向乙，正面可见且背面可见，视线落在乙；" + tail
        side = base + "甲同时站在画面左侧和画面右侧，身体面向乙，侧面可见，视线落在乙；" + tail
        self.assertTrue(any("正面和背面" in issue for issue in validator.spatial_facing_issues(plane, ["甲", "乙"])))
        self.assertTrue(any("画面左侧和右侧" in issue for issue in validator.spatial_facing_issues(side, ["甲", "乙"])))

    def test_actor_cannot_face_and_turn_back_to_same_person(self) -> None:
        prompt = (
            "摄影机位于长桌南侧，朝北拍摄，保持在甲与乙关系轴同一侧。"
            "甲站在画面左侧，身体面向乙并背对乙，侧面可见，视线落在乙；"
            "乙站在画面右侧，身体面向甲，侧面可见，视线落在甲。两人对峙。"
        )
        issues = validator.spatial_facing_issues(prompt, ["甲", "乙"])
        self.assertTrue(any("同时面向并背对乙" in issue for issue in issues), issues)

    def test_generic_boundary_background_must_match_camera_direction(self) -> None:
        prompt = (
            "摄影机位于舱门外侧，朝舱内拍摄，保持在甲与乙关系轴同一侧。"
            "甲站在舱门外侧，身体面向乙，背面可见，视线落在乙；"
            "乙站在舱门内侧，身体面向甲，正面可见，视线落在甲。"
            "舱外星空作为后景，两人对峙。"
        )
        issues = validator.spatial_facing_issues(prompt, ["甲", "乙"])
        self.assertTrue(any("外侧空间在摄影机身后" in issue for issue in issues), issues)

    def test_generic_boundary_crossing_requires_start_cross_and_end(self) -> None:
        malformed = "甲进入舱内，直接停在舱门内侧，身体面向舱内。"
        issues = validator.spatial_facing_issues(malformed, ["甲"])
        self.assertTrue(any("完整可见动作链" in issue for issue in issues), issues)
        valid = "甲从舱门外侧起步，跨过舱门进入舱门内侧，最终停在舱内，身体面向舱内。"
        self.assertEqual([], validator.spatial_facing_issues(valid, ["甲"]))

    def test_return_home_requires_threshold_crossing_chain(self) -> None:
        prompt = "沈青乔回家，直接停在门槛内侧。"
        issues = validator.spatial_facing_issues(prompt, ["沈青乔"])
        self.assertTrue(any("完整可见动作链" in issue for issue in issues), issues)

    def test_similar_props_require_visible_distinction(self) -> None:
        issues = validator.spatial_facing_issues("沈青乔和阿丰各提一个竹篮，双竹篮归属固定。", ["沈青乔", "阿丰"])
        self.assertTrue(any("同类道具" in issue for issue in issues), issues)

    def test_unlisted_similar_props_use_generic_detection(self) -> None:
        issues = validator.spatial_facing_issues("甲和乙各持一把纸伞，两把纸伞归属固定。", ["甲", "乙"])
        self.assertTrue(any("同类道具" in issue for issue in issues), issues)

    def test_unlisted_prop_state_is_tracked_without_a_prop_dictionary(self) -> None:
        previous = "铜铃停在甲右手，甲站在门边。"
        current = "铜铃放在桌面，甲仍站在门边。"
        self.assertEqual(["铜铃"], validator.prop_state_jump(previous, current))

    def test_camera_signature_distinguishes_angle(self) -> None:
        overhead = validator.camera_signature("俯视近景，镜头固定。")
        oblique = validator.camera_signature("斜俯近景，镜头固定。")
        self.assertNotEqual(overhead, oblique)

    def test_adjacent_relation_shots_reject_unexplained_screen_side_flip(self) -> None:
        previous = (
            "摄影机位于长桌南侧，朝桌北侧拍摄，保持在甲与乙关系轴同一侧。"
            "甲站在画面左侧，身体面向乙，侧面可见，视线落在乙；"
            "乙站在画面右侧，身体面向甲，侧面可见，视线落在甲。"
        )
        current = (
            "摄影机位于长桌北侧，朝桌南侧拍摄。"
            "甲站在画面右侧，身体面向乙，侧面可见，视线落在乙；"
            "乙站在画面左侧，身体面向甲，侧面可见，视线落在甲。"
        )
        issues = validator.axis_continuity_issues(previous, current, ["甲", "乙"])
        self.assertTrue(any("屏幕方向翻转" in issue for issue in issues), issues)

    def test_axis_crossing_requires_visible_neutral_transition(self) -> None:
        previous = (
            "摄影机位于长桌南侧，朝桌北侧拍摄，保持在甲与乙关系轴同一侧。"
            "甲在画面左侧，乙在画面右侧。"
        )
        current = (
            "摄影机从长桌南侧横移越过甲乙关系轴到北侧，经过二人正侧面的中性机位，"
            "画面连续展示甲乙屏幕方向交换。"
        )
        self.assertEqual([], validator.axis_continuity_issues(previous, current, ["甲", "乙"]))

    def test_physical_camera_side_flip_is_rejected_without_screen_side_labels(self) -> None:
        previous = (
            "摄影机位于长桌南侧，朝北拍摄，保持在甲与乙关系轴同一侧。"
            "甲站在桌边，身体面向乙，侧面可见，视线落在乙；"
            "乙站在桌对面，身体面向甲，侧面可见，视线落在甲。两人对峙。"
        )
        current = previous.replace("长桌南侧，朝北", "长桌北侧，朝南")
        issues = validator.axis_continuity_issues(previous, current, ["甲", "乙"])
        self.assertTrue(any("物理对侧" in issue for issue in issues), issues)


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

    def test_time_aliases_are_normalized(self) -> None:
        self.assertEqual({"night"}, validator.time_state_signature("子夜洞窟"))
        self.assertEqual({"dawn"}, validator.time_state_signature("破晓山门"))
        self.assertEqual({"dusk"}, validator.time_state_signature("暮色庭院"))

    def test_unlisted_physical_light_source_is_accepted_and_tracked(self) -> None:
        prompt = (
            "子夜洞窟，无可见天光，熔岩为唯一主光源，红光照亮岩壁和人物侧脸；"
            "最后20%背景亮度、主光方向、色温和曝光保持到结束。"
        )
        self.assertEqual([], validator.temporal_lighting_issues(prompt))
        self.assertIn("source:熔岩", validator.primary_light_sources(prompt))
        issues = validator.temporal_lighting_continuity_issues(
            prompt,
            "子夜洞窟，无可见天光，荧光植物为唯一主光源，曝光保持到结束。",
        )
        self.assertTrue(any("主光源冲突" in issue for issue in issues), issues)

    def test_generic_prop_transfer_triggers_keyframes(self) -> None:
        for prop in ("铜铃", "纸伞", "玉佩"):
            reasons = validator.keyframe_trigger_reasons(f"甲把{prop}递给乙。", "1，5s，普通。")
            self.assertIn("道具/衣物转移或签字付款", reasons, prop)

    def test_unlisted_light_and_material_count_as_executable_visual_detail(self) -> None:
        self.assertTrue(validator.has_executable_visual_detail("熔岩承担主光，红光照亮岩壁裂纹。"))
        self.assertTrue(validator.has_executable_visual_detail("玉石表面哑光磨损清晰可见。"))

    def test_unlisted_boundary_crossing_triggers_keyframes(self) -> None:
        reasons = validator.keyframe_trigger_reasons(
            "甲从结界外侧穿过结界进入结界内侧。", "1，5s，普通。"
        )
        self.assertIn("门车门/电梯空间穿越", reasons)


class OutputFormatTests(unittest.TestCase):
    @staticmethod
    def _memory_anchor_fixture() -> tuple[str, str]:
        direct = (
            "门框隔开两人且旧钥匙停在中间，门框把甲与乙分在门外和门内；"
            "第一眼落在旧钥匙裂纹，甲握紧旧钥匙的指节发白，二人由试探转为对峙。"
        )
        control = (
            "画面质感：门框分割构图，焦点在旧钥匙与二人距离；"
            "记忆锚点：门框把甲与乙分在门外和门内，旧钥匙停在两人之间；"
            "第一眼焦点：旧钥匙裂纹；"
            "成立原因：门框和旧钥匙同时把进入与拒绝变成可见关系；"
            "情绪载体：甲握紧旧钥匙的指节发白；"
            "关系/认知变化：二人由试探转为对峙；"
            "相邻差异：观众位置改为门外受阻视点，关系几何由同侧变成门框两侧，视觉载体由人物脸转为旧钥匙；"
            "不可降级核心：门框隔开两人且旧钥匙停在中间。"
        )
        return direct, control

    def test_memory_anchor_requires_complete_specific_contract(self) -> None:
        direct, control = self._memory_anchor_fixture()
        self.assertEqual([], validator.memory_anchor_contract_issues(control, direct))
        malformed = "画面质感：记忆锚点：很震撼；成立原因：高级感。"
        issues = validator.memory_anchor_contract_issues(malformed, direct)
        self.assertTrue(any("过于空泛" in issue for issue in issues), issues)
        self.assertTrue(any("合同缺少关系/认知变化" in issue for issue in issues), issues)

    def test_signature_shot_requires_three_adjacent_difference_dimensions(self) -> None:
        direct, control = self._memory_anchor_fixture()
        weak = re.sub(
            r"相邻差异：.*?；不可降级核心：",
            "相邻差异：只改变机位；不可降级核心：",
            control,
        )
        issues = validator.memory_anchor_contract_issues(weak, direct)
        self.assertTrue(any("至少三个维度" in issue for issue in issues), issues)

    def test_memory_anchor_visible_fact_must_reach_direct_prompt(self) -> None:
        _, control = self._memory_anchor_fixture()
        issues = validator.memory_anchor_contract_issues(
            control, "普通平视中景，甲与乙站立交谈。"
        )
        self.assertTrue(any("未转译进直接提示词" in issue for issue in issues), issues)

    def test_signature_relationship_change_must_reach_direct_prompt(self) -> None:
        direct, control = self._memory_anchor_fixture()
        without_change = direct.replace("二人由试探转为对峙。", "二人隔门站定。")
        issues = validator.memory_anchor_contract_issues(control, without_change)
        self.assertTrue(any("关系/认知变化未转译" in issue for issue in issues), issues)

    def test_signature_core_must_finish_in_first_sixty_percent(self) -> None:
        direct, control = self._memory_anchor_fixture()
        core = "门框隔开两人且旧钥匙停在中间"
        late = direct.replace(core + "，", "")
        late = late.replace(
            "二人由试探转为对峙。",
            "二人由试探转为对峙，土墙、门板、衣褶、地面和背景保持清晰稳定；" + core + "。",
        )
        issues = validator.memory_anchor_contract_issues(control, late)
        self.assertTrue(any("前60%" in issue for issue in issues), issues)

    def test_memory_anchor_rejects_production_meta_language_in_direct_prompt(self) -> None:
        direct, control = self._memory_anchor_fixture()
        issues = validator.memory_anchor_contract_issues(
            control, direct + "观众看清两人关系。"
        )
        self.assertTrue(any("制作意图" in issue for issue in issues), issues)

    def test_every_rolling_five_shot_window_requires_an_anchor(self) -> None:
        direct, control = self._memory_anchor_fixture()
        no_anchor = [(1, f"S1-0{i + 1}-1", "普通镜头", "") for i in range(5)]
        issues = validator.memory_anchor_density_issues(no_anchor)
        self.assertTrue(any("连续五镜缺少有效签名镜头" in issue for issue in issues), issues)

        one_anchor = list(no_anchor)
        one_anchor[2] = (1, "S1-03-1", direct, control)
        self.assertEqual([], validator.memory_anchor_density_issues(one_anchor))

    def test_signature_claim_cannot_hide_an_unchanged_adjacent_prompt(self) -> None:
        direct, control = self._memory_anchor_fixture()
        records = [(1, f"S1-0{i + 1}-1", direct, control if i == 2 else "") for i in range(5)]
        issues = validator.memory_anchor_density_issues(records)
        self.assertTrue(any("实际差异不足三类" in issue for issue in issues), issues)

    def test_signature_actual_neighbor_difference_requires_three_categories(self) -> None:
        signature = "50mm平视中近景，三角构图，焦点落在甲双眼，摄影机固定。"
        neighbor = "50mm平视中近景，中央构图，焦点落在甲双眼，摄影机缓慢推近。"
        self.assertEqual(2, validator.signature_neighbor_difference_count(signature, neighbor))
        self.assertLess(
            validator.signature_neighbor_difference_count(signature, neighbor),
            validator.SIGNATURE_MIN_NEIGHBOR_DIFFERENCES,
        )

    def test_anchor_spacing_must_cover_all_rolling_windows(self) -> None:
        direct, control = self._memory_anchor_fixture()
        records = [(1, f"S1-{i + 1:02d}-1", "普通镜头", "") for i in range(6)]
        records[0] = (1, "S1-01-1", direct, control)
        issues = validator.memory_anchor_density_issues(records)
        self.assertTrue(any("S1-02-1~S1-06-1" in issue for issue in issues), issues)

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

    def test_global_scale_gate_accepts_semantic_equivalents(self) -> None:
        wording = (
            "人物骨架保持稳定，真实身高与体型固定；四肢长度全程不变，关节位置稳定；"
            "空间透视和消失点固定；身体支撑持续接触承载面；站立时脚底落地，"
            "行走时步态连续，坐姿时臀背接触座面；腾空保持离地、空中轨迹到着地连续；"
            "人物身高差与相对尺寸一致；画面占比随物理距离平滑变化，固定距离时投影尺度不变。"
        )
        self.assertEqual([], validator.missing_global_scale_concepts(wording))

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
            "左侧窗光照亮脸和手，阴影保留细节，高光稳定。人物身体面向门口，右手压住桌沿，"
            "双脚接地，道具仍在桌面右侧；听见开门声后保持戒备但对外平静，随后抬眼，"
            "呼吸停顿，眼神停在门口形成余波。"
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

    def test_shot_quality_control_rejects_semantic_subject_and_target_mismatch(self) -> None:
        control = (
            "画面质感：门框构图，焦点锁甲右脸、铜铃裂纹和墙面纹理。\n"
            "光效与曝光：右侧壁灯为主光，照亮甲右脸和铜铃裂纹，曝光稳定。\n"
            "动态美学：固定起幅，相见触发二人停步，固定机位稳定落幅。\n"
            "表演与情绪：看见来人触发甲指节压紧铜铃提环，余波停在门内距离。\n"
            "穿帮控制：可见人数2人，铜铃归甲，脚底保持支撑。\n"
            "抽卡策略：高风险，固定机位，自动首轮检查。\n"
            "蒙太奇与剪辑：非蒙太奇，以脚步声停止为切点。"
        )
        direct = (
            "门框构图，焦点在乙双眼，右侧壁灯为主光并照亮乙脸部；"
            "二人看见彼此后停步，乙肩背僵住。固定机位稳定落幅，"
            "可见人数2人，人物槽位、道具归属和脚底支撑固定。"
        )
        issues = validator.quality_control_issues(control, direct, ["甲", "乙"])
        self.assertTrue(any("画面质感" in issue and "甲" in issue for issue in issues), issues)
        self.assertTrue(any("光效与曝光" in issue and "铜铃" in issue for issue in issues), issues)
        self.assertTrue(any("表演与情绪" in issue and "铜铃提环" in issue for issue in issues), issues)

    def test_keyframe_contract_rejects_time_light_and_spatial_drift(self) -> None:
        direct = (
            "夜晚小院屋内，右侧油灯为主光源并承担曝光，门外保持深蓝黑位。"
            "摄影机位于门槛外侧朝屋内拍摄，保持在沈青乔与卫景耘关系轴同一侧。"
            "本镜画面内可见人数：2人。沈青乔站在门槛外侧画面左侧，身体面向卫景耘，"
            "背面可见，视线落在卫景耘；卫景耘站在门槛内侧画面右侧，身体面向沈青乔，"
            "正面可见，视线落在沈青乔。"
        )
        keyframes = (
            "首帧：白天小院，日光为主光，沈青乔站在门槛内侧，卫景耘站在门外。\n"
            "尾帧：同一机位，二人停住。"
        )
        issues = validator.keyframe_contract_issues(
            keyframes, direct, ["沈青乔", "卫景耘"]
        )
        self.assertTrue(any("时段" in issue for issue in issues), issues)
        self.assertTrue(any("主光源" in issue for issue in issues), issues)
        self.assertTrue(any("空间合同" in issue for issue in issues), issues)

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

    def test_split_scene_file_keeps_its_global_scene_number(self) -> None:
        text = "#### S2-01｜镜头组总时长：2s\n\n【出现人物】\n甲\n"
        issues = validator.validate(Path("项目_S2_客厅_即梦投喂分镜.md"), text)
        self.assertFalse(any("首个镜头组必须为" in issue for issue in issues))

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

    def test_fixed_dialogue_rate_is_shadow_advice_only(self) -> None:
        direct = (
            "16:9，3D自然电影CG，客厅窗光照亮人物正脸。平视近景，镜头固定。"
            "甲开口说：“这是一句明显超过两秒估算容量的可见对白。”说完闭口，乙听见后抬眼。"
        )
        block = (
            "【镜号】\n1，2s，普通。\n\n"
            f"【画面描述｜直接复制】\n{direct}\n\n"
            "【表演与声音】\n甲说完闭口，乙闭口听。\n\n"
            "【状态继承】\n甲乙仍相对站立。\n\n"
            "【本镜制作控制】\n"
        )
        issues: list[str] = []
        validator.validate_child("S1-01", 1, "1，2s，普通。", block, ["甲", "乙"], issues)
        self.assertFalse(any("visible dialogue duration too short" in issue for issue in issues), issues)
        text = "#### S1-01｜镜头组总时长：2s\n\n【出现人物】\n甲\n乙\n\n" + block
        diagnostics = validator.shadow_validate(Path("dummy.md"), text)
        self.assertTrue(any("dialogue_rate_estimate=" in item and "advisory_only=true" in item for item in diagnostics), diagnostics)

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

    def test_direct_prompt_hard_limits_follow_complexity_and_keyframes(self) -> None:
        self.assertEqual(500, validator.direct_prompt_hard_limit("1，4s，普通。"))
        self.assertEqual(650, validator.direct_prompt_hard_limit("1，4s，复杂。"))
        self.assertEqual(
            700,
            validator.direct_prompt_hard_limit("1，4s，复杂。", "首帧...尾帧", "0-4s..."),
        )

    def test_validate_child_applies_each_prompt_ceiling(self) -> None:
        def length_issues(length: int, complexity: str, keyframed: bool = False) -> list[str]:
            optional = ""
            if keyframed:
                optional = (
                    "\n【关键帧生图提示】\n首帧：甲站定。尾帧：甲站定。\n"
                    "\n【即梦视频提示｜配合关键帧】\n0-4s：甲保持站定。\n"
                )
            block = (
                f"【镜号】\n1，4s，{complexity}。\n\n"
                f"【画面描述｜直接复制】\n{'甲' * length}\n\n"
                "【表演与声音】\n无台词。\n\n"
                "【状态继承】\n甲保持站定。\n\n"
                "【本镜制作控制】\n画面质感：甲。\n光效与曝光：甲。\n动态美学：甲。\n"
                "表演与情绪：甲。\n穿帮控制：甲。\n抽卡策略：甲。\n蒙太奇与剪辑：甲。\n"
                + optional
            )
            issues: list[str] = []
            validator.validate_child("S1-01", 1, f"1，4s，{complexity}。", block, ["甲"], issues)
            return [issue for issue in issues if "direct prompt over" in issue]

        self.assertEqual([], length_issues(500, "普通"))
        self.assertTrue(length_issues(501, "普通"))
        self.assertEqual([], length_issues(650, "复杂"))
        self.assertTrue(length_issues(651, "复杂"))
        self.assertEqual([], length_issues(700, "复杂", keyframed=True))
        self.assertTrue(length_issues(701, "复杂", keyframed=True))

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
