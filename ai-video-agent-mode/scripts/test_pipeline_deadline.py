#!/usr/bin/env python3
"""Deterministic deadline and dispatch-recovery regression tests."""

import json
import os
import tempfile

from contract_registry import PIPELINE_HARD_DEADLINE_SECONDS, PROMPT_CONTRACT_VERSION
from dispatch_cache import active_packet_paths
from dispatch_queue import retire_timed_out_dispatches
from pipeline_deadline import feasibility, fuse, status
from pipeline_state import PHASE_TIMEOUT_SECONDS, init_state, load_state, save_state, set_agent_id


def _write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def _packet(run_dir, dispatch_id="dispatch-original", attempt=1, with_manifest=True):
    directory = os.path.join(run_dir, ".cache", "dispatch")
    path = os.path.join(directory, "master_production_original_packet.json")
    output = os.path.join(run_dir, ".cache", "composer", "batch_original.prompt_package.json")
    packet = {
        "contract_version": PROMPT_CONTRACT_VERSION,
        "dispatch_id": dispatch_id,
        "dispatch_group_id": "group-1",
        "dispatch_attempt": attempt,
        "created_at": 100.0,
        "phase": "master_production",
        "run_dir": run_dir,
        "source_path": os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"),
        "source_sha256": "fixture",
        "_batch_output_path": output,
        "items": [{"shot_id": "S1", "subshot_id": "S1"}],
    }
    _write(path, packet)
    if with_manifest:
        _write(os.path.join(directory, "active_master_production_manifest.json"), {
            "contract_version": PROMPT_CONTRACT_VERSION,
            "phase": "master_production",
            "packets": [{
                "packet_path": path,
                "dispatch_id": dispatch_id,
                "shot_ids": ["S1"],
                "effective": True,
                "attempt": attempt,
            }],
        })
    return path


def test_deadline_and_report():
    with tempfile.TemporaryDirectory() as run_dir:
        init_state(run_dir)
        state = load_state(run_dir)
        state["pipeline_started_at"] = 100.0
        state["pipeline_deadline_at"] = 100.0 + PIPELINE_HARD_DEADLINE_SECONDS
        state["current_phase"] = "master_production"
        state["phases"]["master_production"].update({
            "status": "running",
            "dispatches": {"D1": {"status": "running", "spawn_time": 120.0}},
        })
        expired = status(state, now=100.0 + PIPELINE_HARD_DEADLINE_SECONDS)
        assert expired["expired"] is True and expired["remaining_seconds"] == 0
        report = fuse(run_dir, state, "hard_deadline_exceeded",
                      now=100.0 + PIPELINE_HARD_DEADLINE_SECONDS)
        assert report["status"] == "fused"
        assert report["retired_dispatch_ids"] == ["D1"]
        assert os.path.isfile(os.path.join(run_dir, ".cache", "control", "fuse_report.json"))


def test_feasibility_uses_real_worker_cap():
    with tempfile.TemporaryDirectory() as run_dir:
        _write(os.path.join(run_dir, "project_config.json"), {"execution": {"worker_slots": 99}})
        init_state(run_dir)
        state = load_state(run_dir)
        state["pipeline_started_at"] = 0.0
        state["pipeline_deadline_at"] = 1000.0
        state["current_phase"] = "master_production"
        # Four remaining packets require two waves because the executable cap is
        # three workers, even when a project config claims more slots.
        forecast = feasibility(run_dir, state, packet_count=4, now=0.0)
        assert forecast["estimated_remaining_seconds"] > 1000
        assert forecast["feasible"] is False


def test_unique_timeout_replacement_and_completed_preservation():
    with tempfile.TemporaryDirectory() as run_dir:
        init_state(run_dir)
        packet_path = _packet(run_dir)
        spawn = 200.0
        set_agent_id(run_dir, "master_production", "worker-1",
                     dispatch_id="dispatch-original", spawn_time=spawn)
        now = spawn + PHASE_TIMEOUT_SECONDS["master_production"] + 1
        recovery = retire_timed_out_dispatches(
            run_dir, "master_production", [packet_path], now=now,
        )
        assert recovery["retired_dispatch_ids"] == ["dispatch-original"]
        assert not recovery["exhausted_dispatch_ids"]
        replacement = recovery["replacement_packets"][0]
        assert replacement["dispatch_id"] != "dispatch-original"
        assert replacement["attempt"] == 2
        assert os.path.isfile(replacement["packet_path"])
        replacement_packet = json.load(open(replacement["packet_path"], encoding="utf-8"))
        assert replacement_packet["_batch_output_path"] != json.load(open(packet_path, encoding="utf-8"))["_batch_output_path"]
        state = load_state(run_dir)
        assert state["phases"]["master_production"]["dispatches"]["dispatch-original"]["status"] == "timed_out"

    with tempfile.TemporaryDirectory() as run_dir:
        init_state(run_dir)
        packet_path = _packet(run_dir)
        spawn = 200.0
        set_agent_id(run_dir, "master_production", "worker-1",
                     dispatch_id="dispatch-original", spawn_time=spawn)
        recovery = retire_timed_out_dispatches(
            run_dir, "master_production", [packet_path],
            verified_dispatch_ids={"dispatch-original"},
            now=spawn + PHASE_TIMEOUT_SECONDS["master_production"] + 1,
        )
        assert recovery["retired_dispatch_ids"] == []
        assert recovery["replacement_packets"] == []


def test_retry_exhaustion():
    with tempfile.TemporaryDirectory() as run_dir:
        init_state(run_dir)
        packet_path = _packet(run_dir, attempt=3)
        spawn = 200.0
        set_agent_id(run_dir, "master_production", "worker-3",
                     dispatch_id="dispatch-original", spawn_time=spawn)
        recovery = retire_timed_out_dispatches(
            run_dir, "master_production", [packet_path],
            now=spawn + PHASE_TIMEOUT_SECONDS["master_production"] + 1,
        )
        assert recovery["exhausted_dispatch_ids"] == ["dispatch-original"]
        assert recovery["replacement_packets"] == []


def test_legacy_queue_manifest_is_rebuilt():
    with tempfile.TemporaryDirectory() as run_dir:
        init_state(run_dir)
        packet_path = _packet(run_dir, with_manifest=False)
        spawn = 200.0
        set_agent_id(run_dir, "master_production", "worker-legacy",
                     dispatch_id="dispatch-original", spawn_time=spawn)
        recovery = retire_timed_out_dispatches(
            run_dir, "master_production", [packet_path],
            now=spawn + PHASE_TIMEOUT_SECONDS["master_production"] + 1,
        )
        active = active_packet_paths(run_dir, "master_production")
        assert active == [recovery["replacement_packets"][0]["packet_path"]]
        assert packet_path not in active


if __name__ == "__main__":
    test_deadline_and_report()
    test_feasibility_uses_real_worker_cap()
    test_unique_timeout_replacement_and_completed_preservation()
    test_retry_exhaustion()
    test_legacy_queue_manifest_is_rebuilt()
    print("[PIPELINE DEADLINE] PASS")
