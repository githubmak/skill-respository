#!/usr/bin/env python3
"""Regression tests for the source-first Jimeng intake gate."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from source_gate import inspect_path, inspect_text


class SourceGateTests(unittest.TestCase):
    def test_empty_text_blocks(self) -> None:
        result = inspect_text(" ")
        self.assertFalse(result["pass"])
        self.assertTrue(any(item["code"] == "SOURCE_EMPTY" for item in result["blocking"]))

    def test_missing_scene_heading_is_not_blocking(self) -> None:
        result = inspect_text("她推开门，冷光落到桌面。")
        self.assertTrue(result["pass"])
        self.assertTrue(any(item["code"] == "NO_SCENE_ANCHOR" for item in result["advisories"]))
        self.assertIn("lighting_change", result["risk_flags"])

    def test_risk_flags_do_not_invent_visual_facts(self) -> None:
        result = inspect_text("甲：把手机递给我。")
        self.assertTrue(result["pass"])
        self.assertIn("prop_transfer", result["risk_flags"])
        self.assertTrue(result["source_fidelity"]["visual_inference_allowed"])

    def test_style_routing_is_evidence_based(self) -> None:
        one = inspect_text("古装人物走过门边。")
        many = inspect_text("古代府邸，汉服人物在月光下推开木门。")
        self.assertEqual(one["style_evidence"]["confidence"], "low")
        self.assertEqual(many["style_evidence"]["confidence"], "high")

    def test_unlisted_transfer_and_world_style_use_structural_evidence(self) -> None:
        result = inspect_text("末世轨道舱内，机械装甲人物把玉佩递给同伴，舱门外极光闪动。")
        self.assertIn("prop_transfer", result["risk_flags"])
        self.assertGreaterEqual(result["style_evidence"]["independent_channel_count"], 3)

    def test_path_read_error_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            missing = Path(root) / "missing.txt"
            result = inspect_path(str(missing))
        self.assertFalse(result["pass"])
        self.assertTrue(any(item["code"] == "SOURCE_MISSING" for item in result["blocking"]))

    def test_performance_cues_remain_bound_to_exact_dialogue(self) -> None:
        result = inspect_text("甲（压着嗓子）：别出声。\n乙：（笑）你也怕了？")
        self.assertEqual(2, result["stats"]["performance_cue_count"])
        first, second = result["performance_cues"]
        self.assertEqual(
            ("甲", "（压着嗓子）", "speaker_suffix", "别出声。"),
            (first["speaker"], first["cue"], first["cue_position"], first["dialogue"]),
        )
        self.assertEqual(
            ("乙", "（笑）", "dialogue_prefix", "你也怕了？"),
            (second["speaker"], second["cue"], second["cue_position"], second["dialogue"]),
        )
        self.assertEqual("乙：（笑）你也怕了？", second["source_line"])


if __name__ == "__main__":
    unittest.main()
