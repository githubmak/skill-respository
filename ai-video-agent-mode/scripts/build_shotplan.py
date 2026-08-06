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
from speech_events import SPEECH_KINDS

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
    confirmed_max = cfg.get("max_shot_duration")
    if not isinstance(confirmed_max, (int, float)) or isinstance(confirmed_max, bool) or confirmed_max < 2.5:
        raise ValueError("project_config.max_shot_duration must be explicitly user-confirmed")
    plan["max_shot_duration"] = float(confirmed_max)
    plan.setdefault("dialogue_map", {})
    plan.setdefault("dialogue_events", {})
    plan.setdefault("shots", [])

    _normalize_ids_and_durations(plan)
    _validate_max_shot_duration(plan)
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
        # Do not derive creative prose from another field. A missing core
        # action is a model-authored contract error and is left empty for the
        # validator to report.
        shot.setdefault("core_action", "")
        subshots = shot.setdefault("subshots", [])
        for sub_index, ss in enumerate(subshots, 1):
            ssid = ss.get("subshot_id") or "%s-%02d" % (shot_id, sub_index)
            if ssid in seen_subshots:
                raise ValueError("duplicate subshot_id: %s" % ssid)
            seen_subshots.add(ssid)
            ss["subshot_id"] = ssid
            ss.setdefault("shot_id", shot_id)
            if "duration_sec" in ss:
                raise ValueError("duration_sec is obsolete; use duration")
            ss.setdefault("duration", 0)
            ss.setdefault("characters", [])
            ss.setdefault("dialogue_refs", [])
            ss.setdefault("base_action", "")
        shot["total_duration"] = round(sum(float(ss.get("duration", 0) or 0) for ss in subshots), 2)
    plan["total_shots"] = len(plan.get("shots", []))


def _validate_max_shot_duration(plan):
    maximum = float(plan.get("max_shot_duration", 0) or 0)
    over = []
    for shot in plan.get("shots", []):
        total = float(shot.get("total_duration", 0) or 0)
        if total > maximum + 1e-6:
            over.append("%s=%gs" % (shot.get("shot_id", "?"), total))
    if over:
        raise ValueError(
            "main shot duration exceeds user-confirmed max_shot_duration=%gs: %s"
            % (maximum, ", ".join(over))
        )


def _validate_dialogue_refs(plan):
    dialogue_map = plan.get("dialogue_map", {}) or {}
    dialogue_events = plan.get("dialogue_events", {}) or {}
    missing = []
    malformed = []
    for shot in plan.get("shots", []):
        for ss in shot.get("subshots", []):
            for ref in ss.get("dialogue_refs", []) or []:
                if ref not in dialogue_map:
                    missing.append("%s:%s" % (ss.get("subshot_id", "?"), ref))
                    continue
                event = dialogue_events.get(ref)
                if not isinstance(event, dict):
                    malformed.append("%s:%s missing dialogue_events record" % (ss.get("subshot_id", "?"), ref))
                    continue
                if event.get("ref") != ref:
                    malformed.append("%s:%s ref mismatch" % (ss.get("subshot_id", "?"), ref))
                if event.get("kind") not in SPEECH_KINDS:
                    malformed.append("%s:%s invalid kind" % (ss.get("subshot_id", "?"), ref))
                if not str(event.get("speaker", "") or "").strip():
                    malformed.append("%s:%s missing speaker" % (ss.get("subshot_id", "?"), ref))
                text = str(event.get("text", "") or "")
                if not text:
                    malformed.append("%s:%s missing text" % (ss.get("subshot_id", "?"), ref))
                raw = str(dialogue_map.get(ref, "") or "")
                if text and raw != text and not raw.endswith("：" + text) and not raw.endswith(":" + text):
                    malformed.append("%s:%s text differs from dialogue_map" % (ss.get("subshot_id", "?"), ref))
    if missing:
        raise ValueError("dialogue_refs missing from dialogue_map: %s" % ", ".join(missing[:20]))
    if malformed:
        raise ValueError("dialogue_events invalid: %s" % ", ".join(malformed[:20]))

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: build_shotplan.py <run_dir> [draft_shot_plan.json]")
        sys.exit(1)
    run_dir = sys.argv[1]
    normalize(run_dir, sys.argv[2] if len(sys.argv) > 2 else None)
