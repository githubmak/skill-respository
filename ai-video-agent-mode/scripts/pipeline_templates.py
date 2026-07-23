"""Current-contract pipeline gate declarations."""

GATES = {
    "user_confirm": {
        "input": [],
        "output": ["project_config.json"],
        "validator": None
    },
    "orchestrator": {
        "input": [],
        "output": [
            ".cache/orchestrator/shot_plan.json",
            ".cache/orchestrator/source_ledger.json",
            ".cache/orchestrator/dramatic_beat_ledger.json",
        ],
        "validator": None
    },
    "scene_lock": {
        "input": [".cache/orchestrator/shot_plan.json"],
        "output": [".cache/analysis/scene_locks.json"],
        "validator": "scene_lock"
    },
    "master_production": {
        "input": [".cache/orchestrator/shot_plan.json", ".cache/analysis/scene_locks.json"],
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
        "output": [".cache/review/llm_gate_result.json"],
        "validator": None
    },
    "grid_storyboard": {
        "input": [
            ".cache/composer/merged.prompt_package.json",
            ".cache/orchestrator/shot_plan.json",
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


def get_retry_decision(result, max_retries=None):
    """Given a gate result, decide what to do. Returns 'retry', 'block', or 'pass'."""
    if result["blocked"]:
        return "block"
    if result["retry_needed"]:
        return "retry"
    return "pass"
