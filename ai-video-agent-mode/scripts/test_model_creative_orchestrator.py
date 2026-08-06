#!/usr/bin/env python3
"""Regression tests for the model-owned Orchestrator handoff."""

import json
import os
import tempfile

from prepare_creative_blueprint import prepare
from preflight_check import _validate_dialogue_source_lock, _validate_source_snapshot
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
        assert len(request["required_outputs"]) == 3
        assert os.path.isfile(request_path)
        snapshot = json.load(open(request["source_snapshot_path"], encoding="utf-8"))
        assert snapshot["source_sha256"] == request["source_sha256"]
        assert snapshot["lines"][1]["text"] == "角色A：你终于来了。"
        source_records = [{
            "source_id": "SRC0001", "line": 2,
            "type": "dialogue", "text": "角色A：你终于来了。",
        }]
        issues = []
        _validate_source_snapshot(run_dir, source_records, issues)
        _validate_dialogue_source_lock({
            "D1": {"text": "你终于来了。", "source_ids": ["SRC0001"]},
        }, {"SRC0001": source_records[0]}, issues)
        assert not issues
        _validate_dialogue_source_lock({
            "D2": {"text": "你终于回来了。", "source_ids": ["SRC0001"]},
        }, {"SRC0001": source_records[0]}, issues)
        assert any(item["check"] == "DIALOGUE_SOURCE_TEXT" for item in issues)

        detail = execute_local_phase(run_dir, "orchestrator", source_path)
        assert detail["action"] == "creative_authoring_required"
        assert not os.path.exists(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"))
        assert not os.path.exists(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.draft.json"))

    supervisor_source = open(
        os.path.join(os.path.dirname(__file__), "workflow_supervisor.py"), encoding="utf-8"
    ).read()
    assert "from generate_shotplan import" not in supervisor_source
    assert "build_scene_motion_plan" not in supervisor_source
    print("model creative orchestrator regression passed")


if __name__ == "__main__":
    run()
