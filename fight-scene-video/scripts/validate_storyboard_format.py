#!/usr/bin/env python3
"""Validate the deterministic Seedance storyboard delivery contract."""

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
SCENE_CARD = (
    r"- 场景 \d{2}｜[^\r\n]+\n"
    r"  - 场景影调：[^\r\n]+\n"
    r"  - 场景色卡：[^\r\n]+\n"
    r"  - 场景光影：[^\r\n]+"
)
GLOBAL_PREFIX = re.compile(
    rf"\A{STYLE_LOCK}\n\n{GLOBAL_CARD}\n\n{SEEDANCE_PROMPTS}\n\n"
)
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
SEGMENT_HEADER = r"生成段 \d{2}｜[^｜\r\n]+｜\d+(?:\.\d+)?s"
SEGMENT = rf"{SEGMENT_HEADER}\n\n{BLOCK}(?:\n\n{BLOCK})*"
SCENE_SECTION = rf"{SCENE_CARD}\n\n(?:{SEGMENT}(?:\n\n{SEGMENT})*|{BLOCK}(?:\n\n{BLOCK})*)"
DOCUMENT = re.compile(
    rf"\A{STYLE_LOCK}\n\n{GLOBAL_CARD}\n\n{SEEDANCE_PROMPTS}\n\n"
    rf"{SCENE_SECTION}(?:\n\n{SCENE_SECTION})*\n?\Z"
)
SEGMENT_LINE = re.compile(
    r"(?m)^生成段 (?P<number>\d{2})｜(?P<name>[^｜\r\n]+)｜"
    r"(?P<duration>\d+(?:\.\d+)?)s$"
)
SHOT = re.compile(
    rf"(?P<header>{HEADER})\n"
    rf"  - 起始状态：(?P<start_type>{START_TYPES})｜(?P<start_state>[^\r\n]+)\n"
    r"  - 景别机位：(?P<shot_setup>[^\r\n]+)\n"
    r"  - 构图/光影：(?P<light>[^\r\n]+)\n"
    r"  - 画面/表演：(?P<visual>[^\r\n]+)\n"
    r"  - 运镜/焦点：(?P<camera_focus>[^\r\n]+)\n"
    r"  - 特效：(?P<vfx>[^\r\n]+)\n"
    r"  - 台词/音效：台词：(?P<dialogue>[^\r\n]+)；音效：(?P<audio>[^\r\n]+)\n"
    r"  - 尾帧：(?P<tail>[^\r\n]+)"
)
RELATIVE_STATE = re.compile(
    r"继承镜(?:号)?\s*\d+|镜(?:号)?\s*\d+状态|(?<!当)前镜|前一镜|上一镜|下一镜|"
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
    global_match = GLOBAL_PREFIX.match(normalized)
    content = normalized[global_match.end() :] if global_match else normalized
    if not DOCUMENT.fullmatch(normalized):
        errors.append(
            "正文未严格匹配固定列表格式：第一项必须是全局风格锁定，"
            "其下依次写用户指定风格、剧本推断补全、最终执行风格；第二项必须是全局色卡/影调/光影，"
            "其下依次写全局影调、全局色卡、全局光影；第三项必须是Seedance 2.5专属提示词，"
            "其下写正向提示词和负向提示词；每个场景必须先写“- 场景 NN｜场景名”及场景影调、场景色卡、场景光影；多段文件再写生成段标题和镜头列表项，"
            "单段文件可直接写镜头列表项。每镜使用“- 镜头 NN｜时长s”，其下依次缩进列出起始状态、景别机位、构图/光影、画面/表演、运镜/焦点、特效、台词/音效、尾帧。"
        )
        return errors

    segment_headers = list(SEGMENT_LINE.finditer(normalized))
    if segment_headers:
        segment_numbers = [int(match.group("number")) for match in segment_headers]
        expected_segments = list(range(1, len(segment_numbers) + 1))
        if segment_numbers != expected_segments:
            errors.append(
                f"生成段编号必须从01开始连续递增；当前为 {segment_numbers}。"
            )

        segments: list[tuple[int, str, float, str]] = []
        for index, match in enumerate(segment_headers):
            body_start = match.end() + 2
            next_segment = segment_headers[index + 1].start() - 2 if index + 1 < len(segment_headers) else len(normalized)
            next_scene = normalized.find("\n\n- 场景 ", body_start)
            body_end = min(next_segment, next_scene if next_scene != -1 else len(normalized))
            segment_body = normalized[body_start:body_end].rstrip("\n")
            segments.append(
                (
                    int(match.group("number")),
                    match.group("name"),
                    float(match.group("duration")),
                    segment_body,
                )
            )
    else:
        segments = []

    numbers = [int(value) for value in re.findall(r"(?m)^- 镜头 (\d{2})｜", content)]
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        errors.append(f"镜头编号必须从01开始连续递增；当前为 {numbers}。")

    scene_numbers = [int(value) for value in re.findall(r"(?m)^- 场景 (\d{2})｜", normalized)]
    expected_scenes = list(range(1, len(scene_numbers) + 1))
    if scene_numbers != expected_scenes:
        errors.append(f"场景编号必须从01开始连续递增；当前为 {scene_numbers}。")

    for segment_number, segment_name, declared_duration, segment_body in segments:
        durations = [
            float(value)
            for value in re.findall(
                r"(?m)^- 镜头 \d{2}｜(\d+(?:\.\d+)?)s$",
                segment_body,
            )
        ]
        segment_duration = sum(durations)
        if declared_duration >= 0 and abs(segment_duration - declared_duration) > 1e-9:
            errors.append(
                f"生成段 {segment_number:02d}“{segment_name}”标题标注{declared_duration:g}秒，"
                f"但段内镜头合计{segment_duration:g}秒；两者必须一致。"
            )
        if segment_duration > 30.0 + 1e-9:
            errors.append(
                f"生成段 {segment_number:02d}“{segment_name}”镜头时长之和为{segment_duration:g}秒，"
                "超过30秒硬上限；请在自然因果接缝拆段，不得删改剧情或强行加速。"
            )

    for shot_index, match in enumerate(SHOT.finditer(content), start=1):
        body = " ".join(
            match.group(name)
            for name in (
                "start_state",
                "shot_setup",
                "light",
                "visual",
                "camera_focus",
                "vfx",
                "dialogue",
                "audio",
                "tail",
            )
        )
        start_type = match.group("start_type")
        if shot_index == 1 and start_type not in {"场景起镜", "转场起镜"}:
            errors.append(
                "镜头 01 的起始状态必须为场景起镜或转场起镜，并完整建立起态。"
            )
        if shot_index > 1 and start_type == "场景起镜":
            errors.append(
                f"镜头 {shot_index:02d} 不是全文首镜，不能使用场景起镜；新时空请使用转场起镜。"
            )
        if match.group("start_state").strip() == "无":
            errors.append(f"镜头 {shot_index:02d} 的起始状态不得写无。")
        if match.group("visual").strip() == "无":
            errors.append(f"镜头 {shot_index:02d} 的画面/表演不得写无。")
        if match.group("camera_focus").strip() == "无":
            errors.append(f"镜头 {shot_index:02d} 的运镜/焦点不得写无。")
        tail_value = match.group("tail").strip().rstrip("。.!！")
        if tail_value in EMPTY_TAIL_VALUES:
            errors.append(
                f"镜头 {shot_index:02d} 的尾帧必须写具体终态，包括生成段末镜和全场最后一镜；"
                "不得用无、结束、无后续镜或无需承接占位。"
            )
        reference = RELATIVE_STATE.search(body)
        if reference:
            errors.append(
                f"镜头 {shot_index:02d} 使用跨镜替代语“{reference.group(0)}”；"
                "请重述本镜生成所需的具体可见状态。"
            )

        internal = INTERNAL_MARKER.search(body)
        if internal:
            errors.append(
                f"镜头 {shot_index:02d} 含内部标记“{internal.group(0)}”；"
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
