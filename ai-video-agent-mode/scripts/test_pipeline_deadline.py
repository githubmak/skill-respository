#!/usr/bin/env python3
"""Deterministic deadline and dispatch-recovery regression tests."""

import json
import os
import tempfile

from contract_registry import (
    PHASE_STARTUP_PROGRESS_SECONDS,
    PHASE_STALL_PROGRESS_SECONDS,
    PIPELINE_HARD_DEADLINE_SECONDS,
    PIPELINE_FORECAST_UNCERTAINTY_SECONDS,
    PROMPT_CONTRACT_VERSION,
)
from dispatch_cache import active_packet_paths
from dispatch_queue import retire_timed_out_dispatches
from dispatch_receipts import heartbeat as receipt_heartbeat, issue as issue_receipt
from pipeline_deadline import feasibility, fuse, status
from pipeline_state import (
    PHASE_TIMEOUT_SECONDS,
    init_state,
    load_state,
    mark_pipeline_complete,
    record_heartbeat,
    save_state,
    set_agent_id,
)


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


def _editor_packet(run_dir):
    directory = os.path.join(run_dir, ".cache", "dispatch")
    path = os.path.join(directory, "editor_pass2_original_packet.json")
    output = os.path.join(run_dir, ".cache", "review", "editor_checkpoint.json")
    packet = {
        "contract_version": PROMPT_CONTRACT_VERSION,
        "dispatch_id": "editor-original",
        "dispatch_group_id": "editor-group",
        "dispatch_attempt": 1,
        "created_at": 100.0,
        "phase": "editor_pass2",
        "run_dir": run_dir,
        "source_path": os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json"),
        "source_sha256": "fixture",
        "_batch_output_path": output,
        "items": [{"window_id": "W001"}, {"window_id": "W002"}],
    }
    _write(path, packet)
    _write(output, {"windows": [{
        "window_id": "W001", "pass": True, "blocking": [],
        "return_to_phase": None, "affected_shot_ids": [], "creative_cause": "",
    }]})
    _write(os.path.join(directory, "active_editor_pass2_manifest.json"), {
        "contract_version": PROMPT_CONTRACT_VERSION,
        "phase": "editor_pass2",
        "packets": [{"packet_path": path, "dispatch_id": "editor-original", "effective": True}],
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


def test_forecast_uncertainty_does_not_extend_hard_deadline():
    with tempfile.TemporaryDirectory() as run_dir:
        init_state(run_dir)
        state = load_state(run_dir)
        state["pipeline_started_at"] = 0.0
        state["pipeline_deadline_at"] = 1000.0
        state["current_phase"] = "export"
        near = feasibility(run_dir, state, now=950.0)
        assert near["forecast_overrun_seconds"] <= PIPELINE_FORECAST_UNCERTAINTY_SECONDS
        assert near["feasible"] is True
        expired = feasibility(run_dir, state, now=1000.0)
        assert expired["expired"] is True
        assert expired["feasible"] is False


def test_terminal_state_is_persisted():
    with tempfile.TemporaryDirectory() as run_dir:
        init_state(run_dir)
        state = load_state(run_dir)
        state["pipeline_started_at"] = 100.0
        state["phases"]["export"]["completed_at"] = 125.0
        save_state(run_dir, state)
        completed = mark_pipeline_complete(run_dir)
        assert completed["pipeline_status"] == "completed"
        assert completed["pipeline_completed_at"] == 125.0
        assert completed["pipeline_elapsed_seconds"] == 25.0
        assert load_state(run_dir)["pipeline_status"] == "completed"


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


def test_timeout_reuses_validated_checkpoint_items():
    with tempfile.TemporaryDirectory() as run_dir:
        init_state(run_dir)
        packet_path = _editor_packet(run_dir)
        spawn = 200.0
        set_agent_id(run_dir, "editor_pass2", "editor-worker", dispatch_id="editor-original", spawn_time=spawn)
        recovery = retire_timed_out_dispatches(
            run_dir, "editor_pass2", [packet_path],
            now=spawn + PHASE_TIMEOUT_SECONDS["editor_pass2"] + 1,
        )
        reuse = recovery["replacement_packets"][0]["checkpoint_reuse"]
        assert reuse["validated_item_ids"] == ["W001"]
        replacement = json.load(open(recovery["replacement_packets"][0]["packet_path"], encoding="utf-8"))
        assert replacement["checkpoint_reuse"]["path"].endswith("editor_checkpoint.json")


def test_liveness_heartbeats_do_not_hide_startup_content_stall():
    with tempfile.TemporaryDirectory() as run_dir:
        init_state(run_dir)
        packet_path = _packet(run_dir)
        spawn = 200.0
        set_agent_id(run_dir, "master_production", "worker-1",
                     dispatch_id="dispatch-original", spawn_time=spawn)
        record_heartbeat(run_dir, "master_production", "worker-1", "dispatch-original",
                         progress={"output_exists": False, "output_bytes": 0,
                                   "completed_item_count": 0, "output_parseable": False},
                         observed_at=spawn + 60)
        record_heartbeat(run_dir, "master_production", "worker-1", "dispatch-original",
                         progress={"output_exists": False, "output_bytes": 0,
                                   "completed_item_count": 0, "output_parseable": False},
                         observed_at=spawn + PHASE_STARTUP_PROGRESS_SECONDS["master_production"] - 1)
        recovery = retire_timed_out_dispatches(
            run_dir, "master_production", [packet_path], now=spawn + PHASE_STARTUP_PROGRESS_SECONDS["master_production"] + 1
        )
        assert recovery["retirement_reasons"]["dispatch-original"] == "startup_content_stall"
        assert recovery["replacement_packets"]


def test_content_growth_resets_progress_stall_timer():
    with tempfile.TemporaryDirectory() as run_dir:
        init_state(run_dir)
        packet_path = _packet(run_dir)
        spawn = 200.0
        set_agent_id(run_dir, "master_production", "worker-1",
                     dispatch_id="dispatch-original", spawn_time=spawn)
        progress_one = {"output_exists": True, "output_bytes": 100,
                        "completed_item_count": 1, "output_parseable": True}
        record_heartbeat(run_dir, "master_production", "worker-1", "dispatch-original",
                         progress=progress_one, observed_at=spawn + 100)
        recovery = retire_timed_out_dispatches(
            run_dir, "master_production", [packet_path], now=spawn + 100 + PHASE_STALL_PROGRESS_SECONDS["master_production"] - 1
        )
        assert recovery["retired_dispatch_ids"] == []
        progress_two = dict(progress_one, output_bytes=200, completed_item_count=2)
        record_heartbeat(run_dir, "master_production", "worker-1", "dispatch-original",
                         progress=progress_two, observed_at=spawn + 100 + PHASE_STALL_PROGRESS_SECONDS["master_production"] - 1)
        recovery = retire_timed_out_dispatches(
            run_dir, "master_production", [packet_path], now=spawn + 100 + 2 * PHASE_STALL_PROGRESS_SECONDS["master_production"] - 2
        )
        assert recovery["retired_dispatch_ids"] == []
        recovery = retire_timed_out_dispatches(
            run_dir, "master_production", [packet_path], now=spawn + 100 + 2 * PHASE_STALL_PROGRESS_SECONDS["master_production"] + 1
        )
        assert recovery["retirement_reasons"]["dispatch-original"] == "content_progress_stall"


def test_absolute_timeout_precedes_content_stall():
    with tempfile.TemporaryDirectory() as run_dir:
        init_state(run_dir)
        packet_path = _packet(run_dir)
        spawn = 200.0
        set_agent_id(run_dir, "master_production", "worker-1",
                     dispatch_id="dispatch-original", spawn_time=spawn)
        record_heartbeat(run_dir, "master_production", "worker-1", "dispatch-original",
                         progress={"output_exists": True, "output_bytes": 100,
                                   "completed_item_count": 1, "output_parseable": True},
                         observed_at=spawn + PHASE_TIMEOUT_SECONDS["master_production"] - 10)
        recovery = retire_timed_out_dispatches(
            run_dir, "master_production", [packet_path], now=spawn + PHASE_TIMEOUT_SECONDS["master_production"] + 1
        )
        assert recovery["retirement_reasons"]["dispatch-original"] == "absolute_packet_timeout"


def test_receipt_records_content_progress_separately_from_liveness():
    with tempfile.TemporaryDirectory() as run_dir:
        packet_path = _packet(run_dir)
        packet = json.load(open(packet_path, encoding="utf-8"))
        issue_receipt(packet_path, packet, "worker-1")
        no_progress, _ = receipt_heartbeat(
            packet_path, packet, "worker-1",
            progress={"output_exists": False, "output_bytes": 0,
                      "completed_item_count": 0, "output_parseable": False},
            observed_at=100.0,
        )
        assert no_progress["heartbeat_count"] == 1
        assert no_progress["progress_count"] == 0
        progressed, _ = receipt_heartbeat(
            packet_path, packet, "worker-1",
            progress={"output_exists": True, "output_bytes": 120,
                      "completed_item_count": 1, "output_parseable": True},
            observed_at=120.0,
        )
        assert progressed["heartbeat_count"] == 2
        assert progressed["progress_count"] == 1
        assert progressed["first_progress_at"] == 120.0


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
    test_forecast_uncertainty_does_not_extend_hard_deadline()
    test_terminal_state_is_persisted()
    test_unique_timeout_replacement_and_completed_preservation()
    test_timeout_reuses_validated_checkpoint_items()
    test_liveness_heartbeats_do_not_hide_startup_content_stall()
    test_content_growth_resets_progress_stall_timer()
    test_absolute_timeout_precedes_content_stall()
    test_receipt_records_content_progress_separately_from_liveness()
    test_retry_exhaustion()
    test_legacy_queue_manifest_is_rebuilt()
    print("[PIPELINE DEADLINE] PASS")
