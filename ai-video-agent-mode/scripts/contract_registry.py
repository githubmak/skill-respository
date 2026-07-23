"""Canonical structural requirements shared by every current-contract gate."""

SHOT_REQUIRED_FIELDS = frozenset({
    "shot_id", "subshot_id", "duration", "full_prompt", "negative_prompt",
    "qa_metadata", "generation_control",
})

QA_REQUIRED_FIELDS = (
    "dramatic_goal", "performance_priority", "action_budget", "start_state", "end_state",
    "performance_contract", "continuity_contract", "reroll_control", "dialogue_refs",
    "dialogue_events", "editorial_mode", "camera_beat_map", "sequence_context",
    "quality_contract", "dramatic_design", "duration_design", "viewpoint",
    "visual_hierarchy", "entry_strategy", "reveal_strategy",
    "focus_strategy", "temporal_transition_contract",
)
