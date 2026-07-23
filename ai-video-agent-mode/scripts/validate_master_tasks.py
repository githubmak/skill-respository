#!/usr/bin/env python3
"""Validate the canonical Jimeng main-shot delivery package."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from modec_v4 import PROMPT_LABELS, jimeng_shot_group_issues, split_sections, timeline_issues


def validate(run_dir):
    path = os.path.join(run_dir, ".cache", "composer", "jimeng_master_tasks.json")
    plan_path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")
    package, plan = _load(path), _load(plan_path)
    errors = []
    tasks = package.get("shots", []) if isinstance(package, dict) else []
    expected = {shot.get("shot_id", ""): [sub.get("subshot_id", "") for sub in shot.get("subshots", [])] for shot in plan.get("shots", [])}
    actual = {task.get("shot_id", ""): task for task in tasks if isinstance(task, dict)}
    if package.get("contract_version") != "jimeng-t2v-v1":
        errors.append("contract_version must be jimeng-t2v-v1")
    if set(actual) != set(expected):
        errors.append("main-shot coverage mismatch")
    for shot_id, source_ids in expected.items():
        task = actual.get(shot_id, {})
        if task.get("source_subshot_ids") != source_ids:
            errors.append("%s source_subshot_ids mismatch" % shot_id)
        if not 1 <= len(source_ids) <= 3:
            errors.append("%s must contain 1-3 child shots" % shot_id)
        if task.get("generation_control", {}).get("mode") != "t2v":
            errors.append("%s is not T2V" % shot_id)
        prompt = str(task.get("full_prompt", "") or "")
        if list(split_sections(prompt, PROMPT_LABELS)) != PROMPT_LABELS:
            errors.append("%s does not contain current five sections" % shot_id)
        errors.extend("%s: %s" % (shot_id, issue) for issue in timeline_issues(prompt, task.get("duration", 0)))
        mode = task.get("qa_metadata", {}).get("editorial_mode", "continuous_take")
        errors.extend("%s: %s" % (shot_id, issue) for issue in jimeng_shot_group_issues(prompt, mode))
    return errors


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate_master_tasks.py <run_dir>")
    issues = validate(sys.argv[1])
    print(json.dumps(issues, ensure_ascii=False, indent=2))
    raise SystemExit(0 if not issues else 1)
