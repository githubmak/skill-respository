#!/usr/bin/env python3
"""Small, durable runtime primitives shared by the production pipeline.

The pipeline deliberately keeps these concerns outside prompt text: content
addressed artefacts, field-scoped patches, a single issue ledger and real
worker heartbeats.  All writes are atomic so a resumed run never observes a
half-written control file.
"""
import hashlib
import json
import os
import time
import uuid
from contextlib import contextmanager


def sha256_json(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def atomic_json(path, value):
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    temporary = path + ".%s.tmp" % uuid.uuid4().hex
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return path


@contextmanager
def json_lock(path, timeout_seconds=15, stale_seconds=120):
    """Portable lock for short JSON read-modify-write operations.

    ``O_EXCL`` works on Windows and POSIX.  A stale lock from a crashed worker
    is recoverable; callers only hold it while updating a small control file.
    """
    lock_path = path + ".lock"
    parent = os.path.dirname(os.path.abspath(lock_path))
    os.makedirs(parent, exist_ok=True)
    deadline = time.time() + timeout_seconds
    acquired = False
    while not acquired:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write("%s\n" % os.getpid())
            acquired = True
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(lock_path) > stale_seconds:
                    os.unlink(lock_path)
                    continue
            except FileNotFoundError:
                continue
            if time.time() >= deadline:
                raise TimeoutError("timed out waiting for JSON lock: %s" % path)
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            os.unlink(lock_path)
        except FileNotFoundError:
            pass


def cache_artifact(run_dir, stage, value, inputs=None):
    """Store an immutable JSON artifact and return its content-addressed key."""
    record = {"stage": stage, "inputs": inputs or {}, "value": value}
    digest = sha256_json(record)
    path = os.path.join(run_dir, ".cache", "content", stage, digest + ".json")
    if not os.path.exists(path):
        atomic_json(path, record)
    index = os.path.join(run_dir, ".cache", "content", "index.json")
    with json_lock(index):
        current = _load(index)
        current[stage] = {"sha256": digest, "path": path, "updated_at": time.time()}
        atomic_json(index, current)
        return current[stage]


def record_issues(run_dir, stage, issues, source_sha256=None):
    path = os.path.join(run_dir, ".cache", "issues.json")
    entries = []
    for issue in issues or []:
        if isinstance(issue, dict):
            entry = dict(issue)
        else:
            entry = {"message": str(issue)}
        entry.setdefault("stage", stage)
        entry.setdefault("field", _infer_field(entry.get("message", "")))
        entry.setdefault("created_at", time.time())
        entry["source_sha256"] = source_sha256
        entry["issue_id"] = sha256_json({k: entry.get(k) for k in ("stage", "subshot_id", "field", "message", "source_sha256")})[:16]
        entries.append(entry)
    with json_lock(path):
        data = _load(path)
        data[stage] = entries
        atomic_json(path, data)
    return entries


def patch_only(previous, replacement, fields):
    """Merge exactly named dotted fields; locked/unmentioned fields survive."""
    result = json.loads(json.dumps(previous, ensure_ascii=False))
    for field in fields or []:
        source, target = replacement, result
        bits = field.split(".")
        for bit in bits[:-1]:
            if not isinstance(source, dict) or bit not in source:
                source = None; break
            source = source[bit]
            target = target.setdefault(bit, {})
        if source is not None and isinstance(source, dict) and bits[-1] in source:
            target[bits[-1]] = source[bits[-1]]
    return result


def _infer_field(message):
    for field in ("full_prompt", "negative_prompt", "generation_control", "performance_contract",
                  "continuity_contract", "reroll_control", "dialogue_events", "camera_beat_map", "qa_metadata"):
        if field in str(message):
            return field
    return "validator_reported_field"


def _load(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            value = json.load(handle)
            return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}
