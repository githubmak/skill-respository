#!/usr/bin/env python3
"""Compatibility entry point for deterministic Master output validation."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from validate_deterministic_package import validate_package


def validate_composer_output(
    path, run_dir=None, report_path=None, allow_incomplete=False, selected_shot_ids=None
):
    result = validate_package(
        path,
        run_dir=run_dir,
        report_path=report_path,
        allow_incomplete=True,
        selected_shot_ids=selected_shot_ids,
        allow_batch_envelope=True,
    )
    label = "PASS" if result["pass"] else "FAIL"
    print("[DETERMINISTIC MASTER VALIDATION] %s - %d shot(s)" % (label, result["shot_count"]))
    for issue in result["issues"][:80]:
        print("  - " + issue)
    return 0 if result["pass"] else 1


def _load_scaffold_for_batch(batch_path, run_dir=None):
    """Read the packet-linked scaffold without interpreting creative fields."""
    candidates = []
    directory = os.path.dirname(os.path.abspath(batch_path))
    candidates.extend(
        os.path.join(directory, name)
        for name in os.listdir(directory) if name.endswith("_scaffold.json")
    ) if os.path.isdir(directory) else None
    if run_dir:
        dispatch_dir = os.path.join(run_dir, ".cache", "dispatch")
        if os.path.isdir(dispatch_dir):
            candidates.extend(
                os.path.join(dispatch_dir, name)
                for name in os.listdir(dispatch_dir) if name.endswith("_scaffold.json")
            )
    for candidate in sorted(candidates, key=lambda value: os.path.getmtime(value), reverse=True):
        try:
            with open(candidate, "r", encoding="utf-8-sig") as handle:
                data = json.load(handle)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        shots = data.get("shots", []) if isinstance(data, dict) else []
        return {
            str(item.get("subshot_id", "") or item.get("shot_id", "")): item
            for item in shots if isinstance(item, dict)
        }
    return {}


if __name__ == "__main__":
    args = sys.argv[1:]
    run_dir = None
    if "--run-dir" in args:
        index = args.index("--run-dir")
        run_dir = args[index + 1]
        del args[index:index + 2]
    if len(args) != 1:
        raise SystemExit("usage: validate_composer_output.py <package.json> [--run-dir <run_dir>]")
    raise SystemExit(validate_composer_output(args[0], run_dir))
