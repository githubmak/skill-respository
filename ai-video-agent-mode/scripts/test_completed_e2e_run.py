#!/usr/bin/env python3
"""Validate a completed real E2E run without fabricating Agent outputs.

This regression is intentionally post-run.  It proves that a run produced by
the real supervisor/worker protocol is still complete after code changes:
state, provenance, prompt package, validation, export files, and performance
report must all agree on the same current artifacts.
"""

import argparse
import hashlib
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(__file__)
sys.path.insert(0, SCRIPT_DIR)

from check_export import check_export
from performance_budget import report as performance_report
from pipeline_state import PHASE_ORDER, load_state
from record_batch_provenance import verify as verify_batch_provenance
from validate_modec import main as validate_modec
from contract_registry import PROMPT_CONTRACT_VERSION


def run(run_dir, source_path=None, expected_shots=None):
    run_dir = os.path.abspath(run_dir)
    issues = []

    state = _load_json(os.path.join(run_dir, ".cache", "pipeline_state.json"), issues)
    config = _load_json(os.path.join(run_dir, "project_config.json"), issues)
    plan = _load_json(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"), issues)
    package_path = os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json")
    package = _load_json(package_path, issues)
    validate_result = _load_json(os.path.join(run_dir, ".cache", "validate", "result.json"), issues)
    export_result = _load_json(os.path.join(run_dir, ".cache", "export", "result.json"), issues)

    _check_state(state, issues)
    _check_package(plan, package, expected_shots, issues)
    _check_source_manifest(run_dir, source_path, expected_shots, issues)
    _check_validate_result(package_path, validate_result, issues)
    markdown_path = _check_export_result(package_path, export_result, config, issues)
    _check_merge_provenance(package_path, issues)

    if os.path.isfile(package_path):
        if validate_modec(run_dir) != 0:
            issues.append("validate_modec failed")
    if markdown_path:
        _passed, failed = check_export(markdown_path, run_dir, quality_mode=False)
        if failed:
            issues.append("check_export failed with %s issue(s)" % failed)

    performance_path, performance = performance_report(run_dir)
    if not performance.get("completed"):
        issues.append("performance report says core pipeline is not completed")
    if expected_shots is not None and performance.get("main_shot_count") != expected_shots:
        issues.append("performance main_shot_count expected %s got %s" % (
            expected_shots, performance.get("main_shot_count")
        ))
    if expected_shots == 50 and performance.get("slo_eligible") is not True:
        issues.append("50-shot run must be SLO eligible")
    if expected_shots not in (None, 50) and performance.get("slo_eligible") is not False:
        issues.append("non-50-shot fixture must not be marked SLO eligible")

    result = {
        "pass": not issues,
        "run_dir": run_dir,
        "expected_shots": expected_shots,
        "markdown_path": markdown_path,
        "performance_report": performance_path,
        "issues": issues,
    }
    return result


def _check_state(state, issues):
    if not isinstance(state, dict):
        return
    phases = state.get("phases", {})
    for phase in PHASE_ORDER:
        status = phases.get(phase, {}).get("status") if isinstance(phases.get(phase), dict) else None
        if status != "done":
            issues.append("phase %s status expected done got %s" % (phase, status))


def _check_package(plan, package, expected_shots, issues):
    if not isinstance(package, dict):
        return
    shots = package.get("shots")
    if package.get("contract_version") != PROMPT_CONTRACT_VERSION:
        issues.append("package contract_version is not %s" % PROMPT_CONTRACT_VERSION)
    if not isinstance(shots, list) or not shots:
        issues.append("package shots[] missing or empty")
        return
    if expected_shots is not None and len(shots) != expected_shots:
        issues.append("package expected %s shots got %s" % (expected_shots, len(shots)))
    expected_source_ids = {
        str(subshot.get("subshot_id", "") or "")
        for shot in plan.get("shots", []) if isinstance(shot, dict)
        for subshot in shot.get("subshots", []) if isinstance(subshot, dict)
    }
    actual_source_ids = [
        source_id
        for shot in shots if isinstance(shot, dict)
        for source_id in _as_list(shot.get("source_subshot_ids", [shot.get("subshot_id", "")]))
    ]
    if set(actual_source_ids) != expected_source_ids or len(actual_source_ids) != len(expected_source_ids):
        issues.append("source_subshot_ids coverage mismatch")


def _check_source_manifest(run_dir, source_path, expected_shots, issues):
    manifest_path = os.path.join(run_dir, ".cache", "e2e_fixture_manifest.json")
    if not os.path.exists(manifest_path):
        return
    manifest = _load_json(manifest_path, issues)
    if expected_shots is not None and manifest.get("main_shot_count") != expected_shots:
        issues.append("fixture manifest expected %s shots got %s" % (
            expected_shots, manifest.get("main_shot_count")
        ))
    if source_path:
        source_path = os.path.abspath(source_path)
        if not os.path.isfile(source_path):
            issues.append("source file missing: " + source_path)
        elif manifest.get("source_sha256") != _sha256(source_path):
            issues.append("fixture source_sha256 does not match source file")


def _check_validate_result(package_path, validate_result, issues):
    if not isinstance(validate_result, dict):
        return
    if validate_result.get("pass") is not True:
        issues.append("validate result pass is not true")
    if os.path.isfile(package_path) and validate_result.get("package_sha256") != _sha256(package_path):
        issues.append("validate result package_sha256 is stale")


def _check_export_result(package_path, export_result, config, issues):
    if not isinstance(export_result, dict):
        return ""
    markdown_path = str(export_result.get("markdown_path", "") or "").strip()
    markdown_paths = export_result.get("markdown_paths") if isinstance(export_result.get("markdown_paths"), dict) else {}
    feed_paths = [str(path).strip() for path in markdown_paths.values() if str(path).strip()] or ([markdown_path] if markdown_path else [])
    index_path = str(export_result.get("index_markdown_path", "") or "").strip()
    configured_path = str(((config or {}).get("delivery") or {}).get("markdown_path", "") or "").strip()
    if export_result.get("pass") is not True:
        issues.append("export result pass is not true")
    if configured_path and not markdown_paths and os.path.abspath(configured_path) != os.path.abspath(markdown_path):
        issues.append("export markdown_path differs from confirmed delivery path")
    if not feed_paths or any(not os.path.isfile(path) for path in feed_paths) or (index_path and not os.path.isfile(index_path)):
        issues.append("exported markdown missing")
        return markdown_path
    if markdown_paths:
        expected_hashes = export_result.get("markdown_sha256_by_target", {})
        for target_path in feed_paths:
            target = next((key for key, value in markdown_paths.items() if os.path.abspath(str(value)) == os.path.abspath(target_path)), "")
            if target and expected_hashes.get(target) != _sha256(target_path):
                issues.append("export markdown_sha256_by_target is stale for " + target)
    elif export_result.get("markdown_sha256") != _sha256(markdown_path):
        issues.append("export markdown_sha256 is stale")
    if os.path.isfile(package_path) and export_result.get("package_sha256") != _sha256(package_path):
        issues.append("export package_sha256 is stale")
    xlsx_path = os.path.splitext(((configured_path or markdown_path)))[0] + ".xlsx"
    if not os.path.isfile(xlsx_path):
        issues.append("exported xlsx missing")
    return markdown_path


def _check_merge_provenance(package_path, issues):
    manifest_path = package_path + ".merge_provenance.json"
    manifest = _load_json(manifest_path, issues)
    if not isinstance(manifest, dict):
        return
    if manifest.get("output_path") != os.path.abspath(package_path):
        issues.append("merge provenance output_path mismatch")
    if os.path.isfile(package_path) and manifest.get("output_sha256") != _sha256(package_path):
        issues.append("merge provenance output_sha256 is stale")
    sources = manifest.get("source_batches", [])
    if not isinstance(sources, list) or not sources:
        issues.append("merge provenance has no source_batches")
        return
    for source in sources:
        batch_path = source.get("batch_path") if isinstance(source, dict) else ""
        valid, reason, _record = verify_batch_provenance(batch_path) if batch_path and os.path.exists(batch_path) else (False, "batch missing", None)
        if not valid:
            issues.append("invalid source batch provenance: " + reason)


def _load_json(path, issues):
    if not os.path.exists(path):
        issues.append("missing " + path)
        return {}
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            value = json.load(handle)
            return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError) as exc:
        issues.append("cannot parse %s: %s" % (path, exc))
        return {}


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _as_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.replace("；", ",").replace("、", ",").split(",") if part.strip()]
    return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--source")
    parser.add_argument("--expected-shots", type=int)
    args = parser.parse_args()
    outcome = run(args.run_dir, args.source, args.expected_shots)
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    raise SystemExit(0 if outcome["pass"] else 1)
