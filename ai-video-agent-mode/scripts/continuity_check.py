"""Cross-shot continuity check."""
import json, os, re, sys


LEFT_WORDS = ["画左", "左侧", "画面左", "向左", "从左", "左方"]
RIGHT_WORDS = ["画右", "右侧", "画面右", "向右", "从右", "右方"]
TURN_OR_TRANSITION_WORDS = ["转身", "绕行", "绕到", "穿过", "越过", "跨过", "空镜", "转场", "切到", "镜头绕", "环绕", "反打", "过肩"]


def _side_of(text):
    if not isinstance(text, str):
        return None
    left = any(w in text for w in LEFT_WORDS)
    right = any(w in text for w in RIGHT_WORDS)
    if left and not right:
        return "left"
    if right and not left:
        return "right"
    return None


def _has_axis_transition(text):
    return isinstance(text, str) and any(w in text for w in TURN_OR_TRANSITION_WORDS)


def _characters_for_item(item, known_chars):
    blob = "\n".join(str(item.get(k, "")) for k in ["visible_characters", "character_action", "axis_space"])
    return [c for c in known_chars if c and c in blob]


def _axis_crossing_issue(prev_item, curr_item, known_chars):
    if prev_item.get("shot_id") and curr_item.get("shot_id"):
        # Only enforce across adjacent shots in the same scene/shot group when possible.
        prev_scene = prev_item.get("scene", "")
        curr_scene = curr_item.get("scene", "")
        if prev_scene and curr_scene and prev_scene != curr_scene:
            return None
    prev_blob = "\n".join(str(prev_item.get(k, "")) for k in ["axis_end", "axis_space", "camera", "character_action", "end_state"])
    curr_blob = "\n".join(str(curr_item.get(k, "")) for k in ["axis_start", "axis_space", "camera", "character_action", "char_entry_exit"])
    if _has_axis_transition(prev_blob + "\n" + curr_blob):
        return None
    prev_side = _side_of(prev_blob)
    curr_side = _side_of(curr_blob)
    if not prev_side or not curr_side or prev_side == curr_side:
        return None
    shared = set(_characters_for_item(prev_item, known_chars)) & set(_characters_for_item(curr_item, known_chars))
    if known_chars and not shared:
        return None
    return "相邻镜头疑似无解释越轴：%s 从 %s 到 %s，缺少转身/绕行/空镜/反打等过渡说明" % (
        ",".join(sorted(shared)) if shared else "角色", prev_side, curr_side)


def _extract_characters(shot_plan):
    """Extract unique character names from shot_plan data."""
    chars = set()
    for shot in shot_plan.get("shots", []):
        for ss in shot.get("subshots", []):
            for c in ss.get("characters", []):
                if c: chars.add(c)
    return sorted(chars)


def run(run_dir, dry=False):
    """Check continuity across all director packets.

    Scans all .director_packet.json files in .cache/director/
    and .cache/orchestrator/shot_plan.json.

    Returns:
        (warning_count, error_count, issues_list)
    """
    director_dir = os.path.join(run_dir, ".cache", "director")
    plan_path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")

    issues = []
    warnings = 0
    errors = 0

    shot_plan = {}
    if os.path.exists(plan_path):
        with open(plan_path, "r", encoding="utf-8-sig") as f:
            shot_plan = json.load(f)

    if not os.path.isdir(director_dir):
        return (0, 0, issues)

    packets = []
    for fn in sorted(os.listdir(director_dir)):
        if fn.endswith(".director_packet.json"):
            fp = os.path.join(director_dir, fn)
            with open(fp, "r", encoding="utf-8-sig") as f:
                try:
                    packets.append(json.load(f))
                except json.JSONDecodeError:
                    issues.append((fn, "JSON_PARSE", 0, "invalid_json"))
                    errors += 1
    if not packets:
        dp_fallback = os.path.join(director_dir, "director_pass.json")
        if os.path.exists(dp_fallback):
            with open(dp_fallback, "r", encoding="utf-8-sig") as f:
                try:
                    packets.append(json.load(f))
                except Exception:
                    pass

    if not packets:
        if not dry:
            char_state = _track_characters(packets, shot_plan)
        else:
            char_state = {}
        _save_report(run_dir, warnings, errors, issues, char_state)
        return (warnings, errors, issues)

    prev_size = None
    for pkt in packets:
        for item in pkt.get("items", []):
            sz = item.get("shot_size", "")
            sid = item.get("subshot_id", "?")
            if prev_size and sz:
                size_jumps = {"ECU": 1, "CU": 2, "MCU": 3, "MS": 4, "FS": 5, "LS": 6, "ELS": 7}
                pn = size_jumps.get(prev_size.split("(")[0].strip(), 0)
                cn = size_jumps.get(sz.split("(")[0].strip(), 0)
                if pn and cn and abs(cn - pn) >= 4:
                    issues.append((sid, "SHOT_SIZE_GAP", abs(cn-pn), "<=3"))
                    warnings += 1
            if sz:
                prev_size = sz

    known_chars = _extract_characters(shot_plan)
    prev_item = None
    for pkt in packets:
        for item in pkt.get("items", []):
            if prev_item is not None:
                axis_issue = _axis_crossing_issue(prev_item, item, known_chars)
                if axis_issue:
                    issues.append((item.get("subshot_id", "?"), "AXIS_CROSSING", "blocking", axis_issue))
                    errors += 1
            prev_item = item

    if not dry:
        char_state = _track_characters(packets, shot_plan)
    else:
        char_state = {}
    _save_report(run_dir, warnings, errors, issues, char_state)

    return (warnings, errors, issues)


def _track_characters(packets, shot_plan):
    """Track character presence/action continuity across shots.
    Character names are extracted from shot_plan data, not hardcoded."""
    known_chars = _extract_characters(shot_plan)
    if not known_chars:
        return {}
    char_track = {}
    for pkt in packets:
        for item in pkt.get("items", []):
            sid = item.get("shot_id", "?")
            ca = item.get("character_action", "")
            chars = []
            for name in known_chars:
                if name in ca[:50]:
                    chars.append(name)
                    if name not in char_track:
                        char_track[name] = {"shots": [], "actions": [], "inconsistencies": []}
                    char_track[name]["shots"].append(sid)
                    if "." in ca:
                        action = ca.split(".")[0].strip()[:20]
                        if char_track[name]["actions"] and action != char_track[name]["actions"][-1]:
                            char_track[name]["actions"].append(action)
            for name in chars:
                pass
    return char_track


def _save_report(run_dir, warnings, errors, issues, char_state=None):
    report_path = os.path.join(run_dir, ".cache", "continuity", "report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        report = {"warnings": warnings, "errors": errors, "issues": issues}
        if char_state:
            report["character_state"] = char_state
        json.dump(report, f, ensure_ascii=False)
    print("[CONTINUITY] %d errors, %d warnings" % (errors, warnings))
