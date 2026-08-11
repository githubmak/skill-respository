#!/usr/bin/env python3
"""Regression tests for previously fixed storyboard skill failure modes."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR_PATH = SKILL_ROOT / "scripts" / "validate_storyboard_format.py"
SPEC = importlib.util.spec_from_file_location("storyboard_validator", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator: {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


PREFIX = """- 全局风格锁定
  - 用户指定风格：电影写实
  - 剧本推断补全：现代都市；推断依据：室内对白
  - 最终执行风格：现代都市电影写实

- 全局色卡/影调/光影
  - 全局影调：克制
  - 全局色卡：冷白墙面，明黄服装
  - 全局光影：窗光从右侧进入

- Seedance 2.5 专属提示词
  - 正向提示词：人物动作连续，道具状态稳定
  - 负向提示词：禁止穿墙穿物和无因换手

- 人物锚点
  - 宋棠：基准音色：年轻女声；基本性格锚点：窘迫但维持体面
  - 陆夫人：基准音色：沉稳女声；基本性格锚点：从容掌握节奏

- 场景 01｜客厅
  - 场景影调：冷静
  - 场景色卡：冷白与明黄
  - 场景光影：右侧窗光"""


def shot(
    number: int,
    start_state: str,
    visual: str,
    tail: str,
    *,
    start_type: str = "状态接力",
    duration: int = 4,
    setup: str = "宋棠中景，平视，摄影机位于茶几外侧",
    composition: str = "构图：宋棠位于画面右侧；光影：右侧窗光照亮宋棠",
    camera: str = "镜头固定在宋棠中景，焦点落在宋棠面部",
    audio: str = "无",
) -> str:
    return f"""- 镜头 {number:02d}｜{duration}s
  - 起始状态：{start_type}｜{start_state}
  - 景别机位：{setup}
  - 构图/光影：{composition}
  - 画面/表演：{visual}
  - 运镜/焦点：{camera}
  - 特效：无
  - 台词/音效：台词：无；音效：{audio}
  - 尾帧：{tail}"""


def document(*shots: str) -> str:
    return "\n\n".join((PREFIX, *shots))


def opening_shot() -> str:
    return shot(
        1,
        "宋棠站在茶几外侧，茶杯留在杯碟上",
        "宋棠站定，茶杯保持在杯碟上",
        "宋棠站在茶几外侧，茶杯仍在杯碟上",
        start_type="场景起镜",
    )


class SkillSourceBaselineTests(unittest.TestCase):
    def test_core_rules_remain_in_skill_source(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        required_markers = (
            "至少比较两套非同构摄影候选",
            "每个拟切点必须至少满足一项",
            "源文已经写出“眼眶发红",
            "每镜先锁定拍摄主体归属",
            "画外只描述具名人物",
            "原文每一个明确【转场】",
            "逐场维护实体与道具连续性账本",
            "允许连续三个不超过 3 秒的短镜",
            "禁止用同一中景/中近景加短促推进覆盖 10 秒以上关键反转",
            "禁止在同一镜内连续写 A -> B -> C",
            "环绕运镜只改变摄影机围绕主体的路径与观察方向",
            "导演直觉首稿",
            "L0-L3、道具账本、连续性与生成负载是后置护栏",
            "不可替代的视觉句",
        )
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, skill_text)

    def test_non_regression_reference_is_mandatory(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/non-regression-baseline.md", skill_text)
        self.assertIn("references/beat-shot-mode-decision.md", skill_text)
        baseline = (SKILL_ROOT / "references" / "non-regression-baseline.md")
        self.assertTrue(baseline.is_file())
        decision = (SKILL_ROOT / "references" / "beat-shot-mode-decision.md")
        self.assertTrue(decision.is_file())

    def test_director_first_pass_precedes_governance(self) -> None:
        previs = (
            SKILL_ROOT / "references" / "one-pass-director-previsualization.md"
        ).read_text(encoding="utf-8")
        decision = (
            SKILL_ROOT / "references" / "beat-shot-mode-decision.md"
        ).read_text(encoding="utf-8")
        baseline = (
            SKILL_ROOT / "references" / "non-regression-baseline.md"
        ).read_text(encoding="utf-8")

        for marker in (
            "最强起幅是什么",
            "唯一主要拍摄主体是谁",
            "摄影机的一个主视觉动词是什么",
            "与相邻镜头形成哪一种主要反差",
            "不惯性保留另一人物肩部",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, previs)

        self.assertIn("本参考在导演直觉首稿之后使用", decision)
        self.assertIn("分类不是审美配额", decision)
        self.assertIn("导演视觉首稿先于治理规则", baseline)


class ValidatorRegressionTests(unittest.TestCase):
    def test_single_shot_size_without_fixed_prop_position_is_valid(self) -> None:
        text = document(
            shot(
                1,
                "宋棠站在客厅中央",
                "宋棠抬头看向前方",
                "宋棠保持站姿",
                start_type="场景起镜",
                setup="宋棠中近景，低机位仰拍",
                camera="镜头缓慢向前推进，保持宋棠中近景",
            )
        )
        self.assertEqual([], VALIDATOR.validate(text))

    def test_direct_full_to_closeup_shorthand_is_valid(self) -> None:
        text = document(
            shot(
                1,
                "宋棠站在客厅中央",
                "宋棠抬眼，注意力落向前方",
                "宋棠眼睛停在画面中央",
                start_type="场景起镜",
                setup="宋棠全景转眼部特写，低机位正面",
                camera="从宋棠全身缓慢下摇，最后停在宋棠眼睛",
            )
        )
        framing_errors = [
            error for error in VALIDATOR.validate(text)
            if "景别" in error or "起终幅" in error
        ]
        self.assertEqual([], framing_errors)

    def test_three_shot_sizes_in_one_shot_are_blocked(self) -> None:
        text = document(
            shot(
                1,
                "宋棠站在客厅中央",
                "宋棠向前迈步并抬眼",
                "宋棠眼睛停在画面中央",
                start_type="场景起镜",
                setup="宋棠全景转中景再转眼部特写，低机位正面",
                camera="镜头从宋棠全身推进到上半身，再停在宋棠眼睛",
            )
        )
        self.assertTrue(
            any("出现多个连续景别" in error for error in VALIDATOR.validate(text))
        )

    def test_orbit_changes_direction_not_shot_size(self) -> None:
        text = document(
            shot(
                1,
                "宋棠站在客厅中央",
                "宋棠保持身体朝向，陆夫人留在她对面",
                "宋棠仍处于中景，摄影机停在侧后方",
                start_type="场景起镜",
                setup="宋棠中景，平视正面",
                camera="保持宋棠中景，从正面环绕到侧后方后停止",
            )
        )
        self.assertEqual([], VALIDATOR.validate(text))

    def test_default_cli_does_not_emit_creative_review(self) -> None:
        shots = [
            shot(
                number,
                "宋棠站在茶几外侧",
                "宋棠看向陆夫人并维持站姿",
                "宋棠仍站在茶几外侧",
                start_type="场景起镜" if number == 1 else "状态接力",
                duration=5,
                camera="镜头固定并缓慢平稳推进，焦点落在宋棠面部",
            )
            for number in range(1, 11)
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "storyboard.md"
            path.write_text(document(*shots), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(VALIDATOR_PATH), str(path)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("REVIEW:", result.stdout)

    def test_creative_review_cli_is_explicit_opt_in(self) -> None:
        shots = [
            shot(
                number,
                "宋棠站在茶几外侧",
                "宋棠看向陆夫人并维持站姿",
                "宋棠仍站在茶几外侧",
                start_type="场景起镜" if number == 1 else "状态接力",
                duration=5,
                camera="镜头固定并缓慢平稳推进，焦点落在宋棠面部",
            )
            for number in range(1, 11)
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "storyboard.md"
            path.write_text(document(*shots), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(VALIDATOR_PATH), str(path), "--creative-review"],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("REVIEW:", result.stdout)

    def test_ambiguous_body_closeup_is_blocked(self) -> None:
        text = document(
            shot(
                1,
                "宋棠站在茶几外侧",
                "宋棠收紧鞋尖",
                "鞋面停在画面中央",
                start_type="场景起镜",
                setup="鞋面局部特写，低机位正面",
            )
        )
        self.assertTrue(any("没有写明人物归属" in error for error in VALIDATOR.validate(text)))

    def test_variable_framing_requires_named_start_and_end(self) -> None:
        text = document(
            shot(
                1,
                "宋棠站在茶几外侧",
                "宋棠抬起头",
                "宋棠面部停在画面中",
                start_type="场景起镜",
                camera="从宋棠手部上移，最终定格宋棠面部",
            )
        )
        self.assertTrue(any("唯一的具名起终幅" in error for error in VALIDATOR.validate(text)))

    def test_offscreen_gaze_is_blocked(self) -> None:
        text = document(
            shot(
                1,
                "宋棠站在茶几外侧",
                "陆夫人的打量落在画外，宋棠抬起头",
                "宋棠面部停在画面中",
                start_type="场景起镜",
            )
        )
        self.assertTrue(any("画外可见物" in error for error in VALIDATOR.validate(text)))

    def test_tail_cannot_keep_regions_outside_terminal_closeup(self) -> None:
        text = document(
            shot(
                1,
                "宋棠站在茶几外侧",
                "宋棠维持站姿",
                "宋棠鞋面和兔耳帽同时留在画面中",
                start_type="场景起镜",
                setup="宋棠鞋面局部特写起幅，低机位正面；终幅为宋棠兔耳帽特写",
                camera="从宋棠鞋面上移，最终定格宋棠兔耳帽",
            )
        )
        self.assertTrue(
            any("终点特写与尾帧可见范围冲突" in error for error in VALIDATOR.validate(text))
        )

    def test_prop_cannot_first_appear_in_later_start_state(self) -> None:
        text = document(
            opening_shot(),
            shot(
                2,
                "宋棠右手压住亮起的手机衣袋",
                "宋棠维持站姿",
                "宋棠右手仍压住手机衣袋",
            ),
        )
        self.assertTrue(any("首次出现道具“手机”" in error for error in VALIDATOR.validate(text)))

    def test_prop_introduction_requires_causal_entry(self) -> None:
        text = document(
            opening_shot(),
            shot(
                2,
                "宋棠双手垂在身侧",
                "宋棠低头查看手机屏幕",
                "手机握在宋棠右手中，亮起的屏幕朝向她",
            ),
        )
        self.assertTrue(
            any("没有识别到" in error and "手机" in error for error in VALIDATOR.validate(text))
        )

    def test_prop_change_requires_tail_settlement(self) -> None:
        text = document(
            opening_shot(),
            shot(
                2,
                "宋棠双手垂在身侧",
                "订单提示音响起，宋棠侧袋震动，她从侧袋拿出手机",
                "宋棠低头维持沉默",
                audio="订单提示音",
            ),
        )
        self.assertTrue(any("改变了道具“手机”" in error for error in VALIDATOR.validate(text)))

    def test_prop_state_cannot_jump_between_cuts(self) -> None:
        text = document(
            opening_shot(),
            shot(
                2,
                "宋棠双手垂在身侧",
                "订单提示音响起，宋棠侧袋震动，她发现后伸手压住侧袋",
                "宋棠右手压在仍震动的侧袋，手机没有拿出",
                audio="订单提示音，侧袋持续震动",
            ),
            shot(
                3,
                "宋棠右手拿着手机，亮起的屏幕朝向她",
                "宋棠低头查看屏幕",
                "手机仍握在宋棠右手中，亮起的屏幕朝向她",
            ),
        )
        self.assertTrue(
            any("最终状态冲突" in error and "手机" in error for error in VALIDATOR.validate(text))
        )

    def test_valid_prop_chain_passes(self) -> None:
        text = document(
            opening_shot(),
            shot(
                2,
                "宋棠双手垂在身侧",
                "订单提示音响起，宋棠侧袋震动，她发现后伸手压住侧袋",
                "宋棠右手压在仍震动的侧袋，手机没有拿出",
                audio="订单提示音，侧袋持续震动",
            ),
            shot(
                3,
                "宋棠右手压在仍震动的侧袋，手机没有拿出",
                "宋棠从侧袋拿出手机，屏幕朝向自己",
                "手机握在宋棠右手中，亮起的屏幕朝向她",
                start_type="动作接力",
            ),
        )
        phone_errors = [error for error in VALIDATOR.validate(text) if "手机" in error]
        self.assertEqual([], phone_errors)

    def test_strong_emotion_restatement_warns(self) -> None:
        text = document(
            shot(
                1,
                "宋棠站在门边",
                "宋棠眼眶发红，仍站在原地",
                "宋棠眼眶发红地站着",
                start_type="场景起镜",
            )
        )
        warnings = VALIDATOR.conservatism_warnings(text, "宋棠眼眶发红。")
        self.assertTrue(any("复用了源文强情绪结果" in warning for warning in warnings))

    def test_explicit_transition_without_bridge_warns(self) -> None:
        text = document(
            shot(
                1,
                "宋棠站在客厅内",
                "宋棠维持站姿",
                "宋棠站在客厅内",
                start_type="场景起镜",
            )
        )
        warnings = VALIDATOR.conservatism_warnings(text, "【转场】\n陆家别墅外。")
        self.assertTrue(any("明确【转场】" in warning for warning in warnings))

    def test_fragmented_short_shots_warn(self) -> None:
        shots = [
            shot(
                number,
                "宋棠站在茶几外侧",
                "宋棠看向陆夫人并停顿",
                "宋棠仍站在茶几外侧",
                start_type="场景起镜" if number == 1 else "状态接力",
                duration=3,
            )
            for number in range(1, 9)
        ]
        warnings = VALIDATOR.conservatism_warnings(document(*shots))
        self.assertTrue(any("对白表演可能被切得过碎" in warning for warning in warnings))

    def test_three_short_shots_with_roles_are_not_auto_rejected(self) -> None:
        shots = [
            shot(
                1,
                "宋棠站在茶几外侧",
                "订单提示音突然响起，侧袋震动",
                "宋棠侧袋仍在震动",
                start_type="场景起镜",
                duration=3,
                setup="宋棠侧袋局部特写，平视侧面，摄影机位于茶几外侧",
                camera="镜头快速靠近宋棠侧袋并立即停止",
                audio="订单提示音",
            ),
            shot(
                2,
                "宋棠侧袋仍在震动",
                "宋棠的乖巧控制断裂，手掌压住侧袋",
                "宋棠手掌压住仍震动的侧袋，手机没有拿出",
                duration=3,
                setup="宋棠手部局部特写，平视侧面，摄影机位于茶几外侧",
                camera="镜头跟随宋棠手掌快速下移，压住侧袋时急停",
                audio="袋内震动声",
            ),
            shot(
                3,
                "宋棠手掌压住仍震动的侧袋，手机没有拿出",
                "宋棠从茶几边缘退回外侧，重新遮住窘迫",
                "宋棠站回茶几外侧，手仍压住袋内手机",
                duration=3,
                setup="宋棠与陆夫人双人全景，斜俯侧面，摄影机位于茶几上方",
                camera="斜俯全景随宋棠退回方向拉开，她站定时停止",
            ),
            *[
                shot(
                    number,
                    "宋棠站在茶几外侧，手压住袋内手机",
                    "宋棠维持现实动作并完成对白",
                    "宋棠仍站在茶几外侧，手机留在侧袋内",
                    duration=6,
                )
                for number in range(4, 8)
            ],
        ]
        warnings = VALIDATOR.conservatism_warnings(document(*shots))
        self.assertFalse(any("连续至少四个不超过3秒" in warning for warning in warnings))

    def test_long_same_range_critical_shot_warns(self) -> None:
        shots = [
            shot(
                1,
                "宋棠俯身靠近茶几维持乖巧策略",
                "超时提示音突然命中，宋棠的乖巧控制失效，侧袋震动，她伸手压住手机",
                "宋棠手仍压住袋内手机",
                start_type="场景起镜",
                duration=14,
                setup="宋棠中近景，平视正面，摄影机位于陆夫人身侧",
                camera="摄影机从宋棠中近景短促靠近，在她压住侧袋时立即停止",
                audio="超时提示音，袋内震动声",
            ),
            *[
                shot(
                    number,
                    "宋棠站在茶几外侧",
                    "宋棠维持现实动作",
                    "宋棠仍站在茶几外侧",
                    duration=6,
                )
                for number in range(2, 7)
            ],
        ]
        warnings = VALIDATOR.conservatism_warnings(document(*shots))
        self.assertTrue(any("关键刺激被困在同一中景" in warning for warning in warnings))
        self.assertEqual([], VALIDATOR.validate(document(*shots)))

    def test_long_stable_narrative_shot_is_not_mislabeled_critical(self) -> None:
        shots = [
            shot(
                1,
                "宋棠站在茶几外侧听陆夫人说明条件",
                "陆夫人完整说明工作时间，宋棠维持站姿并听完",
                "宋棠仍站在茶几外侧，陆夫人保持原位",
                start_type="场景起镜",
                duration=14,
                setup="宋棠与陆夫人双人中景，平视侧面，摄影机位于茶几边缘",
                camera="摄影机固定在双人中景，焦点保持在正在说话的陆夫人",
            ),
            *[
                shot(
                    number,
                    "宋棠站在茶几外侧",
                    "宋棠维持现实动作",
                    "宋棠仍站在茶几外侧",
                    duration=6,
                )
                for number in range(2, 7)
            ],
        ]
        warnings = VALIDATOR.conservatism_warnings(document(*shots))
        self.assertFalse(any("关键刺激被困在同一中景" in warning for warning in warnings))

    def test_conservative_camera_curve_warns(self) -> None:
        shots = [
            shot(
                number,
                "宋棠站在茶几外侧",
                "宋棠看向陆夫人并维持站姿",
                "宋棠仍站在茶几外侧",
                start_type="场景起镜" if number == 1 else "状态接力",
                duration=5,
                camera="镜头固定并缓慢平稳推进，焦点落在宋棠面部",
            )
            for number in range(1, 11)
        ]
        warnings = VALIDATOR.conservatism_warnings(document(*shots))
        self.assertTrue(any("固定、缓慢或平稳运镜占比较高" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main(verbosity=2)
