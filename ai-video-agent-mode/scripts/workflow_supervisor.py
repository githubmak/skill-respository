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
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from build_shotplan import normalize
from prepare_creative_blueprint import prepare as prepare_creative_blueprint, missing_model_outputs
from preflight_check import run as preflight_check
from source_gate import run as source_gate
from pre_editor_gate import run as pre_editor_gate
from validate_modec import main as validate_modec
from validate_scene_locks import validate as validate_scene_locks
from export_with_validation import export_with_validation, _record_normalization_provenance
from normalize_prompt_package import normalize_package
from pipeline_runner import run as pipeline_run
from pipeline_runtime import atomic_json
from pipeline_state import load_state, save_state
from contract_registry import PROMPT_CONTRACT_VERSION
from validation_receipt import create_receipt
from verified_reuse import publish_run as publish_verified_run, reuse_orchestrator_blueprint


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
            if isinstance(detail, dict) and detail.get("action") == "creative_authoring_required":
                history.append({"action": "creative_authoring_required", "phase": outcome["phase"], "detail": detail})
                status = "creative_authoring_stalled" if detail.get("stalled") else "creative_authoring_required"
                return _result(
                    status,
                    history,
                    phase=outcome.get("phase"),
                    creative_request_path=detail.get("request_path"),
                    revision_request_path=detail.get("revision_request_path"),
                    progress=detail.get("progress"),
                    progress_command=detail.get("progress_command"),
                    missing_outputs=detail.get("missing_outputs", []),
                    reason=detail.get("reason") or "模型必须先提交创意蓝图后才能继续确定性门禁",
                )
            history.append({"action": "local_action_complete", "phase": outcome["phase"], "detail": detail})
            continue
        if action == "spawn":
            return _result("host_dispatch_required", history, phase=outcome.get("phase"),
                           dispatch_packets=outcome.get("dispatch_packets", []),
                           worker_leases=outcome.get("worker_leases", []),
                           interrupt_dispatch_ids=outcome.get("interrupt_dispatch_ids", []),
                           budget=outcome.get("budget"),
                           protocol=_dispatch_protocol())
        if action == "wait_for_workers":
            return _result("waiting_for_workers", history, phase=outcome.get("phase"),
                           worker_status=outcome.get("worker_status", []),
                           poll_after_seconds=outcome.get("poll_after_seconds", 10),
                           budget=outcome.get("budget"))
        if action in ("field_patch_retry", "creative_reauthor_retry"):
            history.append({
                "action": "targeted_retry_prepared",
                "phase": outcome.get("phase"),
                "target_shot_ids": outcome.get("target_shot_ids", []),
                "dispatch_packets": outcome.get("dispatch_packets", []),
            })
            continue
        if action == "creative_reauthor_required":
            return _result(
                "creative_authoring_required", history, phase=outcome.get("next", "orchestrator"),
                revision_request_path=outcome.get("revision_request_path"),
                target_shot_ids=outcome.get("target_shot_ids", []),
                reason=outcome.get("reason"),
            )
        if action == "completed":
            return _result("completed", history)
        if action == "fused":
            return _result("fused", history, phase=outcome.get("phase"),
                           report_path=outcome.get("report_path"),
                           budget=outcome.get("budget"), reason="pipeline deadline gate stopped execution")
        return _result(action or "blocked", history, phase=outcome.get("phase"),
                       reason=outcome.get("reason"), expected_outputs=outcome.get("expected_outputs"))
    return _result("blocked", history, reason="supervisor tick limit reached")


def execute_local_phase(run_dir, phase, source_path=None):
    if phase == "user_confirm":
        return {"config_path": os.path.join(run_dir, "project_config.json")}
    if phase == "orchestrator":
        source_path = _required_source(run_dir, source_path)
        source_report = source_gate(
            run_dir,
            source_path,
            config_path=os.path.join(run_dir, "project_config.json"),
        )
        if not source_report.get("pass"):
            failures = source_report.get("blocking", [])
            detail = "; ".join(
                str(item.get("message", item)) if isinstance(item, dict) else str(item)
                for item in failures[:6]
            )
            raise ValueError("source gate failed: " + detail)
        creative_request, request_path = prepare_creative_blueprint(run_dir, source_path)
        revision = _pending_orchestrator_revision(run_dir)
        if revision:
            return {
                "action": "creative_authoring_required",
                "request_path": request_path,
                "revision_request_path": revision.get("path", ""),
                "source_snapshot_path": creative_request.get("source_snapshot_path", ""),
                "missing_outputs": revision.get("unchanged_outputs", []),
                "authority": "model",
                "reason": "model Editor returned a global directing cause to Orchestrator",
            }
        missing_outputs = missing_model_outputs(creative_request)
        reuse = {"applied": False, "phase": "orchestrator", "reason": "model-authored drafts already exist"}
        if missing_outputs:
            reuse = reuse_orchestrator_blueprint(run_dir)
            missing_outputs = missing_model_outputs(creative_request)
        if missing_outputs:
            progress = _creative_progress_status(creative_request)
            return {
                "action": "creative_authoring_required",
                "request_path": request_path,
                "source_snapshot_path": creative_request.get("source_snapshot_path", ""),
                "missing_outputs": missing_outputs,
                "authority": "model",
                "progress": progress,
                "progress_command": (creative_request.get("checkpoint_policy") or {}).get("progress_command", []),
                "stalled": progress.get("stalled", False),
            }
        normalize(run_dir)
        issues = preflight_check(run_dir)
        blocking = [item for item in issues if item.get("severity", "blocking") == "blocking"]
        if blocking:
            raise ValueError("orchestrator preflight failed: " + "; ".join(
                str(item.get("msg", item.get("message", item))) if isinstance(item, dict) else str(item)
                for item in blocking[:8]
            ))
        scene_locks_draft = os.path.join(run_dir, ".cache", "orchestrator", "scene_locks.draft.json")
        shot_plan_path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")
        scene_lock_issues = validate_scene_locks(scene_locks_draft, shot_plan_path)
        if scene_lock_issues:
            raise ValueError("orchestrator scene locks failed: " + "; ".join(scene_lock_issues[:8]))
        _promote_scene_locks(run_dir, scene_locks_draft)
        _write_orchestrator_receipt(run_dir)
        state = load_state(run_dir)
        state.get("phases", {}).get("orchestrator", {}).pop("revision_request", None)
        state.get("phases", {}).get("orchestrator", {}).pop("revision_request_path", None)
        save_state(run_dir, state)
        return {
            "source_path": source_path,
            "source_gate_path": source_report.get("report_path", ""),
            "source_gate_advisories": source_report.get("advisories", []),
            "preflight_advisories": [item for item in issues if item.get("severity") == "advisory"],
            "creative_request_path": request_path,
            "creative_authority": "model",
            "verified_reuse": reuse,
        }
    if phase == "editor_pass1":
        result, path = pre_editor_gate(run_dir)
        if not result.get("pass"):
            retry = _prepare_pre_editor_retry(run_dir, result)
            if retry.get("dispatch_packets"):
                return retry
            raise ValueError("pre-editor deterministic gate failed: " + path)
        return {"gate_path": path}
    if phase == "validate":
        package_path = os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json")
        source_sha256 = _sha256(package_path)
        normalize_package(package_path, package_path)
        _record_normalization_provenance(package_path, source_sha256)
        if validate_modec(run_dir) != 0:
            raise ValueError("validate_modec failed")
        deterministic_path = os.path.join(run_dir, ".cache", "validate", "deterministic_package.json")
        receipt_path, _receipt = create_receipt(run_dir, package_path, (
            deterministic_path,
        ))
        path = os.path.join(run_dir, ".cache", "validate", "result.json")
        atomic_json(path, {"pass": True, "validated_at": time.time(),
                           "validator_scope": "deterministic_facts_plus_model_editor",
                           "deterministic_report": deterministic_path,
                           "validation_receipt": receipt_path,
                           "package_sha256": _sha256(package_path)})
        try:
            reuse_record_path, reuse_record = publish_verified_run(run_dir)
            reuse_publish = {
                "pass": True,
                "record_path": reuse_record_path,
                "shot_count": len(reuse_record.get("shot_ids", [])),
            }
        except (OSError, ValueError) as exc:
            reuse_publish = {"pass": False, "reason": str(exc)}
            atomic_json(os.path.join(run_dir, ".cache", "reuse", "publish_error.json"), reuse_publish)
            raise ValueError("validated reuse publication failed: " + str(exc))
        return {"result_path": path, "verified_reuse_publish": reuse_publish}
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
        export_result = _load_json(path) if os.path.exists(path) else {}
        export_result.update({"pass": True, "exported_at": time.time(),
                              "package_sha256": _sha256(os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json"))})
        if not export_result.get("markdown_path"):
            export_result.update({"markdown_path": destination, "markdown_sha256": _sha256(destination)})
        atomic_json(path, export_result)
        _write_delivery_status(run_dir, destination, "approved")
        return {"result_path": path, "markdown_path": export_result.get("markdown_path", destination),
                "markdown_paths": export_result.get("markdown_paths", {}),
                "index_markdown_path": export_result.get("index_markdown_path", "")}
    raise ValueError("no local executor for phase: " + phase)


def _prepare_pre_editor_retry(run_dir, gate_result):
    if gate_result.get("composer_pass") is not False:
        return {}
    report_path = gate_result.get("composer_validation_path", "")
    if not report_path or not os.path.exists(report_path):
        return {}
    report = _load_json(report_path)
    failed = [str(item) for item in report.get("failed_subshot_ids", []) if str(item)]
    issues = [str(item) for item in report.get("issues", []) if str(item)]
    if not failed or not issues:
        return {}
    windows = []
    structured_targets = [
        item for item in report.get("repair_targets", []) if isinstance(item, dict)
    ]
    for shot_id in failed:
        shot_issues = [issue for issue in issues if issue.startswith(shot_id + ":")]
        targets = [
            dict(item, shot_id=shot_id)
            for item in structured_targets
            if str(item.get("shot_id", "")) == shot_id
        ]
        if not targets:
            targets = [{
                "shot_id": shot_id,
                "field_path": "validator_reported_field",
                "reason": "validator did not provide a structured field_path",
            }]
        windows.append({
            "window_id": "PRE_" + shot_id,
            "pass": False,
            "repair_scope": next((str(item.get("repair_scope", "field")) for item in targets if isinstance(item, dict)), "field"),
            "blocking": shot_issues,
            "repair_targets": targets or [{"shot_id": shot_id, "field_path": "validator_reported_field"}],
        })
    review_path = os.path.join(run_dir, ".cache", "review", "pre_editor_retry_review.json")
    atomic_json(review_path, {
        "contract_version": PROMPT_CONTRACT_VERSION,
        "source": "pre_editor_composer_validation",
        "windows": windows,
    })
    from prepare_master_retry import prepare
    packets = prepare(run_dir, review_path)
    state = load_state(run_dir)
    state["current_phase"] = "master_production"
    state["phases"]["master_production"].update({"status": "pending", "agent_id": None, "target_shot_ids": failed})
    state["phases"]["editor_pass1"].update({"status": "pending", "agent_id": None, "target_shot_ids": failed})
    state["phases"]["editor_pass2"].update({"status": "pending", "agent_id": None, "target_shot_ids": failed})
    save_state(run_dir, state)
    return {
        "gate_path": os.path.join(run_dir, ".cache", "review", "pre_editor_gate.json"),
        "retry_review_path": review_path,
        "dispatch_packets": packets,
        "target_shot_ids": failed,
        "reason": "pre_editor_composer_validation",
    }


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


def _dispatch_protocol():
    return [
        "spawn one persistent worker for each worker_lease, never one worker per packet",
        "register every packet in that lease with register_dispatch_lease.py and the returned Agent ID",
        "before each packet, run start_leased_dispatch.py and then record its first heartbeat",
        "process lease packet_paths in order and keep the same worker alive between packets",
        "do not wait beyond the packet timeout; interrupt the worker and call the supervisor again",
        "accept only packet._batch_output_path after JSON parsing succeeds",
        "run record_batch_provenance.py, then call workflow_supervisor.py again",
        "pass exact input/output token counts to provenance only when the host exposes them; otherwise leave unavailable",
        "poll immediately after a lease finishes or fails; use the 10-second poll only while no state change occurs",
    ]


def _write_orchestrator_receipt(run_dir):
    """Bind normalized shot plan to the exact model draft that produced it."""
    orchestrator_dir = os.path.join(run_dir, ".cache", "orchestrator")
    report_path = os.path.join(run_dir, ".cache", "preflight", "report.json")
    receipt = {
        "contract_version": PROMPT_CONTRACT_VERSION,
        "draft_sha256": _sha256(os.path.join(orchestrator_dir, "shot_plan.draft.json")),
        "shot_plan_sha256": _sha256(os.path.join(orchestrator_dir, "shot_plan.json")),
        "scene_locks_draft_sha256": _sha256(os.path.join(orchestrator_dir, "scene_locks.draft.json")),
        "scene_locks_sha256": _sha256(os.path.join(run_dir, ".cache", "analysis", "scene_locks.json")),
        "source_ledger_sha256": _sha256(os.path.join(orchestrator_dir, "source_ledger.json")),
        "source_snapshot_sha256": _sha256(os.path.join(orchestrator_dir, "source_snapshot.json")),
        "preflight_report_sha256": _sha256(report_path),
        "preflight_pass": True,
        "created_at": time.time(),
    }
    atomic_json(os.path.join(orchestrator_dir, "creative_validation_receipt.json"), receipt)


def _pending_orchestrator_revision(run_dir):
    state = load_state(run_dir)
    phase = state.get("phases", {}).get("orchestrator", {})
    revision = phase.get("revision_request") if isinstance(phase, dict) else None
    if not isinstance(revision, dict):
        return None
    orchestrator_dir = os.path.join(run_dir, ".cache", "orchestrator")
    paths = {
        "shot_plan_draft": os.path.join(orchestrator_dir, "shot_plan.draft.json"),
        "scene_locks_draft": os.path.join(orchestrator_dir, "scene_locks.draft.json"),
    }
    prior = revision.get("prior_draft_sha256", {}) if isinstance(revision.get("prior_draft_sha256"), dict) else {}
    unchanged = [
        path for name, path in paths.items()
        if not os.path.isfile(path) or (prior.get(name) and _sha256(path) == prior.get(name))
    ]
    if not unchanged:
        return None
    return {"path": phase.get("revision_request_path", ""), "unchanged_outputs": unchanged}


def _creative_progress_status(request, now=None):
    now = float(now if now is not None else time.time())
    policy = request.get("checkpoint_policy", {}) if isinstance(request, dict) else {}
    progress = _load_json(str(policy.get("progress_path", "") or ""))
    started = request.get("authoring_started_at")
    started = float(started) if isinstance(started, (int, float)) else now
    last = progress.get("last_progress_at")
    startup_stalled = not isinstance(last, (int, float)) and now - started >= 5 * 60
    content_stalled = isinstance(last, (int, float)) and now - float(last) >= 3 * 60
    return {
        "started_at": started,
        "last_progress_at": last,
        "progress_count": int(progress.get("progress_count", 0) or 0),
        "total_items": int(progress.get("total_items", 0) or 0),
        "total_bytes": int(progress.get("total_bytes", 0) or 0),
        "stalled": startup_stalled or content_stalled,
        "stall_reason": (
            "startup_content_stall" if startup_stalled else
            "content_progress_stall" if content_stalled else ""
        ),
    }


def _promote_scene_locks(run_dir, draft_path):
    """Copy validated model bytes to the stable production path without rewriting them."""
    output_path = os.path.join(run_dir, ".cache", "analysis", "scene_locks.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    temporary = output_path + ".tmp"
    shutil.copyfile(draft_path, temporary)
    os.replace(temporary, output_path)


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
