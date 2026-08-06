#!/usr/bin/env python3
"""Regression tests for deterministic blocking/facing sheets."""

from __future__ import annotations

import tempfile
import unittest
import xml.etree.ElementTree as ET
import json
from pathlib import Path

from render_blocking_reference import main, output_directory, output_path, png_output_path, render_svg, validate_spec


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
        self.assertIn("CAM1｜关系镜｜正向·下→上", svg)
        self.assertIn("门槛", svg)
        self.assertIn("门内", svg)
        self.assertIn("门外", svg)
        self.assertGreaterEqual(svg.count("<polygon"), 3)
        self.assertIn("本图不表示运动轨迹", svg)
        self.assertIn('fill-opacity="0.05"', svg)
        self.assertNotIn("#7c3aed0d", svg)

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
        self.assertIn("CAM2｜关系镜｜斜向·左下→右上", render_svg(oblique))

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
        self.assertIn("CAM1｜关系镜｜斜向·右下→左上", render_svg(closeup))

    def test_camera_path_is_validated_and_drawn_from_same_blocking(self) -> None:
        moving = {**SPEC, "states": [{**SPEC["states"][0], "cameras": [{
            **SPEC["states"][0]["cameras"][0],
            "subjects": ["卫景耘"],
            "path": {
                "mode": "track", "end_x": 0.62, "end_y": 0.90, "end_facing_deg": 260,
                "trigger": "卫景耘退开", "dramatic_gain": "显露关系距离",
            },
        }]}]}
        normalized = validate_spec(moving)
        self.assertEqual(normalized["states"][0]["cameras"][0]["path"]["mode"], "track")
        svg = render_svg(moving)
        self.assertIn("track｜显露关系距离", svg)
        self.assertIn("青色虚线路径", svg)

        blocked = {**SPEC, "states": [{**SPEC["states"][0], "anchors": [{
            **SPEC["states"][0]["anchors"][0], "solid": True,
        }], "cameras": [{
            **SPEC["states"][0]["cameras"][0],
            "path": {
                "mode": "track", "end_x": 0.5, "end_y": 0.1, "end_facing_deg": 90,
                "trigger": "人物起身", "dramatic_gain": "显露空间变化",
            },
        }]}]}
        with self.assertRaisesRegex(ValueError, "intersects solid anchor 长桌"):
            validate_spec(blocked)

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

    def test_rejects_parallel_arrows_in_two_person_relationship(self) -> None:
        parallel = {**SPEC, "states": [{**SPEC["states"][0], "characters": [
            {"name": "沈青乔", "x": 0.35, "y": 0.7, "facing_deg": 0},
            {"name": "卫景耘", "x": 0.65, "y": 0.7, "facing_deg": 0},
        ]}]}
        with self.assertRaisesRegex(ValueError, "must face"):
            validate_spec(parallel)

    def test_independent_relationship_allows_intentional_non_facing(self) -> None:
        independent = {**SPEC, "states": [{**SPEC["states"][0], "cameras": [
            {**SPEC["states"][0]["cameras"][0], "facing_mode": "independent"}
        ], "characters": [
            {"name": "沈青乔", "x": 0.35, "y": 0.7, "facing_deg": 0},
            {"name": "卫景耘", "x": 0.65, "y": 0.7, "facing_deg": 0},
        ]}]}
        self.assertEqual(validate_spec(independent)["states"][0]["cameras"][0]["facing_mode"], "independent")

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

    def test_reverse_panel_can_reuse_prior_blocking_without_copying_geometry(self) -> None:
        base_state = SPEC["states"][0]
        reused = {
            "blocking_id": "B1",
            "label": "反打",
            "reuse_blocking": True,
            "cameras": [{
                "label": "CAM2", "x": 0.5, "y": 0.05, "facing_deg": 90,
                "fov_deg": 120, "subjects": ["沈青乔", "卫景耘"],
            }],
        }
        normalized = validate_spec({**SPEC, "states": [base_state, reused]})
        self.assertEqual(normalized["states"][0]["characters"], normalized["states"][1]["characters"])
        self.assertIn("B1｜反打", render_svg({**SPEC, "states": [base_state, reused]}))
        with self.assertRaisesRegex(ValueError, "cannot override"):
            validate_spec({**SPEC, "states": [base_state, {**reused, "characters": base_state["characters"]}]})

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

    def test_output_uses_exact_shot_number_and_refuses_implicit_versioning(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            first = output_path(root, "S1-03")
            self.assertEqual("S1-03.svg", first.name)
            self.assertEqual("S1-03.png", png_output_path(first).name)
            first.write_text("first", encoding="utf-8")
            with self.assertRaisesRegex(FileExistsError, "use --replace"):
                output_path(root, "S1-03")
            self.assertEqual(first, output_path(root, "S1-03", replace=True))

    def test_storyboard_path_places_exact_named_images_in_staging_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            storyboard = base / "exports" / "第1场_即梦投喂分镜.md"
            spec_path = base / "blocking.json"
            spec_path.write_text(json.dumps(SPEC, ensure_ascii=False), encoding="utf-8")
            directory, resolved_storyboard = output_directory(storyboard, None)
            self.assertEqual((storyboard.parent / "staging" / "blocking").resolve(), directory)
            self.assertEqual(storyboard.resolve(), resolved_storyboard)
            self.assertEqual(0, main([
                str(spec_path), "--storyboard", str(storyboard), "--replace", "--compact",
                "--report", str(base / "blocking.report.json"),
            ]))
            self.assertTrue((storyboard.parent / "staging" / "blocking" / "S1-03.svg").is_file())

    def test_rejects_character_on_boundary_without_explicit_exception(self) -> None:
        on_boundary = {**SPEC, "states": [{**SPEC["states"][0], "characters": [
            {"name": "沈青乔", "x": 0.1, "y": 0.7, "facing_deg": 0},
            {"name": "卫景耘", "x": 0.65, "y": 0.7, "facing_deg": 180},
        ]}]}
        with self.assertRaisesRegex(ValueError, "too close to boundary"):
            validate_spec(on_boundary)

    def test_rejects_label_collision_after_render_layout(self) -> None:
        collision = {**SPEC, "states": [{**SPEC["states"][0], "characters": [
            {"name": "沈青乔", "x": 0.35, "y": 0.7, "facing_deg": 0, "label_dx": 180},
            {"name": "卫景耘", "x": 0.65, "y": 0.7, "facing_deg": 180, "label_dx": -180},
        ]}]}
        with self.assertRaisesRegex(ValueError, "label collision"):
            render_svg(collision)

    def test_rejects_anchor_label_hidden_by_character_marker(self) -> None:
        hidden = {**SPEC, "states": [{**SPEC["states"][0], "anchors": [{
            "label": "菜篮", "shape": "rect", "x": 0.35, "y": 0.7, "width": 0.1, "height": 0.08,
        }]}]}
        with self.assertRaisesRegex(ValueError, "label-to-marker collision: 菜篮"):
            render_svg(hidden)

        offset = {**SPEC, "states": [{**SPEC["states"][0], "anchors": [{
            "label": "菜篮", "shape": "rect", "x": 0.35, "y": 0.7, "width": 0.1, "height": 0.08,
            "label_dy": 70,
        }]}]}
        self.assertIn("菜篮", render_svg(offset))

    def test_auto_over_shoulder_is_rejected_without_director_camera_choice(self) -> None:
        characters = [
            {"name": "沈青乔", "x": 0.3, "y": 0.5, "facing_deg": 0},
            {"name": "卫景耘", "x": 0.7, "y": 0.5, "facing_deg": 180},
        ]
        base = {
            "blocking_id": "B2",
            "anchors": [{"label": "桌子", "shape": "rect", "x": 0.76, "y": 0.2, "width": 0.18, "height": 0.1, "solid": True}],
            "boundaries": [{
                "label": "门墙", "side_a": "门外", "side_b": "屋内",
                "x1": 0.5, "y1": 0.0, "x2": 0.5, "y2": 1.0,
                "blocks_view": True,
                "openings": [{"start": 0.4, "end": 0.6, "label": "门洞"}],
            }],
            "characters": characters,
        }
        spec = {
            "shot_group": "S1-04",
            "scene": "门口",
            "states": [
                {**base, "label": "卫景耘肩后看沈青乔", "cameras": [{
                    "label": "CAM-A", "shot_type": "over_shoulder", "auto_position": True,
                    "foreground_character": "卫景耘", "target_character": "沈青乔", "axis_side": "positive",
                }]},
                {**base, "label": "沈青乔肩后看卫景耘", "cameras": [{
                    "label": "CAM-B", "shot_type": "over_shoulder", "auto_position": True,
                    "foreground_character": "沈青乔", "target_character": "卫景耘", "axis_side": "positive",
                }]},
            ],
        }
        with self.assertRaisesRegex(ValueError, "auto_position is disabled"):
            validate_spec(spec)

    def test_independent_over_shoulder_allows_target_to_face_away(self) -> None:
        state = {
            "blocking_id": "B-AWAY",
            "label": "背向近肩",
            "anchors": [{"label": "矮柜", "shape": "rect", "x": 0.2, "y": 0.2, "width": 0.12, "height": 0.1}],
            "boundaries": [],
            "characters": [
                {"name": "卫景耘", "x": 0.3, "y": 0.5, "facing_deg": 0},
                {"name": "沈青乔", "x": 0.7, "y": 0.5, "facing_deg": 0},
            ],
            "cameras": [{
                "label": "CAM-A", "shot_type": "over_shoulder", "x": 0.18, "y": 0.56, "facing_deg": 6,
                "foreground_character": "卫景耘", "target_character": "沈青乔", "axis_side": "positive",
                "facing_mode": "independent",
            }],
        }
        normalized = validate_spec({"shot_group": "S3-05", "scene": "门槛", "states": [state]})
        self.assertEqual("independent", normalized["states"][0]["cameras"][0]["facing_mode"])

        default_mutual = {**state, "cameras": [{
            key: value for key, value in state["cameras"][0].items() if key != "facing_mode"
        }]}
        with self.assertRaisesRegex(ValueError, "must physically face"):
            validate_spec({"shot_group": "S3-05", "scene": "门槛", "states": [default_mutual]})

    def test_rejects_occluded_target_and_wrong_reverse_axis_side(self) -> None:
        characters = [
            {"name": "甲", "x": 0.25, "y": 0.5, "facing_deg": 0},
            {"name": "乙", "x": 0.75, "y": 0.5, "facing_deg": 180},
        ]
        state = {
            "blocking_id": "B3",
            "label": "遮挡错误",
            "anchors": [{"label": "柜子", "shape": "rect", "x": 0.5, "y": 0.5, "width": 0.12, "height": 0.2, "solid": True}],
            "boundaries": [],
            "characters": characters,
            "cameras": [{"label": "CAM", "x": 0.9, "y": 0.5, "facing_deg": 180, "fov_deg": 60, "subjects": ["甲"]}],
        }
        with self.assertRaisesRegex(ValueError, "blocked by 柜子"):
            validate_spec({"shot_group": "S1-05", "states": [state]})

        reverse_base = {
            **state,
            "anchors": [{"label": "边桌", "shape": "rect", "x": 0.5, "y": 0.15, "width": 0.1, "height": 0.1}],
            "cameras": [{
                "label": "CAM-A", "shot_type": "over_shoulder", "x": 0.82, "y": 0.56, "facing_deg": 174,
                "foreground_character": "乙", "target_character": "甲", "axis_side": "positive",
            }],
        }
        reverse_other = {
            **reverse_base,
            "label": "错误越轴反打",
            "cameras": [{
                "label": "CAM-B", "shot_type": "over_shoulder", "x": 0.18, "y": 0.44, "facing_deg": 6,
                "foreground_character": "甲", "target_character": "乙", "axis_side": "negative",
            }],
        }
        with self.assertRaisesRegex(ValueError, "same axis_side"):
            validate_spec({"shot_group": "S1-06", "states": [reverse_base, reverse_other]})


if __name__ == "__main__":
    unittest.main()
