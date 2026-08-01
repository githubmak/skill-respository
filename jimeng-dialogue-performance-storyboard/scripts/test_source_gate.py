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

    def test_path_read_error_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            missing = Path(root) / "missing.txt"
            result = inspect_path(str(missing))
        self.assertFalse(result["pass"])
        self.assertTrue(any(item["code"] == "SOURCE_MISSING" for item in result["blocking"]))


if __name__ == "__main__":
    unittest.main()
