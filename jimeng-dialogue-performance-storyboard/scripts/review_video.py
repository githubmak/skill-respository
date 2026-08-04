#!/usr/bin/env python3
"""Run optional FFmpeg-backed objective metrics on generated videos."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys


def analyzer_path():
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repository = os.path.dirname(skill_dir)
    return os.path.join(repository, "ai-video-agent-mode", "scripts", "calibration", "visual_metrics.py")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--samples", type=int, default=18)
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)
    analyzer = analyzer_path()
    if not os.path.isfile(analyzer):
        print("video metrics analyzer is unavailable; expected sibling skill: " + analyzer, file=sys.stderr)
        return 2
    command = [sys.executable, analyzer]
    if args.self_test:
        command.append("--self-test")
    else:
        command.extend(["--samples", str(args.samples), *args.paths])
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
