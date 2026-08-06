import os
import unittest

from seedance_target import normalize_target, variant_paths
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

    def test_target_module_has_no_creative_adapters(self):
        import seedance_target
        self.assertFalse(hasattr(seedance_target, "adapt_lighting_text"))
        self.assertFalse(hasattr(seedance_target, "adapt_visual_prefix"))

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
