"""Choose the smallest safe AI-video workflow for an explicit task mode."""
import argparse
import json
import os
import sys

from resolve_run_mode import DEFAULT_INTENTS, resolve


ROUTES = {
    "full": {
        "description": "Run the complete current eight-stage pipeline for new or materially changed source content.",
        "requires": [],
        "agents": True,
        "read_first": ["references/stage_gates.md"],
        "read_on_demand": [
            ".cache/stage_summary/<phase>.json",
            "references/contracts/contract_index.md",
        ],
        "run_only": ["scripts/workflow_supervisor.py"],
    },
    "audit": {
        "description": "Review an existing prompt package without regenerating prompts or exporting.",
        "requires": [".cache/composer/merged.prompt_package.json"],
        "agents": False,
        "read_first": [],
        "read_on_demand": [
            ".cache/validate/result.json",
            "references/contracts/contract_index.md",
        ],
        "run_only": [
            "scripts/episode_state_graph.py",
            "scripts/episode_director_audit.py",
            "scripts/emotion_camera_audit.py",
            "scripts/validate_modec.py",
            "scripts/check_export.py",
        ],
    },
    "export": {
        "description": "Export an already validated package; never regenerate creative stages.",
        "requires": [".cache/composer/merged.prompt_package.json", ".cache/orchestrator/shot_plan.json"],
        "agents": False,
        "required_done_phases": ["editor_pass2", "validate"],
        "read_first": [],
        "read_on_demand": ["references/export_spec.md"],
        "run_only": ["scripts/export_with_validation.py"],
    },
    "compose": {
        "description": "Generate Master Production packets from approved scene locks and shot plan.",
        "requires": ["project_config.json", ".cache/orchestrator/shot_plan.json", ".cache/analysis/scene_locks.json"],
        "agents": True,
        "read_first": ["references/agent_protocol.md"],
        "read_on_demand": [
            "packet.constraints_path",
            "packet.composer_scaffold_path",
            "packet.scene_lock_cache_path",
        ],
        "run_only": [
            "scripts/dispatch_cache.py",
            "scripts/validate_composer_output.py",
        ],
    },
    "single-repair": {
        "description": "Repair only one failing subshot in one agent phase.",
        "requires": ["project_config.json", ".cache/sources.json"],
        "agents": True,
        "requires_subshot_id": True,
        "read_first": [
            "packet.constraints_path",
            "packet.retry_context_path",
        ],
        "read_on_demand": [".cache/stage_summary/<phase>.json"],
        "run_only": [
            "scripts/record_batch_provenance.py",
            "scripts/merge_agent_outputs.py",
        ],
    },
}


def _context_plan(spec):
    return {
        "read_first": list(spec.get("read_first", [])),
        "read_on_demand": list(spec.get("read_on_demand", [])),
        "run_only": list(spec.get("run_only", [])),
        "preload_full_contracts": False,
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
        "context_plan": _context_plan(spec),
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


def high_quality_fast_start(run_dir, config_path, source_path):
    """Confirm complete setup and advance the unchanged pipeline to its first pause."""
    source_path = os.path.abspath(source_path)
    if not os.path.isfile(source_path):
        raise ValueError("source file does not exist: %s" % source_path)
    from configuration_wizard import confirm_all
    from workflow_supervisor import run_until_pause

    context_plan = _context_plan(ROUTES["full"])
    configuration = confirm_all(run_dir, config_path)
    initialization = resolve("full", run_dir, "resume")
    if not initialization.get("pass"):
        return {
            "pass": False,
            "mode": "full",
            "intent": "new",
            "setup_mode": "high_quality_fast",
            "context_plan": context_plan,
            "configuration": configuration,
            "initialization": initialization,
            "blocking": initialization.get("blocking", ["confirmed configuration could not initialize"]),
        }
    supervisor = run_until_pause(run_dir, source_path)
    status = supervisor.get("status")
    passed = status in {"host_dispatch_required", "waiting_for_workers", "completed"}
    return {
        "pass": passed,
        "mode": "full",
        "intent": "new",
        "setup_mode": "high_quality_fast",
        "context_plan": context_plan,
        "quality_pipeline_preserved": True,
        "skipped_phases": [],
        "configuration": configuration,
        "initialization": initialization,
        "supervisor": supervisor,
        "blocking": [] if passed else [supervisor.get("reason") or status or "fast start blocked"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=sorted(ROUTES))
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--subshot-id")
    parser.add_argument("--intent", choices=("new", "resume", "audit", "reexport"))
    parser.add_argument("--config", help="Complete JSON configuration for high-quality fast mode.")
    parser.add_argument("--source", help="Source script for high-quality fast mode.")
    parser.add_argument("--auto-start", action="store_true", help="Confirm complete configuration and start the unchanged full pipeline.")
    args = parser.parse_args()
    try:
        if args.auto_start:
            if args.mode != "full" or args.intent not in (None, "new"):
                raise ValueError("--auto-start only supports full --intent new")
            if not args.config or not args.source:
                raise ValueError("--auto-start requires both --config and --source")
            outcome = high_quality_fast_start(args.run_dir, args.config, args.source)
        else:
            if args.config or args.source:
                raise ValueError("--config and --source require --auto-start")
            outcome = route(args.mode, args.run_dir, args.subshot_id, args.intent)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"pass": False, "blocking": [str(exc)]}, ensure_ascii=False))
        sys.exit(2)
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    sys.exit(0 if outcome["pass"] else 1)
