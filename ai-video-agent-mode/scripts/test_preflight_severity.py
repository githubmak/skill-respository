#!/usr/bin/env python3
"""Preflight blocks facts, not creative choices."""

import json
import os
import tempfile
import unittest

from preflight_check import run


def _write(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


class PreflightBoundaryTests(unittest.TestCase):
    def _run(self, duration=3, dialogue="原句"):
        root = tempfile.TemporaryDirectory()
        run_dir = root.name
        _write(os.path.join(run_dir, "project_config.json"), {"max_shot_duration": 15})
        _write(os.path.join(run_dir, ".cache", "orchestrator", "source_snapshot.json"), {
            "lines": [{"line": 1, "text": "甲：原句"}],
        })
        _write(os.path.join(run_dir, ".cache", "orchestrator", "source_ledger.json"), {
            "units": [{"source_id": "SRC000001", "line": 1, "text": "甲：原句"}],
        })
        _write(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"), {
            "dialogue_events": {"D1": {
                "ref": "D1", "kind": "台词", "speaker": "甲", "text": dialogue, "source_ids": ["SRC000001"],
            }},
            "shots": [{"shot_id": "S1", "subshots": [{
                "subshot_id": "S1-1", "duration": duration, "dialogue_refs": ["D1"],
                "source_ids": ["SRC000001"],
                # Deliberately no base_action, camera, palette, or punctuation.
            }]}],
        })
        return root, run(run_dir)

    def test_missing_creative_fields_do_not_trigger_engine_judgment(self):
        root, issues = self._run()
        self.addCleanup(root.cleanup)
        self.assertEqual(issues, [])

    def test_duration_and_verbatim_dialogue_still_block(self):
        root, issues = self._run(duration=16, dialogue="改句")
        self.addCleanup(root.cleanup)
        self.assertTrue(any(item["check"].startswith("DURATION_") for item in issues), issues)
        self.assertTrue(any(item["check"] == "DIALOGUE_SOURCE_TEXT" for item in issues), issues)


if __name__ == "__main__":
    unittest.main()
