#!/usr/bin/env python3
"""Record and promote reviewed blocking-reference artifacts without creative edits."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from render_blocking_reference import BLOCKING_GATE_VERSION


SCHEMA_VERSION = 2


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record_review(render_report: str, decision: str, findings: list[str]) -> dict:
    report_path = Path(render_report).expanduser().resolve()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    if not payload.get("pass"):
        raise ValueError("cannot record visual PASS for a failed geometry render")
    if payload.get("blocking_gate_version") != BLOCKING_GATE_VERSION:
        raise ValueError("render report uses a stale blocking gate; rerender with the current renderer before review")
    artifacts = []
    for key in ("output_path", "png_path"):
        raw = payload.get(key)
        if not raw:
            continue
        path = Path(raw).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(str(path))
        artifacts.append({"path": str(path), "sha256": sha256_file(path)})
    if not artifacts:
        raise ValueError("render report has no SVG/PNG artifacts")
    return {
        "schema_version": SCHEMA_VERSION,
        "blocking_gate_version": BLOCKING_GATE_VERSION,
        "reference_role": "jimeng_2d_spatial_reference",
        "generation_reference_allowed": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "shot_group": payload.get("shot_group"),
        "geometry_review": "PASS",
        "visual_review": decision,
        "findings": findings,
        "artifacts": artifacts,
        "promotion_allowed": decision == "PASS",
        "primary_storyboard_modified": False,
    }


def promote(review_path: str, delivery_dir: str, replace: bool = False) -> dict:
    review = json.loads(Path(review_path).expanduser().resolve().read_text(encoding="utf-8"))
    if review.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("2D spatial review uses a stale schema; rerun record before promotion")
    if review.get("blocking_gate_version") != BLOCKING_GATE_VERSION:
        raise ValueError("visual review uses a stale blocking gate; rerender and review again before promotion")
    if review.get("visual_review") != "PASS" or not review.get("promotion_allowed"):
        raise ValueError("promotion requires geometry PASS and visual_review PASS")
    if review.get("reference_role") != "jimeng_2d_spatial_reference" or review.get("generation_reference_allowed") is not True:
        raise ValueError("2D blocking artifacts must be explicitly reviewed as Jimeng spatial references before promotion")
    destination_dir = Path(delivery_dir).expanduser().resolve()
    if "staging" in destination_dir.parts:
        raise ValueError("delivery directory cannot be inside staging")
    destination_dir.mkdir(parents=True, exist_ok=True)
    promoted = []
    for item in review.get("artifacts", []):
        if Path(item["path"]).suffix.lower() != ".png":
            continue
        source = Path(item["path"]).expanduser().resolve()
        if sha256_file(source) != item.get("sha256"):
            raise ValueError(f"review artifact changed after visual approval: {source}")
        destination = destination_dir / source.name
        if destination.exists() and not replace:
            raise FileExistsError(f"destination exists; use --replace: {destination}")
        shutil.copy2(source, destination)
        promoted.append({"path": str(destination), "sha256": sha256_file(destination)})
    if not promoted:
        raise ValueError("2D Jimeng promotion requires a reviewed PNG artifact")
    return {
        "pass": True,
        "schema_version": SCHEMA_VERSION,
        "shot_group": review.get("shot_group"),
        "promoted": promoted,
        "visual_review": "PASS",
        "reference_role": "jimeng_2d_spatial_reference",
        "generation_reference_allowed": True,
        "primary_storyboard_modified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    record = sub.add_parser("record")
    record.add_argument("--render-report", required=True)
    record.add_argument("--decision", choices=("PASS", "REVISE"), required=True)
    record.add_argument("--finding", action="append", default=[])
    record.add_argument("--review", required=True)
    promote_parser = sub.add_parser("promote")
    promote_parser.add_argument("--review", required=True)
    promote_parser.add_argument("--delivery-dir", required=True)
    promote_parser.add_argument("--replace", action="store_true")
    for command in (record, promote_parser):
        command.add_argument("--compact", action="store_true")
        command.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    if not args.compact:
        parser.error("--compact is required")
    try:
        if args.command == "record":
            result = record_review(args.render_report, args.decision, args.finding)
            result["pass"] = True
            Path(args.review).expanduser().resolve().write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        else:
            result = promote(args.review, args.delivery_dir, args.replace)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"pass": False, "error": str(exc), "primary_storyboard_modified": False}
    report = Path(args.report).expanduser().resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS" if result.get("pass") else "FAIL",
        "shot_group": result.get("shot_group"),
        "promotion_count": len(result.get("promoted", [])),
        "report": str(report),
    }, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
