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
    confirmed_max = cfg.get("max_shot_duration")
    if not isinstance(confirmed_max, (int, float)) or isinstance(confirmed_max, bool) or confirmed_max < 2.5:
        raise ValueError("project_config.max_shot_duration must be explicitly user-confirmed")
    plan["max_shot_duration"] = float(confirmed_max)
    plan.setdefault("dialogue_map", {})
    plan.setdefault("dialogue_events", {})
    plan.setdefault("shots", [])

    _normalize_ids_and_durations(plan)
    _validate_max_shot_duration(plan)
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
                if event.get("kind") not in ("台词", "OS", "OV"):
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





def split_dialogue(text, max_chars_per_segment=None, max_seconds=None, reserve_seconds=0.8):
    """Split dialogue only at semantic sentence boundaries.

    Mode C v4 prefers duration-based packing. ``max_chars_per_segment`` remains
    available for legacy callers, but the Orchestrator should pass the user's
    confirmed per-shot duration as ``max_seconds``. Text is never rewritten.
    """
    import re as _re_sd
    text = str(text or "")
    segments = [
        part.strip()
        for part in _re_sd.findall(r".+?(?:[。！？]+|…{2,}|—{2,})(?:[”’」』】）\)]*)|.+$", text, flags=_re_sd.S)
        if part.strip()
    ]
    result = []
    buf = ""
    for seg in segments:
        candidate = buf + seg
        within_chars = max_chars_per_segment is None or len(candidate) <= max_chars_per_segment
        within_seconds = max_seconds is None or _estimate_dialogue_seconds(candidate) + reserve_seconds <= max_seconds + 1e-6
        if within_chars and within_seconds:
            buf += seg
        else:
            if buf:
                result.append(buf)
            buf = seg
            if max_seconds is not None and _estimate_dialogue_seconds(buf) + reserve_seconds > max_seconds + 1e-6:
                raise ValueError(
                    "single dialogue sentence exceeds user-confirmed max_shot_duration and has no safe semantic split: %s"
                    % buf
                )
            if max_chars_per_segment is not None and len(buf) > max_chars_per_segment:
                # A single semantic sentence is intentionally preserved even
                # when it exceeds the legacy soft character target.
                pass
    if buf:
        result.append(buf)
    output = []
    for s in result:
        seconds = _estimate_dialogue_seconds(s)
        output.append((s, seconds))
    return output


def _estimate_dialogue_seconds(text):
    text = str(text or "")
    import re as _re_est
    spoken_chars = len(_re_est.sub(r"[\s，,、；;：:。！？!?…—‘’“”\"'「」『』（）()【】\[\]]", "", text))
    short_pauses = len(_re_est.findall(r"[，,、]", text))
    medium_pauses = len(_re_est.findall(r"[；;：:]", text))
    sentence_ends = len(_re_est.findall(r"[。！？!?]+", text))
    long_pauses = len(_re_est.findall(r"…{2,}|—{2,}", text))
    seconds = (
        spoken_chars / 4.5
        + short_pauses * 0.25
        + medium_pauses * 0.35
        + sentence_ends * 0.5
        + long_pauses * 0.6
    )
    return max(round(seconds, 1), 0.5)

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
