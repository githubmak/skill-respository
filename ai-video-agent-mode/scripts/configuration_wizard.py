#!/usr/bin/env python3
"""Persist one explicitly confirmed Phase-0 answer at a time.

The wizard is intentionally stateful only after the user has supplied an
export base.  It prevents a caller from treating template defaults as a bulk
confirmation and makes the next required question deterministic.
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
    "图片": "i2v", "图片生成视频": "i2v", "图生视频": "i2v", "i2v": "i2v",
    "参考视频": "r2v", "参考视频生成视频": "r2v", "视频生成视频": "r2v", "r2v": "r2v",
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
        if field == "generation_control.mode" and isinstance(value, str):
            value = MODE_ALIASES.get(value.strip().lower(), MODE_ALIASES.get(value.strip(), value))
        _set(config, field, value)
        if not _value_is_present(field, value):
            raise ValueError("invalid value for %s" % field)
        if field not in confirmation["confirmed_fields"]:
            confirmation["confirmed_fields"].append(field)
    _write(path, config)
    return _status(config, run_dir)


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
    args = parser.parse_args(argv)
    try:
        if args.command == "start":
            result = start(args.run_dir, args.export_base)
        elif args.command == "answer":
            result = answer(args.run_dir, args.field, args.value)
        else:
            result = _status(_load(_config_path(args.run_dir)), os.path.abspath(args.run_dir))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"pass": False, "action": "blocked", "issues": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
