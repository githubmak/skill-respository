#!/usr/bin/env python3
"""Regression checks for compact routing and companion output."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from concise_storyboard import extract
from route_task import route


SKILL_ROOT = Path(__file__).resolve().parent.parent


class RuntimeToolTests(unittest.TestCase):
    def test_default_route_is_compact(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            source.write_text("SCENE 1 客厅\n甲：你回来了。", encoding="utf-8")
            result = route("generate", str(source))
        self.assertTrue(result["pass"])
        self.assertEqual(result["read_first"], ["references/runtime-core.md", "references/output-template.md"])
        self.assertEqual(result["read_on_demand"], [])
        runtime = (SKILL_ROOT / "references" / "runtime-core.md").read_text(encoding="utf-8")
        self.assertIn("普通对白逐镜先写内部轻量内核", runtime)
        self.assertIn("表面台词 -> 本句实际维护/争取/回避的关系", runtime)
        self.assertEqual(result["run_during_generation"][0]["after"], "each_shot")
        self.assertEqual(result["run_during_generation"][0]["script"], "scripts/incremental_validate.py")
        self.assertEqual(
            result["run_during_generation"][0]["arguments"],
            ["<scene_draft.md>", "--current-shot", "<shot_id>"],
        )
        self.assertNotIn("command", result["run_during_generation"][0])
        self.assertIn("scripts/validate_storyboard.py", result["run_after_generation"])
        self.assertTrue(any("scene_contract.py" in item for item in result["run_after_generation"]))
        self.assertEqual(result["read_after_generation"], ["references/review-pipeline.md"])
        self.assertEqual(result["optional_after_delivery"], ["scripts/concise_storyboard.py"])
        self.assertIn("scripts/review_manifest.py verify", result["run_after_review"])

    def test_risks_load_only_specialist_references(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            source.write_text("SCENE 1 电梯\n三人围在门边，甲把手机递给乙。", encoding="utf-8")
            result = route("generate", str(source))
        self.assertIn("references/physical-structure-continuity.md", result["read_on_demand"])
        self.assertIn("references/spatial-camera-runtime.md", result["read_on_demand"])
        self.assertIn("references/generation-risk-guards.md", result["read_on_demand"])
        self.assertIn("references/blocking-facing-reference.md", result["read_on_demand"])
        self.assertEqual(
            "scripts/render_blocking_reference.py",
            result["run_before_prompt_compilation"][0]["script"],
        )
        self.assertIn("--png", result["run_before_prompt_compilation"][0]["arguments"])
        self.assertIn("--storyboard", result["run_before_prompt_compilation"][0]["arguments"])
        self.assertIn("<planned_output.md>", result["run_before_prompt_compilation"][0]["arguments"])
        self.assertNotIn("--output-dir", result["run_before_prompt_compilation"][0]["arguments"])
        self.assertTrue(result["run_before_prompt_compilation"][0]["exact_shot_number_filenames"])
        self.assertTrue(result["run_before_prompt_compilation"][0]["same_directory_as_storyboard"])
        self.assertTrue(result["run_before_prompt_compilation"][0]["same_source_svg_png"])

    def test_audit_and_video_review_cannot_bypass_semantic_review(self):
        audit = route("audit")
        video = route("video-review")
        self.assertIn("references/review-pipeline.md", audit["read_first"])
        self.assertTrue(audit["design_review_required"])
        self.assertIn("references/review-pipeline.md", video["read_first"])
        self.assertTrue(video["objective_metrics_only"])
        self.assertTrue(video["visual_semantic_review_required"])

    def test_natural_camera_language_and_three_speakers_route_specialists(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            source.write_text(
                "SCENE 1 站厅\n摄影机沿中线缓慢拉开，再快速右摇落到出口。\n"
                "甲：“走吧。”乙：“等一下。”丙：“闸机锁了。”",
                encoding="utf-8",
            )
            result = route("generate", str(source))
        self.assertIn("references/cinematic-grammar-library.md", result["read_on_demand"])
        self.assertIn("references/prompt-performance-runtime.md", result["read_on_demand"])
        self.assertIn("references/spatial-camera-runtime.md", result["read_on_demand"])

    def test_unfamiliar_prose_and_viewpoint_path_route_conservatively(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            source.write_text(
                "轨道舱忽然失重。直到舱门开启，她却发现时间环已经归零。"
                "摄影机贴近舷窗后穿过舱门，落到她握紧的玉佩。",
                encoding="utf-8",
            )
            result = route("generate", str(source))
        self.assertIn("references/narrative-mode-routing.md", result["read_on_demand"])
        self.assertIn("references/cinematic-grammar-library.md", result["read_on_demand"])

    def test_explicit_performance_cue_routes_performance_rules(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            source.write_text("SCENE 1 客厅\n甲（压着嗓子）：别出声。", encoding="utf-8")
            result = route("generate", str(source))
        self.assertIn("references/prompt-performance-runtime.md", result["read_on_demand"])
        self.assertIn(
            "explicit source performance cue",
            result["routing_reasons"]["references/prompt-performance-runtime.md"],
        )

    def test_critical_two_person_turn_routes_performance_without_parenthetical(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            source.write_text("SCENE 1 门口\n甲：别进来。\n乙：我只是想解释。", encoding="utf-8")
            result = route("generate", str(source))
        self.assertIn("references/prompt-performance-runtime.md", result["read_on_demand"])
        self.assertIn(
            "critical two-person performance turn",
            result["routing_reasons"]["references/prompt-performance-runtime.md"],
        )

    def test_scene_contract_adds_second_stage_specialists(self):
        contract = {
            "version": 1,
            "scene_id": "S1",
            "risk_vector": ["critical_performance_turn", "boundary"],
            "shots": [{
                "shot_id": "S1-01-1",
                "performance": {
                    "source_anchor": "甲拒绝乙",
                    "relationship_goal": "阻止靠近",
                    "speaker_actor": "甲",
                    "speaker_visible_fact": "甲按住门框",
                    "listener_actor": "乙",
                    "listener_trigger": "听到拒绝后",
                    "listener_visible_fact": "乙停在门外",
                    "end_residue": "甲仍按住门框",
                    "readability": "中近景看清手",
                    "camera_service": "甲肩后看清乙停步",
                },
                "visual_core": {
                    "first_focus": "按住门框的手",
                    "core_fact": "门框隔开两人",
                    "end_image": "两人隔门停住",
                },
                "spatial": {"blocking_id": "B1"},
                "protected_facts": ["甲屋内、乙门外"],
            }],
        }
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            source.write_text("SCENE 1 门口\n甲：别动。\n乙：好。", encoding="utf-8")
            result = route("generate", str(source), contract)
        self.assertIn("references/prompt-performance-runtime.md", result["read_on_demand"])
        self.assertIn("references/spatial-camera-runtime.md", result["read_on_demand"])
        self.assertIn("references/blocking-facing-reference.md", result["read_on_demand"])

    def test_concise_view_preserves_direct_prompt(self):
        source = "【镜号】\n1-1，4s，普通。\n\n【画面描述｜直接复制】\n原样提示词。\n\n【表演与声音】\n无台词。"
        self.assertEqual(extract(source), [("1-1，4s，普通。", "原样提示词。")])

    def test_output_template_is_compact_schema_not_a_second_runtime(self):
        template = (SKILL_ROOT / "references" / "output-template.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(template.splitlines()), 180)
        self.assertLessEqual(len(template.encode("utf-8")), 18000)
        self.assertIn("本文件只规定最终 Markdown 的结构、字段顺序和投喂边界", template)
        self.assertIn("普通镜不超过500字，复杂镜不超过650字", template)
        self.assertIn("只有复杂且成对关键帧保护的复合镜可到700字", template)
        self.assertIn("内部 IR、受保护载荷和回译结论不得输出", template)
        self.assertEqual(template.count("【本镜制作控制】"), 1)

    def test_performance_compiler_is_pre_prompt_and_round_trip_guarded(self):
        runtime = (SKILL_ROOT / "references" / "runtime-core.md").read_text(encoding="utf-8")
        performance = (SKILL_ROOT / "references" / "prompt-performance-rules.md").read_text(encoding="utf-8")
        review = (SKILL_ROOT / "references" / "review-pipeline.md").read_text(encoding="utf-8")
        for requirement in (
            "performance_ir",
            "source_anchor | relationship_goal | speaker_behavior | listener_response | end_residue | readability | camera_service",
            "受保护可见载荷",
            "前置语义门禁",
            "回译",
            "不增加输出字段",
        ):
            self.assertIn(requirement, runtime)
        self.assertIn("表演 IR 与前置编译门禁", performance)
        self.assertIn("关系意图 | 角色专属行为 | 触发与听者回应 | 句末残留 | 机位如何看清", performance)
        self.assertIn("隐藏候选来源、评分、导演上限合同与表演 IR", review)

    def test_compact_runtime_preserves_non_degradable_quality_contract(self):
        runtime = (SKILL_ROOT / "references" / "runtime-core.md").read_text(encoding="utf-8")
        for requirement in (
            "导演上限合同",
            "遮蔽候选来源",
            "不做平均化拼接",
            "表演候选先于机位设计",
            "台词意图 -> 对外策略 -> 身体真实倾向 -> 不受控泄露",
            "常态动作 -> 压力下变形 -> 峰值破例或坚持的代价 -> 结束残留",
            "触发者 -> 第一接收者 -> 延迟理解者 -> 试图控场者 -> 关系落幅",
            "不可降级视觉核心",
            "签名镜",
            "关系投影",
            "站位面向线稿",
            "身体面向",
            "完整视场",
            "触发 -> 接收 -> 可见处理 -> 选择/压住选择 -> 对手反应 -> 落幅",
            "遮挡、距离感、信息显露或关系压力",
            "最后20%稳定终态",
            "incremental_validate.py",
            "validate_storyboard.py",
            "设计审美复核始终强制",
            "任何字节变化使旧结论失效",
        ):
            self.assertIn(requirement, runtime)

    def test_skill_router_stays_compact_and_review_is_mandatory(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        review = (SKILL_ROOT / "references" / "review-pipeline.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(skill.splitlines()), 80)
        self.assertIn("review-pipeline.md", skill)
        for requirement in (
            "设计审查不可关闭",
            "隐藏候选来源",
            "visual_review=required",
            "scripts/review_video.py",
            "SHA-256",
            "field -> shot -> pair -> window -> scene",
            "非投喂",
        ):
            self.assertIn(requirement, review)

    def test_performance_creativity_stays_internal_and_is_reviewed(self):
        performance = (SKILL_ROOT / "references" / "prompt-performance-rules.md").read_text(encoding="utf-8")
        review = (SKILL_ROOT / "references" / "review-pipeline.md").read_text(encoding="utf-8")
        template = (SKILL_ROOT / "references" / "output-template.md").read_text(encoding="utf-8")
        for requirement in (
            "表演创意赛与行为弧线",
            "fast=2/balanced=3/director=4",
            "台词意图 -> 对外策略 -> 身体真实倾向 -> 不受控泄露",
            "不新增输出字段",
            "先锁定胜出的表演核心，再选构图、景别、机位、焦点和运镜",
            "一个窗口只有一个主要反应者",
        ):
            self.assertIn(requirement, performance)
        for failure in ("演法换名后可套给无关人物", "多人同时明显反应", "机位或运镜遮掉表演核心"):
            self.assertIn(failure, review)
        self.assertNotIn("【表演候选赛】", template)
        self.assertNotIn("【行为签名演变】", template)

    def test_ordinary_dialogue_core_adds_depth_without_context_or_field_cost(self):
        performance = (SKILL_ROOT / "references" / "prompt-performance-rules.md").read_text(encoding="utf-8")
        review = (SKILL_ROOT / "references" / "review-pipeline.md").read_text(encoding="utf-8")
        template = (SKILL_ROOT / "references" / "output-template.md").read_text(encoding="utf-8")
        for requirement in (
            "普通对白轻量内核",
            "不运行候选赛，也不新增输出字段",
            "角色专属行为载体",
            "唯一听者关系回应",
            "句末可继承残留",
            "开口前关系起态 -> 台词中的角色专属行为 -> 触发后的听者回应 -> 句末残留",
        ):
            self.assertIn(requirement, performance)
        for failure in ("普通对白只有台词和通用微表情", "听者反应不改变关系读取", "句末状态全部重置"):
            self.assertIn(failure, review)
        self.assertNotIn("【普通对白轻量内核】", template)


if __name__ == "__main__":
    unittest.main()
