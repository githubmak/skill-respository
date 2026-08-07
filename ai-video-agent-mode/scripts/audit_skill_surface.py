#!/usr/bin/env python3
"""Reject retired agent surfaces and accidental phase resurrection."""

from __future__ import annotations

import os
import re

from contract_registry import AGENT_PHASE_NAMES


CURRENT_AGENT_PHASES = frozenset({"master_production", "editor_pass2"})
RETIRED_RELATIVE_PATHS = (
    "references/agents/01_orchestrator_storyboard_agent.md",
    "references/agents/02_director_enhancement_agent.md",
    "references/agents/02_scene_lock_agent.md",
    "references/agents/03_master_production_agent.md",
    "references/agents/04_qa_review_agent.md",
    "references/examples/camera_example.json",
    "references/examples/director_example.json",
    "references/examples/emotion_example.json",
    "references/examples/scene_example.json",
    "scripts/modec_v4.py",
    "scripts/apply_targeted_master_repair.py",
    "scripts/prepare_episode7_e2e_fixture.py",
    "scripts/validator/contamination.py",
    "scripts/validator/field_types.py",
    "scripts/validator/quality.py",
    "references/runbook.md",
    "references/dispatch/scene_lock_note.md",
    "references/dynamic_performance_reference.md",
    "references/visual-direction-profiles.md",
    "scripts/visual_profile_router.py",
    "scripts/emotion_camera_audit.py",
    "scripts/episode_director_audit.py",
    "scripts/episode_state_graph.py",
    "scripts/scene_motion_plan.py",
    "scripts/scene_texture_plan.py",
    "scripts/spatial_storyboard.py",
    "scripts/current_keyframe.py",
    "scripts/negative_prompts.py",
    "scripts/scene_lock_authority.py",
    "scripts/test_current_pipeline.py",
    "scripts/test_keyframe_pipeline.py",
    "scripts/test_preproduction_quality_plans.py",
    "scripts/test_quality_control_matrix.py",
    "scripts/test_quality_upgrades.py",
)
PROJECT_SPECIFIC_RUNTIME_PATTERNS = (
    re.compile(r"\bif\s+(?:shot_id|subshot_id)\s*==\s*['\"]S\d", re.I),
    re.compile(r"\bSELECTED_SHOT_IDS\b"),
)


def audit(skill_root: str) -> list[str]:
    issues = []
    if AGENT_PHASE_NAMES != CURRENT_AGENT_PHASES:
        issues.append(
            "current agent phases changed: expected %s, got %s"
            % (sorted(CURRENT_AGENT_PHASES), sorted(AGENT_PHASE_NAMES))
        )
    for relative in RETIRED_RELATIVE_PATHS:
        if os.path.exists(os.path.join(skill_root, relative)):
            issues.append("retired surface still exists: " + relative)

    contract_path = os.path.join(skill_root, "references", "format_constraints.md")
    try:
        with open(contract_path, "r", encoding="utf-8-sig") as handle:
            contract = handle.read()
    except OSError:
        issues.append("missing active field contract: references/format_constraints.md")
    else:
        if "## §A — 归档分析记录结构" in contract:
            issues.append("archive-only §A remains in the active field contract")
    scripts_dir = os.path.join(skill_root, "scripts")
    for name in os.listdir(scripts_dir):
        if not name.endswith(".py") or name.startswith("test_") or name == "golden_jimeng_check.py":
            continue
        path = os.path.join(scripts_dir, name)
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                source = handle.read()
        except OSError:
            continue
        if any(pattern.search(source) for pattern in PROJECT_SPECIFIC_RUNTIME_PATTERNS):
            issues.append("project-specific shot branch remains in production script: scripts/" + name)
    return issues


def main() -> int:
    root = os.path.dirname(os.path.dirname(__file__))
    issues = audit(root)
    print("[SKILL SURFACE] %s" % ("PASS" if not issues else "FAIL"))
    for issue in issues:
        print("- " + issue)
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
