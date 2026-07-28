"""Strict contract validation for one immutable Scene Lock record per scene."""
import json
import sys

REQUIRED = ("scene", "space_anchor", "screen_positions", "wardrobe_lock", "prop_state",
            "light_source", "light_direction", "light_temperature", "audio_policy")
OPTIONAL_FLAT_FIELDS = (
    "space_id", "space_master_sentence", "entrance_exit", "prop_activity_zone",
    "tone_palette", "light_texture_purpose",
)


def validate(path):
    with open(path, encoding="utf-8-sig") as handle:
        data = json.load(handle)
    issues, seen = [], set()
    space_master_by_id = {}
    scenes = data.get("scenes", []) if isinstance(data, dict) else []
    if not isinstance(scenes, list) or not scenes:
        return ["scenes must be a non-empty list"]
    for index, item in enumerate(scenes):
        prefix = "scene[%d]" % index
        if not isinstance(item, dict):
            issues.append(prefix + " must be an object"); continue
        scene = str(item.get("scene", "") or "").strip()
        if not scene or scene in seen:
            issues.append(prefix + " scene must be non-empty and unique")
        seen.add(scene)
        for field in REQUIRED[1:]:
            value = item.get(field)
            if value is None or value == "" or value == [] or value == {}:
                issues.append(prefix + " missing " + field)
            elif not isinstance(value, str):
                issues.append(prefix + " " + field + " must be a non-empty flat string")
        for field in OPTIONAL_FLAT_FIELDS:
            if field not in item:
                continue
            value = item.get(field)
            if value is None or value == "" or value == [] or value == {}:
                issues.append(prefix + " " + field + " must be a non-empty flat string when present")
            elif not isinstance(value, str):
                issues.append(prefix + " " + field + " must be a non-empty flat string")
        space_id = str(item.get("space_id", "") or "").strip()
        master_sentence = str(item.get("space_master_sentence", "") or "").strip()
        if space_id and master_sentence:
            previous = space_master_by_id.setdefault(space_id, master_sentence)
            if previous != master_sentence:
                issues.append(prefix + " space_id reuses a different space_master_sentence")
    return issues


if __name__ == "__main__":
    result = validate(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(1 if result else 0)
