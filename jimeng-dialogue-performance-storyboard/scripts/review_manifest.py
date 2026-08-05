#!/usr/bin/env python3
"""Create and verify non-feed review manifests for storyboard deliverables."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


SCHEMA_VERSION = 1
DESIGN_STATES = ("PASS", "REVISE")
VISUAL_STATES = ("PASS", "REVISE", "NOT_RUN")
REVIEW_MODES = ("independent", "self_check")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_record(path: str | Path) -> dict:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(str(resolved))
    return {"path": str(resolved), "sha256": sha256_file(resolved)}


def build_manifest(
    source: str | Path,
    outputs: list[str | Path],
    review_mode: str,
    design_review: str,
    visual_review: str,
    reviewer_context_id: str = "",
    independent: bool | None = None,
) -> dict:
    if review_mode not in REVIEW_MODES:
        raise ValueError("review_mode must be independent or self_check")
    if design_review not in DESIGN_STATES:
        raise ValueError("design_review must be PASS or REVISE")
    if visual_review not in VISUAL_STATES:
        raise ValueError("visual_review must be PASS, REVISE, or NOT_RUN")
    expected_independent = review_mode == "independent"
    if independent is not None and independent != expected_independent:
        raise ValueError("review_mode and independent flag conflict")
    if expected_independent and not reviewer_context_id.strip():
        raise ValueError("independent review requires reviewer_context_id")
    if not outputs:
        raise ValueError("at least one output is required")
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": _file_record(source),
        "outputs": [_file_record(path) for path in outputs],
        "review": {
            "mode": review_mode,
            "independent": expected_independent,
            "reviewer_context_id": reviewer_context_id.strip(),
            "design_review": design_review,
            "visual_review": visual_review,
        },
        "limitations": [
            "SHA-256 verifies reviewed bytes, not reviewer identity or context freshness.",
            "Any source or output byte change makes the recorded review stale.",
        ],
        "primary_output_modified": False,
    }


def write_manifest(path: str | Path, payload: dict) -> Path:
    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination


def verify_manifest(path: str | Path) -> dict:
    manifest_path = Path(path).expanduser().resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    changed: list[dict] = []
    records = [("source", payload.get("source", {}))]
    records.extend(("output", item) for item in payload.get("outputs", []))
    for kind, record in records:
        target = Path(record.get("path", ""))
        if not target.is_file():
            changed.append({"kind": kind, "path": str(target), "reason": "missing"})
            continue
        actual = sha256_file(target)
        if actual != record.get("sha256"):
            changed.append({
                "kind": kind,
                "path": str(target),
                "reason": "sha256_changed",
                "expected_sha256": record.get("sha256", ""),
                "actual_sha256": actual,
            })
    status = "stale" if changed else "current"
    return {
        "pass": not changed,
        "status": status,
        "manifest_path": str(manifest_path),
        "changed": changed,
        "recorded_review": payload.get("review", {}),
        "effective_review_status": "STALE" if changed else "CURRENT",
        "freshness_proof": "byte_hash_only",
        "primary_output_modified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--source", required=True)
    create.add_argument("--output", action="append", required=True)
    create.add_argument("--manifest", required=True)
    create.add_argument("--review-mode", choices=REVIEW_MODES, required=True)
    create.add_argument("--reviewer-context-id", default="")
    create.add_argument("--design-review", choices=DESIGN_STATES, required=True)
    create.add_argument("--visual-review", choices=VISUAL_STATES, required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--manifest", required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "create":
            payload = build_manifest(
                args.source,
                args.output,
                args.review_mode,
                args.design_review,
                args.visual_review,
                args.reviewer_context_id,
            )
            destination = write_manifest(args.manifest, payload)
            result = {"pass": True, "status": "current", "manifest_path": str(destination), **payload}
        else:
            result = verify_manifest(args.manifest)
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"pass": False, "status": "error", "error": str(exc), "primary_output_modified": False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
