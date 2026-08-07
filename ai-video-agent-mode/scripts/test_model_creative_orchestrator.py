#!/usr/bin/env python3
"""Regression tests for the model-owned Orchestrator handoff."""

import json
import os
import tempfile

from prepare_creative_blueprint import prepare
from preflight_check import _validate_dialogue_source_lock, _validate_source_snapshot, run as preflight_run
from build_shotplan import normalize
from pipeline_runner import _local_phase_valid, _sha256
from workflow_supervisor import execute_local_phase


def _write(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if isinstance(value, str):
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(value)
    else:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)


def run():
    with tempfile.TemporaryDirectory(prefix="creative-orchestrator-") as root:
        run_dir = os.path.join(root, "run")
        source_path = os.path.join(root, "source.txt")
        _write(source_path, "SCENE 1 夜 内\n角色A：你终于来了。\n△角色B停在门边。\n")
        _write(os.path.join(run_dir, "project_config.json"), {
            "project_name": "测试",
            "canvas": "16:9",
            "visual_style": "3D 精致国风次时代CG建模，UE5引擎渲染",
            "max_shot_duration": 15,
            "target_platform": "即梦",
            "generation_control": {"mode": "t2v", "audio_enabled": True},
        })

        request, request_path = prepare(run_dir, source_path)
        assert request["authority"] == "model"
        assert set(request["required_outputs"]) == {"shot_plan_draft", "scene_locks_draft"}
        assert os.path.isfile(request_path)
        snapshot = json.load(open(request["source_snapshot_path"], encoding="utf-8"))
        assert snapshot["source_sha256"] == request["source_sha256"]
        assert snapshot["lines"][1]["text"] == "角色A：你终于来了。"
        source_ledger = json.load(open(request["source_ledger_path"], encoding="utf-8"))
        source_records = source_ledger["units"]
        assert [item["source_id"] for item in source_records] == [
            "SRC000001", "SRC000002", "SRC000003",
        ]
        issues = []
        _validate_source_snapshot(run_dir, source_records, issues)
        _validate_dialogue_source_lock({
            "D1": {"text": "你终于来了。", "source_ids": ["SRC000002"]},
        }, {item["source_id"]: item for item in source_records}, issues)
        assert not issues
        _validate_dialogue_source_lock({
            "D2": {"text": "你终于回来了。", "source_ids": ["SRC000002"]},
        }, {item["source_id"]: item for item in source_records}, issues)
        assert any(item["check"] == "DIALOGUE_SOURCE_TEXT" for item in issues)

        detail = execute_local_phase(run_dir, "orchestrator", source_path)
        assert detail["action"] == "creative_authoring_required"
        assert not os.path.exists(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"))
        assert not os.path.exists(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.draft.json"))
        assert not os.path.exists(os.path.join(run_dir, ".cache", "orchestrator", "scene_locks.draft.json"))
        assert os.path.exists(os.path.join(run_dir, ".cache", "orchestrator", "source_ledger.json"))

    with tempfile.TemporaryDirectory(prefix="creative-source-reuse-") as root:
        run_dir = os.path.join(root, "run")
        source_path = os.path.join(root, "source.txt")
        _write(source_path, "场景一\n甲：同一句源文。\n乙转身。\n")
        _write(os.path.join(run_dir, "project_config.json"), {
            "project_name": "复用测试", "canvas": "16:9", "visual_style": "模型自定",
            "max_shot_duration": 15, "target_platform": "即梦",
            "generation_control": {"mode": "t2v", "audio_enabled": True},
        })
        prepare(run_dir, source_path)
        _write(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.draft.json"), {
            "dialogue_map": {"D1": "同一句源文。"},
            "dialogue_events": {
                "D1": {
                    "ref": "D1", "kind": "台词", "speaker": "甲", "text": "同一句源文。",
                    "source_ids": ["SRC000002"],
                },
            },
            "source_exclusions": [],
            "shots": [
                {"shot_id": "S1", "scene": "场景一", "subshots": [{
                    "subshot_id": "S1-1", "duration": 5,
                    "source_ids": ["SRC000001", "SRC000002"], "dialogue_refs": ["D1"],
                }]},
                {"shot_id": "S2", "scene": "场景一", "subshots": [{
                    "subshot_id": "S2-1", "duration": 5,
                    "source_ids": ["SRC000002", "SRC000003"], "dialogue_refs": [],
                }]},
            ],
        })
        _write(os.path.join(run_dir, ".cache", "orchestrator", "scene_locks.draft.json"), {
            "scenes": [{
                "scene": "场景一", "space_id": "SPACE-1",
                "creative_scene_contract": {"model_freeform": "同一次导演理解生成的场景资产"},
            }],
        })
        normalize(run_dir)
        assert preflight_run(run_dir) == []
        detail = execute_local_phase(run_dir, "orchestrator", source_path)
        assert detail["creative_authority"] == "model"
        promoted = os.path.join(run_dir, ".cache", "analysis", "scene_locks.json")
        draft = os.path.join(run_dir, ".cache", "orchestrator", "scene_locks.draft.json")
        assert open(promoted, "rb").read() == open(draft, "rb").read()

    with tempfile.TemporaryDirectory(prefix="creative-receipt-") as root:
        orchestrator = os.path.join(root, ".cache", "orchestrator")
        preflight = os.path.join(root, ".cache", "preflight", "report.json")
        paths = {
            "draft_sha256": os.path.join(orchestrator, "shot_plan.draft.json"),
            "shot_plan_sha256": os.path.join(orchestrator, "shot_plan.json"),
            "scene_locks_draft_sha256": os.path.join(orchestrator, "scene_locks.draft.json"),
            "scene_locks_sha256": os.path.join(root, ".cache", "analysis", "scene_locks.json"),
            "source_ledger_sha256": os.path.join(orchestrator, "source_ledger.json"),
            "source_snapshot_sha256": os.path.join(orchestrator, "source_snapshot.json"),
            "preflight_report_sha256": preflight,
        }
        for path in paths.values():
            _write(path, {})
        receipt = {key: _sha256(path) for key, path in paths.items()}
        receipt["preflight_pass"] = True
        _write(os.path.join(orchestrator, "creative_validation_receipt.json"), receipt)
        assert _local_phase_valid(root, "orchestrator")
        _write(paths["draft_sha256"], {"model_revision": 2})
        assert not _local_phase_valid(root, "orchestrator")

    supervisor_source = open(
        os.path.join(os.path.dirname(__file__), "workflow_supervisor.py"), encoding="utf-8"
    ).read()
    assert "from generate_shotplan import" not in supervisor_source
    assert "build_scene_motion_plan" not in supervisor_source
    print("model creative orchestrator regression passed")


if __name__ == "__main__":
    run()
