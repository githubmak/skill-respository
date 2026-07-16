"""Validate shot durations against total limits."""
import json, os, sys


def validate(sp_path, max_per_shot=15, max_total=600):
    """Validate all shot durations.

    Args:
        sp_path: Path to shot_plan.json
        max_per_shot: Max seconds per individual shot
        max_total: Max total seconds for all shots

    Returns:
        list of issues [(shot_id, field, value, expected)]
    """
    if not os.path.exists(sp_path):
        return [("shot_plan.json", "FILE", 0, "not_found")]

    try:
        with open(sp_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return [("shot_plan.json", "JSON", 0, "parse_error")]

    issues = []
    total_dur = 0.0
    shots = data.get("shots", [])

    for shot in shots:
        sid = shot.get("shot_id", "?")
        subshots = shot.get("subshots", [])
        shot_dur = 0.0

        for ss in subshots:
            d = ss.get("duration", 0)
            if not isinstance(d, (int, float)) or d <= 0:
                issues.append(("%s/%s" % (sid, ss.get("subshot_id", "?")), "duration", d, ">0"))
            shot_dur += d

        if shot_dur > max_per_shot:
            issues.append((sid, "shot_duration", shot_dur, "<=%d" % max_per_shot))
        total_dur += shot_dur

    if total_dur > max_total:
        issues.append(("TOTAL", "total_duration", total_dur, "<=%d" % max_total))

    if issues:
        print("[DURATION] %d duration issue(s)" % len(issues))
    else:
        print("[DURATION] PASS - %.1fs total" % total_dur)

    return issues


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "shot_plan.json"
    issues = validate(path)
    print(json.dumps(issues, ensure_ascii=False, indent=2))
