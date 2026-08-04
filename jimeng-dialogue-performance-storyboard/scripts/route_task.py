#!/usr/bin/env python3
"""Route Jimeng work to the smallest safe context set."""

from __future__ import annotations

import argparse
import json
import re

from source_gate import inspect_path


BASE_READ = ["references/runtime-core.md", "references/output-template.md"]
RISK_REFERENCES = {
    "physical_support": "references/physical-structure-continuity.md",
    "prop_transfer": "references/physical-structure-continuity.md",
    "screen_or_text": "references/generation-risk-guards.md",
    "multi_person": "references/spatial-camera-continuity.md",
    "lighting_change": "references/visual-attraction-rules.md",
}
NARRATIVE_TERMS = re.compile(r"悬疑|误会|喜剧|惊吓|威胁|蒙太奇|闪回|梦境|追逐|无台词")
COMPLEX_CAMERA_TERMS = re.compile(
    r"环绕|多莉变焦|希区柯克|闯入式|甩镜|强运镜|正反打|"
    r"(?:摄影机|镜头|机位)[^。；;\n]{0,12}(?:快速|急速|突然)?(?:左摇|右摇|摇镜|拉开|拉远|横移)"
)


def route(mode, source=None):
    if mode == "video-review":
        return {
            "pass": True,
            "mode": mode,
            "read_first": [],
            "read_on_demand": [],
            "run_only": ["scripts/review_video.py"],
            "primary_output_unchanged": True,
        }
    if mode == "audit":
        return {
            "pass": True,
            "mode": mode,
            "read_first": ["references/output-template.md"],
            "read_on_demand": ["references/validation-checklist.md"],
            "run_only": ["scripts/validate_storyboard.py"],
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
    text = intake.pop("_source_text", "")
    if NARRATIVE_TERMS.search(text):
        on_demand.append("references/narrative-mode-routing.md")
        reasons["references/narrative-mode-routing.md"] = ["non-default narrative mode"]
    if COMPLEX_CAMERA_TERMS.search(text):
        on_demand.append("references/cinematic-grammar-library.md")
        reasons["references/cinematic-grammar-library.md"] = ["complex camera request"]
    if intake.get("stats", {}).get("speaker_count", 0) >= 3:
        on_demand.append("references/prompt-performance-rules.md")
        reasons["references/prompt-performance-rules.md"] = ["three or more speaking roles"]
        on_demand.append("references/spatial-camera-continuity.md")
        reasons.setdefault("references/spatial-camera-continuity.md", []).append("three or more speaking roles")
    on_demand = list(dict.fromkeys(on_demand))
    return {
        "pass": True,
        "mode": "generate",
        "read_first": BASE_READ,
        "read_on_demand": on_demand,
        "routing_reasons": reasons,
        "run_before_generation": ["scripts/source_gate.py"],
        "run_during_generation": [{
            "after": "each_shot",
            "command": "python3 scripts/incremental_validate.py <scene_draft.md> --current-shot <shot_id>",
            "max_local_repair_attempts": 2,
            "scope_order": ["field", "shot", "pair", "window", "scene"],
        }],
        "run_after_generation": ["scripts/validate_storyboard.py", "scripts/concise_storyboard.py"],
        "preload_all_references": False,
        "primary_output_unchanged": True,
        "source_gate": intake,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("generate", "audit", "video-review"))
    parser.add_argument("--source")
    args = parser.parse_args(argv)
    result = route(args.mode, args.source)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
