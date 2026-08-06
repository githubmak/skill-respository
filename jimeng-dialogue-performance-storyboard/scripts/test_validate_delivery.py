#!/usr/bin/env python3
"""Tests for deterministic-only delivery validation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from review_manifest import build_manifest, write_manifest
from validate_delivery import sha256_file, validate_delivery


SOURCE = """8-1
场景：夜 内 堂屋
人物：满满 阿丰 沈青乔
阿丰：娘亲，这粥好像……和以前吃的不一样。
沈青乔（OS）：饥荒几年，俩孩子怕是糙米都没吃上几口，更别说精米。
"""


def storyboard(source: Path, *, target: str = "auto", status: str = "DRAFT", audio: str | None = None,
               reference: str = "无", prompt_tail: str = "") -> str:
    audio = audio if audio is not None else (
        "阿丰：娘亲，这粥好像……和以前吃的不一样。\n"
        "沈青乔（OS）：饥荒几年，俩孩子怕是糙米都没吃上几口，更别说精米。"
    )
    return f"""# 第8集｜即梦 Seedance 分镜

## 项目信息
- Seedance 目标：{target}
- 画幅与风格：16:9，任意模型创作风格
- 源文 SHA-256：{sha256_file(source)}
- 交付状态：{status}

## 全局连续性
模型自由创作。

## 场景导演方案
### S1｜堂屋
- 戏剧与表演方向：模型判断。
- 摄影机与剪辑方向：模型判断。
- 光影与色卡：模型判断。

## 分镜投喂卡

#### S1-01｜吃粥

【时长】
12s

【出现人物】
阿丰、沈青乔

【Seedance 直投提示】
起始画面：由模型自由决定，没有强制运镜或情绪关键词。
表演时序：阿丰说完原文后闭口，随后沈青乔的OS进入。
摄影机：摄影机保持静止，因为模型选择了静止。
焦点：焦点由模型选择并保持。
色卡：由模型为本镜独立设计主色、辅助色与点缀色。
影调：由模型为本镜独立设计对比度、饱和度、亮暗层级与肤色基准。
光影：由模型为本镜独立设计真实光源、方向、受光面、阴影与材质响应。
声音：阿丰可见口型说：“娘亲，这粥好像……和以前吃的不一样。”沈青乔OS为：“饥荒几年，俩孩子怕是糙米都没吃上几口，更别说精米。”
结束画面：由模型选定的画面稳定保持。{prompt_tail}

【声音原文】
{audio}

【审核后参考素材】
{reference}
"""


class ValidateDeliveryTests(unittest.TestCase):
    def test_passes_without_creative_keywords_scores_or_camera_quota(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            source = base / "source.txt"
            output = base / "storyboard.md"
            source.write_text(SOURCE, encoding="utf-8")
            output.write_text(storyboard(source), encoding="utf-8")
            result = validate_delivery(source, [output], "auto")
        self.assertTrue(result["pass"], result["issues"])
        self.assertFalse(result["creative_decisions_evaluated"])

    def test_audio_must_be_verbatim_complete_and_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            source = base / "source.txt"
            output = base / "storyboard.md"
            source.write_text(SOURCE, encoding="utf-8")
            output.write_text(storyboard(source, audio="阿丰：娘亲，这粥好像和以前吃的不一样。"), encoding="utf-8")
            result = validate_delivery(source, [output], "auto")
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("AUDIO_MISSING", codes)
        self.assertIn("AUDIO_EXTRA", codes)

    def test_audio_body_must_exist_inside_copy_ready_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            source = base / "source.txt"
            output = base / "storyboard.md"
            source.write_text(SOURCE, encoding="utf-8")
            text = storyboard(source).replace(
                "娘亲，这粥好像……和以前吃的不一样。",
                "本句故意从直投提示删除",
                1,
            )
            output.write_text(text, encoding="utf-8")
            result = validate_delivery(source, [output], "auto")
        self.assertIn("AUDIO_NOT_IN_PROMPT", {item["code"] for item in result["issues"]})

    def test_staging_and_svg_cannot_enter_seedance_reference_field(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            source = base / "source.txt"
            staging = base / "staging" / "blocking"
            staging.mkdir(parents=True)
            svg = staging / "S1-01.svg"
            svg.write_text("<svg/>", encoding="utf-8")
            output = base / "storyboard.md"
            source.write_text(SOURCE, encoding="utf-8")
            output.write_text(storyboard(source, reference=str(svg)), encoding="utf-8")
            result = validate_delivery(source, [output], "auto")
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("REFERENCE_ROLE", codes)
        self.assertIn("STAGING_REFERENCE", codes)

    def test_hard_prompt_limit_is_engineering_only(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            source = base / "source.txt"
            output = base / "storyboard.md"
            source.write_text(SOURCE, encoding="utf-8")
            output.write_text(storyboard(source, prompt_tail="画" * 701), encoding="utf-8")
            result = validate_delivery(source, [output], "auto")
        self.assertIn("PROMPT_HARD_LIMIT", {item["code"] for item in result["issues"]})

    def test_final_requires_current_final_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            reports = base / "reports"
            reports.mkdir()
            source = base / "source.txt"
            output = base / "storyboard.md"
            source.write_text(SOURCE, encoding="utf-8")
            output.write_text(storyboard(source, status="FINAL"), encoding="utf-8")
            manifest = reports / "manifest.json"
            payload = build_manifest(source, [output], "self_check", "PASS", "PASS", delivery_root=base)
            write_manifest(manifest, payload)
            result = validate_delivery(source, [output], "auto", final=True, review_manifest=manifest)
        self.assertTrue(result["pass"], result["issues"])

    def test_both_versions_share_shots_durations_and_audio(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            source = base / "source.txt"
            v20 = base / "v20.md"
            v25 = base / "v25.md"
            source.write_text(SOURCE, encoding="utf-8")
            v20.write_text(storyboard(source, target="2.0"), encoding="utf-8")
            v25.write_text(storyboard(source, target="2.5"), encoding="utf-8")
            result = validate_delivery(source, [v20, v25], "both")
        self.assertTrue(result["pass"], result["issues"])


if __name__ == "__main__":
    unittest.main()
