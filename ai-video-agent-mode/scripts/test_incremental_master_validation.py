#!/usr/bin/env python3
"""Regression checks for scoped Composer validation and retry planning."""

import json
import io
import os
import tempfile
from contextlib import redirect_stdout

from incremental_validation import ALL_MUTABLE_FIELDS, build_repair_report
from pipeline_runner import _prepare_incremental_master_retry
from prepare_master_retry import _effective_scope
from validate_composer_output import validate_composer_output


def _write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def main():
    shots = [
        {"shot_id": "S1", "subshot_id": "S1"},
        {"shot_id": "S2", "subshot_id": "S2"},
        {"shot_id": "S3", "subshot_id": "S3"},
    ]
    report = build_repair_report([
        "S1: qa_metadata缺少performance_contract",
        "S2: full_prompt必须明确使用项目画幅16:9",
    ], shots)
    assert report["partial_reuse_safe"] is True
    assert report["failed_subshot_ids"] == ["S1", "S2"]
    by_shot = {item["shot_id"]: item for item in report["repair_targets"]}
    assert by_shot["S1"]["repair_scope"] == "field"
    assert "qa_metadata.performance_contract" in by_shot["S1"]["fields"]
    assert by_shot["S2"]["fields"] == ["full_prompt"]

    pair = build_repair_report([
        "S1→S2: 下一片段start_lock必须等于上一片段end_lock"
    ], shots)
    assert pair["repair_scope"] == "pair"
    assert pair["failed_subshot_ids"] == ["S1", "S2"]
    assert all(item["dependent_shot_ids"] == ["S1", "S2"] for item in pair["repair_targets"])
    assert all(item["fields"] == [ALL_MUTABLE_FIELDS] for item in pair["repair_targets"])

    global_report = build_repair_report([
        "batch顶层只能包含shots，或contract_version与shots"
    ], shots)
    assert global_report["repair_scope"] == "scene"
    assert global_report["partial_reuse_safe"] is False
    assert global_report["failed_subshot_ids"] == ["S1", "S2", "S3"]
    assert all(item["fields"] == [ALL_MUTABLE_FIELDS] for item in global_report["repair_targets"])

    assert _effective_scope("field", 0) == "field"
    assert _effective_scope("field", 1) == "field"
    assert _effective_scope("field", 2) == "shot"
    assert _effective_scope("pair", 3) == "pair"

    with tempfile.TemporaryDirectory() as run_dir:
        batch_path = os.path.join(run_dir, ".cache", "composer", "batch.json")
        scaffold_path = os.path.join(run_dir, ".cache", "dispatch", "scaffold.json")
        packet_path = os.path.join(run_dir, ".cache", "dispatch", "master_production_packet.json")
        minimal = {
            "shot_id": "S1",
            "subshot_id": "S1",
            "duration": 4,
            "full_prompt": "",
            "negative_prompt": "",
            "qa_metadata": {},
            "generation_control": {},
        }
        _write(batch_path, {"shots": [minimal]})
        _write(scaffold_path, {
            "locked_fields": [],
            "shots": [
                {"shot_id": "S1", "subshot_id": "S1"},
                {"shot_id": "S2", "subshot_id": "S2"},
            ],
        })
        _write(packet_path, {
            "phase": "master_production",
            "_batch_output_path": batch_path,
            "composer_scaffold_path": scaffold_path,
        })
        full_report_path = os.path.join(run_dir, "full.json")
        with redirect_stdout(io.StringIO()):
            full_result = validate_composer_output(batch_path, run_dir, full_report_path)
        assert full_result == 1
        full_report = json.load(open(full_report_path, encoding="utf-8"))
        assert any("BATCH_COVERAGE" in issue for issue in full_report["issues"]), full_report
        assert full_report["partial_reuse_safe"] is False
        assert full_report["failed_subshot_ids"] == ["S1", "S2"]

        incremental_report_path = os.path.join(run_dir, "incremental.json")
        with redirect_stdout(io.StringIO()):
            incremental_result = validate_composer_output(
                batch_path,
                run_dir,
                incremental_report_path,
                allow_incomplete=True,
                selected_shot_ids=["S1"],
            )
        assert incremental_result == 1
        incremental_report = json.load(open(incremental_report_path, encoding="utf-8"))
        assert not any("BATCH_COVERAGE" in issue for issue in incremental_report["issues"])
        assert incremental_report["failed_subshot_ids"] == ["S1"]

    with tempfile.TemporaryDirectory() as run_dir:
        plan_path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")
        _write(plan_path, {
            "shots": [
                {"shot_id": "S1", "scene": "场景A", "subshots": [{"subshot_id": "S1-01", "duration": 4}]},
                {"shot_id": "S2", "scene": "场景A", "subshots": [{"subshot_id": "S2-01", "duration": 4}]},
            ]
        })
        _write(os.path.join(run_dir, "project_config.json"), {
            "canvas": "16:9",
            "visual_style": "动态漫",
            "generation_control": {"audio_enabled": True},
        })
        _write(os.path.join(run_dir, ".cache", "analysis", "scene_locks.json"), {
            "scenes": [{"scene": "场景A", "space_id": "SPACE-1", "creative": "模型场景资产"}],
        })
        report_path = os.path.join(run_dir, ".cache", "provenance", "partial.validation.json")
        _write(report_path, {
            "failed_subshot_ids": ["S1"],
            "repair_scope": "field",
            "repair_targets": [{
                "shot_id": "S1",
                "fields": ["full_prompt"],
                "repair_scope": "field",
                "dependent_shot_ids": ["S1"],
                "reasons": ["S1: full_prompt缺少落幅"],
            }],
        })
        original = os.path.join(run_dir, ".cache", "composer", "partial.json")
        _write(original, {"shots": []})
        _write(original + ".provenance.json", {
            "phase": "master_production",
            "recorded_at": 1,
            "validation_mode": "partial",
            "validated_subshot_ids": ["S2"],
            "failed_subshot_ids": ["S1"],
            "validation_report_path": report_path,
        })
        retry = _prepare_incremental_master_retry(run_dir, [original])
        assert retry["target_shot_ids"] == ["S1"]
        assert retry["repair_scope"] == "field"
        packet = json.load(open(retry["packets"][0], encoding="utf-8"))
        context = json.load(open(packet["retry_context_path"], encoding="utf-8"))
        assert context["fields_by_main_shot"] == {
            "S1": ["full_prompt"]
        }
        assert context["repair_scope_by_main_shot"] == {"S1": "field"}

    print("[INCREMENTAL MASTER VALIDATION] PASS")


if __name__ == "__main__":
    main()
