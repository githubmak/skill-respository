#!/usr/bin/env python3
"""Render deterministic multi-character blocking/facing sheets as SVG."""

from __future__ import annotations

import argparse
import copy
import html
import json
import math
import re
import shutil
import subprocess
from pathlib import Path


SHOT_GROUP_RE = re.compile(r"^S\d+-\d+$")
PALETTE = ("#2563eb", "#d97706", "#dc2626", "#059669", "#7c3aed", "#475569")
SHOT_TYPES = ("relationship", "over_shoulder")
AXIS_SIDES = ("positive", "negative")


def _number(value, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not 0.0 <= result <= 1.0:
        raise ValueError(f"{label} must be between 0 and 1")
    return result


def _angle(value, label: str) -> float:
    try:
        return float(value) % 360.0
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric degrees") from exc


def _fov(value, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric degrees") from exc
    if not 10.0 <= result <= 120.0:
        raise ValueError(f"{label} must be between 10 and 120 degrees")
    return result


def _boolean(value, label: str, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ValueError(f"{label} must be boolean")


def _character_by_name(characters: list[dict], name: str, label: str) -> dict:
    character = next((item for item in characters if item["name"] == name), None)
    if character is None:
        raise ValueError(f"{label} must name a character in this state")
    return character


def _axis_side_value(point: tuple[float, float], characters: list[dict]) -> float:
    first, second = characters[:2]
    axis_x = second["x"] - first["x"]
    axis_y = second["y"] - first["y"]
    return axis_x * (point[1] - first["y"]) - axis_y * (point[0] - first["x"])


def _solve_over_shoulder_camera(camera: dict, characters: list[dict]) -> tuple[float, float, float]:
    foreground = _character_by_name(characters, str(camera.get("foreground_character", "")).strip(), "foreground_character")
    target = _character_by_name(characters, str(camera.get("target_character", "")).strip(), "target_character")
    dx, dy = target["x"] - foreground["x"], target["y"] - foreground["y"]
    distance = math.hypot(dx, dy)
    if distance < 0.12:
        raise ValueError("over-shoulder characters are too close for a stable camera")
    ux, uy = dx / distance, dy / distance
    desired_side = str(camera.get("axis_side", "positive"))
    if desired_side not in AXIS_SIDES:
        raise ValueError("axis_side must be positive or negative")
    side_sign = 1.0 if desired_side == "positive" else -1.0
    canonical_dx = characters[1]["x"] - characters[0]["x"]
    canonical_dy = characters[1]["y"] - characters[0]["y"]
    canonical_length = math.hypot(canonical_dx, canonical_dy) or 1.0
    side_x = -canonical_dy / canonical_length * side_sign
    side_y = canonical_dx / canonical_length * side_sign
    back_distance = distance * float(camera.get("back_ratio", 0.30))
    lateral_distance = distance * float(camera.get("lateral_ratio", 0.14))
    x = foreground["x"] - ux * back_distance + side_x * lateral_distance
    y = foreground["y"] - uy * back_distance + side_y * lateral_distance
    if not 0.0 <= x <= 1.0 or not 0.0 <= y <= 1.0:
        raise ValueError("auto over-shoulder camera falls outside the scene; change axis_side or blocking")
    facing = math.degrees(math.atan2(target["y"] - y, target["x"] - x)) % 360.0
    return x, y, facing


def _angle_delta(left: float, right: float) -> float:
    return abs((left - right + 180.0) % 360.0 - 180.0)


def _point_segment_distance(point, start, end) -> float:
    px, py = point
    x1, y1 = start
    x2, y2 = end
    dx, dy = x2 - x1, y2 - y1
    denominator = dx * dx + dy * dy
    if denominator <= 1e-12:
        return math.hypot(px - x1, py - y1)
    ratio = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / denominator))
    return math.hypot(px - (x1 + ratio * dx), py - (y1 + ratio * dy))


def _segment_crossing(first_start, first_end, second_start, second_end):
    px, py = first_start
    rx, ry = first_end[0] - px, first_end[1] - py
    qx, qy = second_start
    sx, sy = second_end[0] - qx, second_end[1] - qy
    denominator = rx * sy - ry * sx
    if abs(denominator) <= 1e-12:
        return None
    qpx, qpy = qx - px, qy - py
    t = (qpx * sy - qpy * sx) / denominator
    u = (qpx * ry - qpy * rx) / denominator
    return (t, u) if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0 else None


def _point_inside_anchor(point, anchor: dict, margin: float = 0.0) -> bool:
    px, py = point
    half_w = anchor["width"] / 2 + margin
    half_h = anchor["height"] / 2 + margin
    if anchor["shape"] == "ellipse":
        if half_w <= 0.0 or half_h <= 0.0:
            return False
        return ((px - anchor["x"]) / half_w) ** 2 + ((py - anchor["y"]) / half_h) ** 2 <= 1.0
    if anchor["shape"] == "line":
        start = (anchor["x"] - anchor["width"] / 2, anchor["y"])
        end = (anchor["x"] + anchor["width"] / 2, anchor["y"])
        return _point_segment_distance(point, start, end) <= max(margin, anchor["height"] / 2)
    return abs(px - anchor["x"]) <= half_w and abs(py - anchor["y"]) <= half_h


def _segment_hits_anchor(start, end, anchor: dict, margin: float = 0.012) -> bool:
    steps = max(24, int(math.hypot(end[0] - start[0], end[1] - start[1]) * 180))
    for index in range(1, steps):
        ratio = index / steps
        point = (start[0] + (end[0] - start[0]) * ratio, start[1] + (end[1] - start[1]) * ratio)
        if _point_inside_anchor(point, anchor, margin):
            return True
    return False


def _validate_over_shoulder(camera: dict, characters: list[dict]) -> None:
    foreground = _character_by_name(characters, camera["foreground_character"], "foreground_character")
    target = _character_by_name(characters, camera["target_character"], "target_character")
    foreground_point = (foreground["x"], foreground["y"])
    target_point = (target["x"], target["y"])
    camera_point = (camera["x"], camera["y"])
    relation_distance = math.hypot(target["x"] - foreground["x"], target["y"] - foreground["y"])
    camera_distance = math.hypot(camera["x"] - foreground["x"], camera["y"] - foreground["y"])
    ratio = camera_distance / relation_distance
    if not 0.18 <= ratio <= 0.52:
        raise ValueError(f'{camera["label"]} over-shoulder distance ratio must be 0.18-0.52, got {ratio:.2f}')
    to_target = (target["x"] - foreground["x"], target["y"] - foreground["y"])
    to_camera = (camera["x"] - foreground["x"], camera["y"] - foreground["y"])
    if to_target[0] * to_camera[0] + to_target[1] * to_camera[1] >= 0.0:
        raise ValueError(f'{camera["label"]} must stay behind foreground character {foreground["name"]}')
    actual_side = _axis_side_value(camera_point, characters)
    expected_positive = camera["axis_side"] == "positive"
    if abs(actual_side) <= 1e-4 or (actual_side > 0) != expected_positive:
        raise ValueError(f'{camera["label"]} is on the wrong relationship-axis side')
    shoulder_distance = _point_segment_distance(foreground_point, camera_point, target_point)
    if not 0.016 <= shoulder_distance <= 0.065:
        raise ValueError(
            f'{camera["label"]} foreground shoulder must graze view line without covering target; '
            f'offset {shoulder_distance:.3f}'
        )
    if camera["target_character"] not in camera["subjects"]:
        raise ValueError(f'{camera["label"]} target_character must be listed in subjects')
    for actor, other in ((foreground, target), (target, foreground)):
        desired = math.degrees(math.atan2(other["y"] - actor["y"], other["x"] - actor["x"])) % 360.0
        if _angle_delta(actor["facing_deg"], desired) > 55.0:
            raise ValueError(f'{actor["name"]} must physically face {other["name"]} for this dialogue reverse shot')


def _validate_state_geometry(state: dict) -> None:
    characters = state["characters"]
    camera = state["cameras"][0]
    camera_point = (camera["x"], camera["y"])
    for character in characters:
        distance = math.hypot(camera["x"] - character["x"], camera["y"] - character["y"])
        if distance < 0.045:
            raise ValueError(f'{camera["label"]} has no standing clearance from {character["name"]}')
    for anchor in state["anchors"]:
        if not anchor["solid"]:
            continue
        if _point_inside_anchor(camera_point, anchor, 0.018):
            raise ValueError(f'{camera["label"]} overlaps solid anchor {anchor["label"]}')
        for character in characters:
            if _point_inside_anchor((character["x"], character["y"]), anchor, 0.022):
                raise ValueError(f'{character["name"]} overlaps solid anchor {anchor["label"]}')
    if camera["shot_type"] == "over_shoulder":
        _validate_over_shoulder(camera, characters)
    by_name = {character["name"]: character for character in characters}
    for subject_name in camera["subjects"]:
        subject = by_name[subject_name]
        subject_point = (subject["x"], subject["y"])
        for anchor in state["anchors"]:
            if anchor["solid"] and _segment_hits_anchor(camera_point, subject_point, anchor):
                raise ValueError(f'{camera["label"]} view to {subject_name} is blocked by {anchor["label"]}')
        for boundary in state["boundaries"]:
            if not boundary["blocks_view"]:
                continue
            crossing = _segment_crossing(
                camera_point,
                subject_point,
                (boundary["x1"], boundary["y1"]),
                (boundary["x2"], boundary["y2"]),
            )
            if crossing is None:
                continue
            _, boundary_ratio = crossing
            if not any(opening["start"] <= boundary_ratio <= opening["end"] for opening in boundary["openings"]):
                raise ValueError(f'{camera["label"]} view to {subject_name} is blocked by {boundary["label"]}')


def validate_spec(spec: dict) -> dict:
    group = str(spec.get("shot_group", "")).strip()
    if not SHOT_GROUP_RE.fullmatch(group):
        raise ValueError("shot_group must match S1-01")
    states = spec.get("states")
    if not isinstance(states, list) or not states:
        raise ValueError("states must contain at least one stable blocking state")
    normalized_states = []
    for state_index, state in enumerate(states, start=1):
        if not isinstance(state, dict):
            raise ValueError(f"states[{state_index}] must be an object")
        blocking_id = str(state.get("blocking_id", "")).strip()
        if not blocking_id:
            raise ValueError(f"states[{state_index}].blocking_id is required")
        reuse_blocking = _boolean(state.get("reuse_blocking"), f"states[{state_index}].reuse_blocking")
        if reuse_blocking:
            if any(key in state for key in ("characters", "anchors", "boundaries")):
                raise ValueError(f"states[{state_index}] reuse_blocking cannot override characters, anchors, or boundaries")
            previous_state = next(
                (item for item in reversed(normalized_states) if item["blocking_id"] == blocking_id),
                None,
            )
            if previous_state is None:
                raise ValueError(f"states[{state_index}] reuse_blocking requires an earlier state with blocking_id {blocking_id}")
            normalized_characters = copy.deepcopy(previous_state["characters"])
            anchors = copy.deepcopy(previous_state["anchors"])
            boundaries = copy.deepcopy(previous_state["boundaries"])
            names = {character["name"] for character in normalized_characters}
        else:
            characters = state.get("characters")
            if not isinstance(characters, list) or len(characters) < 2:
                raise ValueError(f"states[{state_index}].characters must contain at least two people")
            names: set[str] = set()
            normalized_characters = []
            for char_index, character in enumerate(characters, start=1):
                name = str(character.get("name", "")).strip()
                if not name:
                    raise ValueError(f"states[{state_index}].characters[{char_index}] missing name")
                if name in names:
                    raise ValueError(f"states[{state_index}] duplicate character name: {name}")
                names.add(name)
                normalized_characters.append({
                    "name": name,
                    "x": _number(character.get("x"), f"{name}.x"),
                    "y": _number(character.get("y"), f"{name}.y"),
                    "facing_deg": _angle(character.get("facing_deg"), f"{name}.facing_deg"),
                    "color": str(character.get("color") or PALETTE[(char_index - 1) % len(PALETTE)]),
                })
            raw_anchors = state.get("anchors")
            if not isinstance(raw_anchors, list) or not raw_anchors:
                raise ValueError(f"states[{state_index}].anchors must contain at least one fixed scene anchor")
            anchors = []
            for anchor_index, anchor in enumerate(raw_anchors, start=1):
                shape = str(anchor.get("shape", "rect"))
                if shape not in ("rect", "ellipse", "line"):
                    raise ValueError(f"anchor {anchor_index} shape must be rect, ellipse, or line")
                label = str(anchor.get("label", "")).strip()
                if not label:
                    raise ValueError(f"anchor {anchor_index} missing label")
                anchors.append({
                    "label": label,
                    "shape": shape,
                    "x": _number(anchor.get("x"), f"anchor[{anchor_index}].x"),
                    "y": _number(anchor.get("y"), f"anchor[{anchor_index}].y"),
                    "width": _number(anchor.get("width", 0.1), f"anchor[{anchor_index}].width"),
                    "height": _number(anchor.get("height", 0.1), f"anchor[{anchor_index}].height"),
                    "solid": _boolean(anchor.get("solid"), f"anchor[{anchor_index}].solid"),
                })
            boundaries = []
            for boundary_index, boundary in enumerate(state.get("boundaries", []), start=1):
                label = str(boundary.get("label", "")).strip()
                side_a = str(boundary.get("side_a", "")).strip()
                side_b = str(boundary.get("side_b", "")).strip()
                if not label or not side_a or not side_b:
                    raise ValueError(f"boundary {boundary_index} requires label, side_a, and side_b")
                openings = []
                for opening_index, opening in enumerate(boundary.get("openings", []), start=1):
                    start = _number(opening.get("start"), f"boundary[{boundary_index}].openings[{opening_index}].start")
                    end = _number(opening.get("end"), f"boundary[{boundary_index}].openings[{opening_index}].end")
                    if start >= end:
                        raise ValueError(f"boundary {boundary_index} opening start must be less than end")
                    openings.append({
                        "start": start,
                        "end": end,
                        "label": str(opening.get("label", "通道")).strip() or "通道",
                    })
                boundaries.append({
                    "label": label,
                    "side_a": side_a,
                    "side_b": side_b,
                    "x1": _number(boundary.get("x1"), f"boundary[{boundary_index}].x1"),
                    "y1": _number(boundary.get("y1"), f"boundary[{boundary_index}].y1"),
                    "x2": _number(boundary.get("x2"), f"boundary[{boundary_index}].x2"),
                    "y2": _number(boundary.get("y2"), f"boundary[{boundary_index}].y2"),
                    "blocks_view": _boolean(boundary.get("blocks_view"), f"boundary[{boundary_index}].blocks_view"),
                    "openings": openings,
                })
        raw_cameras = state.get("cameras")
        if not isinstance(raw_cameras, list) or len(raw_cameras) != 1:
            raise ValueError(f"states[{state_index}].cameras must contain exactly one camera")
        cameras = []
        for camera_index, camera in enumerate(raw_cameras, start=1):
            shot_type = str(camera.get("shot_type", "relationship"))
            if shot_type not in SHOT_TYPES:
                raise ValueError(f"camera[{camera_index}].shot_type must be relationship or over_shoulder")
            foreground = str(camera.get("foreground_character", "")).strip()
            target = str(camera.get("target_character", "")).strip()
            axis_side = str(camera.get("axis_side", "positive"))
            auto_position = _boolean(camera.get("auto_position"), f"camera[{camera_index}].auto_position")
            if shot_type == "over_shoulder":
                _character_by_name(normalized_characters, foreground, "foreground_character")
                _character_by_name(normalized_characters, target, "target_character")
                if foreground == target:
                    raise ValueError("foreground_character and target_character must differ")
                if axis_side not in AXIS_SIDES:
                    raise ValueError("axis_side must be positive or negative")
                auto_position = auto_position or camera.get("x") is None or camera.get("y") is None
            if auto_position:
                if shot_type != "over_shoulder":
                    raise ValueError("auto_position is only supported for over_shoulder cameras")
                solved_x, solved_y, solved_facing = _solve_over_shoulder_camera(camera, normalized_characters)
            else:
                solved_x = _number(camera.get("x"), f"camera[{camera_index}].x")
                solved_y = _number(camera.get("y"), f"camera[{camera_index}].y")
                solved_facing = _angle(camera.get("facing_deg"), f"camera[{camera_index}].facing_deg")
            subjects = camera.get("subjects")
            if subjects is None:
                subjects = [target] if shot_type == "over_shoulder" else [
                    character["name"] for character in normalized_characters
                ]
            if not isinstance(subjects, list) or not subjects:
                raise ValueError(f"camera[{camera_index}].subjects must contain at least one character name")
            subjects = [str(subject).strip() for subject in subjects]
            if len(set(subjects)) != len(subjects) or any(subject not in names for subject in subjects):
                raise ValueError(f"camera[{camera_index}].subjects must be unique names from this state")
            cameras.append({
                "label": str(camera.get("label", f"CAM{camera_index}")),
                "x": solved_x,
                "y": solved_y,
                "facing_deg": solved_facing,
                "fov_deg": _fov(camera.get("fov_deg", 52.0 if shot_type == "over_shoulder" else 50.0), f"camera[{camera_index}].fov_deg"),
                "subjects": subjects,
                "shot_type": shot_type,
                "foreground_character": foreground,
                "target_character": target,
                "axis_side": axis_side,
                "auto_position": auto_position,
            })
        normalized_states.append({
            "blocking_id": blocking_id,
            "label": str(state.get("label", f"稳定状态{state_index}")),
            "characters": normalized_characters,
            "anchors": anchors,
            "boundaries": boundaries,
            "cameras": cameras,
        })
    blocking_signatures = {}
    for state in normalized_states:
        signature = {
            "characters": [
                {key: character[key] for key in ("name", "x", "y", "facing_deg")}
                for character in state["characters"]
            ],
            "anchors": state["anchors"],
            "boundaries": state["boundaries"],
        }
        previous = blocking_signatures.setdefault(state["blocking_id"], signature)
        if signature != previous:
            raise ValueError(
                f'blocking_id {state["blocking_id"]} must keep characters, facing, anchors, and boundaries unchanged'
            )
        _validate_state_geometry(state)
    axis_sides_by_blocking: dict[str, set[str]] = {}
    for state in normalized_states:
        camera = state["cameras"][0]
        if camera["shot_type"] == "over_shoulder":
            axis_sides_by_blocking.setdefault(state["blocking_id"], set()).add(camera["axis_side"])
    for blocking_id, sides in axis_sides_by_blocking.items():
        if len(sides) > 1:
            raise ValueError(f"blocking_id {blocking_id} reverse-shot cameras must stay on the same axis_side")
    return {
        "shot_group": group,
        "scene": str(spec.get("scene", "")).strip(),
        "states": normalized_states,
    }


def _point(x: float, y: float, box: tuple[float, float, float, float]) -> tuple[float, float]:
    left, top, width, height = box
    return left + x * width, top + y * height


def _arrow(x: float, y: float, angle: float, length: float, color: str, width: float = 5) -> str:
    radians = math.radians(angle)
    end_x = x + math.cos(radians) * length
    end_y = y + math.sin(radians) * length
    head = 14
    wing = 7
    back_x = end_x - math.cos(radians) * head
    back_y = end_y - math.sin(radians) * head
    left_x = back_x + math.cos(radians + math.pi / 2) * wing
    left_y = back_y + math.sin(radians + math.pi / 2) * wing
    right_x = back_x + math.cos(radians - math.pi / 2) * wing
    right_y = back_y + math.sin(radians - math.pi / 2) * wing
    return (
        f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{end_x:.1f}" y2="{end_y:.1f}" '
        f'stroke="{html.escape(color)}" stroke-width="{width}" stroke-linecap="round"/>'
        f'<polygon points="{end_x:.1f},{end_y:.1f} {left_x:.1f},{left_y:.1f} '
        f'{right_x:.1f},{right_y:.1f}" fill="{html.escape(color)}"/>'
    )


def _render_anchor(anchor: dict, box: tuple[float, float, float, float]) -> str:
    x, y = _point(anchor["x"], anchor["y"], box)
    width = anchor["width"] * box[2]
    height = anchor["height"] * box[3]
    label = html.escape(anchor["label"])
    style = (
        'fill="#e2e8f0" stroke="#334155" stroke-width="3"'
        if anchor["solid"] else
        'fill="#f8fafc" stroke="#64748b" stroke-width="2" stroke-dasharray="8 5"'
    )
    if anchor["shape"] == "ellipse":
        shape = f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{width / 2:.1f}" ry="{height / 2:.1f}" {style}/>'
    elif anchor["shape"] == "line":
        shape = f'<line x1="{x - width / 2:.1f}" y1="{y:.1f}" x2="{x + width / 2:.1f}" y2="{y:.1f}" {style}/>'
    else:
        shape = f'<rect x="{x - width / 2:.1f}" y="{y - height / 2:.1f}" width="{width:.1f}" height="{height:.1f}" rx="5" {style}/>'
    return shape + f'<text x="{x:.1f}" y="{y + 5:.1f}" text-anchor="middle" class="anchor">{label}</text>'


def _camera_direction_label(angle: float) -> str:
    normalized = angle % 360.0
    cardinals = (
        (0.0, "左→右"),
        (90.0, "上→下"),
        (180.0, "右→左"),
        (270.0, "下→上"),
    )
    for cardinal, direction in cardinals:
        delta = abs((normalized - cardinal + 180.0) % 360.0 - 180.0)
        if delta <= 1.0:
            return f"正向·{direction}"
    if normalized < 90.0:
        direction = "左上→右下"
    elif normalized < 180.0:
        direction = "右上→左下"
    elif normalized < 270.0:
        direction = "右下→左上"
    else:
        direction = "左下→右上"
    return f"斜向·{direction}"


def _ray_to_box_edge(
    x: float,
    y: float,
    angle: float,
    box: tuple[float, float, float, float],
) -> tuple[float, float]:
    left, top, width, height = box
    right, bottom = left + width, top + height
    radians = math.radians(angle)
    dx, dy = math.cos(radians), math.sin(radians)
    distances = []
    if dx > 1e-9:
        distances.append((right - x) / dx)
    elif dx < -1e-9:
        distances.append((left - x) / dx)
    if dy > 1e-9:
        distances.append((bottom - y) / dy)
    elif dy < -1e-9:
        distances.append((top - y) / dy)
    distance = min(value for value in distances if value >= 0.0)
    return x + dx * distance, y + dy * distance


def _validate_camera_coverage(
    camera: dict,
    characters: list[dict],
    box: tuple[float, float, float, float],
) -> None:
    camera_x, camera_y = _point(camera["x"], camera["y"], box)
    by_name = {character["name"]: character for character in characters}
    for subject in camera["subjects"]:
        character = by_name[subject]
        subject_x, subject_y = _point(character["x"], character["y"], box)
        distance = math.hypot(subject_x - camera_x, subject_y - camera_y)
        if distance < 24.0:
            raise ValueError(f'{camera["label"]} overlaps subject {subject}')
        target_angle = math.degrees(math.atan2(subject_y - camera_y, subject_x - camera_x)) % 360.0
        delta = abs((target_angle - camera["facing_deg"] + 180.0) % 360.0 - 180.0)
        subject_radius = math.degrees(math.asin(min(1.0, 24.0 / distance)))
        required_half_angle = delta + subject_radius + 2.0
        if required_half_angle > camera["fov_deg"] / 2.0:
            raise ValueError(
                f'{camera["label"]} cannot fully see {subject}: required half-angle '
                f'{required_half_angle:.1f} exceeds half FOV {camera["fov_deg"] / 2.0:.1f}'
            )


def _render_camera(camera: dict, box: tuple[float, float, float, float]) -> str:
    x, y = _point(camera["x"], camera["y"], box)
    angle = camera["facing_deg"]
    fov = camera["fov_deg"]
    rays = []
    for ray_angle in (angle - fov / 2, angle + fov / 2):
        rays.append(_ray_to_box_edge(x, y, ray_angle, box))
    label_x = max(box[0] + 110.0, min(box[0] + box[2] - 110.0, x))
    label_y = y - 54.0 if camera["y"] > 0.72 else y + 50.0
    purpose = "近肩" if camera["shot_type"] == "over_shoulder" else "关系镜"
    direction = _camera_direction_label(angle)
    label = f'{camera["label"]}｜{purpose}｜{direction}'
    return (
        f'<polygon points="{x:.1f},{y:.1f} {rays[0][0]:.1f},{rays[0][1]:.1f} '
        f'{rays[1][0]:.1f},{rays[1][1]:.1f}" fill="#7c3aed" fill-opacity="0.05" stroke="#7c3aed" '
        f'stroke-width="2" stroke-dasharray="9 7"/>'
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="15" fill="#0f172a"/>'
        + _arrow(x, y, angle, 45, "#0f172a", 4)
        + f'<g aria-label="{html.escape(label)}">'
        + f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="middle" class="camera">{html.escape(camera["label"])}｜{purpose}</text>'
        + f'<text x="{label_x:.1f}" y="{label_y + 22:.1f}" text-anchor="middle" class="camera direction">{html.escape(direction)}</text>'
        + '</g>'
    )


def _render_boundary(boundary: dict, box: tuple[float, float, float, float]) -> str:
    x1, y1 = _point(boundary["x1"], boundary["y1"], box)
    x2, y2 = _point(boundary["x2"], boundary["y2"], box)
    mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1.0
    tangent_x, tangent_y = dx / length, dy / length
    normal_x, normal_y = -dy / length, dx / length
    label_x = mid_x - tangent_x * 48
    label_y = mid_y - tangent_y * 48
    side_tangent_offset = 18
    side_normal_offset = 72
    side_a_x = mid_x + tangent_x * side_tangent_offset + normal_x * side_normal_offset
    side_a_y = mid_y + tangent_y * side_tangent_offset + normal_y * side_normal_offset
    side_b_x = mid_x + tangent_x * side_tangent_offset - normal_x * side_normal_offset
    side_b_y = mid_y + tangent_y * side_tangent_offset - normal_y * side_normal_offset
    segments = []
    if boundary["blocks_view"]:
        cursor = 0.0
        for opening in sorted(boundary["openings"], key=lambda item: item["start"]):
            if opening["start"] > cursor:
                segments.append((cursor, opening["start"]))
            cursor = max(cursor, opening["end"])
        if cursor < 1.0:
            segments.append((cursor, 1.0))
        line_markup = "".join(
            f'<line x1="{x1 + dx * start:.1f}" y1="{y1 + dy * start:.1f}" '
            f'x2="{x1 + dx * end:.1f}" y2="{y1 + dy * end:.1f}" '
            'stroke="#0f172a" stroke-width="8"/>'
            for start, end in segments
        )
        opening_markup = "".join(
            f'<text x="{x1 + dx * ((opening["start"] + opening["end"]) / 2):.1f}" '
            f'y="{y1 + dy * ((opening["start"] + opening["end"]) / 2) - 12:.1f}" '
            f'text-anchor="middle" class="side">{html.escape(opening["label"])}</text>'
            for opening in boundary["openings"]
        )
    else:
        line_markup = (
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            'stroke="#0f172a" stroke-width="5" stroke-dasharray="14 7"/>'
        )
        opening_markup = ""
    return (
        line_markup + opening_markup
        + f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="middle" class="boundary">{html.escape(boundary["label"])}</text>'
        f'<text x="{side_a_x:.1f}" y="{side_a_y:.1f}" text-anchor="middle" class="side">{html.escape(boundary["side_a"])}</text>'
        f'<text x="{side_b_x:.1f}" y="{side_b_y:.1f}" text-anchor="middle" class="side">{html.escape(boundary["side_b"])}</text>'
    )


def render_svg(spec: dict, width: int = 1400, panel_height: int = 760) -> str:
    spec = validate_spec(spec)
    states = spec["states"]
    height = 90 + len(states) * panel_height + 54
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text{font-family:'PingFang SC','Microsoft YaHei','Noto Sans CJK SC',sans-serif;letter-spacing:0}",
        ".title{font-size:30px;font-weight:700;fill:#111827}.panel{font-size:22px;font-weight:700;fill:#1f2937}",
        ".name{font-size:20px;font-weight:700}.anchor{font-size:17px;fill:#475569}.camera{font-size:17px;font-weight:700;fill:#0f172a}.direction{font-size:15px}",
        ".boundary{font-size:18px;font-weight:700;fill:#0f172a}.side{font-size:17px;font-weight:700;fill:#475569}",
        ".legend{font-size:17px;fill:#334155}",
        "</style>",
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="52" y="52" class="title">{html.escape(spec["shot_group"])}｜站位面向线稿'
        + (f'｜{html.escape(spec["scene"])}' if spec["scene"] else "") + "</text>",
    ]
    for index, state in enumerate(states):
        top = 90 + index * panel_height
        box = (70.0, top + 62.0, width - 140.0, panel_height - 105.0)
        parts.extend([
            f'<rect x="38" y="{top:.1f}" width="{width - 76}" height="{panel_height - 22}" rx="8" fill="#ffffff" stroke="#cbd5e1" stroke-width="2"/>',
            f'<text x="70" y="{top + 40:.1f}" class="panel">{html.escape(state["blocking_id"])}｜{html.escape(state["label"])}</text>',
            f'<rect x="{box[0]:.1f}" y="{box[1]:.1f}" width="{box[2]:.1f}" height="{box[3]:.1f}" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1"/>',
        ])
        for camera in state["cameras"]:
            _validate_camera_coverage(camera, state["characters"], box)
        for anchor in state["anchors"]:
            parts.append(_render_anchor(anchor, box))
        for boundary in state["boundaries"]:
            parts.append(_render_boundary(boundary, box))
        for camera in state["cameras"]:
            parts.append(_render_camera(camera, box))
        for character in state["characters"]:
            x, y = _point(character["x"], character["y"], box)
            color = html.escape(character["color"])
            parts.extend([
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="24" fill="#ffffff" stroke="{color}" stroke-width="6"/>',
                _arrow(x, y, character["facing_deg"], 70, color),
                f'<text x="{x:.1f}" y="{y - 36:.1f}" text-anchor="middle" class="name" fill="{color}">{html.escape(character["name"])}</text>',
            ])
    parts.append(
        f'<text x="52" y="{height - 20}" class="legend">场景锚点/边界两侧＝位置基准　人物圆点＝稳定站位　人物箭头＝身体面向　CAM标签/箭头/视锥＝正斜方向与范围；本图不表示运动轨迹</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def output_path(output_dir: str | Path, shot_group: str, replace: bool = False) -> Path:
    directory = Path(output_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    base = directory / f"{shot_group}.svg"
    base_png = directory / f"{shot_group}.png"
    if not replace and (base.exists() or base_png.exists()):
        raise FileExistsError(f"shot reference already exists for {shot_group}; use --replace")
    return base


def png_output_path(svg_path: Path) -> Path:
    if svg_path.suffix.lower() != ".svg" or not SHOT_GROUP_RE.fullmatch(svg_path.stem):
        raise ValueError("SVG output name must be an exact shot group such as S1-03.svg")
    return svg_path.with_suffix(".png")


def output_directory(storyboard: str | Path | None, output_dir: str | Path | None) -> tuple[Path, Path | None]:
    if storyboard is not None:
        storyboard_path = Path(storyboard).expanduser().resolve()
        return storyboard_path.parent, storyboard_path
    if output_dir is not None:
        return Path(output_dir).expanduser().resolve(), None
    raise ValueError("--storyboard or --output-dir is required")


def export_png(svg_path: Path, png_path: Path) -> str:
    converters = []
    if shutil.which("sips"):
        converters.append(("sips", ["sips", "-s", "format", "png", str(svg_path), "--out", str(png_path)]))
    if shutil.which("magick"):
        converters.append(("magick", ["magick", str(svg_path), str(png_path)]))
    if shutil.which("rsvg-convert"):
        converters.append(("rsvg-convert", ["rsvg-convert", "-o", str(png_path), str(svg_path)]))
    failures = []
    for name, command in converters:
        completed = subprocess.run(command, text=True, capture_output=True)
        if completed.returncode == 0 and png_path.is_file() and png_path.stat().st_size > 0:
            return name
        failures.append(f"{name}: {completed.stderr.strip() or completed.stdout.strip() or completed.returncode}")
    detail = "; ".join(failures) if failures else "no sips, magick, or rsvg-convert executable"
    raise ValueError("PNG export unavailable: " + detail)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", help="JSON blocking specification")
    destination_group = parser.add_mutually_exclusive_group(required=True)
    destination_group.add_argument("--storyboard", help="planned Markdown output path; images use its parent directory")
    destination_group.add_argument("--output-dir", help="explicit directory for standalone use")
    parser.add_argument("--replace", action="store_true", help="replace the exact shot-number files")
    parser.add_argument("--png", action="store_true", help="also export a same-source PNG for Jimeng")
    args = parser.parse_args(argv)
    try:
        spec_path = Path(args.spec).expanduser().resolve()
        spec = validate_spec(json.loads(spec_path.read_text(encoding="utf-8-sig")))
        directory, storyboard_path = output_directory(args.storyboard, args.output_dir)
        destination = output_path(directory, spec["shot_group"], args.replace)
        destination.write_text(render_svg(spec), encoding="utf-8")
        png_path = None
        converter = None
        if args.png:
            png_path = png_output_path(destination)
            converter = export_png(destination, png_path)
        result = {
            "pass": True,
            "shot_group": spec["shot_group"],
            "state_count": len(spec["states"]),
            "output_path": str(destination),
            "png_path": str(png_path) if png_path else None,
            "format": "svg+png" if png_path else "svg",
            "png_converter": converter,
            "storyboard_path": str(storyboard_path) if storyboard_path else None,
            "same_directory_as_storyboard": storyboard_path is not None and destination.parent == storyboard_path.parent,
            "primary_storyboard_modified": False,
        }
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"pass": False, "error": str(exc), "primary_storyboard_modified": False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
