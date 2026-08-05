#!/usr/bin/env python3
"""Regression tests for deterministic blocking/facing sheets."""

from __future__ import annotations

import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from render_blocking_reference import output_path, render_svg, validate_spec


SPEC = {
    "shot_group": "S1-03",
    "scene": "客厅",
    "states": [{
        "blocking_id": "B1",
        "label": "子镜1起幅",
        "anchors": [{"label": "长桌", "shape": "rect", "x": 0.5, "y": 0.5, "width": 0.5, "height": 0.18}],
        "boundaries": [{"label": "门槛", "side_a": "门内", "side_b": "门外", "x1": 0.1, "y1": 0.2, "x2": 0.1, "y2": 0.8}],
        "characters": [
            {"name": "沈青乔", "x": 0.35, "y": 0.7, "facing_deg": 0},
            {"name": "卫景耘", "x": 0.65, "y": 0.7, "facing_deg": 180},
        ],
        "cameras": [{"label": "CAM1", "x": 0.5, "y": 0.95, "facing_deg": 270, "fov_deg": 120}],
    }],
}


class BlockingReferenceTests(unittest.TestCase):
    def test_svg_contains_exact_names_facing_arrows_and_group_title(self) -> None:
        svg = render_svg(SPEC)
        self.assertIn("S1-03｜站位面向线稿", svg)
        self.assertIn("沈青乔", svg)
        self.assertIn("卫景耘", svg)
        self.assertIn("CAM1｜正向·下→上", svg)
        self.assertIn("门槛", svg)
        self.assertIn("门内", svg)
        self.assertIn("门外", svg)
        self.assertGreaterEqual(svg.count("<polygon"), 3)
        self.assertIn("本图不表示运动轨迹", svg)

    def test_boundary_and_camera_labels_are_spatially_separated(self) -> None:
        root = ET.fromstring(render_svg(SPEC))
        positions = {}
        for element in root.iter("{http://www.w3.org/2000/svg}text"):
            key = "CAM1" if (element.text or "").startswith("CAM1｜") else element.text
            if key in {"门槛", "门内", "门外", "CAM1"}:
                positions[key] = (float(element.attrib["x"]), float(element.attrib["y"]))
        for first, second in (("门槛", "门内"), ("门槛", "门外"), ("门内", "门外")):
            distance = sum((a - b) ** 2 for a, b in zip(positions[first], positions[second])) ** 0.5
            self.assertGreater(distance, 60)
        camera_x = 70 + 0.5 * (1400 - 140)
        camera_y = 90 + 62 + 0.95 * (760 - 105)
        distance = sum((a - b) ** 2 for a, b in zip(positions["CAM1"], (camera_x, camera_y))) ** 0.5
        self.assertGreater(distance, 35)

    def test_camera_label_distinguishes_oblique_direction(self) -> None:
        oblique = {**SPEC, "states": [{**SPEC["states"][0], "cameras": [
            {"label": "CAM2", "x": 0.1, "y": 0.9, "facing_deg": 315, "fov_deg": 110}
        ]}]}
        self.assertIn("CAM2｜斜向·左下→右上", render_svg(oblique))

    def test_rejects_camera_that_cannot_see_declared_subject(self) -> None:
        impossible = {**SPEC, "states": [{**SPEC["states"][0], "cameras": [
            {"label": "CAM1", "x": 0.5, "y": 0.95, "facing_deg": 270, "fov_deg": 20}
        ]}]}
        with self.assertRaisesRegex(ValueError, "cannot fully see"):
            render_svg(impossible)

    def test_rejects_subject_marker_clipped_by_fov_edge(self) -> None:
        edge_clipped = {**SPEC, "states": [{**SPEC["states"][0], "characters": [
            {"name": "沈青乔", "x": 0.22, "y": 0.62, "facing_deg": 0},
            {"name": "卫景耘", "x": 0.56, "y": 0.62, "facing_deg": 180},
        ], "cameras": [
            {"label": "CAM1", "x": 0.39, "y": 0.94, "facing_deg": 270, "fov_deg": 100}
        ]}]}
        with self.assertRaisesRegex(ValueError, "cannot fully see"):
            render_svg(edge_clipped)

    def test_camera_can_limit_coverage_check_to_named_subjects(self) -> None:
        closeup = {**SPEC, "states": [{**SPEC["states"][0], "cameras": [
            {"label": "CAM1", "x": 0.5, "y": 0.95, "facing_deg": 225, "fov_deg": 30, "subjects": ["沈青乔"]}
        ]}]}
        self.assertIn("CAM1｜斜向·右下→左上", render_svg(closeup))

    def test_rejects_invalid_group_coordinates_and_duplicate_names(self) -> None:
        invalid = {**SPEC, "shot_group": "scene-3"}
        with self.assertRaisesRegex(ValueError, "S1-01"):
            validate_spec(invalid)
        invalid = {**SPEC, "states": [{**SPEC["states"][0], "characters": [
            {"name": "甲", "x": 1.2, "y": 0.5, "facing_deg": 0},
            {"name": "甲", "x": 0.2, "y": 0.5, "facing_deg": 180},
        ]}]}
        with self.assertRaises(ValueError):
            validate_spec(invalid)

    def test_same_blocking_id_allows_camera_change_but_rejects_position_change(self) -> None:
        base_state = SPEC["states"][0]
        reverse_camera = {
            "label": "CAM2", "x": 0.5, "y": 0.05, "facing_deg": 90,
            "fov_deg": 120, "subjects": ["沈青乔", "卫景耘"],
        }
        same_blocking = {**SPEC, "states": [
            base_state,
            {**base_state, "label": "反打", "cameras": [reverse_camera]},
        ]}
        self.assertIn("B1｜反打", render_svg(same_blocking))
        moved_characters = [dict(character) for character in base_state["characters"]]
        moved_characters[0]["x"] = 0.4
        changed_blocking = {**SPEC, "states": [
            base_state,
            {**base_state, "label": "错误反打", "characters": moved_characters, "cameras": [reverse_camera]},
        ]}
        with self.assertRaisesRegex(ValueError, "must keep characters"):
            validate_spec(changed_blocking)

    def test_requires_fixed_scene_anchor_and_complete_boundary_sides(self) -> None:
        no_anchor = {**SPEC, "states": [{**SPEC["states"][0], "anchors": []}]}
        with self.assertRaisesRegex(ValueError, "fixed scene anchor"):
            validate_spec(no_anchor)
        bad_boundary = {**SPEC, "states": [{**SPEC["states"][0], "boundaries": [
            {"label": "门槛", "side_a": "门内", "x1": 0.1, "y1": 0.2, "x2": 0.1, "y2": 0.8}
        ]}]}
        with self.assertRaisesRegex(ValueError, "side_b"):
            validate_spec(bad_boundary)
        no_camera = {**SPEC, "states": [{**SPEC["states"][0], "cameras": []}]}
        with self.assertRaisesRegex(ValueError, "exactly one camera"):
            validate_spec(no_camera)
        two_cameras = {**SPEC, "states": [{**SPEC["states"][0], "cameras": [
            SPEC["states"][0]["cameras"][0], SPEC["states"][0]["cameras"][0]
        ]}]}
        with self.assertRaisesRegex(ValueError, "exactly one camera"):
            validate_spec(two_cameras)

    def test_output_uses_group_filename_and_versions_without_replace(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            first = output_path(root, "S1-03")
            first.write_text("first", encoding="utf-8")
            second = output_path(root, "S1-03")
            self.assertEqual("S1-03_站位面向线稿-v2.svg", second.name)
            self.assertEqual(first, output_path(root, "S1-03", replace=True))


if __name__ == "__main__":
    unittest.main()
