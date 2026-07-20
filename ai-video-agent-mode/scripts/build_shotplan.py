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
    _normalize_scene_names(plan)
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
            ss.setdefault("duration_sec", ss.get("duration", 0))
            ss.setdefault("characters", [])
            ss.setdefault("dialogue_refs", [])
            ss.setdefault("base_action", "")
        shot["total_duration"] = round(sum(float(ss.get("duration", 0) or 0) for ss in subshots), 2)
    plan["total_shots"] = len(plan.get("shots", []))


def _normalize_scene_names(plan):
    scene_names = {}
    for shot in plan.get("shots", []):
        raw = shot.get("scene", "").strip()
        if not raw:
            continue
        cleaned = raw.rstrip("0123456789 ").rstrip("-").strip()
        scene_names[raw] = cleaned
    for shot in plan.get("shots", []):
        raw = shot.get("scene", "").strip()
        if raw in scene_names:
            shot["scene"] = scene_names[raw]


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





def split_dialogue(text, max_chars_per_segment=60):
    """Split dialogue text at sentence boundaries, merging consecutive punctuation.
    Consecutive "！！" / "？？" / "？！" / "……" are treated as ONE boundary.
    Returns list of (text_segment, estimated_seconds) tuples.
    """
    import re as _re_sd
    collapsed = _re_sd.sub(r"([！？…])\1+", r"\1", text)
    segments = _re_sd.split(r"(?<=[。！？…])", collapsed)
    segments = [s.strip() for s in segments if s.strip()]
    result = []
    buf = ""
    for seg in segments:
        if len(buf + seg) <= max_chars_per_segment:
            buf += seg
        else:
            if buf:
                result.append(buf)
            buf = seg
    if buf:
        result.append(buf)
    output = []
    for s in result:
        chars = len(s)
        sentences = sum(1 for c in s if c in "。！？…")
        seconds = max(round(chars / 4.5 + sentences * 0.5, 1), 0.5)
        output.append((s, seconds))
    return output

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: build_shotplan.py <run_dir> [draft_shot_plan.json]")
        sys.exit(1)
    run_dir = sys.argv[1]
    normalize(run_dir, sys.argv[2] if len(sys.argv) > 2 else None)
    # Phase 1.5: Inject spatial coordinates (铁律 #44)
    try:
        from spatial_registry import run as spatial_registry_run
        spatial_registry_run(run_dir)
    except ImportError:
        print("[build_shotplan] spatial_registry.py not found — skipping spatial injection.")
        print("[build_shotplan] Run spatial_registry.py manually after Phase 1.")
    except Exception as e:
        print(f"[build_shotplan] spatial_registry failed: {e} — continuing without spatial data.")
