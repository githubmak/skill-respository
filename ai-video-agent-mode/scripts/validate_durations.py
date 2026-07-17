"""Validate shot durations against total limits + dialogue-content timing."""
import json, os, sys, re
if not os.environ.get("PYTHONPYCACHEPREFIX") and not getattr(sys, "pycache_prefix", None):
    sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))
from pycache_policy import block_source_pycache_until_run_dir, ensure_pycache_prefix_from_path

block_source_pycache_until_run_dir()
from shot_semantics import is_true_non_action_subshot

# Chinese dialogue delivery speed: chars/sec
DIALOGUE_CHARS_PER_SEC = 4.5
PAUSE_PER_PUNCTUATION = 0.3     # seconds per ,/、/；
PAUSE_PER_SENTENCE_END = 0.5     # seconds per 。/！/？/……
ACTION_TIME_BASE = 2.0           # default action time per subshot (seconds)

# Emotion-based speed adjustment (multiplier on base 4.5 chars/sec)
EMOTION_SPEED = {
    "激动": 1.2, "兴奋": 1.2, "慌乱": 1.1, "炸裂": 1.2,
    "崩溃": 1.1, "热情": 1.1, "愉快": 1.1, "急切": 1.2,
    "催促": 1.2,
    "迟疑": 0.85, "压抑": 0.85, "阴沉": 0.85, "低落": 0.8,
    "委屈": 0.85, "嘲讽": 0.8, "威胁": 0.8, "冷淡": 0.85,
    "忰忐": 0.85, "隐忍": 0.85, "暗沉": 0.85, "失落": 0.85,
    "无奈": 0.9, "无语": 0.9, "吐槽": 0.95,
}
DEFAULT_SPEED_FACTOR = 1.0


# Emotion-based speed adjustment (multiplier on base 4.5 chars/sec)
EMOTION_SPEED = {
    "激动": 1.2, "兴奋": 1.2, "慌乱": 1.1, "炸裂": 1.2,
    "崩溃": 1.1, "热情": 1.1, "愉快": 1.1, "急切": 1.2,
    "催促": 1.2,
    "迟疑": 0.85, "压抑": 0.85, "阴沉": 0.85, "低落": 0.8,
    "委屈": 0.85, "嘲讽": 0.8, "威胁": 0.8, "冷淡": 0.85,
    "忰忐": 0.85, "隐忍": 0.85, "暗沉": 0.85, "失落": 0.85,
    "无奈": 0.9, "无语": 0.9, "吐槽": 0.95,
}
DEFAULT_SPEED_FACTOR = 1.0


PUNCTUATION_CHARS = set(",，、；")
SENTENCE_ENDS = set("。！？…\u2026")


def _estimate_dialogue_seconds(dialogue_text, emotion_tone=""):
    """Calculate minimum time needed to deliver a line of dialogue naturally.
    Accounts for: character count at speaking rate + punctuation pauses + sentence-end dwell."""
    if not dialogue_text:
        return 0.0
    # Strip speaker prefix like "角色A：" to count only spoken content
    text = re.sub(r"^[^：]+[：]\s*", "", dialogue_text)
    if not text:
        text = dialogue_text
    chars = len(text)
    punct_pauses = sum(1 for c in text if c in PUNCTUATION_CHARS)
    sent_pauses = sum(1 for c in text if c in SENTENCE_ENDS)
    speed_factor = DEFAULT_SPEED_FACTOR
    if emotion_tone:
        for keyword in EMOTION_SPEED:
            if keyword in emotion_tone:
                speed_factor = EMOTION_SPEED[keyword]
                break
    effective_speed = DIALOGUE_CHARS_PER_SEC * speed_factor
    duration = chars / effective_speed + punct_pauses * PAUSE_PER_PUNCTUATION + sent_pauses * PAUSE_PER_SENTENCE_END
    return max(round(duration, 1), 0.5)


def _estimate_action_seconds(base_action, subshot=None):
    """Estimate minimum time for action performance based on keywords."""
    if subshot is not None and is_true_non_action_subshot(subshot):
        return 0.0
    if not base_action:
        return ACTION_TIME_BASE
    # Key action indicators and their estimated times
    action_estimates = {
        "打开": 1.5, "开": 1.0, "取": 1.0, "拿": 0.8, "放": 0.8,
        "叠": 2.0, "折": 1.5, "装": 1.0, "拉": 1.2, "背": 2.0,
        "走": 1.5, "跑": 1.0, "站": 1.0, "坐": 1.5, "蹲": 1.5,
        "推": 1.2, "关": 1.0, "捡": 1.5, "翻": 1.5, "系": 2.0,
        "穿": 2.0, "脱": 1.5, "擦": 1.5, "写": 2.0, "看": 0.8,
        "抱": 1.5, "举": 1.5, "搬": 2.5, "抬": 2.0,
    }
    total = ACTION_TIME_BASE
    action_count = 0
    for word, secs in action_estimates.items():
        if word in base_action:
            total += secs
            action_count += 1
    # Cap at reasonable max for a single subshot
    return min(total, 8.0)


def validate(sp_path, max_per_shot=15, max_total=600, project_config_path=None):
    """Validate shot durations + dialogue-content timing.

    Args:
        sp_path: Path to shot_plan.json
        max_per_shot: Max seconds per individual shot
        max_total: Max total seconds for all shots
        project_config_path: Optional path to project_config.json

    Returns:
        list of issues [(shot_id, field, value, expected)]
    """
    ensure_pycache_prefix_from_path(sp_path)

    if project_config_path and os.path.exists(project_config_path):
        try:
            with open(project_config_path, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
            m = cfg.get("max_shot_duration")
            if m:
                max_per_shot = int(m)
        except Exception:
            pass

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
    dialogue_map = data.get("dialogue_map", {})

    for shot in shots:
        sid = shot.get("shot_id", "?")
        subshots = shot.get("subshots", [])
        shot_dur = 0.0

        for ss in subshots:
            ssid = ss.get("subshot_id", "?")
            d = ss.get("duration", 0)

            # Basic duration > 0 check
            if not isinstance(d, (int, float)) or d <= 0:
                issues.append(("%s/%s" % (sid, ssid), "duration", d, ">0"))
                shot_dur += max(float(d) if isinstance(d, (int, float)) else 0, 0)
                continue

            shot_dur += d

            # === Dialogue-content timing check ===
            dialogue_refs = ss.get("dialogue_refs", [])
            total_dialogue_secs = 0.0
            emotion_tone = ss.get("emotion_tone", "")
            for ref in dialogue_refs:
                dia_text = dialogue_map.get(ref, "")
                if dia_text:
                    total_dialogue_secs += _estimate_dialogue_seconds(dia_text, emotion_tone)

            action_secs = _estimate_action_seconds(ss.get("base_action", ""), ss)
            needed_secs = max(total_dialogue_secs, action_secs) + 0.5  # per SKILL.md: max(dialogue,action)+reaction_blank

            if total_dialogue_secs > 0 and d + 0.001 < needed_secs:
                issues.append(("%s/%s" % (sid, ssid), "duration_too_short",
                    d, ">=%.1f (dialogue %.1fs + action %.1fs)" % (
                        needed_secs, total_dialogue_secs, action_secs)))

        if shot_dur > max_per_shot:
            issues.append((sid, "shot_duration", shot_dur, "<=%d" % max_per_shot))
        total_dur += shot_dur

    if total_dur > max_total:
        issues.append(("TOTAL", "total_duration", total_dur, "<=%d" % max_total))

    if issues:
        print("[DURATION] %d issue(s)" % len(issues))
    else:
        print("[DURATION] PASS - %.1fs total" % total_dur)

    return issues


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "shot_plan.json"
    pcfg = sys.argv[2] if len(sys.argv) > 2 else None
    issues = validate(path, project_config_path=pcfg)
    print(json.dumps(issues, ensure_ascii=False, indent=2))
