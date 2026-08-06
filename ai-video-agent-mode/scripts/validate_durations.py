"""Mechanically validate declared duration values and sums."""

import json
import os


def validate(sp_path, max_per_shot=15, max_total=600, project_config_path=None):
    if project_config_path and os.path.isfile(project_config_path):
        try:
            with open(project_config_path, "r", encoding="utf-8-sig") as handle:
                config = json.load(handle)
            max_per_shot = min(float(config.get("max_shot_duration", max_per_shot)), 15.0)
            max_total = float(config.get("max_total_duration", max_total))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
    try:
        with open(sp_path, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return [("shot_plan.json", "JSON", 0, "readable JSON")]
    issues, total = [], 0.0
    for shot in data.get("shots", []) if isinstance(data, dict) else []:
        shot_id = str(shot.get("shot_id", "?"))
        subtotal = 0.0
        for subshot in shot.get("subshots", []) if isinstance(shot.get("subshots"), list) else []:
            sid = str(subshot.get("subshot_id", "?"))
            value = subshot.get("duration")
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
                issues.append(("%s/%s" % (shot_id, sid), "duration", value, ">0"))
                continue
            if float(value) > max_per_shot:
                issues.append(("%s/%s" % (shot_id, sid), "duration", value, "<=%.1f" % max_per_shot))
            subtotal += float(value)
        declared = shot.get("total_duration")
        if isinstance(declared, (int, float)) and not isinstance(declared, bool) and abs(float(declared) - subtotal) > 0.01:
            issues.append((shot_id, "total_duration", declared, subtotal))
        total += subtotal
    declared_total = data.get("total_duration") if isinstance(data, dict) else None
    if isinstance(declared_total, (int, float)) and not isinstance(declared_total, bool) and abs(float(declared_total) - total) > 0.01:
        issues.append(("GLOBAL", "total_duration", declared_total, total))
    if total > max_total:
        issues.append(("GLOBAL", "total_duration", total, "<=%.1f" % max_total))
    print("[DURATION] %s - %.1fs total" % ("PASS" if not issues else "FAIL", total))
    return issues
