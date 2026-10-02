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
SCENE_SECTION = rf"{SCENE_CARD}\n\n{SEGMENT}(?:\n\n{SEGMENT})*"
DOCUMENT = re.compile(
    rf"\A{STYLE_LOCK}\n\n{GLOBAL_CARD}\n\n{SEEDANCE_PROMPTS}\n\n"
    rf"{SCENE_SECTION}(?:\n\n{SCENE_SECTION})*\n?\Z"
)
SEGMENT_LINE = re.compile(
    r"(?m)^生成段 (?P<number>\d{2})｜(?P<name>[^｜\r\n]+)｜"
    r"(?P<duration>\d+(?:\.\d+)?)s$"
)
SINGLE_UNIT = re.compile(
    r"^###\s+生成单元\s+(G\d+)\s*[｜|]\s*时长[：:]\s*"
    r"(\d+(?:\.\d+)?)\s*秒\s*[｜|]\s*承载[：:]\s*"
    r"(镜头[^｜|\n]+)\s*[｜|]\s*([^｜|\n]+)$",
    re.M,
)
SINGLE_WINDOW = re.compile(
    r"^\s{2,}-\s*(\d+(?:\.\d+)?)\s*[—–-]\s*(\d+(?:\.\d+)?)\s*秒\s*[｜|]\s*(.+)$",
    re.M,
)
SINGLE_FIELDS = [
    "起幅与连续性",
    "摄影与构图",
    "光影、环境色彩与材质",
    "画面与表演时间线",
    "台词与声音层次",
    "落幅状态",
]
SHOT_SIZES = re.compile(r"大特写|特写|近景|中近景|中景|中全景|全景|大远景|远景|半身")
FOCAL_LENGTH = re.compile(r"\d+(?:\.\d+)?\s*(?:mm|毫米)")
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


def validate_single(text: str, max_unit_seconds: float = 35.0, require_focal_length: bool = False) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    errors: list[str] = []
    units = list(SINGLE_UNIT.finditer(normalized))
    if not units:
        return ["未找到单生成单元标题；格式应为 ### 生成单元 G…｜时长：X秒｜承载：镜头…｜单元任务"]
    if normalized[: units[0].start()].strip():
        errors.append("首个生成单元前不得有额外正文。")
    ids = [int(match.group(1)[1:]) for match in units]
    if ids != list(range(ids[0], ids[0] + len(ids))):
        errors.append(f"生成单元编号必须连续递增；当前为 {ids}。")
    for index, match in enumerate(units):
        unit_id = match.group(1).strip()
        duration = float(match.group(2))
        if duration <= 0 or duration > max_unit_seconds:
            errors.append(f"生成单元 {unit_id} 时长必须大于0且不超过{max_unit_seconds:g}秒。")
        end = units[index + 1].start() if index + 1 < len(units) else len(normalized)
        body = normalized[match.end():end].strip()
        field_matches = list(re.finditer(r"(?m)^- ([^：:\n]+)[：:]", body))
        actual_fields = [item.group(1) for item in field_matches]
        for field in SINGLE_FIELDS:
            if field not in actual_fields:
                errors.append(f"生成单元 {unit_id} 缺少字段：{field}。")
        if actual_fields[: len(SINGLE_FIELDS)] != SINGLE_FIELDS:
            errors.append(f"生成单元 {unit_id} 六个核心字段顺序不正确。")
        extras = actual_fields[len(SINGLE_FIELDS) :]
        allowed_extras = ["本生成单元特殊正向约束", "本生成单元特殊负面约束"]
        if extras != [field for field in allowed_extras if field in extras] or len(extras) != len(set(extras)):
            errors.append(f"生成单元 {unit_id} 含未知、重复或乱序字段。")
        timeline = re.search(r"^- 画面与表演时间线[：:]\s*\n(.*?)(?=^- \S|\Z)", body, re.S | re.M)
        if not timeline:
            errors.append(f"生成单元 {unit_id} 缺少嵌套时间线。")
            continue
        windows = list(SINGLE_WINDOW.finditer(timeline.group(1)))
        if not windows:
            errors.append(f"生成单元 {unit_id} 没有可解析的时间段。")
            continue
        previous = 0.0
        for window in windows:
            start, stop = float(window.group(1)), float(window.group(2))
            detail = window.group(3)
            if abs(start - previous) > 0.05 or stop <= start:
                errors.append(f"生成单元 {unit_id} 时间段不连续或起止无效：{start:g}-{stop:g}秒。")
            previous = stop
            if require_focal_length and not FOCAL_LENGTH.search(detail):
                errors.append(f"生成单元 {unit_id} 时间段缺少焦段：{detail}。")
            if not SHOT_SIZES.search(detail):
                errors.append(f"生成单元 {unit_id} 时间段缺少中文景别：{detail}。")
            parts = [part.strip() for part in re.split(r"[｜|]", detail)]
            if len(parts) < 3 or not parts[0] or not parts[1] or not "".join(parts[2:]).strip():
                errors.append(f"生成单元 {unit_id} 时间段必须包含承载镜号、景别和画面执行描述。")
            if not re.search(r"声音[：:]", detail):
                errors.append(f"生成单元 {unit_id} 时间段缺少声音描述。")
        if abs(previous - duration) > 0.05:
            errors.append(f"生成单元 {unit_id} 标题时长{duration:g}秒与时间线结束{previous:g}秒不一致。")
    return errors


def validate(text: str, max_segment_seconds: float = 30.0) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    errors: list[str] = []
    global_match = GLOBAL_PREFIX.match(normalized)
    content = normalized[global_match.end() :] if global_match else normalized
    if not DOCUMENT.fullmatch(normalized):
        errors.append(
            "正文未严格匹配固定列表格式：第一项必须是全局风格锁定，"
            "其下依次写用户指定风格、剧本推断补全、最终执行风格；第二项必须是全局色卡/影调/光影，"
            "其下依次写全局影调、全局色卡、全局光影；第三项必须是Seedance 2.5专属提示词，"
            "其下写正向提示词和负向提示词；每个场景必须先写“- 场景 NN｜场景名”及场景影调、场景色卡、场景光影，再写至少一个生成段标题和镜头列表项。"
            "每镜使用“- 镜头 NN｜时长s”，其下依次缩进列出起始状态、景别机位、构图/光影、画面/表演、运镜/焦点、特效、台词/音效、尾帧。"
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
        if declared_duration <= 0:
            errors.append(f"生成段 {segment_number:02d}“{segment_name}”时长必须大于0秒。")
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
        if segment_duration > max_segment_seconds + 1e-9:
            errors.append(
                f"生成段 {segment_number:02d}“{segment_name}”镜头时长之和为{segment_duration:g}秒，"
                f"超过{max_segment_seconds:g}秒上限；请在自然因果接缝拆段，不得删改剧情或强行加速。"
            )

    scene_starts = [match.start() for match in re.finditer(r"(?m)^- 场景 \d{2}｜", content)]
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
        previous_shot_end = previous_shot.end() if shot_index > 1 else -1
        is_scene_first = shot_index == 1 or any(previous_shot_end < pos < match.start() for pos in scene_starts)
        if shot_index == 1 and start_type != "场景起镜":
            errors.append(
                "镜头 01 的起始状态必须为场景起镜，并完整建立起态。"
            )
        if shot_index > 1 and is_scene_first and start_type not in {"场景起镜", "转场起镜"}:
            errors.append(
                f"镜头 {shot_index:02d} 是新场景首镜，须使用场景起镜或转场起镜。"
            )
        if shot_index > 1 and not is_scene_first and start_type == "场景起镜":
            errors.append(f"镜头 {shot_index:02d} 不是场景首镜，不能使用场景起镜。")
        previous_shot = match
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
    parser.add_argument(
        "--mode",
        choices=["rapid", "refined", "single"],
        default="refined",
        help="rapid/refined 校验连续战斗固定结构；single 校验单生成单元结构。",
    )
    parser.add_argument("--max-segment-seconds", type=float, default=30.0)
    parser.add_argument("--max-unit-seconds", type=float, default=35.0)
    parser.add_argument("--require-focal-length", action="store_true")
    args = parser.parse_args()
    if args.max_segment_seconds <= 0 or args.max_unit_seconds <= 0:
        parser.error("时长上限必须大于0。")

    try:
        text = args.path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        print(f"cannot read {args.path}: {exc}", file=sys.stderr)
        return 2

    errors = (
        validate_single(text, args.max_unit_seconds, args.require_focal_length)
        if args.mode == "single"
        else validate(text, args.max_segment_seconds)
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"format valid: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
