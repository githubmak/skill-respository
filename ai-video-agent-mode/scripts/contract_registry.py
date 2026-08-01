"""Canonical machine contract shared by every current pipeline component."""

PROMPT_CONTRACT_VERSION = "jimeng-t2v-v1"
PIPELINE_CONTRACT_VERSION = "jimeng-t2v-pipeline-v2"

# Keep runtime phase identity, ownership, artifact boundaries, timeout and
# batching policy in one executable registry. Other modules derive their
# public constants from this tuple instead of maintaining parallel copies.
PIPELINE_PHASE_SPECS = (
    {
        "name": "user_confirm", "executor": "local", "input": (),
        "output": ("project_config.json",), "validator": None,
    },
    {
        "name": "orchestrator", "executor": "local", "input": (),
        "output": (
            ".cache/orchestrator/shot_plan.json",
            ".cache/orchestrator/source_ledger.json",
            ".cache/orchestrator/dramatic_beat_ledger.json",
        ),
        "validator": None,
    },
    {
        "name": "scene_lock", "executor": "agent",
        "input": (".cache/orchestrator/shot_plan.json",),
        "output": (".cache/analysis/scene_locks.json",),
        "validator": "scene_lock", "timeout_seconds": 480, "batch_size": 1,
    },
    {
        "name": "master_production", "executor": "agent",
        "input": (
            ".cache/orchestrator/shot_plan.json",
            ".cache/analysis/scene_locks.json",
        ),
        "output": (".cache/composer/merged.prompt_package.json",),
        "validator": "prompt", "timeout_seconds": 720, "batch_size": 6,
    },
    {
        "name": "editor_pass1", "executor": "local",
        "input": (".cache/composer/merged.prompt_package.json",),
        "output": (".cache/review/pre_editor_gate.json",), "validator": None,
    },
    {
        "name": "editor_pass2", "executor": "agent",
        "input": (".cache/composer/merged.prompt_package.json",),
        "output": (".cache/review/llm_gate_result.json",),
        "validator": None, "timeout_seconds": 480, "batch_size": 10,
    },
    {
        "name": "validate", "executor": "local",
        "input": (".cache/composer/merged.prompt_package.json", "project_config.json"),
        "output": (".cache/validate/result.json",), "validator": None,
    },
    {
        "name": "export", "executor": "local",
        "input": (
            ".cache/composer/merged.prompt_package.json",
            ".cache/orchestrator/shot_plan.json",
        ),
        "output": (".cache/export/result.json",), "validator": None,
    },
)

PIPELINE_PHASES = tuple(spec["name"] for spec in PIPELINE_PHASE_SPECS)
PHASE_SPEC_BY_NAME = {spec["name"]: spec for spec in PIPELINE_PHASE_SPECS}
AGENT_PHASE_NAMES = frozenset(
    spec["name"] for spec in PIPELINE_PHASE_SPECS if spec["executor"] == "agent"
)
LOCAL_PHASE_NAMES = frozenset(
    spec["name"] for spec in PIPELINE_PHASE_SPECS if spec["executor"] == "local"
)
PHASE_TIMEOUT_SECONDS = {
    spec["name"]: spec["timeout_seconds"]
    for spec in PIPELINE_PHASE_SPECS if "timeout_seconds" in spec
}
PHASE_BATCH_SIZE = {
    spec["name"]: spec["batch_size"]
    for spec in PIPELINE_PHASE_SPECS if "batch_size" in spec
}


def pipeline_gates():
    """Return mutable gate declarations derived from the canonical registry."""
    return {
        spec["name"]: {
            "input": list(spec["input"]),
            "output": list(spec["output"]),
            "validator": spec["validator"],
        }
        for spec in PIPELINE_PHASE_SPECS
    }


def machine_contract_issues():
    """Return deterministic defects in the executable pipeline registry."""
    issues = []
    if not PIPELINE_PHASES or PIPELINE_PHASES[0] != "user_confirm" or PIPELINE_PHASES[-1] != "export":
        issues.append("pipeline phases must start at user_confirm and end at export")
    if len(PIPELINE_PHASES) != len(set(PIPELINE_PHASES)):
        issues.append("pipeline phase names must be unique")
    if set(PIPELINE_PHASES) != AGENT_PHASE_NAMES | LOCAL_PHASE_NAMES:
        issues.append("every pipeline phase must have exactly one executor")
    if AGENT_PHASE_NAMES & LOCAL_PHASE_NAMES:
        issues.append("agent and local phase sets must not overlap")
    for spec in PIPELINE_PHASE_SPECS:
        name = spec["name"]
        if spec["executor"] not in {"agent", "local"}:
            issues.append("%s has an invalid executor" % name)
        if not isinstance(spec.get("input"), tuple) or not isinstance(spec.get("output"), tuple):
            issues.append("%s artifact boundaries must be tuples" % name)
        if spec["executor"] == "agent":
            if not isinstance(spec.get("timeout_seconds"), int) or spec["timeout_seconds"] <= 0:
                issues.append("%s must define a positive timeout" % name)
            if not isinstance(spec.get("batch_size"), int) or spec["batch_size"] <= 0:
                issues.append("%s must define a positive batch size" % name)
    return issues

SHOT_REQUIRED_FIELDS = frozenset({
    "shot_id", "subshot_id", "duration", "full_prompt", "negative_prompt",
    "qa_metadata", "generation_control",
})

QA_REQUIRED_FIELDS = (
    "dramatic_goal", "performance_priority", "action_budget", "start_state", "end_state",
    "emotion_driver", "performance_contract", "continuity_contract", "reroll_control", "dialogue_refs",
    "dialogue_events", "editorial_mode", "camera_beat_map", "sequence_context",
    "quality_contract", "dramatic_design", "duration_design", "viewpoint",
    "visual_hierarchy", "entry_strategy", "reveal_strategy",
    "focus_strategy", "temporal_transition_contract", "story_punch_contract",
    "scene_tone_palette", "character_scene_objective_contract",
    "relationship_emotion_arc", "sequence_directing_plan",
    "cut_decision_contract", "prompt_information_budget", "sound_directing_plan",
)

# Heavy semantic QA fields are risk-gated by modec_v4 validators instead of
# globally required for every shot. This keeps light/environment/simple shots
# from paying the same context and generation cost as high-risk character shots.
RISK_GATED_QA_FIELDS = (
    "ai_model_readiness_score",
    "pressure_release_design",
)
