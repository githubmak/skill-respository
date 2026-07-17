"""Normalize a main-agent generated shot_plan.json.

This helper deliberately does not create story content. The Orchestrator phase
is expected to read the user's source and write a draft shot plan. This script
then fills mechanical fields, validates identifiers, and saves the normalized
plan under <run_dir>/.cache/orchestrator/shot_plan.json.
"""
import json
import os
import sys

if not os.environ.get("PYTHONPYCACHEPREFIX") and not getattr(sys, "pycache_prefix", None):
    sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))
from pycache_policy import block_source_pycache_until_run_dir, ensure_pycache_prefix

block_source_pycache_until_run_dir()


def normalize(run_dir, draft_path=None):
    ensure_pycache_prefix(run_dir)
    cfg_path = os.path.join(run_dir, "project_config.json")
    if not os.path.exists(cfg_path):
        raise FileNotFoundError("missing project_config.json in run_dir")
    with open(cfg_path, "r", encoding="utf-8-sig") as f:
        cfg = json.load(f)

    draft_path = draft_path or os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.draft.json")
    if not os.path.exists(draft_path):
        raise FileNotFoundError(
            "missing draft shot plan: %s. The main Orchestrator must create it from the user's source." % draft_path
        )
    with open(draft_path, "r", encoding="utf-8-sig") as f:
        plan = json.load(f)

    plan.setdefault("project_name", cfg.get("project_name", ""))
    plan["canvas"] = cfg.get("canvas", plan.get("canvas", ""))
    plan["visual_style"] = cfg.get("visual_style", plan.get("visual_style", ""))
    plan["max_shot_duration"] = cfg.get("max_shot_duration", plan.get("max_shot_duration", 15))
    plan.setdefault("dialogue_map", {})
    plan.setdefault("shots", [])

    _normalize_ids_and_durations(plan)
    _validate_dialogue_refs(plan)

    out_path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print("[SHOTPLAN] normalized %d shots -> %s" % (len(plan.get("shots", [])), out_path))
    return plan


def _normalize_ids_and_durations(plan):
    seen_subshots = set()
    for shot_index, shot in enumerate(plan.get("shots", []), 1):
        shot_id = shot.get("shot_id") or "S1-%02d" % shot_index
        shot["shot_id"] = shot_id
        shot.setdefault("scene", "")
        shot.setdefault("core_action", shot.get("description", ""))
        subshots = shot.setdefault("subshots", [])
        for sub_index, ss in enumerate(subshots, 1):
            ssid = ss.get("subshot_id") or "%s-%02d" % (shot_id, sub_index)
            if ssid in seen_subshots:
                raise ValueError("duplicate subshot_id: %s" % ssid)
            seen_subshots.add(ssid)
            ss["subshot_id"] = ssid
            ss.setdefault("shot_id", shot_id)
            ss.setdefault("duration", 0)
            ss.setdefault("characters", [])
            ss.setdefault("dialogue_refs", [])
            ss.setdefault("base_action", "")
        shot["total_duration"] = round(sum(float(ss.get("duration", 0) or 0) for ss in subshots), 2)
    plan["total_shots"] = len(plan.get("shots", []))


def _validate_dialogue_refs(plan):
    dialogue_map = plan.get("dialogue_map", {}) or {}
    missing = []
    for shot in plan.get("shots", []):
        for ss in shot.get("subshots", []):
            for ref in ss.get("dialogue_refs", []) or []:
                if ref not in dialogue_map:
                    missing.append("%s:%s" % (ss.get("subshot_id", "?"), ref))
    if missing:
        raise ValueError("dialogue_refs missing from dialogue_map: %s" % ", ".join(missing[:20]))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: build_shotplan.py <run_dir> [draft_shot_plan.json]")
        sys.exit(1)
    normalize(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
