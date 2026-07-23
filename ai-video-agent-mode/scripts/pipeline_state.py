"""Pipeline state machine - phase progress, retries, agent ID tracking."""
import json, os, time

# ========== Constants ==========
MAX_RETRIES = 3          # Block when failure count reaches 3: initial attempt + 2 retries
TIMEOUT_SECONDS = 900    # Default sub-agent timeout
# A worker must never be declared stale before its phase can time out.  The
# former 600s global threshold caused duplicate dispatches for 900s phases.
AGENT_STALE_GRACE_SECONDS = 300
BATCH_SIZE = 12          # Safe default; phase-specific sizes are below.
CORE_PIPELINE_TARGET_SECONDS = 55 * 60  # 50 main shots, excludes optional grid

PHASE_TIMEOUT_SECONDS = {
    "scene_lock": 480,
    "master_production": 720,
    "editor_pass2": 480,
}

PHASE_BATCH_SIZE = {
    "scene_lock": 1,
    "master_production": 6,
    "editor_pass2": 10,
}  # Preserve continuity groups; reduce oversized analysis tasks and Composer setup overhead.

AGENT_PHASES = {
    "scene_lock",
    "master_production",
    "editor_pass2",
}

LOCAL_PHASES = {
    "user_confirm",
    "orchestrator",
    "editor_pass1",
    "grid_storyboard",
    "validate",
    "export",
}

PHASE_ORDER = [
    "user_confirm", "orchestrator",
    "scene_lock", "master_production",
    "editor_pass1", "editor_pass2", "grid_storyboard", "validate", "export"
]

# Phases that can be spawned in parallel (group name -> member phases)
PARALLEL_GROUPS = {}


def get_state_path(run_dir):
    return os.path.join(run_dir, ".cache", "pipeline_state.json")


def init_state(run_dir):
    path = get_state_path(run_dir)
    if os.path.exists(path):
        return
    state = {
        "pipeline_started_at": time.time(),
        "core_pipeline_target_seconds": CORE_PIPELINE_TARGET_SECONDS,
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
        state = json.load(f)
    changed = False
    for phase in PHASE_ORDER:
        if phase not in state.get("phases", {}):
            state.setdefault("phases", {})[phase] = {
                "status": "pending", "agent_id": None, "retries": 0,
                "spawn_time": None, "timeout_count": 0,
            }
            changed = True
    if state.get("phase_order") != PHASE_ORDER:
        state["phase_order"] = PHASE_ORDER
        changed = True
    if changed:
        save_state(run_dir, state)
    return state


def save_state(run_dir, state):
    path = get_state_path(run_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def set_agent_id(run_dir, phase, agent_id, dispatch_id=None):
    state = load_state(run_dir)
    now = time.time()
    phase_state = state["phases"][phase]
    phase_state["agent_id"] = agent_id
    phase_state["status"] = "running"
    phase_state["spawn_time"] = now
    phase_state["heartbeat_at"] = now
    if dispatch_id:
        phase_state.setdefault("dispatches", {})[dispatch_id] = {
            "agent_id": agent_id,
            "status": "running",
            "spawn_time": now,
            "heartbeat_at": now,
        }
    save_state(run_dir, state)


def record_heartbeat(run_dir, phase, agent_id=None, dispatch_id=None):
    """Record a real worker liveness signal without changing phase outcome."""
    state = load_state(run_dir)
    now = time.time()
    entry = state["phases"][phase]
    # A phase can own several concurrent dispatches.  The phase-level id is
    # only a legacy summary; dispatch ownership is the authoritative check.
    if not dispatch_id and agent_id and entry.get("agent_id") and entry.get("agent_id") != agent_id:
        raise ValueError("agent_id does not own phase")
    entry["heartbeat_at"] = now
    if dispatch_id:
        dispatch = entry.get("dispatches", {}).get(dispatch_id)
        if not isinstance(dispatch, dict):
            raise ValueError("unknown dispatch_id")
        if agent_id and dispatch.get("agent_id") != agent_id:
            raise ValueError("agent_id does not own dispatch")
        dispatch["heartbeat_at"] = now
    save_state(run_dir, state)
    return now


def mark_started(run_dir, phase):
    """Record local-phase timing without affecting validation or ordering."""
    state = load_state(run_dir)
    entry = state["phases"][phase]
    entry["started_at"] = time.time()
    entry["status"] = "running"
    save_state(run_dir, state)


def mark_waiting(run_dir, phase):
    state = load_state(run_dir)
    state["phases"][phase]["status"] = "waiting"
    save_state(run_dir, state)


def mark_done(run_dir, phase):
    state = load_state(run_dir)
    entry = state["phases"][phase]
    completed_at = time.time()
    entry["status"] = "done"
    entry["completed_at"] = completed_at
    started_at = entry.get("started_at", entry.get("spawn_time"))
    if isinstance(started_at, (int, float)):
        entry["elapsed_seconds"] = round(max(completed_at - started_at, 0), 3)
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
    """Check only after the phase timeout plus a recovery grace period.

    The state format has no heartbeat timestamp yet, so using ``spawn_time``
    before the phase timeout would create a duplicate worker.  A genuine stale
    recovery is therefore deliberately later than normal timeout handling.
    """
    state = load_state(run_dir)
    info = state["phases"].get(phase, {})
    heartbeat = info.get("heartbeat_at", info.get("spawn_time"))
    if not heartbeat:
        return False
    elapsed = time.time() - heartbeat
    threshold = AGENT_STALE_GRACE_SECONDS
    return elapsed > threshold


def advance(run_dir):
    state = load_state(run_dir)
    order = state["phase_order"]
    current = state["current_phase"]
    idx = order.index(current)
    while idx < len(order) - 1:
        idx += 1
        next_phase = order[idx]
        if _skip_optional_phase(run_dir, next_phase):
            state["phases"][next_phase]["status"] = "skipped"
            print("[STATE] skip optional phase: %s" % next_phase)
            continue
        state["current_phase"] = next_phase
        save_state(run_dir, state)
        print("[STATE] %s -> %s" % (current, next_phase))
        return


def _skip_optional_phase(run_dir, phase):
    if phase != "grid_storyboard":
        return False
    config_path = os.path.join(run_dir, "project_config.json")
    if not os.path.exists(config_path):
        return True
    try:
        with open(config_path, "r", encoding="utf-8-sig") as handle:
            config = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return True
    grid = config.get("storyboard_grid", {})
    return not isinstance(grid, dict) or grid.get("enabled") is not True
