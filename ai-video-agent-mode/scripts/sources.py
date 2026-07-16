"""Shot-level traceability - tracks which agent produced which subshot."""
import json, os


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
                "emotion_analysis_from": None,
                "scene_analysis_from": None,
                "camera_movement_from": None,
                "qa_issues": []
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


def mark_subshot_failed(run_dir, subshot_id, issue):
    sources = _load(run_dir)
    if subshot_id in sources:
        sources[subshot_id]["status"] = "failed"
        sources[subshot_id]["qa_issues"].append(list(issue))
        sources[subshot_id]["retries"] += 1
        _save(run_dir, sources)


def get_failed_subshots(run_dir, role=None):
    sources = _load(run_dir)
    failed = []
    for ssid, info in sources.items():
        if info["status"] == "failed":
            if role:
                agent_key = role + "_from"
                if info.get(agent_key):
                    failed.append({"subshot_id": ssid, "issues": info["qa_issues"]})
            else:
                failed.append({"subshot_id": ssid, "issues": info["qa_issues"]})
    return failed


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