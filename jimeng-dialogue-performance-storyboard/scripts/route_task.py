#!/usr/bin/env python3
"""Route Jimeng work to the smallest safe context set."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from scene_contract import load_contract, validate_contract
from source_gate import inspect_path


BASE_READ = ["references/runtime-core.md", "references/output-template.md"]
RISK_REFERENCES = {
    "physical_support": "references/physical-structure-continuity.md",
    "prop_transfer": "references/physical-structure-continuity.md",
    "screen_or_text": "references/generation-risk-guards.md",
    "multi_person": "references/spatial-camera-runtime.md",
    "lighting_change": "references/visual-attraction-rules.md",
}
NARRATIVE_TERMS = re.compile(r"悬疑|误会|喜剧|惊吓|威胁|蒙太奇|闪回|梦境|追逐|无台词")
NARRATIVE_STRUCTURE = re.compile(
    r"(?:直到|却发现|原来|没想到|与此同时|多年后|片刻后|忽然|骤然|真相|秘密|误认|反转|循环|倒叙)"
)
COMPLEX_CAMERA_TERMS = re.compile(
    r"环绕|多莉变焦|希区柯克|闯入式|甩镜|强运镜|正反打|"
    r"(?:摄影机|镜头|机位)[^。；;\n]{0,12}(?:快速|急速|突然)?(?:左摇|右摇|摇镜|拉开|拉远|横移)"
)
COMPLEX_CAMERA_STRUCTURE = re.compile(
    r"(?:摄影机|镜头|机位)[^。；;\n]{0,24}(?:越过|绕到|穿过|贴近|跟随|升起|下降|俯冲|后撤|甩向|掠过)"
)
CRITICAL_PERFORMANCE_TERMS = re.compile(
    r"拒绝|承认|否认|质问|坦白|道歉|告别|求婚|分手|背叛|隐瞒|秘密|保护|"
    r"别进来|别走|住手|我知道了|原来是你|关系重定义"
)
CONTRACT_RISK_REFERENCES = {
    "critical_performance_turn": ("references/prompt-performance-runtime.md",),
    "multi_person": (
        "references/prompt-performance-runtime.md",
        "references/spatial-camera-runtime.md",
        "references/blocking-facing-reference.md",
    ),
    "boundary": (
        "references/spatial-camera-runtime.md",
        "references/blocking-facing-reference.md",
    ),
    "prop_transfer": ("references/physical-structure-continuity.md",),
    "physical_support": ("references/physical-structure-continuity.md",),
    "screen_or_text": ("references/generation-risk-guards.md",),
    "complex_camera": ("references/cinematic-grammar-library.md",),
    "lighting_change": ("references/visual-attraction-rules.md",),
}


def _load_contract(contract) -> dict | None:
    if contract is None:
        return None
    if isinstance(contract, dict):
        return validate_contract(contract)
    path = Path(contract).expanduser().resolve()
    return validate_contract(load_contract(path))


def route(mode, source=None, contract=None):
    if mode == "video-review":
        return {
            "pass": True,
            "mode": mode,
            "read_first": ["references/review-pipeline.md"],
            "read_on_demand": [],
            "run_only": ["scripts/review_video.py"],
            "objective_metrics_only": True,
            "visual_semantic_review_required": True,
            "primary_output_unchanged": True,
        }
    if mode == "audit":
        return {
            "pass": True,
            "mode": mode,
            "read_first": ["references/output-template.md", "references/review-pipeline.md"],
            "read_on_demand": ["references/validation-checklist.md"],
            "run_only": ["scripts/validate_storyboard.py --compact --report <reports>/storyboard.audit.json <output.md>"],
            "design_review_required": True,
            "primary_output_unchanged": True,
        }
    if not source:
        return {"pass": False, "mode": mode, "blocking": ["generate requires --source"]}
    intake = inspect_path(source, include_text=True)
    if not intake.get("pass"):
        return {"pass": False, "mode": mode, "blocking": intake.get("blocking", []), "source_gate": intake}
    on_demand = []
    reasons = {}
    for flag in intake.get("risk_flags", {}):
        reference = RISK_REFERENCES.get(flag)
        if reference and reference not in on_demand:
            on_demand.append(reference)
            reasons.setdefault(reference, []).append(flag)
    if "multi_person" in intake.get("risk_flags", {}):
        on_demand.append("references/blocking-facing-reference.md")
        reasons.setdefault("references/blocking-facing-reference.md", []).append("two or more interacting people")
    text = intake.pop("_source_text", "")
    narrative_reason = ""
    if NARRATIVE_TERMS.search(text) or NARRATIVE_STRUCTURE.search(text):
        narrative_reason = "narrative mode or information-order signal"
    elif any(item.get("code") == "NO_EXPLICIT_BEAT" for item in intake.get("advisories", [])):
        narrative_reason = "unlabeled prose requires conservative beat routing"
    if narrative_reason:
        on_demand.append("references/narrative-mode-routing.md")
        reasons["references/narrative-mode-routing.md"] = [narrative_reason]
    if COMPLEX_CAMERA_TERMS.search(text) or COMPLEX_CAMERA_STRUCTURE.search(text):
        on_demand.append("references/cinematic-grammar-library.md")
        reasons["references/cinematic-grammar-library.md"] = ["complex camera path or viewpoint change"]
    if intake.get("stats", {}).get("speaker_count", 0) >= 3:
        on_demand.append("references/prompt-performance-runtime.md")
        reasons["references/prompt-performance-runtime.md"] = ["three or more speaking roles"]
        on_demand.append("references/spatial-camera-runtime.md")
        reasons.setdefault("references/spatial-camera-runtime.md", []).append("three or more speaking roles")
    if intake.get("performance_cues"):
        on_demand.append("references/prompt-performance-runtime.md")
        reasons.setdefault("references/prompt-performance-runtime.md", []).append("explicit source performance cue")
    if CRITICAL_PERFORMANCE_TERMS.search(text):
        on_demand.append("references/prompt-performance-runtime.md")
        reasons.setdefault("references/prompt-performance-runtime.md", []).append("critical two-person performance turn")
    contract_payload = _load_contract(contract)
    if contract_payload:
        for flag in contract_payload["risk_vector"]:
            for reference in CONTRACT_RISK_REFERENCES.get(flag, ()):
                on_demand.append(reference)
                reasons.setdefault(reference, []).append(f"scene contract: {flag}")
    on_demand = list(dict.fromkeys(on_demand))
    return {
        "pass": True,
        "mode": "generate",
        "skill_root": str(Path(__file__).resolve().parents[1]),
        "read_first": BASE_READ,
        "read_on_demand": on_demand,
        "routing_reasons": reasons,
        "run_before_generation": [
            "<skill_root>/scripts/source_gate.py --source <source> --compact --report <reports>/source-gate.json",
        ],
        "run_after_scene_contract": [{
            "script": "scripts/scene_contract.py",
            "arguments": ["<scene_contract.json>", "--strict-completeness", "--compact", "--report", "<reports>/contract.preflight.json"],
            "then_reroute_with": ["--contract", "<scene_contract.json>"],
        }],
        "run_before_each_shot": {
            "script": "scripts/contract_compile.py",
            "arguments": [
                "<scene_contract.json>", "--shot-id", "<shot_id>", "--compact",
                "--report", "<reports>/<shot_id>.contract-ledger.json",
            ],
            "purpose": "non-feed engineering ledger; preserves model-authored creative facts verbatim",
            "creative_decisions_modified": False,
        },
        "scene_contract_camera_design": {
            "before": "generation-risk adaptation",
            "tone_card": {
                "required_fields": [
                    "emotional_function", "dominant_palette", "support_palette", "accent_palette",
                    "temperature", "key_light", "shadow_tone", "contrast_saturation",
                    "background_brightness", "skin_protection", "material_anchor",
                    "allowed_variation", "forbidden_contamination",
                ],
                "optional_project_calibration": ["technical_baseline", "negative_lighting"],
                "per_shot_recovery": "first 220 prompt chars must recover dominant_palette, temperature, key_light, shadow_tone and skin_protection",
                "full_card_repetition": "forbidden; use a 35-80 character compressed prefix",
            },
            "scene_fields": ["audience_position", "movement_arc", "static_rule", "forbidden_repetition"],
            "shot_fields": ["visual_task", "shot_size", "composition", "mode", "trigger", "path", "dramatic_gain", "end_frame"],
            "overload_policy": "split high-risk actions, then restore the selected camera gain; never default to static",
            "intentional_static_exception": "scene-wide declaration plus distinct per-shot visual tasks and dramatic gains",
            "motion_ownership": "write camera path, focus transition, actor action, and prop invariants as separate clauses",
            "motion_ownership_fields": [
                "camera_path", "focus_path", "actor_path", "prop_path", "terminal_state",
            ],
            "motion_ownership_required_when": "camera.mode is not static",
            "conditional_lighting_fields": [
                "source_entities", "transport_path", "material_response", "luminance_order", "dark_region",
            ],
            "lighting_required_when": "reflective water, scales, tears, glass, metal, wet surfaces, jewelry, or gems become a visual focus",
        },
        "run_during_generation": [{
            "after": "each_shot",
            "script": "scripts/incremental_validate.py",
            "arguments": [
                "<scene_draft.md>", "--current-shot", "<shot_id>", "--compact",
                "--report", "<reports>/<shot_id>.incremental.json",
            ],
            "max_local_repair_attempts": 2,
            "scope_order": ["field", "shot", "pair", "window", "scene"],
            "first_shot_requires_strict_contract_recovery_before_next_shot": True,
        }],
        "run_before_repair_commit": {
            "script": "scripts/repair_scope.py",
            "arguments": [
                "<previous.md>", "<candidate.md>", "--target-shot", "<shot_id>",
                "--scope", "<repair_scope>", "--compact", "--report", "<reports>/<shot_id>.repair.json",
            ],
            "scene_scope_requires_explicit_reason": True,
        },
        "run_before_blocking_repair_commit": {
            "script": "scripts/blocking_repair_preflight.py",
            "arguments": [
                "<previous_spec.json>", "<candidate_spec.json>", "--compact",
                "--report", "<reports>/<shot_group>.blocking-repair.json",
            ],
            "creative_decisions_modified": False,
            "invalid_candidate_does_not_consume_repair_attempt": True,
        },
        "run_before_prompt_compilation": [{
            "when": "(two_or_more_interacting_people or (blocking_reference == required and two_or_more_visible_people)) and blocking_reference != off",
            "script": "scripts/render_blocking_reference.py",
            "arguments": [
                "<blocking_spec.json>", "--storyboard", "<planned_output.md>", "--png", "--replace",
                "--compact", "--report", "<reports>/<shot_group>.blocking.json",
            ],
            "one_pair_per_shot_group": True,
            "exact_shot_number_filenames": True,
            "same_directory_as_storyboard": False,
            "staging_required": True,
            "same_source_svg_png": True,
        }, {
            "script": "<skill_root>/scripts/prompt_preflight.py",
            "arguments": ["<scene_draft.md>", "--advisory", "--compact", "--report", "<reports>/prompt.json"],
            "mutates_primary_output": False,
        }, {
            "script": "<skill_root>/scripts/creative_preflight.py",
            "arguments": ["<scene_draft.md>", "--advisory", "--compact", "--report", "<reports>/creative.json"],
            "mutates_primary_output": False,
        }],
        "run_after_generation": [
            "scripts/validate_storyboard.py --compact --report <reports>/storyboard.json --shadow-report --seedance-target <target> <output.md>",
            "scripts/scene_contract.py <scene_contract.json> --storyboard <output.md> --strict-completeness --compact --report <reports>/contract.final.json",
            "scripts/prompt_preflight.py <output.md> --compact --report <reports>/prompt.final.json",
            "scripts/creative_preflight.py <output.md> --compact --report <reports>/creative.final.json",
        ],
        "read_after_generation": ["references/review-pipeline.md"],
        "run_before_visual_review": {
            "script": "scripts/image_review_prep.py",
            "arguments": [
                "<delivery_dir>", "--output-dir", "<reports>/thumbnails", "--max-size", "320",
                "--compact", "--report", "<reports>/image-review-prep.json",
            ],
            "original_resolution_allowed": "only for thumbnail-suspect images",
        },
        "run_after_review": [
            "scripts/review_manifest.py create --delivery-root <delivery_dir> --compact --report <reports>/manifest.json",
            "scripts/review_manifest.py verify --delivery-root <delivery_dir> --compact --report <reports>/manifest.verify.json",
        ],
        "run_after_blocking_visual_review": [
            "scripts/promote_blocking_reference.py record --render-report <blocking.json> --decision <PASS|REVISE> --review <blocking-review.json> --compact --report <reports>/blocking-review.record.json",
            "scripts/promote_blocking_reference.py promote --review <blocking-review.json> --delivery-dir <approved-blocking-dir> --compact --report <reports>/blocking-promotion.json",
        ],
        "optional_after_delivery": ["scripts/concise_storyboard.py"],
        "execution_policy": {
            "source_gate": "once per source SHA-256; reuse the report until the source changes",
            "route": "once per source/contract SHA-256; reuse the route until either changes",
            "reports": "write full JSON reports to files and print compact summaries only",
            "incremental_validation": "shot plus required continuity windows; never use it as the final file gate",
            "full_validation": "scene/file boundary, after broad contract changes, or before delivery",
            "images": "start with thumbnails/contact sheets; inspect original-resolution PNG only for a suspected issue",
            "context": "one scene or shot group per execution context; restore only version, passed gates, open issues, next action",
            "creative_boundary": "the model owns narrative, performance, blocking, camera, focus, lighting, palette and prompt language; tools only validate and serialize deterministic engineering facts",
            "engineering_tools_must_not_choose_creative_repairs": True,
        },
        "preload_all_references": False,
        "primary_output_unchanged": True,
        "source_gate": intake,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("generate", "audit", "video-review"))
    parser.add_argument("--source")
    parser.add_argument("--contract")
    parser.add_argument("--compact", action="store_true", help="print routing summary; keep full JSON in --report")
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    if not args.compact or not args.report:
        parser.error("legacy route output is disabled; --compact and --report are required")
    result = route(args.mode, args.source, args.contract)
    if args.report:
        report = Path(args.report).expanduser().resolve()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.compact:
        print(json.dumps({
            "status": "PASS" if result.get("pass") else "FAIL",
            "mode": result.get("mode", args.mode),
            "read_first": result.get("read_first", []),
            "read_on_demand_count": len(result.get("read_on_demand", [])),
            "blocking": result.get("blocking", []),
            "report": str(Path(args.report).expanduser().resolve()) if args.report else None,
        }, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
