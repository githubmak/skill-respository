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
        "input": [".cache/orchestrator/shot_plan.json"],
        "output": [".cache/analysis/emotion_output.json"],
        "validator": "emotion_analysis"
    },
    "scene_analysis": {
        "input": [".cache/orchestrator/shot_plan.json"],
        "output": [".cache/analysis/scene_output.json"],
        "validator": "scene_analysis"
    },
    "camera_movement": {
        "input": [".cache/orchestrator/shot_plan.json", ".cache/analysis/emotion_output.json"],
        "output": [".cache/analysis/camera_output.json"],
        "validator": "camera_movement"
    },
    "qa_integration": {
        "input": [".cache/analysis/emotion_output.json", ".cache/analysis/scene_output.json", ".cache/analysis/camera_output.json"],
        "output": [".cache/director/director_pass.json"],
        "validator": "director"
    },
    "director": {
        "input": [".cache/director/director_pass.json"],
        "output": [".cache/director/director_pass.json"],
        "validator": "director"
    },
    "continuity": {
        "input": [".cache/director/director_pass.json", ".cache/orchestrator/shot_plan.json"],
        "output": ["continuity/report.json"],
        "validator": "continuity",
        "SHOT_SIZE_REPEAT": {"max_strict": 4}
    },
    "prompt_composer": {
        "input": [".cache/director/director_pass.json"],
        "output": [".cache/composer/merged.prompt_package.json"],
        "validator": "prompt"
    },
    "editor_pass1": {
        "input": [".cache/composer/merged.prompt_package.json"],
        "output": [".cache/composer/merged.prompt_package.json"],
        "validator": None
    },
    "editor_pass2": {
        "input": [".cache/composer/merged.prompt_package.json"],
        "output": ["review/llm_gate_result.json"],
        "validator": None
    },
    "grid_storyboard": {
        "input": [
            ".cache/composer/merged.prompt_package.json",
            ".cache/orchestrator/shot_plan.json",
            ".cache/director/director_pass.json",
            "project_config.json",
        ],
        "output": [".cache/grid_storyboard/packages.json"],
        "validator": None
    },
    "validate": {
        "input": [".cache/composer/merged.prompt_package.json", "project_config.json"],
        "output": [],
        "validator": None
    },
    "export": {
        "input": [".cache/composer/merged.prompt_package.json", ".cache/orchestrator/shot_plan.json"],
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


def get_retry_decision(result, max_retries=None):
    """Given a gate result, decide what to do. Returns 'retry', 'block', or 'pass'."""
    if result["blocked"]:
        return "block"
    if result["retry_needed"]:
        return "retry"
    return "pass"
