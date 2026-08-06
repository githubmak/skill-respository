#!/usr/bin/env python3
"""Regression tests for version-bound review state."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from review_manifest import build_manifest, delivery_status, verify_manifest, write_manifest


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
            self.assertEqual(payload["delivery_status"], "PROVISIONAL")
            write_manifest(manifest, payload)
            self.assertEqual("current", verify_manifest(manifest)["status"])
            output.write_text("修改后的分镜", encoding="utf-8")
            stale = verify_manifest(manifest)
            self.assertEqual("stale", stale["status"])
            self.assertEqual("STALE", stale["effective_review_status"])
            self.assertEqual("STALE", stale["delivery_status"])

    def test_only_design_and_visual_pass_is_final(self) -> None:
        self.assertEqual(delivery_status("PASS", "PASS"), "FINAL")
        self.assertEqual(delivery_status("REVISE", "PASS"), "PROVISIONAL")
        self.assertEqual(delivery_status("PASS", "NOT_RUN"), "PROVISIONAL")

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

    def test_delivery_inventory_rejects_unregistered_media_but_ignores_staging(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            source = base / "source.txt"
            output = base / "storyboard.md"
            staging = base / "staging" / "blocking"
            reports = base / "reports"
            manifest = reports / "review.json"
            source.write_text("剧情", encoding="utf-8")
            output.write_text("分镜", encoding="utf-8")
            staging.mkdir(parents=True)
            reports.mkdir()
            (staging / "rejected.png").write_bytes(b"rejected")
            payload = build_manifest(
                source, [output], "self_check", "PASS", "PASS", delivery_root=base
            )
            write_manifest(manifest, payload)
            self.assertTrue(verify_manifest(manifest, base)["pass"])
            (base / "unreviewed.png").write_bytes(b"unreviewed")
            result = verify_manifest(manifest, base)
            self.assertFalse(result["pass"])
            self.assertTrue(any(item["reason"] == "unregistered_delivery_file" for item in result["changed"]))

    def test_manifest_requires_outputs_to_leave_staging(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            source = base / "source.txt"
            staged = base / "staging" / "storyboard.md"
            source.write_text("剧情", encoding="utf-8")
            staged.parent.mkdir()
            staged.write_text("分镜", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "promoted out of staging"):
                build_manifest(source, [staged], "self_check", "PASS", "PASS", delivery_root=base)


if __name__ == "__main__":
    unittest.main()
