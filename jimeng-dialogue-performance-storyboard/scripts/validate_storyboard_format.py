#!/usr/bin/env python3
"""Validate hard storyboard contracts; run creative diagnostics only on request."""

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
SHOT_SIZE_TOKEN = re.compile(
    r"局部特写|大特写|中近景|中全景|大全景|特写|近景|中景|全景"
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
SOURCE_EMOTION_RESULTS = (
    (
        "眼眶或眼睛发红",
        re.compile(r"(?:眼眶|眼睛|眼角|双眼).{0,5}(?:发红|泛红|通红|红了|红着)"),
    ),
    ("将要哭泣", re.compile(r"快要哭|要哭出来|泫然欲泣|眼含泪|含着泪|噙着泪")),
)
POST_EMOTION_ACTION_SEED = re.compile(
    r"重心.{0,8}(?:前移|后移|压向|移向|退向|门外|出口|对方)|"
    r"身体.{0,8}(?:前倾|后撤|转向|朝向|靠向|移向)|"
    r"肩背.{0,8}(?:前倾|后撤|塌下|绷紧|失去支撑)|"
    r"手(?:臂|掌|腕)?.{0,10}(?:垂下|放下|松开|收回|抬起|伸向|抓住|扶住|压住|挡住)|"
    r"迈出|跨出|起步|抬脚|脚步|扑向|飞扑|冲向|逼近|靠近|退开|后退|"
    r"抱住|拥抱|占住|让开|离开|转身|起身|坐下|站起|推开|拉开|夺回|递出"
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
CONCRETE_CAMERA_POSITION = re.compile(
    r"低机位|高机位|贴地|平视|仰拍|俯拍|斜俯|正面|侧面|侧后方|肩后|"
    r"门内|门外|门框|桌边|茶几边|车内|车外|车侧|屋内|室内|走廊|"
    r"人物(?:胸口|腰部|肩部|背后|身后|身侧|前方|后方)"
)
ABSTRACT_CAMERA_ENDPOINT = re.compile(
    r"(?:定格|停(?:在|住)|落幅(?:在|到)?)[^，；。]{0,28}"
    r"(?:关系|状态|姿态|压迫感|控制感|矛盾感|氛围|格局)(?:[，；。]|$)"
)
PERFORMANCE_SEQUENCE_TERMS = re.compile(r"随后|接着|然后|紧接着|立刻|立即|再(?:次|度|向|把|将|抬|转|退|进|松|抓)")
CRITICAL_BEAT_LANGUAGE = re.compile(
    r"突然|命中|失效|断裂|断住|截断|震动|提示音|暴露|认出|警觉|危险|"
    r"反转|改写|扑向|飞扑|报警|控制.{0,6}(?:失去|破裂)|策略.{0,6}(?:改变|失效)"
)
PSEUDO_DYNAMIC_MID_MOVEMENT = re.compile(
    r"固定|短促(?:靠近|推进)|(?:轻微|小幅|缓慢|平稳)(?:靠近|推进|推近)"
)
REAL_IMPACT_ROUTE = re.compile(
    r"快速跟拍|快速横移|快速拉开|斜俯|被动.{0,6}退让|遮挡.{0,8}揭示|"
    r"局部特写起幅|大特写起幅|特写起幅|终幅为"
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


def classify_shot_size(shot_setup: str) -> str | None:
    for name, pattern in SHOT_SIZE_PATTERNS:
        if pattern.search(shot_setup):
            return name
    return None


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


def counts_as_expressive_movement(camera_focus: str) -> bool:
    """Treat mixed 'fast but steady' wording as a review signal, not full impact."""
    if not STRONG_EXPRESSIVE_MOVEMENT.search(camera_focus):
        return False
    if CONSERVATIVE_MOVEMENT.search(camera_focus):
        return bool(
            re.search(r"急停|立即停(?:止|住)|斜俯|甩镜|冲击式", camera_focus)
        )
    return bool(EXPRESSIVE_MOVEMENT.search(camera_focus))


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
        active_emotions = [
            (label, pattern)
            for label, pattern in SOURCE_EMOTION_RESULTS
            if pattern.search(source_normalized)
        ]
        restated_emotions: list[tuple[int, str]] = []
        for index, shot in enumerate(shots, start=1):
            visual = shot.group("visual")
            tail = shot.group("tail")
            for label, pattern in active_emotions:
                match = pattern.search(visual)
                if match is None:
                    continue
                after_result = visual[match.end():] + "；" + tail
                if POST_EMOTION_ACTION_SEED.search(after_result):
                    continue
                restated_emotions.append((index, label))
                break
        if restated_emotions:
            sample = "、".join(
                f"{index:02d}（{label}）"
                for index, label in restated_emotions[:6]
            )
            warnings.append(
                f"镜头 {sample} 复用了源文强情绪结果，但其后和尾帧未识别到手臂、重心、"
                "身体朝向、距离或道具形成的动作起势；请补出旧控制失效与下一行动方向，"
                "不要只把原词换成近义词，也不要擅自升级为落泪、痛哭或攻击。"
            )
    if len(shots) < 6:
        return warnings

    durations = []
    for shot in shots:
        duration_match = re.search(r"｜(\d+(?:\.\d+)?)s", shot.group("header"))
        durations.append(float(duration_match.group(1)) if duration_match else 0.0)

    average_duration = sum(durations) / len(durations)
    if len(shots) >= 8 and average_duration < 3.2:
        warnings.append(
            f"全片平均镜长仅 {average_duration:.1f} 秒；对白表演可能被切得过碎。"
            "请先按连续表演单元合并镜头，再保留确有主体、策略、动作结果、"
            "新事实或转场变化的切点。"
        )

    short_runs: list[tuple[int, int]] = []
    run_start: int | None = None
    for index, duration in enumerate(durations, start=1):
        if duration <= 3.0:
            if run_start is None:
                run_start = index
            continue
        if run_start is not None and index - run_start >= 4:
            short_runs.append((run_start, index - 1))
        run_start = None
    if run_start is not None and len(durations) + 1 - run_start >= 4:
        short_runs.append((run_start, len(durations)))
    if short_runs:
        start, end = short_runs[0]
        warnings.append(
            f"镜头 {start:02d}-{end:02d} 连续至少四个不超过3秒的短镜；"
            "三个短镜可以分别承担刺激证据、控制断裂和动作起势/结果，"
            "从第四个开始请检查是否重复景别、视线、表情或同一策略，并用稳定镜承接余波。"
        )

    scene_markers = list(re.finditer(r"(?m)^- 场景 \d{2}｜", normalized))
    scene_ids = [
        sum(marker.start() < shot.start() for marker in scene_markers)
        for shot in shots
    ]

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
    merge_candidates = []
    for index in range(len(shots) - 1):
        current = shots[index]
        following = shots[index + 1]
        combined_visual = visuals[index] + "；" + visuals[index + 1]
        if scene_ids[index] != scene_ids[index + 1]:
            continue
        if current.group("start_type") == "转场起镜" or following.group("start_type") == "转场起镜":
            continue
        if durations[index] > 4.0 or durations[index + 1] > 4.0:
            continue
        if durations[index] + durations[index + 1] > 7.0:
            continue
        if STRATEGY_ACTION.search(combined_visual):
            continue
        if STRONG_EXPRESSIVE_MOVEMENT.search(
            current.group("camera_focus") + "；" + following.group("camera_focus")
        ):
            continue
        if not any(term in combined_visual for term in MICRO_ACTION_TERMS):
            continue
        merge_candidates.append((index + 1, index + 2))
    if merge_candidates:
        sample = "、".join(
            f"{start:02d}-{end:02d}" for start, end in merge_candidates[:4]
        )
        warnings.append(
            f"镜头对 {sample} 均为同场景短镜，未识别到策略动作或独立摄影冲击，"
            "可能只在重复表情、视线或相近信息；请证明各镜新增职责，否则合并为镜内变化。"
        )
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
    pseudo_dynamic_critical = []
    for index, shot in enumerate(shots, start=1):
        duration = durations[index - 1]
        visual = shot.group("visual")
        dialogue = shot.group("dialogue")
        semantic_breaks = visual.count("；") + len(re.findall(r"[。！？?!]", dialogue))
        if duration >= 10 and semantic_breaks >= 3:
            overloaded.append(index)
        combined_beat = "；".join((visual, dialogue, shot.group("audio")))
        size = sizes[index - 1]
        setup = shot.group("shot_setup")
        camera = shot.group("camera_focus")
        if (
            duration >= 10
            and size in {"中景", "中近景", "近景"}
            and "起幅" not in setup
            and "终幅" not in setup
            and CRITICAL_BEAT_LANGUAGE.search(combined_beat)
            and PSEUDO_DYNAMIC_MID_MOVEMENT.search(camera)
            and REAL_IMPACT_ROUTE.search(setup + "；" + camera) is None
        ):
            pseudo_dynamic_critical.append(index)
    if overloaded:
        sample = "、".join(f"{index:02d}" for index in overloaded[:6])
        warnings.append(
            f"镜头 {sample} 时长不少于10秒，且画面动作与台词/OS包含多个语义节拍；"
            "请确认是否把刺激、控制断裂、策略改变、关系结果或长段旁白塞进同一镜。"
        )
    if pseudo_dynamic_critical:
        sample = "、".join(f"{index:02d}" for index in pseudo_dynamic_critical[:6])
        warnings.append(
            f"镜头 {sample} 的关键刺激被困在同一中景/中近景/近景中，"
            "仅用固定或短促推近承载多个职责；请复核是否需要局部刺激/控制断裂镜、"
            "叙事性策略或结果镜，或具有不同观看职责的起幅与终幅。"
            "这是非阻断复核提示；若候选比较证明固定停留最准确，不要为了清除提示机械拆镜。"
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
    missing_camera_position = []
    unsplit_composition = []
    abstract_endpoints = []
    over_choreographed = []
    for index, shot in enumerate(shots, start=1):
        combined = shot.group("shot_setup") + "；" + shot.group("camera_focus")
        if INDIRECT_CAMERA_DESCRIPTION.search(combined):
            indirect_camera.append(index)
        if not CONCRETE_CAMERA_POSITION.search(shot.group("shot_setup")):
            missing_camera_position.append(index)
        composition = shot.group("composition")
        if "构图：" not in composition or "光影：" not in composition:
            unsplit_composition.append(index)
        if ABSTRACT_CAMERA_ENDPOINT.search(shot.group("camera_focus")):
            abstract_endpoints.append(index)
        if len(PERFORMANCE_SEQUENCE_TERMS.findall(shot.group("visual"))) >= 4:
            over_choreographed.append(index)
    if indirect_camera:
        sample = "、".join(f"{index:02d}" for index in indirect_camera[:6])
        warnings.append(
            f"镜头 {sample} 的描述把身侧/肩后机位、人物视线和摄影机路径揉在一起；"
            "请优先改成“从具体可见起点起镜，直接运动，最终定格具体读点”的短句。"
        )

    concrete_threshold = max(5, math.ceil(len(shots) * 0.35))
    if len(missing_camera_position) >= concrete_threshold:
        sample = "、".join(f"{index:02d}" for index in missing_camera_position[:6])
        warnings.append(
            f"镜头 {sample} 等较多景别机位没有识别到低/高机位、俯仰或正侧方向；"
            "请优先补这些直接摄影信息。只有遮挡、轴线、出入口、接触或空间连续需要时，"
            "才补门内外、桌边、车内外等相对实体位置。"
        )

    composition_threshold = max(5, math.ceil(len(shots) * 0.3))
    if len(unsplit_composition) >= composition_threshold:
        sample = "、".join(f"{index:02d}" for index in unsplit_composition[:6])
        warnings.append(
            f"镜头 {sample} 等较多构图/光影字段未按“构图：……；光影：……”分开描述；"
            "请分别写前中后景/左右位置，以及实体光源、进入方向、受光对象和阴影结果。"
        )

    if abstract_endpoints:
        sample = "、".join(f"{index:02d}" for index in abstract_endpoints[:6])
        warnings.append(
            f"镜头 {sample} 的运镜以关系、状态、姿态、压迫感或氛围等抽象意义收尾；"
            "请改为具体人物、身体部位、道具、门窗、车辆或画面边缘的最终位置。"
        )

    if over_choreographed:
        sample = "、".join(f"{index:02d}" for index in over_choreographed[:6])
        warnings.append(
            f"镜头 {sample} 的画面/表演包含过多连续步骤词，可能接近逐帧编舞；"
            "请只冻结刺激、主动作、关键接触、关系结果和尾帧余势，保留自然表演空间。"
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
    parser.add_argument(
        "--source",
        type=Path,
        help="optional source script used to verify explicit transition markers",
    )
    parser.add_argument(
        "--creative-review",
        action="store_true",
        help=(
            "print non-blocking creative diagnostics; use only when diagnosing an "
            "existing storyboard, never as a normal generation gate"
        ),
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
    if args.creative_review:
        for warning in conservatism_warnings(text, source_text):
            print(f"REVIEW: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
