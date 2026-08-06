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

    def test_speaker_normalization_excludes_cues_channels_and_structure_labels(self) -> None:
        source = """人物：沈青乔、满满、阿丰、卫景耘、豆宝
场景：院儿内小屋门口，夜
满满（兴奋）：爹爹，娘亲带我们去抓鱼了！
满满：爹爹你看！
卫景耘（不信）：不会有毒吧？
沈青乔（皱眉，OS）：还剩点粗盐。
阿丰（OS）：今天好像不一样了。
豆宝：发现可食用植物。
"""
        result = inspect_text(source)
        self.assertEqual(
            ["满满", "卫景耘", "沈青乔", "阿丰", "豆宝"],
            result["stats"]["speakers"],
        )
        self.assertEqual(5, result["stats"]["speaker_count"])
        self.assertNotIn("人物", result["stats"]["speakers"])
        self.assertNotIn("场景", result["stats"]["speakers"])


if __name__ == "__main__":
    unittest.main()
