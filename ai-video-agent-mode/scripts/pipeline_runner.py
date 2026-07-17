"""Pipeline orchestration engine - state-driven, tick-based."""
import json, os, sys, time

if not os.environ.get("PYTHONPYCACHEPREFIX") and not getattr(sys, "pycache_prefix", None):
    sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))
from pycache_policy import block_source_pycache_until_run_dir, ensure_pycache_prefix

block_source_pycache_until_run_dir()
from pipeline_templates import GATES
from pipeline_state import (
    load_state, save_state, set_agent_id,
    mark_waiting, mark_done, mark_failed, mark_timeout, advance, init_state,
    MAX_RETRIES, TIMEOUT_SECONDS, PARALLEL_GROUPS, is_timed_out, is_agent_stale, BATCH_SIZE,
    AGENT_PHASES, LOCAL_PHASES, PHASE_BATCH_SIZE, PHASE_TIMEOUT_SECONDS
)
from sources import init_sources, set_batch_agent, get_failed_subshots, get_passed_subshots, mark_subshot_failed, mark_subshot_passed
from gate_check import check as gate_check
from agent_handoff import build_items_from_output, write_handoff
from dispatch_cache import prepare_dispatch_packet, prepare_parallel_dispatch

# Plugin registry: phase handlers extend this dict
from handler_registry import PHASE_HANDLERS

def register_handler(phase_name):
    """Decorator: register a handler function for a pipeline phase."""
    def wrapper(fn):
        PHASE_HANDLERS[phase_name] = fn
        return fn
    return wrapper


def run(run_dir):
    """One pipeline tick. Returns action dict for main agent.

    Actions:
      completed          - pipeline done
      advance            - move to next phase
      batch_spawn        - spawn multiple agents in parallel
      spawn              - spawn one agent
      waiting            - waiting for output from spawned agents
      send_back          - retry with corrections (only failed subshots)
      failed             - validation failed, retry limits not yet hit
      blocked            - pipeline cannot proceed (recovery attempted)
      recover            - agent went stale, re-spawn needed
    """
    ensure_pycache_prefix(run_dir)
    state = load_state(run_dir)
    phase = state["current_phase"]
    phase_info = state["phases"].get(phase, {})
    status = phase_info.get("status", "pending")
    phase_config = GATES.get(phase)

    if not phase_config:
        return {"action": "completed"}

    # ==== Local/script phases are executed by the main agent or registered handlers ====
    if phase in LOCAL_PHASES:
        missing = _missing_inputs(run_dir, phase_config)
        if missing:
            return {"action": "blocked", "phase": phase, "reason": "missing: %s" % missing}
        handler_result = _run_local_phase(run_dir, phase)
        if handler_result and handler_result.get("action") == "blocked":
            return handler_result
        if phase_config.get("output") and not _outputs_exist(run_dir, phase_config):
            return {
                "action": "local_action_required",
                "phase": phase,
                "role": _phase_to_role(phase),
                "expected_outputs": phase_config.get("output", []),
            }
        issues = _validate(run_dir, phase, phase_config)
        if issues:
            mark_failed(run_dir, phase)
            return {"action": "failed", "phase": phase, "issues": issues[:10]}
        mark_done(run_dir, phase)
        advance(run_dir)
        new_phase = load_state(run_dir)["current_phase"]
        return {"action": "advance", "next": new_phase, "from": phase, "local": True}

    # ==== Check if current phase is done → advance ====
    if status == "done":
        advance(run_dir)
        new_phase = load_state(run_dir)["current_phase"]
        return {"action": "advance", "next": new_phase, "from": phase}

    # ==== Check for parallel batch spawn ====
    for group_name, member_phases in PARALLEL_GROUPS.items():
        if phase == member_phases[0]:
            all_pending = all(
                state["phases"].get(m, {}).get("status", "pending") == "pending"
                for m in member_phases
            )
            if all_pending:
                preflight_issues = _run_preflight(run_dir)
                if preflight_issues:
                    return {"action": "blocked", "phase": phase, "reason": "preflight_failed", "issues": preflight_issues[:20]}
                roles = [_phase_to_role(m) for m in member_phases]
                batch_sizes = {m: PHASE_BATCH_SIZE.get(m, BATCH_SIZE) for m in member_phases}
                return {
                    "action": "batch_spawn",
                    "phases": member_phases,
                    "roles": roles,
                    "batch_sizes": batch_sizes,
                    "timeouts": {m: PHASE_TIMEOUT_SECONDS.get(m, TIMEOUT_SECONDS) for m in member_phases},
                    "dispatch_packets": prepare_parallel_dispatch(run_dir, member_phases, batch_sizes),
                }

    # ==== Timeout check (running/waiting phase exceeded 5min) ====
    if is_timed_out(run_dir, phase):
        mark_timeout(run_dir, phase)
        tc = phase_info.get("timeout_count", 0) + 1
        if tc >= 3:
            return {"action": "blocked", "phase": phase, "reason": "timeout_exhausted", "timeout_count": tc}
        return {
            "action": "spawn",
            "phase": phase,
            "role": _phase_to_role(phase),
            "reason": "timeout",
            "batch_size": PHASE_BATCH_SIZE.get(phase, BATCH_SIZE),
            "timeout": PHASE_TIMEOUT_SECONDS.get(phase, TIMEOUT_SECONDS),
            "dispatch_packet": prepare_dispatch_packet(run_dir, phase, PHASE_BATCH_SIZE.get(phase, BATCH_SIZE)),
        }

    # ==== Stale agent check (agent too old, force recovery) ====
    if is_agent_stale(run_dir, phase) and status in ("running", "waiting"):
        agent_id = phase_info.get("agent_id")
        return {"action": "recover", "phase": phase, "agent_id": agent_id, "role": _phase_to_role(phase)}

    # ==== Failed phase with retries remaining → send_back (incremental) ====
    if status == "failed" and phase_info.get("retries", 0) > 0:
        retries = phase_info.get("retries", 0)
        agent_id = phase_info.get("agent_id")
        if retries >= MAX_RETRIES:
            return {"action": "blocked", "phase": phase, "reason": "max_retries(%d)" % MAX_RETRIES}
        # Only send back subshots that still have issues
        failed = get_failed_subshots(run_dir, _phase_to_role(phase))
        passed = get_passed_subshots(run_dir)
        return {
            "action": "send_back",
            "phase": phase,
            "agent_id": agent_id,
            "shots": failed,
            "passed_count": len(passed),
            "dispatch_packet": prepare_dispatch_packet(
                run_dir,
                phase,
                PHASE_BATCH_SIZE.get(phase, BATCH_SIZE),
                [s.get("subshot_id") for s in failed],
            ),
            "respawn_fallback": True,
            "respawn_role": _phase_to_role(phase),
        }

    # ==== Missing input files ====
    missing = _missing_inputs(run_dir, phase_config)
    if missing:
        return {"action": "blocked", "phase": phase, "reason": "missing: %s" % missing}

    # ==== No agent spawned yet ====
    agent_id = phase_info.get("agent_id")
    if phase in AGENT_PHASES and not agent_id:
        return {
            "action": "spawn",
            "phase": phase,
            "role": _phase_to_role(phase),
            "batch_size": PHASE_BATCH_SIZE.get(phase, BATCH_SIZE),
            "timeout": PHASE_TIMEOUT_SECONDS.get(phase, TIMEOUT_SECONDS),
            "dispatch_packet": prepare_dispatch_packet(run_dir, phase, PHASE_BATCH_SIZE.get(phase, BATCH_SIZE)),
        }
    if phase not in AGENT_PHASES and not agent_id:
        return {"action": "blocked", "phase": phase, "reason": "phase_not_marked_agent_or_local"}

    # ==== Agent spawned but output not ready yet ====
    if not _outputs_exist(run_dir, phase_config):
        mark_waiting(run_dir, phase)
        return {"action": "waiting", "phase": phase}

    # ==== Validate agent output (100% pass rate enforced here) ====
    _update_handoff_from_outputs(run_dir, phase, phase_config)
    issues = _validate(run_dir, phase, phase_config)
    if issues:
        # Per-subshot tracking: mark passing subshots so retry only gets failures
        _track_subshot_results(run_dir, issues, phase_config)
        mark_failed(run_dir, phase)
        return {"action": "failed", "phase": phase, "issues": issues[:10]}

    # ==== Phase passed ====
    mark_done(run_dir, phase)
    advance(run_dir)
    new_phase = load_state(run_dir)["current_phase"]
    return {"action": "advance", "next": new_phase, "from": phase}


def _track_subshot_results(run_dir, issues, phase_config):
    """Mark which subshots failed vs passed for incremental retry."""
    # Get all subshot IDs from the output file
    for out in phase_config.get("output", []):
        p = _resolve_output_path(run_dir, out)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                failed_by_id = {}
                for iss in issues:
                    ssid = _parse_subshot_id(iss)
                    if ssid and ssid != "GLOBAL":
                        failed_by_id.setdefault(ssid, []).append(iss)
                for item in data.get("items", []):
                    ssid = item.get("subshot_id", "")
                    if ssid in failed_by_id:
                        first_issue = failed_by_id[ssid][0] if failed_by_id.get(ssid) else {}
                        mark_subshot_failed(run_dir, ssid, (first_issue.get("check","?"), first_issue.get("msg","")), phase_config.get("validator"))
                    elif ssid:
                        mark_subshot_passed(run_dir, ssid, phase_config.get("validator"))
            except Exception:
                pass
            break


def _update_handoff_from_outputs(run_dir, phase, phase_config):
    role = _phase_to_role(phase)
    for out in phase_config.get("output", []):
        p = _resolve_output_path(run_dir, out)
        if os.path.exists(p):
            try:
                items = build_items_from_output(p, role)
                if items:
                    write_handoff(run_dir, role, items)
            except Exception:
                pass
            break


def _parse_subshot_id(issue):
    if isinstance(issue, dict):
        for key in ["subshot_id", "ssid"]:
            val = issue.get(key)
            if isinstance(val, str) and "-" in val:
                return val
        raw = issue.get("msg", "")
    else:
        raw = str(issue)
    import re
    m = re.search(r"S\d+-\d+-\d+", raw)
    if m:
        return m.group(0)
    for part in str(raw).split():
        if "-" in part and len(part) > 4:
            return part
    for part in str(raw).replace("[", " ").replace("]", " ").split():
        if "-" in part and len(part) > 4:
            return part
    return "GLOBAL"


def _phase_to_role(phase):
    m = {
        "emotion_analysis": "emotion_analysis",
        "scene_analysis": "scene_analysis",
        "camera_movement": "camera_movement",
        "qa_integration": "qa_integration",
        "prompt_composer": "prompt",
    }
    return m.get(phase, phase)


def _missing_inputs(run_dir, config):
    missing = []
    for inp in config.get("input", []):
        if not os.path.exists(_resolve_input_path(run_dir, inp)):
            missing.append(inp)
    return missing


def _outputs_exist(run_dir, config):
    for out in config.get("output", []):
        if not os.path.exists(_resolve_output_path(run_dir, out)):
            return False
    return True


def _resolve_input_path(run_dir, path):
    if path == "project_config.json":
        return os.path.join(run_dir, path)
    if path.startswith(".cache") or os.path.isabs(path):
        return os.path.join(run_dir, path) if not os.path.isabs(path) else path
    return os.path.join(run_dir, path)


def _resolve_output_path(run_dir, path):
    if path == "project_config.json":
        return os.path.join(run_dir, path)
    if path.startswith(".cache") or os.path.isabs(path):
        return os.path.join(run_dir, path) if not os.path.isabs(path) else path
    return os.path.join(run_dir, ".cache", path)


def _run_local_phase(run_dir, phase):
    if phase == "qa_integration":
        _assemble_analysis(run_dir)
    elif phase == "continuity":
        from continuity_check import run as continuity_run
        warnings, errors, issues = continuity_run(run_dir, dry=False)
        if errors:
            return {"action": "blocked", "phase": phase, "reason": "continuity_errors", "issues": issues}
    elif phase == "validate":
        from hybrid_gate import run as hybrid_gate
        result = hybrid_gate(run_dir, phase="validate", require_llm=False)
        if not result.get("pass", False):
            return {"action": "blocked", "phase": phase, "reason": "hybrid_gate_failed", "issues": result.get("issues", [])}
    return None


def _run_preflight(run_dir):
    from preflight_check import run as preflight_run
    return preflight_run(run_dir)


def _validate(run_dir, phase, config):
    """Run gate check. Returns blocking issues or empty list."""
    gc = gate_check(run_dir, phase, strict=False)
    if gc["bypass_detected"]:
        return [{"check": "BYPASS", "severity": "blocking", "msg": "Output existed before agent spawn"}]
    return [i for i in gc["issues"] if i["severity"] == "blocking"]


def _assemble_analysis(run_dir):
    """Phase assembly: uses registered handlers or default fallback.

    Phase handlers are registered via @register_handler(phase_name).
    If no handler registered for a phase, this function does nothing.
    """
    state = load_state(run_dir)
    phase = state["current_phase"]
    handler = PHASE_HANDLERS.get(phase)
    if handler:
        return handler(run_dir)
    # Default: old hardcoded assemble logic for backward compat
    if phase == "qa_integration":
        _default_assemble(run_dir)


def _default_assemble(run_dir):
    """Default qa_integration handler (hardcoded emotion+scene+camera merge).
    Replace by registering a handler for "qa_integration" phase."""
    from assemble_director import run as assemble_director
    paths = {
        "emotion": os.path.join(run_dir, ".cache", "analysis", "emotion_output.json"),
        "scene": os.path.join(run_dir, ".cache", "analysis", "scene_output.json"),
        "camera": os.path.join(run_dir, ".cache", "analysis", "camera_output.json"),
        "plan": os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"),
    }
    out = os.path.join(run_dir, ".cache", "director", "director_pass.json")
    ep = paths["emotion"] if os.path.exists(paths["emotion"]) else None
    sp = paths["scene"] if os.path.exists(paths["scene"]) else None
    cp = paths["camera"] if os.path.exists(paths["camera"]) else None
    if os.path.exists(paths["plan"]):
        pcfg = os.path.join(run_dir, "..", "project_config.json")
        assemble_director(ep, sp, cp, paths["plan"], out,
                          project_config_path=pcfg if os.path.exists(pcfg) else None)
