#!/usr/bin/env python3
"""Detect wording that repeatedly triggered false-positive storyboard validation.

This is intentionally a lint pass, not a creative rewrite.  Advisory mode reports
risks before compilation; strict mode makes the same risks release-blocking.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from validate_storyboard import direct_prompt, iter_children, iter_groups


BOUNDARY_NEGATION = re.compile(r"没有(?:跨过|越过|进入)|未(?:跨过|越过)|不(?:越过|跨过)")
TERMINAL_MARKERS = re.compile(r"保持到结束|稳定到结束|终态停稳|直到结束")
DIALOGUE_TEXT = re.compile(r"“[^”]*”|‘[^’]*’|\"[^\"]*\"")


def lint_markdown(markdown: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for group in iter_groups(markdown):
        group_id = group.group(1)
        for number, child in enumerate(iter_children(group.group(3)), start=1):
            shot_id = f"{group_id}-{number}"
            prompt = direct_prompt(child.group(0))
            if not prompt:
                continue
            # Dialogue may legitimately contain a negative phrase; lint only the visual prose.
            visual_prose = DIALOGUE_TEXT.sub("", prompt)
            boundary = BOUNDARY_NEGATION.search(visual_prose)
            if boundary:
                findings.append({
                    "shot_id": shot_id,
                    "code": "BOUNDARY_NEGATION",
                    "message": "负向门槛措辞容易污染相邻人物状态；改写为逐人正向起点/转换/终态。",
                    "match": boundary.group(0),
                })
            terminal_matches = list(TERMINAL_MARKERS.finditer(visual_prose))
            for match in terminal_matches:
                if match.start() < len(prompt) * 0.70:
                    findings.append({
                        "shot_id": shot_id,
                        "code": "EARLY_TERMINAL_MARKER",
                        "message": "终态词出现在正文前段，可能让签名核心被判定为过晚；将稳定句后置到最后20%。",
                        "match": match.group(0),
                    })
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("storyboard")
    parser.add_argument("--advisory", action="store_true", help="report findings without failing")
    args = parser.parse_args(argv)
    try:
        path = Path(args.storyboard).expanduser().resolve()
        findings = lint_markdown(path.read_text(encoding="utf-8-sig"))
        result = {
            "pass": args.advisory or not findings,
            "mode": "advisory" if args.advisory else "strict",
            "storyboard": str(path),
            "findings": findings,
            "primary_storyboard_modified": False,
        }
    except (OSError, ValueError) as exc:
        result = {"pass": False, "error": str(exc), "primary_storyboard_modified": False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
