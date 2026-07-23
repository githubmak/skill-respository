#!/usr/bin/env python3
"""Resolve initialization and configuration reuse before a pipeline route runs.

This is deliberately deterministic.  A caller must not infer whether an old
``project_config.json`` is safe to reuse from the presence of a run directory.
"""

import argparse
import hashlib
import json
import os
import sys


CONFIG_VERSION = 2
BASE_FIELDS = (
    "export_base",
    "canvas",
    "visual_style",
    "max_shot_duration",
    "target_platform",
    "generation_control.mode",
    "generation_control.audio_enabled",
    "storyboard_grid.enabled",
)

# Keep user interaction light while preserving a deterministic order.  The
# export base stands alone because no run artifacts may exist before it is
# confirmed; all later turns ask for at most two fields.
CONFIG_GROUPS = (
    ("export_base",),
    ("canvas", "visual_style"),
    ("max_shot_duration", "target_platform"),
    ("generation_control.audio_enabled", "storyboard_grid.enabled"),
)

DEFAULT_INTENTS = {
    "full": "new",
    "audit": "audit",
    "export": "reexport",
    "compose": "resume",
    "single-repair": "resume",
}

FIELD_PROMPTS = {
    "export_base": "请输入本次项目的输出目录（绝对路径）。",
    "canvas": "请输入画幅，例如 16:9 或 9:16。",
    "visual_style": "请输入本项目的视觉风格描述。",
    "max_shot_duration": "请输入单条生成片段的最大时长（秒，不能超过平台能力）。",
    "target_platform": "请输入目标生成平台，例如 即梦、可灵、Runway 或 Veo。",
    "generation_control.audio_enabled": "请输入是否启用原生音频：true 或 false。",
    "storyboard_grid.enabled": "请输入是否生成自动九宫格剧情包：true 或 false。",
}


def _load_config(run_dir):
    path = os.path.join(run_dir, "project_config.json")
    if not os.path.exists(path):
        return None, "project_config.json is missing"
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        return None, "project_config.json cannot be parsed: %s" % exc
    if not isinstance(value, dict):
        return None, "project_config.json must contain an object"
    return value, ""


def _get(config, dotted):
    value = config
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _value_is_present(field, value):
    if field in ("generation_control.audio_enabled", "storyboard_grid.enabled"):
        return isinstance(value, bool)
    if field == "max_shot_duration":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0
    return isinstance(value, str) and bool(value.strip())


def confirmation_snapshot(config):
    """Capture exactly the Phase-0 values the user approved."""
    return {field: _get(config, field) for field in BASE_FIELDS}


def confirmation_snapshot_hash(snapshot):
    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _snapshot_field_matches(config, snapshot, field):
    return isinstance(snapshot, dict) and field in snapshot and snapshot[field] == _get(config, field)


def config_issues(config, run_dir=None, require_confirmation=True):
    """Return stable, user-actionable configuration issues.

    Template defaults never count as user confirmation.  The creator must add
    confirmation metadata only after the user has accepted the filled values.
    """
    if not isinstance(config, dict):
        return ["project_config.json is missing or invalid"]
    issues = []
    for field in BASE_FIELDS:
        if not _value_is_present(field, _get(config, field)):
            issues.append(field)
    prompt_limits = config.get("prompt_limits", {})
    if not isinstance(prompt_limits, dict):
        issues.append("prompt_limits")
    else:
        hard_max_chars = prompt_limits.get("hard_max_chars")
        if hard_max_chars is not None and (
            not isinstance(hard_max_chars, int)
            or isinstance(hard_max_chars, bool)
            or hard_max_chars <= 0
        ):
            issues.append("prompt_limits.hard_max_chars")
    if run_dir and _value_is_present("export_base", config.get("export_base")):
        export_base = os.path.abspath(str(config["export_base"]).strip())
        run_abs = os.path.abspath(run_dir)
        try:
            inside_base = os.path.commonpath([run_abs, export_base]) == export_base
        except ValueError:
            inside_base = False
        if not inside_base:
            issues.append("export_base must contain run_dir")
    if not require_confirmation:
        return issues

    confirmation = config.get("confirmation")
    if not isinstance(confirmation, dict):
        return issues + ["confirmation"]
    if confirmation.get("config_version") != CONFIG_VERSION:
        issues.append("confirmation.config_version")
    if not isinstance(confirmation.get("confirmed_at"), str) or not confirmation["confirmed_at"].strip():
        issues.append("confirmation.confirmed_at")
    fields = confirmation.get("confirmed_fields")
    if not isinstance(fields, list):
        issues.append("confirmation.confirmed_fields")
    else:
        confirmed = set(fields)
        for field in BASE_FIELDS:
            if field not in confirmed:
                issues.append("confirmation.%s" % field)
    if confirmation.get("confirmed_at"):
        snapshot = confirmation.get("confirmed_values")
        if not isinstance(snapshot, dict):
            issues.append("confirmation.confirmed_values")
        else:
            for field in BASE_FIELDS:
                if not _snapshot_field_matches(config, snapshot, field):
                    issues.append("confirmation.value_mismatch.%s" % field)
            expected_hash = confirmation_snapshot_hash(snapshot)
            if confirmation.get("confirmed_values_sha256") != expected_hash:
                issues.append("confirmation.confirmed_values_sha256")
    return issues


def _has_prior_run_artifacts(run_dir):
    if not os.path.isdir(run_dir):
        return False
    for name in ("project_config.json", ".cache", "pipeline_state.json"):
        if os.path.exists(os.path.join(run_dir, name)):
            return True
    return False


def _next_field(config):
    confirmation = config.get("confirmation", {}) if isinstance(config, dict) else {}
    confirmed = set(confirmation.get("confirmed_fields", [])) if isinstance(confirmation, dict) else set()
    for field in BASE_FIELDS:
        if field not in confirmed or not _value_is_present(field, _get(config, field)):
            return field
    return None


def next_fields(config):
    """Return the next ordered confirmation group, containing at most two fields."""
    confirmation = config.get("confirmation", {}) if isinstance(config, dict) else {}
    confirmed = set(confirmation.get("confirmed_fields", [])) if isinstance(confirmation, dict) else set()
    snapshot = confirmation.get("confirmed_values") if isinstance(confirmation, dict) else None
    snapshot_required = bool(confirmation.get("confirmed_at")) if isinstance(confirmation, dict) else False
    for group in CONFIG_GROUPS:
        remaining = [
            field for field in group
            if field not in confirmed
            or not _value_is_present(field, _get(config, field))
            or (snapshot_required and not _snapshot_field_matches(config, snapshot, field))
        ]
        if remaining:
            return remaining
    return []


def _question_payload(config, missing):
    fields = next_fields(config if isinstance(config, dict) else {}) or [BASE_FIELDS[0]]
    return {
        "scope": "full_setup",
        "next_fields": fields,
        "remaining_fields": [item for item in BASE_FIELDS if item in fields or item not in (
            config.get("confirmation", {}).get("confirmed_fields", []) if isinstance(config, dict) else []
        )],
        "missing_or_unconfirmed": missing,
        "messages": [FIELD_PROMPTS[field] for field in fields],
        "sequential": True,
        "maximum_fields_this_turn": 2,
    }


def resolve(route, run_dir, intent=None):
    """Return one authoritative route/init decision without modifying files."""
    if route not in DEFAULT_INTENTS:
        raise ValueError("unknown route: %s" % route)
    intent = intent or DEFAULT_INTENTS[route]
    if intent not in ("new", "resume", "audit", "reexport"):
        raise ValueError("intent must be new, resume, audit, or reexport")
    result = {
        "pass": False,
        "route": route,
        "intent": intent,
        "run_dir": os.path.abspath(run_dir),
        "reuse_policy": "",
        "blocking": [],
        "requires_user_confirm": False,
        "questions": [],
    }

    # A fresh manual full run must never silently consume an earlier run.  Keep
    # the old cache as provenance; select a unique run directory instead.
    if route == "full" and intent == "new":
        result["reuse_policy"] = "fresh_run_only"
        if _has_prior_run_artifacts(run_dir):
            result["blocking"].append(
                "full/new requires a new empty run_dir; preserve the old run for audit instead of clearing or reusing its cache"
            )
            return result
        result["requires_user_confirm"] = True
        result["questions"].append(_question_payload({}, list(BASE_FIELDS)))
        return result

    # Read-only audit deliberately does not turn a review request into a setup
    # interview.  Its package requirement is checked by route_task.py.
    if route == "audit":
        result["pass"] = True
        result["reuse_policy"] = "read_only_existing_artifact"
        return result

    config, error = _load_config(run_dir)
    if error:
        if route == "full" and intent == "resume":
            result["requires_user_confirm"] = True
            result["questions"].append(_question_payload({}, list(BASE_FIELDS)))
        else:
            result["blocking"].append("%s requires an already confirmed project_config.json" % route)
        return result

    issues = config_issues(config, run_dir=run_dir, require_confirmation=True)
    if issues:
        if route == "full" and intent == "resume":
            result["requires_user_confirm"] = True
            result["questions"].append(_question_payload(config, issues))
        else:
            result["blocking"].append(
                "%s cannot reuse an unconfirmed configuration: %s" % (route, ", ".join(issues))
            )
        return result

    result["pass"] = True
    result["reuse_policy"] = "confirmed_configuration_reuse"
    if route == "export" or intent == "reexport":
        result["export_destination_confirmation_required"] = True
        result["export_confirmation_message"] = (
            "Confirm the Markdown delivery path for this export. Reuse the confirmed "
            "project configuration, but do not infer a new delivery filename."
        )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("route", choices=sorted(DEFAULT_INTENTS))
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--intent", choices=("new", "resume", "audit", "reexport"))
    args = parser.parse_args(argv)
    try:
        outcome = resolve(args.route, args.run_dir, args.intent)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        outcome = {"pass": False, "blocking": [str(exc)]}
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    return 0 if outcome.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
