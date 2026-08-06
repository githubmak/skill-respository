#!/usr/bin/env python3
"""Compile executable prompt clauses from a validated scene contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scene_contract import compile_contract, load_contract


def compact_report(result: dict) -> dict:
    """Keep the persisted compiler handoff small; recovery can rebuild field maps."""
    if not result.get("shots"):
        return result
    shots = []
    design_only_fields = result["shots"][0]["design_only_fields"] if result["shots"] else []
    for shot in result["shots"]:
        required_field_ids = []
        for phase in ("prefix", "body", "terminal"):
            for clause in shot["clauses"][phase]:
                required_field_ids.extend(clause["field_ids"])
        shots.append({
            "shot_id": shot["shot_id"],
            "prefix": shot["prefix"],
            "body": shot["body"],
            "terminal": shot["terminal"],
            "character_count": shot["character_count"],
            "prompt_limit": shot["prompt_limit"],
            "reserved_for_scene_dialogue": shot["reserved_for_scene_dialogue"],
            "required_field_ids": required_field_ids,
            "issues": shot["issues"],
        })
    return {
        **result,
        "shots": shots,
        "artifact_role": "non_feed_engineering_ledger",
        "feed_ready": False,
        "creative_decisions_modified": False,
        "design_only_fields": design_only_fields,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract")
    parser.add_argument("--shot-id", required=True)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    if not args.compact or not args.report:
        parser.error("contract compilation requires --compact and --report")
    try:
        result = compact_report(compile_contract(load_contract(args.contract), args.shot_id))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"pass": False, "error": str(exc), "primary_storyboard_modified": False}
    report = Path(args.report).expanduser().resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS" if result.get("pass") else "FAIL",
        "scene_id": result.get("scene_id"),
        "shot_count": result.get("shot_count", 0),
        "issue_count": len(result.get("issues", [])),
        "report": str(report),
    }, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
