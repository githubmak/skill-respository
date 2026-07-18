"""Pipeline state machine - phase progress, retries, agent ID tracking."""
import json, os, time

# ========== Constants ==========
MAX_RETRIES = 3          # Sub-agent retries before escalation (3 attempts: initial + 2 retries)
TIMEOUT_SECONDS = 480    # Default sub-agent timeout
TOTAL_ATTEMPTS = 5       # 1 initial + 4 retries
AGENT_STALE_SECONDS = 600  # 10min: agent considered stale, force re-spawn
BATCH_SIZE = 60          # Max subshots per sub-agent spawn (balanced quality/efficiency)

PHASE_TIMEOUT_SECONDS = {
    "emotion_analysis": 900,  # kept high for quality
    "scene_analysis": 900,
    "camera_movement": 900,
    "prompt_composer": 900,
}

PHASE_BATCH_SIZE = {"prompt_composer": 8}  # Natural language generation is slow; 30/batch prevents timeout

AGENT_PHASES = {
    "emotion_analysis",
    "scene_analysis",
    "camera_movement",
    "prompt_composer",
    "editor_pass2",
}

LOCAL_PHASES = {
    "user_confirm",
    "orchestrator",
    "qa_integration", "enrich_prompt",
    "director",
    "continuity",
    "editor_pass1",
    "validate",
    "export",
}

PHASE_ORDER = [
    "user_confirm", "orchestrator",
    "emotion_analysis", "scene_analysis", "camera_movement",
    "qa_integration", "enrich_prompt",
    "director",
    "continuity", "prompt_composer",
    "editor_pass1", "editor_pass2", "validate", "export"
]

# Phases that can be spawned in parallel (group name -> member phases)
PARALLEL_GROUPS = {
    "analysis_group": ["emotion_analysis", "scene_analysis", "camera_movement"],
}


def get_state_path(run_dir):
    return os.path.join(run_dir, ".cache", "pipeline_state.json")


def init_state(run_dir):
    path = get_state_path(run_dir)
    if os.path.exists(path):
        return
    state = {
        "current_phase": PHASE_ORDER[0],
        "phase_order": PHASE_ORDER,
        "phases": {p: {"status": "pending", "agent_id": None, "retries": 0, "spawn_time": None, "timeout_count": 0} for p in PHASE_ORDER}
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print("[STATE] initialized: %s" % PHASE_ORDER[0])


def load_state(run_dir):
    path = get_state_path(run_dir)
    if not os.path.exists(path):
        init_state(run_dir)
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_state(run_dir, state):
    path = get_state_path(run_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def set_agent_id(run_dir, phase, agent_id):
    state = load_state(run_dir)
    state["phases"][phase]["agent_id"] = agent_id
    state["phases"][phase]["status"] = "running"
    state["phases"][phase]["spawn_time"] = time.time()
    save_state(run_dir, state)


def mark_waiting(run_dir, phase):
    state = load_state(run_dir)
    state["phases"][phase]["status"] = "waiting"
    save_state(run_dir, state)


def mark_done(run_dir, phase):
    state = load_state(run_dir)
    state["phases"][phase]["status"] = "done"
    save_state(run_dir, state)


def mark_failed(run_dir, phase):
    state = load_state(run_dir)
    state["phases"][phase]["status"] = "failed"
    state["phases"][phase]["retries"] += 1
    save_state(run_dir, state)


def mark_timeout(run_dir, phase):
    """Mark a phase as timed out and increment timeout counter."""
    state = load_state(run_dir)
    state["phases"][phase]["status"] = "timeout"
    state["phases"][phase]["timeout_count"] = state["phases"][phase].get("timeout_count", 0) + 1
    save_state(run_dir, state)


def is_timed_out(run_dir, phase):
    """Check if a running phase has exceeded the timeout."""
    state = load_state(run_dir)
    info = state["phases"].get(phase, {})
    spawn_time = info.get("spawn_time")
    if not spawn_time or info.get("status") not in ("running", "waiting"):
        return False
    elapsed = time.time() - spawn_time
    return elapsed > PHASE_TIMEOUT_SECONDS.get(phase, TIMEOUT_SECONDS)


def is_agent_stale(run_dir, phase):
    """Check if a spawned agent has gone stale (no update for too long)."""
    state = load_state(run_dir)
    info = state["phases"].get(phase, {})
    spawn_time = info.get("spawn_time")
    if not spawn_time:
        return False
    elapsed = time.time() - spawn_time
    return elapsed > AGENT_STALE_SECONDS


def advance(run_dir):
    state = load_state(run_dir)
    order = state["phase_order"]
    current = state["current_phase"]
    idx = order.index(current)
    if idx < len(order) - 1:
        state["current_phase"] = order[idx + 1]
        save_state(run_dir, state)
        print("[STATE] %s -> %s" % (current, order[idx + 1]))
