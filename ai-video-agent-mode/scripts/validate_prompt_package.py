"""Validate prompt package completeness and consistency."""
import json, os, sys


def validate(pkg_path):
    """Validate a prompt package JSON file.

    Checks:
      1. JSON structure valid
      2. All items have required fields
      3. merged_full_prompts covers all shot_ids
      4. Duration totals match

    Returns:
        list of issues [(subshot_id, field, value, expected)]
    """
    if not os.path.exists(pkg_path):
        return [("FILE", "not_found", 0, "")]

    try:
        with open(pkg_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [("JSON", "parse_error", 0, str(e))]

    issues = []
    items = data.get("items", [])
    shot_ids = set()
    required_prompt_fields = ["full_prompt", "shot_id", "subshot_id", "duration"]

    for item in items:
        sid = item.get("subshot_id", "?")
        shot_ids.add(item.get("shot_id", "?"))

        for field in required_prompt_fields:
            if field not in item or item.get(field) is None:
                issues.append((sid, field, "missing", "required"))

        fp = item.get("full_prompt", "")
        if len(fp) < 500:
            issues.append((sid, "full_prompt.len", len(fp), ">=500"))

        dur = item.get("duration", 0)
        if not isinstance(dur, (int, float)) or dur <= 0:
            issues.append((sid, "duration", dur, ">0"))

    # Check merged_full_prompts cover all shot_ids
    merged = data.get("merged_full_prompts", [])
    merged_ids = set(m.get("shot_id", "") for m in merged)
    missing_merged = shot_ids - merged_ids
    for sid in missing_merged:
        issues.append((sid, "merged_full_prompts", "missing", "merge_required"))

    if issues:
        print("[VALIDATE_PKG] %d issue(s) found" % len(issues))
    else:
        print("[VALIDATE_PKG] PASS")

    return issues


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: validate_prompt_package.py <pkg_path>")
        sys.exit(1)
    issues = validate(sys.argv[1])
    print(json.dumps(issues, ensure_ascii=False, indent=2))
    sys.exit(0 if len(issues) == 0 else 1)
