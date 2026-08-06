#!/usr/bin/env python3
"""Run deterministic configuration and Orchestrator checks for an external production script.

This test deliberately stops before Agent work. It proves that a real source
can be configured, snapshotted, and handed to the model creative stage without
calling the retired local shot generator.
"""

import argparse
import json
import os
import shutil
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(__file__)
sys.path.insert(0, SCRIPT_DIR)

from configuration_wizard import answer, start
from prepare_creative_blueprint import missing_model_outputs, prepare
from source_gate import run as source_gate


def run(source_path, min_shots=1):
    source_path = os.path.abspath(source_path)
    if not os.path.isfile(source_path):
        raise ValueError("source file does not exist: %s" % source_path)

    root = tempfile.mkdtemp(prefix="ai-video-source-smoke-")
    run_dir = os.path.join(root, "run")
    try:
        start(run_dir, root)
        answer(run_dir, ["canvas", "visual_style"], ["\"16:9\"", "\"3D 精致国风次时代CG建模，UE5引擎渲染\""])
        answer(run_dir, ["max_shot_duration", "target_platform"], ["15", "\"即梦\""])
        answer(run_dir, ["seedance_target"], ["\"auto\""])
        answer(run_dir, ["generation_control.audio_enabled"], ["true"])
        answer(run_dir, ["delivery.markdown_path"], [json.dumps(os.path.join(root, "delivery.md"), ensure_ascii=False)])

        config_path = os.path.join(run_dir, "project_config.json")
        source_report = source_gate(run_dir, source_path, config_path=config_path)
        if not source_report.get("pass"):
            raise ValueError("source gate failed: %s" % source_report.get("blocking"))
        request, request_path = prepare(run_dir, source_path)
        missing = missing_model_outputs(request)
        if len(missing) != 1 or not missing[0].endswith("shot_plan.draft.json"):
            raise ValueError("creative authoring handoff must require only the model-authored shot plan")
        snapshot_path = request.get("source_snapshot_path", "")
        with open(snapshot_path, encoding="utf-8-sig") as handle:
            snapshot = json.load(handle)
        with open(request.get("source_ledger_path", ""), encoding="utf-8-sig") as handle:
            source_ledger = json.load(handle)
        if snapshot.get("line_count", 0) < min_shots:
            raise ValueError("source snapshot is unexpectedly empty")
        if len(source_ledger.get("units", [])) != snapshot.get("line_count", 0):
            raise ValueError("engineering source ledger does not cover every snapshot line")
        return {
            "pass": True,
            "action": request.get("action"),
            "creative_authoring_required": True,
            "request_path": request_path,
            "source_snapshot_path": snapshot_path,
            "source_ledger_path": request.get("source_ledger_path", ""),
            "source_line_count": snapshot.get("line_count", 0),
            "source_sha256": snapshot.get("source_sha256", ""),
        }
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--min-shots", type=int, default=1)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.source, args.min_shots), ensure_ascii=False, indent=2))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"pass": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
