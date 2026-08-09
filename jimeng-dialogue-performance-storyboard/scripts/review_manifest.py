#!/usr/bin/env python3
"""Create and verify byte-bound review attestations for storyboard deliverables."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


SCHEMA_VERSION = 3
DESIGN_STATES = ("PASS", "REVISE")
VISUAL_STATES = ("PASS", "REVISE", "NOT_APPLICABLE", "NOT_RUN")
REVIEW_MODES = ("independent", "self_check")
DELIVERY_EXTENSIONS = {".md", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".xlsx"}
NON_DELIVERY_DIRECTORIES = {"reports", "staging", ".staging"}
VISUAL_EXTENSIONS = {".svg", ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov"}
VIDEO_EXTENSIONS = {".mp4", ".mov"}


def delivery_status(design_review: str, visual_review: str) -> str:
    """Visual review is required only when visual evidence is part of delivery."""
    visual_complete = visual_review in {"PASS", "NOT_APPLICABLE"}
    return "FINAL" if design_review == "PASS" and visual_complete else "PROVISIONAL"


def evidence_scope(visual_review: str, visual_outputs: list[Path]) -> str:
    if visual_review == "PASS" and any(path.suffix.lower() in VIDEO_EXTENSIONS for path in visual_outputs):
        return "RENDER_REVIEWED"
    if visual_review == "PASS":
        return "REFERENCE_REVIEWED"
    if visual_review == "NOT_APPLICABLE":
        return "TEXT_ONLY"
    return "INCOMPLETE"


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


def _within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _delivery_inventory(root: Path) -> set[Path]:
    inventory = set()
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in DELIVERY_EXTENSIONS:
            continue
        relative = path.relative_to(root)
        if any(part in NON_DELIVERY_DIRECTORIES for part in relative.parts[:-1]):
            continue
        inventory.add(path.resolve())
    return inventory


def build_manifest(
    source: str | Path,
    outputs: list[str | Path],
    review_reports: list[str | Path],
    review_mode: str,
    design_review: str,
    visual_review: str,
    reviewer_context_id: str = "",
    independent: bool | None = None,
    delivery_root: str | Path | None = None,
) -> dict:
    if review_mode not in REVIEW_MODES:
        raise ValueError("review_mode must be independent or self_check")
    if design_review not in DESIGN_STATES:
        raise ValueError("design_review must be PASS or REVISE")
    if visual_review not in VISUAL_STATES:
        raise ValueError("visual_review must be PASS, REVISE, NOT_APPLICABLE, or NOT_RUN")
    expected_independent = review_mode == "independent"
    if independent is not None and independent != expected_independent:
        raise ValueError("review_mode and independent flag conflict")
    if expected_independent and not reviewer_context_id.strip():
        raise ValueError("independent review requires reviewer_context_id")
    if not outputs:
        raise ValueError("at least one output is required")
    if not review_reports:
        raise ValueError("at least one review report is required")
    resolved_outputs = [Path(path).expanduser().resolve() for path in outputs]
    resolved_review_reports = [Path(path).expanduser().resolve() for path in review_reports]
    if set(resolved_outputs) & set(resolved_review_reports):
        raise ValueError("review reports must be separate from formal outputs")
    visual_outputs = [path for path in resolved_outputs if path.suffix.lower() in VISUAL_EXTENSIONS]
    if visual_review == "NOT_APPLICABLE" and visual_outputs:
        raise ValueError("visual_review=NOT_APPLICABLE is invalid when visual outputs are registered")
    if visual_review == "PASS" and not visual_outputs:
        raise ValueError("visual_review=PASS requires at least one registered visual output; use NOT_APPLICABLE for text-only delivery")
    resolved_root = Path(delivery_root).expanduser().resolve() if delivery_root else None
    if resolved_root and any(not _within(path, resolved_root) for path in resolved_outputs):
        raise ValueError("all outputs must be inside delivery_root")
    if resolved_root and any(not _within(path, resolved_root) for path in resolved_review_reports):
        raise ValueError("all review reports must be inside delivery_root")
    if resolved_root:
        for path in resolved_outputs:
            relative = path.relative_to(resolved_root)
            if relative.parts and relative.parts[0] in NON_DELIVERY_DIRECTORIES:
                raise ValueError("reviewed outputs must be promoted out of staging/reports before delivery manifest creation")
        for path in resolved_review_reports:
            relative = path.relative_to(resolved_root)
            if not relative.parts or relative.parts[0] != "reports":
                raise ValueError("review reports must be stored under delivery_root/reports")
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "review_attestation",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": _file_record(source),
        "outputs": [_file_record(path) for path in resolved_outputs],
        "review_reports": [_file_record(path) for path in resolved_review_reports],
        "delivery_root": str(resolved_root) if resolved_root else "",
        "inventory_policy": "all deliverable files outside reports/staging are registered; review reports are hash-bound separately",
        "review": {
            "mode": review_mode,
            "independent": expected_independent,
            "reviewer_context_id": reviewer_context_id.strip(),
            "design_review": design_review,
            "visual_review": visual_review,
            "visual_evidence_count": len(visual_outputs),
        },
        "delivery_status": delivery_status(design_review, visual_review),
        "evidence_scope": evidence_scope(visual_review, visual_outputs),
        "limitations": [
            "This record attests declared review results; it does not prove review quality or reviewer independence.",
            "SHA-256 verifies reviewed bytes, not reviewer identity or context freshness.",
            "Any source, output, or review-report byte change makes the recorded review stale.",
            "TEXT_ONLY means prompt and design review completed without a reviewed Seedance render.",
            "REFERENCE_REVIEWED means visual references were reviewed but no delivered video render was verified.",
        ],
        "primary_output_modified": False,
    }


def write_manifest(path: str | Path, payload: dict) -> Path:
    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination


def verify_manifest(path: str | Path, delivery_root: str | Path | None = None) -> dict:
    manifest_path = Path(path).expanduser().resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    changed: list[dict] = []
    raw_root = delivery_root or payload.get("delivery_root", "")
    resolved_root = Path(raw_root).expanduser().resolve() if raw_root else None
    records = [("source", payload.get("source", {}))]
    records.extend(("output", item) for item in payload.get("outputs", []))
    records.extend(("review_report", item) for item in payload.get("review_reports", []))
    if payload.get("schema_version", 0) < SCHEMA_VERSION:
        changed.append({"kind": "manifest", "path": str(manifest_path), "reason": "legacy_schema_without_review_report_binding"})
    if not payload.get("review_reports"):
        changed.append({"kind": "review_report", "path": "", "reason": "missing_review_report_binding"})
    for kind, record in records:
        target = Path(record.get("path", ""))
        if kind in {"output", "review_report"} and resolved_root and not _within(target.resolve(), resolved_root):
            changed.append({"kind": kind, "path": str(target), "reason": "outside_delivery_root"})
            continue
        if kind == "review_report" and resolved_root:
            relative = target.resolve().relative_to(resolved_root)
            if not relative.parts or relative.parts[0] != "reports":
                changed.append({"kind": kind, "path": str(target), "reason": "outside_reports_directory"})
                continue
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
    if resolved_root and resolved_root.is_dir():
        registered = {
            Path(item.get("path", "")).expanduser().resolve()
            for item in payload.get("outputs", [])
        }
        source_path = Path(payload.get("source", {}).get("path", "")).expanduser().resolve()
        for extra in sorted(_delivery_inventory(resolved_root) - registered - {source_path}):
            changed.append({"kind": "output", "path": str(extra), "reason": "unregistered_delivery_file"})
    status = "stale" if changed else "current"
    return {
        "pass": not changed,
        "status": status,
        "manifest_path": str(manifest_path),
        "changed": changed,
        "recorded_review": payload.get("review", {}),
        "delivery_root": str(resolved_root) if resolved_root else "",
        "effective_review_status": "STALE" if changed else "CURRENT",
        "delivery_status": "STALE" if changed else payload.get("delivery_status", "PROVISIONAL"),
        "evidence_scope": payload.get("evidence_scope", "INCOMPLETE"),
        "freshness_proof": "byte_hash_only",
        "primary_output_modified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--source", required=True)
    create.add_argument("--output", action="append", required=True)
    create.add_argument("--review-report", action="append", required=True)
    create.add_argument("--manifest", required=True)
    create.add_argument("--review-mode", choices=REVIEW_MODES, required=True)
    create.add_argument("--reviewer-context-id", default="")
    create.add_argument("--design-review", choices=DESIGN_STATES, required=True)
    create.add_argument("--visual-review", choices=VISUAL_STATES, required=True)
    create.add_argument("--delivery-root")
    create.add_argument("--compact", action="store_true")
    create.add_argument("--report")
    verify = subparsers.add_parser("verify")
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--delivery-root")
    verify.add_argument("--compact", action="store_true")
    verify.add_argument("--report")
    args = parser.parse_args(argv)
    if not getattr(args, "compact", False) or not getattr(args, "report", None):
        parser.error("legacy manifest output is disabled; --compact and --report are required")
    if args.command == "create" and not args.delivery_root:
        parser.error("create requires --delivery-root so the manifest binds the actual delivery directory")

    try:
        if args.command == "create":
            payload = build_manifest(
                args.source,
                args.output,
                args.review_report,
                args.review_mode,
                args.design_review,
                args.visual_review,
                args.reviewer_context_id,
                delivery_root=args.delivery_root,
            )
            destination = write_manifest(args.manifest, payload)
            result = {"pass": True, "status": "current", "manifest_path": str(destination), **payload}
        else:
            result = verify_manifest(args.manifest, args.delivery_root)
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"pass": False, "status": "error", "error": str(exc), "primary_output_modified": False}
    report_path = getattr(args, "report", None)
    if report_path:
        destination = Path(report_path).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if getattr(args, "compact", False):
        print(json.dumps({
            "status": "PASS" if result.get("pass") else "FAIL",
            "manifest_path": result.get("manifest_path"),
            "delivery_status": result.get("delivery_status"),
            "evidence_scope": result.get("evidence_scope", "INCOMPLETE"),
            "changed_count": len(result.get("changed", [])),
            "delivery_root": result.get("delivery_root", ""),
            "report": str(Path(report_path).expanduser().resolve()) if report_path else None,
        }, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
