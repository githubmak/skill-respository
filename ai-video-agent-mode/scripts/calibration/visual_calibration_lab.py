#!/usr/bin/env python3
"""Offline, evidence-backed visual A/B calibration for real rendered videos.

This module is deliberately detached from the production pipeline. It is run
manually after real before/after videos exist and never changes prompt policy.
"""

import argparse
import datetime as _datetime
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import tempfile


PROTOCOL_VERSION = "visual-calibration-v1"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
SCORE_FIELDS = (
    "light_color_quality",
    "material_realism",
    "motion_liveness",
    "character_physics",
    "prompt_fidelity",
    "composition_depth",
    "artifact_control",
    "continuity",
)
CRITICAL_FIELDS = (
    "character_physics",
    "artifact_control",
    "continuity",
    "prompt_fidelity",
)
OBJECTIVE_COMPARE_FIELDS = (
    "luminance_mean",
    "luminance_drift",
    "highlight_clipping_mean",
    "highlight_clipping_max",
    "shadow_crush_mean",
    "shadow_crush_max",
    "red_blue_balance_mean",
    "red_blue_balance_drift",
    "detail_energy_mean",
    "detail_energy_flicker",
    "frame_delta_mean",
    "frame_delta_std",
    "frame_delta_max",
    "horizontal_edge_proxy_position_drift",
)
PROMOTION_THRESHOLDS = {
    "min_cases": 4,
    "min_scene_types": 2,
    "min_generation_fingerprints": 2,
    "min_after_win_rate": 0.65,
    "min_target_mean_delta": 0.5,
    "max_critical_mean_regression": -0.25,
    "max_severe_objective_flags": 0,
}


class CalibrationError(ValueError):
    """Raised when calibration evidence is incomplete or inconsistent."""


def prepare_case(
    before_video,
    after_video,
    before_prompt,
    after_prompt,
    strategy_spec,
    out_dir,
    case_id,
    strategy_id,
    scene_type,
    generation_fingerprint,
    target_dimensions,
):
    """Create a neutral review packet and a separate integrity mapping."""
    source_paths = {
        "before_video": _required_file(before_video, "before_video"),
        "after_video": _required_file(after_video, "after_video"),
        "before_prompt": _required_file(before_prompt, "before_prompt"),
        "after_prompt": _required_file(after_prompt, "after_prompt"),
        "strategy_spec": _required_file(strategy_spec, "strategy_spec"),
    }
    for key in ("before_video", "after_video"):
        if os.path.splitext(source_paths[key])[1].lower() not in VIDEO_EXTENSIONS:
            raise CalibrationError("%s扩展名不受支持" % key)
    if source_paths["before_video"] == source_paths["after_video"]:
        raise CalibrationError("before_video与after_video不能是同一个文件")
    text_values = {
        "case_id": case_id,
        "strategy_id": strategy_id,
        "scene_type": scene_type,
        "generation_fingerprint": generation_fingerprint,
    }
    for key, value in text_values.items():
        if not str(value or "").strip():
            raise CalibrationError("%s不能为空" % key)
        text_values[key] = str(value).strip()
    targets = _validate_targets(target_dimensions)
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    review_path = os.path.join(out_dir, "blind_review.json")
    sealed_path = os.path.join(out_dir, "sealed_mapping.json")
    if os.path.exists(review_path) or os.path.exists(sealed_path):
        raise CalibrationError("输出目录已有校准清单；请使用新的case目录")

    labels = ["a", "b"]
    if secrets.randbelow(2):
        labels.reverse()
    generation_by_label = {labels[0]: "before", labels[1]: "after"}
    neutral_paths = {}
    created = []
    try:
        for label in ("a", "b"):
            generation = generation_by_label[label]
            extension = os.path.splitext(source_paths[generation + "_video"])[1].lower()
            target = os.path.join(out_dir, "candidate_%s%s" % (label, extension))
            if os.path.exists(target):
                raise CalibrationError("中性候选文件已存在：%s" % target)
            _copy_atomic(source_paths[generation + "_video"], target)
            neutral_paths[label] = target
            created.append(target)

        media = {}
        for label in ("a", "b"):
            generation = generation_by_label[label]
            media[label] = {
                "neutral_path": neutral_paths[label],
                "neutral_sha256": _sha256_file(neutral_paths[label]),
                "source_path": source_paths[generation + "_video"],
                "source_sha256": _sha256_file(source_paths[generation + "_video"]),
                "generation": generation,
            }
        sealed_payload = {
            "protocol_version": PROTOCOL_VERSION,
            "case_id": text_values["case_id"],
            "strategy_id": text_values["strategy_id"],
            "strategy_spec_path": source_paths["strategy_spec"],
            "strategy_spec_sha256": _sha256_file(source_paths["strategy_spec"]),
            "scene_type": text_values["scene_type"],
            "generation_fingerprint": text_values["generation_fingerprint"],
            "target_dimensions": targets,
            "created_utc": _utc_now(),
            "mapping": generation_by_label,
            "media": media,
            "prompts": {
                "before": {
                    "path": source_paths["before_prompt"],
                    "sha256": _sha256_file(source_paths["before_prompt"]),
                },
                "after": {
                    "path": source_paths["after_prompt"],
                    "sha256": _sha256_file(source_paths["after_prompt"]),
                },
            },
        }
        sealed = dict(sealed_payload)
        sealed["integrity_sha256"] = _canonical_sha256(sealed_payload)
        review = {
            "protocol_version": PROTOCOL_VERSION,
            "case_id": text_values["case_id"],
            "blind_confirmed": False,
            "reviewer_id": "",
            "video_a": os.path.basename(neutral_paths["a"]),
            "video_b": os.path.basename(neutral_paths["b"]),
            "scores": {
                label: {field: None for field in SCORE_FIELDS}
                for label in ("a", "b")
            },
            "winner": None,
            "notes": "",
        }
        _write_json_atomic(sealed_path, sealed)
        created.append(sealed_path)
        _write_json_atomic(review_path, review)
        created.append(review_path)
    except Exception:
        for path in reversed(created):
            if os.path.isfile(path):
                os.unlink(path)
        raise
    return {"blind_review": review_path, "sealed_mapping": sealed_path}


def finalize_case(review_path, sealed_path, out_path, analyzer=None, sample_count=18):
    """Validate sealed evidence, run metrics, and reveal before/after in a report."""
    review_path = _required_file(review_path, "review")
    sealed_path = _required_file(sealed_path, "sealed_mapping")
    review = _read_json(review_path)
    sealed = _read_json(sealed_path)
    issues = _validate_review_and_seal(review, sealed, os.path.dirname(review_path))
    if issues:
        raise CalibrationError("；".join(issues))

    neutral_paths = [sealed["media"][label]["neutral_path"] for label in ("a", "b")]
    analyzer = analyzer or _run_swift_analyzer
    objective_rows = analyzer(neutral_paths, sample_count)
    if not isinstance(objective_rows, list) or len(objective_rows) != 2:
        raise CalibrationError("客观分析器必须返回两个视频的指标")
    metrics_by_path = {}
    for row in objective_rows:
        if not isinstance(row, dict) or not isinstance(row.get("metrics"), dict):
            raise CalibrationError("客观分析器返回格式错误")
        metrics_by_path[os.path.abspath(str(row.get("path", "")))] = row["metrics"]
    label_metrics = {}
    for label in ("a", "b"):
        path = os.path.abspath(sealed["media"][label]["neutral_path"])
        if path not in metrics_by_path:
            raise CalibrationError("客观分析器缺少%s候选指标" % label.upper())
        label_metrics[label] = metrics_by_path[path]

    mapping = sealed["mapping"]
    label_for = {generation: label for label, generation in mapping.items()}
    scores = review["scores"]
    before_scores = scores[label_for["before"]]
    after_scores = scores[label_for["after"]]
    subjective_deltas = {
        field: round(after_scores[field] - before_scores[field], 4)
        for field in SCORE_FIELDS
    }
    before_metrics = label_metrics[label_for["before"]]
    after_metrics = label_metrics[label_for["after"]]
    objective_deltas = _numeric_deltas(before_metrics, after_metrics)
    risk_flags = _objective_risk_flags(before_metrics, after_metrics)
    winner_generation = (
        "tie" if review["winner"] == "tie" else mapping[review["winner"]]
    )
    report = {
        "protocol_version": PROTOCOL_VERSION,
        "status": "complete",
        "case": {
            "case_id": sealed["case_id"],
            "strategy_id": sealed["strategy_id"],
            "strategy_spec_sha256": sealed["strategy_spec_sha256"],
            "scene_type": sealed["scene_type"],
            "generation_fingerprint": sealed["generation_fingerprint"],
            "target_dimensions": sealed["target_dimensions"],
        },
        "evidence": {
            "reviewer_id": review["reviewer_id"],
            "blind_confirmed": True,
            "sealed_mapping_integrity_sha256": sealed["integrity_sha256"],
            "prompt_before_sha256": sealed["prompts"]["before"]["sha256"],
            "prompt_after_sha256": sealed["prompts"]["after"]["sha256"],
            "video_before_sha256": sealed["media"][label_for["before"]]["source_sha256"],
            "video_after_sha256": sealed["media"][label_for["after"]]["source_sha256"],
            "winner_label": review["winner"],
            "winner_generation": winner_generation,
        },
        "subjective": {
            "before": before_scores,
            "after": after_scores,
            "deltas": subjective_deltas,
        },
        "objective": {
            "before": before_metrics,
            "after": after_metrics,
            "deltas": objective_deltas,
            "risk_flags": risk_flags,
            "limitations": [
                "客观指标只诊断亮度、裁切、色偏、细节和帧间变化，不替代审美盲评",
                "horizontal_edge_proxy不是地平线或人物姿态识别",
                "frame_delta变化不能单独证明灵动性提升或下降",
            ],
        },
        "finalized_utc": _utc_now(),
    }
    report["integrity_sha256"] = _canonical_sha256(report)
    _write_json_atomic(os.path.abspath(out_path), report)
    return report


def promote_reports(report_paths, out_path, strategy_id=None):
    """Aggregate real reports into a non-production validation registry."""
    reports = []
    seen_cases = set()
    for path in report_paths:
        report = _read_json(_required_file(path, "report"))
        if report.get("protocol_version") != PROTOCOL_VERSION or report.get("status") != "complete":
            raise CalibrationError("报告不是已完成的%s证据" % PROTOCOL_VERSION)
        report_digest = report.get("integrity_sha256")
        report_payload = {key: value for key, value in report.items() if key != "integrity_sha256"}
        if report_digest != _canonical_sha256(report_payload):
            raise CalibrationError("报告完整性摘要不匹配：%s" % path)
        case = report.get("case", {})
        case_id = str(case.get("case_id", ""))
        if not case_id or case_id in seen_cases:
            raise CalibrationError("报告case_id缺失或重复：%s" % case_id)
        seen_cases.add(case_id)
        if strategy_id and case.get("strategy_id") != strategy_id:
            continue
        reports.append(report)
    if not reports:
        raise CalibrationError("没有可聚合的报告")

    groups = {}
    for report in reports:
        groups.setdefault(report["case"]["strategy_id"], []).append(report)
    validated = []
    rejected = []
    for current_strategy, rows in sorted(groups.items()):
        evaluation = _evaluate_strategy(current_strategy, rows)
        if evaluation["status"] == "validated":
            validated.append(evaluation)
        else:
            rejected.append(evaluation)
    registry = {
        "protocol_version": PROTOCOL_VERSION,
        "registry_scope": "offline_evidence_only",
        "auto_consumed_by_production": False,
        "generated_utc": _utc_now(),
        "thresholds": PROMOTION_THRESHOLDS,
        "validated_strategies": validated,
        "rejected_candidates": rejected,
    }
    _write_json_atomic(os.path.abspath(out_path), registry)
    return registry


def _evaluate_strategy(strategy_id, reports):
    reasons = []
    case_count = len(reports)
    scene_types = {row["case"]["scene_type"] for row in reports}
    fingerprints = {row["case"]["generation_fingerprint"] for row in reports}
    spec_hashes = {row["case"]["strategy_spec_sha256"] for row in reports}
    after_wins = sum(row["evidence"]["winner_generation"] == "after" for row in reports)
    after_win_rate = after_wins / case_count if case_count else 0.0
    targets = sorted({
        field
        for row in reports
        for field in row["case"].get("target_dimensions", [])
    })
    target_means = {
        field: _mean([
            row["subjective"]["deltas"][field]
            for row in reports
            if field in row["case"].get("target_dimensions", [])
        ])
        for field in targets
    }
    critical_means = {
        field: _mean([row["subjective"]["deltas"][field] for row in reports])
        for field in CRITICAL_FIELDS
    }
    severe_flags = sum(
        flag.get("severity") == "severe"
        for row in reports
        for flag in row.get("objective", {}).get("risk_flags", [])
        if isinstance(flag, dict)
    )

    t = PROMOTION_THRESHOLDS
    if case_count < t["min_cases"]:
        reasons.append("有效案例少于%d" % t["min_cases"])
    if len(scene_types) < t["min_scene_types"]:
        reasons.append("场景类型少于%d" % t["min_scene_types"])
    if len(fingerprints) < t["min_generation_fingerprints"]:
        reasons.append("生成参数/seed指纹少于%d" % t["min_generation_fingerprints"])
    if len(spec_hashes) != 1:
        reasons.append("同一strategy_id绑定了不同策略规格版本")
    if after_win_rate < t["min_after_win_rate"]:
        reasons.append("after胜率低于%.2f" % t["min_after_win_rate"])
    for field, value in target_means.items():
        if value < t["min_target_mean_delta"]:
            reasons.append("目标维度%s平均提升低于%.2f" % (field, t["min_target_mean_delta"]))
    for field, value in critical_means.items():
        if value < t["max_critical_mean_regression"]:
            reasons.append("关键维度%s平均回退超过%.2f" % (field, abs(t["max_critical_mean_regression"])))
    if severe_flags > t["max_severe_objective_flags"]:
        reasons.append("存在%d个严重客观退化标记" % severe_flags)
    return {
        "strategy_id": strategy_id,
        "strategy_spec_sha256": next(iter(spec_hashes)) if len(spec_hashes) == 1 else None,
        "status": "validated" if not reasons else "insufficient_evidence",
        "case_count": case_count,
        "scene_type_count": len(scene_types),
        "generation_fingerprint_count": len(fingerprints),
        "after_win_rate": round(after_win_rate, 4),
        "target_dimension_mean_deltas": target_means,
        "critical_dimension_mean_deltas": critical_means,
        "severe_objective_flag_count": severe_flags,
        "case_ids": [row["case"]["case_id"] for row in reports],
        "reasons": reasons,
    }


def _validate_review_and_seal(review, sealed, review_dir):
    issues = []
    if not isinstance(review, dict) or review.get("protocol_version") != PROTOCOL_VERSION:
        issues.append("blind_review协议版本错误")
        return issues
    if not isinstance(sealed, dict) or sealed.get("protocol_version") != PROTOCOL_VERSION:
        issues.append("sealed_mapping协议版本错误")
        return issues
    forbidden = {"mapping", "sealed_mapping", "before", "after"} & set(review)
    if forbidden:
        issues.append("盲评文件泄漏映射字段：%s" % ",".join(sorted(forbidden)))
    if review.get("case_id") != sealed.get("case_id"):
        issues.append("case_id不一致")
    if review.get("blind_confirmed") is not True:
        issues.append("blind_confirmed必须在评分完成后设为true")
    if not str(review.get("reviewer_id", "")).strip():
        issues.append("reviewer_id不能为空")
    if review.get("winner") not in {"a", "b", "tie"}:
        issues.append("winner只允许a/b/tie")
    scores = review.get("scores")
    for label in ("a", "b"):
        row = scores.get(label) if isinstance(scores, dict) else None
        for field in SCORE_FIELDS:
            value = row.get(field) if isinstance(row, dict) else None
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 1 <= value <= 10:
                issues.append("scores.%s.%s必须是1-10分" % (label, field))
    mapping = sealed.get("mapping", {})
    if not isinstance(mapping, dict) or {mapping.get("a"), mapping.get("b")} != {"before", "after"}:
        issues.append("封存映射必须是before/after一一映射")
    integrity = sealed.get("integrity_sha256")
    payload = {key: value for key, value in sealed.items() if key != "integrity_sha256"}
    if integrity != _canonical_sha256(payload):
        issues.append("sealed_mapping完整性摘要不匹配")
    for key in ("strategy_id", "strategy_spec_sha256", "scene_type", "generation_fingerprint"):
        if not sealed.get(key):
            issues.append("sealed_mapping.%s缺失" % key)
    try:
        _validate_targets(sealed.get("target_dimensions"))
    except CalibrationError as exc:
        issues.append(str(exc))
    expected_names = {}
    for label in ("a", "b"):
        media = sealed.get("media", {}).get(label, {}) if isinstance(sealed.get("media"), dict) else {}
        neutral = os.path.abspath(str(media.get("neutral_path", "")))
        source = os.path.abspath(str(media.get("source_path", "")))
        expected_names[label] = os.path.basename(neutral)
        _check_evidence_file(issues, "candidate_%s" % label, neutral, media.get("neutral_sha256"))
        _check_evidence_file(issues, "%s_source_video" % label, source, media.get("source_sha256"))
        if os.path.isfile(neutral) and os.path.isfile(source):
            if _sha256_file(neutral) != _sha256_file(source):
                issues.append("candidate_%s与封存源视频内容不一致" % label)
    for label in ("a", "b"):
        review_video = os.path.abspath(os.path.join(review_dir, str(review.get("video_" + label, ""))))
        sealed_video = os.path.abspath(str(sealed.get("media", {}).get(label, {}).get("neutral_path", "")))
        if review_video != sealed_video or os.path.basename(review_video) != expected_names.get(label):
            issues.append("video_%s未指向封存的中性候选" % label)
    for generation in ("before", "after"):
        prompt = sealed.get("prompts", {}).get(generation, {}) if isinstance(sealed.get("prompts"), dict) else {}
        _check_evidence_file(issues, generation + "_prompt", prompt.get("path"), prompt.get("sha256"))
    _check_evidence_file(
        issues,
        "strategy_spec",
        sealed.get("strategy_spec_path"),
        sealed.get("strategy_spec_sha256"),
    )
    return issues


def _check_evidence_file(issues, label, path, expected_sha):
    path = os.path.abspath(str(path or ""))
    if not os.path.isfile(path) or os.path.getsize(path) <= 0:
        issues.append("%s证据文件缺失或为空" % label)
    elif not _is_sha256(expected_sha) or _sha256_file(path) != expected_sha:
        issues.append("%s证据SHA256不匹配" % label)


def _run_swift_analyzer(paths, sample_count):
    script = os.path.join(os.path.dirname(__file__), "visual_metrics.swift")
    command = ["/usr/bin/swift", script, "--samples", str(sample_count)] + list(paths)
    proc = subprocess.run(command, text=True, capture_output=True)
    if proc.returncode != 0:
        raise CalibrationError("视频指标分析失败：%s" % (proc.stderr.strip() or proc.stdout.strip()))
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise CalibrationError("视频指标分析器未返回有效JSON") from exc
    if payload.get("pass") is not True:
        raise CalibrationError("视频指标分析失败：%s" % payload.get("errors"))
    return payload.get("videos", [])


def _objective_risk_flags(before, after):
    flags = []
    rules = (
        ("highlight_clipping_mean", 0.03, 0.08, "高光裁切增加"),
        ("shadow_crush_mean", 0.03, 0.10, "暗部压死增加"),
        ("luminance_drift", 0.04, 0.08, "亮度漂移增加"),
        ("red_blue_balance_drift", 0.04, 0.08, "红蓝平衡漂移增加"),
        ("detail_energy_flicker", 0.03, 0.07, "细节能量闪烁增加"),
        ("horizontal_edge_proxy_position_drift", 0.04, 0.08, "水平强边缘位置漂移增加"),
    )
    for field, increase, severe_after, message in rules:
        b = before.get(field)
        a = after.get(field)
        if _number(b) and _number(a) and a - b > increase:
            flags.append({
                "metric": field,
                "severity": "severe" if a >= severe_after else "warning",
                "before": b,
                "after": a,
                "message": message,
            })
    return flags


def _numeric_deltas(before, after):
    result = {}
    for field in OBJECTIVE_COMPARE_FIELDS:
        b = before.get(field)
        a = after.get(field)
        if _number(b) and _number(a):
            result[field] = round(a - b, 6)
    return result


def _validate_targets(values):
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple)) or not values:
        raise CalibrationError("target_dimensions至少需要一个目标维度")
    targets = []
    for value in values:
        field = str(value or "").strip()
        if field not in SCORE_FIELDS:
            raise CalibrationError("未知目标维度：%s" % field)
        if field not in targets:
            targets.append(field)
    return targets


def _required_file(path, label):
    path = os.path.abspath(str(path or ""))
    if not os.path.isfile(path) or os.path.getsize(path) <= 0:
        raise CalibrationError("%s必须指向真实非空文件" % label)
    return path


def _copy_atomic(source, target):
    parent = os.path.dirname(target)
    fd, temp_path = tempfile.mkstemp(prefix=".candidate-", dir=parent)
    os.close(fd)
    try:
        shutil.copyfile(source, temp_path)
        os.replace(temp_path, target)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def _write_json_atomic(path, payload):
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".json-", dir=parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def _read_json(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise CalibrationError("JSON根节点必须是对象：%s" % path)
    return payload


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(payload):
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_sha256(value):
    text = str(value or "").lower()
    return len(text) == 64 and all(char in "0123456789abcdef" for char in text)


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _mean(values):
    values = list(values)
    return round(sum(values) / len(values), 4) if values else 0.0


def _utc_now():
    return _datetime.datetime.now(_datetime.timezone.utc).replace(microsecond=0).isoformat()


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="创建中性A/B盲评包与独立封存映射")
    prepare.add_argument("--before-video", required=True)
    prepare.add_argument("--after-video", required=True)
    prepare.add_argument("--before-prompt", required=True)
    prepare.add_argument("--after-prompt", required=True)
    prepare.add_argument("--strategy-spec", required=True)
    prepare.add_argument("--out-dir", required=True)
    prepare.add_argument("--case-id", required=True)
    prepare.add_argument("--strategy-id", required=True)
    prepare.add_argument("--scene-type", required=True)
    prepare.add_argument("--generation-fingerprint", required=True)
    prepare.add_argument("--target-dimension", action="append", required=True)
    finalize = sub.add_parser("finalize", help="验证盲评并计算真实视频客观诊断")
    finalize.add_argument("--review", required=True)
    finalize.add_argument("--sealed", required=True)
    finalize.add_argument("--out", required=True)
    finalize.add_argument("--samples", type=int, default=18)
    promote = sub.add_parser("promote", help="聚合报告并生成离线策略证据注册表")
    promote.add_argument("--report", action="append", required=True)
    promote.add_argument("--out", required=True)
    promote.add_argument("--strategy-id")
    return parser


def main():
    args = _parser().parse_args()
    try:
        if args.command == "prepare":
            result = prepare_case(
                args.before_video,
                args.after_video,
                args.before_prompt,
                args.after_prompt,
                args.strategy_spec,
                args.out_dir,
                args.case_id,
                args.strategy_id,
                args.scene_type,
                args.generation_fingerprint,
                args.target_dimension,
            )
        elif args.command == "finalize":
            if not 4 <= args.samples <= 120:
                raise CalibrationError("samples必须在4-120之间")
            result = finalize_case(args.review, args.sealed, args.out, sample_count=args.samples)
        else:
            result = promote_reports(args.report, args.out, args.strategy_id)
    except (CalibrationError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"pass": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    print(json.dumps({"pass": True, "result": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
