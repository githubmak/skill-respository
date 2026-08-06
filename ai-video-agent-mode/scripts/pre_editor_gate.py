#!/usr/bin/env python3
"""Cached local gate between Composer merge and Editor Pass 2.

This gate contains deterministic package checks only. Creative and semantic
review starts in the model Editor from the source, scene contracts, and full
model-authored package; code does not pre-score its camera or emotional value.
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from validate_composer_output import validate_composer_output
from contract_registry import PROMPT_CONTRACT_VERSION


PACKAGE_RELATIVE_PATH = ".cache/composer/merged.prompt_package.json"
GATE_RELATIVE_PATH = ".cache/review/pre_editor_gate.json"


def run(run_dir):
    package_path = os.path.join(run_dir, PACKAGE_RELATIVE_PATH)
    if not os.path.isfile(package_path):
        raise FileNotFoundError("Missing merged Composer package: %s" % package_path)
    package_sha256 = _sha256(package_path)
    validator_sha256 = _sha256(os.path.join(os.path.dirname(__file__), "validate_deterministic_package.py"))
    gate_path = os.path.join(run_dir, GATE_RELATIVE_PATH)
    cached = _load(gate_path)
    if (
        cached.get("package_sha256") == package_sha256
        and cached.get("validator_sha256") == validator_sha256
        and isinstance(cached.get("pass"), bool)
    ):
        return cached, gate_path

    review_dir = os.path.dirname(gate_path)
    os.makedirs(review_dir, exist_ok=True)
    composer_report = os.path.join(review_dir, "pre_editor_composer_validation.json")
    composer_pass = validate_composer_output(package_path, run_dir, composer_report) == 0
    result = {
        "contract_version": PROMPT_CONTRACT_VERSION,
        "package_path": os.path.abspath(package_path),
        "package_sha256": package_sha256,
        "validator_sha256": validator_sha256,
        "composer_validation_path": composer_report,
        "composer_pass": composer_pass,
        "semantic_review_authority": "model_editor",
        "semantic_audit_path": "",
        "semantic_pass": None,
        "pass": composer_pass,
    }
    with open(gate_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    return result, gate_path


def _load(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: pre_editor_gate.py <run_dir>")
    result, path = run(sys.argv[1])
    print("[PRE-EDITOR GATE] %s: %s" % ("PASS" if result["pass"] else "FAIL", path))
    raise SystemExit(0 if result["pass"] else 1)
