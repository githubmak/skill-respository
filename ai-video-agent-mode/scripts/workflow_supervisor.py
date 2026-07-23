#!/usr/bin/env python3
"""Resume-safe control plane for the current AI-video prompt pipeline.

The supervisor executes deterministic local phases itself and turns Agent work
into explicit immutable dispatch requests.  A Codex host consumes those
requests by spawning workers, registering their real IDs, recording at least
one heartbeat, and recording provenance after the worker writes its batch.
It never fabricates an Agent result or treats an unverified batch as complete.
"""

import argparse
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from detect_source_rules import detect_source_rules
from generate_shotplan import generate
from build_shotplan import normalize
from preflight_check import run as preflight_check
from pre_editor_gate import run as pre_editor_gate
from emotion_camera_audit import audit as emotion_camera_audit
from validate_modec import main as validate_modec
from check_export import check_export
from export_with_validation import export_with_validation, _record_normalization_provenance
from normalize_prompt_package import normalize_package
from pipeline_runner import run as pipeline_run
from pipeline_runtime import atomic_json


CONTROL_RELATIVE_PATH = ".cache/control/supervisor.json"


def run_until_pause(run_dir, source_path=None, max_ticks=24):
    """Advance local work until a host dispatch, worker wait, or terminal state."""
    run_dir = os.path.abspath(run_dir)
    _record_request(run_dir, source_path)
    history = []
    for _ in range(max_ticks):
        outcome = pipeline_run(run_dir)
        history.append(outcome)
        action = outcome.get("action")
        if action in ("advance",):
            continue
        if action == "local_action_required":
            try:
                detail = execute_local_phase(run_dir, outcome["phase"], source_path)
            except Exception as exc:
                return _result("blocked", history, phase=outcome.get("phase"), reason=str(exc))
            history.append({"action": "local_action_complete", "phase": outcome["phase"], "detail": detail})
            continue
        if action == "spawn":
            return _result("host_dispatch_required", history, phase=outcome.get("phase"),
                           dispatch_packets=outcome.get("dispatch_packets", []),
                           protocol=_dispatch_protocol())
        if action == "wait_for_workers":
            return _result("waiting_for_workers", history, phase=outcome.get("phase"),
                           worker_status=outcome.get("worker_status", []))
        if action == "completed":
            return _result("completed", history)
        return _result(action or "blocked", history, phase=outcome.get("phase"),
                       reason=outcome.get("reason"), expected_outputs=outcome.get("expected_outputs"))
    return _result("blocked", history, reason="supervisor tick limit reached")


def execute_local_phase(run_dir, phase, source_path=None):
    if phase == "user_confirm":
        return {"config_path": os.path.join(run_dir, "project_config.json")}
    if phase == "orchestrator":
        source_path = _required_source(run_dir, source_path)
        _detect_and_persist_source_rules(run_dir, source_path)
        generate(
            source_path,
            os.path.join(run_dir, ".cache", "orchestrator"),
            os.path.join(run_dir, "project_config.json"),
        )
        normalize(run_dir)
        issues = preflight_check(run_dir)
        if issues:
            raise ValueError("orchestrator preflight failed: " + "; ".join(
                str(item.get("msg", item.get("message", item))) if isinstance(item, dict) else str(item)
                for item in issues[:8]
            ))
        return {"source_path": source_path}
    if phase == "editor_pass1":
        result, path = pre_editor_gate(run_dir)
        if not result.get("pass"):
            raise ValueError("pre-editor deterministic gate failed: " + path)
        return {"gate_path": path}
    if phase == "grid_storyboard":
        raise RuntimeError("grid_storyboard requires the host to invoke nine-panel-video-storyboard and write packages.json")
    if phase == "validate":
        package_path = os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json")
        source_sha256 = _sha256(package_path)
        normalize_package(package_path, package_path)
        _record_normalization_provenance(package_path, source_sha256)
        audit, audit_path = emotion_camera_audit(run_dir)
        if not audit.get("pass"):
            raise ValueError("emotion/camera audit failed: " + audit_path)
        if validate_modec(run_dir) != 0:
            raise ValueError("validate_modec failed")
        if check_export("", run_dir, quality_mode=True) != 0:
            raise ValueError("quality gate failed")
        path = os.path.join(run_dir, ".cache", "validate", "result.json")
        atomic_json(path, {"pass": True, "validated_at": time.time(), "emotion_camera_audit": audit_path,
                           "package_sha256": _sha256(package_path)})
        return {"result_path": path}
    if phase == "export":
        config = _load_json(os.path.join(run_dir, "project_config.json"))
        destination = ((config.get("delivery") or {}).get("markdown_path") or "").strip()
        if not destination:
            raise ValueError("delivery.markdown_path is missing from the confirmed configuration")
        os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
        _write_delivery_status(run_dir, destination, "running")
        try:
            exit_code = export_with_validation(destination, run_dir)
        except BaseException as exc:
            _write_delivery_status(run_dir, destination, "blocked", str(exc))
            raise
        if exit_code != 0:
            _write_delivery_status(run_dir, destination, "blocked", "export validation failed")
            raise ValueError("export validation failed")
        path = os.path.join(run_dir, ".cache", "export", "result.json")
        destination = os.path.abspath(destination)
        atomic_json(path, {"pass": True, "exported_at": time.time(), "markdown_path": destination,
                           "markdown_sha256": _sha256(destination),
                           "package_sha256": _sha256(os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json"))})
        _write_delivery_status(run_dir, destination, "approved")
        return {"result_path": path, "markdown_path": os.path.abspath(destination)}
    raise ValueError("no local executor for phase: " + phase)


def _record_request(run_dir, source_path):
    path = os.path.join(run_dir, CONTROL_RELATIVE_PATH)
    current = _load_json(path)
    if source_path:
        source_path = os.path.abspath(source_path)
        if not os.path.isfile(source_path):
            raise ValueError("source file does not exist: " + source_path)
        digest = _sha256(source_path)
        previous = current.get("source") if isinstance(current.get("source"), dict) else {}
        if previous.get("sha256") and previous.get("sha256") != digest:
            raise ValueError("source changed after this run began; start a new run_dir")
        current["source"] = {"path": source_path, "sha256": digest}
    current["updated_at"] = time.time()
    atomic_json(path, current)


def _required_source(run_dir, source_path):
    if source_path:
        return os.path.abspath(source_path)
    saved = _load_json(os.path.join(run_dir, CONTROL_RELATIVE_PATH)).get("source", {})
    path = saved.get("path") if isinstance(saved, dict) else ""
    if not path or not os.path.isfile(path):
        raise ValueError("orchestrator needs --source on the first supervisor call")
    return path


def _detect_and_persist_source_rules(run_dir, source_path):
    config_path = os.path.join(run_dir, "project_config.json")
    config = _load_json(config_path)
    rules = detect_source_rules(source_path)
    config["source_rules"] = {
        "characters": rules.get("characters", []),
        "action_keywords": rules.get("action_keywords", []),
        "scene_header_pattern": rules.get("scene_header_pattern", "^SCENE"),
        "dialogue_pattern": rules.get("dialogue_pattern_desc", "角色名（语气）：台词"),
    }
    config["character_list"] = list(rules.get("characters", []))
    atomic_json(config_path, config)


def _dispatch_protocol():
    return [
        "spawn one worker for each dispatch packet",
        "register the returned Agent ID with register_dispatch_agent.py",
        "record at least one heartbeat while the worker is running",
        "accept only packet._batch_output_path after JSON parsing succeeds",
        "run record_batch_provenance.py, then call workflow_supervisor.py again",
    ]


def _result(status, history, **fields):
    result = {"status": status, "history": history}
    result.update({key: value for key, value in fields.items() if value is not None})
    return result


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_delivery_status(run_dir, destination, status, reason=""):
    destination = os.path.abspath(destination)
    atomic_json(os.path.join(run_dir, ".cache", "export", "delivery_status.json"), {
        "status": status,
        "updated_at": time.time(),
        "markdown_path": destination,
        "existing_output_is_stale": status == "blocked" and os.path.exists(destination),
        "reason": reason,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--source")
    parser.add_argument("--max-ticks", type=int, default=24)
    args = parser.parse_args()
    print(json.dumps(run_until_pause(args.run_dir, args.source, args.max_ticks), ensure_ascii=False, indent=2))
