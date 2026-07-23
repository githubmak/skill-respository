"""Content quality checks for current director and prompt packets."""
import json
import os
import re


DIRECTOR_THRESHOLDS = {
    "camera_position": 20,
    "axis_space": 30,
    "character_action": 30,
    "lighting": 30,
}


def quality_check_director(packet_path):
    if not os.path.exists(packet_path):
        return [(os.path.basename(packet_path), "FILE", 0, "not_found")]
    try:
        with open(packet_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception:
        return [(os.path.basename(packet_path), "JSON", 0, "valid_json")]

    issues = []
    for item in data.get("items", []):
        ssid = item.get("subshot_id", "?")
        for field, minimum in DIRECTOR_THRESHOLDS.items():
            text = str(item.get(field, "") or "")
            if len(text) < minimum:
                issues.append((ssid, field, len(text), ">=%d" % minimum))
            if re.search(r"\b[XYZ]\s*[:=]\s*-?\d+", text):
                issues.append((ssid, field + "[XYZ]", 0, "use screen direction, not coordinates"))
        if item.get("duration", 0) <= 0:
            issues.append((ssid, "duration", item.get("duration", 0), ">0"))
    return issues


def quality_check_prompt(path, minc=None, hard_max_chars=None):
    if not os.path.exists(path):
        return [(os.path.basename(path), "FILE", 0, "not_found")]
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception:
        return [(os.path.basename(path), "JSON", 0, "valid_json")]
    issues = []
    for item in data.get("shots", []):
        ssid = item.get("subshot_id", "?")
        fp = item.get("full_prompt", "")
        if isinstance(minc, int) and minc > 0 and len(fp) < minc:
            issues.append((ssid, "fp.len", len(fp), ">=%d" % minc))
        if isinstance(hard_max_chars, int) and hard_max_chars > 0 and len(fp) > hard_max_chars:
            issues.append((ssid, "fp.len", len(fp), "<=%d" % hard_max_chars))
    return issues
