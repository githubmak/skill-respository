#!/usr/bin/env python3
"""Prepare immutable source evidence for model-authored shot planning.

This module intentionally performs no story parsing or shot design. It records
the exact source bytes as a line-addressable snapshot and writes the contract
paths the current model must author before deterministic validation can resume.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time


REQUEST_VERSION = "model-creative-blueprint-v4"


def prepare(run_dir, source_path):
    run_dir = os.path.abspath(run_dir)
    source_path = os.path.abspath(source_path)
    config_path = os.path.join(run_dir, "project_config.json")
    if not os.path.isfile(source_path):
        raise ValueError("source file does not exist: " + source_path)
    if not os.path.isfile(config_path):
        raise ValueError("project_config.json is missing")

    raw = _read_utf8(source_path)
    config = _load_json(config_path)
    output_dir = os.path.join(run_dir, ".cache", "orchestrator")
    os.makedirs(output_dir, exist_ok=True)

    snapshot_path = os.path.join(output_dir, "source_snapshot.json")
    snapshot = {
        "snapshot_version": REQUEST_VERSION,
        "source_path": source_path,
        "source_sha256": _sha256(source_path),
        "encoding": _source_encoding(source_path),
        "line_count": len(raw.splitlines()),
        "lines": [
            {"line": index, "text": value}
            for index, value in enumerate(raw.splitlines(), 1)
        ],
    }
    _atomic_json(snapshot_path, snapshot)

    source_ledger_path = os.path.join(output_dir, "source_ledger.json")
    source_ledger = {
        "ledger_version": REQUEST_VERSION,
        "source_sha256": snapshot["source_sha256"],
        "units": [
            {
                "source_id": "SRC%06d" % index,
                "line": line["line"],
                "text": line["text"],
            }
            for index, line in enumerate(snapshot["lines"], 1)
        ],
    }
    _atomic_json(source_ledger_path, source_ledger)

    request_path = os.path.join(output_dir, "creative_blueprint_request.json")
    required_outputs = {
        "shot_plan_draft": os.path.join(output_dir, "shot_plan.draft.json"),
        "scene_locks_draft": os.path.join(output_dir, "scene_locks.draft.json"),
    }
    previous_request = _load_optional_json(request_path)
    request = {
        "request_version": REQUEST_VERSION,
        "action": "MODEL_CREATIVE_AUTHORING_REQUIRED",
        "authority": "model",
        "source_path": source_path,
        "source_snapshot_path": snapshot_path,
        "source_ledger_path": source_ledger_path,
        "source_sha256": snapshot["source_sha256"],
        "project_config_path": config_path,
        "creative_contract_path": os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "references", "contracts", "model_creative_blueprint_contract.md",
        ),
        "required_outputs": required_outputs,
        "authoring_started_at": previous_request.get("authoring_started_at", time.time()),
        "checkpoint_policy": {
            "atomic_replace": True,
            "progress_after_each_completed_scene_group": True,
            "semantic_transform": False,
            "progress_path": os.path.join(run_dir, ".cache", "control", "orchestrator_progress.json"),
            "progress_command": [
                sys.executable,
                os.path.join(os.path.dirname(__file__), "record_creative_progress.py"),
                request_path,
            ],
        },
        "hard_constraints": {
            "canvas": config.get("canvas", ""),
            "visual_style": config.get("visual_style", ""),
            "max_shot_duration": config.get("max_shot_duration"),
            "target_platform": config.get("target_platform", ""),
            "generation_mode": (config.get("generation_control") or {}).get("mode", ""),
            "dialogue_text_must_remain_exact": True,
        },
        "model_owned_decisions": [
            "story_and_subtext", "character_goal_and_relationship", "emotion_and_performance",
            "dramatic_beats", "shot_splitting", "reaction_ownership", "narrative_weight",
            "shot_function", "coverage_and_duration_strategy", "blocking", "camera", "focus",
            "lighting_and_palette", "action_design", "seedance_semantic_compilation",
            "scene_lock_design", "visual_punctuation", "final_aesthetic_judgment",
        ],
        "engine_forbidden_decisions": [
            "infer_emotion", "pack_narrative_beats", "select_reaction_owner",
            "choose_narrative_weight", "choose_camera", "semantic_compress",
        ],
        "resume_command": [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "workflow_supervisor.py"),
            "--run-dir", run_dir,
            "--source", source_path,
        ],
    }
    _atomic_json(request_path, request)
    return request, request_path


def missing_model_outputs(request):
    outputs = request.get("required_outputs", {}) if isinstance(request, dict) else {}
    return [path for path in outputs.values() if not os.path.isfile(str(path))]


def _read_utf8(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return handle.read()


def _source_encoding(path):
    with open(path, "rb") as handle:
        return "utf-8-sig" if handle.read(3) == b"\xef\xbb\xbf" else "utf-8"


def _load_json(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("project_config.json must contain an object")
    return value


def _load_optional_json(path):
    try:
        return _load_json(path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {}


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path, value):
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temporary, path)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: prepare_creative_blueprint.py <run_dir> <source_path>")
    prepared, path = prepare(sys.argv[1], sys.argv[2])
    print(json.dumps({
        "action": prepared["action"],
        "request_path": path,
        "missing_outputs": missing_model_outputs(prepared),
    }, ensure_ascii=False, indent=2))
