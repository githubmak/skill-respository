"""Pipeline state machine - phase progress, retries, agent ID tracking."""
import json, os, time

from contract_registry import (
    AGENT_PHASE_NAMES,
    LOCAL_PHASE_NAMES,
    PHASE_BATCH_SIZE as CONTRACT_PHASE_BATCH_SIZE,
    PHASE_TIMEOUT_SECONDS as CONTRACT_PHASE_TIMEOUT_SECONDS,
    PIPELINE_CONTRACT_VERSION,
    PIPELINE_PHASES,
)
from pipeline_deadline import ensure_state_contract
from pipeline_runtime import atomic_json, json_lock
from dispatch_progress import apply_progress

# ========== Constants ==========
MAX_RETRIES = 3          # Block when failure count reaches 3: initial attempt + 2 retries
TIMEOUT_SECONDS = 900    # Default sub-agent timeout
# A worker must never be declared stale before its phase can time out.  The
# former 600s global threshold caused duplicate dispatches for 900s phases.
AGENT_STALE_GRACE_SECONDS = 300
BATCH_SIZE = 12          # Safe default; phase-specific sizes are below.
CORE_PIPELINE_TARGET_SECONDS = 55 * 60  # 50 main shots

PHASE_TIMEOUT_SECONDS = dict(CONTRACT_PHASE_TIMEOUT_SECONDS)
PHASE_BATCH_SIZE = dict(CONTRACT_PHASE_BATCH_SIZE)
AGENT_PHASES = set(AGENT_PHASE_NAMES)
LOCAL_PHASES = set(LOCAL_PHASE_NAMES)
PHASE_ORDER = list(PIPELINE_PHASES)

# Phases that can be spawned in parallel (group name -> member phases)
PARALLEL_GROUPS = {}


def get_state_path(run_dir):
    return os.path.join(run_dir, ".cache", "pipeline_state.json")


def init_state(run_dir):
    path = get_state_path(run_dir)
    if os.path.exists(path):
        return
    state = {
        "pipeline_contract_version": PIPELINE_CONTRACT_VERSION,
        "pipeline_started_at": time.time(),
        "core_pipeline_target_seconds": CORE_PIPELINE_TARGET_SECONDS,
        "current_phase": PHASE_ORDER[0],
        "phase_order": PHASE_ORDER,
        "phases": {p: {"status": "pending", "agent_id": None, "retries": 0, "spawn_time": None, "timeout_count": 0} for p in PHASE_ORDER}
    }
    ensure_state_contract(state)
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
    before_deadline = (
        state.get("pipeline_deadline_seconds"), state.get("pipeline_deadline_at"),
        state.get("pipeline_status"),
    )
    ensure_state_contract(state)
    changed = before_deadline != (
        state.get("pipeline_deadline_seconds"), state.get("pipeline_deadline_at"),
        state.get("pipeline_status"),
    )
    state_contract_version = state.get("pipeline_contract_version")
    if not state_contract_version:
        state["pipeline_contract_version"] = PIPELINE_CONTRACT_VERSION
        changed = True
    elif state_contract_version != PIPELINE_CONTRACT_VERSION:
        raise ValueError(
            "pipeline state contract mismatch: %s != %s"
            % (state_contract_version, PIPELINE_CONTRACT_VERSION)
        )
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
    atomic_json(path, state)


def set_agent_id(run_dir, phase, agent_id, dispatch_id=None, spawn_time=None, status="running"):
    # Several packets may be registered at once. Serialize the full
    # read-modify-write so one worker cannot erase another dispatch record.
    with json_lock(get_state_path(run_dir)):
        state = load_state(run_dir)
        now = float(spawn_time) if isinstance(spawn_time, (int, float)) else time.time()
        phase_state = state["phases"][phase]
        phase_state["agent_id"] = agent_id
        phase_state["status"] = "running"
        # Preserve the first worker start as the phase wall-clock origin.  A
        # later packet registration must not make earlier queue waves disappear
        # from performance telemetry.
        if not isinstance(phase_state.get("started_at"), (int, float)):
            phase_state["started_at"] = now
        if status == "running" and not isinstance(phase_state.get("spawn_time"), (int, float)):
            phase_state["spawn_time"] = now
        if status == "running":
            phase_state["heartbeat_at"] = now
        if dispatch_id:
            existing = phase_state.setdefault("dispatches", {}).get(dispatch_id, {})
            entry = {
                "agent_id": agent_id,
                "status": status,
                "spawn_time": now if status == "running" else None,
                "heartbeat_at": now if status == "running" else None,
                "output_bytes": 0,
                "completed_item_count": 0,
                "progress_count": 0,
                "first_progress_at": None,
                "last_progress_at": None,
            }
            if status == "leased":
                entry["leased_at"] = now
            for key in ("lease_id", "lease_position", "lease_size"):
                if key in existing:
                    entry[key] = existing[key]
            phase_state["dispatches"][dispatch_id] = entry
        save_state(run_dir, state)


def reserve_dispatch_lease(run_dir, phase, agent_id, lease_id, packet_records, leased_at=None):
    """Bind one real worker to queued packets without starting packet timers."""
    with json_lock(get_state_path(run_dir)):
        state = load_state(run_dir)
        now = float(leased_at) if isinstance(leased_at, (int, float)) else time.time()
        phase_state = state["phases"][phase]
        phase_state["status"] = "running"
        phase_state["agent_id"] = agent_id
        if not isinstance(phase_state.get("started_at"), (int, float)):
            phase_state["started_at"] = now
        dispatches = phase_state.setdefault("dispatches", {})
        size = len(packet_records)
        for position, record in enumerate(packet_records, 1):
            dispatch_id = str(record.get("dispatch_id", "") or "")
            if not dispatch_id:
                raise ValueError("lease packet is missing dispatch_id")
            current = dispatches.get(dispatch_id, {})
            if current.get("status") in {"running", "waiting", "done", "partial"}:
                raise ValueError("dispatch is already active or complete: " + dispatch_id)
            dispatches[dispatch_id] = {
                "agent_id": agent_id,
                "status": "leased",
                "leased_at": now,
                "lease_id": lease_id,
                "lease_position": position,
                "lease_size": size,
                "spawn_time": None,
                "heartbeat_at": None,
                "output_bytes": 0,
                "completed_item_count": 0,
                "progress_count": 0,
                "first_progress_at": None,
                "last_progress_at": None,
            }
        save_state(run_dir, state)


def start_leased_dispatch(run_dir, phase, agent_id, dispatch_id, started_at=None):
    """Start the absolute timeout only when a leased packet begins execution."""
    with json_lock(get_state_path(run_dir)):
        state = load_state(run_dir)
        entry = state["phases"][phase].get("dispatches", {}).get(dispatch_id)
        if not isinstance(entry, dict) or entry.get("status") != "leased":
            raise ValueError("dispatch is not leased: " + str(dispatch_id))
        if entry.get("agent_id") != agent_id:
            raise ValueError("agent_id does not own leased dispatch")
        now = float(started_at) if isinstance(started_at, (int, float)) else time.time()
        entry["status"] = "running"
        entry["spawn_time"] = now
        entry["heartbeat_at"] = None
        state["phases"][phase]["spawn_time"] = min(
            value for value in (
                state["phases"][phase].get("spawn_time"), now
            ) if isinstance(value, (int, float))
        )
        save_state(run_dir, state)
        return now


def record_heartbeat(run_dir, phase, agent_id=None, dispatch_id=None, progress=None, observed_at=None):
    """Record a real worker liveness signal without changing phase outcome."""
    with json_lock(get_state_path(run_dir)):
        state = load_state(run_dir)
        now = float(observed_at) if isinstance(observed_at, (int, float)) else time.time()
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
            apply_progress(dispatch, progress, now)
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


def mark_pipeline_complete(run_dir):
    """Persist the terminal state after the final validated export."""
    state = load_state(run_dir)
    final_phase = state.get("phase_order", PHASE_ORDER)[-1]
    final_completed_at = state.get("phases", {}).get(final_phase, {}).get("completed_at")
    completed_at = (
        float(final_completed_at)
        if isinstance(final_completed_at, (int, float))
        else time.time()
    )
    state["pipeline_status"] = "completed"
    state["pipeline_completed_at"] = completed_at
    started_at = state.get("pipeline_started_at")
    if isinstance(started_at, (int, float)):
        state["pipeline_elapsed_seconds"] = round(max(completed_at - started_at, 0), 3)
    save_state(run_dir, state)
    return state


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

    Prefer the latest heartbeat and fall back to ``spawn_time`` for migrated
    runs. A genuine stale recovery stays later than normal timeout handling.
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
        state["current_phase"] = next_phase
        save_state(run_dir, state)
        print("[STATE] %s -> %s" % (current, next_phase))
        return
