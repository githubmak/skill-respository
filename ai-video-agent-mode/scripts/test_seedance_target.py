import os
import unittest

from seedance_target import adapt_lighting_text, adapt_visual_prefix, normalize_target, variant_paths
from resolve_run_mode import config_issues


class SeedanceTargetTests(unittest.TestCase):
    def test_aliases_and_targets(self):
        self.assertEqual(normalize_target("双版本"), "both")
        self.assertEqual(normalize_target("Seedance 2.5"), "2.5")

    def test_both_paths_are_independent_and_indexed(self):
        paths, index = variant_paths(r"C:\out\scene.md", "both")
        self.assertTrue(paths["2.0"].endswith("scene_Seedance2.0.md"))
        self.assertTrue(paths["2.5"].endswith("scene_Seedance2.5.md"))
        self.assertTrue(index.endswith("00_双版本索引.md"))
        self.assertNotEqual(paths["2.0"], paths["2.5"])

    def test_lighting_adapters_are_distinct(self):
        base = "窗光从左侧落到人物脸部，右侧脸颊保留阴影。"
        self.assertIn("浅至中等阴影", adapt_lighting_text(base, "2.0"))
        self.assertIn("中深明暗层次", adapt_lighting_text(base, "2.5"))
        self.assertEqual(adapt_lighting_text(base, "auto"), base)

    def test_old_uniform_face_rule_is_rewritten_for_newer_targets(self):
        old = "脸部受光均匀，鼻侧、眼窝和下颌只保留浅阴影。"
        self.assertNotIn("脸部受光均匀", adapt_visual_prefix(old, "2.5"))
        self.assertIn("中深", adapt_visual_prefix(old, "2.5"))
        self.assertIn("中等", adapt_visual_prefix(old, "auto"))

    def test_both_rejects_duration_above_cross_version_limit(self):
        config = {
            "export_base": r"C:\out", "canvas": "16:9", "visual_style": "写实",
            "max_shot_duration": 20, "target_platform": "即梦", "seedance_target": "both",
            "generation_control": {"mode": "t2v", "audio_enabled": True},
            "delivery": {"markdown_path": r"C:\out\scene.md"},
        }
        self.assertTrue(any("<=15" in issue for issue in config_issues(config, require_confirmation=False)))


if __name__ == "__main__":
    unittest.main()
