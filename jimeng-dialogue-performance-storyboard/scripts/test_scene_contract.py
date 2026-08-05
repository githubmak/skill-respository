#!/usr/bin/env python3
"""Regression tests for compact internal scene contracts."""

from __future__ import annotations

import unittest

from scene_contract import recovery_issues, validate_contract


CONTRACT = {
    "version": 1,
    "scene_id": "S1",
    "risk_vector": ["critical_performance_turn", "boundary"],
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
16:9现代写实，夜晚室内门口，中近景看清手与门框，沈青乔门外、卫景耘屋内。第一焦点落在沈青乔压住门框的右手；沈青乔肩后固定机位看清卫景耘。沈青乔说：“别进来。”卫景耘听到“别进来”后，脚步停在门槛内侧。门框把两人隔在门外与屋内。最后两人隔着门槛停住，沈青乔右手仍压住门框，镜头稳定到结束。

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
        broken = MARKDOWN.replace("卫景耘听到“别进来”后，脚步停在门槛内侧。", "卫景耘没有明显动作。")
        broken = broken.replace("沈青乔右手仍压住门框", "沈青乔恢复自然站姿")
        issues = recovery_issues(CONTRACT, broken)
        self.assertTrue(any("listener_visible_fact" in issue for issue in issues))
        self.assertTrue(any("end_residue" in issue for issue in issues))

    def test_object_shot_uses_null_performance_without_inventing_actors(self) -> None:
        contract = {
            "version": 1,
            "scene_id": "S1",
            "risk_vector": [],
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
固定近景，第一焦点是桌上的钥匙，钥匙停在门边桌面。光线稳定，最后钥匙仍停在门边桌面。

【表演与声音】
无台词。
"""
        self.assertIsNone(validate_contract(contract)["shots"][0]["performance"])
        self.assertEqual(recovery_issues(contract, markdown), [])


if __name__ == "__main__":
    unittest.main()
