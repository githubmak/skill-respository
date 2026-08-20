#!/usr/bin/env python3
"""Regression tests for the streamlined storyboard skill architecture."""

from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = SKILL_ROOT / "SKILL.md"
CONTRACT_PATH = SKILL_ROOT / "references" / "production-contract.md"
VALIDATOR_PATH = SKILL_ROOT / "scripts" / "validate_seedance_delivery.py"

SPEC = importlib.util.spec_from_file_location("seedance_delivery_validator", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator: {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class StreamlinedSkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = SKILL_PATH.read_text(encoding="utf-8")
        cls.contract = CONTRACT_PATH.read_text(encoding="utf-8")

    def test_entrypoint_is_small_and_discriminating(self) -> None:
        self.assertLessEqual(len(self.skill.splitlines()), 120)
        self.assertIn("name: jimeng-dialogue-performance-storyboard", self.skill)
        self.assertIn("即梦 Seedance AI 漫剧/短剧分镜", self.skill)

    def test_runtime_delays_delivery_contract_until_blueprint_freeze(self) -> None:
        self.assertIn("蓝图冻结前只使用本文件", self.skill)
        self.assertIn("references/production-contract.md", self.skill)
        self.assertIn("冻结后需要正式交付时，再完整读取生产合同", self.skill)
        self.assertIn("不预填交付字段", self.skill)
        self.assertLessEqual(len(self.contract.splitlines()), 190)

    def test_single_source_compile_is_stable_but_allows_evidence_based_reopening(self) -> None:
        combined = f"{self.skill}\n{self.contract}"
        for marker in (
            "编译不无因重新选择镜头",
            "不限于硬错误",
            "具体创作失败",
            "局部重开",
            "栏目编译映射",
            "审核必须指出具体失败",
            "没有实际失败时，不得改写已冻结的长镜头、留白、静止、特殊机位",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

    def test_all_linked_references_exist(self) -> None:
        links = re.findall(r"\[[^]]+\]\((references/[^)]+)\)", self.skill)
        self.assertGreaterEqual(len(links), 10)
        for relative in links:
            with self.subTest(reference=relative):
                self.assertTrue((SKILL_ROOT / relative).is_file())

    def test_facts_and_dialogue_are_protected(self) -> None:
        for marker in (
            "不改人物、身份、性格、关系、知情、事件顺序、因果",
            "台词、OS、OV 默认逐字、逐句、按原归属和顺序保留",
            "不删减、合并、润色、证据化增强或替换措辞",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.skill)

    def test_performance_cannot_be_flattened(self) -> None:
        combined = f"{self.skill}\n{self.contract}"
        for marker in (
            "情绪不能压成",
            "刺激进入 -> 确认或误判 -> 第一冲动",
            "说前刺激/准备 -> 台词开始 -> 关键词或语义转折",
            "停止或保持状态",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

    def test_performance_emotion_and_dialogue_tone_share_one_source(self) -> None:
        combined = f"{self.skill}\n{self.contract}"
        for marker in (
            "外在策略与内在压力",
            "旧情绪残留",
            "该句在当下要完成的现实作用",
            "开口基线 -> 关键词/语义转折 -> 话落状态",
            "标点只提供语法边界",
            "不以微动作数量为准",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

    def test_camera_and_physics_are_executable(self) -> None:
        combined = f"{self.skill}\n{self.contract}"
        for marker in (
            "摄影机不得穿墙、穿物或从不可达区域拍摄",
            "起幅、运动中和终幅分别检查",
            "保持一条可追踪路径",
            "重力、支撑、接触、受力、惯性和终点保持",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

    def test_scene_assets_are_required_without_overhead_map(self) -> None:
        combined = f"{self.skill}\n{self.contract}"
        self.assertIn("不含人物的场景资产图提示词", combined)
        self.assertIn("正向提示词", combined)
        self.assertIn("负向约束", combined)
        self.assertIn("关键道具资产提示词", combined)
        self.assertIn("导演审核版与 Seedance 直投版每场都独立输出", combined)
        self.assertIn("不输出俯视调度图", combined)

    def test_model_semantic_review_replaces_external_runtime_validation(self) -> None:
        combined = f"{self.skill}\n{self.contract}"
        self.assertIn("正常工作流不调用外部技能、代理或脚本校验器", combined)
        self.assertIn("模型语义复审", combined)
        self.assertIn("不能用关键词命中代替导演判断", combined)

    def test_optional_references_have_explicit_triggers(self) -> None:
        for trigger in (
            "复杂心理反转、多人对白传播",
            "时长竞争或高负载长镜",
            "重动作、打斗、VFX、蒙太奇或特殊剪辑",
            "关键道具换手、开合、显隐、破损或控制权变化",
            "原文明确标注转场",
        ):
            with self.subTest(trigger=trigger):
                self.assertIn(trigger, self.skill)

    def test_maintenance_references_are_not_default_runtime(self) -> None:
        self.assertIn("仅用于修改技能和回归检查", self.skill)
        self.assertIn("普通生成不读取这两个文件", self.skill)

    def test_direct_and_director_schemas_remain_complete(self) -> None:
        for marker in (
            "# 作品名｜导演审核版",
            "### 场景资产图提示词",
            "# 作品名｜Seedance独立直投版",
            "## 【全局摄影规则】",
            "## 【场景空间位置关系】",
            "**画面与表演时间线**",
            "**台词与声音层次**",
            "**落幅状态**",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.contract)

    def test_direct_schema_uses_complete_merged_execution_fields(self) -> None:
        self.assertIn("**起幅与连续性**", self.contract)
        self.assertIn("**光影、环境色彩与材质**", self.contract)
        self.assertIn("第一帧完整执行快照", self.contract)
        self.assertIn("本镜完整执行快照", self.contract)
        for retired in (
            "**本镜环境色彩**",
            "**当前资产与连续性**",
            "**起幅状态**",
            "**光影/色彩/材质**",
        ):
            with self.subTest(retired=retired):
                self.assertNotIn(retired, self.contract)

    def test_fixed_templates_match_validator(self) -> None:
        for template in (
            VALIDATOR.IDENTITY_TEMPLATE,
            VALIDATOR.CG3D_TEMPLATE,
            VALIDATOR.FACE_NEGATIVE_TEMPLATE,
            VALIDATOR.CG3D_NEGATIVE,
        ):
            with self.subTest(template=template[:20]):
                self.assertEqual(1, self.contract.count(template))

    def test_identity_template_locks_identity_without_freezing_performance(self) -> None:
        self.assertIn("表情肌肉、眼球视线、眼睑、嘴唇、下颌、头颈姿态与呼吸按剧情自然联动", VALIDATOR.IDENTITY_TEMPLATE)
        self.assertIn("不得改变人物身份、五官基础比例", VALIDATOR.IDENTITY_TEMPLATE)
        self.assertNotIn("仅面部肌肉做表情运动", VALIDATOR.IDENTITY_TEMPLATE)
        self.assertNotIn("只改变表情肌肉", VALIDATOR.IDENTITY_TEMPLATE)

    def test_shot_specific_constraints_are_optional_and_risk_triggered(self) -> None:
        self.assertIn("仅有本镜新增风险时保留", self.contract)
        self.assertIn("不存在的 OS、OV、BGM、特效或特殊约束删除整项", self.contract)

    def test_runtime_contract_keeps_direct_output_clean(self) -> None:
        for marker in (
            "时间线第一行从 `0.0秒` 开始",
            "相邻时间窗首尾相接",
            "直投版禁止原句对照",
            "沿用上一镜/同上",
            "不存在的 OS、OV、BGM、特效或特殊约束删除整项",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.contract)


if __name__ == "__main__":
    unittest.main(verbosity=2)
