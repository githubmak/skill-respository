#!/usr/bin/env python3
"""Validate the deterministic Seedance storyboard delivery contract."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


HEADER = r"镜号 \d{2}｜[^｜\r\n]+｜[^｜\r\n]+｜\d+(?:\.\d+)?s"
BLOCK = (
    rf"{HEADER}\n\n"
    r"画面内容：[^\r\n]+\n\n"
    r"特效：[^\r\n]+\n\n"
    r"光影：[^\r\n]+\n\n"
    r"音效：[^\r\n]+\n\n"
    r"台词：[^\r\n]+"
)
DOCUMENT = re.compile(rf"\A{BLOCK}(?:\n\n{BLOCK})*\n?\Z")
SHOT = re.compile(
    rf"(?P<header>{HEADER})\n\n"
    r"画面内容：(?P<visual>[^\r\n]+)\n\n"
    r"特效：(?P<vfx>[^\r\n]+)\n\n"
    r"光影：(?P<light>[^\r\n]+)\n\n"
    r"音效：(?P<audio>[^\r\n]+)\n\n"
    r"台词：(?P<dialogue>[^\r\n]+)"
)
RELATIVE_STATE = re.compile(
    r"继承镜(?:号)?\s*\d+|镜(?:号)?\s*\d+状态|前镜|前一镜|上一镜|下一镜|"
    r"同上|沿用(?:前镜|上一镜|此前)?|继续上一镜|保持此前状态"
)
INTERNAL_MARKER = re.compile(
    r"(?<![A-Za-z0-9])P\d+(?![A-Za-z0-9])|(?<![A-Za-z0-9])K\d+(?![A-Za-z0-9])|"
    r"(?<![A-Za-z0-9])CAM(?:ERA)?(?![A-Za-z0-9])|剧本保真矩阵|原文证据|"
    r"负面提示词|负面约束|风险分数"
)


def validate(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    errors: list[str] = []
    if not DOCUMENT.fullmatch(normalized):
        errors.append(
            "正文未严格匹配固定格式：镜头标题后依次为画面内容、特效、光影、音效、台词，字段间一个空行。"
        )
        return errors

    numbers = [int(value) for value in re.findall(r"(?m)^镜号 (\d{2})｜", normalized)]
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        errors.append(f"镜号必须从01开始连续递增；当前为 {numbers}。")

    durations = [
        float(value)
        for value in re.findall(
            r"(?m)^镜号 \d{2}｜[^｜\r\n]+｜[^｜\r\n]+｜(\d+(?:\.\d+)?)s$",
            normalized,
        )
    ]
    segment_duration = sum(durations)
    if segment_duration > 30.0 + 1e-9:
        errors.append(
            f"镜头时长之和为{segment_duration:g}秒，超过单个生成段30秒硬上限；"
            "请在自然因果接缝拆段，不得删改剧情或强行加速。"
        )

    for shot_index, match in enumerate(SHOT.finditer(normalized), start=1):
        body = " ".join(
            match.group(name)
            for name in ("visual", "vfx", "light", "audio", "dialogue")
        )
        reference = RELATIVE_STATE.search(body)
        if reference:
            errors.append(
                f"镜号 {shot_index:02d} 使用跨镜替代语“{reference.group(0)}”；"
                "请重述本镜生成所需的具体可见状态。"
            )

        internal = INTERNAL_MARKER.search(body)
        if internal:
            errors.append(
                f"镜号 {shot_index:02d} 含内部标记“{internal.group(0)}”；"
                "最终正文只能保留可见画面、动作、特效、光影、声音和台词。"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    try:
        text = args.path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        print(f"cannot read {args.path}: {exc}", file=sys.stderr)
        return 2

    errors = validate(text)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"format valid: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
