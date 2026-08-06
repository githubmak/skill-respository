#!/usr/bin/env python3
"""Check deterministic package and export-layout facts only."""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from seedance_target import normalize_target
from validate_deterministic_package import selected_seedance_prompt, validate_package


INTERNAL_TITLE_LEAK = re.compile(
    r"(?m)^\s*(?:#+\s*)?[^|\n]+\|\s*S\d+-\d+\s*\|[^\n]*\|\s*"
    r"(?:dialogue|action|dramatic|environment|object)\s*\|\s*"
    r"(?:neutral|latent|rising|peak|release)\s*$"
)


def check_export(md_path, run_dir, quality_mode=False):
    package_path = _find_package(run_dir)
    report = validate_package(
        package_path,
        run_dir=run_dir,
        report_path=os.path.join(run_dir, ".cache", "validate", "deterministic_export_check.json"),
        require_editor=True,
    )
    failures = list(report["issues"])
    if not quality_mode:
        failures.extend(_delivery_file_issues(md_path, run_dir, package_path))
    total = 2 if quality_mode else 6
    failed = len(failures)
    print("[DETERMINISTIC EXPORT CHECK] %s" % ("PASS" if not failures else "FAIL"))
    for issue in failures[:80]:
        print("  - " + issue)
    return max(0, total - failed), failed


def _delivery_file_issues(md_path, run_dir, package_path):
    if not md_path or not os.path.isfile(md_path):
        return ["MARKDOWN: delivery file is missing"]
    with open(md_path, "r", encoding="utf-8-sig") as handle:
        text = handle.read()
    package = _load(package_path)
    config = _load_optional(os.path.join(run_dir, "project_config.json"))
    target = _target_from_export_path(md_path, normalize_target(config.get("seedance_target", "auto")))
    issues = []
    for shot in package.get("shots", []):
        if not isinstance(shot, dict):
            continue
        shot_id = str(shot.get("shot_id", ""))
        prompt = selected_seedance_prompt(shot, target)
        if shot_id not in text:
            issues.append("%s: shot id is absent from Markdown" % shot_id)
        if prompt and prompt not in text:
            issues.append("%s: model-authored Seedance prompt was changed or omitted" % shot_id)
        card = shot.get("director_card", "")
        if isinstance(card, str) and card and card not in text:
            issues.append("%s: model-authored director_card was changed or omitted" % shot_id)
        for event in (shot.get("qa_metadata", {}) or {}).get("dialogue_events", []):
            if isinstance(event, dict) and str(event.get("text", "")) not in text:
                issues.append("%s: verbatim dialogue is absent from Markdown" % shot_id)
    if INTERNAL_TITLE_LEAK.search(text):
        issues.append("LAYOUT: internal machine title leaked")
    xlsx_path = os.path.splitext(md_path)[0] + ".xlsx"
    if not os.path.isfile(xlsx_path):
        issues.append("XLSX: companion workbook is missing")
    return issues


def _target_from_export_path(path, configured):
    name = os.path.basename(path)
    if configured == "both":
        if "Seedance2.0" in name:
            return "2.0"
        if "Seedance2.5" in name:
            return "2.5"
    return configured


def _find_package(run_dir):
    for relative in (
        ".cache/composer/merged.prompt_package.json",
        ".cache/composer/prompt_package.json",
        ".cache/prompt_package.json",
    ):
        path = os.path.join(run_dir, relative)
        if os.path.isfile(path):
            return path
    return os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json")


def _plan_index(plan):
    by_id, scene_by_id, expected_source_ids = {}, {}, set()
    for shot in plan.get("shots", []) if isinstance(plan, dict) else []:
        if not isinstance(shot, dict):
            continue
        scene = str(shot.get("scene", ""))
        for subshot in shot.get("subshots", []) if isinstance(shot.get("subshots"), list) else []:
            if not isinstance(subshot, dict):
                continue
            sid = str(subshot.get("subshot_id", ""))
            if sid:
                by_id[sid] = subshot
                scene_by_id[sid] = scene
                expected_source_ids.add(sid)
    return by_id, scene_by_id, expected_source_ids


def _export_check(md_path, quality_mode, expected_ids):
    if quality_mode:
        return True, "quality mode"
    if not md_path or not os.path.isfile(md_path):
        return False, "markdown missing"
    with open(md_path, "r", encoding="utf-8-sig") as handle:
        text = handle.read()
    ids_ok = all(identifier in text for identifier in expected_ids)
    xlsx_ok = os.path.isfile(os.path.splitext(md_path)[0] + ".xlsx")
    title_ok = not INTERNAL_TITLE_LEAK.search(text)
    return ids_ok and xlsx_ok and title_ok, "ids=%s, xlsx=%s, title=%s" % (ids_ok, xlsx_ok, title_ok)


def _direct_export_blocks(markdown_text):
    pattern = re.compile(
        r"【画面描述｜直接复制】\s*\n+(.*?)(?=\n+【导演卡｜直接复制[^】]*】|\n+#### |\Z)",
        re.S,
    )
    return [match.group(1).strip() for match in pattern.finditer(str(markdown_text or "")) if match.group(1).strip()]


def _production_control_export_issues(markdown_text):
    """Retained API: production-control semantics are reviewed by the model Editor."""
    return []


def _source_dialogue_events(plan, metadata):
    ledger = plan.get("dialogue_events", {}) if isinstance(plan.get("dialogue_events"), dict) else {}
    return [dict(ledger[ref]) for ref in _as_list(metadata.get("dialogue_refs", [])) if isinstance(ledger.get(ref), dict)]


def _as_list(value):
    return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _load_optional(path):
    try:
        return _load(path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _editor_review_check(llm_review):
    valid = (
        isinstance(llm_review, dict)
        and llm_review.get("pass") is True
        and isinstance(llm_review.get("blocking"), list)
        and not llm_review["blocking"]
    )
    return valid, "ok" if valid else "missing or blocking model Editor review"


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--quality":
        _passed, failed = check_export("", sys.argv[2], quality_mode=True)
        raise SystemExit(0 if failed == 0 else 1)
    if len(sys.argv) == 3:
        _passed, failed = check_export(sys.argv[1], sys.argv[2], quality_mode=False)
        raise SystemExit(0 if failed == 0 else 1)
    raise SystemExit("usage: check_export.py <export.md> <run_dir> | --quality <run_dir>")
