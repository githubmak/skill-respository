#!/usr/bin/env python3
"""Diagnose missing camera design without rewriting authored prompts."""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from modec_v4 import PROMPT_LABELS, split_sections


SHORT_MOVES = "固定|推|拉|摇|移|跟|升|降|俯|仰|环绕|甩|变焦|旋转|手持|穿梭"


def enforce_camera_detail(run_dir):
    package_path = _find_prompt_package(run_dir)
    director_path = os.path.join(run_dir, ".cache", "director", "director_pass.json")
    if not os.path.exists(package_path) or not os.path.exists(director_path):
        print("[ENFORCE V4] Missing input files")
        return 0
    with open(director_path, "r", encoding="utf-8-sig") as handle:
        director = json.load(handle)
    with open(package_path, "r", encoding="utf-8-sig") as handle:
        package = json.load(handle)
    issues = 0
    for shot in package.get("shots", package.get("items", [])):
        sections = split_sections(shot.get("full_prompt", ""), PROMPT_LABELS)
        if list(sections) != PROMPT_LABELS:
            issues += 1
            continue
        design = sections["镜头设计"]
        if "主要运镜" not in design:
            issues += 1
    if issues:
        print(f"[CAMERA CONTRACT] {issues} shot(s) missing authored camera design; return them to Composer")
    else:
        print("[CAMERA CONTRACT] PASS - no prompt was rewritten")
    return issues


def _find_prompt_package(run_dir):
    candidates = [
        os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json"),
        os.path.join(run_dir, ".cache", "composer", "prompt_package.json"),
        os.path.join(run_dir, ".cache", "prompt_package.json"),
    ]
    return next((path for path in candidates if os.path.exists(path)), candidates[0])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: enforce_camera_detail.py <run_dir>")
        sys.exit(2)
    enforce_camera_detail(sys.argv[1])
