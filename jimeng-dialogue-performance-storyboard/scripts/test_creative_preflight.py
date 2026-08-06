#!/usr/bin/env python3
"""Regression tests for the creative minimum gate."""

from __future__ import annotations

import unittest

from creative_preflight import lint_markdown


GENERIC = """#### S1-01｜镜头组总时长：4s

【出现人物】
甲
乙

【镜号】
1，4s，普通。

【画面描述｜直接复制】
16:9写实，固定中近景，轻推，甲皱眉，乙抬眼，停稳到结束。
"""


DISTINCTIVE = """#### S1-01｜镜头组总时长：4s

【出现人物】
甲
乙

【镜号】
1，4s，普通。

【画面描述｜直接复制】
16:9写实，夜晚油灯主光。第一焦点落在甲压住门框的手，门框遮住两人之间的通道；乙听见甲的拒绝后退开半步，火光映出甲仍未松开的手，最后两人停在门槛两侧。
"""


class CreativePreflightTests(unittest.TestCase):
    def test_generic_prompt_is_blocked_in_strict_report(self) -> None:
        report = lint_markdown(GENERIC)
        self.assertTrue(any(item["code"] == "CREATIVE_CORE_THIN" for item in report["findings"]))

    def test_distinctive_prompt_has_no_creative_findings(self) -> None:
        report = lint_markdown(DISTINCTIVE)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["shots"][0]["score"], 5)

    def test_physical_luminance_hierarchy_counts_as_lighting_duty(self) -> None:
        markdown = DISTINCTIVE.replace(
            "火光映出甲仍未松开的手",
            "月光从门洞斜落到鱼篓湿鳞，湿鳞只形成低亮反光和窄高光，亮度低于乙的受光侧脸",
        )
        report = lint_markdown(markdown)
        self.assertFalse(any(item["code"] == "GROUP_LIGHTING_DUTY_MISSING" for item in report["findings"]))


if __name__ == "__main__":
    unittest.main()
