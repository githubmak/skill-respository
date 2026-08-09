#!/usr/bin/env python3
"""Validate the fixed storyboard contract and report non-blocking load risks."""

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
SEQUENCE_MARKER = re.compile(r"先|再|随后|随即|然后|继而|同时|立即|最终|最后|紧接着")
MICRO_TIMING = re.compile(
    r"(?:第|在)?\d+(?:\.\d+)?(?:秒|s)(?:内|时|后|前|到)?",
    re.IGNORECASE,
)
EXACT_MOTION_MEASURE = re.compile(
    r"\d+(?:\.\d+)?(?:毫米|厘米|公分|度|mm|cm|°)",
    re.IGNORECASE,
)
INTERNAL_MARKER = re.compile(
    r"(?<![A-Za-z0-9])P\d+(?![A-Za-z0-9])|(?<![A-Za-z0-9])K[0-4](?![A-Za-z0-9])|"
    r"(?<![A-Za-z0-9])CAM(?:ERA)?(?![A-Za-z0-9])|剧本保真矩阵|唯一叙事目标|原文证据"
)

QUOTE_TEXT = re.compile(r"“([^”]*)”|\"([^\"]*)\"")
PAUSE_SHORT = re.compile(r"[，、,]")
PAUSE_MEDIUM = re.compile(r"[；：;:]")
PAUSE_LONG = re.compile(r"[。！？!?]")
PAUSE_ELLIPSIS = re.compile(r"……|\.\.\.")


def dialogue_timing(dialogue: str) -> tuple[int, float, float]:
    """Return spoken CJK count, estimated minimum seconds, and selected cps.

    Speaker names and OS/OV/system labels are excluded when quoted dialogue is used.
    The estimate is a lower bound that may run in parallel with compatible action.
    """
    quoted = [left or right for left, right in QUOTE_TEXT.findall(dialogue)]
    spoken = "".join(quoted) if quoted else dialogue
    if not quoted:
        spoken = re.sub(
            r"(?:^|[；;]\s*)(?:[^：:；;]{1,24})[：:]",
            "",
            spoken,
        )
    spoken = re.sub(r"\b(?:OS|OV|VO|系统音)\b", "", spoken, flags=re.IGNORECASE)
    spoken_chars = len(re.findall(r"[\u3400-\u9fff]", spoken))

    if re.search(r"低语|迟疑|哽咽|抽泣|喘息|虚弱|委屈|无奈", dialogue):
        cps = 3.0
    elif re.search(r"急促|快速|疾呼|大喊|尖叫|厉喝", dialogue):
        cps = 4.2
    else:
        cps = 3.8

    pause_seconds = (
        len(PAUSE_SHORT.findall(spoken)) * 0.12
        + len(PAUSE_MEDIUM.findall(spoken)) * 0.2
        + len(PAUSE_LONG.findall(spoken)) * 0.3
        + len(PAUSE_ELLIPSIS.findall(spoken)) * 0.45
    )
    return spoken_chars, spoken_chars / cps + pause_seconds, cps


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
            f"同一文件代表一个生成段，镜头时长之和为{segment_duration:g}秒，超过Seedance单次30秒硬上限；"
            "请在自然因果接缝拆成多个生成段，不得删改S原文事实或强行加速。"
        )

    for shot_index, match in enumerate(SHOT.finditer(normalized), start=1):
        header = match.group("header")
        duration_match = re.search(r"｜(\d+(?:\.\d+)?)s$", header)
        duration = float(duration_match.group(1)) if duration_match else 0.0
        body = " ".join(match.group(name) for name in ("visual", "vfx", "light", "audio", "dialogue"))

        reference = RELATIVE_STATE.search(body)
        if reference:
            errors.append(
                f"镜号 {shot_index:02d} 使用跨镜替代语“{reference.group(0)}”；"
                "请在本镜重述生成所需的可见起始状态。"
            )

        internal = INTERNAL_MARKER.search(body)
        if internal:
            errors.append(
                f"镜号 {shot_index:02d} 含内部标记“{internal.group(0)}”；"
                "最终Seedance正文只能保留真实可见的画面、动作、特效、光影、声音和台词。"
            )

        dialogue = match.group("dialogue")
        if dialogue != "无":
            spoken_chars, minimum, cps = dialogue_timing(dialogue)
            if duration > 0 and minimum > duration:
                errors.append(
                    f"镜号 {shot_index:02d} 的实际台词正文约{spoken_chars}个汉字，"
                    f"按约{cps:g}字/秒并计停顿至少约{minimum:.1f}秒，{duration:g}秒可能说不完；"
                    "即使与动作并行也必须延时或拆镜，不能机械累加或快读。"
                )
    return errors


def review_warnings(text: str) -> list[str]:
    """Return heuristic warnings that require semantic review, not automatic failure."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not DOCUMENT.fullmatch(normalized):
        return []

    warnings: list[str] = []
    for shot_index, match in enumerate(SHOT.finditer(normalized), start=1):
        header = match.group("header")
        duration_match = re.search(r"｜(\d+(?:\.\d+)?)s$", header)
        duration = float(duration_match.group(1)) if duration_match else 0.0
        dense_text = match.group("visual") + match.group("vfx")
        sequence_count = len(SEQUENCE_MARKER.findall(dense_text))
        sequence_limit = 5 if duration <= 3.0 else 8 if duration <= 6.0 else 11 if duration <= 8.0 else 14
        if sequence_count >= sequence_limit:
            warnings.append(
                f"镜号 {shot_index:02d} 为{duration:g}秒，含{sequence_count}个顺序标记，"
                "疑似堆积微动作或多个视觉中心；请先删除无锚点E、压缩N、去除重复，"
                "并聚合同一动作弧。若仍存在独立视觉中心再拆镜；不得删改S原文事实。"
            )

        micro_timing_count = len(MICRO_TIMING.findall(dense_text))
        exact_measure_count = len(EXACT_MOTION_MEASURE.findall(dense_text))
        if micro_timing_count >= 2 or exact_measure_count >= 2:
            warnings.append(
                f"镜号 {shot_index:02d} 含{micro_timing_count}处正文时间码和"
                f"{exact_measure_count}处精确运动量化，疑似替模型逐帧编舞；"
                "请只保留S规定或避免误读所需的控制点，把N/E身体补间、惯性和次级运动留给模型。"
            )
    return warnings


def self_test() -> int:
    valid = (
        "镜号 01｜超远全景｜镜头缓慢向前匀速推进，微俯角｜2.2s\n\n"
        "画面内容：深夜都市背街，巷心伫立宋棠一人。\n\n"
        "特效：空气漂浮细微都市扬尘颗粒。\n\n"
        "光影：冷调月夜，高位冷白月光。\n\n"
        "音效：城市远处微弱车流底噪。\n\n"
        "台词：无\n\n"
        "镜号 02｜五官极致特写｜锁脸定镜，平视机位呼吸式极慢微推｜5.5s\n\n"
        "画面内容：仍悬在巷心上空的宋棠缓缓阖眼，半脸傩纹沿肌肤成型。\n\n"
        "特效：朱砂纹路从眼尾向颧骨生长，鎏金微光沿纹理流动。\n\n"
        "光影：冷白环境光压低，朱砂与鎏金暖光集中照亮五官。\n\n"
        "音效：低沉呼吸与细微金属共鸣。\n\n"
        "台词：无\n"
    )
    invalid_field = valid.replace("\n\n特效：", "\n\n人物主体：宋棠。\n\n特效：")
    invalid_reference = valid.replace(
        "巷心伫立宋棠一人。", "继承镜01状态，巷心伫立宋棠一人。"
    )
    invalid_segment_duration = valid.replace("｜5.5s", "｜28s")
    high_load = valid.replace(
        "深夜都市背街，巷心伫立宋棠一人。",
        "先起身，再转身，随后跳起，随即翻滚，然后挥手，同时转头，" + "复杂动作" * 120,
    )
    invalid_dialogue = valid.replace("台词：无", "台词：宋棠：“这是一句明显无法在两秒之内自然完整说完的对白。”")
    invalid_internal = valid.replace("巷心伫立宋棠一人。", "P1原文证据：巷心伫立宋棠一人。")
    over_directed = valid.replace(
        "仍悬在巷心上空的宋棠缓缓阖眼，半脸傩纹沿肌肤成型。",
        "第0.2秒宋棠右手抬高10厘米，第0.6秒腕部旋转30度，随后阖眼。",
    )
    cases = (
        not validate(valid),
        bool(validate(invalid_field)),
        bool(validate(invalid_reference)),
        bool(validate(invalid_segment_duration)),
        not validate(high_load),
        bool(review_warnings(high_load)),
        not validate(over_directed),
        bool(review_warnings(over_directed)),
        bool(validate(invalid_dialogue)),
        bool(validate(invalid_internal)),
    )
    if not all(cases):
        print("self-test failed", file=sys.stderr)
        return 1
    print("self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.path is None:
        parser.error("path is required unless --self-test is used")

    try:
        text = args.path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        print(f"cannot read {args.path}: {exc}", file=sys.stderr)
        return 2

    errors = validate(text)
    warnings = review_warnings(text)
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if warnings:
        print(f"format valid with {len(warnings)} review warning(s): {args.path}")
    else:
        print(f"format valid: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
