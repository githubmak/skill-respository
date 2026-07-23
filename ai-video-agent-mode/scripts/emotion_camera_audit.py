#!/usr/bin/env python3
"""Final semantic audit for performance, expectation anchors, and camera cuts."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from modec_v4 import (
    attention_handoff_issues, camera_competition_issues, continuity_contract_issues,
    expectation_anchor_issues, jimeng_shot_group_issues, performance_causality_issues,
    listener_reaction_issues, performance_contract_issues, shot_group_handoff_issues,
)


def audit(run_dir, output_path=None):
    package_path = _find_package(run_dir)
    package = _load(package_path) if package_path else {}
    output_path = output_path or os.path.join(run_dir, ".cache", "review", "emotion_camera_audit.json")
    results = []
    for shot in package.get("shots", []) if isinstance(package.get("shots"), list) else []:
        metadata = shot.get("qa_metadata", {}) if isinstance(shot.get("qa_metadata"), dict) else {}
        roles = metadata.get("performance_priority", {}) if isinstance(metadata.get("performance_priority"), dict) else {}
        visible = [roles.get("primary", "")] + list(roles.get("supporting", []) or []) + list(roles.get("background", []) or [])
        visible = [str(value).strip() for value in visible if str(value).strip()]
        prompt = str(shot.get("full_prompt", "") or "")
        mode = metadata.get("editorial_mode", "continuous_take")
        issues = []
        issues.extend(performance_causality_issues(metadata, visible))
        issues.extend(performance_contract_issues(metadata, prompt, visible))
        issues.extend(listener_reaction_issues(metadata, prompt))
        issues.extend(expectation_anchor_issues(metadata, prompt))
        issues.extend(continuity_contract_issues(metadata, prompt, visible))
        issues.extend(camera_competition_issues(prompt, mode))
        issues.extend(attention_handoff_issues(metadata, prompt))
        issues.extend(shot_group_handoff_issues(metadata))
        issues.extend(jimeng_shot_group_issues(prompt, mode))
        results.append({"shot_id": shot.get("shot_id", ""), "subshot_id": shot.get("subshot_id", ""), "pass": not issues, "issues": issues})
    result = {"contract_version": "jimeng-t2v-v1", "pass": bool(results) and all(item["pass"] for item in results), "shots": results}
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    return result, output_path


def _find_package(run_dir):
    for relative in (".cache/composer/merged.prompt_package.json", ".cache/composer/prompt_package.json", ".cache/prompt_package.json"):
        path = os.path.join(run_dir, relative)
        if os.path.exists(path):
            return path
    return ""


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit("usage: emotion_camera_audit.py <run_dir> [output.json]")
    result, path = audit(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)
    print("[EMOTION CAMERA AUDIT] %s: %s" % ("PASS" if result["pass"] else "FAIL", path))
    raise SystemExit(0 if result["pass"] else 1)
