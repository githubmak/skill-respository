"""Field type validation for current pipeline packets."""
import json
import os


DIRECTOR_REQUIRED = {
    "shot_id": str,
    "subshot_id": str,
    "duration": (int, float),
    "shot_size": str,
    "camera_position": str,
    "camera": str,
    "axis_space": str,
    "visible_characters": str,
    "character_action": str,
    "dialogue_audio": str,
    "lighting": str,
    "end_state": str,
}

PROMPT_REQUIRED = {
    "shot_id": str,
    "subshot_id": str,
    "duration": (int, float),
    "full_prompt": str,
}


def validate_field_types(packet_path):
    if not os.path.exists(packet_path):
        return [(os.path.basename(packet_path), "FILE", "", "not_found")]
    try:
        with open(packet_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception:
        return [(os.path.basename(packet_path), "JSON", "", "parse_error")]

    items = data.get("items", [])
    issues = []
    if not isinstance(items, list):
        return [(os.path.basename(packet_path), "items", type(items).__name__, "list")]

    required = PROMPT_REQUIRED if _looks_like_prompt(items) else DIRECTOR_REQUIRED
    for item in items:
        ssid = item.get("subshot_id", "?") if isinstance(item, dict) else "?"
        if not isinstance(item, dict):
            issues.append((ssid, "item", type(item).__name__, "dict"))
            continue
        sid = item.get("shot_id", "")
        if isinstance(sid, str) and len(sid.split("-")) == 3:
            issues.append((ssid, "shot_id", sid, "two-segment format"))
        for field, expected_type in required.items():
            value = item.get(field)
            if not isinstance(value, expected_type):
                exp = "number" if expected_type == (int, float) else expected_type.__name__
                issues.append((ssid, field, type(value).__name__, exp))
    return issues


def _looks_like_prompt(items):
    return any(isinstance(item, dict) and "full_prompt" in item for item in items)
