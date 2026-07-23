#!/usr/bin/env python3
"""Evaluate real 50-main-shot pipeline runs against the Jimeng SLO.

Usage:
  python3 benchmark_core_pipeline.py <run_dir> [<run_dir> ...]

Each run directory must contain a completed ``shot_plan.json`` and the
performance report written by ``performance_budget.py``.  This utility never
generates prompts or fabricates latency; it only summarizes measured runs.
"""

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
    scenarios = {item["scenario"] for item in valid if item["scenario"]}
    missing_scenarios = sorted(REQUIRED_SCENARIOS - scenarios)
    normal_scenarios = {item["scenario"] for item in valid if item["injected_failure_rate"] == 0}
    fault_scenarios = {item["scenario"] for item in valid if item["injected_failure_rate"] == 0.10}
    result = {
        "target_seconds": TARGET_SECONDS,
        "run_count": len(records),
        "valid_run_count": len(valid),
        "p95_seconds": p95,
        "scenarios": sorted(scenarios),
        "missing_scenarios": missing_scenarios,
        "normal_scenarios": sorted(normal_scenarios),
        "fault_injection_scenarios": sorted(fault_scenarios),
        "pass": bool(
            len(valid) >= 6
            and not missing_scenarios
            and REQUIRED_SCENARIOS <= normal_scenarios
            and REQUIRED_SCENARIOS <= fault_scenarios
            and p95 is not None
            and p95 <= TARGET_SECONDS
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
    shot_count = len(plan.get("shots", [])) if isinstance(plan, dict) else 0
    if shot_count != 50:
        issues.append("expected exactly 50 main shots, got %s" % shot_count)
    scenario = str((config or {}).get("benchmark", {}).get("scenario", "") or "").strip().lower()
    if scenario not in REQUIRED_SCENARIOS:
        issues.append("project_config.benchmark.scenario must be dialogue/action/mixed")
    failure_rate = (config or {}).get("benchmark", {}).get("injected_failure_rate", 0)
    if failure_rate not in (0, 0.10):
        issues.append("injected_failure_rate must be 0 or 0.10")
    return {
        "run_dir": os.path.abspath(run_dir),
        "scenario": scenario,
        "injected_failure_rate": failure_rate,
        "elapsed_seconds": report.get("elapsed_seconds") if isinstance(report, dict) else None,
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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: benchmark_core_pipeline.py <run_dir> [<run_dir> ...]")
    outcome = evaluate(sys.argv[1:])
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    raise SystemExit(0 if outcome["pass"] else 1)
