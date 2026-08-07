#!/usr/bin/env python3
"""Regression coverage for high-quality fast configuration and auto-start."""

import json
import os
import tempfile

from configuration_wizard import answer, start
from resolve_run_mode import BASE_FIELDS, config_issues
from route_task import high_quality_fast_start


SOURCE = """SCENE 1 夜 内 客厅

林岚站在餐桌左侧，右手压着尚未拆封的文件袋。周启停在门边。

林岚：你今晚回来，不是为了看我。

周启：我只是想把事情说清楚。

林岚把文件袋推到桌面中央。周启伸出的手停在桌沿前。
"""


def _write(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        if isinstance(value, str):
            handle.write(value)
        else:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")


def _read(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _config(root):
    return {
        "export_base": root,
        "canvas": "9:16",
        "visual_style": "写实电影级动态漫短剧",
        "max_shot_duration": 15,
        "target_platform": "即梦",
        "seedance_target": "auto",
        "generation_control": {
            "mode": "t2v",
            "audio_enabled": True,
        },
        "delivery": {"markdown_path": os.path.join(root, "delivery.md")},
        "confirmation": {
            "config_version": 999,
            "confirmed_at": "fake",
            "confirmed_fields": list(BASE_FIELDS),
            "confirmed_values": {},
            "confirmed_values_sha256": "fake",
        },
    }


def run():
    with tempfile.TemporaryDirectory(prefix="ai-video-fast-start-") as root:
        source_path = os.path.join(root, "source.txt")
        config_path = os.path.join(root, "fast_config.json")
        run_dir = os.path.join(root, "run")
        _write(source_path, SOURCE)
        _write(config_path, _config(root))

        outcome = high_quality_fast_start(run_dir, config_path, source_path)
        assert outcome["pass"] is True
        assert outcome["setup_mode"] == "high_quality_fast"
        assert outcome["quality_pipeline_preserved"] is True
        assert outcome["skipped_phases"] == []
        assert outcome["context_plan"]["preload_full_contracts"] is False
        assert outcome["context_plan"]["read_first"] == [
            "references/creative_engineering_boundary.md", "references/stage_gates.md"
        ]
        assert outcome["supervisor"]["status"] == "creative_authoring_required"
        assert outcome["supervisor"]["phase"] == "orchestrator"
        assert outcome["supervisor"]["creative_request_path"].endswith("creative_blueprint_request.json")
        assert len(outcome["supervisor"]["missing_outputs"]) == 2

        saved = _read(os.path.join(run_dir, "project_config.json"))
        assert not config_issues(saved, run_dir=run_dir, require_confirmation=True)
        assert saved["confirmation"]["confirmed_at"] != "fake"
        assert saved["confirmation"]["config_version"] != 999
        assert saved["confirmation"]["confirmed_fields"] == list(BASE_FIELDS)
        assert "supports_negative_prompt" not in saved["generation_control"]
        assert "performance_direction" not in saved
        assert "quality_policy" not in saved
        assert "max_static_shot_duration" not in saved
        assert "source_rules" not in saved
        state = _read(os.path.join(run_dir, ".cache", "pipeline_state.json"))
        assert state["phases"]["user_confirm"]["status"] == "done"
        assert state["phases"]["orchestrator"]["status"] == "running"
        assert state["current_phase"] == "orchestrator"
        assert os.path.isfile(os.path.join(run_dir, ".cache", "orchestrator", "source_snapshot.json"))
        assert os.path.isfile(os.path.join(run_dir, ".cache", "orchestrator", "source_ledger.json"))
        assert os.path.isfile(os.path.join(run_dir, ".cache", "orchestrator", "creative_blueprint_request.json"))
        assert not os.path.exists(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"))
        source_gate_path = os.path.join(run_dir, ".cache", "preflight", "source_gate.json")
        assert os.path.isfile(source_gate_path)
        source_gate = _read(source_gate_path)
        assert source_gate["pass"] is True
        assert not source_gate["blocking"]

    with tempfile.TemporaryDirectory(prefix="ai-video-fast-invalid-") as root:
        source_path = os.path.join(root, "source.txt")
        _write(source_path, SOURCE)

        incomplete = _config(root)
        incomplete.pop("visual_style")
        incomplete_path = os.path.join(root, "incomplete.json")
        incomplete_run = os.path.join(root, "incomplete-run")
        _write(incomplete_path, incomplete)
        try:
            high_quality_fast_start(incomplete_run, incomplete_path, source_path)
            raise AssertionError("incomplete batch config was accepted")
        except ValueError as exc:
            assert "visual_style" in str(exc)
        assert not os.path.exists(incomplete_run)

        outside = _config(root)
        outside["delivery"]["markdown_path"] = os.path.join(os.path.dirname(root), "outside.md")
        outside_path = os.path.join(root, "outside.json")
        outside_run = os.path.join(root, "outside-run")
        _write(outside_path, outside)
        try:
            high_quality_fast_start(outside_run, outside_path, source_path)
            raise AssertionError("delivery outside export_base was accepted")
        except ValueError as exc:
            assert "delivery.markdown_path must be under export_base" in str(exc)
        assert not os.path.exists(outside_run)

        dirty = os.path.join(root, "dirty-run")
        sentinel = os.path.join(dirty, "keep.txt")
        _write(sentinel, "keep")
        valid_path = os.path.join(root, "valid.json")
        _write(valid_path, _config(root))
        try:
            high_quality_fast_start(dirty, valid_path, source_path)
            raise AssertionError("dirty run_dir was accepted")
        except ValueError as exc:
            assert "new and empty" in str(exc)
        assert open(sentinel, encoding="utf-8").read() == "keep"

    # The original ordered Wizard remains supported and now records the fixed
    # T2V mode in its complete confirmation snapshot.
    with tempfile.TemporaryDirectory(prefix="ai-video-wizard-compat-") as root:
        run_dir = os.path.join(root, "run")
        start(run_dir, root)
        answer(run_dir, ["canvas", "visual_style"], ["\"16:9\"", "\"动态漫\""])
        answer(run_dir, ["max_shot_duration", "target_platform"], ["15", "\"即梦\""])
        answer(run_dir, ["seedance_target"], ["\"auto\""])
        answer(run_dir, ["generation_control.audio_enabled"], ["true"])
        result = answer(run_dir, ["delivery.markdown_path"], [json.dumps(os.path.join(root, "delivery.md"), ensure_ascii=False)])
        assert result["pass"] is True
        saved = _read(os.path.join(run_dir, "project_config.json"))
        assert saved["confirmation"]["confirmed_fields"] == list(BASE_FIELDS)
        assert not config_issues(saved, run_dir=run_dir, require_confirmation=True)

    print("high-quality fast start regression passed")


if __name__ == "__main__":
    run()
