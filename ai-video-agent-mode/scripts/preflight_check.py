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
from shot_semantics import requires_base_action, requires_characters


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
            base_action = ss.get("base_action", "")
            characters = ss.get("characters", []) or []
            dialogue_refs = ss.get("dialogue_refs", []) or []
            shot_size = ss.get("shot_size", "")
            shot_type = ss.get("shot_type", "") or ss.get("visual_type", "") or ss.get("purpose", "")
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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: preflight_check.py <run_dir>")
        sys.exit(1)
    issues = run(sys.argv[1])
    print(json.dumps(issues, ensure_ascii=False, indent=2))
    sys.exit(0 if not issues else 1)
