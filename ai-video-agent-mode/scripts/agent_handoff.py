"""Persist compact agent handoff memory for context recovery."""
import json
import os
import time


def handoff_dir(run_dir):
    return os.path.join(run_dir, ".cache", "handoff")


def handoff_path(run_dir, role):
    return os.path.join(handoff_dir(run_dir), "%s_handoff.json" % role)


def write_handoff(run_dir, role, items, batch_index=None, agent_id=None, notes=None):
    """Write a compact, append-only handoff file for a role.

    items should contain per-subshot dictionaries. The function deliberately
    stores summaries and anchors, not full prompts, so retry messages stay small.
    """
    os.makedirs(handoff_dir(run_dir), exist_ok=True)
    path = handoff_path(run_dir, role)
    data = _load(path)
    record = {
        "role": role,
        "agent_id": agent_id,
        "batch_index": batch_index,
        "updated_at": time.time(),
        "items": [_normalize_item(item) for item in (items or [])],
        "notes": notes or [],
    }
    data.setdefault("records", []).append(record)
    data["latest"] = _merge_latest(data.get("latest", {}), record["items"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def read_handoff(run_dir, role=None, subshot_ids=None, max_chars=6000):
    """Return a compact handoff summary for retry/recover prompts."""
    roles = [role] if role else _available_roles(run_dir)
    wanted = set(subshot_ids or [])
    lines = []
    for r in roles:
        path = handoff_path(run_dir, r)
        data = _load(path)
        latest = data.get("latest", {})
        if not latest:
            continue
        lines.append("## handoff:%s" % r)
        for ssid in sorted(latest):
            if wanted and ssid not in wanted:
                continue
            item = latest[ssid]
            lines.append("- %s | %s" % (ssid, item.get("summary", "")))
            for key in ["decision_basis", "continuity_anchors", "open_questions", "do_not_change"]:
                val = item.get(key)
                if val:
                    lines.append("  %s: %s" % (key, _short(val, 280)))
    text = "\n".join(lines)
    return text[:max_chars]


def build_items_from_output(output_path, role):
    """Create handoff items from a role output JSON."""
    if not output_path or not os.path.exists(output_path):
        return []
    with open(output_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    items = []
    for item in data.get("items", []):
        ssid = item.get("subshot_id")
        if not ssid:
            continue
        items.append(_item_from_role_output(item, role))
    return items


def _item_from_role_output(item, role):
    ssid = item.get("subshot_id", "")
    if role == "emotion_analysis":
        return {
            "subshot_id": ssid,
            "summary": "情绪=%s，视线=%s，张力=%s" % (item.get("emotion_type", ""), item.get("gaze", ""), item.get("body_tension", "")),
            "decision_basis": item.get("emotion_trigger_short", ""),
            "continuity_anchors": "start=%s; end=%s" % (item.get("action_beat_start", ""), item.get("action_beat_end", "")),
            "do_not_change": "不改原始台词/OV/OS，只补无声表演",
        }
    if role == "scene_analysis":
        return {
            "subshot_id": ssid,
            "summary": "空间=%s/%s，灯光=%sK %s" % (item.get("space_type", ""), item.get("space_name", ""), item.get("light_temp", ""), item.get("light_direction", "")),
            "decision_basis": item.get("mood_atmosphere", ""),
            "continuity_anchors": "positions=%s; bg=%s/%s/%s" % (item.get("char_positions", []), item.get("bg_foreground", ""), item.get("bg_midground", ""), item.get("bg_background", "")),
            "do_not_change": "同场景保持光源方向、背景元素、人物站位连续",
        }
    if role == "camera_movement":
        return {
            "subshot_id": ssid,
            "summary": "景别=%s，机位=%s，运镜=%s" % (item.get("shot_size", ""), item.get("camera_relative_pos", ""), item.get("movement_type", "")),
            "decision_basis": item.get("movement_detail", ""),
            "continuity_anchors": "axis_start=%s; axis_end=%s; entry=%s; exit=%s" % (item.get("axis_start", ""), item.get("axis_end", ""), item.get("char_entry", ""), item.get("char_exit", "")),
            "do_not_change": "保持180度轴线，越轴必须写明转身/绕行/空镜过渡",
        }
    return {
        "subshot_id": ssid,
        "summary": _short(item.get("full_prompt") or item.get("character_action") or str(item), 240),
        "decision_basis": item.get("repair_notes", "") or item.get("commercial_quality", ""),
        "continuity_anchors": "shot=%s duration=%s" % (item.get("shot_id", ""), item.get("duration", "")),
        "do_not_change": "不新增、删除、改写台词/OV/OS",
    }


def _normalize_item(item):
    ssid = item.get("subshot_id", "")
    return {
        "subshot_id": ssid,
        "summary": _short(item.get("summary", ""), 500),
        "decision_basis": _short(item.get("decision_basis", ""), 500),
        "continuity_anchors": _short(item.get("continuity_anchors", ""), 500),
        "open_questions": _short(item.get("open_questions", ""), 500),
        "do_not_change": _short(item.get("do_not_change", ""), 500),
    }


def _merge_latest(latest, items):
    latest = dict(latest or {})
    for item in items:
        ssid = item.get("subshot_id")
        if ssid:
            latest[ssid] = item
    return latest


def _available_roles(run_dir):
    hd = handoff_dir(run_dir)
    if not os.path.isdir(hd):
        return []
    roles = []
    for fn in os.listdir(hd):
        if fn.endswith("_handoff.json"):
            roles.append(fn[:-len("_handoff.json")])
    return roles


def _load(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _short(value, limit):
    if isinstance(value, (list, tuple)):
        value = "；".join(str(v) for v in value)
    elif isinstance(value, dict):
        value = json.dumps(value, ensure_ascii=False)
    value = str(value or "").replace("\n", " ").strip()
    return value[:limit]


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("usage: agent_handoff.py <run_dir> <role> [output.json]")
        sys.exit(1)
    run_dir, role = sys.argv[1], sys.argv[2]
    if len(sys.argv) > 3:
        items = build_items_from_output(sys.argv[3], role)
        print(write_handoff(run_dir, role, items))
    else:
        print(read_handoff(run_dir, role))
