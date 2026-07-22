"""Choose the smallest safe AI-video workflow for an explicit task mode."""
import argparse
import json
import os
import sys

from resolve_run_mode import DEFAULT_INTENTS, resolve


ROUTES = {
    "full": {
        "description": "Run the complete Phase 0-10 pipeline for new or materially changed source content.",
        "requires": [],
        "agents": True,
    },
    "audit": {
        "description": "Review an existing prompt package without regenerating prompts or exporting.",
        "requires": [".cache/composer/merged.prompt_package.json"],
        "agents": False,
    },
    "export": {
        "description": "Export an already validated package; never regenerate creative stages.",
        "requires": [".cache/composer/merged.prompt_package.json", ".cache/orchestrator/shot_plan.json"],
        "agents": False,
        "required_done_phases": ["editor_pass2", "validate"],
    },
    "compose": {
        "description": "Generate Composer packets from an approved Director result.",
        "requires": ["project_config.json", ".cache/director/director_pass.json"],
        "agents": True,
    },
    "single-repair": {
        "description": "Repair only one failing subshot in one agent phase.",
        "requires": ["project_config.json", ".cache/sources.json"],
        "agents": True,
        "requires_subshot_id": True,
    },
}


def route(mode, run_dir=None, subshot_id=None, intent=None):
    if mode not in ROUTES:
        raise ValueError("mode must be one of: %s" % ", ".join(sorted(ROUTES)))
    spec = dict(ROUTES[mode])
    result = {
        "mode": mode,
        "description": spec["description"],
        "uses_agents": spec["agents"],
        "run_dir": run_dir or "",
        "missing": [],
        "blocking": [],
    }
    intent = intent or DEFAULT_INTENTS[mode]
    result["intent"] = intent
    if spec.get("requires_subshot_id") and not subshot_id:
        result["blocking"].append("single-repair requires --subshot-id")
    if not run_dir:
        result["blocking"].append("--run-dir is required")
        return result
    initialization = resolve(mode, run_dir, intent)
    result["initialization"] = initialization
    if initialization.get("blocking"):
        result["blocking"].extend(initialization["blocking"])
    if initialization.get("requires_user_confirm"):
        result["needs_user_confirm"] = True
        result["questions"] = initialization.get("questions", [])
    for relative_path in spec.get("requires", []):
        if not os.path.exists(os.path.join(run_dir, relative_path)):
            result["missing"].append(relative_path)
    state_path = os.path.join(run_dir, ".cache", "pipeline_state.json")
    if spec.get("required_done_phases"):
        if not os.path.exists(state_path):
            result["blocking"].append("pipeline_state.json is required for this route")
        else:
            with open(state_path, "r", encoding="utf-8-sig") as handle:
                state = json.load(handle)
            phases = state.get("phases", {})
            for phase in spec["required_done_phases"]:
                if phases.get(phase, {}).get("status") != "done":
                    result["blocking"].append("%s must be done before %s" % (phase, mode))
    if result["missing"]:
        result["blocking"].append("required artifacts are missing")
    result["pass"] = not result["blocking"] and not result.get("needs_user_confirm", False)
    if subshot_id:
        result["subshot_id"] = subshot_id
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=sorted(ROUTES))
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--subshot-id")
    parser.add_argument("--intent", choices=("new", "resume", "audit", "reexport"))
    args = parser.parse_args()
    try:
        outcome = route(args.mode, args.run_dir, args.subshot_id, args.intent)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"pass": False, "blocking": [str(exc)]}, ensure_ascii=False))
        sys.exit(2)
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    sys.exit(0 if outcome["pass"] else 1)
