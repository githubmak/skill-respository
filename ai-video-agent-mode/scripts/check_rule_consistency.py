#!/usr/bin/env python3
"""Check the creative-sovereignty architecture for internal contradictions."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from contract_registry import PROMPT_CONTRACT_VERSION, machine_contract_issues
from creative_engineering_boundary import MODEL, field_owner


DETERMINISTIC_RUNTIME_FILES = (
    "scripts/validate_deterministic_package.py",
    "scripts/validate_composer_output.py",
    "scripts/validate_modec.py",
    "scripts/check_export.py",
    "scripts/export_with_validation.py",
    "scripts/normalize_prompt_package.py",
    "scripts/batch_planner.py",
    "scripts/dispatch_cache.py",
    "scripts/workflow_supervisor.py",
)

FORBIDDEN_RUNTIME_CALLS = (
    "production_control_grounding_issues",
    "aesthetic_directing_contract_issues",
    "camera_competition_issues",
    "adapt_lighting_text",
    "adapt_visual_prefix",
    "compile_direct_prompt(",
    "compile_director_card(",
    "build_negative_prompt_for_item",
    "from shot_semantics import",
    "from production_intelligence import",
    "from prompt_contract import",
    "dispatch_risk(",
)

MODEL_FIELDS = (
    "full_prompt",
    "seedance_prompt",
    "seedance_prompt_variants",
    "director_card",
    "negative_prompt",
    "qa_metadata.scene_tone_palette",
    "qa_metadata.continuity_contract",
    "qa_metadata.performance_contract",
)


def check(skill_root):
    issues = list(machine_contract_issues())
    for field in MODEL_FIELDS:
        if field_owner(field) != MODEL:
            issues.append("creative field is not model-owned: %s" % field)

    for relative in DETERMINISTIC_RUNTIME_FILES:
        path = os.path.join(skill_root, relative)
        text = _read(path)
        if text is None:
            issues.append("missing runtime file: " + relative)
            continue
        for forbidden in FORBIDDEN_RUNTIME_CALLS:
            if forbidden in text:
                issues.append("%s contains forbidden creative heuristic call: %s" % (relative, forbidden))

    export_text = _read(os.path.join(skill_root, "scripts", "export_with_validation.py")) or ""
    for required in ("selected_seedance_prompt", '"semantic_transform": False', "CREATIVE_REWRITE_REQUIRED"):
        if required not in export_text:
            issues.append("export does not prove pass-through model prompts: " + required)

    boundary = _read(os.path.join(skill_root, "references", "creative_engineering_boundary.md")) or ""
    for required in ("Seedance", "关键词", "正则", "大模型", "工程"):
        if required not in boundary:
            issues.append("creative boundary is missing: " + required)

    schema = _read(os.path.join(skill_root, "references", "schemas", "pipeline.schema.json")) or ""
    for required in (
        '"seedance_prompt"', '"seedance_prompt_variants"', '"director_card"',
        '"additionalProperties": true', '"description": "Model-owned creative analysis.',
    ):
        if required not in schema:
            issues.append("pipeline schema is missing: " + required)

    registry_path = os.path.join(skill_root, "scripts", "contract_registry.py")
    for root, _dirs, files in os.walk(skill_root):
        for filename in files:
            if not filename.endswith((".py", ".md", ".json", ".yaml")):
                continue
            path = os.path.join(root, filename)
            if path == registry_path:
                continue
            text = _read(path) or ""
            if PROMPT_CONTRACT_VERSION in text:
                issues.append("%s duplicates the current prompt contract literal" % os.path.relpath(path, skill_root))
    return {"pass": not issues, "issues": issues, "rule_count": 5}


def _read(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return handle.read()
    except OSError:
        return None


if __name__ == "__main__":
    result = check(os.path.dirname(os.path.dirname(__file__)))
    print("[RULE CONSISTENCY] %s" % ("PASS" if result["pass"] else "FAIL"))
    for issue in result["issues"]:
        print("- " + issue)
    raise SystemExit(0 if result["pass"] else 1)
