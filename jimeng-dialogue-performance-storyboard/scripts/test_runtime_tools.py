#!/usr/bin/env python3
"""Regression checks for compact routing and companion output."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from concise_storyboard import extract
from route_task import route


SKILL_ROOT = Path(__file__).resolve().parent.parent


class RuntimeToolTests(unittest.TestCase):
    def test_default_route_is_compact(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            source.write_text("SCENE 1 客厅\n甲：你回来了。", encoding="utf-8")
            result = route("generate", str(source))
        self.assertTrue(result["pass"])
        self.assertEqual(result["read_first"], ["references/runtime-core.md", "references/output-template.md"])
        self.assertEqual(result["read_on_demand"], [])
        self.assertEqual(result["run_during_generation"][0]["after"], "each_shot")
        self.assertEqual(result["run_during_generation"][0]["script"], "scripts/incremental_validate.py")
        self.assertEqual(
            result["run_during_generation"][0]["arguments"],
            ["<scene_draft.md>", "--current-shot", "<shot_id>"],
        )
        self.assertNotIn("command", result["run_during_generation"][0])

    def test_risks_load_only_specialist_references(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            source.write_text("SCENE 1 电梯\n三人围在门边，甲把手机递给乙。", encoding="utf-8")
            result = route("generate", str(source))
        self.assertIn("references/physical-structure-continuity.md", result["read_on_demand"])
        self.assertIn("references/spatial-camera-continuity.md", result["read_on_demand"])
        self.assertIn("references/generation-risk-guards.md", result["read_on_demand"])

    def test_natural_camera_language_and_three_speakers_route_specialists(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            source.write_text(
                "SCENE 1 站厅\n摄影机沿中线缓慢拉开，再快速右摇落到出口。\n"
                "甲：“走吧。”乙：“等一下。”丙：“闸机锁了。”",
                encoding="utf-8",
            )
            result = route("generate", str(source))
        self.assertIn("references/cinematic-grammar-library.md", result["read_on_demand"])
        self.assertIn("references/prompt-performance-rules.md", result["read_on_demand"])
        self.assertIn("references/spatial-camera-continuity.md", result["read_on_demand"])

    def test_unfamiliar_prose_and_viewpoint_path_route_conservatively(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            source.write_text(
                "轨道舱忽然失重。直到舱门开启，她却发现时间环已经归零。"
                "摄影机贴近舷窗后穿过舱门，落到她握紧的玉佩。",
                encoding="utf-8",
            )
            result = route("generate", str(source))
        self.assertIn("references/narrative-mode-routing.md", result["read_on_demand"])
        self.assertIn("references/cinematic-grammar-library.md", result["read_on_demand"])

    def test_concise_view_preserves_direct_prompt(self):
        source = "【镜号】\n1-1，4s，普通。\n\n【画面描述｜直接复制】\n原样提示词。\n\n【表演与声音】\n无台词。"
        self.assertEqual(extract(source), [("1-1，4s，普通。", "原样提示词。")])

    def test_output_template_keeps_upper_bound_controls_in_both_shot_definitions(self):
        template = (SKILL_ROOT / "references" / "output-template.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(template.count("光影在显露、遮蔽、隔离、吸引注意或关系转折中的本镜职责"), 2)
        self.assertGreaterEqual(template.count("遮挡/距离/信息/权力关系的前后差值"), 2)
        self.assertGreaterEqual(template.count("策略变化或坚持策略的代价"), 2)
        self.assertIn("基础光态、峰值有因变化和结束光态", template)
        self.assertIn("演员调度与摄影机响应", template)
        self.assertIn("主要人物目标、保护对象、对外策略、策略转折和行为签名", template)
        self.assertNotIn("动态美学：[起幅、触发、主体动作/有意静止", template)


if __name__ == "__main__":
    unittest.main()
