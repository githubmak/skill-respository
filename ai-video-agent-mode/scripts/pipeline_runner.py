"""Pipeline orchestration engine - state-driven, tick-based."""
import hashlib, json, os, sys, time

if not os.environ.get("PYTHONPYCACHEPREFIX") and not getattr(sys, "pycache_prefix", None):
    sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))
from pycache_policy import block_source_pycache_until_run_dir, ensure_pycache_prefix

block_source_pycache_until_run_dir()
from pipeline_templates import GATES
from pipeline_state import (
    load_state, save_state, set_agent_id,
    mark_waiting, mark_done, mark_failed, mark_timeout, mark_started, advance, init_state,
    MAX_RETRIES, TIMEOUT_SECONDS, PARALLEL_GROUPS, is_timed_out, is_agent_stale, BATCH_SIZE,
    AGENT_PHASES, LOCAL_PHASES, PHASE_BATCH_SIZE, PHASE_TIMEOUT_SECONDS
)
from sources import init_sources, set_batch_agent, get_failed_subshots, get_passed_subshots, mark_subshot_failed, mark_subshot_passed
from gate_check import check as gate_check
from agent_handoff import build_items_from_output, write_handoff
from dispatch_cache import prepare_dispatch_packet, prepare_dispatch_packets, prepare_parallel_dispatch
from merge_agent_outputs import merge_agent_outputs
from record_batch_provenance import verify as verify_batch_provenance
from resolve_run_mode import resolve as resolve_run_mode

# Plugin registry: phase handlers extend this dict
from handler_registry import PHASE_HANDLERS
import assemble_director  # registers qa_integration handler
import generate_grid_storyboards  # registers optional grid_storyboard handler

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

    # Phase 0 is an explicit configuration handshake, never an inference from
    # an old file name or cache.  Resume is used here because route_task has
    # already selected the fresh run versus reuse policy before the state file
    # is initialized.
    if phase == "user_confirm":
        initialization = resolve_run_mode("full", run_dir, "resume")
        if initialization.get("requires_user_confirm"):
            return {
                "action": "needs_user_confirm",
                "phase": phase,
                "questions": initialization.get("questions", []),
            }
        if initialization.get("blocking"):
            return {
                "action": "blocked",
                "phase": phase,
                "reason": "initialization_invalid",
                "issues": initialization["blocking"],
            }

    if phase == "emotion_analysis" and status == "pending" and not _emotion_analysis_required(run_dir):
        _write_empty_emotion_output(run_dir)
        mark_done(run_dir, phase)
        _write_stage_summary(run_dir, phase, phase_config)
        advance(run_dir)
        return {"action": "advance", "next": load_state(run_dir)["current_phase"], "from": phase, "skipped": "no_character_performance"}

    # ==== Local/script phases are executed by the main agent or registered handlers ====
    if phase in LOCAL_PHASES:
        missing = _missing_inputs(run_dir, phase_config)
        if missing:
            return {"action": "blocked", "phase": phase, "reason": "missing: %s" % missing}
        mark_started(run_dir, phase)
        handler_result = _run_local_phase(run_dir, phase)
        if handler_result and handler_result.get("action") in ("blocked", "auto_repair"):
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
        _merge_batch_outputs(run_dir, phase)
        mark_done(run_dir, phase)
        _write_stage_summary(run_dir, phase, phase_config)
        advance(run_dir)
        new_phase = load_state(run_dir)["current_phase"]
        return {"action": "advance", "next": new_phase, "from": phase, "local": True}

    # ==== Check if current phase is done → advance ====
    if status == "done":
        # Provenance recording marks a worker phase done before the public
        # aggregate exists. Always materialize it here before advancing.
        if phase == "prompt_composer" and not _verified_phase_batches(run_dir, phase):
            return {"action": "blocked", "phase": phase, "reason": "partial_or_unverified_composer_batches"}
        _merge_batch_outputs(run_dir, phase)
        if phase_config.get("output") and not _outputs_exist(run_dir, phase_config):
            return {"action": "blocked", "phase": phase, "reason": "verified_batches_missing_public_merge"}
        if phase == "editor_pass2":
            semantic_repair = _route_semantic_repair(run_dir)
            if semantic_repair:
                return semantic_repair
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

    # ==== Timeout check (running/waiting phase exceeded its configured limit) ====
    if is_timed_out(run_dir, phase):
        mark_timeout(run_dir, phase)
        tc = phase_info.get("timeout_count", 0) + 1
        if tc >= 3:
            return {"action": "blocked", "phase": phase, "reason": "timeout_exhausted", "timeout_count": tc}
        dispatch_packets = prepare_dispatch_packets(run_dir, phase, PHASE_BATCH_SIZE.get(phase, BATCH_SIZE))
        return {
            "action": "spawn",
            "phase": phase,
            "role": _phase_to_role(phase),
            "reason": "timeout",
            "batch_size": PHASE_BATCH_SIZE.get(phase, BATCH_SIZE),
            "timeout": PHASE_TIMEOUT_SECONDS.get(phase, TIMEOUT_SECONDS),
            "dispatch_packet": dispatch_packets[0] if dispatch_packets else None,
            "dispatch_packets": dispatch_packets,
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
        retry_mode = "validator_targeted" if retries == 1 else "single_subshot_field_repair"
        retry_batch_size = 1 if retries >= 2 else PHASE_BATCH_SIZE.get(phase, BATCH_SIZE)
        retry_ids = [shot.get("subshot_id") for shot in failed if shot.get("subshot_id")]
        retry_packets = prepare_dispatch_packets(run_dir, phase, retry_batch_size, retry_ids)
        return {
            "action": "send_back",
            "phase": phase,
            "agent_id": agent_id,
            "shots": failed,
            "passed_count": len(passed),
            "retry_mode": retry_mode,
            "batch_size": retry_batch_size,
            "dispatch_packet": retry_packets[0] if retry_packets else None,
            "dispatch_packets": retry_packets,
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
        repair_scope = phase_info.get("repair_scope", [])
        dispatch_packets = prepare_dispatch_packets(run_dir, phase, PHASE_BATCH_SIZE.get(phase, BATCH_SIZE), repair_scope or None)
        review_packet = None
        if phase == "editor_pass2":
            from hybrid_gate import run as hybrid_gate
            review = hybrid_gate(run_dir, phase="editor_pass2", require_llm=False)
            if not review.get("pass", False):
                return {"action": "blocked", "phase": phase, "reason": "deterministic_qa_failed_before_semantic_review", "issues": review.get("issues", [])}
            review_packet = review.get("llm_review_packet")
        return {
            "action": "spawn",
            "phase": phase,
            "role": _phase_to_role(phase),
            "batch_size": PHASE_BATCH_SIZE.get(phase, BATCH_SIZE),
            "timeout": PHASE_TIMEOUT_SECONDS.get(phase, TIMEOUT_SECONDS),
            "dispatch_packet": dispatch_packets[0] if dispatch_packets else None,
            "dispatch_packets": dispatch_packets,
            "review_packet": review_packet,
        }
    if phase not in AGENT_PHASES and not agent_id:
        return {"action": "blocked", "phase": phase, "reason": "phase_not_marked_agent_or_local"}

    # ==== Agent spawned but output not ready yet ====
    # Always rematerialize from verified batches before validation so a retry
    # cannot be hidden behind an old public aggregate. A partial Composer batch
    # is not publishable until every failed subshot has a verified replacement.
    if phase == "prompt_composer" and not _verified_phase_batches(run_dir, phase):
        mark_waiting(run_dir, phase)
        return {"action": "waiting", "phase": phase, "reason": "partial_or_unverified_composer_batches"}
    _merge_batch_outputs(run_dir, phase)
    if not _outputs_exist(run_dir, phase_config):
        mark_waiting(run_dir, phase)
        return {"action": "waiting", "phase": phase}

    # A semantic review can send only the affected subshots to the earliest
    # responsible phase.  Downstream public artefacts are rebuilt afterwards.
    if phase == "editor_pass2":
        semantic_repair = _route_semantic_repair(run_dir)
        if semantic_repair:
            return semantic_repair

    # ==== Validate agent output (100% pass rate enforced here) ====
    _update_handoff_from_outputs(run_dir, phase, phase_config)
    issues = _validate(run_dir, phase, phase_config)
    if issues:
        # Per-subshot tracking: mark passing subshots so retry only gets failures
        _track_subshot_results(run_dir, issues, phase_config)
        mark_failed(run_dir, phase)
        return {"action": "failed", "phase": phase, "issues": issues[:10]}

    # ==== Phase passed ====
    _merge_batch_outputs(run_dir, phase)
    mark_done(run_dir, phase)
    _write_stage_summary(run_dir, phase, phase_config)
    advance(run_dir)
    new_phase = load_state(run_dir)["current_phase"]
    return {"action": "advance", "next": new_phase, "from": phase}



def _merge_batch_outputs(run_dir, phase):
    """Materialize a public phase output only from verified packet batches.

    Packet paths are authoritative: worker filenames intentionally carry a
    dispatch id and must never be guessed with a legacy glob.  Batch artefacts
    stay on disk so every public merge remains auditable and retry-safe.
    """
    phase_config = GATES.get(phase, {})
    outputs = phase_config.get("output", [])
    if not outputs:
        return
    main_out = _resolve_output_path(run_dir, outputs[0])
    batch_files = _verified_phase_batches(run_dir, phase)
    if not batch_files:
        return
    if phase == "editor_pass2":
        # Semantic review is a singleton contract, not an items/shots package.
        # Preserve its hash-bound result verbatim from the newest verified run.
        with open(batch_files[-1], "r", encoding="utf-8-sig") as handle:
            review = json.load(handle)
        os.makedirs(os.path.dirname(main_out), exist_ok=True)
        with open(main_out, "w", encoding="utf-8") as handle:
            json.dump(review, handle, ensure_ascii=False, indent=2)
        print("[MERGE] semantic review -> %s" % main_out)
        return
    stats = merge_agent_outputs(main_out, *batch_files, require_provenance=True)
    if stats.get("invalid_provenance"):
        print("[MERGE] public output not materialized: unverified batches remain")


def _verified_phase_batches(run_dir, phase):
    # A freshly dispatched repair must finish before old verified batches can
    # materialize a public output again. This prevents a stale package from
    # racing ahead of the worker that is replacing it.
    state = load_state(run_dir)
    dispatches = state.get("phases", {}).get(phase, {}).get("dispatches", {})
    if any(
        isinstance(entry, dict) and entry.get("status") in ("running", "waiting")
        for entry in dispatches.values()
    ):
        return []
    dispatch_dir = os.path.join(run_dir, ".cache", "dispatch")
    if not os.path.isdir(dispatch_dir):
        return []
    packets = []
    for name in os.listdir(dispatch_dir):
        if not name.endswith("_packet.json"):
            continue
        path = os.path.join(dispatch_dir, name)
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                packet = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if packet.get("contract_version") == "modec-v4" and packet.get("phase") == phase:
            packets.append(packet)
    packets.sort(key=lambda packet: (float(packet.get("created_at", 0) or 0), packet.get("dispatch_id", "")))
    records = []
    for packet in packets:
        path = str(packet.get("_batch_output_path", "") or "")
        if not path or not os.path.exists(path):
            continue
        verified, reason, manifest = verify_batch_provenance(path)
        if not verified:
            print("[MERGE] waiting for verified %s batch: %s" % (phase, reason))
            continue
        records.append((packet, path, manifest or {}))
    # A partial Composer batch may carry successful records forward, but its
    # failed records cannot be omitted from the phase. Wait until later retry
    # batches have verified every failed subshot before exposing any aggregate.
    if phase == "prompt_composer":
        for index, (packet, _path, manifest) in enumerate(records):
            if manifest.get("validation_mode") != "partial":
                continue
            failed = set(manifest.get("failed_subshot_ids", []))
            repaired = set()
            for _later_packet, _later_path, later_manifest in records[index + 1:]:
                repaired.update(later_manifest.get("validated_subshot_ids", []))
            unresolved = sorted(failed - repaired)
            if unresolved:
                print("[MERGE] waiting for Composer retries: %s" % ", ".join(unresolved))
                return []
    return [path for _packet, path, _manifest in records]


def _route_semantic_repair(run_dir):
    """Invalidate only the necessary suffix of the pipeline for LLM findings."""
    path = os.path.join(run_dir, ".cache", "review", "llm_gate_result.json")
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            review = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    from hybrid_gate import run as hybrid_gate
    gate = hybrid_gate(run_dir, phase="editor_pass2", require_llm=True)
    if not gate.get("llm_review_result"):
        return {"action": "blocked", "phase": "editor_pass2", "reason": "stale_or_unverified_semantic_review", "issues": gate.get("issues", [])}
    targets = [target for target in review.get("repair_targets", []) if isinstance(target, dict)]
    if not targets:
        return None
    allowed = {"emotion_analysis", "scene_analysis", "camera_movement", "prompt_composer"}
    grouped = {}
    for target in targets:
        phase = target.get("send_back_to")
        sid = target.get("subshot_id")
        if phase in allowed and isinstance(sid, str) and sid:
            grouped.setdefault(phase, []).append(sid)
    if not grouped:
        return {"action": "blocked", "phase": "editor_pass2", "reason": "invalid_semantic_repair_targets"}
    # An upstream correction invalidates only its causal dependants. Persist
    # exact scopes so the normal dispatcher never expands a semantic repair to
    # the entire scene.
    scopes = {phase: sorted(set(ids)) for phase, ids in grouped.items()}
    for upstream, downstream in (("emotion_analysis", "camera_movement"), ("emotion_analysis", "prompt_composer"),
                                 ("scene_analysis", "camera_movement"), ("scene_analysis", "prompt_composer"),
                                 ("camera_movement", "prompt_composer")):
        if upstream in scopes:
            scopes.setdefault(downstream, [])
            scopes[downstream] = sorted(set(scopes[downstream]) | set(scopes[upstream]))
    order = ["emotion_analysis", "scene_analysis", "camera_movement", "prompt_composer"]
    earliest = min(scopes, key=order.index)
    state = load_state(run_dir)
    start = state["phase_order"].index(earliest)
    stop = state["phase_order"].index("editor_pass2")
    for phase in state["phase_order"][start:stop + 1]:
        entry = state["phases"][phase]
        if phase in scopes or phase in ("qa_integration", "director", "continuity", "editor_pass1", "editor_pass2", "validate"):
            entry["status"] = "pending"
            entry["agent_id"] = None
        if phase in scopes:
            entry["repair_scope"] = scopes[phase]
    state["current_phase"] = earliest
    save_state(run_dir, state)
    invalidated = [
        ".cache/composer/merged.prompt_package.json",
        ".cache/review/deterministic_qa.json",
        ".cache/review/llm_gate_result.json",
    ]
    analysis_outputs = {
        "emotion_analysis": ".cache/analysis/emotion_output.json",
        "scene_analysis": ".cache/analysis/scene_output.json",
        "camera_movement": ".cache/analysis/camera_output.json",
    }
    if any(phase in scopes for phase in analysis_outputs):
        invalidated.append(".cache/director/director_pass.json")
    invalidated.extend(analysis_outputs[phase] for phase in scopes if phase in analysis_outputs)
    for relative in invalidated:
        if not relative:
            continue
        try:
            os.remove(os.path.join(run_dir, relative))
        except FileNotFoundError:
            pass
    return {
        "action": "semantic_repair",
        "phase": "editor_pass2",
        "next_phase": earliest,
        "targets": scopes,
        "instruction": "Redispatch the listed subshots at the earliest phase, rebuild Director and Composer, then repeat deterministic and semantic QA.",
    }

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


def _write_stage_summary(run_dir, phase, phase_config):
    """Persist resume metadata without making an auxiliary summary a hard gate."""
    try:
        from write_stage_summary import write_summary
        paths = [
            _resolve_output_path(run_dir, output)
            for output in phase_config.get("output", [])
        ]
        path = write_summary(run_dir, phase, paths)
        print("[SUMMARY] %s" % path)
    except Exception as exc:
        print("[SUMMARY] skipped for %s: %s" % (phase, exc))


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
    elif phase == "grid_storyboard":
        _assemble_analysis(run_dir)
        from generate_grid_storyboards import OUTPUT_RELATIVE_PATH, validate as validate_grid
        issues = validate_grid(os.path.join(run_dir, OUTPUT_RELATIVE_PATH))
        if issues:
            return {"action": "blocked", "phase": phase, "reason": "grid_validation_failed", "issues": issues}
    elif phase == "editor_pass1":
        return _run_deterministic_qa(run_dir)
    elif phase == "validate":
        from hybrid_gate import run as hybrid_gate
        result = hybrid_gate(run_dir, phase="validate", require_llm=True)
        if not result.get("pass", False):
            return {"action": "blocked", "phase": phase, "reason": "hybrid_gate_failed", "issues": result.get("issues", [])}
    return None


def _run_preflight(run_dir):
    from preflight_check import run as preflight_run
    return preflight_run(run_dir)


def _run_deterministic_qa(run_dir):
    """First QA pass: route exact structural failures back to Composer automatically."""
    from validate_prompt_package import validate as validate_prompt_package
    package_path = os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json")
    plan_path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")
    signature, inputs = _deterministic_qa_signature(run_dir)
    review_dir = os.path.join(run_dir, ".cache", "review")
    os.makedirs(review_dir, exist_ok=True)
    report_path = os.path.join(review_dir, "deterministic_qa.json")
    cache_path = os.path.join(review_dir, "deterministic_qa.cache.json")
    cached = _load_deterministic_qa_cache(cache_path, signature)
    if cached is not None:
        issues = cached.get("issues", [])
        cache_hit = True
    else:
        issues = validate_prompt_package(package_path, plan_path)
        cache_hit = False
        with open(cache_path, "w", encoding="utf-8") as handle:
            json.dump({
                "contract_version": "modec-v4", "signature": signature,
                "inputs": inputs, "issues": issues, "pass": not issues,
                "created_at": time.time(),
            }, handle, ensure_ascii=False, indent=2)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump({"pass": not issues, "issues": issues, "cache_hit": cache_hit, "signature": signature}, handle, ensure_ascii=False, indent=2)
    if not issues:
        return None
    ids = sorted({str(issue[0]) for issue in issues if isinstance(issue, (list, tuple)) and str(issue[0]).startswith("S")})
    packets = prepare_dispatch_packets(
        run_dir, "prompt_composer", PHASE_BATCH_SIZE.get("prompt_composer", BATCH_SIZE), ids or None
    )
    # A repair is a new Composer phase, not an instruction attached to the
    # already-completed editor phase. Invalidate only the public aggregate;
    # verified source batches remain as provenance and are superseded by the
    # newly dispatched replacements during merge.
    state = load_state(run_dir)
    state["current_phase"] = "prompt_composer"
    for phase in ("prompt_composer", "editor_pass1", "editor_pass2", "validate"):
        state["phases"][phase]["status"] = "pending"
        state["phases"][phase]["agent_id"] = None
    save_state(run_dir, state)
    try:
        os.remove(package_path)
    except FileNotFoundError:
        pass
    try:
        os.remove(os.path.join(run_dir, ".cache", "review", "llm_gate_result.json"))
    except FileNotFoundError:
        pass
    return {
        "action": "auto_repair",
        "phase": "editor_pass1",
        "repair_phase": "prompt_composer",
        "review_path": report_path,
        "issues": issues[:20],
        "dispatch_packets": packets,
        "instruction": "Redispatch only failing subshots, merge verified replacements, then rerun Editor Pass 1 before semantic QA.",
    }


def _deterministic_qa_signature(run_dir):
    """Fingerprint all package inputs and validator code used by Pass 1."""
    root = os.path.dirname(__file__)
    paths = {
        "prompt_package": os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json"),
        "shot_plan": os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"),
        "director": os.path.join(run_dir, ".cache", "director", "director_pass.json"),
        "project_config": os.path.join(run_dir, "project_config.json"),
        "validate_prompt_package": os.path.join(root, "validate_prompt_package.py"),
        "modec_v4": os.path.join(root, "modec_v4.py"),
        "shot_semantics": os.path.join(root, "shot_semantics.py"),
    }
    inputs = {name: _file_sha256(path) for name, path in paths.items()}
    raw = json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest(), inputs


def _file_sha256(path):
    if not os.path.exists(path):
        return "missing"
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_deterministic_qa_cache(path, signature):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            cached = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    if cached.get("contract_version") != "modec-v4" or cached.get("signature") != signature:
        return None
    return cached if isinstance(cached.get("issues"), list) else None


def _emotion_analysis_required(run_dir):
    from shot_semantics import requires_emotion_analysis
    path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")
    if not os.path.exists(path):
        return True
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            plan = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return True
    return any(
        requires_emotion_analysis(subshot)
        for shot in plan.get("shots", [])
        for subshot in shot.get("subshots", [])
    )


def _write_empty_emotion_output(run_dir):
    path = os.path.join(run_dir, ".cache", "analysis", "emotion_output.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"items": []}, handle, ensure_ascii=False, indent=2)


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
    # Built-in fallback if handler registration is unavailable.
    if phase == "qa_integration":
        _default_assemble(run_dir)


def _default_assemble(run_dir):
    """Default qa_integration handler."""
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
        pcfg = os.path.join(run_dir, "project_config.json")
        assemble_director(ep, sp, cp, paths["plan"], out,
                          project_config_path=pcfg if os.path.exists(pcfg) else None)
