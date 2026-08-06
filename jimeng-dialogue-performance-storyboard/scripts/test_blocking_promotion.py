#!/usr/bin/env python3
"""Regression tests for blocking-reference review isolation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from promote_blocking_reference import BLOCKING_GATE_VERSION, promote, record_review


class BlockingPromotionTests(unittest.TestCase):
    def test_failed_geometry_cannot_be_marked_visual_pass(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            report = Path(root) / "render.json"
            report.write_text(json.dumps({"pass": False}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "failed geometry"):
                record_review(str(report), "PASS", [])

    def test_reviewed_artifacts_promote_only_outside_staging(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            svg = root_path / "S1-01.svg"
            png = root_path / "S1-01.png"
            svg.write_text("<svg/>", encoding="utf-8")
            png.write_bytes(b"png")
            render = root_path / "render.json"
            render.write_text(json.dumps({
                "pass": True,
                "blocking_gate_version": BLOCKING_GATE_VERSION,
                "shot_group": "S1-01",
                "output_path": str(svg),
                "png_path": str(png),
            }), encoding="utf-8")
            review = record_review(str(render), "PASS", [])
            review_path = root_path / "review.json"
            review_path.write_text(json.dumps(review), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "inside staging"):
                promote(str(review_path), str(root_path / "staging"))
            destination = root_path / "approved"
            result = promote(str(review_path), str(destination))
            self.assertTrue(result["pass"])
            self.assertTrue((destination / "S1-01.svg").is_file())
            self.assertTrue((destination / "S1-01.png").is_file())

    def test_stale_gate_review_cannot_be_recorded_or_promoted(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            svg = root_path / "S1-02.svg"
            svg.write_text("<svg/>", encoding="utf-8")
            render = root_path / "render.json"
            render.write_text(json.dumps({
                "pass": True,
                "blocking_gate_version": BLOCKING_GATE_VERSION - 1,
                "shot_group": "S1-02",
                "output_path": str(svg),
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stale blocking gate"):
                record_review(str(render), "PASS", [])

            review = root_path / "review.json"
            review.write_text(json.dumps({
                "blocking_gate_version": BLOCKING_GATE_VERSION - 1,
                "visual_review": "PASS",
                "promotion_allowed": True,
                "artifacts": [],
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stale blocking gate"):
                promote(str(review), str(root_path / "approved"))


if __name__ == "__main__":
    unittest.main()
