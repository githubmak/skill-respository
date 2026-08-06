#!/usr/bin/env python3
import unittest

from repair_scope import analyze


def _draft(first: str, second: str = "") -> str:
    return (
        "## 全局锁定\n版本\n\n"
        "#### S1-01｜镜头组总时长：4s\n\n"
        "【镜号】\n1，4s，普通。\n\n"
        "【画面描述｜直接复制】\n" + first + "\n\n"
        + ("【镜号】\n2，4s，普通。\n\n【画面描述｜直接复制】\n" + second + "\n\n" if second else "")
    )


class RepairScopeTests(unittest.TestCase):
    def test_single_shot_change_passes(self):
        result = analyze(_draft("旧"), _draft("新"), "S1-01-1", "shot")
        self.assertTrue(result["pass"], result)
        self.assertEqual(result["changed_shots"], ["S1-01-1"])

    def test_unscoped_second_shot_change_fails(self):
        result = analyze(_draft("旧", "旧2"), _draft("新", "新2"), "S1-01-1", "shot")
        self.assertFalse(result["pass"])
        self.assertTrue(any("exceed" in issue for issue in result["issues"]))

    def test_global_change_requires_scene_scope(self):
        result = analyze(_draft("旧"), _draft("旧").replace("版本", "新版本"), "S1-01-1", "shot")
        self.assertFalse(result["pass"])
        self.assertTrue(result["global_or_group_changed"])


if __name__ == "__main__":
    unittest.main()
