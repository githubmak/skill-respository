#!/usr/bin/env python3
"""Deterministically validate the copied model-authored main-shot package."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from validate_deterministic_package import validate_package


def validate(run_dir):
    path = os.path.join(run_dir, ".cache", "composer", "jimeng_master_tasks.json")
    result = validate_package(path, run_dir=run_dir)
    return result["issues"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate_master_tasks.py <run_dir>")
    issues = validate(sys.argv[1])
    for issue in issues:
        print(issue)
    raise SystemExit(0 if not issues else 1)
