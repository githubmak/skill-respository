#!/usr/bin/env python3
"""Regression checks for exact, cross-run validated creative reuse."""

import json
import os
import tempfile
import time

from contract_registry import PROMPT_CONTRACT_VERSION
from dispatch_receipts import heartbeat as receipt_heartbeat, issue as issue_receipt
from merge_agent_outputs import merge_agent_outputs
from pipeline_state import init_state, load_state, record_heartbeat, set_agent_id
from record_batch_provenance import record as record_batch_provenance
from performance_budget import _agent_phase_wall_seconds, _dispatch_active_union_seconds
from validation_receipt import create_receipt
from verified_reuse import (
    EDITOR_REVIEW,
    PACKAGE,
    SCENE_LOCKS,
    SHOT_PLAN,
    publish_run,
    reuse_agent_phase,
    reuse_orchestrator_blueprint,
    verify_phase_reuse,
)


def _write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def _config(export_base, style="model-authored-style", delivery="out.md"):
    return {
        "project_name": "reuse-fixture",
        "canvas": "16:9",
        "visual_style": style,
        "max_shot_duration": 15,
        "target_platform": "即梦",
        "seedance_target": "auto",
        "generation_control": {"mode": "t2v", "audio_enabled": True},
        "export_base": export_base,
        "delivery": {"markdown_path": os.path.join(export_base, delivery)},
        "confirmation": {"confirmed_at": delivery},
    }


def _source_fixture(run_dir, export_base):
    init_state(run_dir)
    _write(os.path.join(run_dir, "project_config.json"), _config(export_base))
    _write(os.path.join(run_dir, ".cache", "orchestrator", "source_snapshot.json"), {
        "source_sha256": "source-hash-1",
    })
    plan = {
        "shots": [
            {"shot_id": "S001", "subshots": [{"subshot_id": "S001", "duration": 5}]},
            {"shot_id": "S002", "subshots": [{"subshot_id": "S002", "duration": 6}]},
        ]
    }
    locks = {"scenes": [{"scene": "SC1", "space_id": "SPACE1", "model_owned": "unchanged"}]}
    _write(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.draft.json"), plan)
    _write(os.path.join(run_dir, SHOT_PLAN), plan)
    _write(os.path.join(run_dir, ".cache", "orchestrator", "scene_locks.draft.json"), locks)
    _write(os.path.join(run_dir, SCENE_LOCKS), locks)
    shots = [_valid_shot("S001", 5, "A"), _valid_shot("S002", 6, "B")]
    package_path = os.path.join(run_dir, PACKAGE)
    batch_path = os.path.join(run_dir, ".cache", "composer", "fixture.prompt_package.json")
    packet_path = os.path.join(run_dir, ".cache", "dispatch", "fixture_packet.json")
    packet = {
        "contract_version": PROMPT_CONTRACT_VERSION,
        "dispatch_id": "fixture-dispatch",
        "dispatch_group_id": "fixture-group",
        "phase": "master_production",
        "run_dir": run_dir,
        "source_path": os.path.join(run_dir, SHOT_PLAN),
        "_batch_output_path": batch_path,
        "items": [{"shot_id": shot["shot_id"], "subshot_id": shot["subshot_id"]} for shot in shots],
    }
    _write(packet_path, packet)
    spawn_time = time.time()
    set_agent_id(run_dir, "master_production", "fixture-worker", "fixture-dispatch", spawn_time=spawn_time)
    issue_receipt(packet_path, packet, "fixture-worker")
    record_heartbeat(run_dir, "master_production", "fixture-worker", "fixture-dispatch")
    receipt_heartbeat(packet_path, packet, "fixture-worker")
    _write(batch_path, {"shots": shots})
    record_batch_provenance(packet_path)
    merge_agent_outputs(package_path, batch_path, require_provenance=True)
    review_path = os.path.join(run_dir, EDITOR_REVIEW)
    _write(review_path, {
        "contract_version": PROMPT_CONTRACT_VERSION,
        "pass": True,
        "blocking": [],
        "windows": [
            {"window_id": "W001", "pass": True, "blocking": [], "current": {"shot_id": "S001"}},
            {"window_id": "W002", "pass": True, "blocking": [], "current": {"shot_id": "S002"}},
        ],
    })
    deterministic = os.path.join(run_dir, ".cache", "validate", "deterministic_package.json")
    _write(deterministic, {"pass": True, "package": "mechanically-validated"})
    create_receipt(run_dir, package_path, (deterministic,))


def _valid_shot(shot_id, duration, marker):
    return {
        "shot_id": shot_id,
        "subshot_id": shot_id,
        "source_subshot_ids": [shot_id],
        "duration": duration,
        "full_prompt": "model full prompt " + marker,
        "seedance_prompt": "model Seedance prompt " + marker,
        "director_card": "model director card " + marker,
        "negative_prompt": "model negative prompt " + marker,
        "qa_metadata": {"dialogue_refs": [], "dialogue_events": [], "unknown_model_field": marker},
        "generation_control": {"mode": "t2v", "audio_enabled": True},
    }


def _target_fixture(run_dir, export_base, source_hash="source-hash-1", style="model-authored-style"):
    _write(os.path.join(run_dir, "project_config.json"), _config(export_base, style=style, delivery="second.md"))
    _write(os.path.join(run_dir, ".cache", "orchestrator", "source_snapshot.json"), {
        "source_sha256": source_hash,
    })
    init_state(run_dir)


def test_verified_reuse_happy_path(root):
    export_base = os.path.join(root, "delivery")
    source_run = os.path.join(root, "source-run")
    target_run = os.path.join(root, "target-run")
    _source_fixture(source_run, export_base)
    record_path, published = publish_run(source_run)
    assert os.path.isfile(record_path)
    assert len(published["per_shot_output_hashes"]) == 2

    _target_fixture(target_run, export_base)
    orchestrator = reuse_orchestrator_blueprint(target_run)
    assert orchestrator["applied"] is True
    assert os.path.isfile(os.path.join(target_run, ".cache", "orchestrator", "shot_plan.draft.json"))

    # Normal Orchestrator normalization deterministically creates these files.
    _write(os.path.join(target_run, SHOT_PLAN), json.load(open(os.path.join(source_run, SHOT_PLAN), encoding="utf-8")))
    _write(os.path.join(target_run, SCENE_LOCKS), json.load(open(os.path.join(source_run, SCENE_LOCKS), encoding="utf-8")))
    master = reuse_agent_phase(target_run, "master_production")
    assert master["applied"] is True and master["reused_item_count"] == 2
    assert open(os.path.join(target_run, PACKAGE), "rb").read() == open(os.path.join(source_run, PACKAGE), "rb").read()
    merge_provenance = json.load(open(os.path.join(target_run, PACKAGE) + ".merge_provenance.json", encoding="utf-8"))
    assert merge_provenance["provenance_mode"] == "verified_reuse"
    assert verify_phase_reuse(target_run, "master_production")[0] is True

    editor = reuse_agent_phase(target_run, "editor_pass2")
    assert editor["applied"] is True and editor["reused_item_count"] == 2
    assert verify_phase_reuse(target_run, "editor_pass2")[0] is True


def test_reuse_rejects_changed_inputs(root):
    export_base = os.path.join(root, "delivery-reject")
    source_run = os.path.join(root, "source-reject")
    _source_fixture(source_run, export_base)
    publish_run(source_run)

    changed_source = os.path.join(root, "changed-source")
    _target_fixture(changed_source, export_base, source_hash="different")
    assert reuse_orchestrator_blueprint(changed_source)["applied"] is False

    changed_config = os.path.join(root, "changed-config")
    _target_fixture(changed_config, export_base, style="different-style")
    assert reuse_orchestrator_blueprint(changed_config)["applied"] is False

    changed_plan = os.path.join(root, "changed-plan")
    _target_fixture(changed_plan, export_base)
    assert reuse_orchestrator_blueprint(changed_plan)["applied"] is True
    _write(os.path.join(changed_plan, SHOT_PLAN), {"shots": [{"shot_id": "DIFFERENT"}]})
    _write(os.path.join(changed_plan, SCENE_LOCKS), json.load(open(os.path.join(source_run, SCENE_LOCKS), encoding="utf-8")))
    assert reuse_agent_phase(changed_plan, "master_production")["applied"] is False

    # A changed source artifact invalidates both its publication hash and final
    # validation receipt; it can never be accepted by a later run.
    _write(os.path.join(source_run, PACKAGE), {
        "contract_version": PROMPT_CONTRACT_VERSION,
        "shots": [{"shot_id": "S001", "subshot_id": "S001", "model_creative_payload": {"prompt": "tampered"}}],
    })
    fresh_target = os.path.join(root, "after-tamper")
    _target_fixture(fresh_target, export_base)
    assert reuse_orchestrator_blueprint(fresh_target)["applied"] is False


def test_phase_timing_preserves_first_worker_start(root):
    run_dir = os.path.join(root, "timing")
    init_state(run_dir)
    set_agent_id(run_dir, "master_production", "worker-1", "dispatch-1", spawn_time=100.0)
    set_agent_id(run_dir, "master_production", "worker-2", "dispatch-2", spawn_time=220.0)
    phase = load_state(run_dir)["phases"]["master_production"]
    assert phase["started_at"] == 100.0
    assert phase["spawn_time"] == 100.0
    assert phase["dispatches"]["dispatch-2"]["spawn_time"] == 220.0
    active_union = _dispatch_active_union_seconds({
        "a": {"spawn_time": 100.0, "recorded_at": 160.0},
        "b": {"spawn_time": 140.0, "recorded_at": 200.0},
        "c": {"spawn_time": 230.0, "recorded_at": 250.0},
    })
    assert active_union == 120.0
    inferred = _agent_phase_wall_seconds(
        {"completed_at": 300.0, "elapsed_seconds": 80.0},
        {"a": {"spawn_time": 100.0, "recorded_at": 160.0}, "b": {"spawn_time": 220.0, "recorded_at": 260.0}},
        now=400.0,
    )
    assert inferred == 200.0


def run():
    with tempfile.TemporaryDirectory(prefix="verified-reuse-") as root:
        test_verified_reuse_happy_path(root)
        test_reuse_rejects_changed_inputs(root)
        test_phase_timing_preserves_first_worker_start(root)
    print("verified reuse regression: PASS")


if __name__ == "__main__":
    run()
