#!/usr/bin/env python3
"""Regression checks for incremental repair scoping."""

from __future__ import annotations

import unittest

from incremental_validate import _issue, analyze


def _child(
    number: int,
    direct: str,
    state: str,
    include_performance: bool = True,
    memory_anchor: str = "",
) -> str:
    performance = "【表演与声音】\n无台词。\n\n" if include_performance else ""
    return (
        f"【镜号】\n{number}，3s，普通。\n\n"
        f"【画面描述｜直接复制】\n{direct}\n\n"
        f"{performance}"
        f"【状态继承】\n{state}\n\n"
        "【本镜制作控制】\n"
        "画面质感：人物实焦，木桌划痕是材质锚点。" + memory_anchor + "\n"
        "光效与曝光：左侧窗光照亮脸和手，暗部可读。\n"
        "动态美学：稳定起幅，动作发生后落幅停稳。\n"
        "表演与情绪：环境触发抬眼，肩背泄露紧张，余波停在门口。\n"
        "穿帮控制：双脚接地，人物边界和道具归属保持。\n"
        "抽卡策略：低风险，固定机位，自动首轮检查。\n"
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
    def test_signature_core_position_is_scoped_to_shot_and_both_fields(self):
        target = _issue(
            "不可降级视觉核心必须在直接提示词前60%内完成",
            "field",
            ["S1-01-1"],
        )
        self.assertEqual("MEMORY_ANCHOR_DENSITY", target["code"])
        self.assertEqual("shot", target["repair_scope"])
        self.assertEqual(["【画面描述｜直接复制】", "【本镜制作控制】"], target["fields"])

    def test_expanded_prompt_limit_keeps_length_issue_code(self):
        target = _issue(
            "S1-01-1: direct prompt over 650 chars -> 651",
            "field",
            ["S1-01-1"],
        )
        self.assertEqual("DIRECT_PROMPT_LENGTH", target["code"])
        self.assertEqual(["【画面描述｜直接复制】"], target["fields"])

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

    def test_physical_axis_flip_is_caught_during_incremental_validation(self):
        previous = (
            "摄影机位于长桌南侧，朝北拍摄，保持在甲与乙关系轴同一侧。"
            "甲站在桌边，身体面向乙，侧面可见，视线落在乙；"
            "乙站在桌对面，身体面向甲，侧面可见，视线落在甲。两人对峙。"
        )
        current = previous.replace("长桌南侧，朝北", "长桌北侧，朝南")
        draft = (
            "#### S1-01\n\n【出现人物】\n甲\n乙\n\n"
            + _child(1, previous, "甲乙仍隔桌对峙。")
            + "\n"
            + _child(2, current, "甲乙仍隔桌对峙。")
        )
        result = analyze(draft, "S1-01-2")
        target = next(item for item in result["issues"] if item["code"] == "AXIS_CONTINUITY")
        self.assertEqual("pair", target["repair_scope"])
        self.assertEqual(["S1-01-1", "S1-01-2"], target["shot_ids"])

    def test_full_validation_remains_mandatory(self):
        draft = "#### S1-01\n\n【出现人物】\n她\n\n" + _child(
            1, _direct("她发现漏水后转身按下阀门，水流停止；"),
            "她仍面向关闭的水阀。",
        )
        result = analyze(draft, "S1-01-1")
        self.assertTrue(result["final_full_validation_required"])
        self.assertFalse(result["primary_output_modified"])

    def test_explicit_timing_failure_repairs_shot_header_and_window(self):
        issue = _issue(
            "S1-01-1: 【口型分窗】显式时间窗失败 -> 尾部空档 2-3s 未分配",
            "field",
            ["S1-01-1"],
        )
        self.assertEqual("TIMING_WINDOW", issue["code"])
        self.assertEqual("shot", issue["repair_scope"])
        self.assertEqual(["【镜号】", "【口型分窗】"], issue["fields"])

    def test_state_boundary_failure_repairs_direct_and_state_in_one_shot(self):
        issue = _issue(
            "S1-01-1: 【状态继承】结束边界失败 -> 结束状态新增未入正文道具/支撑 -> 钥匙",
            "field",
            ["S1-01-1"],
        )
        self.assertEqual("STATE_BOUNDARY", issue["code"])
        self.assertEqual("shot", issue["repair_scope"])
        self.assertEqual(["【画面描述｜直接复制】", "【状态继承】"], issue["fields"])

    def test_fifth_shot_without_memory_anchor_returns_window_scope(self):
        children = [
            _child(
                index,
                _direct(f"人物触碰第{index}只杯子后收回手；"),
                "人物仍面向桌面。",
            )
            for index in range(1, 6)
        ]
        draft = "#### S1-01\n\n【出现人物】\n人物\n\n" + "\n".join(children)
        result = analyze(draft, "S1-01-5")
        target = next(item for item in result["issues"] if item["code"] == "MEMORY_ANCHOR_DENSITY")
        self.assertEqual("window", target["repair_scope"])
        self.assertEqual([f"S1-01-{index}" for index in range(1, 6)], target["shot_ids"])
        self.assertEqual(["【画面描述｜直接复制】", "【本镜制作控制】"], target["fields"])

    def test_fifth_shot_accepts_valid_memory_anchor_in_window(self):
        anchor = (
            "记忆锚点：墙角水阀把人物和扩散积水连成斜线；"
            "第一眼焦点：水阀锈斑；"
            "成立原因：水阀与积水边缘同时呈现原因和后果；"
            "情绪载体：人物按住水阀的指节发白；"
            "关系/认知变化：人物由迟疑转为决定；"
            "相邻差异：观众位置贴近地面，信息显露从积水转到水阀，视觉载体从杯子转为锈斑；"
            "不可降级核心：水阀、发白指节与停止扩散的积水同时入画。"
        )
        children = [
            _child(
                index,
                _direct(
                    "水阀、发白指节与停止扩散的积水同时入画，墙角水阀把人物和扩散积水连成斜线，"
                    "前景积水倒影映出水阀锈斑，第一眼落在水阀锈斑，人物按住水阀的指节发白，"
                    "水阀与积水边缘同时呈现原因和后果，人物由迟疑转为决定，"
                    "积水边缘停在人物脚前；"
                    if index == 3 else f"人物触碰第{index}只杯子后收回手；"
                ),
                "人物仍面向桌面。",
                memory_anchor=anchor if index == 3 else "",
            )
            for index in range(1, 6)
        ]
        draft = "#### S1-01\n\n【出现人物】\n人物\n\n" + "\n".join(children)
        result = analyze(draft, "S1-01-5")
        self.assertFalse(any(item["code"] == "MEMORY_ANCHOR_DENSITY" for item in result["issues"]), result)


if __name__ == "__main__":
    unittest.main()
