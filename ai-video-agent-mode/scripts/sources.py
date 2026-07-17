"""Shot-level traceability - per-subshot pass/fail tracking for incremental retry."""
import json, os

from agent_handoff import read_handoff

def get_sources_path(run_dir):
    return os.path.join(run_dir, ".cache", "sources.json")


def init_sources(run_dir, shot_plan):
    path = get_sources_path(run_dir)
    if os.path.exists(path):
        return
    sources = {}
    for shot in shot_plan.get("shots", []):
        for ss in shot.get("subshots", []):
            ssid = ss["subshot_id"]
            sources[ssid] = {
                "shot_id": shot["shot_id"],
                "status": "pending",
                "retries": 0,
                "passed_phases": [],      # phases where this subshot passed validation
                "failed_phases": [],      # phases where this subshot failed
                "qa_issues": [],
            }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    print("[SOURCES] %d subshots initialized" % len(sources))


def set_batch_agent(run_dir, shots, role, agent_id):
    sources = _load(run_dir)
    role_key = role + "_from"
    for shot in shots:
        for ss in shot.get("subshots", []):
            ssid = ss["subshot_id"]
            if ssid in sources:
                sources[ssid][role_key] = agent_id
                sources[ssid]["status"] = "running"
    _save(run_dir, sources)


def mark_subshot_passed(run_dir, subshot_id, phase=None):
    """Mark a subshot as passed validation in the given phase."""
    sources = _load(run_dir)
    if subshot_id in sources:
        info = sources[subshot_id]
        info["status"] = "passed"
        if phase and phase not in info.get("passed_phases", []):
            info.setdefault("passed_phases", []).append(phase)
        info["qa_issues"] = []  # clear old issues on pass
        _save(run_dir, sources)


def mark_subshot_failed(run_dir, subshot_id, issue, phase=None):
    """Mark a subshot as failed with specific issue."""
    sources = _load(run_dir)
    if subshot_id in sources:
        info = sources[subshot_id]
        info["status"] = "failed"
        info["qa_issues"].append({
            "check": issue[0] if isinstance(issue, (list, tuple)) else "?",
            "msg": issue[1] if isinstance(issue, (list, tuple)) else str(issue),
            "phase": phase or "unknown",
        })
        info["retries"] = info.get("retries", 0) + 1
        if phase and phase not in info.get("failed_phases", []):
            info.setdefault("failed_phases", []).append(phase)
        _save(run_dir, sources)


def get_failed_subshots(run_dir, role=None):
    """Get only subshots that are still failing (excludes passed ones).
    This ensures retry only sends failed items, not already-passed ones."""
    sources = _load(run_dir)
    failed = []
    for ssid, info in sources.items():
        if info.get("status") == "failed" or info.get("status") == "pending":
            if role:
                agent_key = role + "_from"
                if info.get(agent_key) or not info.get("passed_phases"):
                    failed.append({
                        "subshot_id": ssid,
                        "issues": info.get("qa_issues", []),
                        "handoff": read_handoff(run_dir, role, [ssid], max_chars=1200) if role else read_handoff(run_dir, subshot_ids=[ssid], max_chars=1200),
                    })
            else:
                failed.append({
                    "subshot_id": ssid,
                    "issues": info.get("qa_issues", []),
                    "handoff": read_handoff(run_dir, subshot_ids=[ssid], max_chars=1200),
                })
    return failed


def get_passed_subshots(run_dir):
    """Get subshots that have passed all validation."""
    sources = _load(run_dir)
    return [ssid for ssid, info in sources.items() if info.get("status") == "passed"]


def get_source_info(run_dir, subshot_id):
    sources = _load(run_dir)
    return sources.get(subshot_id)


def reset_failed(run_dir, subshot_ids):
    sources = _load(run_dir)
    for ssid in subshot_ids:
        if ssid in sources:
            sources[ssid]["status"] = "running"
            sources[ssid]["qa_issues"] = []
    _save(run_dir, sources)


def _load(run_dir):
    path = get_sources_path(run_dir)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(run_dir, data):
    path = get_sources_path(run_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
