"""Retry handler - sends correction messages to failed sub-agents."""
import json, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from pipeline_state import load_state


def analyze_failures(run_dir, phase):
    state = load_state(run_dir)
    phase_info = state["phases"].get(phase, {})
    agent_id = phase_info.get("agent_id")
    retries = phase_info.get("retries", 0)

    if not agent_id:
        return {"retry_needed": False, "reason": "no_agent"}
    if retries >= 2:
        return {"retry_needed": False, "reason": "max_retries"}

    from gate_check import check as gate_check
    gc = gate_check(run_dir, phase, strict=False)
    blocking = [i for i in gc["issues"] if i["severity"] == "blocking"]

    if not blocking:
        return {"retry_needed": False, "reason": "all_clean"}

    shot_issues = {}
    for iss in blocking:
        ssid = "GLOBAL"
        for part in iss.get("msg", "").split():
            if "-" in part and len(part) > 4:
                ssid = part; break
        shot_issues.setdefault(ssid, []).append(iss)

    lines = ["## 修正要求", "检查到以下问题，请修正："]
    for ssid, iss_list in shot_issues.items():
        lines.append("### " + ssid)
        for iss in iss_list:
            lines.append("- [" + iss.get("check","?") + "] " + iss.get("msg",""))

    return {
        "retry_needed": True,
        "agent_id": agent_id,
        "correction_msg": chr(10).join(lines),
        "retry_count": retries + 1,
    }