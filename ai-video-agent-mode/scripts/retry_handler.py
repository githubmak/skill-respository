"""Retry handler - incremental correction messages, stale-agent recovery."""
import json, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from pipeline_state import load_state, MAX_RETRIES


def analyze_failures(run_dir, phase, passed_subshots=None):
    """Build incremental correction message for sub-agent retry.

    Args:
        run_dir: Run directory
        phase: Phase name
        passed_subshots: List of subshot IDs that already passed (excluded from msg)

    Returns:
        dict with retry_needed, agent_id, correction_msg (only current failures),
        retry_count, recovery_needed
    """
    state = load_state(run_dir)
    phase_info = state["phases"].get(phase, {})
    agent_id = phase_info.get("agent_id")
    retries = phase_info.get("retries", 0)
    passed_subshots = passed_subshots or []

    if not agent_id:
        return {"retry_needed": False, "reason": "no_agent", "recovery_needed": True}
    if retries >= MAX_RETRIES:
        return {"retry_needed": False, "reason": "max_retries"}

    from gate_check import check as gate_check
    gc = gate_check(run_dir, phase, strict=False)
    blocking = [i for i in gc["issues"] if i["severity"] == "blocking"]

    if not blocking:
        return {"retry_needed": False, "reason": "all_clean", "recovery_needed": False}

    # Group issues by subshot_id, excluding passed subshots
    shot_issues = {}
    for iss in blocking:
        ssid = "GLOBAL"
        for part in iss.get("msg", "").split():
            if "-" in part and len(part) > 4 and part not in passed_subshots:
                ssid = part
                break
        # Skip if this subshot already passed
        if ssid == "GLOBAL" or ssid not in passed_subshots:
            if ssid not in shot_issues:
                shot_issues[ssid] = []
            shot_issues[ssid].append(iss)

    # Remove passed subshots from the issues entirely
    for ps in passed_subshots:
        if ps in shot_issues:
            del shot_issues[ps]

    if not shot_issues:
        return {"retry_needed": False, "reason": "all_passed", "recovery_needed": False}

    # Build minimal correction message: only what is still broken
    lines = ["## 修正要求（仅本次仍失败的项目）"]
    for ssid in sorted(shot_issues.keys()):
        iss_list = shot_issues[ssid]
        lines.append("")
        if ssid == "GLOBAL":
            lines.append("### 全局问题")
        else:
            lines.append("### 子镜头 %s" % ssid)
        for iss in iss_list:
            lines.append("- [%s] %s" % (iss.get("check","?"), iss.get("msg","")))

    return {
        "retry_needed": True,
        "agent_id": agent_id,
        "correction_msg": "\\n".join(lines),
        "retry_count": retries + 1,
        "recovery_needed": True,
        "remaining_shot_issues": shot_issues,
        "passed_count": len(passed_subshots),
        "failed_count": len(shot_issues),
    }
