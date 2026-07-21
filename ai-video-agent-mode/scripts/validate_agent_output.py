"""Validate director/prompt agent output."""
import json, os, sys
from validator.field_types import validate_field_types
from validator.quality import quality_check_director, quality_check_prompt


def validate(packet_path, role="director", min_chars=120):
    """Run full validation pipeline.

    Args:
        packet_path: Path to agent output JSON
        role: "director" or "prompt"
        min_chars: Minimum chars for full_prompt (prompt role only)

    Returns:
        dict with keys:
          valid (bool) - overall pass/fail
          issues (list) - all issues found
          retry_needed (bool) - True if any blocking issue requires retry
    """
    if not os.path.exists(packet_path):
        return {"valid": False, "issues": [("FILE", "not_found", 0, "")], "retry_needed": True}

    if role in ("analysis", "emotion_analysis", "scene_analysis", "camera_movement"):
        all_issues = _validate_analysis(packet_path, role)
        _print_result(role, all_issues)
        return {"valid": not all_issues, "issues": all_issues, "retry_needed": bool(all_issues)}

    # Step 1: Field type validation
    field_issues = validate_field_types(packet_path)

    # === Continuity report validator ===
    if role == "continuity":
        try:
            with open(packet_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            errs = data.get("errors", 0)
            warns = data.get("warnings", 0)
            issues = []
            for iss in data.get("issues", []):
                if len(iss) >= 4:
                    issues.append(("CONTINUITY", iss[1], iss[2], iss[3]))
            if errs > 0 or warns > 2:
                return {"valid": False, "issues": issues, "retry_needed": True}
            return {"valid": True, "issues": [], "retry_needed": False}
        except Exception:
            return {"valid": True, "issues": [], "retry_needed": False}

    if role == "director":
        quality_issues = quality_check_director(packet_path)
    else:
        quality_issues = quality_check_prompt(packet_path, minc=min_chars)

    all_issues = field_issues + quality_issues

    # Step 3: Determine if retry is needed
    retry_needed = len(all_issues) > 0
    valid = not retry_needed

    _print_result(role, all_issues)

    return {"valid": valid, "issues": all_issues, "retry_needed": retry_needed}


def _validate_analysis(path, role):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as exc:
        return [("GLOBAL", "JSON", type(exc).__name__, "valid_json")]

    issues = []
    if not isinstance(data, dict):
        return [("GLOBAL", "root", type(data).__name__, "object")]
    extra_keys = set(data) - {"items"}
    for key in sorted(extra_keys):
        issues.append(("GLOBAL", "top_key", key, "items only"))
    items = data.get("items")
    if not isinstance(items, list):
        return issues + [("GLOBAL", "items", type(items).__name__, "list")]

    if role == "analysis":
        role = _infer_analysis_role(path, items)

    required = _analysis_required_fields(role)
    for item in items:
        if not isinstance(item, dict):
            issues.append(("?", "item", type(item).__name__, "dict"))
            continue
        sid = item.get("subshot_id", "?")
        if item.get("id") != sid:
            issues.append((sid, "id", item.get("id"), "same as subshot_id"))
        shot_id = item.get("shot_id", "")
        if isinstance(shot_id, str) and len(shot_id.split("-")) == 3:
            issues.append((sid, "shot_id", shot_id, "two-segment format"))
        for field in required:
            if field not in item:
                issues.append((sid, field, "missing", "required"))
        if role in ("analysis", "emotion_analysis"):
            level = item.get("expression_level")
            if level not in ("micro", "visible", "strong"):
                issues.append((sid, "expression_level", level, "micro|visible|strong"))
            if "per_char_actions" in item and not isinstance(item.get("per_char_actions"), list):
                issues.append((sid, "per_char_actions", type(item.get("per_char_actions")).__name__, "list"))
            elif isinstance(item.get("per_char_actions"), list):
                actions = [action for action in item.get("per_char_actions", []) if isinstance(action, dict)]
                roles = [action.get("performance_role") for action in actions]
                for index, assigned in enumerate(roles):
                    if assigned not in ("primary", "supporting", "background"):
                        issues.append((sid, "per_char_actions[%d].performance_role" % index, assigned, "primary|supporting|background"))
                if actions and roles.count("primary") != 1:
                    issues.append((sid, "performance_role.primary", roles.count("primary"), "exactly 1"))
                if roles.count("supporting") > 1:
                    issues.append((sid, "performance_role.supporting", roles.count("supporting"), "<=1"))
        if role in ("analysis", "scene_analysis"):
            hard = item.get("light_hardness")
            if hard is not None and hard not in ("soft", "hard", "mixed"):
                issues.append((sid, "light_hardness", hard, "soft|hard|mixed"))
            temp = item.get("light_temp")
            if temp is not None and not isinstance(temp, (int, float)):
                issues.append((sid, "light_temp", type(temp).__name__, "number"))
        if role in ("analysis", "camera_movement"):
            size = item.get("shot_size")
            allowed_sizes = ("大特写", "特写", "中近景", "中景", "全景", "大远景")
            if size is not None and size not in allowed_sizes:
                issues.append((sid, "shot_size", size, "|".join(allowed_sizes)))
            move = item.get("movement_type")
            allowed_moves = ("固定", "推", "拉", "摇", "移", "跟", "升", "降", "俯", "仰", "环绕", "甩", "变焦", "旋转", "手持", "穿梭")
            if move is not None and move not in allowed_moves:
                issues.append((sid, "movement_type", move, "|".join(allowed_moves)))
            lens = item.get("camera_lens_mm")
            if lens is not None and not isinstance(lens, (int, float)):
                issues.append((sid, "camera_lens_mm", type(lens).__name__, "number"))
    return issues


def _infer_analysis_role(path, items):
    name = os.path.basename(path).lower()
    if "emotion" in name:
        return "emotion_analysis"
    if "scene" in name:
        return "scene_analysis"
    if "camera" in name or "movement" in name:
        return "camera_movement"

    first = next((item for item in items if isinstance(item, dict)), {})
    if "expression_level" in first or "per_char_actions" in first:
        return "emotion_analysis"
    if "space_type" in first or "light_temp" in first or "bg_foreground" in first:
        return "scene_analysis"
    if "shot_size" in first or "movement_type" in first or "camera_lens_mm" in first:
        return "camera_movement"
    return "analysis_generic"


def _analysis_required_fields(role):
    common = ["id", "shot_id", "subshot_id"]
    if role == "emotion_analysis":
        return common + [
            "emotion_type", "expression_level", "gaze", "micro_expression",
            "body_tension", "body_parts_focus", "voice_tone",
            "action_beat_start", "action_beat_transition", "action_beat_end",
            "per_char_actions", "emotion_trigger_short", "performance_note",
        ]
    if role == "scene_analysis":
        return common + [
            "space_type", "space_name", "char_positions", "char_wardrobes",
            "bg_foreground", "bg_midground", "bg_background", "light_type",
            "light_temp", "light_direction", "light_hardness", "mood_atmosphere",
            "ambient_sound", "audio_background", "audio_foreground", "audio_midground",
            "bgm_style", "color_contrast_desc", "light_effect_primary_char",
            "light_effect_other_chars", "lighting", "sfx_timing",
        ]
    if role == "camera_movement":
        return common + [
            "shot_size", "camera_lens_mm", "camera_relative_pos",
            "camera_distance_steps", "camera_height_relative", "angle_str",
            "camera_facing_desc", "movement_type", "movement_detail",
            "movement_speed", "axis_start", "axis_end", "char_entry",
            "char_exit", "end_state", "composition", "lens_effect",
            "movement_arc_deg", "body_extra",
        ]
    return common


def _print_result(role, issues):
    if issues:
        print("[VALIDATE] %s - %d issue(s) found" % (role, len(issues)))
        for iss in issues[:5]:
            print("  [%s] %s: %s vs expected %s" % (iss[1], iss[0], iss[2], iss[3]))
        if len(issues) > 5:
            print("  ... and %d more" % (len(issues) - 5))
    else:
        print("[VALIDATE] %s - PASS" % role)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: validate_agent_output.py <packet_path> [role]")
        sys.exit(1)
    role = sys.argv[2] if len(sys.argv) > 2 else "director"
    result = validate(sys.argv[1], role)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["valid"] else 1)
