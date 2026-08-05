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


if __name__ == "__main__":
    unittest.main()
