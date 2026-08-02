#!/usr/bin/env python3
"""Build a conservative pre-composition motion plan from the shot plan.

The plan reserves cross-shot motion roles and semantic motion families before
Master Production writes prompts. It never invents a visible action: workers
must still ground every driver and response in the source or Scene Lock.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


PLAN_VERSION = "scene-motion-plan-v1"

LOCOMOTION_RE = re.compile(r"走|跑|奔|追|靠近|离开|退后|上前|起身|坐下|落地|起跳|轻功|骑")
PROP_CONTACT_RE = re.compile(r"拿|握|抓|压|推|拉|递|接|放|碰|触|开门|关门|杯|文件|手机|剑|刀|伞")
EYELINE_RE = re.compile(r"看|望|盯|抬眼|转头|回头|视线|目光")
ENVIRONMENT_RE = re.compile(r"风|雨|雪|云|门响|脚步|车灯|窗光|烛|火|水纹|倒影|反光")
CHANGE_RE = re.compile(r"打开|关闭|推开|转向|转身|起身|坐下|递|接|放下|拿起|拔|落|停|进入|离开|出现|消失")


def build(run_dir: str, output_path: str | None = None) -> tuple[dict[str, Any], str]:
    run_path = Path(run_dir).expanduser().resolve()
    plan_path = run_path / ".cache" / "orchestrator" / "shot_plan.json"
    plan = _load(plan_path)
    shots = plan.get("shots", []) if isinstance(plan, dict) else []
    if not isinstance(shots, list) or not shots:
        raise ValueError("scene motion plan requires a non-empty normalized shot_plan.json")

    scene_groups: dict[str, list[dict[str, Any]]] = {}
    for shot in shots:
        if not isinstance(shot, dict):
            continue
        scene = str(shot.get("scene", "") or "__default__")
        scene_groups.setdefault(scene, []).append(shot)

    scenes = []
    advisories = []
    for scene, scene_shots in scene_groups.items():
        roles = _roles_for_count(len(scene_shots), scene_shots)
        records = []
        previous_family = ""
        for index, (shot, role) in enumerate(zip(scene_shots, roles)):
            text = _shot_text(shot)
            family, alternatives = _motion_family(text, previous_family)
            previous_family = family
            visible = _characters(shot)
            dialogue = any(
                subshot.get("dialogue_refs")
                for subshot in shot.get("subshots", [])
                if isinstance(subshot, dict)
            )
            response_budget = 1 if dialogue or len(visible) > 1 else 2
            driver = _driver_class(text)
            if driver == "deliberate_hold":
                response_budget = 0
            records.append({
                "shot_id": str(shot.get("shot_id", "") or ""),
                "subshot_ids": [
                    str(item.get("subshot_id", "") or "")
                    for item in shot.get("subshots", [])
                    if isinstance(item, dict)
                ],
                "dynamic_role": role,
                "source_driver_class": driver,
                "reserved_motion_family": family,
                "allowed_alternatives": alternatives,
                "response_budget": response_budget,
                "camera_budget": "locked_or_one_motivated_low_amplitude_path",
                "static_anchor_required": True,
                "stable_end_state_required": True,
                "source_grounding_required": True,
            })
            if driver == "deliberate_hold" and role not in {"hold", "recover"}:
                advisories.append({
                    "severity": "advisory",
                    "scene": scene,
                    "shot_id": str(shot.get("shot_id", "") or ""),
                    "code": "MOTION_DRIVER_SPARSE",
                    "message": "本镜缺少明确源文动力源；允许保持稳定，不得为动态角色强加动作",
                })
        scenes.append({
            "scene": scene,
            "motion_roles": roles,
            "shots": records,
            "policy": "角色仅分配跨镜动静职责；可见动作必须回指源文或Scene Lock，弱证据不强行动画",
        })

    result = {
        "plan_version": PLAN_VERSION,
        "blocking": [],
        "advisories": advisories,
        "scenes": scenes,
    }
    destination = Path(output_path) if output_path else run_path / ".cache" / "orchestrator" / "scene_motion_plan.json"
    _write(destination, result)
    return result, str(destination)


def shot_motion_record(plan: dict[str, Any], shot_id: str, scene: str = "") -> dict[str, Any]:
    for scene_record in plan.get("scenes", []) if isinstance(plan, dict) else []:
        if scene and str(scene_record.get("scene", "")) != str(scene):
            continue
        for record in scene_record.get("shots", []) if isinstance(scene_record, dict) else []:
            if str(record.get("shot_id", "")) == str(shot_id):
                return dict(record)
    return {}


def _roles_for_count(count: int, shots: list[dict[str, Any]]) -> list[str]:
    if count <= 1:
        return ["initiate" if shots and CHANGE_RE.search(_shot_text(shots[0])) else "hold"]
    if count == 2:
        return ["initiate", "payoff"]
    if count == 3:
        return ["hold", "initiate", "payoff"]
    roles = ["hold"] + ["propagate"] * (count - 3) + ["payoff", "recover"]
    roles[1] = "initiate"
    return roles


def _motion_family(text: str, previous: str) -> tuple[str, list[str]]:
    candidates = []
    if LOCOMOTION_RE.search(text):
        candidates.append("body_weight_or_locomotion")
    if PROP_CONTACT_RE.search(text):
        candidates.append("prop_contact_or_hand_force")
    if EYELINE_RE.search(text):
        candidates.append("eyeline_head_body_phase")
    if ENVIRONMENT_RE.search(text):
        candidates.append("source_coupled_environment")
    if re.search(r"：|说|问|答|喊|低声|沉默", text):
        candidates.append("breath_voice_body_residue")
    candidates.append("stable_observation")
    family = next((item for item in candidates if item != previous), candidates[0])
    alternatives = [item for item in candidates if item != family][:2]
    return family, alternatives


def _driver_class(text: str) -> str:
    if LOCOMOTION_RE.search(text):
        return "source_body_displacement"
    if PROP_CONTACT_RE.search(text):
        return "source_prop_contact"
    if ENVIRONMENT_RE.search(text):
        return "source_environment_or_sound"
    if EYELINE_RE.search(text):
        return "source_eyeline_change"
    if re.search(r"：|说|问|答|喊|低声", text):
        return "source_dialogue_or_voice"
    return "deliberate_hold"


def _shot_text(shot: dict[str, Any]) -> str:
    parts = [str(shot.get("core_action", "") or "")]
    for subshot in shot.get("subshots", []) if isinstance(shot.get("subshots"), list) else []:
        if isinstance(subshot, dict):
            parts.append(str(subshot.get("base_action", "") or ""))
    return "；".join(part for part in parts if part)


def _characters(shot: dict[str, Any]) -> list[str]:
    result = []
    for subshot in shot.get("subshots", []) if isinstance(shot.get("subshots"), list) else []:
        if not isinstance(subshot, dict):
            continue
        for character in subshot.get("characters", []) or []:
            value = str(character).strip()
            if value and value not in result:
                result.append(value)
    return result


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)

