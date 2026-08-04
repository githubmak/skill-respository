#!/usr/bin/env python3
"""Create and verify cryptographic receipts for unchanged validation inputs."""

import hashlib
import json
import os

from pipeline_runtime import atomic_json


RECEIPT_VERSION = "validation-receipt-v1"
RECEIPT_RELATIVE_PATH = ".cache/validate/validation_receipt.json"
INPUT_PATHS = (
    "project_config.json",
    ".cache/orchestrator/shot_plan.json",
    ".cache/review/llm_gate_result.json",
)


def create_receipt(run_dir, package_path, validation_outputs):
    run_dir = os.path.abspath(run_dir)
    receipt = {
        "receipt_version": RECEIPT_VERSION,
        "package": _record(run_dir, package_path),
        "inputs": [_record(run_dir, os.path.join(run_dir, relative)) for relative in INPUT_PATHS],
        "validation_outputs": [_record(run_dir, path) for path in validation_outputs],
        "validator_bundle_sha256": validator_bundle_sha256(),
    }
    path = os.path.join(run_dir, RECEIPT_RELATIVE_PATH)
    atomic_json(path, receipt)
    return path, receipt


def verify_receipt(run_dir, package_path):
    run_dir = os.path.abspath(run_dir)
    path = os.path.join(run_dir, RECEIPT_RELATIVE_PATH)
    receipt = _load(path)
    if receipt.get("receipt_version") != RECEIPT_VERSION:
        return False, "missing or legacy receipt", receipt
    if receipt.get("validator_bundle_sha256") != validator_bundle_sha256():
        return False, "validator code changed", receipt
    expected = [receipt.get("package", {})]
    expected.extend(receipt.get("inputs", []) if isinstance(receipt.get("inputs"), list) else [])
    expected.extend(receipt.get("validation_outputs", []) if isinstance(receipt.get("validation_outputs"), list) else [])
    if not expected or any(not _record_is_current(run_dir, item) for item in expected):
        return False, "validation input or result changed", receipt
    package_record = receipt.get("package", {})
    if os.path.realpath(_resolve(run_dir, package_record.get("path", ""))) != os.path.realpath(package_path):
        return False, "package path changed", receipt
    return True, "unchanged validated inputs", receipt


def validator_bundle_sha256():
    scripts_dir = os.path.dirname(__file__)
    digest = hashlib.sha256()
    names = sorted(
        name for name in os.listdir(scripts_dir)
        if name.endswith(".py")
        and not name.startswith("test_")
    )
    for name in names:
        path = os.path.join(scripts_dir, name)
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256(path).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _record(run_dir, path):
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise ValueError("validation receipt input is missing: " + path)
    try:
        stored_path = os.path.relpath(path, run_dir)
    except ValueError:
        stored_path = path
    return {"path": stored_path, "sha256": _sha256(path)}


def _record_is_current(run_dir, record):
    if not isinstance(record, dict) or not record.get("path") or not record.get("sha256"):
        return False
    path = _resolve(run_dir, record["path"])
    return os.path.isfile(path) and _sha256(path) == record["sha256"]


def _resolve(run_dir, path):
    return path if os.path.isabs(path) else os.path.join(run_dir, path)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}
