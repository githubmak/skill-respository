#!/usr/bin/env python3
"""Regression for first-pass quality ownership and Editor return routing."""

import json
import os
import tempfile

from pipeline_runner import _request_orchestrator_revision
from pipeline_state import init_state, load_state
from prepare_creative_blueprint import prepare as prepare_creative_blueprint
from prepare_master_retry import prepare
from record_creative_progress import record as record_creative_progress
from record_batch_provenance import _valid_editor_routing
from workflow_supervisor import _creative_progress_status


def _write(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def main():
    assert _valid_editor_routing({
        "pass": True, "blocking": [], "return_to_phase": None,
        "affected_shot_ids": [], "creative_cause": "",
    })
    assert _valid_editor_routing({
        "pass": False, "blocking": ["人物关系误读"],
        "return_to_phase": "orchestrator", "affected_shot_ids": ["S1"],
        "creative_cause": "整集人物目标理解错误",
    })
    assert not _valid_editor_routing({
        "pass": False, "blocking": ["镜头情绪没有成立"],
        "return_to_phase": "master_production", "affected_shot_ids": ["S1"],
        "creative_cause": "单镜表演与机位因果脱节",
        "repair_targets": [{"shot_id": "S1", "field_path": "seedance_prompt"}],
    })

    with tempfile.TemporaryDirectory(prefix="quality-frontload-") as run_dir:
        _write(os.path.join(run_dir, "project_config.json"), {
            "seedance_target": "auto", "generation_control": {"audio_enabled": True},
        })
        _write(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"), {
            "shots": [{
                "shot_id": "S1", "scene": "场景A",
                "subshots": [{"subshot_id": "S1-1", "duration": 5, "source_ids": ["SRC000001"]}],
            }],
        })
        _write(os.path.join(run_dir, ".cache", "orchestrator", "source_ledger.json"), {
            "units": [{"source_id": "SRC000001", "line": 1, "text": "原文"}],
        })
        _write(os.path.join(run_dir, ".cache", "analysis", "scene_locks.json"), {
            "scenes": [{"scene": "场景A", "space_id": "SPACE-1", "creative": "模型场景设计"}],
        })
        review_path = os.path.join(run_dir, ".cache", "review", "llm_gate_result.json")
        _write(review_path, {"windows": [{
            "window_id": "W1", "pass": False,
            "blocking": ["表演与镜头没有共同完成情绪转折"],
            "return_to_phase": "master_production",
            "affected_shot_ids": ["S1"],
            "creative_cause": "单镜导演执行没有实现已建立的全局意图",
        }]})
        packets = prepare(run_dir, review_path)
        packet = json.load(open(packets[0], encoding="utf-8"))
        context = json.load(open(packet["retry_context_path"], encoding="utf-8"))
        assert packet["creative_regeneration"] is True
        assert context["mode"] == "creative_regeneration"
        assert context["fields_by_main_shot"]["S1"] == ["__all_mutable__"]
        assert "phrase-level patch" in packet["instruction"]

        init_state(run_dir)
        draft_dir = os.path.join(run_dir, ".cache", "orchestrator")
        _write(os.path.join(draft_dir, "shot_plan.draft.json"), {"shots": [{"shot_id": "S1"}]})
        _write(os.path.join(draft_dir, "scene_locks.draft.json"), {"scenes": [{"scene": "场景A"}]})
        revision_path = _request_orchestrator_revision(run_dir, {
            "blocking": ["全局人物关系误读"],
            "windows": [{
                "pass": False, "return_to_phase": "orchestrator",
                "creative_cause": "人物目标理解错误",
            }],
        }, ["S1"])
        state = load_state(run_dir)
        assert state["current_phase"] == "orchestrator"
        assert state["phases"]["orchestrator"]["revision_request_path"] == revision_path
        assert state["phases"]["master_production"]["status"] == "pending"

        source_path = os.path.join(run_dir, "source.txt")
        with open(source_path, "w", encoding="utf-8") as handle:
            handle.write("第一行原文\n第二行原文\n")
        request, _request_path = prepare_creative_blueprint(run_dir, source_path)
        progress = record_creative_progress(_request_path)
        assert progress["total_items"] == 2
        assert progress["progress_count"] == 1
        assert _creative_progress_status(request)["stalled"] is False

    print("[QUALITY FRONTLOAD] PASS")


if __name__ == "__main__":
    main()
