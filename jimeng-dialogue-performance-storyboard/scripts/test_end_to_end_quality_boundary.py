#!/usr/bin/env python3
"""End-to-end regression for creative ownership and deterministic engineering gates."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from contract_compile import compact_report
from render_blocking_reference import output_directory, validate_spec
from review_manifest import build_manifest, verify_manifest, write_manifest
from scene_contract import compile_contract
from source_gate import inspect_text
from test_render_blocking_reference import SPEC
from test_scene_contract import CONTRACT


class EndToEndQualityBoundaryTests(unittest.TestCase):
    def test_realistic_dialogue_chain_preserves_creativity_and_blocks_engineering_leaks(self) -> None:
        source = """人物：沈青乔、满满、阿丰、卫景耘、豆宝
场景：院儿内小屋门口，夜
满满（兴奋）：爹爹，娘亲带我们去抓鱼了！
卫景耘（不信）：不会有毒吧？
阿丰：娘亲教了我们辨别有毒的和没有毒的。
沈青乔（皱眉，OS）：还剩点粗盐。
豆宝：发现可食用植物。
"""
        intake = inspect_text(source)
        self.assertEqual(["满满", "卫景耘", "阿丰", "沈青乔", "豆宝"], intake["stats"]["speakers"])

        contract = copy.deepcopy(CONTRACT)
        contract["camera_strategy"] = {
            "audience_position": "观众在门内观察关系",
            "movement_arc": "单镜静止保留边界压力",
            "static_rule": "单镜有意静止",
            "forbidden_repetition": "单镜无重复",
        }
        contract["shots"][0]["camera"] = {
            "visual_task": "由大模型选定的导演任务",
            "shot_size": "中近景",
            "composition": "由大模型选定的门框构图",
            "mode": "static",
            "trigger": "沈青乔说别进来",
            "path": "摄影机固定在沈青乔肩后",
            "dramatic_gain": "由大模型选定的静止收益",
            "end_frame": "两人隔着门槛停住",
        }
        ledger = compact_report(compile_contract(contract))
        self.assertFalse(ledger["feed_ready"])
        self.assertFalse(ledger["creative_decisions_modified"])
        self.assertNotIn("由大模型选定的导演任务", ledger["shots"][0]["body"])
        self.assertIn("摄影机固定在沈青乔肩后", ledger["shots"][0]["body"])

        boundary_failure = copy.deepcopy(SPEC)
        boundary_failure["states"][0]["characters"][0]["x"] = 0.1
        with self.assertRaisesRegex(ValueError, "too close to boundary"):
            validate_spec(boundary_failure)

        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            storyboard = base / "storyboard.md"
            source_path = base / "source.txt"
            source_path.write_text(source, encoding="utf-8")
            storyboard.write_text("分镜", encoding="utf-8")
            directory, _ = output_directory(storyboard, None)
            self.assertEqual((base / "staging" / "blocking").resolve(), directory)
            manifest = base / "reports" / "manifest.json"
            manifest.parent.mkdir()
            payload = build_manifest(source_path, [storyboard], "self_check", "PASS", "PASS", delivery_root=base)
            write_manifest(manifest, payload)
            (base / "unreviewed.png").write_bytes(b"unreviewed")
            self.assertFalse(verify_manifest(manifest, base)["pass"])


if __name__ == "__main__":
    unittest.main()
