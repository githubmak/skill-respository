#!/usr/bin/env python3
"""Create deterministic 50-main-shot benchmark fixture runs.

These fixtures exercise the benchmark guard and reporting contract.  They are
not real sub-agent latency evidence; ``benchmark_core_pipeline.py`` preserves
that distinction with ``evidence_kind=synthetic_fixture``.
"""

import argparse
import json
import os
import time


SCENARIOS = ("dialogue", "action", "mixed")
FAILURE_RATES = (0, 0.10)


def create(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    run_dirs = []
    for scenario in SCENARIOS:
        for failure_rate in FAILURE_RATES:
            suffix = "normal" if failure_rate == 0 else "fail10"
            run_dir = os.path.join(out_dir, "%s_%s_50shot" % (scenario, suffix))
            _write_fixture(run_dir, scenario, failure_rate)
            run_dirs.append(run_dir)
    return run_dirs


def _write_fixture(run_dir, scenario, failure_rate):
    os.makedirs(os.path.join(run_dir, ".cache", "orchestrator"), exist_ok=True)
    os.makedirs(os.path.join(run_dir, ".cache", "performance"), exist_ok=True)
    shot_plan = {
        "project_name": "synthetic_%s_%s" % (scenario, "fail10" if failure_rate else "normal"),
        "total_shots": 50,
        "shots": [_shot(index, scenario) for index in range(1, 51)],
    }
    elapsed_seconds = _elapsed_seconds(scenario, failure_rate)
    project_config = {
        "generation_control": {"mode": "t2v", "audio_enabled": scenario != "action"},
        "benchmark": {
            "scenario": scenario,
            "injected_failure_rate": failure_rate,
            "evidence_kind": "synthetic_fixture",
            "note": "Constructed fixture for benchmark guard regression; not real Agent SLO evidence.",
        },
    }
    performance = {
        "target_seconds": 55 * 60,
        "elapsed_seconds": elapsed_seconds,
        "time_breakdown": {
            "wall_clock_seconds": elapsed_seconds,
            "local_compute_seconds": round(elapsed_seconds * 0.08, 3),
            "worker_wait_wall_seconds": round(elapsed_seconds * 0.82, 3),
            "dispatch_worker_seconds": round(elapsed_seconds * 2.4, 3),
            "unattributed_or_pause_seconds": round(elapsed_seconds * 0.10, 3),
        },
        "dispatch_summary": {
            "total_dispatch_count": 12 if failure_rate == 0 else 18,
            "done_dispatch_count": 12 if failure_rate == 0 else 18,
            "running_dispatch_count": 0,
            "waiting_dispatch_count": 0,
            "failed_dispatch_count": 0,
            "retry_count": 0 if failure_rate == 0 else 5,
            "manifest_active_packet_count": 12 if failure_rate == 0 else 13,
            "manifest_active_retry_packet_count": 0 if failure_rate == 0 else 5,
            "manifest_superseded_packet_count": 0 if failure_rate == 0 else 5,
            "stale_or_superseded_packet_count": 0 if failure_rate == 0 else 5,
        },
        "completed": True,
        "main_shot_count": 50,
        "slo_eligible": True,
        "within_target": elapsed_seconds <= 55 * 60,
        "evidence_kind": "synthetic_fixture",
        "scope": "main shots",
        "generated_at": time.time(),
    }
    _write_json(os.path.join(run_dir, "project_config.json"), project_config)
    _write_json(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"), shot_plan)
    _write_json(os.path.join(run_dir, ".cache", "performance", "core_pipeline_budget.json"), performance)


def _shot(index, scenario):
    shot_id = "S%03d" % index
    if scenario == "dialogue":
        action = "角色A与角色B在固定空间内完成一句对白与一个倾听反应"
        shot_type = "dialogue"
    elif scenario == "action":
        action = "角色A完成一次接近、接触、移动、稳定终态的动作链"
        shot_type = "action"
    else:
        action = "角色A说话后递出道具，角色B接住并留下反应"
        shot_type = "mixed"
    return {
        "shot_id": shot_id,
        "scene": "合成测试场景",
        "total_duration": 6.0,
        "core_action": action,
        "subshots": [{
            "subshot_id": shot_id + "-01",
            "duration": 6.0,
            "shot_size": "中景",
            "shot_type": shot_type,
            "base_action": action,
            "characters": ["角色A", "角色B"] if scenario != "action" else ["角色A"],
            "dialogue_refs": ["D%03d" % index] if scenario in ("dialogue", "mixed") else [],
        }],
    }


def _elapsed_seconds(scenario, failure_rate):
    base = {"dialogue": 2380, "action": 2620, "mixed": 2870}[scenario]
    return float(base + (260 if failure_rate else 0))


def _write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Create synthetic 50-shot benchmark fixture run directories.")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    run_dirs = create(args.out_dir)
    print(json.dumps({"run_dirs": run_dirs}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
