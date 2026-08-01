#!/usr/bin/env python3
"""Regression tests for blocking/advisory Orchestrator preflight tiers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from preflight_check import run


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _fixture(root: Path, base_action: str = "甲站在门口") -> None:
    _write(root / "project_config.json", {"max_shot_duration": 10})
    _write(root / ".cache/orchestrator/source_ledger.json", {
        "units": [{"source_id": "SRC0001", "type": "action", "text": base_action}],
    })
    _write(root / ".cache/orchestrator/dramatic_beat_ledger.json", {
        "beats": [{"beat_id": "B0001", "owner_subshot_id": "S1-01-01", "source_ids": ["SRC0001"]}],
    })
    _write(root / ".cache/orchestrator/shot_plan.json", {
        "dialogue_map": {},
        "dialogue_events": {},
        "shots": [{
            "shot_id": "S1-01",
            "subshots": [{
                "subshot_id": "S1-01-01",
                "duration": 3.0,
                "characters": ["甲"],
                "dialogue_refs": [],
                "base_action": base_action,
                "dramatic_design": {
                    "narrative_beat_id": "B0001",
                    "dramatic_beat_ids": ["B0001"],
                    "visual_punctuation": ["rack_focus", "light_reveal", "unsupported"],
                },
                "duration_design": {
                    "duration_strategy": "pack_toward_limit",
                    "justified_content_duration": 3.0,
                    "utilization_ratio": 0.3,
                    "dramatic_beats": ["B0001"],
                },
            }],
        }],
    })


class PreflightSeverityTests(unittest.TestCase):
    def test_visual_punctuation_is_advisory_only(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            _fixture(root_path)
            issues = run(str(root_path))
            report = json.loads((root_path / ".cache/preflight/report.json").read_text(encoding="utf-8"))
        self.assertTrue(issues)
        self.assertTrue(all(item["severity"] == "advisory" for item in issues), issues)
        self.assertTrue(report["pass"])

    def test_missing_action_remains_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            _fixture(root_path, base_action="")
            issues = run(str(root_path))
        self.assertTrue(any(item["check"] == "BASE_ACTION_MISSING" for item in issues), issues)
        self.assertTrue(any(item["severity"] == "blocking" for item in issues), issues)


if __name__ == "__main__":
    unittest.main()
