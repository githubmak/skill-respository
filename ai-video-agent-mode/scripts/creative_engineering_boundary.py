#!/usr/bin/env python3
"""Executable ownership boundary for the model-led video pipeline."""

from __future__ import annotations

import re


BOUNDARY_CONTRACT_VERSION = "creative-engineering-boundary-v1"

MODEL = "model"
ENGINE = "engine"
HYBRID = "hybrid"

PHASE_AUTHORITY = {
    "user_confirm": ENGINE,
    "orchestrator": HYBRID,
    "master_production": MODEL,
    "editor_pass1": ENGINE,
    "editor_pass2": MODEL,
    "validate": HYBRID,
    "export": ENGINE,
}

# Longest matching prefix wins. Array indexes are normalized to []. Creative
# fields default to model ownership; engineering must opt in explicitly.
FIELD_OWNERSHIP = {
    "contract_version": ENGINE,
    "shot_id": ENGINE,
    "subshot_id": ENGINE,
    "duration": ENGINE,
    "source_subshot_ids": ENGINE,
    "source_subshots": ENGINE,
    "generation_control": ENGINE,
    "_scene_lock_ref": ENGINE,
    "full_prompt": MODEL,
    "seedance_prompt": MODEL,
    "seedance_prompt_variants": MODEL,
    "negative_prompt": MODEL,
    "director_card": MODEL,
    "scene_lock": MODEL,
    "qa_metadata": MODEL,
    "qa_metadata.dialogue_refs": ENGINE,
    "qa_metadata.dialogue_events": HYBRID,
    "qa_metadata.dialogue_events[].ref": ENGINE,
    "qa_metadata.dialogue_events[].kind": ENGINE,
    "qa_metadata.dialogue_events[].speaker": ENGINE,
    "qa_metadata.dialogue_events[].text": ENGINE,
    "qa_metadata.quality_contract": MODEL,
    "qa_metadata.prompt_information_budget": MODEL,
    "qa_metadata.scene_tone_palette": MODEL,
    "qa_metadata.continuity_contract": MODEL,
}

ENGINE_ONLY_OPERATIONS = frozenset({
    "parse", "serialize", "count", "deterministic_validate", "hash", "version",
    "merge_verified", "layout", "export", "resume",
})

FORBIDDEN_ENGINE_OPERATIONS = frozenset({
    "semantic_rewrite", "semantic_compress", "select_creative_clause",
    "infer_emotion", "choose_camera", "judge_aesthetics", "judge_seedance_semantics",
    "repair_scene_lock", "delete_creative_field", "compile_seedance_prompt",
})


def normalize_field_path(path):
    value = str(path or "").strip().replace("review_contracts.", "qa_metadata.")
    value = re.sub(r"\[\d+\]", "[]", value)
    return value


def field_owner(path):
    normalized = normalize_field_path(path)
    matches = [
        (prefix, owner) for prefix, owner in FIELD_OWNERSHIP.items()
        if normalized == prefix or normalized.startswith(prefix + ".")
    ]
    if not matches:
        return MODEL
    return max(matches, key=lambda item: len(item[0]))[1]


def repair_executor(path, issue_code=""):
    """Route semantic repairs to the model and mechanical defects to code."""
    code = str(issue_code or "").upper()
    if code in {"BATCH_CONTRACT", "SCHEMA_CONFLICT"}:
        return ENGINE
    return ENGINE if field_owner(path) == ENGINE else MODEL


def creative_rewrite_issue(path, current_chars, max_chars, reason=""):
    message = "CREATIVE_REWRITE_REQUIRED:%s:%s>%s" % (
        normalize_field_path(path), int(current_chars), int(max_chars)
    )
    if reason:
        message += ":" + str(reason).strip()
    return message


def boundary_issues():
    issues = []
    owners = {MODEL, ENGINE, HYBRID}
    for phase, owner in PHASE_AUTHORITY.items():
        if owner not in owners:
            issues.append("invalid phase authority: %s=%s" % (phase, owner))
    for path, owner in FIELD_OWNERSHIP.items():
        if not path or owner not in owners:
            issues.append("invalid field ownership: %s=%s" % (path, owner))
    for required in ("full_prompt", "qa_metadata", "shot_id", "duration"):
        if required not in FIELD_OWNERSHIP:
            issues.append("missing ownership declaration: " + required)
    if ENGINE_ONLY_OPERATIONS & FORBIDDEN_ENGINE_OPERATIONS:
        issues.append("engine operation allow/deny lists overlap")
    return issues


if __name__ == "__main__":
    found = boundary_issues()
    print("[CREATIVE BOUNDARY] %s" % ("PASS" if not found else "FAIL"))
    for issue in found:
        print("- " + issue)
    raise SystemExit(0 if not found else 1)
