#!/usr/bin/env python3
"""Render deterministic multi-character blocking/facing sheets as SVG."""

from __future__ import annotations

import argparse
import html
import json
import math
import re
from pathlib import Path


SHOT_GROUP_RE = re.compile(r"^S\d+-\d+$")
PALETTE = ("#2563eb", "#d97706", "#dc2626", "#059669", "#7c3aed", "#475569")


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
            item = {
                "label": label,
                "shape": shape,
                "x": _number(anchor.get("x"), f"anchor[{anchor_index}].x"),
                "y": _number(anchor.get("y"), f"anchor[{anchor_index}].y"),
                "width": _number(anchor.get("width", 0.1), f"anchor[{anchor_index}].width"),
                "height": _number(anchor.get("height", 0.1), f"anchor[{anchor_index}].height"),
            }
            anchors.append(item)
        boundaries = []
        for boundary_index, boundary in enumerate(state.get("boundaries", []), start=1):
            label = str(boundary.get("label", "")).strip()
            side_a = str(boundary.get("side_a", "")).strip()
            side_b = str(boundary.get("side_b", "")).strip()
            if not label or not side_a or not side_b:
                raise ValueError(f"boundary {boundary_index} requires label, side_a, and side_b")
            boundaries.append({
                "label": label,
                "side_a": side_a,
                "side_b": side_b,
                "x1": _number(boundary.get("x1"), f"boundary[{boundary_index}].x1"),
                "y1": _number(boundary.get("y1"), f"boundary[{boundary_index}].y1"),
                "x2": _number(boundary.get("x2"), f"boundary[{boundary_index}].x2"),
                "y2": _number(boundary.get("y2"), f"boundary[{boundary_index}].y2"),
            })
        raw_cameras = state.get("cameras")
        if not isinstance(raw_cameras, list) or len(raw_cameras) != 1:
            raise ValueError(f"states[{state_index}].cameras must contain exactly one camera")
        cameras = []
        for camera_index, camera in enumerate(raw_cameras, start=1):
            subjects = camera.get("subjects")
            if subjects is None:
                subjects = [character["name"] for character in normalized_characters]
            if not isinstance(subjects, list) or not subjects:
                raise ValueError(f"camera[{camera_index}].subjects must contain at least one character name")
            subjects = [str(subject).strip() for subject in subjects]
            if len(set(subjects)) != len(subjects) or any(subject not in names for subject in subjects):
                raise ValueError(f"camera[{camera_index}].subjects must be unique names from this state")
            cameras.append({
                "label": str(camera.get("label", f"CAM{camera_index}")),
                "x": _number(camera.get("x"), f"camera[{camera_index}].x"),
                "y": _number(camera.get("y"), f"camera[{camera_index}].y"),
                "facing_deg": _angle(camera.get("facing_deg"), f"camera[{camera_index}].facing_deg"),
                "fov_deg": _fov(camera.get("fov_deg", 50.0), f"camera[{camera_index}].fov_deg"),
                "subjects": subjects,
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
    style = 'fill="#f8fafc" stroke="#64748b" stroke-width="2" stroke-dasharray="8 5"'
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
    label_rad = math.radians(angle + 180.0)
    label_x = x + math.cos(label_rad) * 40
    label_y = y + math.sin(label_rad) * 40 + 6
    label = f'{camera["label"]}｜{_camera_direction_label(angle)}'
    return (
        f'<polygon points="{x:.1f},{y:.1f} {rays[0][0]:.1f},{rays[0][1]:.1f} '
        f'{rays[1][0]:.1f},{rays[1][1]:.1f}" fill="#0f172a12" stroke="#0f172a" '
        f'stroke-width="2" stroke-dasharray="7 5"/>'
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="15" fill="#0f172a"/>'
        + _arrow(x, y, angle, 45, "#0f172a", 4)
        + f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="middle" class="camera">{html.escape(label)}</text>'
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
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        'stroke="#0f172a" stroke-width="5" stroke-dasharray="14 7"/>'
        f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="middle" class="boundary">{html.escape(boundary["label"])}</text>'
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
        ".name{font-size:20px;font-weight:700}.anchor{font-size:17px;fill:#475569}.camera{font-size:17px;font-weight:700;fill:#0f172a}",
        ".boundary{font-size:18px;font-weight:700;fill:#0f172a}.side{font-size:17px;font-weight:700;fill:#475569}",
        ".legend{font-size:17px;fill:#334155}",
        "</style>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
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
    base = directory / f"{shot_group}_站位面向线稿.svg"
    if replace or not base.exists():
        return base
    version = 2
    while True:
        candidate = directory / f"{shot_group}_站位面向线稿-v{version}.svg"
        if not candidate.exists():
            return candidate
        version += 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", help="JSON blocking specification")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--replace", action="store_true", help="replace the stable group filename")
    args = parser.parse_args(argv)
    try:
        spec_path = Path(args.spec).expanduser().resolve()
        spec = validate_spec(json.loads(spec_path.read_text(encoding="utf-8-sig")))
        destination = output_path(args.output_dir, spec["shot_group"], args.replace)
        destination.write_text(render_svg(spec), encoding="utf-8")
        result = {
            "pass": True,
            "shot_group": spec["shot_group"],
            "state_count": len(spec["states"]),
            "output_path": str(destination),
            "format": "svg",
            "primary_storyboard_modified": False,
        }
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"pass": False, "error": str(exc), "primary_storyboard_modified": False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
