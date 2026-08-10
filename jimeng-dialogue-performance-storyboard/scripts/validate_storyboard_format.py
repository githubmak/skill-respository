#!/usr/bin/env python3
"""Validate the fixed Jimeng dialogue storyboard Markdown contract."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


HEADER = r"- 镜头 \d{2}｜\d+(?:\.\d+)?s"
START_TYPES = r"场景起镜|动作接力|状态接力|反应接力|转场起镜"
STYLE_LOCK = (
    r"- 全局风格锁定\n"
    r"  - 用户指定风格：[^\r\n]+\n"
    r"  - 剧本推断补全：[^\r\n]*；推断依据：[^\r\n]+\n"
    r"  - 最终执行风格：[^\r\n]+"
)
GLOBAL_CARD = (
    r"- 全局色卡/影调/光影\n"
    r"  - 全局影调：[^\r\n]+\n"
    r"  - 全局色卡：[^\r\n]+\n"
    r"  - 全局光影：[^\r\n]+"
)
SEEDANCE_PROMPTS = (
    r"- Seedance 2\.5 专属提示词\n"
    r"  - 正向提示词：[^\r\n]+\n"
    r"  - 负向提示词：[^\r\n]+"
)
PERSON_ANCHOR_LINE = r"  - [^：\r\n]+：基准音色：[^；\r\n]+；基本性格锚点：[^\r\n]+"
PERSON_ANCHORS = rf"- 人物锚点\n{PERSON_ANCHOR_LINE}(?:\n{PERSON_ANCHOR_LINE})*"
EMPTY_TAIL_VALUES = {
    "无",
    "结束",
    "本段结束",
    "全场结束",
    "无后续镜",
    "没有后续镜",
    "无需承接",
    "无须承接",
    "无需尾帧",
    "无须尾帧",
}
BLOCK = (
    rf"{HEADER}\n"
    rf"  - 起始状态：(?:{START_TYPES})｜[^\r\n]+\n"
    r"  - 景别机位：[^\r\n]+\n"
    r"  - 构图/光影：[^\r\n]+\n"
    r"  - 画面/表演：[^\r\n]+\n"
    r"  - 运镜/焦点：[^\r\n]+\n"
    r"  - 特效：[^\r\n]+\n"
    r"  - 台词/音效：台词：[^\r\n]+；音效：[^\r\n]+\n"
    r"  - 尾帧：[^\r\n]+"
)
DOCUMENT = re.compile(
    rf"\A{STYLE_LOCK}\n\n{GLOBAL_CARD}\n\n{SEEDANCE_PROMPTS}\n\n"
    rf"{PERSON_ANCHORS}\n\n{BLOCK}(?:\n\n{BLOCK})*\n?\Z"
)
SHOT = re.compile(
    rf"(?P<header>{HEADER})\n"
    rf"  - 起始状态：(?P<start_type>{START_TYPES})｜(?P<start_state>[^\r\n]+)\n"
    r"  - 景别机位：(?P<shot_setup>[^\r\n]+)\n"
    r"  - 构图/光影：(?P<composition>[^\r\n]+)\n"
    r"  - 画面/表演：(?P<visual>[^\r\n]+)\n"
    r"  - 运镜/焦点：(?P<camera_focus>[^\r\n]+)\n"
    r"  - 特效：(?P<vfx>[^\r\n]+)\n"
    r"  - 台词/音效：台词：(?P<dialogue>[^\r\n]+)；音效：(?P<audio>[^\r\n]+)\n"
    r"  - 尾帧：(?P<tail>[^\r\n]+)"
)
RELATIVE_STATE = re.compile(
    r"上一镜|前一镜|下一镜|同上|沿用(?:上一镜|前一镜|此前)?|"
    r"继续(?:上一镜|前一镜)|保持此前状态|继承镜(?:号)?\s*\d+"
)
def validate(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not DOCUMENT.fullmatch(normalized):
        return [
            "正文未严格匹配固定对白列表模板：第一项必须是全局风格锁定，"
            "其下依次写用户指定风格、剧本推断补全、最终执行风格；第二项必须是全局色卡/影调/光影，"
            "其下依次写全局影调、全局色卡、全局光影；第三项必须是Seedance 2.5专属提示词，"
            "其下写正向提示词和负向提示词；第四项必须是人物锚点且每名主要人物同时写基准音色和基本性格锚点；每镜必须使用“- 镜头 NN｜时长s”，"
            "其下依次缩进列出起始状态、景别机位、构图/光影、画面/表演、运镜/焦点、特效、台词/音效、尾帧；最后一镜也必须有尾帧，禁止表格和平铺段落。"
        ]

    errors: list[str] = []
    numbers = [int(value) for value in re.findall(r"(?m)^- 镜头 (\d{2})｜", normalized)]
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        errors.append(f"镜头编号必须从01开始连续递增；当前为 {numbers}。")

    for shot_index, shot in enumerate(SHOT.finditer(normalized), start=1):
        start_type = shot.group("start_type")
        start_state = shot.group("start_state")
        tail = shot.group("tail")
        if shot_index == 1 and start_type not in {"场景起镜", "转场起镜"}:
            errors.append("镜头 01 的起始状态必须使用场景起镜或转场起镜。")
        if shot_index > 1 and start_type == "场景起镜":
            errors.append(
                f"镜头 {shot_index:02d} 不是全文首镜，不能使用场景起镜；新时空请使用转场起镜。"
            )
        if start_state.strip() == "无":
            errors.append(f"镜头 {shot_index:02d} 的起始状态不得写无。")
        if RELATIVE_STATE.search(start_state):
            errors.append(
                f"镜头 {shot_index:02d} 的起始状态使用空洞跨镜指代；请写具体可见起态。"
            )
        if shot.group("visual").strip() == "无":
            errors.append(f"镜头 {shot_index:02d} 的画面/表演不得写无。")
        if shot.group("camera_focus").strip() == "无":
            errors.append(f"镜头 {shot_index:02d} 的运镜/焦点不得写无。")
        tail_value = tail.strip().rstrip("。.!！")
        if tail_value in EMPTY_TAIL_VALUES:
            errors.append(
                f"镜头 {shot_index:02d} 的尾帧必须写具体终态，包括全场最后一镜；"
                "不得用无、结束、无后续镜或无需承接占位。"
            )
        if RELATIVE_STATE.search(tail):
            errors.append(
                f"镜头 {shot_index:02d} 的尾帧使用空洞跨镜指代；请写具体终态。"
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
