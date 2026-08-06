#!/usr/bin/env python3
"""Ensure the active workflow preserves the creative/engineering boundary."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from route_task import route


SKILL_ROOT = Path(__file__).resolve().parents[1]


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_active_route_has_one_delivery_validator_and_no_creative_gates(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            source.write_text("场景：门口\n甲：你来了。\n乙：嗯。", encoding="utf-8")
            result = route("generate", str(source))
        active = "\n".join(result["run_before_generation"] + result["run_after_generation"] + result["run_after_review"])
        self.assertIn("validate_delivery.py", active)
        for legacy in (
            "scene_contract.py", "contract_compile.py", "incremental_validate.py",
            "validate_storyboard.py", "prompt_preflight.py", "creative_preflight.py",
        ):
            self.assertNotIn(legacy, active)
            self.assertFalse((SKILL_ROOT / "scripts" / legacy).exists())
        self.assertNotIn("legacy_diagnostics_not_in_main_path", result)
        self.assertFalse(result["execution_policy"]["creative_keyword_gates"])
        self.assertFalse(result["execution_policy"]["creative_scores_or_quotas"])
        self.assertFalse(result["execution_policy"]["contract_recovery"])
        self.assertNotIn("style_evidence", result["source_gate"])

    def test_core_and_template_have_one_creative_source_of_truth(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        runtime = (SKILL_ROOT / "references" / "runtime-core.md").read_text(encoding="utf-8")
        template = (SKILL_ROOT / "references" / "output-template.md").read_text(encoding="utf-8")
        self.assertIn("唯一创意事实源", template)
        self.assertIn("不存在必须使用的拍法、运镜次数、景别数量、签名镜配额", runtime)
        self.assertIn("不生成前置 `scene_contract.json`", skill)
        for removed_field in ("【状态继承】", "【本镜制作控制】", "【表演与声音】"):
            self.assertNotIn(removed_field, template)
        for retained in ("【Seedance 直投提示】", "【声音原文】", "【审核后参考素材】"):
            self.assertIn(retained, template)
        for per_shot_visual in ("色卡：", "影调：", "光影："):
            self.assertIn(per_shot_visual, template)
        self.assertNotIn("光影色彩：", template)

    def test_routed_references_do_not_reintroduce_legacy_pipeline(self) -> None:
        routed = (
            "prompt-performance-runtime.md", "spatial-camera-runtime.md", "blocking-facing-reference.md",
            "physical-structure-continuity.md", "generation-risk-guards.md", "visual-attraction-rules.md",
            "narrative-mode-routing.md", "cinematic-grammar-library.md", "seedance-target-adaptation.md",
            "seedance-generation-diagnostics.md",
        )
        forbidden = ("scene_contract.json", "contract_compile.py", "creative_preflight.py", "签名镜配额")
        for name in routed:
            text = (SKILL_ROOT / "references" / name).read_text(encoding="utf-8")
            for term in forbidden:
                self.assertNotIn(term, text, f"{name} reintroduced {term}")

    def test_creative_libraries_are_reachable_without_becoming_gates(self) -> None:
        expected = {
            "color-palette-library.md", "liveness-motion-grammar.md",
            "performance-baseline-library.md", "scene-preset-library.md",
            "shot-patterns.md", "visual-direction-profiles.md",
            "cinematic-grammar-library.md", "narrative-mode-routing.md",
            "seedance-example-patterns.md", "seedance-generation-diagnostics.md",
        }
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            source.write_text("场景：夜，门内\n甲坐在桌边。\n乙：你回来了。\n甲：嗯。", encoding="utf-8")
            result = route("generate", str(source))
        catalog = {Path(item["path"]).name for item in result["creative_reference_catalog"].values()}
        self.assertEqual(expected, catalog)
        suggestions = {Path(item).name for item in result["creative_reference_suggestions"]}
        self.assertIn("performance-baseline-library.md", suggestions)
        self.assertIn("liveness-motion-grammar.md", suggestions)
        self.assertIn("color-palette-library.md", suggestions)
        routed = {Path(item).name for item in result["read_on_demand"]}
        self.assertTrue(expected.isdisjoint(routed))

    def test_seedance_examples_cover_known_ambiguities_without_control_logic(self) -> None:
        examples = (SKILL_ROOT / "references" / "seedance-example-patterns.md").read_text(encoding="utf-8")
        for topic in (
            "摄影机与人物路径分离", "多人对白先后", "道具与容器", "左右参照系",
            "焦点转移", "光影稳定", "参考图职责", "单一稳定终态",
        ):
            self.assertIn(topic, examples)
        for forbidden in (
            "evidence_score", "创意评分", "镜头配额", "关键词校验", "自动修复器",
        ):
            self.assertNotIn(forbidden, examples)
        self.assertIn("未找到可公开核验", examples)
        self.assertIn("不冒充官方能力声明", examples)
        adaptation = (SKILL_ROOT / "references" / "seedance-target-adaptation.md").read_text(encoding="utf-8")
        self.assertIn("餐桌南侧", adaptation)
        self.assertIn("观众无法验证", adaptation)

    def test_source_keywords_do_not_auto_select_creative_camera_or_narrative_references(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            source.write_text(
                "场景：乡村喜剧，摄影机横移后转焦。\n甲：你看错了。\n乙闭口看向篮子。",
                encoding="utf-8",
            )
            result = route("generate", str(source), seedance_target="auto")
        routed = {Path(item).name for item in result["read_on_demand"]}
        self.assertNotIn("cinematic-grammar-library.md", routed)
        self.assertNotIn("narrative-mode-routing.md", routed)
        self.assertNotIn("seedance-example-patterns.md", routed)
        self.assertNotIn("seedance-generation-diagnostics.md", routed)

    def test_generation_diagnostics_are_model_led_and_visual_evidence_based(self) -> None:
        diagnostics = (SKILL_ROOT / "references" / "seedance-generation-diagnostics.md").read_text(encoding="utf-8")
        for topic in (
            "素材先验", "遮挡、出画与重新出现", "首尾帧与跨镜参考",
            "焦点、曝光与材质", "指令冲突", "真实生成后的单变量诊断",
        ):
            self.assertIn(topic, diagnostics)
        for forbidden in (
            "【摄影合同】", "【状态继承】", "固定配额", "自动修复脚本", "必须按顺序删除",
        ):
            self.assertNotIn(forbidden, diagnostics)
        self.assertIn("真实画面审片", diagnostics)
        self.assertIn("不是无限抽卡流程", diagnostics)

    def test_removed_legacy_references_do_not_exist(self) -> None:
        for name in (
            "prompt-performance-rules.md", "regression-cases.md", "runtime-brief.md",
            "validation-checklist.md", "task-adaptation-contract.md", "spatial-camera-continuity.md",
        ):
            self.assertFalse((SKILL_ROOT / "references" / name).exists())

    def test_creative_libraries_contain_knowledge_not_control_contracts(self) -> None:
        creative = {
            name: (SKILL_ROOT / "references" / name).read_text(encoding="utf-8")
            for name in (
                "color-palette-library.md", "liveness-motion-grammar.md",
                "performance-baseline-library.md", "scene-preset-library.md",
                "shot-patterns.md", "visual-direction-profiles.md",
                "cinematic-grammar-library.md", "narrative-mode-routing.md",
                "seedance-example-patterns.md", "seedance-generation-diagnostics.md",
            )
        }
        combined = "\n".join(creative.values())
        for removed in (
            "【本镜制作控制】", "【状态继承】", "evidence_score",
            "场景生命合同", "主色60%-70%", "最多两个低幅耦合响应",
        ):
            self.assertNotIn(removed, combined)
        self.assertIn("由模型", creative["visual-direction-profiles.md"])
        self.assertIn("不设固定值", creative["color-palette-library.md"])


if __name__ == "__main__":
    unittest.main()
