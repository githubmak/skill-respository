"""Contamination checks - XYZ coordinates, JSON-in-JSON, engineering terms."""
import json, re

XYZ_PATTERN = re.compile(r"\b[XxYyZz]\s*[:=]\s*-?\d+")
ENGG_PATTERN = re.compile(r"\b(vector|coordinate|coordinates|xyz|coord)\b", re.IGNORECASE)

FORBIDDEN_TEXT_FIELDS = [
    "axis_space", "camera_position", "composition", "character_action",
    "shot_size", "lighting", "dialogue_audio", "visible_characters",
    "camera", "char_entry_exit", "end_state", "movement_detail"
]


def check_contamination(item):
    """Check a single director item for format contamination.
    
    Returns list of (subshot_id, field, problem_type, detail)
    """
    issues = []
    ssid = item.get("subshot_id", "?")

    # 1. XYZ coordinates in text fields
    for field in FORBIDDEN_TEXT_FIELDS:
        val = item.get(field, "")
        if isinstance(val, str):
            if XYZ_PATTERN.search(val):
                issues.append((ssid, field, "XYZ_COORD", "use Chinese direction terms"))
            if ENGG_PATTERN.search(val):
                issues.append((ssid, field, "ENGG_TERM", "replace with natural language"))

    # 2. JSON-in-JSON (string fields with JSON payload)
    all_text = FORBIDDEN_TEXT_FIELDS + ["character_action"]
    for field in all_text:
        val = item.get(field, "")
        if isinstance(val, str) and len(val) > 10:
            trimmed = val.strip()
            if (trimmed.startswith("{") and trimmed.endswith("}")) or \
               (trimmed.startswith("[") and trimmed.endswith("]")):
                try:
                    json.loads(trimmed)
                    issues.append((ssid, field, "JSON_IN_STRING", "do not embed JSON in text"))
                except json.JSONDecodeError:
                    pass

    return issues


def check_prompt_contamination(prompt_item):
    """Check prompt package item for contamination."""
    issues = []
    ssid = prompt_item.get("subshot_id", "?")
    fp = prompt_item.get("full_prompt", "")
    if isinstance(fp, str) and len(fp) > 20:
        trimmed = fp.strip()
        if trimmed.startswith("{") and trimmed.endswith("}"):
            try:
                json.loads(trimmed)
                issues.append((ssid, "full_prompt", "JSON_IN_STRING", "do not embed JSON in prompt"))
            except json.JSONDecodeError:
                pass
    return issues
