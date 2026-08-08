#!/usr/bin/env python3
"""Validate only mechanically provable delivery facts.

This module deliberately does not parse or score creative language. Camera,
performance, emotion, lighting, palette, rhythm, and Seedance comprehensibility
belong to the model Editor. Missing creative text is routed back to the model;
code never manufactures or rewrites it.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from contract_registry import PROMPT_CONTRACT_VERSION, SHOT_REQUIRED_FIELDS
from seedance_target import normalize_target


MAX_SHOT_SECONDS = 15.0
MAX_SEEDANCE_CHARS = 700
MAX_DIRECTOR_CARD_CHARS = 500
DIALOGUE_FACT_FIELDS = ("ref", "kind", "speaker", "text")


def validate_package(
    package_path, run_dir=None, report_path=None, allow_incomplete=False,
    selected_shot_ids=None, require_editor=False, allow_batch_envelope=False,
):
    issues = []
    package = _load(package_path, issues, "prompt package")
    plan = _load(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"), issues, "shot plan") if run_dir else {}
    config = _load_optional(os.path.join(run_dir, "project_config.json")) if run_dir else {}
    target = normalize_target(config.get("seedance_target", "auto"))

    if not isinstance(package, dict):
        package = {}
    allowed_envelopes = ({"contract_version", "shots"}, {"shots"}) if allow_batch_envelope else ({"contract_version", "shots"},)
    if set(package) not in allowed_envelopes:
        issues.append("PACKAGE_TOP_LEVEL: only contract_version and shots are allowed")
    if ("contract_version" in package or not allow_batch_envelope) and package.get("contract_version") != PROMPT_CONTRACT_VERSION:
        issues.append("CONTRACT_VERSION: expected %s" % PROMPT_CONTRACT_VERSION)
    shots = package.get("shots", [])
    if not isinstance(shots, list) or not shots:
        issues.append("SHOTS: must be a non-empty array")
        shots = []

    selected = {str(value) for value in selected_shot_ids or [] if str(value).strip()}
    if selected:
        shots = [shot for shot in shots if isinstance(shot, dict) and _shot_identity(shot) in selected]
        present = {_shot_identity(shot) for shot in shots}
        for missing in sorted(selected - present):
            issues.append("%s: selected shot is absent" % missing)

    expectations, expected_source_ids = _plan_expectations(plan)
    seen_ids = set()
    covered_source_ids = []
    for index, shot in enumerate(shots):
        if not isinstance(shot, dict):
            issues.append("SHOT_%d: must be an object" % (index + 1))
            continue
        sid = _shot_identity(shot) or "SHOT_%d" % (index + 1)
        prefix = sid + ": "
        if sid in seen_ids:
            issues.append(prefix + "duplicate shot identity")
        seen_ids.add(sid)
        missing_fields = sorted(SHOT_REQUIRED_FIELDS - set(shot))
        if missing_fields:
            issues.append(prefix + "missing fields " + ", ".join(missing_fields))

        duration = shot.get("duration")
        if not _positive_number(duration):
            issues.append(prefix + "duration must be a positive number")
        elif float(duration) > MAX_SHOT_SECONDS:
            issues.append(prefix + "duration exceeds 15 seconds")

        for field in ("full_prompt", "director_card"):
            if not isinstance(shot.get(field), str) or not shot.get(field).strip():
                issues.append(prefix + "CREATIVE_REWRITE_REQUIRED: %s is missing" % field)
        card = shot.get("director_card", "")
        if isinstance(card, str) and len(card) > MAX_DIRECTOR_CARD_CHARS:
            issues.append(prefix + "CREATIVE_REWRITE_REQUIRED: director_card %d>%d chars" % (len(card), MAX_DIRECTOR_CARD_CHARS))
        issues.extend(prefix + issue for issue in _seedance_prompt_issues(shot, target))
        negative = shot.get("negative_prompt")
        if not isinstance(negative, str) or not negative.strip():
            issues.append(prefix + "CREATIVE_REWRITE_REQUIRED: negative_prompt is missing")

        metadata = shot.get("qa_metadata")
        if not isinstance(metadata, dict):
            issues.append(prefix + "qa_metadata must be an object")
            metadata = {}
        for field in ("dialogue_refs", "dialogue_events"):
            if field not in metadata:
                issues.append(prefix + "qa_metadata.%s is missing" % field)
        control = shot.get("generation_control")
        if not isinstance(control, dict):
            issues.append(prefix + "generation_control must be an object")
        else:
            if control.get("mode") != "t2v":
                issues.append(prefix + "generation_control.mode must equal t2v")
            if not isinstance(control.get("audio_enabled"), bool):
                issues.append(prefix + "generation_control.audio_enabled must be boolean")
            if "reference_assets" in control:
                issues.append(prefix + "T2V package must not contain reference_assets")

        expected = expectations.get(str(shot.get("shot_id", "")), {})
        source_ids = _string_list(shot.get("source_subshot_ids", []))
        covered_source_ids.extend(source_ids)
        if expected:
            if source_ids != expected["source_ids"]:
                issues.append(prefix + "source_subshot_ids do not match shot plan")
            if _positive_number(duration) and abs(float(duration) - expected["duration"]) > 0.01:
                issues.append(prefix + "duration does not equal planned source duration")
            issues.extend(prefix + issue for issue in _dialogue_issues(metadata, expected["dialogue_events"]))
            if isinstance(control, dict) and control.get("audio_enabled") is True:
                for event in expected["dialogue_events"]:
                    text = str(event.get("text", ""))
                    for version, prompt in _selected_prompts(shot, target).items():
                        if text and text not in prompt:
                            issues.append(prefix + "verbatim dialogue is absent from Seedance %s prompt" % version)

    if expectations and not allow_incomplete and not selected:
        if seen_ids != set(expectations):
            issues.append("SHOT_COVERAGE: expected %s, got %s" % (sorted(expectations), sorted(seen_ids)))
        if covered_source_ids != expected_source_ids:
            issues.append("SOURCE_COVERAGE: source subshots are missing, reordered, or duplicated")

    if require_editor and run_dir:
        review = _load_optional(os.path.join(run_dir, ".cache", "review", "llm_gate_result.json"))
        if review.get("pass") is not True or not isinstance(review.get("blocking"), list) or review.get("blocking"):
            issues.append("MODEL_EDITOR: final creative review is missing or blocking")
        review_windows = review.get("windows", []) if isinstance(review.get("windows"), list) else []
        reviewed_ids = []
        actual_by_window = {}
        for window in review_windows:
            if not isinstance(window, dict):
                continue
            window_id = str(window.get("window_id", "") or "")
            values = window.get("reviewed_shot_ids", [])
            if not window_id or window_id in actual_by_window or not isinstance(values, list):
                issues.append("MODEL_EDITOR_COVERAGE: window IDs and reviewed_shot_ids must be unique arrays")
                continue
            normalized = [str(value) for value in values if str(value).strip()]
            actual_by_window[window_id] = normalized
            reviewed_ids.extend(normalized)
        if len(reviewed_ids) != len(set(reviewed_ids)) or set(reviewed_ids) != seen_ids:
            issues.append("MODEL_EDITOR_COVERAGE: reviewed shots must exactly cover the delivered package")
        try:
            from editor_scene_windows import build as build_editor_windows
            expected_by_window = {
                str(window.get("window_id", "")): [str(value) for value in window.get("shot_ids", [])]
                for window in build_editor_windows(run_dir)
            }
        except (OSError, ValueError, TypeError):
            expected_by_window = {}
        if actual_by_window != expected_by_window:
            issues.append("MODEL_EDITOR_COVERAGE: reviewed scene windows do not match the planned windows")

    report = {
        "contract_version": PROMPT_CONTRACT_VERSION,
        "validator_scope": "deterministic_only",
        "package_path": os.path.abspath(package_path),
        "package_sha256": _sha256(package_path) if os.path.isfile(package_path) else "",
        "seedance_target": target,
        "pass": not issues,
        "issues": issues,
        "shot_count": len(shots),
    }
    if report_path:
        os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
    return report


def selected_seedance_prompt(shot, target):
    """Select a model-authored prompt without modifying a character."""
    normalized = normalize_target(target)
    if normalized in {"2.0", "2.5"}:
        variants = shot.get("seedance_prompt_variants", {})
        if isinstance(variants, dict) and isinstance(variants.get(normalized), str) and variants[normalized].strip():
            return variants[normalized]
    value = shot.get("seedance_prompt", "")
    return value if isinstance(value, str) else ""


def _seedance_prompt_issues(shot, target):
    issues = []
    if target == "both":
        variants = shot.get("seedance_prompt_variants")
        if not isinstance(variants, dict):
            return ["CREATIVE_REWRITE_REQUIRED: seedance_prompt_variants must contain model-authored 2.0 and 2.5 prompts"]
        prompts = {version: variants.get(version) for version in ("2.0", "2.5")}
    else:
        prompts = {target: selected_seedance_prompt(shot, target)}
    for version, prompt in prompts.items():
        if not isinstance(prompt, str) or not prompt.strip():
            issues.append("CREATIVE_REWRITE_REQUIRED: model-authored Seedance %s prompt is missing" % version)
        elif len(prompt) > MAX_SEEDANCE_CHARS:
            issues.append("CREATIVE_REWRITE_REQUIRED: Seedance %s prompt %d>%d chars" % (version, len(prompt), MAX_SEEDANCE_CHARS))
    return issues


def _selected_prompts(shot, target):
    if target == "both":
        variants = shot.get("seedance_prompt_variants", {})
        return {
            version: str(variants.get(version, "")) if isinstance(variants, dict) else ""
            for version in ("2.0", "2.5")
        }
    return {target: selected_seedance_prompt(shot, target)}


def _dialogue_issues(metadata, expected_events):
    actual = metadata.get("dialogue_events", [])
    if not isinstance(actual, list):
        return ["qa_metadata.dialogue_events must be an array"]
    actual_facts = [tuple(str(event.get(field, "")) for field in DIALOGUE_FACT_FIELDS) for event in actual if isinstance(event, dict)]
    expected_facts = [tuple(str(event.get(field, "")) for field in DIALOGUE_FACT_FIELDS) for event in expected_events]
    if actual_facts != expected_facts:
        return ["dialogue ref/kind/speaker/text differs from the source ledger"]
    refs = _string_list(metadata.get("dialogue_refs", []))
    expected_refs = [facts[0] for facts in expected_facts if facts[0]]
    if refs != expected_refs:
        return ["dialogue_refs differ from the source ledger"]
    return []


def _plan_expectations(plan):
    ledger = plan.get("dialogue_events", {}) if isinstance(plan, dict) else {}
    ledger = ledger if isinstance(ledger, dict) else {}
    expectations = {}
    ordered_source_ids = []
    for planned in plan.get("shots", []) if isinstance(plan, dict) else []:
        if not isinstance(planned, dict):
            continue
        shot_id = str(planned.get("shot_id", ""))
        subshots = planned.get("subshots", []) if isinstance(planned.get("subshots"), list) else []
        source_ids = [str(item.get("subshot_id", "")) for item in subshots if isinstance(item, dict) and item.get("subshot_id")]
        ordered_source_ids.extend(source_ids)
        refs = []
        duration = 0.0
        for item in subshots:
            if not isinstance(item, dict):
                continue
            duration += float(item.get("duration", 0) or 0)
            refs.extend(_string_list(item.get("dialogue_refs", [])))
        events = [dict(ledger[ref]) for ref in refs if isinstance(ledger.get(ref), dict)]
        expectations[shot_id] = {"source_ids": source_ids, "duration": round(duration, 3), "dialogue_events": events}
    return expectations, ordered_source_ids


def _shot_identity(shot):
    return str(shot.get("shot_id", "") or shot.get("subshot_id", ""))


def _positive_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _string_list(value):
    return [str(item) for item in value] if isinstance(value, list) else []


def _load(path, issues, label):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        issues.append("%s: %s" % (label.upper().replace(" ", "_"), exc))
        return {}


def _load_optional(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit("usage: validate_deterministic_package.py <package.json> [run_dir]")
    result = validate_package(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["pass"] else 1)
