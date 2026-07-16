"""Pipeline templates + validation gates with retry support."""
import json, os, sys
from validator.field_types import validate_field_types
from validator.quality import quality_check_director, quality_check_prompt
from validate_agent_output import validate as validate_agent

GATES = {
    "user_confirm": {
        "input": [],
        "output": ["project_config.json"],
        "validator": None
    },
    "orchestrator": {
        "input": [],
        "output": [".cache/orchestrator/shot_plan.json"],
        "validator": None
    },
    "emotion_analysis": {
        "input": ["shot_plan.json"],
        "output": ["analysis/emotion_output.json"],
        "validator": None
    },
    "scene_analysis": {
        "input": ["shot_plan.json"],
        "output": ["analysis/scene_output.json"],
        "validator": None
    },
    "camera_movement": {
        "input": ["shot_plan.json"],
        "output": ["analysis/camera_output.json"],
        "validator": None
    },
    "qa_integration": {
        "input": [".cache/analysis/emotion_output.json", ".cache/analysis/scene_output.json", ".cache/analysis/camera_output.json"],
        "output": ["director/director_pass.json"],
        "validator": None
    },
    "director": {
        "input": ["shot_plan.json", "project_config.json"],
        "output": ["director_pass.json"],
        "validator": "director"
    },
    "continuity": {
        "input": [".cache/director/director_pass.json", ".cache/orchestrator/shot_plan.json"],
        "output": [],
        "validator": None
    },
    "prompt_composer": {
        "input": ["director_pass.json"],
        "output": ["prompt_package.json"],
        "validator": "prompt"
    },
    "editor_pass1": {
        "input": ["prompt_package.json"],
        "output": ["prompt_package.json"],
        "validator": None
    },
    "editor_pass2": {
        "input": ["prompt_package.json"],
        "output": ["prompt_package.json"],
        "validator": None
    },
    "validate": {
        "input": ["prompt_package.json", "project_config.json"],
        "output": [],
        "validator": None
    },
    "export": {
        "input": ["prompt_package.json", "shot_plan.json"],
        "output": [],
        "validator": None
    }
}


def check_gate(run_dir, phase, strict=True):
    """Check gate for a pipeline phase.

    Returns:
        dict: {pass: bool, blocked: bool, retry_needed: bool, issues: list}
    """
    g = GATES.get(phase)
    if not g:
        return {"pass": True, "blocked": False, "retry_needed": False, "issues": []}

    result = {"pass": True, "blocked": False, "retry_needed": False, "issues": []}

    # Step 1: Check input files exist
    missing = [f for f in g["input"] if not os.path.exists(os.path.join(run_dir, f))]
    if missing:
        msg = "BLOCKED: Phase '%s' missing %s." % (phase, missing)
        result["blocked"] = True
        result["issues"].append(("GATE", "missing_input", 0, str(missing)))
        if strict:
            print(msg)
        return result

    # Step 2: Call content validators if configured
    validator_role = g.get("validator")
    if validator_role:
        for out_file in g["output"]:
            out_path = os.path.join(run_dir, out_file)
            if os.path.exists(out_path):
                vr = validate_agent(out_path, role=validator_role)
                result["issues"].extend(vr["issues"])
                if vr["retry_needed"]:
                    result["retry_needed"] = True
                    result["pass"] = False

    return result


def get_retry_decision(result, max_retries=2):
    """Given a gate result, decide what to do. Returns 'retry', 'block', or 'pass'."""
    if result["blocked"]:
        return "block"
    if result["retry_needed"]:
        return "retry"
    return "pass"

