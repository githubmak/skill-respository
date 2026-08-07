#!/usr/bin/env python3
"""Route Jimeng work without making creative decisions.

Routing may select references and deterministic tools. It must never select a
shot, performance, camera, focus, lighting, palette, or creative repair.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from source_gate import inspect_path


BASE_READ = ["references/runtime-core.md", "references/output-template.md"]
SEEDANCE_TARGETS = {"auto", "2.0", "2.5", "both"}
CREATIVE_REFERENCE_CATALOG = {
    "palette_and_lighting": {
        "path": "references/color-palette-library.md",
        "when": "the project has no locked palette, or a scene needs distinct per-shot palette, tonal, and lighting design",
    },
    "liveness": {
        "path": "references/liveness-motion-grammar.md",
        "when": "dialogue, reaction, silence, or low-motion staging risks looking inert or generic",
    },
    "performance": {
        "path": "references/performance-baseline-library.md",
        "when": "character strategy, emotional leakage, or listener response needs individualization",
    },
    "scene_material": {
        "path": "references/scene-preset-library.md",
        "when": "location anchors, usable props, material response, or lived-in detail need development",
    },
    "shot_language": {
        "path": "references/shot-patterns.md",
        "when": "multi-person staging, prop transfer, entrances, boundaries, or shot transitions are complex",
    },
    "visual_direction": {
        "path": "references/visual-direction-profiles.md",
        "when": "the user requests a visual style or the source contains strong period, place, material, weather, or lighting evidence",
    },
    "camera_grammar": {
        "path": "references/cinematic-grammar-library.md",
        "when": "the model needs a more expressive or more legible relationship between camera position, movement, focus, blocking, and editing",
    },
    "narrative_modes": {
        "path": "references/narrative-mode-routing.md",
        "when": "information order, family or ensemble response, comedy, silence, suspense, montage, or non-dialogue causality needs development",
    },
    "seedance_expression_examples": {
        "path": "references/seedance-example-patterns.md",
        "when": "a finished director design contains complex subject ownership, timing, paths, reference frames, props, focus, lighting stability, or reference assets",
    },
    "generation_diagnostics": {
        "path": "references/seedance-generation-diagnostics.md",
        "when": "an actual keyframe or video has identity, occlusion, framing, action, camera, focus, exposure, material, or reference-conflict failures that need model-led diagnosis",
    },
}
RISK_REFERENCES = {
    "physical_support": "references/physical-structure-continuity.md",
    "prop_transfer": "references/physical-structure-continuity.md",
    "screen_or_text": "references/generation-risk-guards.md",
    "multi_person": "references/spatial-camera-runtime.md",
    "lighting_change": "references/visual-attraction-rules.md",
}
PERFORMANCE_SIGNAL = re.compile(
    r"拒绝|承认|否认|质问|坦白|道歉|告别|保护|隐瞒|秘密|"
    r"别进来|别走|住手|我知道了|原来是你"
)


def _append(items: list[str], reasons: dict[str, list[str]], reference: str, reason: str) -> None:
    if reference not in items:
        items.append(reference)
    reasons.setdefault(reference, []).append(reason)


def route(mode: str, source: str | None = None, seedance_target: str = "auto") -> dict:
    if seedance_target not in SEEDANCE_TARGETS:
        return {"pass": False, "mode": mode, "blocking": [f"unsupported seedance_target: {seedance_target}"]}
    if mode == "video-review":
        return {
            "pass": True,
            "mode": mode,
            "read_first": ["references/review-pipeline.md"],
            "read_on_demand": [],
            "run_only": ["scripts/review_video.py"],
            "objective_metrics_only": True,
            "model_visual_review_required": True,
            "creative_decisions_modified": False,
        }
    if mode == "audit":
        return {
            "pass": True,
            "mode": mode,
            "read_first": ["references/output-template.md", "references/review-pipeline.md"],
            "read_on_demand": [],
            "run_only": [
                "scripts/validate_delivery.py --source <source> --storyboard <output.md> "
                "--seedance-target <target> --compact --report <reports>/delivery.audit.json"
            ],
            "model_design_review_required": True,
            "creative_decisions_modified": False,
        }
    if not source:
        return {"pass": False, "mode": mode, "blocking": ["generate requires --source"]}

    intake = inspect_path(source, include_text=True)
    if not intake.get("pass"):
        return {"pass": False, "mode": mode, "blocking": intake.get("blocking", []), "source_gate": intake}
    text = intake.pop("_source_text", "")
    on_demand: list[str] = []
    reasons: dict[str, list[str]] = {}
    creative_suggestions: list[str] = []
    creative_reasons: dict[str, list[str]] = {}
    for flag in intake.get("risk_flags", {}):
        reference = RISK_REFERENCES.get(flag)
        if reference:
            _append(on_demand, reasons, reference, f"source risk: {flag}")
    if "multi_person" in intake.get("risk_flags", {}):
        _append(on_demand, reasons, "references/blocking-facing-reference.md", "multi-person spatial relationship")
    if (
        intake.get("stats", {}).get("speaker_count", 0) >= 2
        or intake.get("performance_cues")
        or PERFORMANCE_SIGNAL.search(text)
    ):
        _append(on_demand, reasons, "references/prompt-performance-runtime.md", "dialogue performance relationship")
        _append(creative_suggestions, creative_reasons, "references/performance-baseline-library.md", "individualized dialogue performance")
        _append(creative_suggestions, creative_reasons, "references/liveness-motion-grammar.md", "dialogue and reaction liveness")
    risk_flags = intake.get("risk_flags", {})
    if any(flag in risk_flags for flag in ("multi_person", "prop_transfer", "screen_or_text")):
        _append(creative_suggestions, creative_reasons, "references/shot-patterns.md", "complex staging or prop/camera readability")
    if (
        intake.get("stats", {}).get("scene_line_count", 0) > 1
        or any(flag in risk_flags for flag in ("physical_support", "prop_transfer", "multi_person"))
    ):
        _append(creative_suggestions, creative_reasons, "references/scene-preset-library.md", "scene anchors and usable material detail")
    _append(
        creative_suggestions,
        creative_reasons,
        "references/color-palette-library.md",
        "every shot requires independent palette, tonal, and lighting design",
    )
    if seedance_target in {"2.5", "both"}:
        _append(on_demand, reasons, "references/seedance-target-adaptation.md", f"explicit target: {seedance_target}")

    return {
        "pass": True,
        "mode": "generate",
        "seedance_target": seedance_target,
        "skill_root": str(Path(__file__).resolve().parents[1]),
        "read_first": BASE_READ,
        "read_on_demand": on_demand,
        "routing_reasons": reasons,
        "creative_reference_suggestions": creative_suggestions,
        "creative_suggestion_reasons": creative_reasons,
        "run_before_generation": [
            "<skill_root>/scripts/source_gate.py --source <source> --compact --report <reports>/source-gate.json"
        ],
        "optional_spatial_workflow": {
            "when": "spatial geometry materially affects blocking, boundary, occlusion, or camera FOV",
            "selection_owner": "model; never source-keyword auto-routing",
            "designer": "model chooses positions, facings, posture, gaze, hand contacts, camera, and FOV",
            "base_render": "scripts/render_blocking_reference.py",
            "vtk_render": "scripts/render_mannequin_reference.py",
            "vtk_read_when_selected": "references/mannequin-blocking.md",
            "vtk_when": "2D cannot prove posture/support, body-versus-head facing, hand contact, prop height, occlusion, or actual camera projection",
            "vtk_per_shot_mandatory": False,
            "physical_state_hash_deduplication": True,
            "shared_scene_multiple_camera_views": True,
            "explicit_shot_id_required": True,
            "frame_contract": {
                "width": 1920,
                "height": 1080,
                "aspect": "16:9",
                "capture_scope": "direct 1920x1080 renderer output",
            },
            "automatic_capture_required": True,
            "automatic_capture_owner": "render_mannequin_reference.py",
            "manual_user_capture": False,
            "browser_required": False,
            "html_output": False,
            "staging_only": True,
            "validator_scope": ["collision", "clearance", "occlusion", "axis_side", "field_of_view", "label_layout"],
            "visual_review_before_promotion": True,
            "mannequin_review_record": (
                "scripts/promote_mannequin_reference.py record --render-report <mannequin-report.json> "
                "--screenshot-dir <delivery>/staging/mannequin --decision <PASS|REVISE> "
                "--review <reports>/mannequin.review.json --compact --report <reports>/mannequin.record.json"
            ),
            "mannequin_clean_promotion": (
                "scripts/promote_mannequin_reference.py promote --review <reports>/mannequin.review.json "
                "--delivery-dir <delivery>/approved-mannequin --compact --report <reports>/mannequin.promote.json"
            ),
            "audit_images_promoted": False,
            "clean_images_generation_reference_allowed_after_review": True,
        },
        "run_after_generation": [
            "scripts/validate_delivery.py --source <source> --storyboard <output.md> "
            "--seedance-target <target> --compact --report <reports>/delivery.draft.json"
        ],
        "read_after_generation": ["references/review-pipeline.md"],
        "run_after_review": [
            "scripts/review_manifest.py create --source <source> --output <output.md> --manifest <manifest.json> "
            "--review-mode <independent|self_check> --design-review <PASS|REVISE> "
            "--visual-review <PASS|REVISE|NOT_RUN> --delivery-root <delivery_dir> "
            "--compact --report <reports>/manifest.create.json",
            "scripts/review_manifest.py verify --manifest <manifest.json> --delivery-root <delivery_dir> "
            "--compact --report <reports>/manifest.verify.json",
            "scripts/validate_delivery.py --source <source> --storyboard <output.md> "
            "--seedance-target <target> --final --review-manifest <manifest.json> "
            "--compact --report <reports>/delivery.final.json",
        ],
        "creative_reference_catalog": CREATIVE_REFERENCE_CATALOG,
        "execution_policy": {
            "creative_owner": "model",
            "engineering_owner": "deterministic delivery facts only",
            "creative_keyword_gates": False,
            "creative_scores_or_quotas": False,
            "contract_recovery": False,
            "per_shot_validator_loop": False,
            "source_gate_cache": "reuse while source SHA-256 is unchanged",
            "reports": "full JSON on disk; compact terminal summary",
        },
        "source_gate": intake,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("generate", "audit", "video-review"))
    parser.add_argument("--source")
    parser.add_argument("--seedance-target", choices=tuple(sorted(SEEDANCE_TARGETS)), default="auto")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    if not args.compact or not args.report:
        parser.error("--compact and --report are required")
    result = route(args.mode, args.source, args.seedance_target)
    report = Path(args.report).expanduser().resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS" if result.get("pass") else "FAIL",
        "mode": result.get("mode", args.mode),
        "read_first": result.get("read_first", []),
        "read_on_demand_count": len(result.get("read_on_demand", [])),
        "blocking": result.get("blocking", []),
        "report": str(report),
    }, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
