"""Gate check - validates pipeline phase integrity before proceeding.
Ensures: input files exist, agent was spawned, output created BY agent, validation passes.
Exits with code 1 on failure in --strict mode."""
import json, os, sys, time

# Add parent to path
sys.path.insert(0, os.path.dirname(__file__))
from pipeline_state import load_state, PHASE_ORDER
from pipeline_templates import GATES
from validate_agent_output import validate as val_agent
from sources import get_sources_path
from validator.contamination import check_contamination
from hybrid_gate import run as hybrid_gate

SPAWN_TOLERANCE = 0.3  # seconds: output must be created at least this long after spawn


def check(run_dir, phase=None, strict=False):
    """Run gate checks for a pipeline phase.
    
    Args:
        run_dir: Run directory path
        phase: Phase name to check. If None, uses current_phase from state.
        strict: If True, returns exit code 1 on failure.
    
    Returns:
        dict {pass: bool, bypass_detected: bool, issues: list}
    """
    state = load_state(run_dir)
    if not phase:
        phase = state["current_phase"]
    
    phase_config = GATES.get(phase)
    if not phase_config:
        return {"pass": True, "bypass_detected": False, "issues": []}
    
    result = {"pass": True, "bypass_detected": False, "issues": []}
    phase_info = state["phases"].get(phase, {})
    
    # ==== CHECK 1: Input files exist ====
    for inp in phase_config.get("input", []):
        p = _resolve_input_path(run_dir, inp)
        if not os.path.exists(p):
            result["issues"].append({
                "check": "INPUT_EXISTS",
                "file": inp,
                "severity": "blocking",
                "msg": "Missing input: %s" % inp
            })
    
    # ==== CHECK 2: Agent was spawned (for phases that need one) ====
    agent_id = phase_info.get("agent_id")
    spawn_time = phase_info.get("spawn_time")
    status = phase_info.get("status", "pending")
    
    # Phases that require a sub-agent
    agent_phases = ["emotion_analysis", "scene_analysis", "camera_movement", "prompt_composer", "editor_pass2"]
    
    if phase in agent_phases:
        if not agent_id:
            result["issues"].append({
                "check": "AGENT_SPAWNED",
                "severity": "blocking",
                "msg": "No agent spawned for phase %s" % phase
            })
        elif not spawn_time:
            result["issues"].append({
                "check": "AGENT_SPAWN_TIME",
                "severity": "warning",
                "msg": "Agent spawned but no spawn_time recorded (can't verify provenance)"
            })
    
    # ==== CHECK 3: Output provenance (timestamp check) ====
    outputs = phase_config.get("output", [])
    for out in outputs:
        p = _resolve_output_path(run_dir, out)
        if os.path.exists(p) and spawn_time:
            file_mtime = os.path.getmtime(p)
            if file_mtime <= spawn_time:
                result["bypass_detected"] = True
                result["issues"].append({
                    "check": "OUTPUT_BYPASS",
                    "file": out,
                    "severity": "blocking",
                    "msg": "Output %s was created BEFORE agent spawn (mtime=%.3f, spawn=%.3f). Main agent bypass!" % (
                        out, file_mtime, spawn_time)
                })
    
    # ==== CHECK 4: Output validation + contamination ====
    for out in outputs:
        p = _resolve_output_path(run_dir, out)
        if not os.path.exists(p):
            continue  # not created yet, not a violation
        
        # Skip validation if provenance failed (no point validating fake data)
        if result["bypass_detected"]:
            continue

        if phase in ("emotion_analysis", "scene_analysis", "camera_movement"):
            result["issues"].extend(_validate_analysis_items(run_dir, phase, p))

        validator_role = phase_config.get("validator")
        if validator_role:
            vr = val_agent(p, role=validator_role)
            for iss in vr["issues"]:
                severity = "blocking" if vr["retry_needed"] else "warning"
                check_name = iss[1] if len(iss) > 1 else ""
                gate_rule = phase_config.get(check_name, {})
                if gate_rule:
                    max_strict = gate_rule.get("max_strict")
                    value = iss[2] if len(iss) > 2 else 0
                    if max_strict is not None and isinstance(max_strict, (int, float)):
                        severity = "blocking" if value > max_strict else "warning"
                result["issues"].append({
                    "check": "VALIDATE",
                    "file": out,
                    "severity": severity,
                    "msg": "[%s] %s: got %s, expected %s" % (iss[1], iss[0], iss[2], iss[3])
                })
            
            # Contamination check for director-level outputs
            if validator_role in ("director", "emotion_analysis", "scene_analysis", "camera_movement"):
                try:
                    with open(p, "r", encoding="utf-8-sig") as f:
                        data = json.load(f)
                    for item in data.get("items", []):
                        for ciss in check_contamination(item):
                            result["issues"].append({
                                "check": "CONTAMINATION",
                                "file": out,
                                "severity": "blocking",
                                "msg": "[%s] %s: %s" % (ciss[1], ciss[0], ciss[2])
                            })
                except (json.JSONDecodeError, IOError):
                    result["issues"].append({
                        "check": "JSON_PARSE",
                        "file": out,
                        "severity": "blocking",
                        "msg": "Cannot parse JSON"
                    })
    
    # ==== CHECK 5: Hybrid deterministic + LLM review packet ====
    if phase in ("qa_integration", "prompt_composer", "editor_pass2", "validate"):
        require_llm = phase in ("editor_pass2",)
        hg = hybrid_gate(run_dir, phase=phase, require_llm=require_llm)
        for iss in hg.get("issues", []):
            result["issues"].append({
                "check": "HYBRID_%s" % iss.get("check", "gate").upper(),
                "severity": iss.get("severity", "warning"),
                "msg": iss.get("msg", "")
            })
        if hg.get("llm_review_packet"):
            result["llm_review_packet"] = hg["llm_review_packet"]

    # ==== RESULT ====
    blocking = [i for i in result["issues"] if i["severity"] == "blocking"]
    result["pass"] = len(blocking) == 0
    result["per_subshot"] = {}
    
    if result["bypass_detected"]:
        print("[GATE] BYPASS DETECTED in %s! Output existed before agent spawn." % phase)
    
    if result["issues"]:
        for iss in result["issues"]:
            print("[GATE] [%s] %s" % (iss["severity"].upper(), iss["msg"]))
    
    if strict and not result["pass"]:
        print("[GATE] STRICT MODE: failing with exit code 1")
        sys.exit(1)
    
    return result


def _validate_analysis_items(run_dir, phase, output_path):
    issues = []
    try:
        with open(output_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return [{
            "check": "ANALYSIS_JSON",
            "file": os.path.basename(output_path),
            "severity": "blocking",
            "msg": "Cannot parse analysis output JSON"
        }]

    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return [{
            "check": "ANALYSIS_ITEMS",
            "file": os.path.basename(output_path),
            "severity": "blocking",
            "msg": "%s output root must be an object with items[]" % phase
        }]

    seen = set()
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            issues.append({
                "check": "ANALYSIS_ITEM_TYPE",
                "file": os.path.basename(output_path),
                "severity": "blocking",
                "msg": "%s items[%d] must be object" % (phase, idx)
            })
            continue
        shot_id = item.get("shot_id")
        subshot_id = item.get("subshot_id")
        if not isinstance(shot_id, str) or not shot_id:
            issues.append({
                "check": "ANALYSIS_SHOT_ID",
                "file": os.path.basename(output_path),
                "severity": "blocking",
                "msg": "%s items[%d] missing shot_id" % (phase, idx)
            })
        if not isinstance(subshot_id, str) or not subshot_id:
            issues.append({
                "check": "ANALYSIS_SUBSHOT_ID",
                "file": os.path.basename(output_path),
                "severity": "blocking",
                "msg": "%s items[%d] missing subshot_id" % (phase, idx)
            })
        elif subshot_id in seen:
            issues.append({
                "check": "ANALYSIS_SUBSHOT_DUP",
                "file": os.path.basename(output_path),
                "severity": "blocking",
                "msg": "%s duplicate subshot_id %s" % (phase, subshot_id)
            })
        seen.add(subshot_id)

    expected = _expected_subshot_ids(run_dir)
    if expected:
        output_ids = {item.get("subshot_id") for item in items if isinstance(item, dict)}
        missing = sorted(expected - output_ids)
        extra = sorted(output_ids - expected)
        if missing:
            issues.append({
                "check": "ANALYSIS_COVERAGE",
                "file": os.path.basename(output_path),
                "severity": "blocking",
                "msg": "%s missing subshot_id(s): %s" % (phase, ", ".join(missing[:10]))
            })
        if extra:
            issues.append({
                "check": "ANALYSIS_EXTRA",
                "file": os.path.basename(output_path),
                "severity": "blocking",
                "msg": "%s unknown subshot_id(s): %s" % (phase, ", ".join(extra[:10]))
            })
    return issues


def _expected_subshot_ids(run_dir):
    path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            plan = json.load(f)
    except (json.JSONDecodeError, IOError):
        return set()
    return {
        ss.get("subshot_id")
        for shot in plan.get("shots", [])
        for ss in shot.get("subshots", [])
        if ss.get("subshot_id")
    }


def _resolve_input_path(run_dir, path):
    if path == "project_config.json":
        return os.path.join(run_dir, path)
    if os.path.isabs(path):
        return path
    return os.path.join(run_dir, path)


def _resolve_output_path(run_dir, path):
    if path == "project_config.json":
        return os.path.join(run_dir, path)
    if os.path.isabs(path):
        return path
    if path.startswith(".cache"):
        return os.path.join(run_dir, path)
    return os.path.join(run_dir, ".cache", path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: gate_check.py <run_dir> [phase] [--strict]")
        sys.exit(1)
    run_dir = sys.argv[1]
    phase = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    strict = "--strict" in sys.argv
    result = check(run_dir, phase, strict=strict)
    print(json.dumps(result, ensure_ascii=False, indent=2))

def _track_per_subshot(run_dir, phase):
    """Identify which subshots passed vs failed validation.
    Returns dict: {subshot_id: "passed"|"failed"} for output items."""
    from pipeline_state import load_state
    from pipeline_templates import GATES
    state = load_state(run_dir)
    phase_config = GATES.get(phase)
    if not phase_config:
        return {}
    result = {}
    for out in phase_config.get("output", []):
        p = _resolve_output_path(run_dir, out)
        if not os.path.exists(p):
            continue
        try:
            with open(p, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            items = data.get("items", [])
            # Re-run validation on each item to determine pass/fail
            for item in items:
                ssid = item.get("subshot_id", "?")
                if _validate_item(item, phase):
                    result[ssid] = "passed"
                else:
                    result[ssid] = "failed"
        except Exception:
            pass
        break
    return result

def _validate_item(item, phase):
    """Quick per-item validation check. Returns True if item passes basic checks."""
    fp = item.get("full_prompt", "")
    dur = item.get("duration", 0)
    if phase == "prompt_composer":
        return len(fp) >= 500 and isinstance(dur, (int, float)) and dur > 0
    # director level: check key fields have content
    for key in ["shot_size", "camera_position", "character_action", "lighting"]:
        val = item.get(key, "")
        if isinstance(val, str) and len(val) < 5:
            return False
    return True

