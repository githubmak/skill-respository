"""Canonical machine contract shared by every current pipeline component."""

from creative_engineering_boundary import PHASE_AUTHORITY, boundary_issues

PROMPT_CONTRACT_VERSION = "jimeng-t2v-v1"
PIPELINE_CONTRACT_VERSION = "jimeng-t2v-pipeline-v4"
REUSE_CONTRACT_VERSION = "verified-run-reuse-v1"

# Wall-clock reliability contract. This is a hard production deadline, not a
# benchmark target. The supervisor must stop and emit a report when it expires.
PIPELINE_HARD_DEADLINE_SECONDS = 90 * 60
PIPELINE_DEADLINE_WARNING_SECONDS = 10 * 60
# Forecasts use coarse phase targets and can be off by a small scheduling
# interval. This tolerance never extends the hard deadline; it only prevents a
# premature projected-deadline fuse when the estimate is within two minutes.
PIPELINE_FORECAST_UNCERTAINTY_SECONDS = 2 * 60
# Codex exposes four total agent slots in the normal desktop runtime.  The
# supervisor occupies one of them, so a plan that assumes four workers is not
# executable and systematically underestimates queue waves.
PIPELINE_WORKER_SLOT_CAP = 3
WORKER_LEASE_CONTRACT_VERSION = "worker-lease-v1"
# A lease keeps one model worker alive across several immutable packets.  The
# packet timeout starts only when that packet transitions from leased to
# running, so queued work does not expire behind an earlier packet.
MAX_PACKETS_PER_WORKER_LEASE = 4

# Conservative planning targets used to reject a run that can no longer
# finish before the hard deadline. They do not relax per-worker timeouts.
PHASE_PLANNING_SECONDS = {
    "orchestrator": 10 * 60,
    "master_production": 10 * 60,
    "editor_pass1": 60,
    "editor_pass2": 5 * 60,
    "validate": 2 * 60,
    "export": 60,
}

# Keep runtime phase identity, ownership, artifact boundaries, timeout and
# batching policy in one executable registry. Other modules derive their
# public constants from this tuple instead of maintaining parallel copies.
PIPELINE_PHASE_SPECS = (
    {
        "name": "user_confirm", "executor": "local", "input": (),
        "output": ("project_config.json",), "validator": None,
        "authority": PHASE_AUTHORITY["user_confirm"],
    },
    {
        "name": "orchestrator", "executor": "local", "input": (),
        "output": (
            ".cache/orchestrator/source_snapshot.json",
            ".cache/orchestrator/creative_blueprint_request.json",
            ".cache/orchestrator/shot_plan.json",
            ".cache/orchestrator/source_ledger.json",
            ".cache/analysis/scene_locks.json",
            ".cache/orchestrator/creative_validation_receipt.json",
        ),
        "validator": None, "authority": PHASE_AUTHORITY["orchestrator"],
    },
    {
        "name": "master_production", "executor": "agent",
        "input": (
            ".cache/orchestrator/shot_plan.json",
            ".cache/analysis/scene_locks.json",
        ),
        "output": (".cache/composer/merged.prompt_package.json",),
        "validator": "prompt", "timeout_seconds": 720, "batch_size": 6,
        "authority": PHASE_AUTHORITY["master_production"],
    },
    {
        "name": "editor_pass1", "executor": "local",
        "input": (".cache/composer/merged.prompt_package.json",),
        "output": (".cache/review/pre_editor_gate.json",), "validator": None,
        "authority": PHASE_AUTHORITY["editor_pass1"],
    },
    {
        "name": "editor_pass2", "executor": "agent",
        "input": (".cache/composer/merged.prompt_package.json",),
        "output": (".cache/review/llm_gate_result.json",),
        "validator": None, "timeout_seconds": 480, "batch_size": 10,
        "authority": PHASE_AUTHORITY["editor_pass2"],
    },
    {
        "name": "validate", "executor": "local",
        "input": (".cache/composer/merged.prompt_package.json", "project_config.json"),
        "output": (".cache/validate/result.json",), "validator": None,
        "authority": PHASE_AUTHORITY["validate"],
    },
    {
        "name": "export", "executor": "local",
        "input": (
            ".cache/composer/merged.prompt_package.json",
            ".cache/orchestrator/shot_plan.json",
        ),
        "output": (".cache/export/result.json",), "validator": None,
        "authority": PHASE_AUTHORITY["export"],
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
PHASE_STARTUP_PROGRESS_SECONDS = {
    "master_production": 5 * 60,
    "editor_pass2": 5 * 60,
}
PHASE_STALL_PROGRESS_SECONDS = {
    "master_production": 3 * 60,
    "editor_pass2": 3 * 60,
}
MAX_CREATIVE_REAUTHOR_ROUNDS = 2
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
            "authority": spec["authority"],
        }
        for spec in PIPELINE_PHASE_SPECS
    }


def machine_contract_issues():
    """Return deterministic defects in the executable pipeline registry."""
    issues = list(boundary_issues())
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
        if spec.get("authority") != PHASE_AUTHORITY.get(name):
            issues.append("%s authority differs from creative boundary" % name)
        if not isinstance(spec.get("input"), tuple) or not isinstance(spec.get("output"), tuple):
            issues.append("%s artifact boundaries must be tuples" % name)
        if spec["executor"] == "agent":
            if not isinstance(spec.get("timeout_seconds"), int) or spec["timeout_seconds"] <= 0:
                issues.append("%s must define a positive timeout" % name)
            if not isinstance(spec.get("batch_size"), int) or spec["batch_size"] <= 0:
                issues.append("%s must define a positive batch size" % name)
    return issues

SHOT_REQUIRED_FIELDS = frozenset({
    "shot_id", "subshot_id", "source_subshot_ids", "duration", "full_prompt", "seedance_prompt", "director_card", "negative_prompt",
    "qa_metadata", "generation_control",
})

# Only mechanically verifiable source references are required by code. Creative
# analysis fields remain available to Master Production and Editor, but their
# shape and depth are not an engineering pass/fail contract.
QA_REQUIRED_FIELDS = (
    "dialogue_refs", "dialogue_events",
)
