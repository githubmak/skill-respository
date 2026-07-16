"""Contamination checks - XYZ coordinates, JSON-in-JSON, engineering terms."""
import json, re

XYZ_PATTERN = re.compile(r"\b[XxYyZz]\s*[:=]\s*-?\d+")
ENGG_PATTERN = re.compile(r"\b(vector|coordinate|coordinates|xyz|coord)\b", re.IGNORECASE)

FORBIDDEN_TEXT_FIELDS = [
    "axis_space", "camera_position", "composition", "character_action",
    "shot_size", "lighting", "audio_design", "micro_actions"
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

    # 3. Nested dicts inside dict-fields (must be plain text)
    for parent, children in [
        ("camera", ["lens","angle","movement","axis","transition","virtual_camera"]),
        ("emotion", ["cause","expression_chain","micro_expression","psychology_flow","performance_anchor"]),
        ("performance_plan", ["body_action","facial_expression","micro_actions","voice_performance","end_state"]),
    ]:
        pobj = item.get(parent, {})
        if isinstance(pobj, dict):
            for subf in children:
                val = pobj.get(subf)
                if isinstance(val, dict):
                    issues.append((ssid, "%s.%s" % (parent, subf), "NESTED_DICT", "must be plain text"))
                elif isinstance(val, list):
                    issues.append((ssid, "%s.%s" % (parent, subf), "NESTED_LIST", "must be plain text"))

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