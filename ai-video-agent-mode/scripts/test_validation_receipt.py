#!/usr/bin/env python3
"""Regression checks for safe validation reuse and stale-input fallback."""

import json
import os
import tempfile

from validation_receipt import create_receipt, verify_receipt
from contract_registry import PROMPT_CONTRACT_VERSION


def _write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False)


def run():
    with tempfile.TemporaryDirectory(prefix="validation-receipt-") as run_dir:
        package = os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json")
        _write(package, {"contract_version": PROMPT_CONTRACT_VERSION, "shots": []})
        _write(os.path.join(run_dir, "project_config.json"), {"max_shot_duration": 15})
        _write(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"), {"shots": []})
        _write(os.path.join(run_dir, ".cache", "review", "llm_gate_result.json"), {"pass": True, "blocking": []})
        outputs = []
        for name in ("episode_state_graph.json", "episode_director_audit.json", "emotion_camera_audit.json"):
            path = os.path.join(run_dir, ".cache", "validate", name)
            _write(path, {"pass": True})
            outputs.append(path)
        create_receipt(run_dir, package, outputs)
        assert verify_receipt(run_dir, package)[0] is True
        _write(os.path.join(run_dir, "project_config.json"), {"max_shot_duration": 10})
        ok, reason, _receipt = verify_receipt(run_dir, package)
        assert ok is False and "changed" in reason
    print("validation receipt regression: PASS")


if __name__ == "__main__":
    run()
