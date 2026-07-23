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
DEFAULT_MAX_STATIC_SECONDS = 6.0
LONG_DURATION_RATIONALES = {
    "continuous_dialogue",
    "continuous_interaction",
    "continuous_action",
    "sustained_reveal",
}

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


def _long_duration_issues(subshot, duration, dialogue_secs, action_secs, max_static_seconds):
    """Reject long clips whose duration is supported only by atmosphere or a hold.

    A long take remains available, but the Phase 1 plan must state the causal
    reason and the visible beats that consume its time. This catches the common
    case where a single glance or a group freeze is stretched to 10-15 seconds.
    """
    if duration <= max_static_seconds + 1e-6:
        return []

    design = subshot.get("duration_design", {})
    design = design if isinstance(design, dict) else {}
    rationale = str(design.get("duration_rationale", "") or "").strip()
    beats = design.get("dramatic_beats", [])
    if rationale not in LONG_DURATION_RATIONALES:
        return [
            "duration_overfilled",
            duration,
            "<=%.1fs, or duration_rationale in %s with concrete dramatic_beats"
            % (max_static_seconds, "/".join(sorted(LONG_DURATION_RATIONALES))),
        ]
    if not isinstance(beats, list) or len(beats) < 2 or any(not str(beat).strip() for beat in beats):
        return [
            "duration_beats_missing",
            duration,
            "long shot needs at least 2 ordered dramatic_beats; atmosphere/hold/residue alone is insufficient",
        ]

    if rationale == "continuous_dialogue" and dialogue_secs < 3.0:
        return ["duration_rationale_unsupported", rationale, "continuous_dialogue needs >=3.0s spoken content"]
    if rationale == "continuous_interaction" and (
        len(subshot.get("dialogue_refs", []) or []) < 2 or dialogue_secs < 3.0
    ):
        return ["duration_rationale_unsupported", rationale, "continuous_interaction needs >=2 dialogue turns and >=3.0s spoken content"]
    if rationale == "continuous_action" and len(beats) < 2:
        return ["duration_rationale_unsupported", rationale, "continuous_action needs multiple visible action beats"]
    if duration > 10.0:
        if len(beats) < 3:
            return ["duration_beats_missing", duration, ">10s needs at least 3 ordered dramatic_beats"]
        if rationale == "sustained_reveal" and action_secs < 4.0:
            return ["duration_rationale_unsupported", rationale, "sustained_reveal needs an on-screen reveal process, not a static reaction"]
    return []


def _duration_design_issues(subshot, duration, max_per_shot):
    design = subshot.get("duration_design")
    if not isinstance(design, dict):
        return [("duration_design", "missing", "required object")]
    issues = []
    if design.get("duration_strategy") != "pack_toward_limit":
        issues.append(("duration_strategy", design.get("duration_strategy"), "pack_toward_limit"))
    justified = design.get("justified_content_duration")
    if not isinstance(justified, (int, float)) or isinstance(justified, bool) or justified <= 0:
        issues.append(("justified_content_duration", justified, ">0"))
    elif abs(float(justified) - float(duration)) > 0.5:
        issues.append(("duration_padding", duration - float(justified), "<=0.5s unsubstantiated time"))
    utilization = design.get("utilization_ratio")
    expected_ratio = float(duration) / float(max_per_shot) if max_per_shot else 0
    if not isinstance(utilization, (int, float)) or isinstance(utilization, bool):
        issues.append(("utilization_ratio", utilization, "numeric duration/max_shot_duration"))
    elif abs(float(utilization) - expected_ratio) > 0.02:
        issues.append(("utilization_ratio", utilization, "%.3f" % expected_ratio))
    beats = design.get("dramatic_beats")
    if not isinstance(beats, list) or not beats or any(not str(beat).strip() for beat in beats):
        issues.append(("dramatic_beats", beats, "non-empty ordered beat IDs"))
    return issues


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

    max_static_seconds = DEFAULT_MAX_STATIC_SECONDS
    if project_config_path and os.path.exists(project_config_path):
        try:
            with open(project_config_path, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
            m = cfg.get("max_shot_duration")
            if m:
                max_per_shot = float(m)
            mt = cfg.get("max_total_duration")
            if mt:
                max_total = float(mt)
            static_limit = cfg.get("max_static_shot_duration")
            if isinstance(static_limit, (int, float)) and not isinstance(static_limit, bool) and static_limit >= 2.5:
                max_static_seconds = float(static_limit)
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

            for field, value, expected_value in _duration_design_issues(ss, d, max_per_shot):
                issues.append(("%s/%s" % (sid, ssid), field, value, expected_value))

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

            long_issue = _long_duration_issues(
                ss, d, total_dialogue_secs, action_secs, max_static_seconds
            )
            if long_issue:
                field, value, expected = long_issue
                issues.append(("%s/%s" % (sid, ssid), field, value, expected))

        if shot_dur > max_per_shot:
            issues.append((sid, "shot_duration", shot_dur, "<=%g" % max_per_shot))
        total_dur += shot_dur

    if total_dur > max_total:
        issues.append(("TOTAL", "total_duration", total_dur, "<=%g" % max_total))

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
