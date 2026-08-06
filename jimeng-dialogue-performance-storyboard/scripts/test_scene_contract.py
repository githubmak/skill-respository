#!/usr/bin/env python3
"""Regression tests for compact internal scene contracts."""

from __future__ import annotations

import copy
import unittest
import tempfile
from pathlib import Path

from scene_contract import compile_contract, completeness_issues, load_contract, recovery_issues, validate_contract


CONTRACT = {
    "version": 1,
    "scene_id": "S1",
    "risk_vector": ["critical_performance_turn", "boundary"],
    "tone_card": {
        "emotional_function": "门槛边界的拒绝压力",
        "dominant_palette": "暖褐主色",
        "support_palette": "浅木棕辅助",
        "accent_palette": "琥珀小面积点缀",
        "temperature": "3200K暖调",
        "key_light": "右侧油灯主光",
        "shadow_tone": "暖棕阴影",
        "contrast_saturation": "中对比中低饱和",
        "background_brightness": "门外深蓝黑位、背景低亮",
        "skin_protection": "自然偏暖肤色，脸部受光均匀",
        "material_anchor": "木门框哑光纹理",
        "allowed_variation": "拒绝峰值局部压暗",
        "forbidden_contamination": "禁止全场泛绿、肤色青灰",
    },
    "shots": [{
        "shot_id": "S1-01-1",
        "performance": {
            "source_anchor": "沈青乔说别进来",
            "relationship_goal": "阻止卫景耘进入",
            "speaker_actor": "沈青乔",
            "speaker_visible_fact": "沈青乔右手压住门框",
            "listener_actor": "卫景耘",
            "listener_trigger": "听到别进来后",
            "listener_visible_fact": "卫景耘脚步停在门槛内侧",
            "end_residue": "沈青乔右手仍压住门框",
            "readability": "中近景看清手与门框",
            "camera_service": "沈青乔肩后机位看清卫景耘停步",
            "emotional_cause": "卫景耘试图进入门槛",
            "speaker_strategy": "沈青乔用右手压住门框阻止进入",
            "speaker_leak": "沈青乔右手仍压住门框",
            "listener_strategy_shift": "卫景耘从前进转为脚步停在门槛内侧",
        },
        "visual_core": {
            "first_focus": "第一焦点是压住门框的右手",
            "core_fact": "门框把两人隔在门外与屋内",
            "end_image": "两人隔着门槛停住",
        },
        "spatial": {"blocking_id": "B1"},
        "protected_facts": ["沈青乔门外，卫景耘屋内"],
    }],
}


MARKDOWN = """#### S1-01｜镜头组总时长：4s

【出现人物】
沈青乔
卫景耘

【镜号】
1，4s，普通。

【画面描述｜直接复制】
16:9现代写实，暖褐主色，3200K暖调，右侧油灯是主光，暖棕阴影，肤色自然偏暖且脸部受光均匀；夜晚室内门口，中近景看清手与门框，沈青乔门外、卫景耘屋内。卫景耘试图进入门槛，沈青乔用右手压住门框阻止卫景耘进入；第一焦点落在沈青乔压住门框的右手；沈青乔肩后固定机位看清卫景耘。沈青乔说：“别进来。”卫景耘听到“别进来”后从前进转为脚步停在门槛内侧。门框把两人隔在门外与屋内。最后两人隔着门槛停住，沈青乔右手仍压住门框，镜头稳定到结束。

【表演与声音】
沈青乔说完闭口。

【状态继承】
两人隔着门槛停住。

【本镜制作控制】
画面质感：门框隔开两人。
"""


class SceneContractTests(unittest.TestCase):
    def test_valid_contract_and_prompt_recovery(self) -> None:
        normalized = validate_contract(CONTRACT)
        self.assertEqual(normalized["risk_vector"], ["critical_performance_turn", "boundary"])
        self.assertEqual(recovery_issues(CONTRACT, MARKDOWN), [])

    def test_rejects_unknown_risk_and_duplicate_shot(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown risk"):
            validate_contract({**CONTRACT, "risk_vector": ["magic"]})
        duplicate = {**CONTRACT, "shots": [CONTRACT["shots"][0], CONTRACT["shots"][0]]}
        with self.assertRaisesRegex(ValueError, "duplicate shot_id"):
            validate_contract(duplicate)

    def test_detects_lost_listener_and_terminal_residue(self) -> None:
        broken = MARKDOWN.replace("卫景耘听到“别进来”后从前进转为脚步停在门槛内侧。", "卫景耘没有明显动作。")
        broken = broken.replace("沈青乔右手仍压住门框", "沈青乔恢复自然站姿")
        issues = recovery_issues(CONTRACT, broken)
        self.assertTrue(any("listener_visible_fact" in issue for issue in issues))
        self.assertTrue(any("end_residue" in issue for issue in issues))

    def test_compiler_separates_executable_facts_from_director_analysis(self) -> None:
        contract = copy.deepcopy(CONTRACT)
        contract["camera_strategy"] = {
            "audience_position": "观众从门内看向拒绝动作",
            "movement_arc": "单镜静止观察门槛冲突",
            "static_rule": "单镜用静止保留僵持",
            "forbidden_repetition": "单镜无重复",
        }
        contract["shots"][0]["camera"] = {
            "visual_task": "看清拒绝冻结两人距离",
            "shot_size": "中近景",
            "composition": "门框分割两人",
            "mode": "static",
            "trigger": "沈青乔说别进来",
            "path": "摄影机固定在沈青乔肩后",
            "dramatic_gain": "静止放大僵持",
            "end_frame": "两人隔着门槛停住",
        }
        result = compile_contract(contract)
        self.assertTrue(result["pass"], result["issues"])
        self.assertIn("剧情情绪功能=门槛边界的拒绝压力", result["tone_card_header"])
        self.assertIn("辅助色=浅木棕辅助", result["tone_card_header"])
        self.assertIn("影调色卡句：", result["scene_tone_line"])
        self.assertIn("角色声音使用：", result["scene_tone_line"])
        shot = result["shots"][0]
        self.assertIn("沈青乔右手压住门框", shot["assembly"])
        self.assertIn("摄影机固定在沈青乔肩后", shot["assembly"])
        self.assertNotIn("看清拒绝冻结两人距离", shot["assembly"])
        self.assertIn("camera.visual_task", shot["design_only_fields"])

    def test_compiled_assembly_recovers_without_repeating_design_only_fields(self) -> None:
        contract = copy.deepcopy(CONTRACT)
        contract["camera_strategy"] = {
            "audience_position": "观众从门内看向拒绝动作",
            "movement_arc": "单镜静止观察门槛冲突",
            "static_rule": "单镜用静止保留僵持",
            "forbidden_repetition": "单镜无重复",
        }
        contract["shots"][0]["camera"] = {
            "visual_task": "不应逐字进入提示词的导演任务",
            "shot_size": "中近景",
            "composition": "不应逐字进入提示词的构图分析",
            "mode": "static",
            "trigger": "沈青乔说别进来",
            "path": "摄影机固定在沈青乔肩后",
            "dramatic_gain": "不应逐字进入提示词的收益分析",
            "end_frame": "两人隔着门槛停住",
        }
        assembly = compile_contract(contract)["shots"][0]["assembly"]
        markdown = MARKDOWN.replace(
            MARKDOWN.split("【画面描述｜直接复制】\n", 1)[1].split("\n\n【表演与声音】", 1)[0],
            "16:9现代写实，" + assembly + "沈青乔说：‘别进来。’卫景耘闭口。",
        )
        self.assertEqual(recovery_issues(contract, markdown), [])

    def test_object_shot_uses_null_performance_without_inventing_actors(self) -> None:
        contract = {
            "version": 1,
            "scene_id": "S1",
            "risk_vector": [],
            "tone_card": {
                "emotional_function": "钥匙等待",
                "dominant_palette": "暖褐主色",
                "support_palette": "浅木棕辅助",
                "accent_palette": "琥珀点缀",
                "temperature": "3200K暖调",
                "key_light": "右侧台灯主光",
                "shadow_tone": "暖棕阴影",
                "contrast_saturation": "中对比中低饱和",
                "background_brightness": "背景低亮",
                "skin_protection": "自然偏暖肤色",
                "material_anchor": "木桌纹理",
                "allowed_variation": "无",
                "forbidden_contamination": "禁止偏色",
            },
            "shots": [{
                "shot_id": "S1-01-1",
                "performance": None,
                "visual_core": {
                    "first_focus": "第一焦点是桌上的钥匙",
                    "core_fact": "钥匙停在门边桌面",
                    "end_image": "钥匙仍停在门边桌面",
                },
                "spatial": {"blocking_id": ""},
                "protected_facts": [],
            }],
        }
        markdown = """#### S1-01｜镜头组总时长：3s

【出现人物】
无

【镜号】
1，3s，普通。

【画面描述｜直接复制】
16:9写实，暖褐主色，3200K暖调，右侧台灯是主光，暖棕阴影，肤色自然偏暖；固定近景，第一焦点是桌上的钥匙，钥匙停在门边桌面。光线稳定，最后钥匙仍停在门边桌面。

【表演与声音】
无台词。
"""
        self.assertIsNone(validate_contract(contract)["shots"][0]["performance"])
        self.assertEqual(recovery_issues(contract, markdown), [])

    def test_rejects_duplicate_json_keys_in_contract_file(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "scene_contract.json"
            path.write_text('{"version": 1, "scene_id": "S1", "scene_id": "S2"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key: scene_id"):
                load_contract(path)

    def test_strict_completeness_requires_camera_strategy_and_per_shot_gain(self) -> None:
        issues = completeness_issues(CONTRACT)
        self.assertTrue(any("camera_strategy" in issue for issue in issues), issues)
        self.assertTrue(any("camera design" in issue for issue in issues), issues)

        missing_tone = copy.deepcopy(CONTRACT)
        missing_tone.pop("tone_card")
        self.assertTrue(any("tone_card is required" in issue for issue in completeness_issues(missing_tone)), issues)

        complete = copy.deepcopy(CONTRACT)
        complete["camera_strategy"] = {
            "audience_position": "观众先在门内观察，再被推向门槛冲突",
            "movement_arc": "关系镜静观，拒绝发生时短推，落幅停在边界",
            "static_rule": "只有等待回答和僵持余波使用静止",
            "forbidden_repetition": "禁止连续复制固定中景或机械微推",
        }
        complete["shots"][0]["camera"] = {
            "visual_task": "看清拒绝使两人距离冻结",
            "shot_size": "中近景",
            "composition": "沈青乔肩后门框分割两人，压门框的手位于第一焦点",
            "mode": "static",
            "trigger": "沈青乔说别进来",
            "path": "固定肩后机位观察卫景耘停步",
            "dramatic_gain": "静止放大门槛两侧的僵持压力",
            "end_frame": "两人隔着门槛停住",
        }
        self.assertEqual(completeness_issues(complete), [])

    def test_full_scene_card_cannot_replace_per_shot_tone_prefix(self) -> None:
        broken = MARKDOWN.replace(
            "暖褐主色，3200K暖调，右侧油灯是主光，暖棕阴影，肤色自然偏暖且脸部受光均匀；",
            "夜晚室内门口；",
        )
        issues = recovery_issues(CONTRACT, broken)
        self.assertTrue(any("tone_card.dominant_palette" in issue for issue in issues), issues)
        self.assertTrue(any("tone_card.temperature" in issue for issue in issues), issues)

    def test_shot_size_must_match_performance_readability(self) -> None:
        contract = copy.deepcopy(CONTRACT)
        contract["camera_strategy"] = {
            "audience_position": "观众从门内看向拒绝动作",
            "movement_arc": "单镜静止观察门槛冲突",
            "static_rule": "单镜用静止保留僵持",
            "forbidden_repetition": "单镜无重复",
        }
        contract["shots"][0]["camera"] = {
            "visual_task": "看清沈青乔压住门框的手",
            "shot_size": "全景",
            "composition": "门框把两人分在画面两侧",
            "mode": "static",
            "trigger": "沈青乔拒绝进入",
            "path": "摄影机固定在门内观察",
            "dramatic_gain": "全景显露门槛两侧距离",
            "end_frame": "两人隔着门槛停住",
        }
        issues = completeness_issues(contract)
        self.assertTrue(any("conflicts with performance.readability" in issue for issue in issues), issues)

    def test_scene_wide_static_is_rejected_for_multi_shot_scene(self) -> None:
        contract = copy.deepcopy(CONTRACT)
        contract["camera_strategy"] = {
            "audience_position": "观众始终被困在桌外，但景别和遮挡逐步收紧",
            "movement_arc": "全场不移动摄影机，以四个不同观察角度积累沉默压力",
            "static_rule": "全场静止只服务等待、观察、尴尬和最终僵持",
            "forbidden_repetition": "禁止复制同一固定中景、同一视觉任务或同一静止收益",
        }
        tasks_and_gains = [
            ("先看空椅阻断两人的视线", "静止保留空位，让等待没有出口"),
            ("改从门框后观察两人都不先开口", "静止延长沉默，形成被观察的压迫"),
            ("用桌面遮挡只留下双方停住的手", "静止困住手与道具之间的僵持"),
            ("落在两人之间仍未被拿走的钥匙", "静止把最终停顿变成关系悬念"),
        ]
        shots = []
        for index, (task, gain) in enumerate(tasks_and_gains, start=1):
            shot = copy.deepcopy(CONTRACT["shots"][0])
            shot["shot_id"] = f"S1-01-{index}"
            shot["camera"] = {
                "visual_task": task,
                "shot_size": ("全景", "中景", "近景", "特写")[index - 1],
                "composition": f"第{index}个不同观察位置与遮挡关系",
                "mode": "static",
                "trigger": f"第{index}个关系节拍落下",
                "path": f"固定在第{index}个已选观察位置",
                "dramatic_gain": gain,
                "end_frame": f"第{index}个关系结果稳定留在画面",
            }
            shots.append(shot)
        contract["shots"] = shots
        static_issues = completeness_issues(contract)
        self.assertTrue(any("entirely static" in issue for issue in static_issues), static_issues)

        lazy = copy.deepcopy(contract)
        lazy["camera_strategy"]["static_rule"] = "固定机位最安全"
        self.assertTrue(any("entirely static" in issue for issue in completeness_issues(lazy)))

        repeated = copy.deepcopy(contract)
        repeated["shots"][1]["camera"]["visual_task"] = repeated["shots"][0]["camera"]["visual_task"]
        self.assertTrue(any("entirely static" in issue for issue in completeness_issues(repeated)))

    def test_reflective_focus_requires_lighting_transport_contract(self) -> None:
        contract = copy.deepcopy(CONTRACT)
        contract["camera_strategy"] = {
            "audience_position": "观众从门内观察鱼篓和家人反应",
            "movement_arc": "先停在关系镜，再落到鱼篓",
            "static_rule": "只有鱼篓落幅有意静止",
            "forbidden_repetition": "不重复固定中景",
        }
        contract["shots"][0]["visual_core"]["first_focus"] = "第一焦点是鱼篓内湿鳞的水光"
        contract["shots"][0]["camera"] = {
            "visual_task": "让鱼篓成为关系证据",
            "shot_size": "中近景",
            "composition": "鱼篓位于关系中央，人物反应留在后景",
            "mode": "static",
            "trigger": "鱼篓水声响起",
            "path": "固定门内机位观察鱼篓",
            "dramatic_gain": "静止让家人的观察停在鱼篓",
            "end_frame": "鱼篓停在关系轴中央",
        }
        issues = completeness_issues(contract)
        self.assertTrue(any("reflective visual focus requires lighting" in issue for issue in issues), issues)

        contract["shots"][0]["lighting"] = {
            "source_entities": "月光作为主光源，火光作为辅助光源",
            "transport_path": "月光从门外斜落到鱼篓上缘",
            "material_response": "鱼身湿鳞只形成低亮反光和窄高光",
            "luminance_order": "湿鳞亮度低于人物侧脸",
            "dark_region": "篓内保持暗",
        }
        self.assertEqual(completeness_issues(contract), [])

    def test_camera_path_rejects_shared_camera_focus_prop_motion(self) -> None:
        contract = copy.deepcopy(CONTRACT)
        contract["camera_strategy"] = {
            "audience_position": "观众从菜篮证据转向听者",
            "movement_arc": "从手部证据横移到听者反应",
            "static_rule": "本镜不使用静止",
            "forbidden_repetition": "不重复横移",
        }
        contract["shots"][0]["camera"] = {
            "visual_task": "从叶片证据显露听者反应",
            "shot_size": "中近景",
            "composition": "菜篮叶片在前景，卫景耘反应在后景",
            "mode": "track",
            "trigger": "阿丰说到有毒",
            "path": "摄影机横移跟随阿丰手指从叶片落到卫景耘脸",
            "dramatic_gain": "显露卫景耘听见证据后的反应",
            "end_frame": "卫景耘与菜篮形成前后景关系",
        }
        issues = completeness_issues(contract)
        self.assertTrue(any("camera.path motion ownership is ambiguous" in issue for issue in issues), issues)

    def test_moving_camera_requires_typed_motion_ownership(self) -> None:
        contract = copy.deepcopy(CONTRACT)
        contract["camera_strategy"] = {
            "audience_position": "观众从门内观察拒绝后的距离",
            "movement_arc": "门框起幅后沿门槛横移到听者反应",
            "static_rule": "只有句末僵持使用静止",
            "forbidden_repetition": "不重复横移或机械微推",
        }
        contract["shots"][0]["camera"] = {
            "visual_task": "横移显露门框两侧的拒绝结果",
            "shot_size": "中景到中近景",
            "composition": "门框保持分割两人，横移后卫景耘停步成为主焦点",
            "mode": "track",
            "trigger": "卫景耘听到别进来后停步",
            "path": "摄影机沿门槛向右横移0.2米",
            "dramatic_gain": "横移显露卫景耘停步后的关系距离",
            "end_frame": "两人隔着门槛停住",
        }
        missing = completeness_issues(contract)
        self.assertTrue(any("requires camera.motion_ownership" in issue for issue in missing), missing)

        contract["shots"][0]["camera"]["motion_ownership"] = {
            "camera_path": "摄影机沿门槛向右横移0.2米",
            "focus_path": "焦点固定在沈青乔压住门框的右手",
            "actor_path": "卫景耘脚步停在门槛内侧，沈青乔右手保持压住门框",
            "prop_path": "道具门框始终固定在门槛位置",
            "terminal_state": "摄影机停稳，两人仍隔着门槛，右手保持压住门框",
        }
        self.assertEqual(completeness_issues(contract), [])


if __name__ == "__main__":
    unittest.main()
