"""Preflight checks before spawning analysis agents."""
import json
import os
import sys

if not os.environ.get("PYTHONPYCACHEPREFIX") and not getattr(sys, "pycache_prefix", None):
    sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))
from pycache_policy import block_source_pycache_until_run_dir, ensure_pycache_prefix

block_source_pycache_until_run_dir()
from validate_durations import validate as validate_durations
from shot_semantics import is_declared_non_action, is_implicit_character_action, render_anchor, requires_base_action, requires_characters


ALLOWED_VISUAL_PUNCTUATION = {
    "occlusion_reveal", "low_angle_scale", "foreground_reaction",
    "camera_follow", "light_reveal", "stop_mark", "rack_focus",
}


def run(run_dir):
    """Validate shot_plan before expensive sub-agent dispatch."""
    ensure_pycache_prefix(run_dir)
    shot_plan_path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")
    project_config_path = os.path.join(run_dir, "project_config.json")
    issues = []

    if not os.path.exists(shot_plan_path):
        return [_issue("GLOBAL", "SHOT_PLAN_MISSING", "missing .cache/orchestrator/shot_plan.json")]

    try:
        with open(shot_plan_path, "r", encoding="utf-8-sig") as f:
            shot_plan = json.load(f)
    except Exception as exc:
        return [_issue("GLOBAL", "SHOT_PLAN_PARSE", str(exc))]

    seen = set()
    dialogue_map = shot_plan.get("dialogue_map", {}) or {}
    dialogue_events = shot_plan.get("dialogue_events", {}) or {}
    declared_beats = {}

    for shot in shot_plan.get("shots", []):
        shot_id = shot.get("shot_id", "")
        if not shot_id:
            issues.append(_issue("GLOBAL", "SHOT_ID_MISSING", "shot missing shot_id"))
        subshots = shot.get("subshots", [])
        if not subshots:
            issues.append(_issue(shot_id or "GLOBAL", "SUBSHOTS_EMPTY", "shot has no subshots"))
        for ss in subshots:
            ssid = ss.get("subshot_id", "")
            if not ssid:
                issues.append(_issue(shot_id or "GLOBAL", "SUBSHOT_ID_MISSING", "subshot missing subshot_id"))
                continue
            if ssid in seen:
                issues.append(_issue(ssid, "SUBSHOT_ID_DUPLICATE", "duplicate subshot_id"))
            seen.add(ssid)
            dramatic_design = ss.get("dramatic_design")
            if not isinstance(dramatic_design, dict):
                issues.append(_issue(ssid, "DRAMATIC_DESIGN_MISSING", "dramatic_design is required"))
            else:
                punctuation = dramatic_design.get("visual_punctuation")
                if not isinstance(punctuation, list):
                    issues.append(_issue(ssid, "VISUAL_PUNCTUATION_TYPE", "dramatic_design.visual_punctuation must be an array"))
                else:
                    if len(punctuation) > 2:
                        issues.append(_issue(ssid, "VISUAL_PUNCTUATION_COUNT", "visual punctuation allows at most 2 devices"))
                    if len(set(punctuation)) != len(punctuation) or any(item not in ALLOWED_VISUAL_PUNCTUATION for item in punctuation):
                        issues.append(_issue(ssid, "VISUAL_PUNCTUATION_VALUE", "visual punctuation contains duplicate or unsupported device"))
                    if (
                        dramatic_design.get("shot_function") == "entrance"
                        and dramatic_design.get("narrative_weight") in ("high", "critical")
                        and not 1 <= len(punctuation) <= 2
                    ):
                        issues.append(_issue(ssid, "VISUAL_PUNCTUATION_COUNT", "important entrance needs 1-2 visual punctuation devices"))
                for beat_id in dramatic_design.get("dramatic_beat_ids", []) or []:
                    if beat_id in declared_beats:
                        issues.append(_issue(ssid, "DRAMATIC_BEAT_DUPLICATE_OWNER", "%s also owned by %s" % (beat_id, declared_beats[beat_id])))
                    declared_beats[beat_id] = ssid
            base_action = ss.get("base_action", "")
            characters = ss.get("characters", []) or []
            dialogue_refs = ss.get("dialogue_refs", []) or []
            shot_size = ss.get("shot_size", "")
            shot_type = ss.get("shot_type", "") or ss.get("visual_type", "") or ss.get("purpose", "")
            if is_declared_non_action(ss):
                if ss.get("non_character_confirmed") is not True:
                    issues.append(_issue(ssid, "NON_CHARACTER_CONFIRMATION_MISSING", "non-character insert must set non_character_confirmed=true"))
                if not render_anchor(ss):
                    issues.append(_issue(ssid, "NON_CHARACTER_RENDER_ANCHOR_MISSING", "non-character insert must provide visual_intent/image_subject/atmosphere"))
                if dialogue_refs or characters or is_implicit_character_action(base_action):
                    issues.append(_issue(ssid, "NON_CHARACTER_CONFIRMATION_CONTRADICTION", "non_character_confirmed=true conflicts with dialogue, visible characters, or implicit human action"))
            if not base_action and requires_base_action(ss):
                issues.append(_issue(ssid, "BASE_ACTION_MISSING", "base_action required for character/action/dialogue shots; use visual_intent/shot_type for true non-action shots"))
            if not characters and requires_characters(base_action, dialogue_refs, shot_size, shot_type):
                issues.append(_issue(ssid, "CHARACTERS_MISSING", "characters required for dialogue/action/performance shots; use shot_type=empty/background/object/establishing for true non-character shots"))
            for ref in dialogue_refs:
                if ref not in dialogue_map:
                    issues.append(_issue(ssid, "DIALOGUE_REF_MISSING", "%s not found in dialogue_map" % ref))
                    continue
                event = dialogue_events.get(ref)
                if not isinstance(event, dict):
                    issues.append(_issue(ssid, "DIALOGUE_EVENT_MISSING", "%s not found in dialogue_events; regenerate Phase 1" % ref))
                    continue
                for field in ("ref", "kind", "speaker", "text"):
                    if not str(event.get(field, "") or "").strip():
                        issues.append(_issue(ssid, "DIALOGUE_EVENT_FIELD", "%s.%s is required" % (ref, field)))
                if event.get("ref") != ref:
                    issues.append(_issue(ssid, "DIALOGUE_EVENT_REF", "%s ref mismatch" % ref))
                if event.get("kind") not in ("台词", "OS", "OV"):
                    issues.append(_issue(ssid, "DIALOGUE_EVENT_KIND", "%s kind must be 台词/OS/OV" % ref))

    source_ledger_path = os.path.join(run_dir, ".cache", "orchestrator", "source_ledger.json")
    beat_ledger_path = os.path.join(run_dir, ".cache", "orchestrator", "dramatic_beat_ledger.json")
    source_ids = _ledger_ids(source_ledger_path, "units", "source_id", issues, "SOURCE_LEDGER")
    beat_records = _ledger_records(beat_ledger_path, "beats", issues, "DRAMATIC_BEAT_LEDGER")
    ledger_beat_ids = set()
    for record in beat_records:
        beat_id = str(record.get("beat_id", "") or "")
        owner = str(record.get("owner_subshot_id", "") or "")
        if not beat_id or beat_id in ledger_beat_ids:
            issues.append(_issue(owner or "GLOBAL", "DRAMATIC_BEAT_LEDGER_ID", "missing or duplicate beat_id: %s" % beat_id))
            continue
        ledger_beat_ids.add(beat_id)
        if owner not in seen:
            issues.append(_issue(owner or "GLOBAL", "DRAMATIC_BEAT_OWNER", "%s owner must exist in shot_plan" % beat_id))
        if declared_beats.get(beat_id) != owner:
            issues.append(_issue(owner or "GLOBAL", "DRAMATIC_BEAT_OWNER_MISMATCH", "%s ledger=%s shot_plan=%s" % (beat_id, owner, declared_beats.get(beat_id))))
        for source_id in record.get("source_ids", []) or []:
            if source_id not in source_ids:
                issues.append(_issue(owner or "GLOBAL", "DRAMATIC_BEAT_SOURCE", "%s references unknown %s" % (beat_id, source_id)))
    for beat_id in sorted(set(declared_beats) - ledger_beat_ids):
        issues.append(_issue(declared_beats[beat_id], "DRAMATIC_BEAT_LEDGER_MISSING", beat_id))

    for dur_issue in validate_durations(shot_plan_path, project_config_path=project_config_path if os.path.exists(project_config_path) else None):
        sid, field, value, expected = dur_issue
        issues.append(_issue(sid, "DURATION_%s" % field, "got %s expected %s" % (value, expected)))

    report_path = os.path.join(run_dir, ".cache", "preflight", "report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"pass": not issues, "issues": issues}, f, ensure_ascii=False, indent=2)
    return issues


def _issue(subshot_id, check, msg):
    return {"subshot_id": subshot_id, "check": check, "severity": "blocking", "msg": msg}


def _ledger_records(path, key, issues, check):
    if not os.path.exists(path):
        issues.append(_issue("GLOBAL", check + "_MISSING", path))
        return []
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except Exception as exc:
        issues.append(_issue("GLOBAL", check + "_PARSE", str(exc)))
        return []
    records = data.get(key)
    if not isinstance(records, list):
        issues.append(_issue("GLOBAL", check + "_STRUCTURE", "%s must be an array" % key))
        return []
    return [record for record in records if isinstance(record, dict)]


def _ledger_ids(path, key, id_field, issues, check):
    records = _ledger_records(path, key, issues, check)
    values = [str(record.get(id_field, "") or "") for record in records]
    if any(not value for value in values) or len(values) != len(set(values)):
        issues.append(_issue("GLOBAL", check + "_ID", "%s values must be non-empty and unique" % id_field))
    return set(values)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: preflight_check.py <run_dir>")
        sys.exit(1)
    issues = run(sys.argv[1])
    print(json.dumps(issues, ensure_ascii=False, indent=2))
    sys.exit(0 if not issues else 1)
