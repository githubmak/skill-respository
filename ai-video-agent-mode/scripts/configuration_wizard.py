#!/usr/bin/env python3
"""Persist explicitly confirmed Phase-0 configuration.

Interactive setup records one ordered answer group at a time. Batch setup
accepts all required fields atomically, but only when the caller explicitly
supplies every field; template defaults never count as confirmation.
"""

import argparse
import copy
import datetime as dt
import json
import os
import sys

from resolve_run_mode import (
    BASE_FIELDS, CONFIG_VERSION, FIELD_PROMPTS, _get, _value_is_present,
    config_issues, confirmation_snapshot, confirmation_snapshot_hash, next_fields,
)


ROOT = os.path.dirname(os.path.dirname(__file__))
TEMPLATE_PATH = os.path.join(ROOT, "references", "project_config.template.json")
MODE_ALIASES = {
    "文本": "t2v", "文本生成视频": "t2v", "文生视频": "t2v", "t2v": "t2v",
}
PLATFORM_ALIASES = {
    "jimeng": "即梦", "seedance": "即梦", "即梦": "即梦",
}
SEEDANCE_TARGET_ALIASES = {
    "自动": "auto", "兼容": "auto", "auto": "auto",
    "2": "2.0", "2.0": "2.0", "seedance2.0": "2.0", "seedance 2.0": "2.0",
    "2.5": "2.5", "seedance2.5": "2.5", "seedance 2.5": "2.5",
    "both": "both", "双版本": "both", "两个": "both", "2.0+2.5": "both",
}


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _write(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _config_path(run_dir):
    return os.path.join(run_dir, "project_config.json")


def _inside_base(run_dir, export_base):
    try:
        return os.path.commonpath([os.path.abspath(run_dir), os.path.abspath(export_base)]) == os.path.abspath(export_base)
    except ValueError:
        return False


def _confirmation(config):
    value = config.get("confirmation")
    if not isinstance(value, dict):
        value = {}
        config["confirmation"] = value
    value["config_version"] = CONFIG_VERSION
    value.setdefault("confirmed_at", "")
    value.setdefault("confirmed_fields", [])
    value.setdefault("confirmed_values", {})
    value.setdefault("confirmed_values_sha256", "")
    if not isinstance(value["confirmed_fields"], list):
        value["confirmed_fields"] = []
    return value


def _set(config, dotted, value):
    parent = config
    parts = dotted.split(".")
    for part in parts[:-1]:
        child = parent.get(part)
        if not isinstance(child, dict):
            child = {}
            parent[part] = child
        parent = child
    parent[parts[-1]] = value


def _deep_merge(base, override):
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _normalize_value(field, value):
    if field == "generation_control.mode" and isinstance(value, str):
        text = value.strip()
        return MODE_ALIASES.get(text.lower(), MODE_ALIASES.get(text, text.lower()))
    if field == "target_platform" and isinstance(value, str):
        text = value.strip()
        return PLATFORM_ALIASES.get(text.lower(), PLATFORM_ALIASES.get(text, text))
    if field == "seedance_target" and isinstance(value, str):
        text = value.strip()
        return SEEDANCE_TARGET_ALIASES.get(text.lower(), SEEDANCE_TARGET_ALIASES.get(text, text.lower()))
    return value


def _next(config):
    fields = next_fields(config)
    return fields[0] if fields else None


def _status(config, run_dir):
    fields = next_fields(config)
    if fields:
        return {
            "pass": False,
            "action": "needs_user_confirm",
            "next_fields": fields,
            "messages": [FIELD_PROMPTS[field] for field in fields],
            "maximum_fields_this_turn": 2,
            "remaining_fields": [field for field in BASE_FIELDS if field not in _confirmation(config)["confirmed_fields"]],
        }
    issues = config_issues(config, run_dir=run_dir, require_confirmation=False)
    if issues:
        return {"pass": False, "action": "blocked", "issues": issues}
    confirmation = _confirmation(config)
    if not confirmation.get("confirmed_at"):
        # generation_control.mode is a fixed T2V contract field rather than a
        # separate Wizard question. Completing setup confirms that fixed value.
        confirmation["confirmed_fields"] = list(BASE_FIELDS)
        snapshot = confirmation_snapshot(config)
        confirmation["confirmed_values"] = snapshot
        confirmation["confirmed_values_sha256"] = confirmation_snapshot_hash(snapshot)
        confirmation["confirmed_at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        _write(_config_path(run_dir), config)
    return {"pass": True, "action": "confirmed", "confirmed_fields": list(BASE_FIELDS)}


def start(run_dir, export_base):
    run_dir = os.path.abspath(run_dir)
    export_base = os.path.abspath(export_base)
    if not _inside_base(run_dir, export_base):
        raise ValueError("run_dir must be created under the user-confirmed export_base")
    if os.path.exists(run_dir) and os.listdir(run_dir):
        raise ValueError("run_dir must be new and empty; do not clear or reuse an old run")
    os.makedirs(run_dir, exist_ok=True)
    config = copy.deepcopy(_load(TEMPLATE_PATH))
    config["export_base"] = export_base
    confirmation = _confirmation(config)
    confirmation["confirmed_fields"] = ["export_base"]
    _write(_config_path(run_dir), config)
    return _status(config, run_dir)


def answer(run_dir, fields, raw_values):
    run_dir = os.path.abspath(run_dir)
    path = _config_path(run_dir)
    if not os.path.exists(path):
        raise ValueError("start the wizard with the export_base before recording later fields")
    config = _load(path)
    expected = next_fields(config)
    if len(fields) != len(raw_values) or not fields or len(fields) > 2:
        raise ValueError("submit one or two field/value pairs")
    if fields != expected[:len(fields)]:
        raise ValueError("submit the next fields in order: %s" % ", ".join(expected))
    confirmation = _confirmation(config)
    if confirmation.get("confirmed_at"):
        # A changed post-confirmation value reopens only its current 1-2 field
        # group. Do not let the old snapshot silently authorize the new value.
        confirmation["confirmed_at"] = ""
        confirmation["confirmed_values"] = {}
        confirmation["confirmed_values_sha256"] = ""
        confirmation["confirmed_fields"] = [
            item for item in confirmation["confirmed_fields"] if item not in expected
        ]
    for field, raw_value in zip(fields, raw_values):
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        value = _normalize_value(field, value)
        _set(config, field, value)
        if not _value_is_present(field, value):
            raise ValueError("invalid value for %s" % field)
        if field not in confirmation["confirmed_fields"]:
            confirmation["confirmed_fields"].append(field)
    _write(path, config)
    return _status(config, run_dir)


def confirm_all(run_dir, config_path):
    """Atomically confirm a complete caller-supplied configuration.

    The input file must explicitly contain every BASE_FIELDS value. Existing
    confirmation metadata is discarded so a copied template or stale run
    cannot authorize itself.
    """
    run_dir = os.path.abspath(run_dir)
    config_path = os.path.abspath(config_path)
    supplied = _load(config_path)
    if not isinstance(supplied, dict):
        raise ValueError("batch config must contain a JSON object")

    for field in BASE_FIELDS:
        value = _normalize_value(field, _get(supplied, field))
        _set(supplied, field, value)
    missing = [field for field in BASE_FIELDS if not _value_is_present(field, _get(supplied, field))]
    if missing:
        raise ValueError("batch config must explicitly provide: %s" % ", ".join(missing))

    export_base = os.path.abspath(str(supplied["export_base"]).strip())
    supplied["export_base"] = export_base
    if not _inside_base(run_dir, export_base):
        raise ValueError("run_dir must be created under the user-confirmed export_base")
    if os.path.exists(run_dir) and os.listdir(run_dir):
        raise ValueError("run_dir must be new and empty; do not clear or reuse an old run")

    supplied.pop("confirmation", None)
    config = _deep_merge(_load(TEMPLATE_PATH), supplied)
    config["confirmation"] = copy.deepcopy(_load(TEMPLATE_PATH)["confirmation"])
    issues = config_issues(config, run_dir=run_dir, require_confirmation=False)
    if issues:
        raise ValueError("invalid batch config: %s" % ", ".join(issues))

    confirmation = _confirmation(config)
    confirmation["confirmed_fields"] = list(BASE_FIELDS)
    snapshot = confirmation_snapshot(config)
    confirmation["confirmed_values"] = snapshot
    confirmation["confirmed_values_sha256"] = confirmation_snapshot_hash(snapshot)
    confirmation["confirmed_at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    os.makedirs(run_dir, exist_ok=True)
    _write(_config_path(run_dir), config)
    return {
        "pass": True,
        "action": "confirmed",
        "setup_mode": "high_quality_fast",
        "confirmed_fields": list(BASE_FIELDS),
        "config_path": _config_path(run_dir),
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    start_parser = sub.add_parser("start")
    start_parser.add_argument("--run-dir", required=True)
    start_parser.add_argument("--export-base", required=True)
    answer_parser = sub.add_parser("answer")
    answer_parser.add_argument("--run-dir", required=True)
    answer_parser.add_argument("--field", choices=BASE_FIELDS, action="append", required=True)
    answer_parser.add_argument("--value", action="append", required=True)
    status_parser = sub.add_parser("status")
    status_parser.add_argument("--run-dir", required=True)
    batch_parser = sub.add_parser("batch")
    batch_parser.add_argument("--run-dir", required=True)
    batch_parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "start":
            result = start(args.run_dir, args.export_base)
        elif args.command == "answer":
            result = answer(args.run_dir, args.field, args.value)
        elif args.command == "status":
            result = _status(_load(_config_path(args.run_dir)), os.path.abspath(args.run_dir))
        else:
            result = confirm_all(args.run_dir, args.config)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"pass": False, "action": "blocked", "issues": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
