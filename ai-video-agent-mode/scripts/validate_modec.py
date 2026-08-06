#!/usr/bin/env python3
"""Final gate: deterministic validity plus model Editor approval."""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from validate_deterministic_package import validate_package


def main(run_dir):
    package_path = _first_existing(run_dir, [
        ".cache/composer/merged.prompt_package.json",
        ".cache/composer/prompt_package.json",
        ".cache/prompt_package.json",
    ])
    report_path = os.path.join(run_dir, ".cache", "validate", "deterministic_package.json")
    result = validate_package(
        package_path,
        run_dir=run_dir,
        report_path=report_path,
        require_editor=True,
    )
    print("[FINAL DELIVERY GATE] %s - deterministic facts + model Editor" % ("PASS" if result["pass"] else "FAIL"))
    for issue in result["issues"][:80]:
        print("  - " + issue)
    return 0 if result["pass"] else 1


def _first_existing(run_dir, candidates):
    for relative in candidates:
        path = os.path.join(run_dir, relative)
        if os.path.isfile(path):
            return path
    return os.path.join(run_dir, candidates[0])


def _load_json(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _load_optional_json(path):
    try:
        return _load_json(path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _as_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[;；,，、/]+", value) if part.strip()]
    return []


def _main_shot_expectations(plan):
    return {
        str(shot.get("shot_id", "")): shot
        for shot in plan.get("shots", []) if isinstance(shot, dict) and shot.get("shot_id")
    }


def _source_dialogue_events(plan, metadata):
    ledger = plan.get("dialogue_events", {}) if isinstance(plan.get("dialogue_events"), dict) else {}
    return [dict(ledger[ref]) for ref in _as_list(metadata.get("dialogue_refs", [])) if isinstance(ledger.get(ref), dict)]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate_modec.py <run_dir>")
    raise SystemExit(main(sys.argv[1]))
