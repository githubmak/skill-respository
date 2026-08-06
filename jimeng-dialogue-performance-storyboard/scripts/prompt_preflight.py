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

from validate_storyboard import (
    camera_prop_motion_ownership_issues,
    direct_prompt,
    intentional_static_camera,
    iter_children,
    iter_groups,
    reflective_light_transport_issues,
    semantic_ambiguity_issues,
)


BOUNDARY_NEGATION = re.compile(r"没有(?:跨过|越过|进入)|未(?:跨过|越过)|不(?:越过|跨过)")
TERMINAL_MARKERS = re.compile(r"保持到结束|稳定到结束|终态停稳|直到结束")
DIALOGUE_TEXT = re.compile(r"“[^”]*”|‘[^’]*’|\"[^\"]*\"")
TEMPLATE_PHRASES = (
    "第一焦点锁定主体与道具",
    "主光显露动作关系",
    "起幅固定",
    "稳定落幅",
)
STATIC_TEMPLATE_TERMS = ("摄影机固定", "固定机位", "镜头固定", "有意静止", "保持静止")


def lint_markdown(markdown: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    phrase_hits: dict[str, list[str]] = {phrase: [] for phrase in TEMPLATE_PHRASES}
    static_template_hits: list[str] = []
    for group in iter_groups(markdown):
        group_id = group.group(1)
        for number, child in enumerate(iter_children(group.group(3)), start=1):
            shot_id = f"{group_id}-{number}"
            prompt = direct_prompt(child.group(0))
            if not prompt:
                continue
            for phrase in TEMPLATE_PHRASES:
                if phrase in prompt:
                    phrase_hits[phrase].append(shot_id)
            if any(term in prompt for term in STATIC_TEMPLATE_TERMS) and not intentional_static_camera(prompt):
                static_template_hits.append(shot_id)
            # Dialogue may legitimately contain a negative phrase; lint only the visual prose.
            visual_prose = DIALOGUE_TEXT.sub("", prompt)
            for issue in reflective_light_transport_issues(visual_prose):
                findings.append({
                    "shot_id": shot_id,
                    "code": "REFLECTIVE_LIGHT_OWNERSHIP",
                    "message": issue,
                    "match": "reflective-light-transport",
                })
            for issue in camera_prop_motion_ownership_issues(visual_prose):
                findings.append({
                    "shot_id": shot_id,
                    "code": "CAMERA_PROP_MOTION_OWNERSHIP",
                    "message": issue,
                    "match": "camera-focus-prop-path",
                })
            for issue in semantic_ambiguity_issues(visual_prose):
                findings.append({
                    "shot_id": shot_id,
                    "code": "SEEDANCE_SEMANTIC_AMBIGUITY",
                    "message": issue,
                    "match": "opaque-visual-language",
                })
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
    for phrase, shot_ids in phrase_hits.items():
        if len(shot_ids) >= 3:
            findings.append({
                "shot_id": shot_ids[-1],
                "code": "REPEATED_TEMPLATE_POLLUTION",
                "message": "同一模板句跨镜头重复出现；删除机械句，恢复本镜具体焦点、因果和终态。",
                "match": phrase,
                "affected_shots": shot_ids,
            })
    if len(static_template_hits) >= 3:
        findings.append({
            "shot_id": static_template_hits[-1],
            "code": "STATIC_CAMERA_TEMPLATE_POLLUTION",
            "message": "固定/静止措辞跨镜头批量重复且没有等待、压迫、观察或僵持收益；回到导演选型，不得批量替换成微推。",
            "match": "static-camera-family",
            "affected_shots": static_template_hits,
        })
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("storyboard")
    parser.add_argument("--advisory", action="store_true", help="report findings without failing")
    parser.add_argument("--report")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)
    if not args.compact or not args.report:
        parser.error("legacy prompt-preflight output is disabled; --compact and --report are required")
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
    if args.report:
        report = Path(args.report).expanduser().resolve()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.compact:
        print(json.dumps({
            "status": "PASS" if result.get("pass") else "FAIL",
            "mode": result.get("mode"),
            "finding_count": len(result.get("findings", [])),
            "report": str(Path(args.report).expanduser().resolve()) if args.report else None,
        }, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
