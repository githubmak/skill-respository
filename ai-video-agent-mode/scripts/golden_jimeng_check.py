#!/usr/bin/env python3
"""Lightweight regression check for the neutral Jimeng prompt exemplar."""

import os
import sys


REQUIRED = ("生成规格：", "主体与空间锁定：", "主镜头连续规则：", "子镜头组：", "光照、声音与稳定约束：")
FORBIDDEN = ("画面锁定：", "镜头设计：", "表演时间轴：", "光照与声音：", "轴线：", "越轴", "OTS", "反打", "reference_assets", "i2v", "r2v")


def check(skill_dir):
    path = os.path.join(skill_dir, "references", "format_example.txt")
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    issues = ["missing %s" % label for label in REQUIRED if label not in text]
    issues.extend("forbidden %s" % token for token in FORBIDDEN if token in text)
    return issues


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(__file__))
    issues = check(root)
    if issues:
        print("[GOLDEN JIMENG] FAIL")
        for issue in issues:
            print("- " + issue)
        raise SystemExit(1)
    print("[GOLDEN JIMENG] PASS")
