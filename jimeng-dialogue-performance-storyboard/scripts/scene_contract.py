#!/usr/bin/env python3
"""Validate compact internal scene contracts and prompt fact recovery."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from validate_storyboard import direct_prompt, iter_children, iter_groups


SHOT_ID_RE = re.compile(r"^S\d+-\d+-\d+$")
RISK_FLAGS = {
    "critical_performance_turn",
    "multi_person",
    "boundary",
    "prop_transfer",
    "physical_support",
    "screen_or_text",
    "complex_camera",
    "lighting_change",
}
PERFORMANCE_FIELDS = (
    "source_anchor",
    "relationship_goal",
    "speaker_actor",
    "speaker_visible_fact",
    "listener_actor",
    "listener_trigger",
    "listener_visible_fact",
    "end_residue",
    "readability",
    "camera_service",
)
VISUAL_FIELDS = ("first_focus", "core_fact", "end_image")


def _text(value: object, label: str, *, required: bool = True) -> str:
    result = str(value or "").strip()
    if required and not result:
        raise ValueError(f"{label} is required")
    return result


def validate_contract(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("scene contract must be an object")
    version = payload.get("version", 1)
    if version != 1:
        raise ValueError("scene contract version must be 1")
    scene_id = _text(payload.get("scene_id"), "scene_id")
    risks = payload.get("risk_vector", [])
    if not isinstance(risks, list):
        raise ValueError("risk_vector must be a list")
    risks = list(dict.fromkeys(_text(item, "risk_vector item") for item in risks))
    unknown = sorted(set(risks) - RISK_FLAGS)
    if unknown:
        raise ValueError("unknown risk flags: " + ",".join(unknown))
    raw_shots = payload.get("shots")
    if not isinstance(raw_shots, list) or not raw_shots:
        raise ValueError("shots must contain at least one shot contract")
    shot_ids: set[str] = set()
    shots = []
    for index, shot in enumerate(raw_shots, start=1):
        if not isinstance(shot, dict):
            raise ValueError(f"shots[{index}] must be an object")
        shot_id = _text(shot.get("shot_id"), f"shots[{index}].shot_id")
        if not SHOT_ID_RE.fullmatch(shot_id):
            raise ValueError(f"shots[{index}].shot_id must match S1-01-1")
        if shot_id in shot_ids:
            raise ValueError(f"duplicate shot_id: {shot_id}")
        shot_ids.add(shot_id)
        performance = shot.get("performance")
        if performance is None:
            normalized_performance = None
        elif isinstance(performance, dict):
            normalized_performance = {
                field: _text(performance.get(field), f"{shot_id}.performance.{field}")
                for field in PERFORMANCE_FIELDS
            }
            if normalized_performance["speaker_actor"] == normalized_performance["listener_actor"]:
                raise ValueError(f"{shot_id} speaker_actor and listener_actor must differ")
        else:
            raise ValueError(f"{shot_id}.performance must be an object or null")
        visual = shot.get("visual_core")
        if not isinstance(visual, dict):
            raise ValueError(f"{shot_id}.visual_core must be an object")
        normalized_visual = {
            field: _text(visual.get(field), f"{shot_id}.visual_core.{field}")
            for field in VISUAL_FIELDS
        }
        spatial = shot.get("spatial") or {}
        if not isinstance(spatial, dict):
            raise ValueError(f"{shot_id}.spatial must be an object")
        blocking_id = _text(spatial.get("blocking_id"), f"{shot_id}.spatial.blocking_id", required=False)
        protected = shot.get("protected_facts", [])
        if not isinstance(protected, list):
            raise ValueError(f"{shot_id}.protected_facts must be a list")
        protected = list(dict.fromkeys(_text(item, f"{shot_id}.protected_facts item") for item in protected))
        shots.append({
            "shot_id": shot_id,
            "performance": normalized_performance,
            "visual_core": normalized_visual,
            "spatial": {"blocking_id": blocking_id},
            "protected_facts": protected,
        })
    return {"version": 1, "scene_id": scene_id, "risk_vector": risks, "shots": shots}


def _compact(text: str) -> str:
    return re.sub(r"[\s，。；;：:、|/（）()《》【】\[\]“”\"'‘’]+", "", text)


def _covered(fact: str, prompt: str) -> bool:
    fact_text = _compact(fact)
    prompt_text = _compact(prompt)
    if not fact_text:
        return True
    if fact_text in prompt_text:
        return True
    if len(fact_text) < 4:
        return fact_text in prompt_text
    grams = {fact_text[index:index + 2] for index in range(len(fact_text) - 1)}
    prompt_grams = {prompt_text[index:index + 2] for index in range(max(0, len(prompt_text) - 1))}
    return bool(grams) and len(grams & prompt_grams) / len(grams) >= 0.68


def storyboard_prompts(markdown: str) -> dict[str, str]:
    prompts: dict[str, str] = {}
    for group in iter_groups(markdown):
        group_id = group.group(1)
        for number, child in enumerate(iter_children(group.group(3)), start=1):
            prompts[f"{group_id}-{number}"] = direct_prompt(child.group(0))
    return prompts


def recovery_issues(contract: dict, markdown: str) -> list[str]:
    contract = validate_contract(contract)
    prompts = storyboard_prompts(markdown)
    issues: list[str] = []
    for shot in contract["shots"]:
        shot_id = shot["shot_id"]
        prompt = prompts.get(shot_id, "")
        if not prompt:
            issues.append(f"{shot_id}: missing direct prompt for contract recovery")
            continue
        performance = shot["performance"]
        facts = [
            ("first_focus", shot["visual_core"]["first_focus"]),
            ("core_fact", shot["visual_core"]["core_fact"]),
            *[("protected_fact", item) for item in shot["protected_facts"]],
        ]
        if performance:
            for actor_field in ("speaker_actor", "listener_actor"):
                actor = performance[actor_field]
                if actor not in prompt:
                    issues.append(f"{shot_id}: protected actor missing -> {actor}")
            facts[:0] = [
                ("speaker_visible_fact", performance["speaker_visible_fact"]),
                ("listener_trigger", performance["listener_trigger"]),
                ("listener_visible_fact", performance["listener_visible_fact"]),
                ("readability", performance["readability"]),
                ("camera_service", performance["camera_service"]),
            ]
        for label, fact in facts:
            if not _covered(fact, prompt):
                issues.append(f"{shot_id}: {label} not recovered in direct prompt -> {fact}")
        terminal_window = prompt[max(0, len(prompt) * 3 // 4):]
        if performance:
            residue = performance["end_residue"]
            if not _covered(residue, terminal_window):
                issues.append(f"{shot_id}: end_residue missing from final 25% -> {residue}")
        end_image = shot["visual_core"]["end_image"]
        if not _covered(end_image, terminal_window):
            issues.append(f"{shot_id}: end_image missing from final 25% -> {end_image}")
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract")
    parser.add_argument("--storyboard")
    args = parser.parse_args(argv)
    try:
        contract_path = Path(args.contract).expanduser().resolve()
        contract = validate_contract(json.loads(contract_path.read_text(encoding="utf-8-sig")))
        issues = []
        if args.storyboard:
            markdown = Path(args.storyboard).expanduser().resolve().read_text(encoding="utf-8-sig")
            issues = recovery_issues(contract, markdown)
        result = {
            "pass": not issues,
            "scene_id": contract["scene_id"],
            "shot_count": len(contract["shots"]),
            "risk_vector": contract["risk_vector"],
            "issues": issues,
            "primary_storyboard_modified": False,
        }
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"pass": False, "error": str(exc), "primary_storyboard_modified": False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
