#!/usr/bin/env python3
"""Route Jimeng work without making creative decisions.

Routing may select references and deterministic tools. It must never select a
shot, performance, camera, focus, lighting, palette, or creative repair.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from source_gate import inspect_path


BASE_READ = ["references/runtime-core.md"]
SEEDANCE_TARGETS = {"auto", "2.0", "2.5", "both"}
CREATIVE_REFERENCE_CATALOG = {
    "palette_and_lighting": {
        "path": "references/color-palette-library.md",
        "when": "the project has no locked scene visual baseline, or a scene needs a motivated visual-state transition",
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
    "generation_diagnostics": {
        "path": "references/seedance-generation-diagnostics.md",
        "when": "an actual keyframe or video has identity, occlusion, framing, action, camera, focus, exposure, material, or reference-conflict failures that need model-led diagnosis",
    },
}
def _minimal_intake(intake: dict) -> dict:
    """Keep the route report useful without embedding source-derived prose."""
    return {
        "source_path": intake.get("source_path"),
        "source_sha256": intake.get("source_sha256"),
        "stats": intake.get("stats", {}),
        "blocking": intake.get("blocking", []),
        "advisory_codes": [item.get("code") for item in intake.get("advisories", [])],
    }


def route(mode: str, source: str | None = None, seedance_target: str = "auto") -> dict:
    if seedance_target not in SEEDANCE_TARGETS:
        return {"pass": False, "mode": mode, "blocking": [f"unsupported seedance_target: {seedance_target}"]}
    if mode == "video-review":
        return {
            "pass": True,
            "mode": mode,
            "read_first": ["references/review-pipeline.md"],
            "read_on_demand": [],
            "run_only": [],
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

    intake = inspect_path(source)
    if not intake.get("pass"):
        return {"pass": False, "mode": mode, "blocking": intake.get("blocking", []), "source_intake": _minimal_intake(intake)}
    resolved_target = "2.0" if seedance_target == "auto" else seedance_target

    return {
        "pass": True,
        "mode": "generate",
        "requested_seedance_target": seedance_target,
        "seedance_target": resolved_target,
        "target_resolution": (
            "auto resolves deterministically to the 2.0 compatibility baseline; use --seedance-target 2.5 when the active interface is confirmed"
            if seedance_target == "auto" else "explicit target"
        ),
        "skill_root": str(Path(__file__).resolve().parents[1]),
        "read_first": BASE_READ,
        "read_before_delivery": ["references/output-template.md", "references/seedance-target-adaptation.md"],
        "read_on_demand": [],
        "routing_reasons": {},
        "run_before_generation": [],
        "optional_spatial_workflow": {
            "selection": "none|2d",
            "when": "use none when the shot is spatially unambiguous; use 2d when plan-view positions, body facings, boundaries, axis side, camera position, or FOV need visual proof",
            "selection_owner": "model; never source-keyword auto-routing",
            "designer": "model chooses positions, body facings, boundaries, camera, and FOV; text owns posture, head direction, gaze, hand contacts, and prop height",
            "base_render": "scripts/render_blocking_reference.py",
            "base_read_when_selected": "references/blocking-facing-reference.md",
            "staging_only": True,
            "blocking_scope": ["collision", "solid_intersection", "blocked_view", "declared_axis_side"],
            "advisory_scope": ["clearance", "composition_ratio", "mutual_facing_tolerance", "edge_clipping", "label_layout"],
            "visual_review_before_promotion": True,
            "blocking_png_promotion": (
                "scripts/promote_blocking_reference.py promote --review <reports>/blocking.review.json "
                "--delivery-dir <delivery>/approved-jimeng-2d --compact --report <reports>/blocking.promote.json"
            ),
            "audit_images_promoted": False,
            "blocking_png_generation_reference_allowed_after_review": True,
            "complex_pose_fallback": "write named facts in the direct prompt, split the shot, or use an already reviewed keyframe/reference video",
        },
        "run_after_generation": [
            "scripts/validate_delivery.py --source <source> --storyboard <output.md> "
            "--seedance-target <target> --compact --report <reports>/delivery.draft.json"
        ],
        "read_after_generation": ["references/review-pipeline.md"],
        "run_after_review": [
            "scripts/review_manifest.py create --source <source> --output <output.md> --manifest <manifest.json> "
            "--review-mode <independent|self_check> --design-review <PASS|REVISE> "
            "--visual-review <PASS|REVISE|NOT_APPLICABLE|NOT_RUN> --delivery-root <delivery_dir> "
            "--compact --report <reports>/manifest.create.json",
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
            "source_intake_cache": "reuse while source SHA-256 is unchanged",
            "reports": "full JSON on disk; compact terminal summary",
        },
        "source_intake": _minimal_intake(intake),
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
