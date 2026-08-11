#!/usr/bin/env python3
"""Validate the fixed contract and warn about conservative shot design."""

from __future__ import annotations

import argparse
import math
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
SCENE_CARD = (
    r"- 场景 \d{2}｜[^\r\n]+\n"
    r"  - 场景影调：[^\r\n]+\n"
    r"  - 场景色卡：[^\r\n]+\n"
    r"  - 场景光影：[^\r\n]+"
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
    rf"{PERSON_ANCHORS}\n\n{SCENE_CARD}\n\n{BLOCK}(?:\n\n{BLOCK})*"
    rf"(?:\n\n{SCENE_CARD}\n\n{BLOCK}(?:\n\n{BLOCK})*)*\n?\Z"
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

SHOT_SIZE_PATTERNS = (
    ("大特写", re.compile(r"大特写")),
    ("局部特写", re.compile(r"局部特写")),
    ("特写", re.compile(r"特写")),
    ("大全景", re.compile(r"大全景")),
    ("中全景", re.compile(r"中全景")),
    ("全景", re.compile(r"全景")),
    ("中近景", re.compile(r"中近景")),
    ("近景", re.compile(r"近景")),
    ("中景", re.compile(r"中景")),
)
CONSERVATIVE_MOVEMENT = re.compile(r"固定|缓慢|平稳|轻轻|轻微")
EXPRESSIVE_MOVEMENT = re.compile(
    r"快速(?:跟拍|跟随|推进|靠近|后退|停止)|急停|立即停(?:止|住)|"
    r"短促|斜俯|甩镜|冲击式|大特写|局部特写"
)
STRONG_EXPRESSIVE_MOVEMENT = re.compile(
    r"急停|立即停(?:止|住)|斜俯|甩镜|冲击式|"
    r"快速(?:跟拍|跟随|推进|靠近|后退|停止)"
)
GLOBAL_MOTION_BAN = re.compile(
    r"禁止(?:任何|所有)?(?:快速运动|高速运镜|快速运镜|剧烈镜头|剧烈运镜)|"
    r"不允许(?:任何|所有)?(?:快速运动|高速运镜|快速运镜|剧烈镜头|剧烈运镜)"
)
MICRO_ACTION_TERMS = (
    "看",
    "视线",
    "眼神",
    "皱眉",
    "眯眼",
    "嘴角",
    "微笑",
    "僵住",
    "停住",
    "停顿",
    "呼吸",
    "微微",
    "缓缓",
    "逐渐",
    "保持",
    "维持",
)
STRATEGY_ACTION = re.compile(
    r"走向|走到|跑出|冲向|扑向|飞扑|逼近|靠近|退开|后退|退向|"
    r"拉开距离|缩短.{0,4}距离|转身|起身|坐下|站起|递出|递回|接过|"
    r"拿出|放下|推开|推回|拉开|拽住|夺回|扔下|藏起|遮住|挡住|"
    r"关上|打开|踹开|抱住|拥抱|挣开|让开|跨过|绕到|占住|上车|"
    r"下车|骑着|刹停|抓住|松开|扶住|压住|指向|迈进|欠身"
)
IMPACT_MECHANISMS = (
    ("短促逼近/冲击逼近", re.compile(r"短促.{0,12}(?:逼近|靠近)|冲击式.{0,12}(?:逼近|靠近)")),
    ("急停/立即停止", re.compile(r"急停|立即停(?:止|住)|快速停止")),
    ("斜俯运动", re.compile(r"斜俯")),
    ("遮挡揭示", re.compile(r"遮挡|门框.{0,12}(?:横移|揭示)|前景.{0,12}(?:移开|揭示)")),
)
INDIRECT_CAMERA_DESCRIPTION = re.compile(
    r"从[^，；]{0,18}(?:身侧|肩后)看[^，；]{0,24}(?:视线|目光)|"
    r"(?:顺着|跟随)[^，；]{0,12}(?:视线|目光)(?:看|移动|上移|下移|落到|转到)"
)
EXPLICIT_TRANSITION_MARKER = re.compile(
    r"【\s*转场\s*】|\[\s*转场\s*\]|转场\s*[：:]"
)
TRANSITION_BRIDGE_LANGUAGE = re.compile(
    r"声音桥|尾音(?:持续|延续)|声音(?:延续|先行|承接)|"
    r"匹配切|动作匹配|物体匹配|形状匹配|光影匹配|"
    r"遮挡(?:切换|占满|退开)|占满画面|同方向(?:接住|延续)|"
    r"运动方向延续|甩镜.{0,10}(?:切|接)|黑场.{0,10}(?:进入|接入)|"
    r"前景.{0,10}(?:遮满|擦过)|(?:门板|车门).{0,12}(?:合拢|打开).{0,8}(?:尾响|声音)"
)


def classify_shot_size(shot_setup: str) -> str | None:
    for name, pattern in SHOT_SIZE_PATTERNS:
        if pattern.search(shot_setup):
            return name
    return None


def counts_as_expressive_movement(camera_focus: str) -> bool:
    """Treat mixed 'fast but steady' wording as a review signal, not full impact."""
    if not STRONG_EXPRESSIVE_MOVEMENT.search(camera_focus):
        return False
    if CONSERVATIVE_MOVEMENT.search(camera_focus):
        return bool(
            re.search(r"急停|立即停(?:止|住)|斜俯|甩镜|冲击式", camera_focus)
        )
    return bool(EXPRESSIVE_MOVEMENT.search(camera_focus))


def conservatism_warnings(text: str, source_text: str | None = None) -> list[str]:
    """Return non-blocking prompts for a deliberate creative check."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    warnings: list[str] = []
    negative_prompt = re.search(r"(?m)^  - 负向提示词：([^\r\n]+)", normalized)
    if negative_prompt and GLOBAL_MOTION_BAN.search(negative_prompt.group(1)):
        warnings.append(
            "负向提示词无条件禁止快速运动或高速运镜，可能误伤有动机的表现性镜头；"
            "请改为禁止无动机乱晃、失控抖动、穿墙穿物或运动后无法停稳。"
        )

    shots = list(SHOT.finditer(normalized))
    if source_text is not None:
        source_normalized = source_text.replace("\r\n", "\n").replace("\r", "\n")
        marker_count = len(EXPLICIT_TRANSITION_MARKER.findall(source_normalized))
        bridged_transitions = 0
        for index, shot in enumerate(shots):
            if shot.group("start_type") != "转场起镜":
                continue
            previous = shots[index - 1] if index > 0 else None
            combined_parts = [
                shot.group("start_state"),
                shot.group("composition"),
                shot.group("visual"),
                shot.group("camera_focus"),
                shot.group("audio"),
            ]
            if previous is not None:
                combined_parts.extend(
                    [
                        previous.group("camera_focus"),
                        previous.group("audio"),
                        previous.group("tail"),
                    ]
                )
            if TRANSITION_BRIDGE_LANGUAGE.search("；".join(combined_parts)):
                bridged_transitions += 1
        if marker_count and bridged_transitions < marker_count:
            warnings.append(
                f"源文本包含 {marker_count} 处明确【转场】，但成稿只识别到 "
                f"{bridged_transitions} 处具有声音、动作、物体、遮挡、光影或运动方向承接的转场镜；"
                "仅使用“转场起镜”标签或直接切新场大全景不算完成。"
            )
    if len(shots) < 6:
        return warnings

    sizes = [classify_shot_size(shot.group("shot_setup")) for shot in shots]
    impact_sizes = {"大全景", "特写", "大特写", "局部特写"}
    middle_sizes = {"中景", "中近景", "近景", "中全景"}
    known_sizes = [size for size in sizes if size is not None]

    if len(shots) >= 8 and not any(size in impact_sizes for size in known_sizes):
        warnings.append(
            "全片未发现大全景、特写、大特写或局部特写；请确认是否遗漏环境尺度、"
            "身体接触、局部证据或认知冲击。"
        )

    if known_sizes:
        middle_count = sum(size in middle_sizes for size in known_sizes)
        if len(shots) >= 10 and middle_count / len(known_sizes) >= 0.7:
            warnings.append(
                "中景、中近景和近景占已识别景别的七成以上；这不是格式错误，"
                "但应确认观看距离曲线是否有剧情依据。"
            )

    repeated_runs: list[tuple[int, int, str]] = []
    run_start = 0
    for index in range(1, len(sizes) + 1):
        if index < len(sizes) and sizes[index] == sizes[run_start]:
            continue
        if sizes[run_start] is not None and index - run_start >= 4:
            repeated_runs.append((run_start + 1, index, sizes[run_start]))
        run_start = index
    if repeated_runs:
        start, end, size = repeated_runs[0]
        warnings.append(
            f"镜头 {start:02d}-{end:02d} 连续使用{size}；请确认重复是在制造等待或压力，"
            "而不是默认覆盖。"
        )

    movements = [shot.group("camera_focus") for shot in shots]
    conservative_count = sum(bool(CONSERVATIVE_MOVEMENT.search(item)) for item in movements)
    expressive_count = sum(counts_as_expressive_movement(item) for item in movements)
    if (
        len(shots) >= 10
        and conservative_count / len(shots) >= 0.55
        and expressive_count / len(shots) < 0.2
    ):
        warnings.append(
            "固定、缓慢或平稳运镜占比较高，而快速跟拍、急停、斜俯或局部爆点较少；"
            "请确认关键转折是否被低风险表达压平。"
        )

    visuals = [shot.group("visual") for shot in shots]
    weak_only = [
        index
        for index, visual in enumerate(visuals, start=1)
        if any(term in visual for term in MICRO_ACTION_TERMS)
        and not STRATEGY_ACTION.search(visual)
    ]
    weak_threshold = max(5, math.ceil(len(shots) * 0.3))
    if len(weak_only) >= weak_threshold:
        sample = "、".join(f"{index:02d}" for index in weak_only[:6])
        warnings.append(
            f"镜头 {sample} 等较多镜头以看、停、僵住、嘴角或呼吸等微反应为主，"
            "未发现明确的道具、距离、占位、接触或出口策略动作；请确认关键情绪是否真正推进为行动。"
        )

    repeated_micro = []
    repeat_threshold = max(5, math.ceil(len(shots) * 0.28))
    for term in MICRO_ACTION_TERMS:
        count = sum(term in visual for visual in visuals)
        if count >= repeat_threshold:
            repeated_micro.append(f"{term}（{count}镜）")
    if repeated_micro:
        warnings.append(
            "画面/表演反复依赖 " + "、".join(repeated_micro[:4]) +
            "；请把其中一部分改为手部/道具、身体重心、人物距离或空间占位变化。"
        )

    action_runs: list[tuple[int, int]] = []
    run_start: int | None = None
    for index, visual in enumerate(visuals, start=1):
        if not STRATEGY_ACTION.search(visual):
            if run_start is None:
                run_start = index
            continue
        if run_start is not None and index - run_start >= 4:
            action_runs.append((run_start, index - 1))
        run_start = None
    if run_start is not None and len(visuals) + 1 - run_start >= 4:
        action_runs.append((run_start, len(visuals)))
    if action_runs:
        start, end = action_runs[0]
        warnings.append(
            f"镜头 {start:02d}-{end:02d} 连续未识别到改变道具、距离、占位、接触或出口的策略动作；"
            "对白可以克制，但反转链不能长期只靠面部状态推进。"
        )

    overloaded = []
    for index, shot in enumerate(shots, start=1):
        duration_match = re.search(r"｜(\d+(?:\.\d+)?)s", shot.group("header"))
        duration = float(duration_match.group(1)) if duration_match else 0.0
        visual = shot.group("visual")
        if duration >= 8 and visual.count("；") >= 2:
            overloaded.append(index)
    if overloaded:
        sample = "、".join(f"{index:02d}" for index in overloaded[:6])
        warnings.append(
            f"镜头 {sample} 时长不少于8秒且画面/表演包含至少三个动作或状态分句；"
            "请确认是否把刺激、反应、策略改变和关系结果塞进同一镜。"
        )

    repeated_mechanisms = []
    mechanism_threshold = max(4, math.ceil(len(shots) * 0.22))
    for label, pattern in IMPACT_MECHANISMS:
        count = sum(bool(pattern.search(movement)) for movement in movements)
        if count >= mechanism_threshold:
            repeated_mechanisms.append(f"{label}（{count}镜）")
    if repeated_mechanisms:
        warnings.append(
            "表现性运镜机制重复集中在 " + "、".join(repeated_mechanisms) +
            "；除非这是明确视觉母题，否则应在声音先行、局部证据、遮挡揭示、"
            "人物占位、快速行动和关系拉开之间更换主机制。"
        )

    indirect_camera = []
    for index, shot in enumerate(shots, start=1):
        combined = shot.group("shot_setup") + "；" + shot.group("camera_focus")
        if INDIRECT_CAMERA_DESCRIPTION.search(combined):
            indirect_camera.append(index)
    if indirect_camera:
        sample = "、".join(f"{index:02d}" for index in indirect_camera[:6])
        warnings.append(
            f"镜头 {sample} 的描述把身侧/肩后机位、人物视线和摄影机路径揉在一起；"
            "请优先改成“从具体可见起点起镜，直接运动，最终定格具体读点”的短句。"
        )

    return warnings


def validate(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not DOCUMENT.fullmatch(normalized):
        return [
            "正文未严格匹配固定对白列表模板：第一项必须是全局风格锁定，"
            "其下依次写用户指定风格、剧本推断补全、最终执行风格；第二项必须是全局色卡/影调/光影，"
            "其下依次写全局影调、全局色卡、全局光影；第三项必须是Seedance 2.5专属提示词，"
            "其下写正向提示词和负向提示词；第四项必须是人物锚点且每名主要人物同时写基准音色和基本性格锚点；其后每个场景必须先写“- 场景 NN｜场景名”及场景影调、场景色卡、场景光影；每镜必须使用“- 镜头 NN｜时长s”，"
            "其下依次缩进列出起始状态、景别机位、构图/光影、画面/表演、运镜/焦点、特效、台词/音效、尾帧；最后一镜也必须有尾帧，禁止表格和平铺段落。"
        ]

    errors: list[str] = []
    numbers = [int(value) for value in re.findall(r"(?m)^- 镜头 (\d{2})｜", normalized)]
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        errors.append(f"镜头编号必须从01开始连续递增；当前为 {numbers}。")

    scene_numbers = [int(value) for value in re.findall(r"(?m)^- 场景 (\d{2})｜", normalized)]
    expected_scenes = list(range(1, len(scene_numbers) + 1))
    if scene_numbers != expected_scenes:
        errors.append(f"场景编号必须从01开始连续递增；当前为 {scene_numbers}。")

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
    parser.add_argument(
        "--source",
        type=Path,
        help="optional source script used to verify explicit transition markers",
    )
    args = parser.parse_args()
    try:
        text = args.path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        print(f"cannot read {args.path}: {exc}", file=sys.stderr)
        return 2

    source_text = None
    if args.source is not None:
        try:
            source_text = args.source.read_text(encoding="utf-8-sig")
        except OSError as exc:
            print(f"cannot read source {args.source}: {exc}", file=sys.stderr)
            return 2

    errors = validate(text)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"format valid: {args.path}")
    for warning in conservatism_warnings(text, source_text):
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
