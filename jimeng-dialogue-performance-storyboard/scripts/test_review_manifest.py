#!/usr/bin/env python3
"""Regression tests for version-bound review state."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from review_manifest import build_manifest, verify_manifest, write_manifest


class ReviewManifestTests(unittest.TestCase):
    def test_manifest_becomes_stale_after_source_or_output_change(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            source = base / "source.txt"
            output = base / "storyboard.md"
            manifest = base / "review.json"
            source.write_text("原始剧情", encoding="utf-8")
            output.write_text("原始分镜", encoding="utf-8")
            payload = build_manifest(source, [output], "self_check", "PASS", "NOT_RUN")
            write_manifest(manifest, payload)
            self.assertEqual("current", verify_manifest(manifest)["status"])
            output.write_text("修改后的分镜", encoding="utf-8")
            stale = verify_manifest(manifest)
            self.assertEqual("stale", stale["status"])
            self.assertEqual("STALE", stale["effective_review_status"])

    def test_self_check_cannot_claim_independence(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            output = Path(root) / "storyboard.md"
            source.write_text("剧情", encoding="utf-8")
            output.write_text("分镜", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "conflict"):
                build_manifest(
                    source, [output], "self_check", "PASS", "NOT_RUN", independent=True
                )

    def test_independent_review_requires_context_identifier(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            output = Path(root) / "storyboard.md"
            source.write_text("剧情", encoding="utf-8")
            output.write_text("分镜", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "reviewer_context_id"):
                build_manifest(source, [output], "independent", "PASS", "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
