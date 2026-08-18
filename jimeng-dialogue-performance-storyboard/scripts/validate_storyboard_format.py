#!/usr/bin/env python3
"""Validate hard storyboard structure and physical continuity contracts."""

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

SHOT_SIZE_TOKEN = re.compile(
    r"局部特写|大特写|中近景|中全景|大全景|特写|近景|中景|全景"
)
VARIABLE_FRAMING_MOVEMENT = re.compile(
    r"(?:从|由)[^，；。]{1,32}(?:上移|下移|上摇|下摇|推进|靠近|拉开|后退|横移|移动)"
    r"[^；。]{0,90}(?:最终|最后|终幅)[^；。]{0,32}(?:定格|停|落)"
)
VERTICAL_SCAN_MOVEMENT = re.compile(r"上移|下移|上摇|下摇")
OFFSCREEN_GAZE = re.compile(
    r"(?:视线|目光|打量|审视).{0,10}(?:落在|停在|留在|位于)?画外|"
    r"画外.{0,10}(?:视线|目光|打量|审视)"
)
CLOSEUP_SETUP = re.compile(r"局部特写|大特写|特写")
BODY_OR_CLOTHING_PART = re.compile(
    r"鞋面|鞋尖|脚|足|裤脚|小腿|膝|衣摆|衣料|腰|腹|胸口|手|手指|手臂|"
    r"袖口|肩|肩颈|脸|面部|眼|眼睛|眼眶|嘴|嘴唇|头|帽|兔耳"
)
FINAL_ENDPOINT_TEXT = re.compile(r"(?:最终|最后|终幅)(?P<endpoint>[^，；。]+)")
TAIL_ABSENCE_LANGUAGE = re.compile(r"移出画面|离开画面|不再入镜|已经出画|不可见")
BODY_REGION_PATTERNS = (
    ("下部", re.compile(r"鞋面|鞋尖|鞋|脚|足|裤脚|小腿|膝")),
    ("中部", re.compile(r"衣摆|衣料|腰|腹|胸口|手|手指|手臂|袖口")),
    ("上部", re.compile(r"肩|肩颈|脸|面部|眼|眼睛|眼眶|嘴|嘴唇|头|帽|兔耳")),
)
PROP_PATTERNS = (
    (
        "手机",
        re.compile(
            r"手机|手机屏幕|手机屏光|冷白屏幕|冷白屏光|"
            r"(?:衣袋|口袋|侧袋).{0,12}(?:震动|震颤|亮起|提示音)|"
            r"(?:震动|震颤|亮起|提示音).{0,12}(?:衣袋|口袋|侧袋)|"
            r"(?:压住|按住).{0,8}(?:衣袋|口袋|侧袋)|"
            r"(?:衣袋|口袋|侧袋).{0,8}(?:压住|按住)"
        ),
    ),
    ("茶杯", re.compile(r"茶杯|杯碟|茶盏|杯子")),
    ("帽子", re.compile(r"兔耳帽|帽子|帽檐|兔耳朵")),
    ("文件", re.compile(r"文件|合同|资料|档案|纸袋")),
    ("信封", re.compile(r"信封")),
    ("钥匙", re.compile(r"钥匙|门卡|房卡")),
    ("包袋", re.compile(r"背包|挎包|手提包|外卖箱|外卖袋|餐袋")),
)
PROP_CHANGE_ACTION = re.compile(
    r"拿出|取出|抽出|掏出|拿起|端起|举起|递出|递给|递回|接过|"
    r"夺过|抢过|放下|放回|搁下|扔下|掉落|落到|塞进|装进|收进|"
    r"藏起|藏到|藏进|遮住|挡住|翻开|展开|打开|合上|关上|"
    r"亮起|熄灭|点亮|换手|交到|转交|松开|压住|摘下|戴上"
)
PROP_INTRO_CUE = re.compile(
    r"提示音|震动|震颤|亮起|响起|拿出|取出|抽出|掏出|打开|翻开|"
    r"露出|显露|揭示|移开.{0,8}遮挡|遮挡.{0,8}移开|进入画面|走入|带着"
)
PROP_LOCATIONS = (
    ("衣袋内", re.compile(r"衣袋|口袋|侧袋|袋内")),
    ("手中", re.compile(r"手中|掌中|手里|拿着|握着|握住|抓着|抓住|端着|托着|举着|捏着")),
    ("身后", re.compile(r"(?:藏在|放在|留在|收在|移到)身后|背到背后")),
    ("茶几上", re.compile(r"(?:在|放在|留在|落在|压在|搁在|放回)茶几(?:上|边)?|茶几上")),
    ("桌面上", re.compile(r"(?:在|放在|留在|落在|压在|搁在|放回)(?:桌面|桌上|桌边)|桌面上|桌上")),
    ("杯碟上", re.compile(r"杯碟")),
    ("包内", re.compile(r"包内|包里|箱内|箱里")),
    ("地面", re.compile(r"地面|地上|脚边")),
    ("门边", re.compile(r"门边|门口|门旁")),
)
PROP_VISIBILITY_STATES = (
    ("屏幕可见", re.compile(r"屏幕|屏光|屏幕朝向|屏幕占满|屏幕亮")),
    ("被遮住", re.compile(r"被.{0,8}(?:身体|手|衣料).{0,8}(?:遮住|挡住)|藏在身后|屏幕避开")),
    ("未拿出", re.compile(r"未拿出|没有拿出|仍在.{0,6}(?:衣袋|口袋|侧袋)|还在.{0,6}(?:衣袋|口袋|侧袋)")),
)
PROP_BINARY_STATES = (
    ("开合", "打开", re.compile(r"打开|翻开|展开|敞开")),
    ("开合", "关闭", re.compile(r"关上|合上|闭合|未打开")),
    ("亮灭", "亮起", re.compile(r"亮起|点亮|屏幕亮|亮着|发亮")),
    ("亮灭", "熄灭", re.compile(r"熄灭|黑屏|暗下|不再发亮")),
)


def shot_size_sequence(value: str) -> list[str]:
    sequence: list[str] = []
    for match in SHOT_SIZE_TOKEN.finditer(value):
        size = match.group(0)
        if not sequence or sequence[-1] != size:
            sequence.append(size)
    return sequence


def has_explicit_single_framing_change(value: str) -> bool:
    matches = list(SHOT_SIZE_TOKEN.finditer(value))
    if len(shot_size_sequence(value)) != 2 or len(matches) < 2:
        return False
    if "起幅" in value and "终幅" in value:
        return True
    between = value[matches[0].end():matches[1].start()]
    return re.search(r"转|到|至", between) is not None


def body_regions(value: str) -> set[str]:
    return {
        label
        for label, pattern in BODY_REGION_PATTERNS
        if pattern.search(value)
    }


def person_marked_absent(name: str, value: str) -> bool:
    return bool(
        re.search(
            rf"{re.escape(name)}[^，；。]{{0,28}}(?:不入镜|画外|已出画|出画|移出画面|离开画面)",
            value,
        )
    )


def mentioned_props(value: str) -> set[str]:
    return {
        name
        for name, pattern in PROP_PATTERNS
        if pattern.search(value)
    }


def prop_pattern(prop_name: str) -> re.Pattern[str]:
    for name, pattern in PROP_PATTERNS:
        if name == prop_name:
            return pattern
    raise KeyError(prop_name)


def prop_context(value: str, prop_name: str) -> str:
    pattern = prop_pattern(prop_name)
    windows = []
    for match in pattern.finditer(value):
        windows.append(value[max(0, match.start() - 36):match.end() + 36])
    return "；".join(windows)


def prop_clauses(value: str, prop_name: str) -> str:
    pattern = prop_pattern(prop_name)
    return "；".join(
        clause
        for clause in re.split(r"[，；。]", value)
        if pattern.search(clause) is not None
    )


def prop_changes_in(value: str, prop_name: str) -> bool:
    pattern = prop_pattern(prop_name)
    return any(
        pattern.search(clause) is not None and PROP_CHANGE_ACTION.search(clause) is not None
        for clause in re.split(r"[，；。]", value)
    )


def nearest_pattern_label(
    value: str,
    anchor_pattern: re.Pattern[str],
    labeled_patterns: tuple[tuple[str, re.Pattern[str]], ...],
) -> str | None:
    anchors = list(anchor_pattern.finditer(value))
    if not anchors:
        return None
    nearest: tuple[float, str] | None = None
    for label, pattern in labeled_patterns:
        for match in pattern.finditer(value):
            center = (match.start() + match.end()) / 2
            distance = min(
                abs(center - ((anchor.start() + anchor.end()) / 2))
                for anchor in anchors
            )
            if nearest is None or distance < nearest[0]:
                nearest = (distance, label)
    return nearest[1] if nearest is not None else None


def prop_state(value: str, prop_name: str, person_names: list[str]) -> dict[str, str]:
    """Extract only explicit, high-confidence prop state for cross-cut checks."""
    pattern = prop_pattern(prop_name)
    if pattern.search(value) is None:
        return {}
    context = prop_clauses(value, prop_name)

    state: dict[str, str] = {}
    for person in person_names:
        held_by_person = re.search(
            rf"{re.escape(person)}[^，；。]{{0,18}}"
            rf"(?:拿着|握着|握住|抓着|抓住|端着|托着|举着|捏着|拿出|取出|接过|夺过)"
            rf"[^，；。]{{0,12}}(?:{pattern.pattern})",
            context,
        )
        prop_in_person_hand = re.search(
            rf"(?:{pattern.pattern})[^，；。]{{0,12}}"
            rf"(?:在|落在|留在){re.escape(person)}(?:的)?(?:手中|掌中|手里|怀里)",
            context,
        )
        matched = held_by_person or prop_in_person_hand
        if matched is not None and not re.search(r"未|没有|并未|尚未", matched.group(0)):
            state["控制者"] = person
            state["位置"] = "手中"
            break

    nearest_location = nearest_pattern_label(context, pattern, PROP_LOCATIONS)
    if nearest_location is not None and not (
        nearest_location == "手中" and "位置" in state
    ):
        state["位置"] = nearest_location

    nearest_visibility = nearest_pattern_label(context, pattern, PROP_VISIBILITY_STATES)
    if nearest_visibility is not None:
        state["显隐"] = nearest_visibility

    for slot, state_value, state_pattern in PROP_BINARY_STATES:
        if state_pattern.search(context):
            state[slot] = state_value

    hand_match = re.search(r"(?:右手|左手)", context)
    if hand_match is not None:
        state["手别"] = hand_match.group(0)
    return state


def prop_state_conflicts(previous: dict[str, str], current: dict[str, str]) -> list[str]:
    conflicts = []
    for slot in ("控制者", "位置", "手别", "开合", "亮灭", "显隐"):
        before = previous.get(slot)
        after = current.get(slot)
        if before is not None and after is not None and before != after:
            conflicts.append(f"{slot}由“{before}”变成“{after}”")
    return conflicts


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
    person_names = re.findall(
        r"(?m)^  - ([^：\r\n]+)：基准音色：",
        normalized,
    )
    numbers = [int(value) for value in re.findall(r"(?m)^- 镜头 (\d{2})｜", normalized)]
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        errors.append(f"镜头编号必须从01开始连续递增；当前为 {numbers}。")

    scene_numbers = [int(value) for value in re.findall(r"(?m)^- 场景 (\d{2})｜", normalized)]
    expected_scenes = list(range(1, len(scene_numbers) + 1))
    if scene_numbers != expected_scenes:
        errors.append(f"场景编号必须从01开始连续递增；当前为 {scene_numbers}。")

    shots = list(SHOT.finditer(normalized))
    scene_markers = list(re.finditer(r"(?m)^- 场景 \d{2}｜", normalized))
    scene_ids = [
        sum(marker.start() < shot.start() for marker in scene_markers)
        for shot in shots
    ]
    established_props: set[str] = set()
    known_prop_states: dict[str, dict[str, str]] = {}

    for shot_index, shot in enumerate(shots, start=1):
        scene_changed = shot_index == 1 or scene_ids[shot_index - 1] != scene_ids[shot_index - 2]
        if scene_changed:
            established_props = set()
            known_prop_states = {}

        start_type = shot.group("start_type")
        start_state = shot.group("start_state")
        shot_setup = shot.group("shot_setup")
        composition = shot.group("composition")
        visual = shot.group("visual")
        camera_focus = shot.group("camera_focus")
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
        if visual.strip() == "无":
            errors.append(f"镜头 {shot_index:02d} 的画面/表演不得写无。")
        if camera_focus.strip() == "无":
            errors.append(f"镜头 {shot_index:02d} 的运镜/焦点不得写无。")
        if (
            CLOSEUP_SETUP.search(shot_setup)
            and BODY_OR_CLOTHING_PART.search(shot_setup)
            and person_names
            and not any(name in shot_setup for name in person_names)
        ):
            errors.append(
                f"镜头 {shot_index:02d} 的身体或服装局部特写没有写明人物归属；"
                "请写成“宋棠鞋面局部特写”或“陆钦眼部大特写”，不能只写身体部位。"
            )
        setup_size_sequence = shot_size_sequence(shot_setup)
        if len(setup_size_sequence) > 2:
            errors.append(
                f"镜头 {shot_index:02d} 的景别机位出现多个连续景别："
                + " -> ".join(setup_size_sequence)
                + "；单镜只能固定一个景别或完成一次 A 到 B 的景别变化，"
                "第三个观看距离请交给相邻有独立职责的镜头。"
            )
        if VARIABLE_FRAMING_MOVEMENT.search(camera_focus) and not (
            ("起幅" in shot_setup and "终幅" in shot_setup)
            or has_explicit_single_framing_change(shot_setup)
        ):
            errors.append(
                f"镜头 {shot_index:02d} 的运镜从一个主体、身体部位或景别移动到另一处，"
                "但景别机位没有写清唯一的具名起终幅；请写“全景转特写”或"
                "“全景起幅；终幅为特写”，且不要加入第三个景别。"
            )
        if OFFSCREEN_GAZE.search("；".join((composition, visual, tail))):
            errors.append(
                f"镜头 {shot_index:02d} 把视线、目光、打量或审视写成画外可见物；"
                "请改成“具名人物不入镜，在画外说话或发出声音”，并直接写画内拍摄主体。"
            )
        for name in person_names:
            gaze_action = re.search(
                rf"{re.escape(name)}(?:的)?[^，；。]{{0,10}}(?:视线|目光|打量|审视|看向)",
                visual,
            )
            if gaze_action is None:
                continue
            framing_text = "；".join((shot_setup, composition))
            if name in shot_setup and not person_marked_absent(name, framing_text):
                continue
            errors.append(
                f"镜头 {shot_index:02d} 在画面/表演中安排了未入镜人物{name}的视线或审视动作；"
                "请让该人物真实进入对应阶段构图，或只保留画外台词/声音和画内人物反应。"
            )
        endpoint_match = FINAL_ENDPOINT_TEXT.search(camera_focus)
        if (
            endpoint_match is not None
            and VERTICAL_SCAN_MOVEMENT.search(camera_focus)
            and CLOSEUP_SETUP.search(shot_setup)
            and not TAIL_ABSENCE_LANGUAGE.search(tail)
        ):
            endpoint_regions = body_regions(endpoint_match.group("endpoint"))
            tail_regions = body_regions(tail)
            extra_regions = tail_regions - endpoint_regions
            if endpoint_regions and extra_regions:
                errors.append(
                    f"镜头 {shot_index:02d} 的终点特写与尾帧可见范围冲突；"
                    "尾帧仍保留了已经在上摇或下摇中移出画面的其他身体部位。"
                )
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

        start_props = mentioned_props(start_state)
        if not scene_changed:
            unestablished = sorted(start_props - established_props)
            for prop_name in unestablished:
                errors.append(
                    f"镜头 {shot_index:02d} 的起始状态首次出现道具“{prop_name}”，"
                    "但本场此前没有可见或可听的建立过程；请把声音/震动/拿出/打开/"
                    "遮挡揭示及人物首次反应移入本镜画面过程，不能让道具在切镜后凭空受控。"
                )

        for prop_name in start_props:
            current_state = prop_state(start_state, prop_name, person_names)
            previous_state = known_prop_states.get(prop_name, {})
            conflicts = prop_state_conflicts(previous_state, current_state)
            if conflicts:
                errors.append(
                    f"镜头 {shot_index:02d} 的起始状态与此前“{prop_name}”最终状态冲突："
                    + "、".join(conflicts)
                    + "；该变化必须在某一镜的画面/表演中完成，并由尾帧结算。"
                )

        visual_props = mentioned_props(visual)
        tail_props = mentioned_props(tail)
        for prop_name in sorted(visual_props):
            if not prop_changes_in(visual, prop_name):
                continue
            if prop_name not in tail_props:
                errors.append(
                    f"镜头 {shot_index:02d} 的画面/表演改变了道具“{prop_name}”，"
                    "但尾帧没有结算其最终控制者、位置或必要物理状态。"
                )
                continue
            final_state = prop_state(tail, prop_name, person_names)
            if not final_state:
                errors.append(
                    f"镜头 {shot_index:02d} 的尾帧提到道具“{prop_name}”，"
                    "但没有写清本镜变化后的最终控制者、位置、显隐、开合或亮灭状态。"
                )

        for prop_name in tail_props:
            final_state = prop_state(tail, prop_name, person_names)
            if final_state:
                known_prop_states[prop_name] = final_state

        establishment_text = "；".join(
            (
                shot_setup,
                composition,
                visual,
                camera_focus,
                shot.group("vfx"),
                shot.group("audio"),
                tail,
            )
        )
        if scene_changed:
            establishment_text = start_state + "；" + establishment_text
        current_props = mentioned_props(establishment_text)
        if not scene_changed:
            introduction_text = "；".join(
                (visual, camera_focus, shot.group("audio"))
            )
            for prop_name in sorted(current_props - established_props - start_props):
                intro_context = prop_clauses(introduction_text, prop_name)
                if PROP_INTRO_CUE.search(intro_context) is None:
                    errors.append(
                        f"镜头 {shot_index:02d} 首次建立道具“{prop_name}”时没有识别到"
                        "声音、物理反馈、人物拿出/打开或遮挡揭示等因果入口；"
                        "不能直接以该道具已经在画面中的状态起镜。"
                    )
        established_props.update(current_props)
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
