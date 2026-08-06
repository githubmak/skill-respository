#!/usr/bin/env python3
"""Dry-run a model-authored blocking repair without changing creative facts or files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from render_blocking_reference import render_svg


def _evaluate(path: str) -> dict:
    source = Path(path).expanduser().resolve()
    try:
        payload = json.loads(source.read_text(encoding="utf-8-sig"))
        render_svg(payload)
        return {"path": str(source), "valid": True, "error": ""}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"path": str(source), "valid": False, "error": str(exc)}


def assess(previous: str, candidate: str) -> dict:
    before = _evaluate(previous)
    after = _evaluate(candidate)
    if not after["valid"]:
        decision = "REJECT_CANDIDATE"
        reason = "candidate violates schema, geometry, coverage, boundary clearance, or label layout"
    elif before["valid"]:
        decision = "VALID_NO_ENGINEERING_FAILURE_TO_REPAIR"
        reason = "both versions are engineering-valid; creative preference remains a model decision"
    else:
        decision = "ACCEPT_ENGINEERING_REPAIR"
        reason = "candidate resolves the previous deterministic engineering failure"
    return {
        "pass": after["valid"],
        "previous": before,
        "candidate": after,
        "decision": decision,
        "reason": reason,
        "creative_decision_made": False,
        "files_modified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("previous")
    parser.add_argument("candidate")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    if not args.compact:
        parser.error("--compact is required")
    result = assess(args.previous, args.candidate)
    report = Path(args.report).expanduser().resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS" if result["pass"] else "FAIL",
        "decision": result["decision"],
        "report": str(report),
    }, ensure_ascii=False, separators=(",", ":")))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
