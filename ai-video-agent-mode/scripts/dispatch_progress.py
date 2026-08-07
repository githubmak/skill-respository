"""Deterministic content-progress evidence for one worker checkpoint."""

import json
import os


ITEM_KEY_BY_PHASE = {
    "master_production": "shots",
    "editor_pass2": "windows",
}


def inspect_output(packet):
    """Return mechanical evidence from the packet's current batch output."""
    path = str(packet.get("_batch_output_path", "") or "")
    evidence = {
        "output_exists": False,
        "output_bytes": 0,
        "output_mtime": None,
        "completed_item_count": 0,
        "output_parseable": False,
    }
    if not path or not os.path.isfile(path):
        return evidence
    evidence["output_exists"] = True
    evidence["output_bytes"] = os.path.getsize(path)
    evidence["output_mtime"] = os.path.getmtime(path)
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError, UnicodeError):
        return evidence
    key = ITEM_KEY_BY_PHASE.get(str(packet.get("phase", "") or ""))
    rows = payload.get(key) if isinstance(payload, dict) and key else None
    if isinstance(rows, list):
        evidence["output_parseable"] = True
        evidence["completed_item_count"] = len(rows)
    return evidence


def apply_progress(entry, progress, observed_at):
    """Update maxima and timestamps only when parseable content grows."""
    if not isinstance(entry, dict) or not isinstance(progress, dict):
        return False
    current_bytes = _nonnegative_int(progress.get("output_bytes"))
    current_items = _nonnegative_int(progress.get("completed_item_count"))
    previous_bytes = _nonnegative_int(entry.get("output_bytes"))
    previous_items = _nonnegative_int(entry.get("completed_item_count"))
    parseable = progress.get("output_parseable") is True
    grew = parseable and current_items > 0 and (
        current_items > previous_items or current_bytes > previous_bytes
    )
    entry["output_exists"] = progress.get("output_exists") is True
    entry["output_mtime"] = progress.get("output_mtime")
    entry["output_bytes"] = max(previous_bytes, current_bytes)
    entry["completed_item_count"] = max(previous_items, current_items)
    if grew:
        entry["progress_count"] = _nonnegative_int(entry.get("progress_count")) + 1
        if not isinstance(entry.get("first_progress_at"), (int, float)):
            entry["first_progress_at"] = float(observed_at)
        entry["last_progress_at"] = float(observed_at)
    return grew


def _nonnegative_int(value):
    if isinstance(value, bool):
        return 0
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0
