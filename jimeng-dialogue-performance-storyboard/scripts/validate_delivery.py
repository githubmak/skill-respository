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
DEFAULT_MAX_SHOT_DURATION = 15.0
SHOT_HEADING_RE = re.compile(r"^####\s+(S\d+-\d+)｜([^\n]+)\s*$", re.M)
FIELD_RE = re.compile(r"^【([^】]+)】\s*$", re.M)
TARGET_RE = re.compile(r"^-\s*Seedance\s*目标：\s*(2\.0|2\.5)\s*$", re.M)
SOURCE_HASH_RE = re.compile(r"^-\s*源文\s*SHA-256：\s*([0-9a-fA-F]{64})\s*$", re.M)
STATUS_RE = re.compile(r"^-\s*交付状态：\s*(DRAFT|PROVISIONAL|FINAL)\s*$", re.M)
DURATION_RE = re.compile(r"^(\d+(?:\.\d+)?)s$", re.I)
CORE_PROMPT_LABELS = ("主体与起态", "动作时间线", "台词", "视觉控制", "稳定结尾")
OPTIONAL_PROMPT_LABELS = ("摄影机", "焦点", "声音设计")
PROMPT_LABEL_ORDER = ("主体与起态", "动作时间线", "台词", "摄影机", "焦点", "视觉控制", "声音设计", "稳定结尾")
FORBIDDEN_INTERNAL_REFERENCES = ("VC-S", "同上镜", "同前", "继承前镜", "继承上一镜", "沿用上一镜", "沿用前镜")
FORBIDDEN_DELIVERY_TERMS = (
    "内部视觉连续性笔记",
    "视觉连续性笔记",
    "视觉连续性基线",
    "事实连续性台账（非投喂）",
    "角色表演弧（非投喂）",
    "场景视觉控制（非投喂）",
)
AMBIGUOUS_BLOCKING_RE = re.compile(
    r"(?<!画面)(?<!最终画面)(?<!摄影机)(?<!门洞)(?<!门框)(?<!厨房)(?<!灶台)(?<!土灶)(?:侧后|深景|稍后|后方门槛|前方门槛)(?!方)"
)
UNBOUND_SUBJECT_RE = re.compile(
    r"(?<![\u4e00-\u9fff])(?:父亲|母亲|孩子|她|他|对方|男人|女人|老人|少女|少年|妻子|丈夫)"
)
EMBEDDED_SUBJECT_RE = re.compile(
    r"(?:随后|此时|接着|然后|之后|说完后|听见后|停稳后)(她|他|对方|父亲|母亲|孩子)"
    r"|(?:看向|递给|交给|靠近|面对|越过|绕过|跟随|转向)(她|他|对方)"
)
PROMPT_CLAUSE_RE = re.compile(
    rf"^(?P<label>{'|'.join((*CORE_PROMPT_LABELS, *OPTIONAL_PROMPT_LABELS))})：(?P<inline>.*)$",
    re.M,
)
SCENE_PLAN_RE = re.compile(r"^###\s+(S\d+)｜[^\n]+$", re.M)
ASSET_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov"}
ENGINEERING_REFERENCE_DIRS = {"approved-lineart", "approved-blocking", "blocking-geometry"}
FORBIDDEN_3D_REFERENCE_DIRS = {"approved-mannequin", "mannequin"}
FORBIDDEN_3D_FILENAME_MARKERS = ("_即梦_3d_空间关系",)
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


def _prompt_clauses(prompt: str) -> dict[str, str]:
    matches = list(PROMPT_CLAUSE_RE.finditer(prompt))
    clauses: dict[str, str] = {}
    for index, match in enumerate(matches):
        label = match.group("label")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(prompt)
        value = (match.group("inline") + prompt[match.end():end]).strip()
        if label in clauses:
            raise ValueError(f"duplicate prompt clause: {label}")
        clauses[label] = value
    return clauses


def _blocking_ambiguities(clause: str) -> list[str]:
    """Find bare blocking shorthand that lacks a named spatial reference."""
    return sorted({match.group(0) for match in AMBIGUOUS_BLOCKING_RE.finditer(clause)})


def _visible_names(value: str) -> set[str]:
    """Extract simple named-person tokens from the visible-person field."""
    if not value or value.strip() in {"无", "无人"}:
        return set()
    names: set[str] = set()
    for token in re.split(r"[,，、;；\n\s]+", value):
        cleaned = re.sub(r"[（(].*?[）)]", "", token).strip()
        if cleaned and cleaned not in {"无", "无人"}:
            names.add(cleaned)
    return names


def _unbound_subjects(prompt_clauses: dict[str, str], visible_names: set[str]) -> list[str]:
    """Find role labels/pronouns used as action subjects outside source audio."""
    terms: set[str] = set()
    for label in ("主体与起态", "动作时间线", "摄影机", "焦点", "视觉控制", "声音设计", "稳定结尾"):
        clause = prompt_clauses.get(label, "")
        if not clause:
            continue
        clause = re.sub(r"（[^）]*）|\([^)]*\)", "", clause)
        for match in UNBOUND_SUBJECT_RE.finditer(clause):
            term = match.group(0)
            if term not in visible_names:
                terms.add(term)
    return sorted(terms)


def _embedded_subject_advisories(prompt_clauses: dict[str, str], visible_names: set[str]) -> list[str]:
    """Flag potentially ambiguous embedded pronouns without blocking delivery."""
    terms: set[str] = set()
    for label in ("主体与起态", "动作时间线", "摄影机", "焦点", "声音设计", "稳定结尾"):
        clause = prompt_clauses.get(label, "")
        if not clause:
            continue
        clause = re.sub(r"（[^）]*）|\([^)]*\)", "", clause)
        for match in EMBEDDED_SUBJECT_RE.finditer(clause):
            term = match.group(1) or match.group(2)
            if term and term not in visible_names:
                terms.add(match.group(0))
    return sorted(terms)


def _shot_key(shot_id: str) -> tuple[int, int]:
    scene, shot = shot_id[1:].split("-", 1)
    return int(scene), int(shot)


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


def inspect_storyboard(path: Path, expected_source_hash: str, max_shot_duration: float = DEFAULT_MAX_SHOT_DURATION) -> dict:
    issues: list[dict] = []
    advisories: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        return {
            "path": str(path), "target": "", "status": "", "shots": [], "audio_lines": [],
            "assets": [], "issues": [_issue("STORYBOARD_READ", str(exc), path)], "advisories": [],
        }
    leaked_terms = [term for term in FORBIDDEN_DELIVERY_TERMS if term in text]
    if leaked_terms:
        issues.append(_issue(
            "INTERNAL_NOTE_LEAK",
            f"formal storyboard contains internal-only term(s): {leaked_terms}; move them to the review report",
            path,
        ))
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

    scene_plans = list(SCENE_PLAN_RE.finditer(text))
    if not scene_plans:
        issues.append(_issue("SCENE_PLAN", "no scene director plan found", path))
    scene_plan_ids = {match.group(1) for match in scene_plans}

    headings = list(SHOT_HEADING_RE.finditer(text))
    if not headings:
        issues.append(_issue("SHOT_MISSING", "no valid shot heading found", path))
    heading_ids = [heading.group(1) for heading in headings]
    heading_keys = [_shot_key(shot_id) for shot_id in heading_ids]
    last_shot_by_scene: dict[int, int] = {}
    out_of_order_shots: list[str] = []
    for shot_id, (scene_number, shot_number) in zip(heading_ids, heading_keys):
        previous = last_shot_by_scene.get(scene_number)
        if previous is not None and shot_number <= previous:
            out_of_order_shots.append(shot_id)
        last_shot_by_scene[scene_number] = shot_number
    if out_of_order_shots:
        issues.append(_issue(
            "SHOT_ORDER",
            f"shot numbers must increase within each scene; cross-scene intercutting remains allowed: {out_of_order_shots}",
            path,
        ))
    missing_scene_plans = sorted({shot_id.split("-", 1)[0] for shot_id in heading_ids} - scene_plan_ids)
    if missing_scene_plans:
        issues.append(_issue(
            "SHOT_SCENE_PLAN",
            f"shot scene IDs have no matching scene director plan: {missing_scene_plans}",
            path,
        ))
    shots_by_scene: dict[int, list[int]] = {}
    for scene_number, shot_number in heading_keys:
        shots_by_scene.setdefault(scene_number, []).append(shot_number)
    for scene_number, shot_numbers in shots_by_scene.items():
        ordered_numbers = sorted(set(shot_numbers))
        gaps = [
            f"S{scene_number}-{previous + 1:02d}..S{scene_number}-{current - 1:02d}"
            for previous, current in zip(ordered_numbers, ordered_numbers[1:])
            if current - previous > 1
        ]
        if gaps:
            advisories.append(_issue(
                "SHOT_GAP",
                f"shot numbering contains internal gap(s): {gaps}; confirm intentional multi-file or editorial omission",
                path,
            ))
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
        required = ("时长", "出现人物", "Seedance 直投提示", "审核后参考素材")
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
            if duration <= 0 or duration > max_shot_duration:
                issues.append(_issue(
                    "DURATION_RANGE",
                    f"{shot_id} duration {duration:g}s must be >0 and <={max_shot_duration:g}s",
                    path,
                    shot_id,
                ))

        prompt = fields.get("Seedance 直投提示", "")
        try:
            prompt_clauses = _prompt_clauses(prompt)
        except ValueError as exc:
            issues.append(_issue("PROMPT_SCHEMA", f"{shot_id} {exc}", path, shot_id))
            prompt_clauses = {}
        for label in CORE_PROMPT_LABELS:
            if not prompt_clauses.get(label, "").strip():
                issues.append(_issue("PROMPT_SCHEMA", f"{shot_id} missing core prompt clause {label}：", path, shot_id))
        actual_prompt_order = list(prompt_clauses)
        prompt_ranks = [PROMPT_LABEL_ORDER.index(label) for label in actual_prompt_order]
        if prompt_ranks != sorted(prompt_ranks):
            issues.append(_issue(
                "PROMPT_ORDER",
                f"{shot_id} prompt clauses are out of order: {actual_prompt_order}",
                path,
                shot_id,
            ))
        for spatial_label in ("主体与起态", "摄影机"):
            ambiguous_blocking = _blocking_ambiguities(prompt_clauses.get(spatial_label, ""))
            if ambiguous_blocking:
                issues.append(_issue(
                    "PROMPT_SPATIAL_AMBIGUITY",
                    f"{shot_id} {spatial_label} contains unreferenced blocking shorthand: {ambiguous_blocking}; name the reference person/anchor and final screen position",
                    path,
                    shot_id,
                ))
        forbidden = [term for term in FORBIDDEN_INTERNAL_REFERENCES if term in prompt]
        if forbidden:
            issues.append(_issue(
                "PROMPT_INTERNAL_REFERENCE",
                f"{shot_id} direct prompt contains internal continuity reference(s): {forbidden}; expand them into visible natural language",
                path,
                shot_id,
            ))

        shot_audio = _audio_field_lines(prompt_clauses.get("台词", ""))
        audio_lines.extend(shot_audio)
        unbound_subjects = _unbound_subjects(prompt_clauses, _visible_names(fields.get("出现人物", "")))
        if unbound_subjects:
            issues.append(_issue(
                "PROMPT_UNBOUND_SUBJECT",
                f"{shot_id} direct prompt uses unbound role/pronoun subject(s): {unbound_subjects}; use a named visible character outside source dialogue",
                path,
                shot_id,
            ))
        embedded_subjects = _embedded_subject_advisories(
            prompt_clauses,
            _visible_names(fields.get("出现人物", "")),
        )
        if embedded_subjects:
            advisories.append(_issue(
                "PROMPT_SUBJECT_ADVISORY",
                f"{shot_id} contains potentially ambiguous embedded reference(s): {embedded_subjects}; revise only when the referent is not unique",
                path,
                shot_id,
            ))

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
            legacy_3d_dirs = sorted({part for part in asset.parts if part.lower() in FORBIDDEN_3D_REFERENCE_DIRS})
            legacy_3d_name = any(marker in asset.name.lower() for marker in FORBIDDEN_3D_FILENAME_MARKERS)
            if legacy_3d_dirs or legacy_3d_name:
                issues.append(_issue(
                    "REFERENCE_ROLE",
                    f"{shot_id} legacy 3D mannequin references are not supported; use an approved-jimeng-2d PNG, reviewed keyframe, or reviewed video",
                    path, shot_id,
                ))
            if ".audit." in asset.name.lower() or asset.name.endswith(("_审核.jpg", "_审核.jpeg", "_审核.png", "_审核.webp")) or asset.suffix.lower() == ".html":
                issues.append(_issue("REFERENCE_ROLE", f"{shot_id} audit/runtime assets cannot occupy the Seedance reference field", path, shot_id))
            if any(part.lower() in {"staging", ".staging"} for part in asset.parts):
                issues.append(_issue("STAGING_REFERENCE", f"{shot_id} references an asset inside staging: {asset}", path, shot_id))
            if asset.suffix.lower() not in ASSET_EXTENSIONS:
                issues.append(_issue("REFERENCE_TYPE", f"{shot_id} unsupported Seedance reference type: {asset.suffix}", path, shot_id))
            if not asset.is_file():
                issues.append(_issue("REFERENCE_MISSING", f"{shot_id} referenced asset does not exist: {asset}", path, shot_id))

        shots.append({
            "shot_id": shot_id,
            "duration": duration,
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
    max_shot_duration: float = DEFAULT_MAX_SHOT_DURATION,
    allow_target_duration_drift: bool = False,
) -> dict:
    issues: list[dict] = []
    advisories: list[dict] = []
    if max_shot_duration <= 0:
        return {
            "pass": False,
            "issues": [_issue("DURATION_LIMIT", "max shot duration must be greater than zero")],
            "advisories": [],
        }
    if not source.is_file():
        return {"pass": False, "issues": [_issue("SOURCE_MISSING", f"source does not exist: {source}")], "advisories": []}
    try:
        source_text = source.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        return {"pass": False, "issues": [_issue("SOURCE_READ", str(exc), source)], "advisories": []}
    source_hash = sha256_file(source)
    expected_audio = source_audio_lines(source_text)
    records = [inspect_storyboard(path.resolve(), source_hash, max_shot_duration) for path in storyboards]
    for record in records:
        issues.extend(record["issues"])
        advisories.extend(record["advisories"])

    targets = {record["target"] for record in records if record["target"]}
    resolved_target = "2.0" if seedance_target == "auto" else seedance_target
    if resolved_target == "both":
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
        ids_20 = [shot_id for shot_id, _ in signatures.get("2.0", [])]
        ids_25 = [shot_id for shot_id, _ in signatures.get("2.5", [])]
        if ids_20 != ids_25:
            issues.append(_issue("VERSION_DRIFT", "2.0 and 2.5 shot IDs differ"))
        else:
            durations_20 = [duration for _, duration in signatures.get("2.0", [])]
            durations_25 = [duration for _, duration in signatures.get("2.5", [])]
            if durations_20 != durations_25:
                if allow_target_duration_drift:
                    advisories.append(_issue(
                        "TARGET_DURATION_DRIFT",
                        "2.0 and 2.5 durations differ under an explicit platform-evidence override; record the evidence in the review report",
                    ))
                else:
                    issues.append(_issue(
                        "VERSION_DRIFT",
                        "2.0 and 2.5 durations differ; pass --allow-target-duration-drift only when confirmed target-interface evidence requires it",
                    ))
    else:
        if targets and targets != {resolved_target}:
            issues.append(_issue("TARGET_MISMATCH", f"expected target {resolved_target}; found {sorted(targets)}"))
        actual_audio = [line for record in records for line in record["audio_lines"]]
        issues.extend(_audio_comparison(expected_audio, actual_audio, f"Seedance {resolved_target}"))

    all_shot_ids = [shot["shot_id"] for record in records for shot in record["shots"]]
    if resolved_target != "both" and len(all_shot_ids) != len(set(all_shot_ids)):
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
                    issues.append(_issue("REVIEW_INCOMPLETE", "FINAL requires design PASS and visual PASS or NOT_APPLICABLE", review_manifest))
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
        "requested_seedance_target": seedance_target,
        "resolved_seedance_target": resolved_target,
        "max_shot_duration": max_shot_duration,
        "allow_target_duration_drift": allow_target_duration_drift,
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
    parser.add_argument("--max-shot-duration", type=float, default=DEFAULT_MAX_SHOT_DURATION)
    parser.add_argument("--allow-target-duration-drift", action="store_true")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    if not args.compact or not args.report:
        parser.error("--compact and --report are required")
    if args.max_shot_duration <= 0:
        parser.error("--max-shot-duration must be greater than zero")
    result = validate_delivery(
        Path(args.source).expanduser().resolve(),
        [Path(item).expanduser().resolve() for item in args.storyboard],
        args.seedance_target,
        args.final,
        Path(args.review_manifest).expanduser().resolve() if args.review_manifest else None,
        args.max_shot_duration,
        args.allow_target_duration_drift,
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
