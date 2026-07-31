#!/usr/bin/env python3
"""Audit episode-wide directing rhythm, performance variety, and speech capacity."""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from contract_registry import PROMPT_CONTRACT_VERSION
from dialogue_timing import analyze_dialogue_timing
from modec_v4 import camera_move_types
from pipeline_runtime import atomic_json


TENSION_MAP = {
    "setup": "setup", "铺垫": "setup", "latent": "setup", "neutral": "setup",
    "rise": "rising", "rising": "rising", "升压": "rising",
    "peak": "peak", "峰值": "peak",
    "release": "release", "释放": "release",
    "buffer": "buffer", "缓冲": "buffer",
}
SHOT_SIZES = ("大特写", "中近景", "中远景", "特写", "近景", "中景", "全景", "远景")
AGGRESSIVE_CAMERA_TERMS = ("快速推近", "急推", "甩镜", "高速", "环绕", "急拉", "猛推")
FIXED_CAMERA_TERMS = ("固定机位", "固定镜头", "机位固定", "摄影机固定", "运镜固定")
PERFORMANCE_FIELDS = (
    "primary_expression", "primary_body_action", "eye_focus",
    "voice_or_breath_control", "readable_image_moment",
)


def audit(run_dir, output_path=None):
    package_path = _find_package(run_dir)
    package = _load(package_path) if package_path else {}
    result = analyze_package(package)
    output_path = output_path or os.path.join(run_dir, ".cache", "validate", "episode_director_audit.json")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    atomic_json(output_path, result)
    return result, output_path


def analyze_package(package):
    shots = package.get("shots", []) if isinstance(package, dict) else []
    shots = shots if isinstance(shots, list) else []
    issues, warnings, records = [], [], []

    for index, shot in enumerate(shots):
        if not isinstance(shot, dict):
            issues.append("shots[%d]必须是对象" % index)
            continue
        metadata = shot.get("qa_metadata", {}) if isinstance(shot.get("qa_metadata"), dict) else {}
        prompt = str(shot.get("full_prompt", "") or "")
        performance = metadata.get("performance_contract", {})
        performance = performance if isinstance(performance, dict) else {}
        basemap = metadata.get("source_constraint_basemap", {})
        basemap = basemap if isinstance(basemap, dict) else {}
        palette = metadata.get("scene_tone_palette", {})
        palette = palette if isinstance(palette, dict) else {}
        dramatic = metadata.get("dramatic_design", {})
        dramatic = dramatic if isinstance(dramatic, dict) else {}
        story_punch = metadata.get("story_punch_contract", {})
        story_punch = story_punch if isinstance(story_punch, dict) else {}
        tension_raw = basemap.get("tension_curve_role") or performance.get("tension_intent") or ""
        tension = TENSION_MAP.get(str(tension_raw).strip(), "unknown")
        active_camera_text = _without_disabled_camera_moves(prompt)
        moves = sorted(camera_move_types(active_camera_text))
        camera_energy = _camera_energy(active_camera_text, moves, metadata)
        dialogue_records, dialogue_issues = analyze_dialogue_timing(
            metadata.get("dialogue_events", []), shot.get("duration", 0)
        )
        sid = str(shot.get("subshot_id", shot.get("shot_id", "")) or "?")
        issues.extend("%s: %s" % (sid, issue) for issue in dialogue_issues)
        records.append({
            "index": index,
            "shot_id": str(shot.get("shot_id", "") or ""),
            "subshot_id": sid,
            "scene_id": str(shot.get("scene") or palette.get("space_id") or "episode"),
            "tension": tension,
            "tension_source": str(tension_raw or ""),
            "shot_size": _shot_size(prompt, metadata),
            "coverage_role": str(dramatic.get("coverage_role", "") or ""),
            "camera_moves": moves,
            "camera_energy": camera_energy,
            "performance_fingerprint": _performance_fingerprint(performance),
            "performance_core_fingerprint": _performance_core_fingerprint(performance),
            "emotion_delta": performance.get("emotion_delta") if isinstance(performance.get("emotion_delta"), int) else None,
            "memory_frame": str(story_punch.get("picture_punctuation", "") or ""),
            "dialogue_timing": dialogue_records,
        })

    if not records:
        issues.append("全集导演审计缺少可分析镜头")
    _audit_tension(records, issues, warnings)
    _audit_camera_and_shot_size(records, issues, warnings)
    _audit_performance_repetition(records, issues, warnings)
    _audit_emotion_and_memory_curve(records, issues, warnings)
    return {
        "contract_version": PROMPT_CONTRACT_VERSION,
        "audit_version": "episode-director-audit-v1",
        "pass": bool(records) and not issues,
        "issues": issues,
        "warnings": warnings,
        "summary": {
            "shot_count": len(records),
            "dialogue_event_count": sum(len(item["dialogue_timing"]) for item in records),
            "peak_count": sum(item["tension"] == "peak" for item in records),
            "release_or_buffer_count": sum(item["tension"] in {"release", "buffer"} for item in records),
            "nonzero_emotion_delta_count": sum(item["emotion_delta"] not in (None, 0) for item in records),
            "warning_count": len(warnings),
        },
        "shots": records,
    }


def _audit_tension(records, issues, warnings):
    for window in _windows(records, 3):
        if all(item["tension"] == "peak" for item in window):
            same_scene = len({item["scene_id"] for item in window}) == 1
            mechanical = len({item["performance_core_fingerprint"] for item in window}) == 1
            high_energy = sum(item["camera_energy"] == "high" for item in window) >= 2
            message = "%s连续三镜均为峰值，缺少释放或关系缓冲" % _window_label(window)
            (issues if same_scene and (mechanical or high_energy) else warnings).append(message)
    for window in _windows(records, 4):
        if all(item["tension"] in {"rising", "peak"} for item in window):
            same_scene = len({item["scene_id"] for item in window}) == 1
            high_energy = sum(item["camera_energy"] == "high" for item in window) >= 3
            message = "%s连续四镜只升不放，张力曲线需语义复核" % _window_label(window)
            (issues if same_scene and high_energy else warnings).append(message)
    if len(records) >= 5 and not any(item["tension"] == "peak" for item in records):
        warnings.append("全集未检测到峰值镜；若源文确有高潮，需复核tension_curve_role")
    for index, item in enumerate(records):
        if item["tension"] != "peak":
            continue
        followers = records[index + 1:index + 3]
        if followers and not any(next_item["tension"] in {"release", "buffer"} for next_item in followers):
            warnings.append("%s峰值后两镜内未出现释放/缓冲" % item["subshot_id"])


def _audit_camera_and_shot_size(records, issues, warnings):
    for window in _windows(records, 3):
        if all(item["camera_energy"] == "high" for item in window):
            issues.append("%s连续三镜高能运镜，镜头响应压过表演" % _window_label(window))
    for window in _windows(records, 4):
        sizes = {item["shot_size"] for item in window}
        roles = {item["coverage_role"] for item in window}
        energies = {item["camera_energy"] for item in window}
        scenes = {item["scene_id"] for item in window}
        if len(scenes) == 1 and len(sizes) == 1 and "unknown" not in sizes and len(roles) == 1 and energies <= {"still", "low"}:
            issues.append("%s连续四镜同景别、同覆盖功能且低运动，画面节奏机械重复" % _window_label(window))
    for window in _windows(records, 3):
        sizes = {item["shot_size"] for item in window}
        if len(sizes) == 1 and "unknown" not in sizes:
            warnings.append("%s连续三镜使用%s，需确认是否为有意保持" % (_window_label(window), window[0]["shot_size"]))


def _audit_performance_repetition(records, issues, warnings):
    for window in _windows(records, 4):
        fingerprints = [item["performance_core_fingerprint"] for item in window]
        if fingerprints[0] and len(set(fingerprints)) == 1:
            issues.append("%s连续四镜重复同一组核心表情/身体微动作" % _window_label(window))
    for window in _windows(records, 3):
        fingerprints = [item["performance_core_fingerprint"] for item in window]
        if fingerprints[0] and len(set(fingerprints)) == 1:
            warnings.append("%s连续三镜核心微表演相同，建议改换泄露部位或身体承接" % _window_label(window))


def _audit_emotion_and_memory_curve(records, issues, warnings):
    for window in _windows(records, 4):
        same_scene = len({item["scene_id"] for item in window}) == 1
        deltas = [item["emotion_delta"] for item in window]
        if same_scene and all(delta == 0 for delta in deltas) and all(item["performance_core_fingerprint"] for item in window):
            warnings.append("%s连续四镜情绪变化量为0，需确认是否为有意压住而非表演停滞" % _window_label(window))
        frames = [_memory_signature(item["memory_frame"]) for item in window]
        if same_scene and frames[0] and len(set(frames)) == 1:
            warnings.append("%s连续四镜使用同一记忆帧戏眼，建议改变压力物、构图关系或落幅" % _window_label(window))


def _camera_energy(prompt, moves, metadata):
    text = str(prompt or "")
    beats = metadata.get("camera_beat_map", []) if isinstance(metadata, dict) else []
    beat_count = len(beats) if isinstance(beats, list) else 0
    if any(term in text for term in AGGRESSIVE_CAMERA_TERMS) or len(moves) >= 2 or beat_count >= 3:
        return "high"
    if moves or beat_count or any(term in text for term in ("推近", "横移", "跟拍", "拉焦", "重构图")):
        return "low"
    if any(term in text for term in FIXED_CAMERA_TERMS):
        return "still"
    return "still"


def _shot_size(prompt, metadata):
    for source in (
        metadata.get("shot_size", "") if isinstance(metadata, dict) else "",
        prompt,
    ):
        text = str(source or "")
        for size in SHOT_SIZES:
            if size in text:
                return size
    return "unknown"


def _performance_fingerprint(performance):
    values = []
    for field in PERFORMANCE_FIELDS:
        value = re.sub(r"[\s，,。！？；;：:]", "", str(performance.get(field, "") or "")).lower()
        if len(value) >= 4:
            values.append(value)
    return "|".join(values)


def _performance_core_fingerprint(performance):
    expression_patterns = (
        ("brow_tighten", r"眉(?:间|头|峰)?.{0,5}(?:收|紧|皱|压)"),
        ("jaw_tighten", r"下颌.{0,5}(?:紧|绷|咬|收)"),
        ("lip_tighten", r"(?:嘴角|唇线|嘴唇).{0,5}(?:压|抿|收|绷)"),
    )
    body_patterns = (
        ("finger_grip", r"(?:拇指|手指|指尖).{0,8}(?:压|扣|掐|攥|收|捏|握)"),
        ("shoulder_tighten", r"(?:肩线|肩颈|双肩).{0,6}(?:抬|沉|紧|绷|缩)"),
        ("weight_shift", r"(?:重心|身体重量).{0,6}(?:前移|后移|偏|压|沉)"),
    )
    expression = _performance_field_signature(performance.get("primary_expression", ""), expression_patterns)
    body = _performance_field_signature(performance.get("primary_body_action", ""), body_patterns)
    return expression + "::" + body if expression or body else ""


def _performance_field_signature(value, patterns):
    text = str(value or "")
    anchors = [label for label, pattern in patterns if re.search(pattern, text)]
    if anchors:
        return "|".join(anchors)
    normalized = re.sub(r"(?:轻轻|缓慢|短促|一下|一次|略微|微微)", "", text)
    normalized = re.sub(r"[\s，,。！？；;：:]", "", normalized).lower()
    return normalized if len(normalized) >= 4 else ""


def _memory_signature(value):
    text = re.sub(r"(?:轻轻|缓慢|短促|一下|一次|略微|微微)", "", str(value or ""))
    return re.sub(r"[\s，,。！？；;：:]", "", text).lower()


def _without_disabled_camera_moves(text):
    return re.sub(
        r"(?:禁止|不使用|不要|避免|无|取消)\s*(?:推镜|推近|拉镜|后拉|摇镜|平摇|横摇|甩镜|横移|侧移|跟拍|环绕|绕拍|手持|变焦|拉焦)",
        "固定镜头",
        str(text or ""),
    )


def _windows(records, size):
    return [records[index:index + size] for index in range(max(0, len(records) - size + 1))]


def _window_label(window):
    return "%s→%s" % (window[0]["subshot_id"], window[-1]["subshot_id"])


def _find_package(run_dir):
    for relative in (
        ".cache/composer/merged.prompt_package.json",
        ".cache/composer/prompt_package.json",
        ".cache/prompt_package.json",
    ):
        path = os.path.join(run_dir, relative)
        if os.path.exists(path):
            return path
    return ""


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit("usage: episode_director_audit.py <run_dir> [output.json]")
    result, path = audit(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)
    print("[EPISODE DIRECTOR AUDIT] %s: %s" % ("PASS" if result["pass"] else "FAIL", path))
    raise SystemExit(0 if result["pass"] else 1)
