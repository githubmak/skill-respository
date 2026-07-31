#!/usr/bin/env python3
"""Read-only audit for pipeline state, active dispatch, and provenance invariants."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pipeline_state import AGENT_PHASES, PHASE_ORDER, get_state_path
from contract_registry import PIPELINE_CONTRACT_VERSION
from record_batch_provenance import verify as verify_provenance


TERMINAL_PHASE_STATUS = {"done"}
RECORDED_DISPATCH_STATUS = {"done", "partial"}


def audit(run_dir):
    """Return deterministic invariant findings without mutating the run directory."""
    run_dir = os.path.abspath(run_dir)
    issues = []
    summary = {
        "run_dir": run_dir,
        "state_path": get_state_path(run_dir),
        "agent_dispatches_checked": 0,
        "active_packets_checked": 0,
        "provenance_checked": 0,
    }
    state = _load_required(summary["state_path"], issues, "pipeline_state")
    if not isinstance(state, dict):
        return _result(issues, summary)

    _audit_state(state, issues)
    phases = state.get("phases", {}) if isinstance(state.get("phases"), dict) else {}
    for phase in AGENT_PHASES:
        phase_state = phases.get(phase, {})
        dispatches = phase_state.get("dispatches", {}) if isinstance(phase_state, dict) else {}
        if not isinstance(dispatches, dict):
            issues.append("%s.dispatches必须是对象" % phase)
            continue
        for dispatch_id, dispatch in dispatches.items():
            if not isinstance(dispatch, dict):
                issues.append("%s.dispatches.%s必须是对象" % (phase, dispatch_id))
                continue
            status = dispatch.get("status")
            if status not in RECORDED_DISPATCH_STATUS:
                # rejected/retired/failed historical entries are audit history,
                # not accepted worker output. They must never be provenance-gated
                # as if they remained active.
                continue
            summary["agent_dispatches_checked"] += 1
            _audit_recorded_dispatch(run_dir, phase, str(dispatch_id), dispatch, issues, summary)
        _audit_active_manifest(run_dir, phase, phase_state, dispatches, issues, summary)

    _audit_completed_artifacts(run_dir, state, issues)
    return _result(issues, summary)


def _audit_state(state, issues):
    if state.get("pipeline_contract_version") not in (None, PIPELINE_CONTRACT_VERSION):
        issues.append("pipeline_state.pipeline_contract_version与当前机器契约不一致")
    order = state.get("phase_order")
    if order != PHASE_ORDER:
        issues.append("pipeline_state.phase_order必须精确等于当前PHASE_ORDER")
    current = state.get("current_phase")
    if current not in PHASE_ORDER:
        issues.append("pipeline_state.current_phase不在PHASE_ORDER中")
    phases = state.get("phases")
    if not isinstance(phases, dict):
        issues.append("pipeline_state.phases必须是对象")
        return
    for phase in PHASE_ORDER:
        entry = phases.get(phase)
        if not isinstance(entry, dict):
            issues.append("pipeline_state.phases.%s缺失或不是对象" % phase)
            continue
        status = entry.get("status")
        if status in TERMINAL_PHASE_STATUS and not _number(entry.get("completed_at")):
            issues.append("%s已完成但completed_at缺失" % phase)
        _time_order_issues(phase, entry, issues)


def _time_order_issues(label, entry, issues):
    spawn = entry.get("spawn_time")
    started = entry.get("started_at")
    heartbeat = entry.get("heartbeat_at")
    completed = entry.get("completed_at")
    recorded = entry.get("recorded_at")
    elapsed = entry.get("elapsed_seconds")
    if elapsed is not None and (not _number(elapsed) or elapsed < 0):
        issues.append("%s.elapsed_seconds必须是非负数" % label)
    if _number(spawn) and _number(heartbeat) and heartbeat < spawn:
        issues.append("%s.heartbeat_at早于spawn_time" % label)
    if _number(spawn) and _number(recorded) and recorded < spawn:
        issues.append("%s.recorded_at早于spawn_time" % label)
    if _number(heartbeat) and _number(recorded) and recorded < heartbeat:
        issues.append("%s.recorded_at早于heartbeat_at" % label)
    baseline = started if _number(started) else spawn
    if _number(baseline) and _number(completed) and completed < baseline:
        issues.append("%s.completed_at早于started_at/spawn_time" % label)


def _audit_recorded_dispatch(run_dir, phase, dispatch_id, dispatch, issues, summary):
    label = "%s.dispatches.%s" % (phase, dispatch_id)
    for field in ("agent_id", "spawn_time", "heartbeat_at", "recorded_at"):
        if field == "agent_id":
            if not str(dispatch.get(field, "") or "").strip():
                issues.append("%s.%s缺失" % (label, field))
        elif not _number(dispatch.get(field)):
            issues.append("%s.%s必须是数值" % (label, field))
    _time_order_issues(label, dispatch, issues)
    packet_path = _find_packet(run_dir, dispatch_id)
    if not packet_path:
        issues.append("%s缺少可定位的dispatch packet" % label)
        return
    packet = _load_required(packet_path, issues, label + ".packet")
    if not isinstance(packet, dict):
        return
    if packet.get("phase") != phase:
        issues.append("%s.packet.phase与状态机阶段不一致" % label)
    if packet.get("dispatch_id") != dispatch_id:
        issues.append("%s.packet.dispatch_id与状态机不一致" % label)
    batch_path = str(packet.get("_batch_output_path", "") or "")
    if not batch_path or not os.path.isfile(batch_path):
        issues.append("%s缺少worker _batch_output_path" % label)
        return
    summary["provenance_checked"] += 1
    verified, reason, _manifest = verify_provenance(batch_path)
    if not verified:
        issues.append("%s.provenance无效：%s" % (label, reason))


def _audit_active_manifest(run_dir, phase, phase_state, dispatches, issues, summary):
    path = os.path.join(run_dir, ".cache", "dispatch", "active_%s_manifest.json" % phase)
    if not os.path.exists(path):
        if dispatches:
            issues.append("%s存在dispatch但缺少active manifest" % phase)
        return
    manifest = _load_required(path, issues, "%s active manifest" % phase)
    if not isinstance(manifest, dict):
        return
    if manifest.get("contract_version") != "jimeng-t2v-v1":
        issues.append("%s active manifest contract_version无效" % phase)
    if manifest.get("phase") != phase:
        issues.append("%s active manifest phase不一致" % phase)
    packets = manifest.get("packets")
    if not isinstance(packets, list):
        issues.append("%s active manifest.packets必须是数组" % phase)
        return
    effective = [item for item in packets if isinstance(item, dict) and item.get("effective") is not False]
    if manifest.get("active_packet_count") != len(effective):
        issues.append("%s active_packet_count与effective packets数量不一致" % phase)
    seen_ids, seen_outputs = set(), set()
    for entry in effective:
        summary["active_packets_checked"] += 1
        dispatch_id = str(entry.get("dispatch_id", "") or "")
        packet_path = str(entry.get("packet_path", "") or "")
        if not dispatch_id or not packet_path or not os.path.isfile(packet_path):
            issues.append("%s active packet缺少有效dispatch_id或packet_path" % phase)
            continue
        if dispatch_id in seen_ids:
            issues.append("%s active manifest存在重复dispatch_id：%s" % (phase, dispatch_id))
        seen_ids.add(dispatch_id)
        packet = _load_required(packet_path, issues, "%s active packet %s" % (phase, dispatch_id))
        if not isinstance(packet, dict):
            continue
        output = os.path.abspath(str(packet.get("_batch_output_path", "") or ""))
        if not output:
            issues.append("%s active packet %s缺少_batch_output_path" % (phase, dispatch_id))
        elif output in seen_outputs:
            issues.append("%s active manifest存在重复_batch_output_path" % phase)
        seen_outputs.add(output)
        dispatch = dispatches.get(dispatch_id)
        if not isinstance(dispatch, dict):
            if (phase_state or {}).get("status") == "done":
                issues.append("%s active packet %s未登记到pipeline_state" % (phase, dispatch_id))
            continue
        if dispatch.get("status") in {"rejected", "retired", "failed"}:
            issues.append("%s active packet %s不能指向%s dispatch" % (phase, dispatch_id, dispatch.get("status")))
        if (phase_state or {}).get("status") == "done" and dispatch.get("status") not in RECORDED_DISPATCH_STATUS:
            issues.append("%s active packet %s未被记录为done/partial" % (phase, dispatch_id))


def _audit_completed_artifacts(run_dir, state, issues):
    phases = state.get("phases", {})
    merged = os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json")
    if phases.get("master_production", {}).get("status") == "done":
        merge_sidecar = merged + ".merge_provenance.json"
        if not os.path.isfile(merged) or not os.path.isfile(merge_sidecar):
            issues.append("master_production已完成但缺少merged prompt package或merge provenance")
    if phases.get("export", {}).get("status") == "done":
        result_path = os.path.join(run_dir, ".cache", "export", "result.json")
        result = _load_required(result_path, issues, "export result")
        if isinstance(result, dict):
            markdown_path = str(result.get("markdown_path", "") or "")
            if not result.get("pass") or not markdown_path or not os.path.isfile(markdown_path):
                issues.append("export已完成但export result未指向有效Markdown产物")


def _find_packet(run_dir, dispatch_id):
    dispatch_dir = os.path.join(run_dir, ".cache", "dispatch")
    for root, _dirs, files in os.walk(dispatch_dir):
        for name in files:
            if name.endswith("_packet.json") and dispatch_id.split("-")[0] in name:
                path = os.path.join(root, name)
                try:
                    if _load(path).get("dispatch_id") == dispatch_id:
                        return path
                except (OSError, json.JSONDecodeError):
                    continue
    return None


def _load_required(path, issues, label):
    if not os.path.isfile(path):
        issues.append("%s缺失：%s" % (label, path))
        return None
    try:
        return _load(path)
    except (OSError, json.JSONDecodeError) as error:
        issues.append("%s不可读取：%s" % (label, error))
        return None


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _result(issues, summary):
    return {"pass": not issues, "issues": issues, "summary": summary}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--report")
    args = parser.parse_args()
    result = audit(args.run_dir)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
    print("[PIPELINE INVARIANTS] %s" % ("PASS" if result["pass"] else "FAIL"))
    for issue in result["issues"]:
        print("- " + issue)
    raise SystemExit(0 if result["pass"] else 1)
