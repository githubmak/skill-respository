#!/usr/bin/env python3
"""Cryptographically guarded reuse of previously validated model authorship.

Reuse is an engineering transport operation.  It never edits, scores, trims,
or regenerates creative text.  A cache hit requires identical source facts,
creative configuration, model-authored blueprint, Scene Lock, creative
contract bundle, prompt contract, per-shot content, Editor acceptance, and
final validation receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(__file__))
from contract_registry import PROMPT_CONTRACT_VERSION, REUSE_CONTRACT_VERSION
from pipeline_runtime import atomic_json, json_lock, sha256_json
from pipeline_state import load_state, save_state
from validation_receipt import verify_receipt as verify_validation_receipt


INDEX_VERSION = "verified-run-index-v1"
REUSE_DIRECTORY_NAME = ".ai-video-verified-cache"

SOURCE_SNAPSHOT = ".cache/orchestrator/source_snapshot.json"
SHOT_PLAN_DRAFT = ".cache/orchestrator/shot_plan.draft.json"
SCENE_LOCKS_DRAFT = ".cache/orchestrator/scene_locks.draft.json"
SHOT_PLAN = ".cache/orchestrator/shot_plan.json"
SCENE_LOCKS = ".cache/analysis/scene_locks.json"
PACKAGE = ".cache/composer/merged.prompt_package.json"
EDITOR_REVIEW = ".cache/review/llm_gate_result.json"
VALIDATION_RECEIPT = ".cache/validate/validation_receipt.json"

PUBLISHED_ARTIFACTS = (
    SHOT_PLAN_DRAFT,
    SCENE_LOCKS_DRAFT,
    SHOT_PLAN,
    SCENE_LOCKS,
    PACKAGE,
    EDITOR_REVIEW,
    VALIDATION_RECEIPT,
)

CREATIVE_CONTRACT_FILES = (
    "references/creative_engineering_boundary.md",
    "references/format_constraints.md",
    "references/contracts/aesthetic_directing_contract.md",
    "references/contracts/direct_copy_contract.md",
    "references/contracts/model_creative_blueprint_contract.md",
    "references/dispatch/master_production_note.md",
    "references/dispatch/editor_pass2_note.md",
)

ENGINEERING_ONLY_CONFIG_KEYS = {
    "benchmark",
    "confirmation",
    "delivery",
    "export_base",
    "reuse",
    "reuse_policy",
    "run_timestamp",
}


def reuse_enabled(run_dir):
    config = _load(os.path.join(run_dir, "project_config.json"))
    execution = config.get("execution", {}) if isinstance(config.get("execution"), dict) else {}
    policy = str(config.get("reuse_policy", execution.get("reuse_policy", "verified")) or "verified").lower()
    return policy not in {"fresh", "disabled", "off", "false", "none"}


def publish_run(run_dir):
    """Publish a completed validation result to the stable verified index."""
    run_dir = os.path.abspath(run_dir)
    package_path = os.path.join(run_dir, PACKAGE)
    origin_ok, origin_reason = _verify_master_origin(run_dir, package_path)
    if not origin_ok:
        raise ValueError("validated reuse publish rejected: " + origin_reason)
    ok, reason, _receipt = verify_validation_receipt(run_dir, package_path)
    if not ok:
        raise ValueError("validated reuse publish rejected: " + reason)
    review = _load(os.path.join(run_dir, EDITOR_REVIEW))
    if review.get("pass") is not True or review.get("blocking"):
        raise ValueError("validated reuse publish rejected: Editor acceptance is missing")
    package = _load(package_path)
    if package.get("contract_version") != PROMPT_CONTRACT_VERSION:
        raise ValueError("validated reuse publish rejected: prompt contract mismatch")
    for relative in PUBLISHED_ARTIFACTS:
        if not os.path.isfile(os.path.join(run_dir, relative)):
            raise ValueError("validated reuse publish rejected: missing " + relative)

    identity = build_identity(run_dir, require_blueprint=True)
    shots = _shot_hashes(package)
    if not shots:
        raise ValueError("validated reuse publish rejected: package has no reusable shots")
    editor_hashes = _editor_window_hashes(review)
    if not editor_hashes or _editor_covered_shot_ids(review) != set(shots):
        raise ValueError("validated reuse publish rejected: Editor windows do not cover every shot")
    record = {
        "reuse_contract_version": REUSE_CONTRACT_VERSION,
        "source_run_dir": run_dir,
        "published_at": time.time(),
        "pre_blueprint_identity": build_identity(run_dir, require_blueprint=False),
        "full_identity": identity,
        "artifact_hashes": {
            relative: _sha256(os.path.join(run_dir, relative))
            for relative in PUBLISHED_ARTIFACTS
        },
        "per_shot_output_hashes": shots,
        "editor_window_hashes": editor_hashes,
        "per_scene_artifact_hashes": _scene_artifact_hashes(
            run_dir, package, review
        ),
        "shot_ids": list(shots),
        "validation_receipt_verified": True,
        "editor_pass_verified": True,
    }
    reuse_dir = os.path.join(run_dir, ".cache", "reuse")
    record_path = os.path.join(reuse_dir, "published.json")
    atomic_json(record_path, record)

    index_path = _index_path(run_dir)
    with json_lock(index_path):
        index = _load(index_path)
        if index.get("index_version") != INDEX_VERSION:
            index = {"index_version": INDEX_VERSION, "entries": []}
        entries = [entry for entry in index.get("entries", []) if isinstance(entry, dict)]
        source_real = os.path.realpath(run_dir)
        entries = [entry for entry in entries if os.path.realpath(str(entry.get("source_run_dir", ""))) != source_real]
        entries.append({
            "source_run_dir": run_dir,
            "record_path": record_path,
            "record_sha256": _sha256(record_path),
            "pre_blueprint_digest": identity_digest(record["pre_blueprint_identity"]),
            "full_identity_digest": identity_digest(identity),
            "published_at": record["published_at"],
        })
        index["entries"] = sorted(entries, key=lambda item: float(item.get("published_at", 0)), reverse=True)[:64]
        atomic_json(index_path, index)
    return record_path, record


def reuse_orchestrator_blueprint(run_dir):
    """Restore an exact validated model blueprint before new authoring starts."""
    run_dir = os.path.abspath(run_dir)
    if not reuse_enabled(run_dir):
        return _miss(run_dir, "orchestrator", "reuse policy requests fresh authorship")
    candidate, reason = find_candidate(run_dir, require_blueprint=False)
    if not candidate:
        return _miss(run_dir, "orchestrator", reason)
    source_run = candidate["source_run_dir"]
    mappings = []
    for relative in (SHOT_PLAN_DRAFT, SCENE_LOCKS_DRAFT):
        source = os.path.join(source_run, relative)
        destination = os.path.join(run_dir, relative)
        _atomic_copy(source, destination)
        mappings.append(_mapping(relative, source, destination))
    record = _new_reuse_record(run_dir, "orchestrator", candidate, mappings)
    path = _write_phase_record(run_dir, "orchestrator", record)
    _write_selected_candidate(run_dir, candidate)
    state = load_state(run_dir)
    phase_state = state["phases"]["orchestrator"]
    phase_state["reuse_contract_version"] = REUSE_CONTRACT_VERSION
    phase_state["reuse_provenance_path"] = path
    phase_state["reuse_source_run"] = source_run
    phase_state["reused_item_count"] = 2
    save_state(run_dir, state)
    return {"applied": True, "phase": "orchestrator", "provenance_path": path,
            "source_run_dir": source_run, "reused_item_count": 2}


def reuse_agent_phase(run_dir, phase):
    """Materialize a validated Master package or Editor review in a new run."""
    run_dir = os.path.abspath(run_dir)
    if phase not in {"master_production", "editor_pass2"}:
        return {"applied": False, "phase": phase, "reason": "phase is not reusable"}
    if not reuse_enabled(run_dir):
        return _miss(run_dir, phase, "reuse policy requests fresh authorship")
    state = load_state(run_dir)
    phase_state = state.get("phases", {}).get(phase, {})
    if phase_state.get("dispatches"):
        return _miss(run_dir, phase, "worker dispatch already exists")
    if phase_state.get("target_shot_ids"):
        return _miss(run_dir, phase, "targeted creative retry cannot use whole-run cache")

    candidate = _selected_candidate(run_dir)
    reason = "selected candidate is missing or stale"
    if candidate:
        candidate, reason = _verify_candidate(run_dir, candidate, require_blueprint=True)
    if not candidate:
        candidate, reason = find_candidate(run_dir, require_blueprint=True)
    if not candidate:
        return _miss(run_dir, phase, reason)

    relative = PACKAGE if phase == "master_production" else EDITOR_REVIEW
    source = os.path.join(candidate["source_run_dir"], relative)
    destination = os.path.join(run_dir, relative)
    _atomic_copy(source, destination)
    mappings = [_mapping(relative, source, destination)]
    record = _new_reuse_record(run_dir, phase, candidate, mappings)
    if phase == "master_production":
        current_hashes = _shot_hashes(_load(destination))
        expected_hashes = candidate.get("per_shot_output_hashes", {})
        if current_hashes != expected_hashes:
            raise ValueError("verified reuse changed per-shot output hashes")
        record["new_run_packet_mapping"] = [
            {
                "source_shot_id": shot_id,
                "target_shot_id": shot_id,
                "source_output_sha256": digest,
                "target_output_sha256": current_hashes[shot_id],
            }
            for shot_id, digest in current_hashes.items()
        ]
        reused_count = len(current_hashes)
    else:
        review = _load(destination)
        if review.get("pass") is not True or review.get("blocking"):
            raise ValueError("verified reuse Editor result is no longer accepted")
        current_windows = _editor_window_hashes(review)
        if current_windows != candidate.get("editor_window_hashes", {}):
            raise ValueError("verified reuse changed Editor window hashes")
        record["new_run_window_mapping"] = [
            {"window_id": key, "source_output_sha256": value, "target_output_sha256": current_windows[key]}
            for key, value in current_windows.items()
        ]
        reused_count = len(current_windows)
    path = _write_phase_record(run_dir, phase, record)

    if phase == "master_production":
        atomic_json(destination + ".merge_provenance.json", {
            "contract_version": PROMPT_CONTRACT_VERSION,
            "output_path": os.path.abspath(destination),
            "output_sha256": _sha256(destination),
            "provenance_mode": "verified_reuse",
            "reuse_contract_version": REUSE_CONTRACT_VERSION,
            "reuse_provenance_path": path,
            "reuse_provenance_sha256": _sha256(path),
            "source_batches": [],
            "created_at": time.time(),
        })

    state = load_state(run_dir)
    phase_state = state["phases"][phase]
    phase_state["reuse_contract_version"] = REUSE_CONTRACT_VERSION
    phase_state["reuse_provenance_path"] = path
    phase_state["reuse_source_run"] = candidate["source_run_dir"]
    phase_state["reused_item_count"] = reused_count
    if not isinstance(phase_state.get("started_at"), (int, float)):
        phase_state["started_at"] = time.time()
    save_state(run_dir, state)
    _write_selected_candidate(run_dir, candidate)
    return {"applied": True, "phase": phase, "provenance_path": path,
            "source_run_dir": candidate["source_run_dir"], "reused_item_count": reused_count}


def verify_phase_reuse(run_dir, phase):
    state = load_state(run_dir)
    phase_state = state.get("phases", {}).get(phase, {})
    path = str(phase_state.get("reuse_provenance_path", "") or "")
    record = _load(path)
    if record.get("reuse_contract_version") != REUSE_CONTRACT_VERSION or record.get("phase") != phase:
        return False, "reuse provenance is missing or unsupported"
    candidate = _load(str(record.get("source_publication_path", "") or ""))
    candidate, reason = _verify_candidate(run_dir, candidate, require_blueprint=True)
    if not candidate:
        return False, reason
    for mapping in record.get("artifact_mappings", []) if isinstance(record.get("artifact_mappings"), list) else []:
        destination = str(mapping.get("target_path", "") or "") if isinstance(mapping, dict) else ""
        if not destination or not os.path.isfile(destination) or _sha256(destination) != mapping.get("target_sha256"):
            return False, "reused target artifact changed"
    return True, "verified reuse provenance"


def find_candidate(run_dir, require_blueprint):
    current = build_identity(run_dir, require_blueprint=require_blueprint)
    digest = identity_digest(current)
    index = _load(_index_path(run_dir))
    if index.get("index_version") != INDEX_VERSION:
        return None, "verified reuse index is unavailable"
    digest_field = "full_identity_digest" if require_blueprint else "pre_blueprint_digest"
    reasons = []
    for entry in index.get("entries", []) if isinstance(index.get("entries"), list) else []:
        if not isinstance(entry, dict) or entry.get(digest_field) != digest:
            continue
        record_path = str(entry.get("record_path", "") or "")
        if not os.path.isfile(record_path) or _sha256(record_path) != entry.get("record_sha256"):
            reasons.append("published reuse record changed")
            continue
        candidate = _load(record_path)
        candidate["_publication_path"] = record_path
        verified, reason = _verify_candidate(run_dir, candidate, require_blueprint=require_blueprint)
        if verified:
            return verified, "verified cache hit"
        reasons.append(reason)
    return None, reasons[0] if reasons else "no exact validated creative identity matched"


def build_identity(run_dir, require_blueprint):
    run_dir = os.path.abspath(run_dir)
    snapshot = _load(os.path.join(run_dir, SOURCE_SNAPSHOT))
    source_sha = str(snapshot.get("source_sha256", "") or "")
    if not source_sha:
        raise ValueError("reuse identity requires source_snapshot.source_sha256")
    config = _load(os.path.join(run_dir, "project_config.json"))
    if not config:
        raise ValueError("reuse identity requires project_config.json")
    identity = {
        "source_sha256": source_sha,
        "project_creative_config_sha256": sha256_json(_creative_config(config)),
        "prompt_contract_version": PROMPT_CONTRACT_VERSION,
        "creative_contract_bundle_sha256": creative_contract_bundle_sha256(),
    }
    if require_blueprint:
        for key, relative in (("shot_plan_sha256", SHOT_PLAN), ("scene_locks_sha256", SCENE_LOCKS)):
            path = os.path.join(run_dir, relative)
            if not os.path.isfile(path):
                raise ValueError("reuse identity requires " + relative)
            identity[key] = _sha256(path)
    return identity


def identity_digest(identity):
    return sha256_json(identity)


def creative_contract_bundle_sha256():
    root = os.path.dirname(os.path.dirname(__file__))
    digest = hashlib.sha256()
    for relative in CREATIVE_CONTRACT_FILES:
        path = os.path.join(root, relative)
        if not os.path.isfile(path):
            raise ValueError("creative contract file is missing: " + relative)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256(path).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _verify_candidate(target_run_dir, candidate, require_blueprint):
    if candidate.get("reuse_contract_version") != REUSE_CONTRACT_VERSION:
        return None, "reuse contract version mismatch"
    source_run = os.path.abspath(str(candidate.get("source_run_dir", "") or ""))
    if not source_run or os.path.realpath(source_run) == os.path.realpath(target_run_dir):
        return None, "reuse source must be a different run"
    if not os.path.isdir(source_run):
        return None, "reuse source run is unavailable"
    try:
        expected_identity = build_identity(target_run_dir, require_blueprint=require_blueprint)
        source_identity = build_identity(source_run, require_blueprint=require_blueprint)
    except ValueError as exc:
        return None, str(exc)
    candidate_identity = candidate.get("full_identity" if require_blueprint else "pre_blueprint_identity")
    if expected_identity != source_identity or candidate_identity != source_identity:
        return None, "source, configuration, blueprint, Scene Lock, or creative contract changed"
    for relative, expected_hash in candidate.get("artifact_hashes", {}).items():
        path = os.path.join(source_run, relative)
        if not os.path.isfile(path) or _sha256(path) != expected_hash:
            return None, "published artifact changed: " + str(relative)
    package_path = os.path.join(source_run, PACKAGE)
    ok, reason, _receipt = verify_validation_receipt(source_run, package_path)
    if not ok:
        return None, "prior validation receipt is stale: " + reason
    package = _load(package_path)
    if _shot_hashes(package) != candidate.get("per_shot_output_hashes"):
        return None, "prior per-shot hashes changed"
    review = _load(os.path.join(source_run, EDITOR_REVIEW))
    if review.get("pass") is not True or review.get("blocking"):
        return None, "prior Editor acceptance is no longer valid"
    if _editor_window_hashes(review) != candidate.get("editor_window_hashes"):
        return None, "prior Editor window hashes changed"
    if _editor_covered_shot_ids(review) != set(candidate.get("per_shot_output_hashes", {})):
        return None, "prior Editor coverage changed"
    if _scene_artifact_hashes(source_run, package, review) != candidate.get("per_scene_artifact_hashes"):
        return None, "prior per-scene creative identity changed"
    return candidate, "verified"


def _creative_config(config):
    return {
        key: value for key, value in config.items()
        if key not in ENGINEERING_ONLY_CONFIG_KEYS
    }


def _verify_master_origin(run_dir, package_path):
    manifest = _load(package_path + ".merge_provenance.json")
    if manifest.get("output_path") != os.path.abspath(package_path):
        return False, "Master merge provenance is missing"
    if not os.path.isfile(package_path) or manifest.get("output_sha256") != _sha256(package_path):
        return False, "Master merge provenance package hash is stale"
    if manifest.get("provenance_mode") == "verified_reuse":
        return verify_phase_reuse(run_dir, "master_production")
    sources = manifest.get("source_batches", [])
    if not isinstance(sources, list) or not sources:
        return False, "Master merge provenance has no worker sources"
    from record_batch_provenance import verify as verify_batch_provenance
    for source in sources:
        batch_path = str(source.get("batch_path", "") or "") if isinstance(source, dict) else ""
        valid, reason, _record = (
            verify_batch_provenance(batch_path)
            if batch_path and os.path.isfile(batch_path)
            else (False, "batch missing", None)
        )
        if not valid:
            return False, "Master worker provenance is invalid: " + reason
    return True, "verified Master origin"


def _shot_hashes(package):
    result = {}
    shots = package.get("shots", []) if isinstance(package, dict) else []
    for shot in shots if isinstance(shots, list) else []:
        if not isinstance(shot, dict):
            return {}
        shot_id = str(shot.get("shot_id", "") or shot.get("subshot_id", "") or "")
        if not shot_id or shot_id in result:
            return {}
        result[shot_id] = sha256_json(shot)
    return result


def _editor_window_hashes(review):
    result = {}
    windows = review.get("windows", []) if isinstance(review, dict) else []
    for window in windows if isinstance(windows, list) else []:
        if not isinstance(window, dict):
            return {}
        window_id = str(window.get("window_id", "") or "")
        if not window_id or window_id in result:
            return {}
        result[window_id] = sha256_json(window)
    return result


def _editor_covered_shot_ids(review):
    result = set()
    windows = review.get("windows", []) if isinstance(review, dict) else []
    for window in windows if isinstance(windows, list) else []:
        if not isinstance(window, dict):
            continue
        reviewed = window.get("reviewed_shot_ids", [])
        if isinstance(reviewed, list):
            result.update(str(value) for value in reviewed if str(value).strip())
            continue
        # Recovery compatibility for publications created before scene windows.
        current = window.get("current", {}) if isinstance(window.get("current"), dict) else {}
        shot_id = str(current.get("shot_id", "") or "")
        if shot_id:
            result.add(shot_id)
    return result


def _scene_artifact_hashes(run_dir, package, review):
    plan = _load(os.path.join(run_dir, SHOT_PLAN))
    locks = _load(os.path.join(run_dir, SCENE_LOCKS))
    shot_hashes = _shot_hashes(package)
    window_hashes = _editor_window_hashes(review)
    windows = review.get("windows", []) if isinstance(review, dict) else []
    scenes = {}
    for row in plan.get("shots", []) if isinstance(plan, dict) else []:
        if not isinstance(row, dict):
            continue
        scene = str(row.get("scene", "") or "__default__")
        scene_row = scenes.setdefault(scene, {"plan_rows": [], "shot_ids": []})
        scene_row["plan_rows"].append(row)
        shot_id = str(row.get("shot_id", "") or "")
        if shot_id:
            scene_row["shot_ids"].append(shot_id)
    lock_by_scene = {
        str(row.get("scene", "") or "__default__"): row
        for row in locks.get("scenes", []) if isinstance(row, dict)
    }
    result = {}
    for scene, row in scenes.items():
        shot_ids = row["shot_ids"]
        scene_windows = {}
        for window in windows if isinstance(windows, list) else []:
            if not isinstance(window, dict):
                continue
            reviewed = {
                str(value) for value in window.get("reviewed_shot_ids", [])
                if str(value).strip()
            }
            window_id = str(window.get("window_id", "") or "")
            if reviewed.intersection(shot_ids) and window_id in window_hashes:
                scene_windows[window_id] = window_hashes[window_id]
        result[scene] = sha256_json({
            "plan_rows": row["plan_rows"],
            "scene_lock": lock_by_scene.get(scene),
            "shot_output_hashes": {
                shot_id: shot_hashes.get(shot_id) for shot_id in shot_ids
            },
            "editor_window_hashes": scene_windows,
        })
    return result


def _new_reuse_record(run_dir, phase, candidate, mappings):
    publication_path = str(candidate.get("_publication_path", "") or os.path.join(
        candidate["source_run_dir"], ".cache", "reuse", "published.json"
    ))
    return {
        "reuse_contract_version": REUSE_CONTRACT_VERSION,
        "phase": phase,
        "target_run_dir": os.path.abspath(run_dir),
        "source_run_dir": candidate["source_run_dir"],
        "source_publication_path": publication_path,
        "source_publication_sha256": _sha256(publication_path),
        "applied_at": time.time(),
        "semantic_transform": False,
        "full_identity": candidate["full_identity"],
        "artifact_mappings": mappings,
        "validation_receipt_verified": True,
        "editor_pass_verified": True,
    }


def _mapping(relative, source, destination):
    source_hash = _sha256(source)
    target_hash = _sha256(destination)
    if source_hash != target_hash:
        raise ValueError("reuse transport changed artifact bytes: " + relative)
    return {
        "relative_path": relative,
        "source_path": os.path.abspath(source),
        "target_path": os.path.abspath(destination),
        "source_sha256": source_hash,
        "target_sha256": target_hash,
    }


def _write_phase_record(run_dir, phase, record):
    path = os.path.join(run_dir, ".cache", "reuse", phase + ".json")
    atomic_json(path, record)
    return path


def _write_selected_candidate(run_dir, candidate):
    selected = dict(candidate)
    selected.pop("_publication_path", None)
    selected["selected_publication_path"] = str(candidate.get("_publication_path", "") or os.path.join(
        candidate["source_run_dir"], ".cache", "reuse", "published.json"
    ))
    atomic_json(os.path.join(run_dir, ".cache", "reuse", "selected_candidate.json"), selected)


def _selected_candidate(run_dir):
    selected = _load(os.path.join(run_dir, ".cache", "reuse", "selected_candidate.json"))
    publication_path = str(selected.pop("selected_publication_path", "") or "")
    if publication_path:
        selected["_publication_path"] = publication_path
    return selected or None


def _miss(run_dir, phase, reason):
    result = {"applied": False, "phase": phase, "reason": str(reason)}
    atomic_json(os.path.join(run_dir, ".cache", "reuse", phase + ".lookup.json"), dict(result, checked_at=time.time()))
    return result


def _index_path(run_dir):
    config = _load(os.path.join(run_dir, "project_config.json"))
    explicit = str((config.get("reuse") or {}).get("cache_dir", "") or "") if isinstance(config.get("reuse"), dict) else ""
    if explicit:
        root = os.path.abspath(explicit)
    else:
        codex_home = str(os.environ.get("CODEX_HOME", "") or "").strip()
        cache_home = str(os.environ.get("XDG_CACHE_HOME", "") or "").strip()
        base = codex_home or (
            os.path.join(cache_home, "codex") if cache_home
            else os.path.join(os.path.expanduser("~"), ".cache", "codex")
        )
        root = os.path.join(os.path.abspath(base), "ai-video-agent-mode", REUSE_DIRECTORY_NAME)
    return os.path.join(root, "index.json")


def _atomic_copy(source, destination):
    if not os.path.isfile(source):
        raise ValueError("reuse source artifact is missing: " + source)
    parent = os.path.dirname(os.path.abspath(destination))
    os.makedirs(parent, exist_ok=True)
    temporary = destination + "." + uuid.uuid4().hex + ".tmp"
    try:
        with open(source, "rb") as reader, open(temporary, "wb") as writer:
            shutil.copyfileobj(reader, writer, length=1024 * 1024)
            writer.flush()
            os.fsync(writer.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("publish", "lookup"))
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--phase", choices=("orchestrator", "master_production", "editor_pass2"), default="master_production")
    args = parser.parse_args()
    if args.command == "publish":
        path, value = publish_run(args.run_dir)
        result = {"pass": True, "record_path": path, "shot_count": len(value.get("shot_ids", []))}
    elif args.phase == "orchestrator":
        result = reuse_orchestrator_blueprint(args.run_dir)
    else:
        result = reuse_agent_phase(args.run_dir, args.phase)
    print(json.dumps(result, ensure_ascii=False, indent=2))
