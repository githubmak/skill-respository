#!/usr/bin/env python3
"""Run the standard ai-video-agent-mode regression suite.

This wrapper does not create Agent outputs.  It runs deterministic contract
tests, optional source smoke checks, optional completed-run E2E verification,
and an optional benchmark guard/report.
"""

import argparse
import json
import os
import subprocess
import sys
import time

from benchmark_core_pipeline import evaluate as evaluate_benchmark
from create_benchmark_fixtures import create as create_benchmark_fixtures


SCRIPT_DIR = os.path.dirname(__file__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", help="Optional source text for smoke test.")
    parser.add_argument("--min-shots", type=int, default=1)
    parser.add_argument("--completed-run", help="Optional completed real E2E run_dir to verify.")
    parser.add_argument("--expected-shots", type=int)
    parser.add_argument("--benchmark-report", help="Optional benchmark JSON path.")
    parser.add_argument("--synthetic-benchmark-dir", help="Optional output directory for deterministic 6x50 benchmark fixtures.")
    args = parser.parse_args()

    steps = []
    steps.append(_run("rule_consistency", [sys.executable, _script("check_rule_consistency.py")]))
    steps.append(_run("source_gate", [sys.executable, _script("test_source_gate.py")]))
    steps.append(_run("preflight_severity", [sys.executable, _script("test_preflight_severity.py")]))
    steps.append(_run("preproduction_quality_plans", [sys.executable, _script("test_preproduction_quality_plans.py")]))
    steps.append(_run("fast_start", [sys.executable, _script("test_fast_start.py")]))
    steps.append(_run("structure", [sys.executable, _script("test_current_pipeline.py")]))
    steps.append(_run("quality_upgrades", [sys.executable, _script("test_quality_upgrades.py")]))
    steps.append(_run("production_intelligence", [sys.executable, _script("test_production_intelligence.py")]))
    steps.append(_run("quality_control_matrix", [sys.executable, _script("test_quality_control_matrix.py")]))
    steps.append(_run("keyframe_pipeline", [sys.executable, _script("test_keyframe_pipeline.py")]))
    steps.append(_run("visual_ab_review", [sys.executable, _script("test_visual_ab_review.py")]))
    steps.append(_run("golden_jimeng", [sys.executable, _script("golden_jimeng_check.py")]))
    if args.source:
        steps.append(_run("source_smoke", [
            sys.executable, _script("test_source_smoke.py"),
            "--source", args.source,
            "--min-shots", str(args.min_shots),
        ]))
    if args.completed_run:
        command = [
            sys.executable, _script("test_completed_e2e_run.py"),
            "--run-dir", args.completed_run,
        ]
        if args.source:
            command.extend(["--source", args.source])
        if args.expected_shots is not None:
            command.extend(["--expected-shots", str(args.expected_shots)])
        steps.append(_run("completed_e2e", command))
    if args.benchmark_report and args.completed_run:
        command = [
            sys.executable, _script("benchmark_core_pipeline.py"),
            "--out", args.benchmark_report,
            args.completed_run,
        ]
        steps.append(_run_benchmark_guard(command, args.expected_shots))
    if args.synthetic_benchmark_dir:
        steps.append(_run_synthetic_benchmark(args.synthetic_benchmark_dir))

    result = {
        "pass": all(step["pass"] for step in steps),
        "steps": steps,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["pass"] else 1)


def _script(name):
    return os.path.join(SCRIPT_DIR, name)


def _run(name, command):
    started = time.time()
    proc = subprocess.run(command, text=True, capture_output=True)
    return {
        "name": name,
        "pass": proc.returncode == 0,
        "returncode": proc.returncode,
        "elapsed_seconds": round(time.time() - started, 3),
        "stdout_tail": _tail(proc.stdout),
        "stderr_tail": _tail(proc.stderr),
        "command": command,
    }


def _run_benchmark_guard(command, expected_shots):
    started = time.time()
    proc = subprocess.run(command, text=True, capture_output=True)
    should_pass = expected_shots == 50
    passed = (proc.returncode == 0) if should_pass else (proc.returncode != 0)
    return {
        "name": "benchmark_guard" if not should_pass else "benchmark_50shot",
        "pass": passed,
        "returncode": proc.returncode,
        "expected_benchmark_pass": should_pass,
        "elapsed_seconds": round(time.time() - started, 3),
        "stdout_tail": _tail(proc.stdout),
        "stderr_tail": _tail(proc.stderr),
        "command": command,
    }


def _run_synthetic_benchmark(out_dir):
    started = time.time()
    try:
        run_dirs = create_benchmark_fixtures(out_dir)
        outcome = evaluate_benchmark(run_dirs)
        report_path = os.path.join(out_dir, "benchmark_report.json")
        os.makedirs(out_dir, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as handle:
            json.dump(outcome, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        passed = outcome.get("pass") is True and outcome.get("real_slo_pass") is False
        return {
            "name": "synthetic_50shot_benchmark",
            "pass": passed,
            "returncode": 0 if passed else 1,
            "elapsed_seconds": round(time.time() - started, 3),
            "report_path": report_path,
            "stdout_tail": json.dumps(outcome, ensure_ascii=False, indent=2)[-3000:],
            "stderr_tail": "",
            "command": ["create_benchmark_fixtures+benchmark_core_pipeline", out_dir],
        }
    except Exception as exc:
        return {
            "name": "synthetic_50shot_benchmark",
            "pass": False,
            "returncode": 1,
            "elapsed_seconds": round(time.time() - started, 3),
            "stdout_tail": "",
            "stderr_tail": str(exc),
            "command": ["create_benchmark_fixtures+benchmark_core_pipeline", out_dir],
        }


def _tail(text, limit=3000):
    text = str(text or "")
    return text[-limit:]


if __name__ == "__main__":
    main()
