#!/usr/bin/env python3
"""Regression tests for prompt wording preflight lint."""

from __future__ import annotations

import unittest

from prompt_preflight import lint_markdown


BASE = """#### S1-01｜镜头组总时长：4s

【出现人物】
甲
乙

【镜号】
1，4s，普通。

【画面描述｜直接复制】
16:9，稳定到结束。夜晚门口，中景。甲在门内，没有跨过门槛；乙在门外。先看甲的手，最后两人停在门槛两侧。
"""


class PromptPreflightTests(unittest.TestCase):
    def test_detects_boundary_negation_and_early_terminal_marker(self) -> None:
        codes = {item["code"] for item in lint_markdown(BASE)}
        self.assertEqual(codes, {"BOUNDARY_NEGATION", "EARLY_TERMINAL_MARKER"})

    def test_clean_prompt_has_no_findings(self) -> None:
        clean = BASE.replace("稳定到结束。", "画面稳定。").replace("没有跨过门槛", "从门内起步")
        self.assertEqual(lint_markdown(clean), [])

    def test_dialogue_negative_phrase_is_not_visual_boundary_fact(self) -> None:
        dialogue = BASE.replace("没有跨过门槛", "他说：“我没有跨过门槛。”")
        dialogue = dialogue.replace("稳定到结束。", "画面稳定。")
        self.assertEqual(lint_markdown(dialogue), [])

    def test_repeated_template_phrase_is_reported_once_as_cross_shot_issue(self) -> None:
        draft = "\n".join(
            BASE.replace("稳定到结束。", "第一焦点锁定主体与道具。稳定到结束。")
            .replace("【镜号】\n1，4s", f"【镜号】\n{index}，4s")
            for index in (1, 2, 3)
        )
        findings = lint_markdown(draft)
        self.assertTrue(any(item["code"] == "REPEATED_TEMPLATE_POLLUTION" for item in findings))

    def test_repeated_unmotivated_static_camera_family_is_reported(self) -> None:
        draft = "\n".join(
            BASE.replace("#### S1-01", f"#### S1-0{index}")
            .replace("稳定到结束。", "固定机位。画面稳定。")
            .replace("没有跨过门槛", "从门内起步")
            for index in (1, 2, 3)
        )
        findings = lint_markdown(draft)
        self.assertTrue(any(item["code"] == "STATIC_CAMERA_TEMPLATE_POLLUTION" for item in findings), findings)

    def test_reflective_light_without_transport_is_reported(self) -> None:
        draft = BASE.replace(
            "夜晚门口，中景。",
            "夜晚门口，月光作为主光源，中景。鱼篓内水光晃动，焦点落在湿鳞银白点缀。",
        )
        codes = {item["code"] for item in lint_markdown(draft)}
        self.assertIn("REFLECTIVE_LIGHT_OWNERSHIP", codes)

    def test_camera_prop_motion_ambiguity_is_reported(self) -> None:
        draft = BASE.replace(
            "先看甲的手，最后两人停在门槛两侧。",
            "菜篮里放着两种野菜；摄影机横移跟随甲手指从叶片落到乙脸，最后手指停在叶片旁。",
        )
        codes = {item["code"] for item in lint_markdown(draft)}
        self.assertIn("CAMERA_PROP_MOTION_OWNERSHIP", codes)

    def test_camera_prop_motion_ambiguity_without_follow_is_reported(self) -> None:
        draft = BASE.replace(
            "先看甲的手，最后两人停在门槛两侧。",
            "两种野菜放在菜篮里；摄影机从叶片落到乙脸，最后手指停在叶片旁。",
        )
        codes = {item["code"] for item in lint_markdown(draft)}
        self.assertIn("CAMERA_PROP_MOTION_OWNERSHIP", codes)

    def test_separate_camera_focus_hand_and_prop_paths_are_clean(self) -> None:
        draft = BASE.replace("稳定到结束。", "画面稳定。").replace("没有跨过门槛", "从门内起步")
        draft = draft.replace(
            "先看甲的手，最后两人停在门槛两侧。",
            "两种野菜始终平放在菜篮内；摄影机沿门槛向右横移0.2米；"
            "焦点从甲的指尖转到乙脸；甲的手指停在安全叶片旁，叶片仍留在菜篮内。",
        )
        self.assertEqual(lint_markdown(draft), [])


if __name__ == "__main__":
    unittest.main()
