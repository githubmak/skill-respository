#!/usr/bin/env python3
"""Ensure the v4 镜头设计 section contains one complete main camera move."""

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
    camera_map = {
        item.get("subshot_id", ""): item.get("movement_detail", item.get("camera", ""))
        for item in director.get("items", [])
    }
    with open(package_path, "r", encoding="utf-8-sig") as handle:
        package = json.load(handle)
    fixed = 0
    issues = 0
    for shot in package.get("shots", package.get("items", [])):
        sections = split_sections(shot.get("full_prompt", ""), PROMPT_LABELS)
        if list(sections) != PROMPT_LABELS:
            issues += 1
            continue
        design = sections["镜头设计"]
        detail = str(camera_map.get(shot.get("subshot_id", ""), "") or "").strip()
        if not detail:
            issues += 1
            continue
        short = re.search(rf"主要运镜[：:]\s*({SHORT_MOVES})(?:[。；]|$)", design)
        if short:
            design = design[:short.start()] + "主要运镜：" + detail.rstrip("。") + "。" + design[short.end():]
            sections["镜头设计"] = design.strip()
            shot["full_prompt"] = "\n\n".join(f"{label}：{sections[label]}" for label in PROMPT_LABELS)
            fixed += 1
        elif "主要运镜" not in design:
            sections["镜头设计"] = design.rstrip("。") + "。主要运镜：" + detail.rstrip("。") + "。"
            shot["full_prompt"] = "\n\n".join(f"{label}：{sections[label]}" for label in PROMPT_LABELS)
            fixed += 1
    with open(package_path, "w", encoding="utf-8") as handle:
        json.dump(package, handle, ensure_ascii=False, indent=2)
    if issues:
        print(f"[ENFORCE V4] {fixed} fixed, {issues} blocking issue(s)")
    else:
        print(f"[ENFORCE V4] PASS - {fixed} fixes")
    return fixed


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
