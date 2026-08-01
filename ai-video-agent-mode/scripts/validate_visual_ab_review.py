#!/usr/bin/env python3
"""Validate evidence-backed blind A/B reviews of actual rendered videos."""

import argparse
import json
import os


SCORE_FIELDS = (
    "prompt_fidelity", "composition_depth", "motion_stability", "emotion_readability",
    "skin_tone_cleanliness", "artifact_control", "continuity",
)
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}


def validate_manifest(manifest, base_dir):
    issues = []
    cases = manifest.get("cases", []) if isinstance(manifest, dict) else []
    if not isinstance(cases, list) or not cases:
        return ["cases必须是非空数组，且只能登记真实成片"]
    seen = set()
    for index, case in enumerate(cases):
        prefix = "cases[%d]" % index
        if not isinstance(case, dict):
            issues.append(prefix + "必须是对象")
            continue
        case_id = str(case.get("case_id", "") or "").strip()
        if not case_id or case_id in seen:
            issues.append(prefix + ".case_id缺失或重复")
        seen.add(case_id)
        if case.get("blind_confirmed") is not True:
            issues.append(prefix + ".blind_confirmed必须为true")
        if not str(case.get("reviewer_id", "") or "").strip():
            issues.append(prefix + ".reviewer_id不能为空")
        paths = {}
        for label in ("a", "b"):
            path = _resolve(base_dir, case.get("video_" + label, ""))
            paths[label] = path
            if not path or not os.path.isfile(path) or os.path.getsize(path) <= 0:
                issues.append(prefix + ".video_%s必须指向真实非空视频文件" % label)
            elif os.path.splitext(path)[1].lower() not in VIDEO_EXTENSIONS:
                issues.append(prefix + ".video_%s扩展名不受支持" % label)
        if paths.get("a") and paths.get("b") and os.path.abspath(paths["a"]) == os.path.abspath(paths["b"]):
            issues.append(prefix + "的A/B不能是同一个文件")
        scores = case.get("scores", {})
        for label in ("a", "b"):
            row = scores.get(label, {}) if isinstance(scores, dict) else {}
            for field in SCORE_FIELDS:
                value = row.get(field) if isinstance(row, dict) else None
                if not isinstance(value, (int, float)) or isinstance(value, bool) or not 1 <= value <= 10:
                    issues.append("%s.scores.%s.%s必须是1-10分" % (prefix, label, field))
        if case.get("winner") not in {"a", "b", "tie"}:
            issues.append(prefix + ".winner只允许a/b/tie")
        mapping = case.get("sealed_mapping", {})
        if not isinstance(mapping, dict) or {mapping.get("a"), mapping.get("b")} != {"before", "after"}:
            issues.append(prefix + ".sealed_mapping必须在盲评后揭示before/after一一映射")
        for field in ("prompt_before_sha256", "prompt_after_sha256"):
            if not _sha256_value(case.get(field)):
                issues.append(prefix + ".%s必须是64位SHA256" % field)
    return issues


def summarize(manifest, base_dir):
    issues = validate_manifest(manifest, base_dir)
    cases = manifest.get("cases", []) if isinstance(manifest, dict) and isinstance(manifest.get("cases"), list) else []
    after_wins = 0
    for case in cases:
        if not isinstance(case, dict):
            continue
        mapping = case.get("sealed_mapping", {}) if isinstance(case.get("sealed_mapping"), dict) else {}
        if case.get("winner") in ("a", "b") and mapping.get(case["winner"]) == "after":
            after_wins += 1
    return {
        "pass": not issues,
        "case_count": len(cases),
        "after_wins": after_wins,
        "after_win_rate": round(after_wins / len(cases), 4) if cases else 0,
        "issues": issues,
    }


def _resolve(base_dir, value):
    text = str(value or "").strip()
    if not text:
        return ""
    return text if os.path.isabs(text) else os.path.abspath(os.path.join(base_dir, text))


def _sha256_value(value):
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(char in "0123456789abcdef" for char in text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    args = parser.parse_args()
    path = os.path.abspath(args.manifest)
    with open(path, "r", encoding="utf-8-sig") as handle:
        manifest = json.load(handle)
    result = summarize(manifest, os.path.dirname(path))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
