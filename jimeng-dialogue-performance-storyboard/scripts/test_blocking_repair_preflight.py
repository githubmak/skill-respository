#!/usr/bin/env python3
"""Regression tests for schema-aware, non-creative blocking repair dry-runs."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from blocking_repair_preflight import assess
from test_render_blocking_reference import SPEC


class BlockingRepairPreflightTests(unittest.TestCase):
    def test_rejects_out_of_schema_fov_before_render_commit(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            previous = root_path / "previous.json"
            candidate = root_path / "candidate.json"
            invalid_previous = {**SPEC, "states": [{**SPEC["states"][0], "cameras": [{
                **SPEC["states"][0]["cameras"][0], "fov_deg": 20,
            }]}]}
            invalid_candidate = {**SPEC, "states": [{**SPEC["states"][0], "cameras": [{
                **SPEC["states"][0]["cameras"][0], "fov_deg": 126,
            }]}]}
            previous.write_text(json.dumps(invalid_previous, ensure_ascii=False), encoding="utf-8")
            candidate.write_text(json.dumps(invalid_candidate, ensure_ascii=False), encoding="utf-8")
            result = assess(str(previous), str(candidate))
            self.assertFalse(result["pass"])
            self.assertEqual("REJECT_CANDIDATE", result["decision"])
            self.assertIn("between 10 and 120", result["candidate"]["error"])
            self.assertFalse(result["creative_decision_made"])

    def test_accepts_model_authored_candidate_that_resolves_engineering_failure(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            previous = root_path / "previous.json"
            candidate = root_path / "candidate.json"
            invalid_previous = {**SPEC, "states": [{**SPEC["states"][0], "cameras": [{
                **SPEC["states"][0]["cameras"][0], "fov_deg": 20,
            }]}]}
            previous.write_text(json.dumps(invalid_previous, ensure_ascii=False), encoding="utf-8")
            candidate.write_text(json.dumps(SPEC, ensure_ascii=False), encoding="utf-8")
            result = assess(str(previous), str(candidate))
            self.assertTrue(result["pass"])
            self.assertEqual("ACCEPT_ENGINEERING_REPAIR", result["decision"])


if __name__ == "__main__":
    unittest.main()
