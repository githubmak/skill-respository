#!/usr/bin/env python3
"""Evaluate real 50-main-shot pipeline runs against the Jimeng SLO.

Usage:
  python3 benchmark_core_pipeline.py <run_dir> [<run_dir> ...]

Each run directory must contain a completed ``shot_plan.json`` and the
performance report written by ``performance_budget.py``.  This utility never
generates prompts or fabricates latency; it only summarizes measured runs.
"""

import argparse
import json
import math
import os
import sys


TARGET_SECONDS = 55 * 60
REQUIRED_SCENARIOS = {"dialogue", "action", "mixed"}


def evaluate(run_dirs):
    records = []
    for run_dir in run_dirs:
        records.append(_record(run_dir))
    valid = [item for item in records if not item["issues"]]
    elapsed = sorted(item["elapsed_seconds"] for item in valid if isinstance(item["elapsed_seconds"], (int, float)))
    p95 = _percentile(elapsed, 0.95) if elapsed else None
    dispatch_counts = sorted(item["total_dispatch_count"] for item in valid if isinstance(item.get("total_dispatch_count"), int))
    retry_counts = sorted(item["retry_count"] for item in valid if isinstance(item.get("retry_count"), int))
    scenarios = {item["scenario"] for item in valid if item["scenario"]}
    missing_scenarios = sorted(REQUIRED_SCENARIOS - scenarios)
    normal_scenarios = {item["scenario"] for item in valid if item["injected_failure_rate"] == 0}
    fault_scenarios = {item["scenario"] for item in valid if item["injected_failure_rate"] == 0.10}
    matrix = _coverage_matrix(valid)
    missing_cells = sorted(
        "%s@%s" % (scenario, "fail10" if failure_rate else "normal")
        for scenario in REQUIRED_SCENARIOS
        for failure_rate in (0, 0.10)
        if not matrix.get(scenario, {}).get(str(failure_rate), {}).get("count")
    )
    synthetic_count = sum(1 for item in valid if item.get("evidence_kind") != "real_pipeline")
    pass_basic = bool(
        len(valid) >= 6
        and not missing_scenarios
        and not missing_cells
        and REQUIRED_SCENARIOS <= normal_scenarios
        and REQUIRED_SCENARIOS <= fault_scenarios
        and p95 is not None
        and p95 <= TARGET_SECONDS
    )
    result = {
        "target_seconds": TARGET_SECONDS,
        "run_count": len(records),
        "valid_run_count": len(valid),
        "synthetic_fixture_count": synthetic_count,
        "p95_seconds": p95,
        "scenarios": sorted(scenarios),
        "missing_scenarios": missing_scenarios,
        "missing_matrix_cells": missing_cells,
        "normal_scenarios": sorted(normal_scenarios),
        "fault_injection_scenarios": sorted(fault_scenarios),
        "coverage_matrix": matrix,
        "dispatch_p95": _percentile(dispatch_counts, 0.95) if dispatch_counts else None,
        "retry_p95": _percentile(retry_counts, 0.95) if retry_counts else None,
        "pass": pass_basic,
        "real_slo_pass": pass_basic and synthetic_count == 0,
        "evidence_note": (
            "synthetic fixtures validate benchmark mechanics only; real SLO claims require real_pipeline evidence"
            if synthetic_count else "all valid runs are marked real_pipeline"
        ),
        "runs": records,
    }
    return result


def _record(run_dir):
    issues = []
    report = _load(os.path.join(run_dir, ".cache", "performance", "core_pipeline_budget.json"), issues)
    plan = _load(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"), issues)
    config = _load(os.path.join(run_dir, "project_config.json"), issues)
    if not isinstance(report, dict) or not report.get("completed"):
        issues.append("core pipeline is not completed")
    dispatch = report.get("dispatch_summary", {}) if isinstance(report, dict) else {}
    if not isinstance(dispatch, dict):
        issues.append("performance.dispatch_summary must be an object")
        dispatch = {}
    shot_count = len(plan.get("shots", [])) if isinstance(plan, dict) else 0
    if shot_count != 50:
        issues.append("expected exactly 50 main shots, got %s" % shot_count)
    scenario = str((config or {}).get("benchmark", {}).get("scenario", "") or "").strip().lower()
    if scenario not in REQUIRED_SCENARIOS:
        issues.append("project_config.benchmark.scenario must be dialogue/action/mixed")
    failure_rate = (config or {}).get("benchmark", {}).get("injected_failure_rate", 0)
    if failure_rate not in (0, 0.10):
        issues.append("injected_failure_rate must be 0 or 0.10")
    evidence_kind = str(
        ((config or {}).get("benchmark", {}) or {}).get("evidence_kind")
        or (report.get("evidence_kind") if isinstance(report, dict) else "")
        or "real_pipeline"
    ).strip()
    if evidence_kind not in ("real_pipeline", "synthetic_fixture"):
        issues.append("evidence_kind must be real_pipeline or synthetic_fixture")
    return {
        "run_dir": os.path.abspath(run_dir),
        "scenario": scenario,
        "injected_failure_rate": failure_rate,
        "evidence_kind": evidence_kind,
        "elapsed_seconds": report.get("elapsed_seconds") if isinstance(report, dict) else None,
        "total_dispatch_count": dispatch.get("total_dispatch_count"),
        "retry_count": dispatch.get("retry_count"),
        "stale_or_superseded_packet_count": dispatch.get("stale_or_superseded_packet_count"),
        "shot_count": shot_count,
        "issues": issues,
    }


def _load(path, issues):
    if not os.path.exists(path):
        issues.append("missing %s" % path)
        return {}
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        issues.append("cannot parse %s: %s" % (path, exc))
        return {}


def _percentile(values, q):
    if not values:
        return None
    index = (len(values) - 1) * q
    lower, upper = math.floor(index), math.ceil(index)
    if lower == upper:
        return round(values[lower], 3)
    return round(values[lower] + (values[upper] - values[lower]) * (index - lower), 3)


def _coverage_matrix(records):
    matrix = {
        scenario: {
            "0": {"count": 0, "elapsed_seconds": []},
            "0.1": {"count": 0, "elapsed_seconds": []},
        }
        for scenario in sorted(REQUIRED_SCENARIOS)
    }
    for record in records:
        scenario = record.get("scenario")
        rate = str(record.get("injected_failure_rate"))
        if scenario not in matrix or rate not in matrix[scenario]:
            continue
        cell = matrix[scenario][rate]
        cell["count"] += 1
        elapsed = record.get("elapsed_seconds")
        if isinstance(elapsed, (int, float)):
            cell["elapsed_seconds"].append(elapsed)
    for scenario in matrix:
        for rate in matrix[scenario]:
            values = matrix[scenario][rate]["elapsed_seconds"]
            matrix[scenario][rate]["p95_seconds"] = _percentile(sorted(values), 0.95) if values else None
    return matrix


def _write(path, data):
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate real completed 50-main-shot pipeline runs.")
    parser.add_argument("--out", help="Optional JSON report path for audit evidence.")
    parser.add_argument("run_dirs", nargs="+")
    args = parser.parse_args()
    outcome = evaluate(args.run_dirs)
    if args.out:
        _write(args.out, outcome)
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    raise SystemExit(0 if outcome["pass"] else 1)
