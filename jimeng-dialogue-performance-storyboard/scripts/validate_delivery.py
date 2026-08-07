#!/usr/bin/env python3
"""Validate deterministic delivery facts for Seedance storyboards.

This validator intentionally does not judge narrative, performance, camera,
focus, lighting, palette, or prompt quality. Those require model review.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import re
from pathlib import Path

from review_manifest import verify_manifest
from source_gate import _dialogue_match


TARGETS = {"auto", "2.0", "2.5", "both"}
SHOT_HEADING_RE = re.compile(r"^####\s+(S\d+-\d+)｜([^\n]+)\s*$", re.M)
FIELD_RE = re.compile(r"^【([^】]+)】\s*$", re.M)
TARGET_RE = re.compile(r"^-\s*Seedance\s*目标：\s*(auto|2\.0|2\.5)\s*$", re.M)
SOURCE_HASH_RE = re.compile(r"^-\s*源文\s*SHA-256：\s*([0-9a-fA-F]{64})\s*$", re.M)
STATUS_RE = re.compile(r"^-\s*交付状态：\s*(DRAFT|PROVISIONAL|FINAL)\s*$", re.M)
DURATION_RE = re.compile(r"^(\d+(?:\.\d+)?)s$", re.I)
PROMPT_LABELS = (
    "起始画面：", "表演时序：", "摄影机：", "焦点：", "色卡：", "影调：", "光影：", "声音：", "结束画面：",
)
ASSET_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov"}
ENGINEERING_REFERENCE_DIRS = {"approved-lineart", "approved-blocking", "blocking-geometry"}
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
PLAIN_ASSET_RE = re.compile(r"(?<![\w/])([^\s，。；;]+\.(?:png|jpg|jpeg|webp|mp4|mov|svg))", re.I)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_audio_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line and _dialogue_match(line) is not None:
            lines.append(line)
    return lines


def _fields(block: str) -> dict[str, str]:
    matches = list(FIELD_RE.finditer(block))
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
        name = match.group(1).strip()
        if name in result:
            raise ValueError(f"duplicate field: 【{name}】")
        result[name] = block[start:end].strip()
    return result


def _audio_field_lines(value: str) -> list[str]:
    if not value or value.strip() == "无":
        return []
    return [line.strip() for line in value.splitlines() if line.strip() and line.strip() != "无"]


def _asset_paths(value: str, storyboard: Path) -> list[Path]:
    if not value or value.strip() == "无":
        return []
    raw_paths = MARKDOWN_LINK_RE.findall(value)
    if not raw_paths:
        raw_paths = [match.group(1) for match in PLAIN_ASSET_RE.finditer(value)]
    paths: list[Path] = []
    for raw in raw_paths:
        cleaned = raw.strip().strip("<>")
        candidate = Path(cleaned).expanduser()
        if not candidate.is_absolute():
            candidate = storyboard.parent / candidate
        paths.append(candidate.resolve())
    return paths


def _issue(code: str, message: str, file: Path | None = None, shot_id: str = "") -> dict:
    item = {"code": code, "message": message}
    if file:
        item["file"] = str(file)
    if shot_id:
        item["shot_id"] = shot_id
    return item


def inspect_storyboard(path: Path, expected_source_hash: str) -> dict:
    issues: list[dict] = []
    advisories: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        return {
            "path": str(path), "target": "", "status": "", "shots": [], "audio_lines": [],
            "assets": [], "issues": [_issue("STORYBOARD_READ", str(exc), path)], "advisories": [],
        }
    target_match = TARGET_RE.search(text)
    status_match = STATUS_RE.search(text)
    hash_match = SOURCE_HASH_RE.search(text)
    target = target_match.group(1) if target_match else ""
    status = status_match.group(1) if status_match else ""
    if not target:
        issues.append(_issue("TARGET_MARKER", "missing or invalid Seedance target marker", path))
    if not status:
        issues.append(_issue("DELIVERY_STATUS", "missing or invalid delivery status", path))
    if not hash_match:
        issues.append(_issue("SOURCE_HASH", "missing source SHA-256 marker", path))
    elif hash_match.group(1).lower() != expected_source_hash:
        issues.append(_issue("SOURCE_HASH", "source SHA-256 marker does not match source bytes", path))

    headings = list(SHOT_HEADING_RE.finditer(text))
    if not headings:
        issues.append(_issue("SHOT_MISSING", "no valid shot heading found", path))
    shots: list[dict] = []
    audio_lines: list[str] = []
    assets: list[str] = []
    seen_ids: set[str] = set()
    for index, heading in enumerate(headings):
        shot_id = heading.group(1)
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        block = text[heading.end():end]
        if shot_id in seen_ids:
            issues.append(_issue("SHOT_DUPLICATE", f"duplicate shot id {shot_id}", path, shot_id))
        seen_ids.add(shot_id)
        try:
            fields = _fields(block)
        except ValueError as exc:
            issues.append(_issue("FIELD_DUPLICATE", str(exc), path, shot_id))
            fields = {}
        required = ("时长", "出现人物", "Seedance 直投提示", "声音原文", "审核后参考素材")
        for name in required:
            if name not in fields or not fields[name].strip():
                issues.append(_issue("FIELD_MISSING", f"{shot_id} missing 【{name}】", path, shot_id))

        duration = None
        duration_text = fields.get("时长", "").strip()
        duration_match = DURATION_RE.fullmatch(duration_text)
        if not duration_match:
            issues.append(_issue("DURATION_FORMAT", f"{shot_id} duration must be a single value such as 8s", path, shot_id))
        else:
            duration = float(duration_match.group(1))
            if duration <= 0 or duration > 15:
                issues.append(_issue("DURATION_RANGE", f"{shot_id} duration {duration:g}s must be >0 and <=15s", path, shot_id))

        prompt = fields.get("Seedance 直投提示", "")
        for label in PROMPT_LABELS:
            if label not in prompt:
                issues.append(_issue("PROMPT_SCHEMA", f"{shot_id} missing prompt clause {label}", path, shot_id))
        prompt_length = len(re.sub(r"\s+", "", prompt))
        if prompt_length > 700:
            issues.append(_issue("PROMPT_HARD_LIMIT", f"{shot_id} prompt has {prompt_length} non-space characters; hard limit is 700", path, shot_id))

        shot_audio = _audio_field_lines(fields.get("声音原文", ""))
        audio_lines.extend(shot_audio)
        for source_line in shot_audio:
            spoken_body = source_line.split("：", 1)[-1].strip()
            if spoken_body and spoken_body not in prompt:
                issues.append(_issue(
                    "AUDIO_NOT_IN_PROMPT",
                    f"{shot_id} source audio text is absent from the copy-ready Seedance prompt: {source_line}",
                    path, shot_id,
                ))
        spoken_chars = sum(len(re.sub(r"[^\w\u4e00-\u9fff]", "", line.split("：", 1)[-1])) for line in shot_audio)
        estimated_floor = spoken_chars / 4.5 if spoken_chars else 0.0

        for asset in _asset_paths(fields.get("审核后参考素材", ""), path):
            assets.append(str(asset))
            if asset.suffix.lower() == ".svg":
                issues.append(_issue("REFERENCE_ROLE", f"{shot_id} SVG blocking diagrams cannot occupy the Seedance reference field", path, shot_id))
            engineering_dirs = sorted({part for part in asset.parts if part.lower() in ENGINEERING_REFERENCE_DIRS})
            if engineering_dirs:
                issues.append(_issue(
                    "REFERENCE_ROLE",
                    f"{shot_id} engineering geometry reference cannot occupy the Seedance reference field: {engineering_dirs[0]}",
                    path, shot_id,
                ))
            if ".audit." in asset.name.lower() or asset.suffix.lower() == ".html":
                issues.append(_issue("REFERENCE_ROLE", f"{shot_id} mannequin audit/runtime assets cannot occupy the Seedance reference field", path, shot_id))
            if any(part.lower() in {"staging", ".staging"} for part in asset.parts):
                issues.append(_issue("STAGING_REFERENCE", f"{shot_id} references an asset inside staging: {asset}", path, shot_id))
            if asset.suffix.lower() not in ASSET_EXTENSIONS:
                issues.append(_issue("REFERENCE_TYPE", f"{shot_id} unsupported Seedance reference type: {asset.suffix}", path, shot_id))
            if not asset.is_file():
                issues.append(_issue("REFERENCE_MISSING", f"{shot_id} referenced asset does not exist: {asset}", path, shot_id))

        shots.append({
            "shot_id": shot_id,
            "duration": duration,
            "prompt_characters": prompt_length,
            "spoken_characters": spoken_chars,
            "speech_floor_seconds_at_4_5_chars_per_second": round(estimated_floor, 2),
            "audio_lines": shot_audio,
        })
    return {
        "path": str(path), "target": target, "status": status, "shots": shots,
        "audio_lines": audio_lines, "assets": assets, "issues": issues, "advisories": advisories,
    }


def _audio_comparison(expected: list[str], actual: list[str], label: str) -> list[dict]:
    if actual == expected:
        return []
    issues: list[dict] = []
    expected_count, actual_count = Counter(expected), Counter(actual)
    missing = list((expected_count - actual_count).elements())
    extra = list((actual_count - expected_count).elements())
    if missing:
        issues.append(_issue("AUDIO_MISSING", f"{label} missing source audio lines: {missing}"))
    if extra:
        issues.append(_issue("AUDIO_EXTRA", f"{label} contains changed, duplicated, or non-source audio lines: {extra}"))
    if not missing and not extra:
        issues.append(_issue("AUDIO_ORDER", f"{label} source audio lines are not in source order"))
    return issues


def validate_delivery(
    source: Path,
    storyboards: list[Path],
    seedance_target: str,
    final: bool = False,
    review_manifest: Path | None = None,
) -> dict:
    issues: list[dict] = []
    advisories: list[dict] = []
    if not source.is_file():
        return {"pass": False, "issues": [_issue("SOURCE_MISSING", f"source does not exist: {source}")], "advisories": []}
    try:
        source_text = source.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        return {"pass": False, "issues": [_issue("SOURCE_READ", str(exc), source)], "advisories": []}
    source_hash = sha256_file(source)
    expected_audio = source_audio_lines(source_text)
    records = [inspect_storyboard(path.resolve(), source_hash) for path in storyboards]
    for record in records:
        issues.extend(record["issues"])
        advisories.extend(record["advisories"])

    targets = {record["target"] for record in records if record["target"]}
    if seedance_target == "both":
        if targets != {"2.0", "2.5"}:
            issues.append(_issue("TARGET_SET", f"both requires 2.0 and 2.5 outputs; found {sorted(targets)}"))
        signatures: dict[str, list[tuple[str, float | None]]] = {}
        for target in ("2.0", "2.5"):
            target_records = [record for record in records if record["target"] == target]
            actual_audio = [line for record in target_records for line in record["audio_lines"]]
            issues.extend(_audio_comparison(expected_audio, actual_audio, f"Seedance {target}"))
            signatures[target] = [
                (shot["shot_id"], shot["duration"])
                for record in target_records for shot in record["shots"]
            ]
        if signatures.get("2.0") != signatures.get("2.5"):
            issues.append(_issue("VERSION_DRIFT", "2.0 and 2.5 shot IDs or durations differ"))
    else:
        if targets and targets != {seedance_target}:
            issues.append(_issue("TARGET_MISMATCH", f"expected target {seedance_target}; found {sorted(targets)}"))
        actual_audio = [line for record in records for line in record["audio_lines"]]
        issues.extend(_audio_comparison(expected_audio, actual_audio, f"Seedance {seedance_target}"))

    all_shot_ids = [shot["shot_id"] for record in records for shot in record["shots"]]
    if seedance_target != "both" and len(all_shot_ids) != len(set(all_shot_ids)):
        issues.append(_issue("SHOT_DUPLICATE_BUNDLE", "shot IDs must be unique across storyboard files"))

    manifest_result = None
    if final:
        if review_manifest is None:
            issues.append(_issue("MANIFEST_REQUIRED", "--final requires --review-manifest"))
        else:
            try:
                manifest_result = verify_manifest(review_manifest)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                issues.append(_issue("MANIFEST_READ", str(exc), review_manifest))
            else:
                if not manifest_result.get("pass"):
                    issues.append(_issue("MANIFEST_STALE", "review manifest is missing files or hashes no longer match", review_manifest))
                if manifest_result.get("delivery_status") != "FINAL":
                    issues.append(_issue("REVIEW_INCOMPLETE", "FINAL requires design_review=PASS and visual_review=PASS", review_manifest))
                manifest_payload = json.loads(review_manifest.read_text(encoding="utf-8"))
                registered = {Path(item.get("path", "")).expanduser().resolve() for item in manifest_payload.get("outputs", [])}
                required_files = {path.resolve() for path in storyboards}
                required_files.update(Path(asset).resolve() for record in records for asset in record["assets"])
                missing_registered = sorted(str(path) for path in required_files - registered)
                if missing_registered:
                    issues.append(_issue("MANIFEST_OUTPUTS", f"manifest does not register required outputs: {missing_registered}", review_manifest))
        for record in records:
            if record["status"] != "FINAL":
                issues.append(_issue("FINAL_MARKER", f"{record['path']} must declare 交付状态：FINAL"))

    return {
        "pass": not issues,
        "mode": "final" if final else "draft",
        "source": str(source.resolve()),
        "source_sha256": source_hash,
        "source_audio_line_count": len(expected_audio),
        "storyboard_count": len(records),
        "shot_count": sum(len(record["shots"]) for record in records),
        "targets": sorted(targets),
        "issues": issues,
        "advisories": advisories,
        "files": records,
        "manifest": manifest_result,
        "creative_decisions_evaluated": False,
        "primary_output_modified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--storyboard", action="append", required=True)
    parser.add_argument("--seedance-target", choices=tuple(sorted(TARGETS)), default="auto")
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--review-manifest")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    if not args.compact or not args.report:
        parser.error("--compact and --report are required")
    result = validate_delivery(
        Path(args.source).expanduser().resolve(),
        [Path(item).expanduser().resolve() for item in args.storyboard],
        args.seedance_target,
        args.final,
        Path(args.review_manifest).expanduser().resolve() if args.review_manifest else None,
    )
    report = Path(args.report).expanduser().resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS" if result.get("pass") else "FAIL",
        "mode": result.get("mode"),
        "storyboard_count": result.get("storyboard_count", 0),
        "shot_count": result.get("shot_count", 0),
        "issue_count": len(result.get("issues", [])),
        "advisory_count": len(result.get("advisories", [])),
        "report": str(report),
    }, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
