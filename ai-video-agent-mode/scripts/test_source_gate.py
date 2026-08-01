#!/usr/bin/env python3
"""Regression tests for the source-first AI-video intake gate."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from source_gate import inspect_source, run


class SourceGateTests(unittest.TestCase):
    def test_empty_source_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "empty.txt"
            source.write_text("\n", encoding="utf-8")
            result = inspect_source(str(source))
        self.assertFalse(result["pass"])
        self.assertTrue(any(item["code"] == "SOURCE_EMPTY" for item in result["blocking"]))

    def test_sparse_prose_is_advisory_only(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "scene.txt"
            source.write_text("雨停后，门缝里落进一条冷光。", encoding="utf-8")
            result = inspect_source(str(source))
        self.assertTrue(result["pass"])
        self.assertTrue(any(item["code"] == "NO_SCENE_ANCHOR" for item in result["advisories"]))
        self.assertTrue(any(item["code"] == "NO_EXPLICIT_BEAT" for item in result["advisories"]))

    def test_unsupported_config_is_early_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "scene.txt"
            source.write_text("场景：客厅\n甲：你好", encoding="utf-8")
            config = Path(root) / "project_config.json"
            config.write_text(json.dumps({"target_platform": "other", "generation_control": {"mode": "i2v"}}), encoding="utf-8")
            result = inspect_source(str(source), str(config))
        codes = {item["code"] for item in result["blocking"]}
        self.assertIn("UNSUPPORTED_PLATFORM", codes)
        self.assertIn("UNSUPPORTED_MODE", codes)

    def test_style_routing_requires_multiple_evidence_channels(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            one_signal = Path(root) / "one.txt"
            one_signal.write_text("古装人物站在门边。", encoding="utf-8")
            many_signals = Path(root) / "many.txt"
            many_signals.write_text("古代府邸，汉服人物在月光下推开木门。", encoding="utf-8")
            one = inspect_source(str(one_signal))
            many = inspect_source(str(many_signals))
        self.assertEqual(one["style_evidence"]["confidence"], "low")
        self.assertEqual(many["style_evidence"]["confidence"], "high")

    def test_run_persists_and_reuses_report(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            source = root_path / "scene.txt"
            source.write_text("场景：院子\n甲：你回来了。", encoding="utf-8")
            first = run(str(root_path / "run"), str(source))
            second = run(str(root_path / "run"), str(source))
            self.assertEqual(first["source_sha256"], second["source_sha256"])
            self.assertTrue(Path(second["report_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
