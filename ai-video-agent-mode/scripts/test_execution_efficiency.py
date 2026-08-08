#!/usr/bin/env python3
"""Offline scheduling and context-load regression for the production path."""

import json
import os
import tempfile

from contract_registry import PHASE_TIMEOUT_SECONDS, PROMPT_CONTRACT_VERSION
from dispatch_queue import plan_worker_leases, retire_timed_out_dispatches
from editor_scene_windows import build as build_editor_windows
from pipeline_runner import (
    _expand_scene_targets,
    _materialize,
    _record_creative_reauthor_round,
)
from pipeline_state import (
    init_state,
    load_state,
    reserve_dispatch_lease,
    start_leased_dispatch,
)


def _write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def _packets(run_dir, count):
    paths = []
    for index in range(count):
        dispatch_id = "D%03d" % (index + 1)
        path = os.path.join(run_dir, ".cache", "dispatch", dispatch_id + "_packet.json")
        _write(path, {
            "contract_version": PROMPT_CONTRACT_VERSION,
            "dispatch_id": dispatch_id,
            "dispatch_group_id": "G1",
            "dispatch_attempt": 1,
            "created_at": 1.0,
            "phase": "master_production",
            "run_dir": run_dir,
            "_batch_output_path": os.path.join(
                run_dir, ".cache", "composer", dispatch_id + ".prompt_package.json"
            ),
            "items": [{"shot_id": dispatch_id, "subshot_id": dispatch_id}],
        })
        paths.append(path)
    return paths


def test_persistent_worker_leases():
    with tempfile.TemporaryDirectory(prefix="worker-leases-") as run_dir:
        _write(os.path.join(run_dir, "project_config.json"), {"execution": {"worker_slots": 3}})
        init_state(run_dir)
        paths = _packets(run_dir, 8)
        leases = plan_worker_leases(run_dir, "master_production", paths)
        assert len(leases) == 3
        assert sorted(lease["packet_count"] for lease in leases) == [2, 3, 3]
        first = leases[0]
        records = [json.load(open(path, encoding="utf-8")) for path in first["packet_paths"]]
        reserve_dispatch_lease(
            run_dir, "master_production", "worker-A", first["lease_id"], records,
            leased_at=100.0,
        )
        state = load_state(run_dir)["phases"]["master_production"]["dispatches"]
        assert {state[row["dispatch_id"]]["agent_id"] for row in records} == {"worker-A"}
        assert all(state[row["dispatch_id"]]["spawn_time"] is None for row in records)

        start_leased_dispatch(
            run_dir, "master_production", "worker-A", records[0]["dispatch_id"],
            started_at=110.0,
        )
        timeout = PHASE_TIMEOUT_SECONDS["master_production"]
        recovery = retire_timed_out_dispatches(
            run_dir, "master_production", paths, now=100.0 + timeout + 1,
        )
        assert records[1]["dispatch_id"] not in recovery["retired_dispatch_ids"]
        state = load_state(run_dir)["phases"]["master_production"]["dispatches"]
        assert state[records[0]["dispatch_id"]]["spawn_time"] == 110.0
        assert state[records[1]["dispatch_id"]]["spawn_time"] is None


def test_scene_window_load():
    with tempfile.TemporaryDirectory(prefix="editor-scene-load-") as run_dir:
        shots = []
        package_shots = []
        for index in range(29):
            shot_id = "S%03d" % (index + 1)
            scene = "SC%02d" % (index // 4 + 1)
            shots.append({"shot_id": shot_id, "scene": scene})
            package_shots.append({"shot_id": shot_id})
        _write(
            os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"),
            {"shots": shots},
        )
        _write(
            os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json"),
            {"contract_version": PROMPT_CONTRACT_VERSION, "shots": package_shots},
        )
        windows = build_editor_windows(run_dir)
        reviewed_refs = sum(len(window["shot_ids"]) for window in windows)
        boundary_refs = sum(
            bool(window["previous_boundary_shot_id"]) + bool(window["next_boundary_shot_id"])
            for window in windows
        )
        assert len(windows) == 8
        assert reviewed_refs == 29
        assert reviewed_refs + boundary_refs <= 45
        assert all(window["capsule_version"] == "editor-scene-review-v3" for window in windows)

        for shot in shots:
            shot["scene"] = "ONE_SCENE"
        for shot in package_shots:
            shot["seedance_prompt"] = "完整模型创作" * 500
        _write(
            os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"),
            {"shots": shots},
        )
        _write(
            os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json"),
            {"contract_version": PROMPT_CONTRACT_VERSION, "shots": package_shots},
        )
        segmented = build_editor_windows(run_dir)
        assert len(segmented) >= 2
        assert [shot_id for window in segmented for shot_id in window["shot_ids"]] == [
            "S%03d" % (index + 1) for index in range(29)
        ]


def test_scene_scoped_reauthor_and_editor_merge():
    with tempfile.TemporaryDirectory(prefix="scene-reauthor-") as run_dir:
        init_state(run_dir)
        _write(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"), {
            "shots": [
                {"shot_id": "S1", "scene": "A"},
                {"shot_id": "S2", "scene": "A"},
                {"shot_id": "S3", "scene": "B"},
            ],
        })
        assert _expand_scene_targets(run_dir, ["S2"]) == ["S1", "S2"]
        review = {
            "windows": [{
                "window_id": "W001", "pass": False, "blocking": ["cause"],
                "return_to_phase": "master_production",
                "creative_cause": "same exact model cause",
                "affected_shot_ids": ["S2"],
            }],
        }
        assert _record_creative_reauthor_round(
            run_dir, review, "master_production"
        )["exhausted"] is False
        assert _record_creative_reauthor_round(
            run_dir, review, "master_production"
        )["exhausted"] is False
        assert _record_creative_reauthor_round(
            run_dir, review, "master_production"
        )["exhausted"] is True

        output = os.path.join(run_dir, ".cache", "review", "llm_gate_result.json")
        _write(output, {
            "windows": [{
                "window_id": "W001", "reviewed_shot_ids": ["S1", "S2"],
                "pass": True, "blocking": [],
            }],
        })
        batch = os.path.join(run_dir, ".cache", "review", "retry.json")
        _write(batch, {
            "windows": [{
                "window_id": "W002", "reviewed_shot_ids": ["S3"],
                "pass": True, "blocking": [],
            }],
        })
        _materialize("editor_pass2", output, [batch], preserve_existing=True)
        merged = json.load(open(output, encoding="utf-8"))
        assert [item["window_id"] for item in merged["windows"]] == ["W001", "W002"]


if __name__ == "__main__":
    test_persistent_worker_leases()
    test_scene_window_load()
    test_scene_scoped_reauthor_and_editor_merge()
    print("execution efficiency regression: PASS")
