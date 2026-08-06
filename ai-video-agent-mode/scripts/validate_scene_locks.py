"""Validate only the deterministic Scene Lock envelope."""

import json
import sys


def validate(path):
    try:
        with open(path, encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return ["scene lock JSON is unreadable: %s" % exc]
    scenes = data.get("scenes", []) if isinstance(data, dict) else []
    if not isinstance(scenes, list) or not scenes:
        return ["scenes must be a non-empty list"]
    issues, seen_scenes, seen_ids = [], set(), set()
    for index, item in enumerate(scenes):
        prefix = "scene[%d]" % index
        if not isinstance(item, dict):
            issues.append(prefix + " must be an object")
            continue
        scene = item.get("scene")
        space_id = item.get("space_id")
        if not isinstance(scene, str) or not scene.strip() or scene in seen_scenes:
            issues.append(prefix + " scene must be a non-empty unique string")
        if not isinstance(space_id, str) or not space_id.strip() or space_id in seen_ids:
            issues.append(prefix + " space_id must be a non-empty unique string")
        seen_scenes.add(scene)
        seen_ids.add(space_id)
        creative_fields = [key for key, value in item.items() if key not in {"scene", "space_id"} and value not in (None, "", [], {})]
        if not creative_fields:
            issues.append(prefix + " CREATIVE_REWRITE_REQUIRED: model-authored scene contract is empty")
    return issues


if __name__ == "__main__":
    result = validate(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(1 if result else 0)
