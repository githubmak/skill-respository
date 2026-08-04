#!/usr/bin/env python3
"""Regression checks for incremental repair scoping."""

from __future__ import annotations

import unittest

from incremental_validate import analyze


def _child(number: int, direct: str, state: str, include_performance: bool = True) -> str:
    performance = "【表演与声音】\n无台词。\n\n" if include_performance else ""
    return (
        f"【镜号】\n{number}，3s，普通。\n\n"
        f"【画面描述｜直接复制】\n{direct}\n\n"
        f"{performance}"
        f"【状态继承】\n{state}\n\n"
        "【本镜制作控制】\n"
        "画面质感：人物实焦，木桌划痕是材质锚点。\n"
        "光效与曝光：左侧窗光照亮脸和手，暗部可读。\n"
        "动态美学：稳定起幅，动作发生后落幅停稳。\n"
        "表演与情绪：环境触发抬眼，肩背泄露紧张，余波停在门口。\n"
        "穿帮控制：双脚接地，人物边界和道具归属保持。\n"
        "抽卡策略：低风险，固定机位，人工首轮检查。\n"
        "蒙太奇与剪辑：非蒙太奇，保持连续因果。\n"
    )


def _direct(extra: str) -> str:
    return (
        "16:9，3D自然电影CG，旧厨房暖黄窗光照在木纹墙面。"
        "平视中景，固定机位，人物身体面向墙角水阀，双脚接地；"
        + extra +
        "动作结束后仍站在墙边，镜头停稳，积水不再扩散。"
    )


class IncrementalValidationTests(unittest.TestCase):
    def test_missing_field_is_scoped_to_current_field(self):
        draft = "#### S1-01\n\n【出现人物】\n她\n\n" + _child(
            1, _direct("她发现漏水后转身按下阀门，水流停止；"),
            "她仍面向关闭的水阀。", include_performance=False,
        )
        result = analyze(draft, "S1-01-1")
        target = next(item for item in result["issues"] if "missing 【表演与声音】" in item["message"])
        self.assertEqual("field", target["repair_scope"])
        self.assertEqual(["S1-01-1"], target["shot_ids"])
        self.assertIn("【表演与声音】", target["fields"])

    def test_prop_jump_is_scoped_to_pair(self):
        first = _child(
            1, _direct("甲右手握住手机停在胸前；"),
            "甲右手仍握住手机停在胸前。",
        )
        second = _child(
            2, _direct("乙左手拿着手机看向门口；"),
            "乙左手仍拿着手机。",
        )
        draft = "#### S1-01\n\n【出现人物】\n甲\n乙\n\n" + first + "\n" + second
        result = analyze(draft, "S1-01-2")
        target = next(item for item in result["issues"] if item["code"] == "PROP_CONTINUITY" and item["repair_scope"] == "pair")
        self.assertEqual(["S1-01-1", "S1-01-2"], target["shot_ids"])

    def test_full_validation_remains_mandatory(self):
        draft = "#### S1-01\n\n【出现人物】\n她\n\n" + _child(
            1, _direct("她发现漏水后转身按下阀门，水流停止；"),
            "她仍面向关闭的水阀。",
        )
        result = analyze(draft, "S1-01-1")
        self.assertTrue(result["final_full_validation_required"])
        self.assertFalse(result["primary_output_modified"])


if __name__ == "__main__":
    unittest.main()
