#!/usr/bin/env python3
"""Shared dialogue-duration and visible lip-window calculations."""

import re


DIALOGUE_CHARS_PER_SEC = 4.5
PAUSE_PER_PUNCTUATION = 0.3
PAUSE_PER_SENTENCE_END = 0.5
PUNCTUATION_CHARS = set(",，、；")
SENTENCE_ENDS = set("。！？…\u2026")
EMOTION_SPEED = {
    "激动": 1.2, "兴奋": 1.2, "慌乱": 1.1, "炸裂": 1.2,
    "崩溃": 1.1, "热情": 1.1, "愉快": 1.1, "急切": 1.2,
    "催促": 1.2, "快速": 1.15, "加快": 1.15,
    "迟疑": 0.85, "压抑": 0.85, "阴沉": 0.85, "低落": 0.8,
    "委屈": 0.85, "嘲讽": 0.8, "威胁": 0.8, "冷淡": 0.85,
    "忐忑": 0.85, "隐忍": 0.85, "暗沉": 0.85, "失落": 0.85,
    "无奈": 0.9, "无语": 0.9, "吐槽": 0.95, "慢速": 0.8,
    "放慢": 0.8, "一字一顿": 0.72, "语速偏慢": 0.85,
    "稍慢": 0.88, "缓慢": 0.82, "慢声": 0.85,
}


def estimate_dialogue_seconds(dialogue_text, emotion_tone=""):
    """Estimate natural speech time using one shared planner/validator model."""
    if not dialogue_text:
        return 0.0
    text = re.sub(r"^[^：]+[：]\s*", "", str(dialogue_text)) or str(dialogue_text)
    effective_speed = speech_chars_per_second(emotion_tone)
    punct_pauses = sum(1 for char in text if char in PUNCTUATION_CHARS)
    sent_pauses = sum(1 for char in text if char in SENTENCE_ENDS)
    duration = len(text) / effective_speed
    duration += punct_pauses * PAUSE_PER_PUNCTUATION
    duration += sent_pauses * PAUSE_PER_SENTENCE_END
    return max(round(duration, 1), 0.5)


def speech_speed_factor(tone):
    text = str(tone or "")
    explicit = _explicit_chars_per_second(text)
    if explicit is not None:
        return explicit / DIALOGUE_CHARS_PER_SEC
    for keyword, factor in EMOTION_SPEED.items():
        if keyword in text:
            return factor
    return 1.0


def speech_chars_per_second(tone):
    explicit = _explicit_chars_per_second(str(tone or ""))
    if explicit is not None:
        return explicit
    return DIALOGUE_CHARS_PER_SEC * speech_speed_factor(tone)


def parse_second_range(value):
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*秒\s*", str(value or ""))
    if not match:
        return None
    start, end = float(match.group(1)), float(match.group(2))
    return (start, end) if start < end else None


def estimate_event_seconds(event):
    """Honor delivery speed and explicit breath pauses without double-counting."""
    event = event if isinstance(event, dict) else {}
    text = str(event.get("text", "") or "")
    delivery = "%s %s" % (event.get("source_tone", "") or "", event.get("delivery", "") or "")
    baseline = estimate_dialogue_seconds(text, delivery)
    effective_speed = speech_chars_per_second(delivery)
    spoken_chars = len(re.sub(r"[\s，,、；;。！？!?…：:]", "", text))
    explicit_pauses = sum(
        float(value) for value in re.findall(r"(\d+(?:\.\d+)?)\s*秒", str(event.get("breath_pause_plan", "") or ""))
    )
    explicit_plan = spoken_chars / effective_speed + explicit_pauses
    return round(max(baseline, explicit_plan), 2)


def analyze_dialogue_timing(events, duration=None, capacity_tolerance=0.12, overlap_tolerance=0.001):
    """Return event timing evidence and hard execution issues."""
    records, issues, visible_windows = [], [], []
    try:
        shot_duration = float(duration or 0)
    except (TypeError, ValueError):
        shot_duration = 0.0
    for index, event in enumerate(events if isinstance(events, list) else []):
        if not isinstance(event, dict):
            continue
        time_range = parse_second_range(event.get("time_range"))
        required = estimate_event_seconds(event)
        available = round(time_range[1] - time_range[0], 2) if time_range else None
        record = {
            "index": index,
            "ref": str(event.get("ref", "") or ""),
            "speaker": str(event.get("speaker", "") or ""),
            "kind": str(event.get("kind", "") or ""),
            "time_range": str(event.get("time_range", "") or ""),
            "required_seconds": required,
            "available_seconds": available,
            "speech_rate_cps": round(speech_chars_per_second(
                "%s %s" % (event.get("source_tone", "") or "", event.get("delivery", "") or "")
            ), 2),
            "visible_lip_sync": bool(event.get("lip_sync") is True and event.get("speaker_visibility") == "visible"),
        }
        records.append(record)
        if time_range and available + capacity_tolerance < required:
            issues.append(
                "dialogue_events[%d]台词时间窗%.2f秒不足，自然表演至少需要%.2f秒" % (index, available, required)
            )
        if time_range and shot_duration > 0 and time_range[1] > shot_duration + capacity_tolerance:
            issues.append("dialogue_events[%d]口型/声音时间窗超出镜头时长" % index)
        if record["visible_lip_sync"] and time_range:
            visible_windows.append((time_range[0], time_range[1], index, record["speaker"]))

    visible_windows.sort()
    for previous, current in zip(visible_windows, visible_windows[1:]):
        overlap = min(previous[1], current[1]) - max(previous[0], current[0])
        if overlap > overlap_tolerance:
            issues.append(
                "dialogue_events[%d]与dialogue_events[%d]可见口型窗重叠%.2f秒（%s/%s）" % (
                    previous[2], current[2], overlap, previous[3], current[3]
                )
            )
    return records, issues


def _explicit_chars_per_second(text):
    match = re.search(r"(?:每秒\s*)?(\d+(?:\.\d+)?)\s*字(?:\s*/\s*秒)?", str(text or ""))
    if not match:
        return None
    value = float(match.group(1))
    return value if 1.5 <= value <= 8.0 else None
