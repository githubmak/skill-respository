#!/usr/bin/env python3
"""Guard local storyboard repairs against accidental whole-file rewrites."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import validate_storyboard as validator


SCOPES = ("field", "shot", "pair", "window", "scene")


def _shot_map(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for group in validator.iter_groups(text):
        group_id, block = group.group(1), group.group(3)
        for number, child in enumerate(validator.iter_children(block), start=1):
            result[f"{group_id}-{number}"] = child.group(0)
    return result


def _non_shot_content(text: str) -> str:
    """Strip shot blocks so global and group-level edits remain visible."""
    pieces: list[str] = []
    cursor = 0
    for group in validator.iter_groups(text):
        pieces.append(text[cursor:group.start(3)])
        cursor = group.end(3)
    pieces.append(text[cursor:])
    return "\n".join(pieces)


def changed_shots(before: str, after: str) -> list[str]:
    first, second = _shot_map(before), _shot_map(after)
    return sorted(shot_id for shot_id in set(first) | set(second) if first.get(shot_id) != second.get(shot_id))


def analyze(before: str, after: str, target_shot: str | None = None, scope: str = "shot") -> dict:
    if scope not in SCOPES:
        raise ValueError("scope must be " + ", ".join(SCOPES))
    changed = changed_shots(before, after)
    global_changed = _non_shot_content(before) != _non_shot_content(after)
    allowed: set[str] = set()
    if target_shot:
        allowed.add(target_shot)
        if scope == "pair":
            scene = target_shot.rsplit("-", 1)[0]
            number = int(target_shot.rsplit("-", 1)[1])
            allowed.update({f"{scene}-{number - 1}", f"{scene}-{number + 1}"})
        elif scope == "window":
            scene = target_shot.rsplit("-", 1)[0]
            number = int(target_shot.rsplit("-", 1)[1])
            allowed.update(f"{scene}-{index}" for index in range(max(1, number - 2), number + 3))
    outside = sorted(set(changed) - allowed) if target_shot and scope != "scene" else []
    issues: list[str] = []
    if target_shot and not changed:
        issues.append(f"{target_shot}: no shot change detected")
    if outside:
        issues.append("changed shots exceed declared " + scope + " scope: " + ",".join(outside))
    if global_changed and scope != "scene":
        issues.append("global or group-level content changed without declared scene scope")
    if not target_shot and scope != "scene":
        issues.append("target_shot is required for field/shot/pair/window scope")
    return {
        "pass": not issues,
        "mode": "repair-scope",
        "declared_scope": scope,
        "target_shot": target_shot or "",
        "changed_shots": changed,
        "changed_shot_count": len(changed),
        "global_or_group_changed": global_changed,
        "issues": issues,
        "primary_output_modified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("--target-shot")
    parser.add_argument("--scope", choices=SCOPES, default="shot")
    parser.add_argument("--report")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)
    if not args.compact or not args.report:
        parser.error("legacy repair-scope output is disabled; --compact and --report are required")
    try:
        result = analyze(
            Path(args.before).expanduser().resolve().read_text(encoding="utf-8-sig"),
            Path(args.after).expanduser().resolve().read_text(encoding="utf-8-sig"),
            args.target_shot,
            args.scope,
        )
    except (OSError, ValueError) as exc:
        result = {"pass": False, "mode": "repair-scope", "error": str(exc), "primary_output_modified": False}
    if args.report:
        report = Path(args.report).expanduser().resolve()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.compact:
        print(json.dumps({
            "status": "PASS" if result.get("pass") else "FAIL",
            "scope": result.get("declared_scope"),
            "target_shot": result.get("target_shot"),
            "changed_shot_count": result.get("changed_shot_count", 0),
            "global_or_group_changed": result.get("global_or_group_changed", False),
            "issues": result.get("issues", []),
            "report": str(Path(args.report).expanduser().resolve()) if args.report else None,
        }, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
