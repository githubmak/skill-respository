#!/usr/bin/env python3
"""Compatibility entry point for deterministic Master output validation."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from validate_deterministic_package import validate_package
from incremental_validation import build_repair_report


def validate_composer_output(
    path, run_dir=None, report_path=None, allow_incomplete=False, selected_shot_ids=None
):
    scaffold = _load_scaffold_for_batch(path, run_dir)
    # Existing immutable packets created before --allow-incomplete was added
    # still identify their batch output through an exact scaffold link.
    effective_allow_incomplete = bool(allow_incomplete or scaffold)
    result = validate_package(
        path,
        run_dir=run_dir,
        report_path=report_path,
        allow_incomplete=effective_allow_incomplete,
        selected_shot_ids=selected_shot_ids,
        allow_batch_envelope=True,
    )
    package = _load_json(path)
    shots = package.get("shots", []) if isinstance(package, dict) else []
    selected = {str(value) for value in selected_shot_ids or [] if str(value).strip()}
    # A worker batch is intentionally incomplete relative to the global plan,
    # but it must still contain exactly the shots locked by its own scaffold.
    batch_scope = bool(scaffold) and not (allow_incomplete and selected)
    if batch_scope:
        actual_ids = {
            str(item.get("shot_id", "") or item.get("subshot_id", ""))
            for item in shots if isinstance(item, dict)
        }
        for missing in sorted(set(scaffold) - actual_ids):
            result["issues"].append("%s: BATCH_COVERAGE missing required main shot" % missing)
        for unexpected in sorted(actual_ids - set(scaffold)):
            result["issues"].append("%s: BATCH_COVERAGE contains an unexpected main shot" % unexpected)
    repair_rows = list(shots) if isinstance(shots, list) else []
    if batch_scope:
        for shot_id, row in scaffold.items():
            if not any(
                isinstance(item, dict)
                and str(item.get("shot_id", "") or item.get("subshot_id", "")) == shot_id
                for item in repair_rows
            ):
                repair_rows.append(row)
    repair = build_repair_report(result["issues"], repair_rows)
    result.update(repair)
    result["pass"] = not result["issues"]
    if report_path:
        os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
    label = "PASS" if result["pass"] else "FAIL"
    print("[DETERMINISTIC MASTER VALIDATION] %s - %d shot(s)" % (label, result["shot_count"]))
    for issue in result["issues"][:80]:
        print("  - " + issue)
    return 0 if result["pass"] else 1


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            value = json.load(handle)
            return value if isinstance(value, dict) else {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _load_scaffold_for_batch(batch_path, run_dir=None):
    """Read the packet-linked scaffold without interpreting creative fields."""
    candidates = []
    directory = os.path.dirname(os.path.abspath(batch_path))
    candidates.extend(
        os.path.join(directory, name)
        for name in os.listdir(directory) if name.endswith("_scaffold.json")
    ) if os.path.isdir(directory) else None
    if run_dir:
        dispatch_dir = os.path.join(run_dir, ".cache", "dispatch")
        if os.path.isdir(dispatch_dir):
            for name in os.listdir(dispatch_dir):
                if not name.endswith("_packet.json"):
                    continue
                packet = _load_json(os.path.join(dispatch_dir, name))
                if os.path.abspath(str(packet.get("_batch_output_path", "") or "")) != os.path.abspath(batch_path):
                    continue
                linked = str(packet.get("composer_scaffold_path", "") or "")
                if linked:
                    candidates.insert(0, linked)
                break
    for candidate in list(dict.fromkeys(candidates)):
        try:
            with open(candidate, "r", encoding="utf-8-sig") as handle:
                data = json.load(handle)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        shots = data.get("shots", []) if isinstance(data, dict) else []
        return {
            str(item.get("subshot_id", "") or item.get("shot_id", "")): item
            for item in shots if isinstance(item, dict)
        }
    return {}


if __name__ == "__main__":
    args = sys.argv[1:]
    run_dir = None
    allow_incomplete = False
    selected_shot_ids = []
    if "--run-dir" in args:
        index = args.index("--run-dir")
        run_dir = args[index + 1]
        del args[index:index + 2]
    if "--allow-incomplete" in args:
        args.remove("--allow-incomplete")
        allow_incomplete = True
    while "--shot-id" in args:
        index = args.index("--shot-id")
        selected_shot_ids.append(args[index + 1])
        del args[index:index + 2]
    if len(args) != 1:
        raise SystemExit(
            "usage: validate_composer_output.py <package.json> [--run-dir <run_dir>] "
            "[--allow-incomplete] [--shot-id <shot_id> ...]"
        )
    raise SystemExit(validate_composer_output(
        args[0], run_dir, allow_incomplete=allow_incomplete,
        selected_shot_ids=selected_shot_ids or None,
    ))
