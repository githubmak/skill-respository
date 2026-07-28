#!/usr/bin/env python3
"""Run deterministic Phase 0/1 checks for an external production script.

This test deliberately stops before Agent work. It proves that a real source
can be configured, parsed, ledgered, duration-validated, and packetized
without storing project names or source content in the skill directory.
"""

import argparse
import json
import os
import shutil
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(__file__)
sys.path.insert(0, SCRIPT_DIR)

from build_shotplan import normalize
from configuration_wizard import answer, start
from detect_source_rules import detect_source_rules
from dispatch_cache import prepare_dispatch_packets
from generate_shotplan import generate
from preflight_check import run as preflight_check


def run(source_path, min_shots=1):
    source_path = os.path.abspath(source_path)
    if not os.path.isfile(source_path):
        raise ValueError("source file does not exist: %s" % source_path)

    root = tempfile.mkdtemp(prefix="ai-video-source-smoke-")
    run_dir = os.path.join(root, "run")
    try:
        start(run_dir, root)
        answer(run_dir, ["canvas", "visual_style"], ["\"9:16\"", "\"smoke-test\""])
        answer(run_dir, ["max_shot_duration", "target_platform"], ["15", "\"即梦\""])
        answer(run_dir, ["generation_control.audio_enabled"], ["true"])
        answer(run_dir, ["delivery.markdown_path"], [json.dumps(os.path.join(root, "delivery.md"), ensure_ascii=False)])

        config_path = os.path.join(run_dir, "project_config.json")
        with open(config_path, "r", encoding="utf-8-sig") as handle:
            config = json.load(handle)
        rules = detect_source_rules(source_path)
        config["source_rules"] = {
            "characters": rules.get("characters", []),
            "action_keywords": rules.get("action_keywords", []),
            "scene_header_pattern": rules.get("scene_header_pattern", r"^SCENE"),
            "dialogue_pattern": rules.get("dialogue_pattern_desc", ""),
        }
        config["character_list"] = list(rules.get("characters", []))
        with open(config_path, "w", encoding="utf-8") as handle:
            json.dump(config, handle, ensure_ascii=False, indent=2)

        generate(source_path, os.path.join(run_dir, ".cache", "orchestrator"), config_path)
        normalize(run_dir)
        issues = preflight_check(run_dir)
        if issues:
            raise ValueError("preflight failed: %s" % "; ".join(item["msg"] for item in issues[:5]))
        with open(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"), encoding="utf-8-sig") as handle:
            plan = json.load(handle)
        shot_count = len(plan.get("shots", []))
        if shot_count < min_shots:
            raise ValueError("expected at least %s shots, got %s" % (min_shots, shot_count))
        packets = prepare_dispatch_packets(run_dir, "scene_lock")
        if not packets:
            raise ValueError("scene-lock packet generation returned no packets")
        return {"pass": True, "shot_count": shot_count, "scene_lock_packets": len(packets)}
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
