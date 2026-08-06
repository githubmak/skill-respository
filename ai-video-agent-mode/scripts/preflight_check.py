"""Deterministic source, ledger, ID, dialogue, and duration preflight."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from validate_durations import validate as validate_durations


SPEECH_KINDS = {"台词", "OS", "OV", "系统音"}


def run(run_dir):
    plan_path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")
    config_path = os.path.join(run_dir, "project_config.json")
    issues = []
    plan = _load_required(plan_path, issues, "SHOT_PLAN")
    shots = plan.get("shots", []) if isinstance(plan, dict) else []
    if not isinstance(shots, list) or not shots:
        issues.append(_issue("GLOBAL", "SHOTS_EMPTY", "shots must be a non-empty array"))
        shots = []

    seen_shots, seen_subshots, referenced_dialogue, referenced_sources = set(), set(), [], []
    dialogue_events = plan.get("dialogue_events", {}) if isinstance(plan.get("dialogue_events"), dict) else {}
    for shot in shots:
        if not isinstance(shot, dict):
            issues.append(_issue("GLOBAL", "SHOT_TYPE", "shot must be an object"))
            continue
        shot_id = str(shot.get("shot_id", ""))
        if not shot_id or shot_id in seen_shots:
            issues.append(_issue(shot_id or "GLOBAL", "SHOT_ID", "shot_id must be non-empty and unique"))
        seen_shots.add(shot_id)
        subshots = shot.get("subshots", [])
        if not isinstance(subshots, list) or not subshots:
            issues.append(_issue(shot_id or "GLOBAL", "SUBSHOTS_EMPTY", "subshots must be a non-empty array"))
            continue
        for subshot in subshots:
            if not isinstance(subshot, dict):
                issues.append(_issue(shot_id, "SUBSHOT_TYPE", "subshot must be an object"))
                continue
            sid = str(subshot.get("subshot_id", ""))
            if not sid or sid in seen_subshots:
                issues.append(_issue(sid or shot_id, "SUBSHOT_ID", "subshot_id must be non-empty and unique"))
            seen_subshots.add(sid)
            refs = subshot.get("dialogue_refs", [])
            if not isinstance(refs, list):
                issues.append(_issue(sid, "DIALOGUE_REFS_TYPE", "dialogue_refs must be an array"))
                refs = []
            referenced_dialogue.extend(str(ref) for ref in refs)
            source_refs = subshot.get("source_ids", [])
            if not isinstance(source_refs, list):
                issues.append(_issue(sid, "SOURCE_IDS_TYPE", "source_ids must be an array"))
                source_refs = []
            referenced_sources.extend(str(source_id) for source_id in source_refs)
            for ref in refs:
                event = dialogue_events.get(ref)
                if not isinstance(event, dict):
                    issues.append(_issue(sid, "DIALOGUE_EVENT_MISSING", "%s is absent" % ref))
                    continue
                facts = tuple(str(event.get(field, "")) for field in ("ref", "kind", "speaker", "text"))
                if not all(facts) or facts[0] != str(ref) or facts[1] not in SPEECH_KINDS:
                    issues.append(_issue(sid, "DIALOGUE_EVENT_FACTS", "%s has invalid locked facts" % ref))

    source_path = os.path.join(run_dir, ".cache", "orchestrator", "source_ledger.json")
    source_records = _ledger_records(source_path, "units", issues, "SOURCE_LEDGER")
    source_ids = [str(item.get("source_id", "")) for item in source_records]
    if any(not value for value in source_ids) or len(source_ids) != len(set(source_ids)):
        issues.append(_issue("GLOBAL", "SOURCE_LEDGER_ID", "source_id values must be non-empty and unique"))
    source_map = {str(item.get("source_id", "")): item for item in source_records if item.get("source_id")}
    _validate_source_snapshot(run_dir, source_records, issues)
    _validate_dialogue_source_lock(dialogue_events, source_map, issues)
    for event in dialogue_events.values():
        if isinstance(event, dict) and isinstance(event.get("source_ids"), list):
            referenced_sources.extend(str(source_id) for source_id in event["source_ids"])
    for source_id in referenced_sources:
        if source_id not in source_map:
            issues.append(_issue("GLOBAL", "SOURCE_REFERENCE", "unknown source_id %s" % source_id))

    excluded_sources = _source_exclusions(plan, source_map, issues)
    overlap = sorted(set(referenced_sources) & excluded_sources)
    if overlap:
        issues.append(_issue(
            "GLOBAL", "SOURCE_COVERAGE_CONFLICT",
            "source_ids cannot be both referenced and explicitly excluded: %s" % ", ".join(overlap[:20]),
        ))
    required_sources = {
        str(item.get("source_id", ""))
        for item in source_records
        if str(item.get("text", "")).strip()
    }
    missing_sources = sorted(required_sources - set(referenced_sources) - excluded_sources)
    if missing_sources:
        issues.append(_issue(
            "GLOBAL", "SOURCE_COVERAGE",
            "every non-empty source line must be referenced or explicitly model-excluded: %s"
            % ", ".join(missing_sources[:20]),
        ))

    for sid, field, value, expected in validate_durations(plan_path, project_config_path=config_path if os.path.isfile(config_path) else None):
        issues.append(_issue(sid, "DURATION_" + field, "got %s expected %s" % (value, expected)))

    report_path = os.path.join(run_dir, ".cache", "preflight", "report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    blocking = [item for item in issues if item["severity"] == "blocking"]
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump({"pass": not blocking, "issues": issues, "blocking": blocking, "advisories": []}, handle, ensure_ascii=False, indent=2)
    return issues


def _issue(subshot_id, check, msg):
    return {"subshot_id": subshot_id, "check": check, "severity": "blocking", "msg": msg}


def _load_required(path, issues, check):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        issues.append(_issue("GLOBAL", check + "_PARSE", str(exc)))
        return {}


def _ledger_records(path, key, issues, check):
    data = _load_required(path, issues, check)
    records = data.get(key)
    if not isinstance(records, list):
        issues.append(_issue("GLOBAL", check + "_STRUCTURE", "%s must be an array" % key))
        return []
    return [record for record in records if isinstance(record, dict)]


def _validate_source_snapshot(run_dir, source_records, issues):
    path = os.path.join(run_dir, ".cache", "orchestrator", "source_snapshot.json")
    if not os.path.isfile(path):
        return
    snapshot = _load_required(path, issues, "SOURCE_SNAPSHOT")
    snapshot_lines = [item for item in snapshot.get("lines", []) if isinstance(item, dict)]
    line_map = {item.get("line"): item.get("text") for item in snapshot_lines}
    if len(source_records) != len(snapshot_lines):
        issues.append(_issue(
            "GLOBAL", "SOURCE_LEDGER_COMPLETENESS",
            "source ledger must contain every snapshot line exactly once",
        ))
    seen_lines = set()
    for record in source_records:
        source_id = str(record.get("source_id", "") or "GLOBAL")
        line = record.get("line")
        if not isinstance(line, int) or line not in line_map:
            issues.append(_issue(source_id, "SOURCE_LEDGER_LINE", "line must reference source snapshot"))
        elif line in seen_lines:
            issues.append(_issue(source_id, "SOURCE_LEDGER_LINE", "snapshot line is duplicated"))
        elif record.get("text") != line_map[line]:
            issues.append(_issue(source_id, "SOURCE_LEDGER_TEXT", "text must exactly match source snapshot"))
        elif source_id != "SRC%06d" % line:
            issues.append(_issue(source_id, "SOURCE_LEDGER_ID", "source_id must match its deterministic line id"))
        seen_lines.add(line)


def _source_exclusions(plan, source_map, issues):
    records = plan.get("source_exclusions", [])
    if not isinstance(records, list):
        issues.append(_issue("GLOBAL", "SOURCE_EXCLUSIONS_TYPE", "source_exclusions must be an array"))
        return set()
    excluded = set()
    for record in records:
        if not isinstance(record, dict):
            issues.append(_issue("GLOBAL", "SOURCE_EXCLUSION_STRUCTURE", "each exclusion must be an object"))
            continue
        source_id = str(record.get("source_id", ""))
        reason = str(record.get("reason", "")).strip()
        if not source_id or source_id in excluded:
            issues.append(_issue(source_id or "GLOBAL", "SOURCE_EXCLUSION_ID", "source_id must be non-empty and unique"))
            continue
        if source_id not in source_map:
            issues.append(_issue(source_id, "SOURCE_EXCLUSION_UNKNOWN", "source_id is absent from the engineering ledger"))
        if not reason:
            issues.append(_issue(source_id, "SOURCE_EXCLUSION_REASON", "model-authored reason is required"))
        excluded.add(source_id)
    return excluded


def _validate_dialogue_source_lock(dialogue_events, source_record_by_id, issues):
    for ref, event in dialogue_events.items():
        if not isinstance(event, dict):
            continue
        source_refs = event.get("source_ids")
        if not isinstance(source_refs, list) or not source_refs:
            issues.append(_issue(str(ref), "DIALOGUE_SOURCE_IDS", "dialogue event requires source_ids"))
            continue
        source_lines = []
        for source_id in source_refs:
            record = source_record_by_id.get(str(source_id))
            if not isinstance(record, dict):
                issues.append(_issue(str(ref), "DIALOGUE_SOURCE_UNKNOWN", "unknown source_id %s" % source_id))
            else:
                source_lines.append(str(record.get("text", "")))
        exact = str(event.get("text", ""))
        if exact and source_lines and not any(exact in line for line in source_lines):
            issues.append(_issue(str(ref), "DIALOGUE_SOURCE_TEXT", "dialogue text is not an exact source substring"))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: preflight_check.py <run_dir>")
    found = run(sys.argv[1])
    print(json.dumps(found, ensure_ascii=False, indent=2))
    raise SystemExit(0 if not found else 1)
