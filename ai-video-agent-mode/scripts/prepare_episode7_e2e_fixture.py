#!/usr/bin/env python3
"""Prepare a small, source-derived run for real Agent dispatch verification.

This is a test harness, not a fixture containing project text.  It derives its
plan from the supplied source at run time, then retains eight deliberately
varied main shots.  The caller still has to run the normal Agent protocol.
"""

import argparse
import hashlib
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(__file__)
sys.path.insert(0, SCRIPT_DIR)

from build_shotplan import normalize
from configuration_wizard import answer, start
from detect_source_rules import detect_source_rules
from generate_shotplan import generate
from pipeline_state import init_state, load_state, save_state
from preflight_check import run as preflight_check


# Dialogue, prop state, multi-person blocking, handoff/contact and OS are all
# represented by these source-local IDs.  IDs are stable only for this source.
SELECTED_SHOT_IDS = ("S1-02", "S1-03", "S1-08", "S1-10", "S1-20", "S1-27", "S1-28", "S1-30")


def prepare(source_path, run_dir):
    source_path = os.path.abspath(source_path)
    run_dir = os.path.abspath(run_dir)
    if not os.path.isfile(source_path):
        raise ValueError("source file does not exist: %s" % source_path)
    if os.path.exists(run_dir) and os.listdir(run_dir):
        raise ValueError("run_dir must be new and empty: %s" % run_dir)

    export_base = os.path.dirname(run_dir)
    os.makedirs(export_base, exist_ok=True)
    start(run_dir, export_base)
    answer(run_dir, ["canvas", "visual_style"], ["\"9:16\"", "\"现代都市短剧，克制表演\""])
    answer(run_dir, ["max_shot_duration", "target_platform"], ["15", "\"即梦\""])
    answer(run_dir, ["generation_control.audio_enabled"], ["true"])
    answer(run_dir, ["delivery.markdown_path"], [json.dumps(os.path.join(run_dir, "episode7_8shot_jimeng.md"), ensure_ascii=False)])

    config_path = os.path.join(run_dir, "project_config.json")
    with open(config_path, encoding="utf-8-sig") as handle:
        config = json.load(handle)
    rules = detect_source_rules(source_path)
    config["source_rules"] = {
        "characters": rules.get("characters", []),
        "action_keywords": rules.get("action_keywords", []),
        "scene_header_pattern": rules.get("scene_header_pattern", r"^SCENE"),
        "dialogue_pattern": rules.get("dialogue_pattern_desc", ""),
    }
    config["character_list"] = list(rules.get("characters", []))
    _write(config_path, config)

    orchestrator_dir = os.path.join(run_dir, ".cache", "orchestrator")
    generate(source_path, orchestrator_dir, config_path)
    normalize(run_dir)
    issues = preflight_check(run_dir)
    if issues:
        raise ValueError("source preflight failed: %s" % "; ".join(str(issue) for issue in issues[:5]))

    plan_path = os.path.join(orchestrator_dir, "shot_plan.json")
    with open(plan_path, encoding="utf-8-sig") as handle:
        plan = json.load(handle)
    shots_by_id = {str(shot.get("shot_id", "")): shot for shot in plan.get("shots", [])}
    missing = [shot_id for shot_id in SELECTED_SHOT_IDS if shot_id not in shots_by_id]
    if missing:
        raise ValueError("source plan no longer contains fixture shots: %s" % ", ".join(missing))
    plan["shots"] = [shots_by_id[shot_id] for shot_id in SELECTED_SHOT_IDS]
    refs = {
        ref for shot in plan["shots"] for subshot in shot.get("subshots", [])
        for ref in subshot.get("dialogue_refs", [])
    }
    plan["dialogue_events"] = {
        ref: event for ref, event in plan.get("dialogue_events", {}).items() if ref in refs
    }
    _write(plan_path, plan)
    _filter_ledger(os.path.join(orchestrator_dir, "source_ledger.json"), refs, "ref")

    coverage = {
        "selected_shot_ids": list(SELECTED_SHOT_IDS),
        "main_shot_count": len(plan["shots"]),
        "dialogue_kinds": sorted({str(event.get("kind", "")) for event in plan["dialogue_events"].values()}),
        "contains_os": any(event.get("kind") == "OS" for event in plan["dialogue_events"].values()),
        "contains_ov": any(event.get("kind") == "OV" for event in plan["dialogue_events"].values()),
        "source_sha256": _sha256(source_path),
    }
    _write(os.path.join(run_dir, ".cache", "e2e_fixture_manifest.json"), coverage)

    # Deterministic planning was already complete above. Resume the normal
    # state machine at Scene Lock so every subsequent stage is real dispatch.
    init_state(run_dir)
    state = load_state(run_dir)
    state["current_phase"] = "scene_lock"
    state["phases"]["user_confirm"]["status"] = "done"
    state["phases"]["orchestrator"]["status"] = "done"
    save_state(run_dir, state)
    return coverage


def _filter_ledger(path, refs, key):
    try:
        with open(path, encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return
    if isinstance(data, list):
        data = [entry for entry in data if isinstance(entry, dict) and entry.get(key) in refs]
    elif isinstance(data, dict):
        data = {name: value for name, value in data.items() if name in refs}
    _write(path, data)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.run_dir), ensure_ascii=False, indent=2))
