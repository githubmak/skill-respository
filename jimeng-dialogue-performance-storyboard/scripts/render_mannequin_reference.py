#!/usr/bin/env python3
"""Render model-authored mannequin blocking directly with PyVista/VTK.

The renderer is deliberately non-creative: it validates the blocking contract,
projects the supplied geometry, writes direct 1920x1080 images, and annotates
audit copies with Pillow. No browser, HTML, WebGL, or automatic camera solving
is involved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
import pyvista as pv
from PIL import Image, ImageDraw, ImageFont

from render_blocking_reference import validate_spec


HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
SHOT_ID_RE = re.compile(r"(?<![A-Za-z0-9])S\d+-\d+(?![A-Za-z0-9])")
POSTURES = {"standing", "sitting"}
PHYSICAL_PHASES = {"static", "start", "end"}
SCHEMA_VERSION = 5
FRAME_CONTRACT = {
    "width": 1920,
    "height": 1080,
    "aspect": "16:9",
    "capture_scope": "direct renderer output",
}
RENDER_BACKEND = "pyvista_vtk_offscreen"
RENDER_PROFILE = "proxy_v3_neutral"


def _finite_number(value, label: str, minimum: float, maximum: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}")
    return result


def _color(value, label: str) -> str:
    result = str(value or "").strip()
    if not HEX_COLOR_RE.fullmatch(result):
        raise ValueError(f"{label} must be a six-digit hex color such as #4F9F90")
    return result.lower()


def _raw_by_label(items: list[dict], key: str = "label") -> dict[str, dict]:
    return {str(item.get(key, "")).strip(): item for item in items if isinstance(item, dict)}


def _shot_id(raw_state: dict, label: str, state_index: int) -> str:
    explicit = str(raw_state.get("shot_id", "")).strip()
    if not SHOT_ID_RE.fullmatch(explicit):
        raise ValueError(f"states[{state_index}].shot_id must be explicit and match S<number>-<number>")
    label_match = SHOT_ID_RE.search(str(label or ""))
    if label_match and label_match.group(0) != explicit:
        raise ValueError(f"states[{state_index}].shot_id {explicit} conflicts with label shot {label_match.group(0)}")
    return explicit


def _physical_phase(raw_state: dict, state_index: int) -> str:
    phase = str(raw_state.get("physical_phase", "static")).strip().lower()
    if phase not in PHYSICAL_PHASES:
        raise ValueError(
            f"states[{state_index}].physical_phase must be static, start, or end"
        )
    return phase


def _image_stem(shot_group: str, shot_id: str, state_index: int, camera_index: int) -> str:
    # State and camera indexes remain in the report; the image name stays
    # readable when selected directly in Jimeng.
    return f"{shot_id}_即梦_3D_空间关系"


def _mannequin_character(raw: dict, normalized: dict, names: set[str], anchors: set[str]) -> dict:
    config = raw.get("mannequin")
    if not isinstance(config, dict):
        raise ValueError(f'{normalized["name"]}.mannequin is required for VTK rendering')
    posture = str(config.get("posture", "")).strip()
    if posture not in POSTURES:
        raise ValueError(f'{normalized["name"]}.mannequin.posture must be standing or sitting')
    gaze_target = str(config.get("gaze_target", "")).strip()
    if gaze_target and gaze_target not in names and gaze_target not in anchors:
        raise ValueError(f'{normalized["name"]}.mannequin.gaze_target must name a character or anchor')
    hand_targets = {}
    raw_targets = config.get("hand_targets", {})
    if not isinstance(raw_targets, dict):
        raise ValueError(f'{normalized["name"]}.mannequin.hand_targets must be an object')
    for hand in ("left", "right"):
        target = raw_targets.get(hand)
        if target is None:
            continue
        if not isinstance(target, dict):
            raise ValueError(f'{normalized["name"]}.{hand} hand target must be an object')
        anchor = str(target.get("anchor", "")).strip()
        character = str(target.get("character", "")).strip()
        if bool(anchor) == bool(character):
            raise ValueError(f'{normalized["name"]}.{hand} requires exactly one anchor or character target')
        if anchor and anchor not in anchors:
            raise ValueError(f'{normalized["name"]}.{hand} target anchor does not exist: {anchor}')
        if character and character not in names:
            raise ValueError(f'{normalized["name"]}.{hand} target character does not exist: {character}')
        hand_targets[hand] = {
            "anchor": anchor or None,
            "character": character or None,
            "height_m": _finite_number(target.get("height_m", 1.0), f'{normalized["name"]}.{hand}.height_m', 0.0, 3.0),
        }
    return {
        "name": normalized["name"], "x": normalized["x"], "z": normalized["y"],
        "body_facing_deg": normalized["facing_deg"],
        "head_facing_deg": _finite_number(config.get("head_facing_deg", normalized["facing_deg"]), f'{normalized["name"]}.mannequin.head_facing_deg', -720.0, 720.0) % 360.0,
        "height_m": _finite_number(config.get("height_m"), f'{normalized["name"]}.mannequin.height_m', 0.6, 2.4),
        "posture": posture, "identity_color": _color(config.get("identity_color"), f'{normalized["name"]}.mannequin.identity_color'),
        "gaze_target": gaze_target or None, "hand_targets": hand_targets,
    }


def _mannequin_anchor(raw: dict, normalized: dict) -> dict:
    config = raw.get("mannequin", {})
    if not isinstance(config, dict):
        raise ValueError(f'anchor {normalized["label"]}.mannequin must be an object')
    kind = str(config.get("kind", "box")).strip()
    if kind not in {"box", "table", "bench", "bowl", "door", "marker"}:
        raise ValueError(f'anchor {normalized["label"]}.mannequin.kind is unsupported: {kind}')
    return {
        "label": normalized["label"], "kind": kind, "x": normalized["x"], "z": normalized["y"],
        "width": normalized["width"], "depth": normalized["height"], "solid": normalized["solid"],
        "height_m": _finite_number(config.get("height_m", 0.12), f'anchor {normalized["label"]}.height_m', 0.01, 5.0),
        "elevation_m": _finite_number(config.get("elevation_m", 0.0), f'anchor {normalized["label"]}.elevation_m', 0.0, 4.0),
        "rotation_deg": _finite_number(config.get("rotation_deg", 0.0), f'anchor {normalized["label"]}.rotation_deg', -720.0, 720.0) % 360.0,
        "color": _color(config.get("color", "#795438"), f'anchor {normalized["label"]}.color'),
    }


def _mannequin_camera(raw: dict, normalized: dict) -> dict:
    config = raw.get("mannequin", {})
    if not isinstance(config, dict):
        raise ValueError(f'camera {normalized["label"]}.mannequin must be an object')
    return {
        "label": normalized["label"], "x": normalized["x"], "z": normalized["y"],
        "facing_deg": normalized["facing_deg"], "fov_deg": normalized["fov_deg"],
        "subjects": list(normalized["subjects"]), "shot_type": normalized["shot_type"],
        "foreground_character": normalized["foreground_character"], "target_character": normalized["target_character"],
        "axis_side": normalized["axis_side"], "facing_mode": normalized["facing_mode"], "path": normalized["path"],
        "height_m": _finite_number(config.get("height_m", 1.55), f'camera {normalized["label"]}.height_m', 0.2, 5.0),
        "look_height_m": _finite_number(config.get("look_height_m", 1.35), f'camera {normalized["label"]}.look_height_m', 0.0, 4.0),
    }


def _hash_payload(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def compile_states(spec: dict) -> dict:
    normalized = validate_spec(spec)
    scene_config = spec.get("mannequin", {})
    if not isinstance(scene_config, dict):
        raise ValueError("top-level mannequin must be an object")
    scene = {
        "name": normalized["scene"],
        "world_width_m": _finite_number(scene_config.get("world_width_m", 10.0), "mannequin.world_width_m", 3.0, 40.0),
        "world_depth_m": _finite_number(scene_config.get("world_depth_m", 8.0), "mannequin.world_depth_m", 3.0, 40.0),
        "floor_color": _color(scene_config.get("floor_color", "#26333b"), "mannequin.floor_color"),
        "background_color": _color(scene_config.get("background_color", "#0d151d"), "mannequin.background_color"),
    }
    raw_geometry_by_blocking: dict[str, dict] = {}
    grouped: dict[str, dict] = {}
    shot_phases: dict[str, dict[str, dict]] = {}
    for index, (raw_state, state) in enumerate(zip(spec["states"], normalized["states"]), start=1):
        blocking_id = state["blocking_id"]
        if not raw_state.get("reuse_blocking"):
            raw_geometry_by_blocking[blocking_id] = raw_state
        geometry_raw = raw_geometry_by_blocking.get(blocking_id)
        if geometry_raw is None:
            raise ValueError(f"state {index} has no source geometry for blocking_id {blocking_id}")
        raw_characters = _raw_by_label(geometry_raw.get("characters", []), "name")
        raw_anchors = _raw_by_label(geometry_raw.get("anchors", []))
        names = {item["name"] for item in state["characters"]}
        anchor_names = {item["label"] for item in state["anchors"]}
        characters = [_mannequin_character(raw_characters.get(item["name"], {}), item, names, anchor_names) for item in state["characters"]]
        anchors = [_mannequin_anchor(raw_anchors.get(item["label"], {}), item) for item in state["anchors"]]
        physical = {"schema_version": SCHEMA_VERSION, "scene": scene, "characters": characters, "anchors": anchors, "boundaries": state["boundaries"]}
        _validate_hand_reach(physical, scene)
        physical_hash = _hash_payload(physical)
        camera = _mannequin_camera(raw_state["cameras"][0], state["cameras"][0])
        label = state["label"]
        state_shot_id = _shot_id(raw_state, label, index)
        physical_phase = _physical_phase(raw_state, index)
        if physical_phase != "static" and camera.get("path"):
            raise ValueError(
                f"states[{index}] cannot combine physical_phase={physical_phase} with camera path; "
                "put the start camera in the start state and the end camera in the end state"
            )
        phase_records = shot_phases.setdefault(state_shot_id, {})
        if physical_phase in phase_records:
            raise ValueError(
                f"shot {state_shot_id} has duplicate physical_phase={physical_phase}"
            )
        phase_records[physical_phase] = {
            "state_index": index,
            "physical_hash": physical_hash,
        }
        view_hash = _hash_payload(camera)
        group = grouped.setdefault(physical_hash, {"physical_hash": physical_hash, "blocking_ids": [], "labels": [], "shot_ids": [], "view_sources": {}, "payload": physical, "views": [], "view_hashes": set()})
        if blocking_id not in group["blocking_ids"]: group["blocking_ids"].append(blocking_id)
        group["labels"].append(label)
        if state_shot_id not in group["shot_ids"]: group["shot_ids"].append(state_shot_id)
        group["view_sources"].setdefault(view_hash, []).append({
            "shot_id": state_shot_id,
            "label": label,
            "physical_phase": physical_phase,
        })
        if view_hash not in group["view_hashes"]:
            group["view_hashes"].add(view_hash)
            group["views"].append({"view_hash": view_hash, **camera})
    for shot_id, phases in shot_phases.items():
        phase_names = set(phases)
        if "static" in phase_names:
            if phase_names != {"static"}:
                raise ValueError(
                    f"shot {shot_id} cannot mix physical_phase=static with start/end"
                )
            continue
        if phase_names != {"start", "end"}:
            missing = "end" if "start" in phase_names else "start"
            raise ValueError(f"shot {shot_id} physical transition is missing {missing} state")
        if phases["start"]["state_index"] > phases["end"]["state_index"]:
            raise ValueError(f"shot {shot_id} start state must appear before end state")
        if phases["start"]["physical_hash"] == phases["end"]["physical_hash"]:
            raise ValueError(f"shot {shot_id} start and end physical states are identical")
    results = []
    for group in grouped.values():
        group["view_hashes"] = sorted(group["view_hashes"])
        for view in group["views"]:
            sources = group["view_sources"].get(view["view_hash"], [])
            view["source_shots"] = list(dict.fromkeys(item["shot_id"] for item in sources))
            view["source_labels"] = [item["label"] for item in sources]
            view["sources"] = sources
            view["physical_phases"] = list(dict.fromkeys(
                item["physical_phase"] for item in sources
            ))
        group["payload"]["views"] = group["views"]
        results.append(group)
    return {"schema_version": SCHEMA_VERSION, "shot_group": normalized["shot_group"], "scene": scene, "source_state_count": len(normalized["states"]), "physical_state_count": len(results), "view_count": sum(len(item["views"]) for item in results), "groups": results}


def output_directory(storyboard: str | None, output_dir: str | None) -> Path:
    if storyboard:
        return Path(storyboard).expanduser().resolve().parent / "staging" / "mannequin"
    if output_dir:
        directory = Path(output_dir).expanduser().resolve()
        if "staging" not in directory.parts:
            raise ValueError("--output-dir must be inside a staging directory")
        return directory
    raise ValueError("either --storyboard or --output-dir is required")


def _world(scene: dict, x: float, y: float, height: float = 0.0) -> tuple[float, float, float]:
    return ((x - 0.5) * scene["world_width_m"], (0.5 - y) * scene["world_depth_m"], height)


def _validate_hand_reach(payload: dict, scene: dict) -> None:
    """Reject contacts that would require stretching a limb beyond human reach."""
    for character in payload["characters"]:
        h = character["height_m"]
        base_z = 0.03 if character["posture"] == "standing" else 0.48
        pos = np.asarray(_world(scene, character["x"], character["z"], base_z), dtype=float)
        facing = math.radians(character["body_facing_deg"])
        forward = np.array([math.cos(facing), -math.sin(facing), 0.0])
        lateral = np.array([-forward[1], forward[0], 0.0])
        shoulder_z = base_z + h * 0.18 + h * 0.38
        shoulders = np.array([pos[0], pos[1], shoulder_z - h * 0.015])
        max_reach = h * 0.45 + 0.03
        for hand, target in character["hand_targets"].items():
            hand_side = 1 if hand == "left" else -1
            shoulder = shoulders + lateral * hand_side * h * 0.13
            end = np.asarray(_target_point(payload, character, target, scene), dtype=float)
            required = float(np.linalg.norm(end - shoulder))
            if required > max_reach:
                raise ValueError(
                    f'{character["name"]}.{hand} hand target is unreachable: '
                    f'{required:.2f}m from shoulder exceeds {max_reach:.2f}m arm reach'
                )


def _hex_rgb(color: str) -> tuple[float, float, float]:
    value = color.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _shade(color: str, factor: float) -> str:
    """Derive a stable secondary material color without changing identity color."""
    rgb = [max(0, min(255, round(channel * factor))) for channel in (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))]
    return "#%02x%02x%02x" % tuple(rgb)


def _head_marker(head, head_facing_deg: float, height_m: float) -> tuple[np.ndarray, np.ndarray]:
    radians = math.radians(head_facing_deg)
    direction = np.array([math.cos(radians), -math.sin(radians), 0.0])
    return np.asarray(head, dtype=float) + direction * height_m * 0.16, direction


def _add_surface(plotter, mesh, color: str, opacity: float = 1.0, *, roughness: float = 0.72, metallic: float = 0.04, smooth: bool = True):
    """Use a neutral engineering material that does not imply finished-look lighting."""
    return plotter.add_mesh(
        mesh, color=color, opacity=opacity, smooth_shading=smooth,
        pbr=False, ambient=0.58, diffuse=0.42, specular=0.0,
    )


def _add_cylinder(plotter, a, b, radius, color, resolution=12):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    vector = b - a
    length = float(np.linalg.norm(vector))
    if length < 1e-5: return
    mesh = pv.Cylinder(center=(a + b) / 2, direction=vector, radius=radius, height=length, resolution=resolution)
    _add_surface(plotter, mesh, color, roughness=0.78, metallic=0.02)


def _target_point(payload: dict, character: dict, target: dict, scene: dict) -> tuple[float, float, float]:
    if target.get("character"):
        other = next(item for item in payload["characters"] if item["name"] == target["character"])
        return _world(scene, other["x"], other["z"], target["height_m"])
    anchor = next(item for item in payload["anchors"] if item["label"] == target["anchor"])
    return _world(scene, anchor["x"], anchor["z"], target["height_m"])


def _solve_elbow(shoulder: np.ndarray, hand: np.ndarray, preferred_bend: np.ndarray, upper: float, lower: float) -> np.ndarray:
    """Solve one stable two-bone arm without inventing an extra forearm."""
    vector = hand - shoulder
    distance = float(np.linalg.norm(vector))
    if distance < 1e-6:
        raise ValueError("hand target cannot occupy the shoulder point")
    direction = vector / distance
    along = (upper * upper - lower * lower + distance * distance) / (2.0 * distance)
    along = max(-upper, min(upper, along))
    bend = preferred_bend - direction * float(np.dot(preferred_bend, direction))
    bend_length = float(np.linalg.norm(bend))
    if bend_length < 1e-6:
        bend = np.cross(direction, np.array([0.0, 0.0, 1.0]))
        bend_length = float(np.linalg.norm(bend))
    bend = bend / max(bend_length, 1e-6)
    perpendicular = math.sqrt(max(0.0, upper * upper - along * along))
    return shoulder + direction * along + bend * perpendicular


def _build_scene(plotter: pv.Plotter, payload: dict, mode: str, scene: dict, camera_state: dict) -> None:
    plotter.set_background("#d9dde1" if mode == "clean" else "#263038")
    plotter.add_light(pv.Light(position=(-5.0, -6.0, 7.0), focal_point=(0.0, 0.0, 1.0), color="#ffffff", intensity=0.9, positional=True))
    plotter.add_light(pv.Light(position=(5.0, 2.0, 4.0), focal_point=(0.0, 0.0, 1.0), color="#ffffff", intensity=0.45, positional=True))
    width, depth = scene["world_width_m"], scene["world_depth_m"]
    _add_surface(plotter, pv.Box(bounds=(-width / 2, width / 2, -depth / 2, depth / 2, -0.08, 0)), "#b8bdc3", smooth=False)
    for anchor in payload["anchors"]:
        center = _world(scene, anchor["x"], anchor["z"], anchor["elevation_m"] + anchor["height_m"] / 2)
        w, d, h = anchor["width"] * width, anchor["depth"] * depth, anchor["height_m"]
        if anchor["kind"] == "bowl":
            mesh = pv.Cylinder(center=center, direction=(0, 0, 1), radius=max(w, d) / 2, height=h, resolution=24)
        elif anchor["kind"] == "marker":
            mesh = pv.Sphere(radius=max(w, d) / 2, center=center)
        else:
            mesh = pv.Box(bounds=(center[0] - w / 2, center[0] + w / 2, center[1] - d / 2, center[1] + d / 2, center[2] - h / 2, center[2] + h / 2))
        anchor_color = anchor["color"] if mode == "audit" else "#8c9298"
        _add_surface(plotter, mesh, anchor_color, opacity=0.88 if anchor["solid"] else 0.35)
        if mode == "audit":
            plotter.add_point_labels(np.array([center]), [anchor["label"]], font_size=12, text_color="white", point_size=0, shape=None)
    for boundary in payload["boundaries"]:
        a = _world(scene, boundary["x1"], boundary["y1"], 1.4); b = _world(scene, boundary["x2"], boundary["y2"], 1.4)
        _add_cylinder(plotter, a, b, 0.035, "#88715b", 8)
    by_name = {item["name"]: item for item in payload["characters"]}
    for character in payload["characters"]:
        h = character["height_m"]
        base_z = 0.03 if character["posture"] == "standing" else 0.48
        pos = _world(scene, character["x"], character["z"], base_z)
        color = character["identity_color"]
        facing = math.radians(character["body_facing_deg"])
        forward = (math.cos(facing), -math.sin(facing), 0)
        lateral = np.array([-forward[1], forward[0], 0.0])
        secondary = _shade(color, 0.68)
        torso_h = h * 0.38
        hip_z = base_z + h * 0.18
        shoulder_z = hip_z + torso_h
        torso_center = (pos[0], pos[1], hip_z + torso_h / 2)
        _add_surface(plotter, pv.Capsule(center=torso_center, direction=(0, 0, 1), radius=h * 0.145, cylinder_length=torso_h * 0.64, resolution=18), color, roughness=0.66)
        _add_surface(plotter, pv.Cylinder(center=(pos[0], pos[1], hip_z), direction=(0, 0, 1), radius=h * 0.16, height=h * 0.10, resolution=16), secondary, roughness=0.76)
        neck = (pos[0], pos[1], shoulder_z + h * 0.055)
        _add_surface(plotter, pv.Cylinder(center=neck, direction=(0, 0, 1), radius=h * 0.065, height=h * 0.11, resolution=14), secondary, roughness=0.70)
        head = (pos[0], pos[1], shoulder_z + h * 0.22)
        _add_surface(plotter, pv.Sphere(center=head, radius=h * 0.135, theta_resolution=20, phi_resolution=14), color, roughness=0.56)
        face_tip, head_forward = _head_marker(head, character["head_facing_deg"], h)
        if mode == "audit":
            _add_surface(plotter, pv.Cone(center=face_tip, direction=head_forward, height=h * 0.12, radius=h * 0.065, resolution=8), secondary)
        if character["posture"] == "standing":
            for side in (-1, 1):
                hip = np.array([pos[0], pos[1], hip_z]) + lateral * side * h * 0.075
                knee = hip + np.array([0.0, 0.0, -h * 0.16]) + lateral * side * h * 0.018
                foot = knee + np.array([0.0, 0.0, -h * 0.16]) + np.array(forward) * h * 0.035
                _add_cylinder(plotter, hip, knee, h * 0.055, secondary, 12)
                _add_cylinder(plotter, knee, foot, h * 0.05, color, 12)
                _add_surface(plotter, pv.Sphere(center=knee, radius=h * 0.062, theta_resolution=12, phi_resolution=8), secondary, roughness=0.72)
        else:
            for side in (-1, 1):
                hip = np.array([pos[0], pos[1], hip_z]) + lateral * side * h * 0.075
                knee = hip + np.array(forward) * h * 0.22 + np.array([0.0, 0.0, -h * 0.02])
                foot = knee + np.array([0.0, 0.0, -h * 0.18]) + np.array(forward) * h * 0.06
                _add_cylinder(plotter, hip, knee, h * 0.06, secondary, 12)
                _add_cylinder(plotter, knee, foot, h * 0.05, color, 12)
                _add_surface(plotter, pv.Sphere(center=knee, radius=h * 0.065, theta_resolution=12, phi_resolution=8), secondary, roughness=0.72)
        shoulders = np.array([pos[0], pos[1], shoulder_z - h * 0.015])
        for side in (-1, 1):
            hand = "left" if side == 1 else "right"
            shoulder = shoulders + lateral * side * h * 0.13
            target = character["hand_targets"].get(hand)
            if target:
                wrist = np.array(_target_point(payload, character, target, scene))
                elbow = _solve_elbow(
                    shoulder, wrist, lateral * side + np.array([0.0, 0.0, -0.35]),
                    h * 0.19, h * 0.26 + 0.03,
                )
            else:
                elbow = shoulder + np.array(forward) * h * 0.06 + np.array([0.0, 0.0, -h * 0.13]) + lateral * side * h * 0.035
                wrist = elbow + np.array(forward) * h * 0.06 + np.array([0.0, 0.0, -h * 0.11]) + lateral * side * h * 0.02
            _add_cylinder(plotter, shoulder, elbow, h * 0.038, color, 12)
            _add_surface(plotter, pv.Sphere(center=elbow, radius=h * 0.045, theta_resolution=12, phi_resolution=8), secondary, roughness=0.70)
            _add_cylinder(plotter, elbow, wrist, h * 0.034, secondary, 12)
            _add_surface(plotter, pv.Sphere(center=wrist, radius=h * 0.04, theta_resolution=12, phi_resolution=8), color, roughness=0.62)
        if mode == "audit":
            plotter.add_point_labels(np.array([head]), [character["name"]], font_size=14, text_color="white", point_size=0, shape=None)
            if character["gaze_target"]:
                target = character["gaze_target"]
                if target in by_name:
                    other = by_name[target]; gaze_end = _world(scene, other["x"], other["z"], other["height_m"] * 0.76)
                else:
                    anchor = next(item for item in payload["anchors"] if item["label"] == target); gaze_end = _world(scene, anchor["x"], anchor["z"], anchor["elevation_m"] + anchor["height_m"])
                _add_cylinder(plotter, head, gaze_end, 0.012, "#f4d35e", 6)


def _camera_pose(scene: dict, camera: dict, pose: str) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    x, y, facing, height = camera["x"], camera["z"], camera["facing_deg"], camera["height_m"]
    if pose == "end" and camera.get("path"):
        path = camera["path"]; x, y, facing = path["end_x"], path["end_y"], path["end_facing_deg"]
    pos = _world(scene, x, y, height)
    rad = math.radians(facing)
    direction = (math.cos(rad), -math.sin(rad), 0.0)
    look = (pos[0] + direction[0] * 10.0, pos[1] + direction[1] * 10.0, camera["look_height_m"])
    return pos, look


def _font(size: int):
    for path in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Light.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _audit_overlay(
    image_path: Path,
    payload: dict,
    camera: dict,
    physical_hash: str,
    pose: str,
    physical_phase: str,
    pose_source: str,
) -> None:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((20, 20, 700, 208), fill=(5, 12, 18, 205), outline=(120, 160, 180, 255), width=2)
    title = f"VTK AUDIT  {camera['label']}  {pose}  {pose_source}"
    draw.text((38, 34), title, fill=(240, 246, 248), font=_font(26))
    draw.text((38, 72), f"physical_state {physical_hash[:12]}  |  1920x1080 16:9", fill=(190, 211, 220), font=_font(18))
    draw.text((38, 96), f"physical phase {physical_phase}  |  camera ({camera['x']:.3f},{camera['z']:.3f})  facing {camera['facing_deg']:.0f}°  FOV {camera['fov_deg']:.0f}°", fill=(190, 211, 220), font=_font(17))
    y = 124
    for char in payload["characters"]:
        draw.ellipse((40, y + 3, 55, y + 18), fill=char["identity_color"])
        draw.text((66, y), f"{char['name']}  {char['posture']}  facing {char['body_facing_deg']:.0f}°", fill=(230, 238, 241), font=_font(17))
        y += 23
    image.save(image_path, quality=94, subsampling=0)


def _apply_camera(plotter: pv.Plotter, scene: dict, camera: dict, pose: str) -> None:
    camera_position, look = _camera_pose(scene, camera, pose)
    plotter.camera.position = camera_position
    plotter.camera.focal_point = look
    plotter.camera.up = (0, 0, 1)
    plotter.camera.view_angle = camera["fov_deg"]


def _render_tasks(payload: dict, scene: dict, mode: str, tasks: list[dict], physical_hash: str) -> None:
    if not tasks:
        return
    plotter = pv.Plotter(off_screen=True, window_size=(FRAME_CONTRACT["width"], FRAME_CONTRACT["height"]))
    _build_scene(plotter, payload, mode, scene, tasks[0]["camera"])
    _apply_camera(plotter, scene, tasks[0]["camera"], tasks[0]["pose"])
    plotter.show(auto_close=False, interactive=False)
    try:
        for task in tasks:
            _apply_camera(plotter, scene, task["camera"], task["pose"])
            plotter.render()
            plotter.screenshot(str(task["output_path"]))
            if mode == "audit":
                _audit_overlay(
                    task["output_path"], payload, task["camera"], physical_hash,
                    task["pose"], task["physical_phase"], task["pose_source"],
                )
    finally:
        plotter.close()


def renderer_versions() -> dict:
    return {"vtk": pv.vtk_version_info if hasattr(pv, "vtk_version_info") else "unknown", "pyvista": pv.__version__, "pillow": __import__("PIL").__version__}


def render_scenes(compiled: dict, directory: Path, replace: bool = False) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    outputs = []
    for state_index, group in enumerate(compiled["groups"]):
        view_records = []
        tasks_by_mode = {"audit": [], "clean": []}
        reuse_links: list[tuple[Path, Path]] = []
        for camera_index, view in enumerate(group["views"]):
            image_names, screenshots = [], []
            sources = view.get("sources", [])
            if not sources:
                raise ValueError(f'camera {view["label"]} has no source state mapping')
            if view.get("path"):
                if any(item["physical_phase"] != "static" for item in sources):
                    raise ValueError(
                        f'camera {view["label"]} path cannot be combined with physical start/end states'
                    )
                pose_batches = [
                    ("start", "camera_path", sources),
                    ("end", "camera_path", sources),
                ]
            else:
                pose_batches = []
                for phase in ("static", "start", "end"):
                    phase_sources = [
                        item for item in sources if item["physical_phase"] == phase
                    ]
                    if phase_sources:
                        pose = phase if phase in {"start", "end"} else "static"
                        pose_source = "physical_state" if phase != "static" else "static"
                        pose_batches.append((pose, pose_source, phase_sources))
            for pose, pose_source, pose_sources in pose_batches:
                pose_label = pose if pose in {"start", "end"} else ""
                primary_paths = {}
                for source_index, source in enumerate(pose_sources):
                    shot_id = source["shot_id"]
                    physical_phase = source["physical_phase"]
                    stem = _image_stem(compiled["shot_group"], shot_id, state_index, camera_index)
                    for mode in ("audit", "clean"):
                        mode_label = "_审核" if mode == "audit" else ""
                        pose_suffix = f"_{pose_label}" if pose_label else ""
                        filename = f"{stem}{pose_suffix}{mode_label}.jpg"
                        image_names.append(filename)
                        record = {
                            "shot_id": shot_id,
                            "physical_state_index": state_index,
                            "physical_phase": physical_phase,
                            "camera_index": camera_index,
                            "pose": pose,
                            "pose_source": pose_source,
                            "mode": mode,
                            "filename": filename,
                            "render_backend": RENDER_BACKEND,
                        }
                        screenshots.append(record)
                        output_path = directory / filename
                        if output_path.exists():
                            if not replace:
                                raise FileExistsError(f"destination exists; use --replace: {output_path}")
                            output_path.unlink()
                        if source_index == 0:
                            primary_paths[mode] = output_path
                            tasks_by_mode[mode].append({
                                "camera": view,
                                "pose": pose,
                                "physical_phase": physical_phase,
                                "pose_source": pose_source,
                                "output_path": output_path,
                            })
                        else:
                            record["render_reused_from"] = primary_paths[mode].name
                            reuse_links.append((output_path, primary_paths[mode]))
            view_records.append({
                "camera_index": camera_index,
                "physical_state_index": state_index,
                "physical_phases": view["physical_phases"],
                "view_hash": view["view_hash"],
                "camera_contract": {key: view[key] for key in (
                    "view_hash", "label", "x", "z", "facing_deg", "fov_deg",
                    "subjects", "shot_type", "foreground_character",
                    "target_character", "axis_side", "facing_mode", "path",
                    "height_m", "look_height_m",
                )},
                "source_shots": view["source_shots"],
                "source_labels": view["source_labels"],
                "suggested_image_names": image_names,
                "screenshots": screenshots,
            })
        for mode in ("audit", "clean"):
            _render_tasks(group["payload"], compiled["scene"], mode, tasks_by_mode[mode], group["physical_hash"])
        for destination, source in reuse_links:
            destination.hardlink_to(source)
        outputs.append({"physical_hash": group["physical_hash"], "blocking_ids": group["blocking_ids"], "labels": group["labels"], "view_count": len(group["views"]), "views": view_records, "render_backend": RENDER_BACKEND, "screenshots_required": ["audit", "clean"]})
    return {"pass": True, "schema_version": SCHEMA_VERSION, "render_backend": RENDER_BACKEND, "render_profile": RENDER_PROFILE, "renderer_versions": renderer_versions(), "frame_contract": FRAME_CONTRACT, "scene_reuse": "one plotter per physical state and mode; camera views reuse geometry", "shot_render_reuse": "identical physical-state/camera/pose images use hard links", "shot_group": compiled["shot_group"], "source_state_count": compiled["source_state_count"], "physical_state_count": compiled["physical_state_count"], "view_count": compiled["view_count"], "deduplicated_state_count": compiled["source_state_count"] - compiled["physical_state_count"], "outputs": outputs, "staging_only": True, "primary_storyboard_modified": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec")
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--storyboard")
    destination.add_argument("--output-dir")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    if not args.compact:
        parser.error("--compact is required")
    try:
        spec = json.loads(Path(args.spec).expanduser().resolve().read_text(encoding="utf-8"))
        compiled = compile_states(spec)
        result = render_scenes(compiled, output_directory(args.storyboard, args.output_dir), args.replace)
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        result = {"pass": False, "error": str(exc), "primary_storyboard_modified": False, "render_backend": RENDER_BACKEND}
    report = Path(args.report).expanduser().resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS" if result.get("pass") else "FAIL", "shot_group": result.get("shot_group"), "render_backend": result.get("render_backend"), "screenshot_count": sum(len(v.get("screenshots", [])) for o in result.get("outputs", []) for v in o.get("views", [])), "report": str(report)}, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
