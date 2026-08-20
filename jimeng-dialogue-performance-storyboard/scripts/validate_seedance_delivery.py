#!/usr/bin/env python3
"""Validate the dual-delivery Seedance storyboard contract."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


GLOBAL_SECTIONS = (
    "项目直投参数",
    "全局摄影规则",
    "全局影调",
    "全局光影",
    "全局环境色彩",
    "分场光影继承表",
    "全局正向提示词",
    "全局负面提示词",
)
CORE_FIELDS = (
    "起幅与连续性",
    "摄影与构图",
    "光影、环境色彩与材质",
    "画面与表演时间线",
    "台词与声音层次",
    "落幅状态",
)
OPTIONAL_FIELDS = ("本镜特殊正向约束", "本镜特殊负面约束")
DIRECTOR_FIELDS = (
    "剧情/类型职责",
    "表演与导演视觉",
    "台词事实映射",
    "连续与声音",
    "直投保护",
)
IDENTITY_TEMPLATE = (
    "人物面部身份与识别特征严格继承参考图，脸型及眉眼鼻唇的基础比例、轮廓和相对位置保持稳定；"
    "表情肌肉、眼球视线、眼睑、嘴唇、下颌、头颈姿态与呼吸按剧情自然联动，允许受光、泪光、"
    "伤势和动作产生真实变化，但不得改变人物身份、五官基础比例或重新采样面部结构；"
    "所有镜头人物面部基准统一"
)
CG3D_TEMPLATE = (
    "3D CG写实电影渲染，人物建模采用高精度次世代角色标准，8K纹理贴图，皮肤细腻完整，"
    "均匀皮肤光照，柔和面部补光，次表面散射皮肤，干净面部光影，皮肤纹理稳定"
)
FACE_NEGATIVE_TEMPLATE = (
    "面部斑驳，脸部黑斑，脏色块，皮肤阴影斑块，面部噪点，脸部脏污，跨镜头人脸不一致，同人物多张脸"
)
CG3D_NEGATIVE = "法线错误，贴图错乱"
NON_REALISTIC_3D_STYLE = re.compile(
    r"卡通\s*3D|3D\s*卡通|黏土|粘土|低多边形|low[\s-]*poly|非写实\s*(?:3D|三维)",
    re.IGNORECASE,
)
REALISTIC_3D_STYLE = re.compile(
    r"3D|三维|次世代(?:写实|角色)?|CG\s*写实",
    re.IGNORECASE,
)

SHOT_HEADER = re.compile(
    r"(?m)^### 镜头S(?P<scene>\d+)-(?P<number>\d+)｜(?:时长：)?"
    r"(?P<duration>\d+(?:\.\d+)?)秒｜(?P<label>[^\r\n]+)$"
)
FIELD_HEADER = re.compile(r"(?m)^- \*\*(?P<name>[^*\r\n]+)\*\*：(?P<value>[^\r\n]*)$")
TIMELINE_ROW = re.compile(
    r"(?m)^[ \t]*-\s+`?(?P<start>\d+(?:\.\d+)?)\s*[—–-]\s*"
    r"(?P<end>\d+(?:\.\d+)?)秒\s*｜(?P<stage>[^`\r\n：:]+)`?\s*[：:]"
    r"(?P<body>[^\r\n]*)"
)
SCENE_HEADER = re.compile(r"(?m)^# 场景(?P<label>[^：｜\r\n]*)[：｜](?P<name>[^\r\n]+)$")
DIRECTOR_SHOT = re.compile(
    r"(?m)^### 镜头\s*S(?P<scene>\d+)-(?P<number>\d+)｜"
    r"(?P<duration>\d+(?:\.\d+)?)秒(?:｜[^\r\n]+)?$"
)
DIRECTOR_SCENE_HEADER = re.compile(r"(?m)^## 场景(?P<label>[^：\r\n]*)：(?P<name>[^\r\n]+)$")
SHOT_SIZE = re.compile(r"局部特写|大特写|中近景|中全景|大全景|特写|近景|中景|全景")
INTERNAL_MARKERS = re.compile(
    r"STYLE_V\d+|TONE_V\d+|LIGHT_V\d+|PALETTE(?:_MASTER|_V|\b)|"
    r"SCENE_PALETTE|SHOT_DELTA|EFFECT_(?:LIBRARY|GATE)|FX\d+|"
    r"\b(?:PRECURSOR|ACTIVE|SUSTAIN|DISSIPATE|ENDED|OFF)\b|"
    r"(?<![A-Za-z0-9])(?:G|C|P)\d{2}(?![A-Za-z0-9])|"
    r"#[0-9A-Fa-f]{6}(?![0-9A-Fa-f])|RGB\s*\(|@图片\d+|"
    r"/(?:Users|Volumes)/[^\s，。；）)]+|[A-Za-z]:\\[^\s，。；）)]+"
)
RELATIVE_REFERENCE = re.compile(
    r"沿用上一镜|继承上一镜|继续上一镜|同上|参照上一镜|上一镜保持不变"
)
EMPTY_EFFECT = re.compile(r"特效\s*[：:]\s*无|本镜无特效|无特效镜头")
ABSTRACT_PERFORMANCE = re.compile(
    r"紧张|绷紧|错愕|震惊|惊讶|窘迫|羞耻|慌乱|尴尬|平静|冷静|愤怒|悲伤|痛苦|压迫感|镇定|自尊受挫"
)
STABLE_PERFORMANCE = re.compile(
    r"(?:保持|维持|延续|仍(?:然)?保持|持续处于|处于)[^。；\n]{0,16}"
    r"(?:平静|冷静|镇定|紧张|绷紧|悲伤|痛苦|愤怒)"
)
PERFORMANCE_CARRIER = re.compile(
    r"视线|目光|眼球|瞳孔|抬眼|低头|呼吸|吸气|停手|抬手|嘴唇|唇线|下颌|眉眼|肩背|肩膀|重心|距离|手指|手掌|握紧|收紧|松开|道具|声线|语速|声量|停顿|尾音|口型|姿态|步幅|身体|转身|停住|看向|移开|锁定"
)
PERFORMANCE_TRIGGER = re.compile(
    r"触发|刺激|听见|看见|意识到|确认|关键词|说到|说前|台词开始|最后一个字|尾音|反应延迟|回应"
)
PERFORMANCE_TERMINAL = re.compile(
    r"停止|停住|停在|保持|落下|结束|结果|残留|余波|锁定|完成|不再|持续|退出状态|镜尾"
)
DIALOGUE_BEFORE = re.compile(
    r"说前|准备|起口前|台词前|开口前|出声前|话音未起|"
    r"(?:吸气|呼吸|停手|停住|抬眼|收回视线|调整重心)[^。；\n]{0,16}(?:开口|出声|说)"
)
DIALOGUE_DURING = re.compile(
    r"说中|关键词|语义转折|台词开始|重音|说到|语速|声线|声量|音量|"
    r"字音|句中|开口\s*[：:]|[：:]\s*[“\"]"
)
DIALOGUE_AFTER = re.compile(
    r"说后|反应延迟|最后一个字|尾音|余波|残留|话落|句末|说完|说罢|"
    r"台词结束|嘴唇闭合|闭口|收声"
)
LIVE_DIALOGUE = re.compile(
    r"人物台词|仅[^；。\n]{0,24}(?:准确)?口型|"
    r"(?:^|[；。\n])[^：:\n]{1,16}[：:]\s*[“\"]"
)
SHOT_SIZE_STRUCTURE = re.compile(
    r"\d+(?:\.\d+)?\s*[—–-]\s*\d+(?:\.\d+)?秒|"
    r"直接切(?:至|到|回)|切入|切回|内部切点|主体交接|焦点(?:从|由).{0,20}(?:转移|交接|落到)"
)
DIRECT_DIALOGUE_AUDIT = re.compile(
    r"(?:原句|处理方式|事实依据|最终执行句)\s*[：:]"
)
TRANSITION_SOURCE = re.compile(r"【\s*转场\s*】|\[\s*转场\s*\]|转场\s*[：:]")
TRANSITION_BRIDGE = re.compile(
    r"声音桥|尾音(?:持续|延续)|声音(?:延续|先行|承接)|动作匹配|匹配切|"
    r"物体匹配|形状匹配|遮挡(?:切换|占满|退开)|占满画面|光影匹配|"
    r"运动方向延续|同方向接住|甩镜.{0,8}(?:切|接)|门板.{0,8}(?:合拢|打开)"
)


@dataclass(frozen=True)
class Shot:
    scene: int
    number: int
    duration: str
    label: str
    fields: tuple[tuple[str, str], ...]

    @property
    def shot_id(self) -> str:
        return f"S{self.scene}-{self.number:02d}"


def section_body(text: str, heading: str) -> str | None:
    pattern = re.compile(
        rf"(?ms)^## 【{re.escape(heading)}】\s*\n(?P<body>.*?)(?=^## 【|^# 场景|\Z)"
    )
    match = pattern.search(text)
    return match.group("body").strip() if match else None


def requires_realistic_3d_template(project_parameters: str) -> bool:
    """Classify the declared medium without reading the prompt template itself."""
    if NON_REALISTIC_3D_STYLE.search(project_parameters):
        return False
    return bool(REALISTIC_3D_STYLE.search(project_parameters))


def parse_fields(block: str) -> tuple[tuple[str, str], ...]:
    matches = list(FIELD_HEADER.finditer(block))
    parsed: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
        continuation = block[match.end():end].strip()
        value = match.group("value").strip()
        if continuation:
            value = f"{value}\n{continuation}".strip()
        parsed.append((match.group("name").strip(), value))
    return tuple(parsed)


def parse_shots(text: str) -> list[Shot]:
    headers = list(SHOT_HEADER.finditer(text))
    shots: list[Shot] = []
    for index, header in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        block = text[header.end():end]
        shots.append(
            Shot(
                scene=int(header.group("scene")),
                number=int(header.group("number")),
                duration=header.group("duration"),
                label=header.group("label").strip(),
                fields=parse_fields(block),
            )
        )
    return shots


def shot_size_sequence(text: str) -> list[str]:
    result: list[str] = []
    for match in SHOT_SIZE.finditer(text):
        token = match.group(0)
        if result and token == result[-1]:
            continue
        if token == "特写" and match.start() > 0:
            prefix = text[max(0, match.start() - 2):match.start()]
            if prefix in {"大", "部"} or prefix.endswith("局部"):
                continue
        if token == "全景" and match.start() > 0:
            prefix = text[max(0, match.start() - 1):match.start()]
            if prefix in {"大", "中"}:
                continue
        if token == "近景" and match.start() > 0 and text[match.start() - 1] == "中":
            continue
        result.append(token)
    return result


def validate_direct(text: str, source_text: str | None = None) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    errors: list[str] = []

    if "Seedance独立直投版" not in normalized[:200]:
        errors.append("标题必须明确标注“Seedance独立直投版”。")

    positions: list[int] = []
    for heading in GLOBAL_SECTIONS:
        marker = f"## 【{heading}】"
        count = normalized.count(marker)
        if count != 1:
            errors.append(f"全局章节“{heading}”必须且只能出现一次；当前出现 {count} 次。")
            continue
        positions.append(normalized.index(marker))
        body = section_body(normalized, heading)
        if body is None or not body:
            errors.append(f"全局章节“{heading}”不得为空。")
    if len(positions) == len(GLOBAL_SECTIONS) and positions != sorted(positions):
        errors.append(
            "全局章节顺序错误；必须按项目直投参数、摄影规则、影调、光影、环境色彩、分场光影继承表、正向、负向排列。"
        )

    internal_hits = sorted(set(match.group(0) for match in INTERNAL_MARKERS.finditer(normalized)))
    if internal_hits:
        errors.append("直投版残留内部标识/颜色代码/本地路径：" + "、".join(internal_hits[:12]))
    if RELATIVE_REFERENCE.search(normalized):
        errors.append("直投版使用了“沿用/继承上一镜/同上”等省略指代；每镜必须自足复述当前事实。")
    if EMPTY_EFFECT.search(normalized):
        errors.append("未激活特效必须零提及；删除“特效：无/本镜无特效”等文字。")
    if DIRECT_DIALOGUE_AUDIT.search(normalized):
        errors.append("直投版残留原句/处理方式/事实依据等台词审核信息；只保留最终执行台词。")

    positive = section_body(normalized, "全局正向提示词") or ""
    negative = section_body(normalized, "全局负面提示词") or ""
    project_parameters = section_body(normalized, "项目直投参数") or ""
    if positive.count(IDENTITY_TEMPLATE) != 1:
        errors.append("全局正向必须逐字且只包含一次通用身份固定模板。")
    if negative.count(FACE_NEGATIVE_TEMPLATE) != 1:
        errors.append("全局负向必须逐字且只包含一次面部稳定负面模板。")
    is_realistic_3d = requires_realistic_3d_template(project_parameters)
    if is_realistic_3d:
        if positive.count(CG3D_TEMPLATE) != 1:
            errors.append("3D 写实项目全局正向必须逐字且只包含一次 3D CG 写实渲染模板。")
        if negative.count(CG3D_NEGATIVE) != 1:
            errors.append("3D 写实项目全局负向必须逐字且只包含一次“法线错误，贴图错乱”。")
    else:
        if positive.count(CG3D_TEMPLATE) != 0:
            errors.append("非 3D 写实项目禁止包含 3D CG 写实渲染模板。")
        if negative.count(CG3D_NEGATIVE) != 0:
            errors.append("非 3D 写实项目禁止包含“法线错误，贴图错乱”等 3D 专属负向词。")

    scenes = list(SCENE_HEADER.finditer(normalized))
    if not scenes:
        errors.append("至少需要一个“# 场景…｜场景名称”章节。")
    for index, scene in enumerate(scenes):
        end = scenes[index + 1].start() if index + 1 < len(scenes) else len(normalized)
        block = normalized[scene.start():end]
        if "## 【场景视觉方案】" not in block:
            errors.append(f"场景“{scene.group('name')}”缺少【场景视觉方案】。")
        else:
            for item in ("场景影调", "场景环境色彩", "场景光影", "光影变化触发"):
                if not re.search(rf"(?m)^- {item}：\S", block):
                    errors.append(f"场景“{scene.group('name')}”的视觉方案缺少“{item}”。")
        if "## 【Seedance完整独立镜头】" not in block:
            errors.append(f"场景“{scene.group('name')}”缺少【Seedance完整独立镜头】。")
        if "## 【场景空间位置关系】" not in block:
            errors.append(
                f"场景“{scene.group('name')}”缺少【场景空间位置关系】；无场景图时也必须按剧本推导。"
            )
        else:
            space = re.search(
                r"(?ms)^## 【场景空间位置关系】\s*\n(?P<body>.*?)(?=^## 【场景视觉方案】)",
                block,
            )
            if space is None or not space.group("body").strip():
                errors.append(f"场景“{scene.group('name')}”的空间位置关系不得为空。")
            else:
                space_body = space.group("body")
                if "空间依据" not in space_body:
                    errors.append(
                        f"场景“{scene.group('name')}”的空间位置关系缺少“空间依据”（场景图锁定/剧本推导/混合建立）。"
                    )

    shots = parse_shots(normalized)
    if not shots:
        errors.append("未找到符合“### 镜头S1-01｜X秒｜短语描述”的镜头。")
    expected_by_scene: dict[int, int] = {}
    for shot in shots:
        expected = expected_by_scene.get(shot.scene, 1)
        if shot.number != expected:
            errors.append(f"镜头 {shot.shot_id} 编号不连续；场景 S{shot.scene} 期望 {expected:02d}。")
        expected_by_scene[shot.scene] = shot.number + 1

        names = [name for name, _ in shot.fields]
        core_names = [name for name in names if name in CORE_FIELDS]
        if core_names != list(CORE_FIELDS):
            errors.append(
                f"镜头 {shot.shot_id} 核心字段缺失或顺序错误；必须依次为："
                + "、".join(CORE_FIELDS)
            )
        unknown = [name for name in names if name not in CORE_FIELDS + OPTIONAL_FIELDS]
        if unknown:
            errors.append(f"镜头 {shot.shot_id} 出现未知字段：" + "、".join(unknown))
        optional_order = [name for name in names if name in OPTIONAL_FIELDS]
        if optional_order not in ([], [OPTIONAL_FIELDS[0]], [OPTIONAL_FIELDS[1]], list(OPTIONAL_FIELDS)):
            errors.append(f"镜头 {shot.shot_id} 的本镜特殊正负面顺序错误。")
        if len(names) != len(set(names)):
            errors.append(f"镜头 {shot.shot_id} 存在重复字段。")

        values = dict(shot.fields)
        for field in CORE_FIELDS:
            value = values.get(field, "").strip()
            if not value or value in {"无", "同上", "沿用上一镜"}:
                errors.append(f"镜头 {shot.shot_id} 的“{field}”必须填写完整执行内容。")
        for field in OPTIONAL_FIELDS:
            if field in values and values[field].strip() in {"", "无", "无特殊约束"}:
                errors.append(f"镜头 {shot.shot_id} 的“{field}”无内容时应删除整字段。")
            if field in values and any(
                template in values[field]
                for template in (IDENTITY_TEMPLATE, CG3D_TEMPLATE, FACE_NEGATIVE_TEMPLATE)
            ):
                errors.append(f"镜头 {shot.shot_id} 的“{field}”重复了全局固定模板。")

        timeline = values.get("画面与表演时间线", "")
        timeline_rows = list(TIMELINE_ROW.finditer(timeline))
        if not timeline_rows:
            errors.append(
                f"镜头 {shot.shot_id} 的画面与表演时间线必须使用逐行“0.0—X.X秒｜阶段名：”结构。"
            )
        else:
            intervals = [
                (float(row.group("start")), float(row.group("end")))
                for row in timeline_rows
            ]
            if abs(intervals[0][0]) > 0.001:
                errors.append(f"镜头 {shot.shot_id} 的时间线必须从 0.0 秒开始。")
            for index, (start, end) in enumerate(intervals):
                if end <= start:
                    errors.append(
                        f"镜头 {shot.shot_id} 的第 {index + 1} 个时间窗终点必须晚于起点。"
                    )
                if index and abs(start - intervals[index - 1][1]) > 0.001:
                    errors.append(
                        f"镜头 {shot.shot_id} 的时间窗不连续；第 {index} 段终点与第 {index + 1} 段起点必须一致。"
                    )
            if abs(intervals[-1][1] - float(shot.duration)) > 0.001:
                errors.append(
                    f"镜头 {shot.shot_id} 的时间线末段必须到达镜头总时长 {shot.duration} 秒。"
                )

            timeline_text = "\n".join(row.group(0) for row in timeline_rows)
            for row in timeline_rows:
                row_text = row.group(0)
                if not ABSTRACT_PERFORMANCE.search(row_text):
                    continue
                # A maintained emotional baseline is already an executable
                # state. New emotional changes still need a carrier, while
                # their trigger and settlement may live in adjacent windows.
                if STABLE_PERFORMANCE.search(row_text):
                    continue
                if (
                    not PERFORMANCE_CARRIER.search(row_text)
                    or not PERFORMANCE_TRIGGER.search(timeline_text)
                    or not PERFORMANCE_TERMINAL.search(timeline_text)
                ):
                    errors.append(
                        f"镜头 {shot.shot_id} 的表演时间窗把情绪压成抽象标签；"
                        "动态情绪需要可见或可听载体，并在整段时间线中形成可追踪的触发与停止/保持结果。"
                    )
                    break

        dialogue = values.get("台词与声音层次", "")
        if dialogue and "无对白" not in dialogue and LIVE_DIALOGUE.search(dialogue):
            if not DIALOGUE_BEFORE.search(dialogue) or not DIALOGUE_DURING.search(dialogue) or not DIALOGUE_AFTER.search(dialogue):
                errors.append(
                    f"镜头 {shot.shot_id} 的台词与声音层次缺少说前/说中/说后表演链；"
                    "可使用自然语言表达开口前准备、台词中的声音/策略变化和话落后的余波，不要求固定标签。"
                )

        framing = values.get("摄影与构图", "")
        sizes = shot_size_sequence(framing)
        if len(sizes) > 2 and not SHOT_SIZE_STRUCTURE.search(framing):
            errors.append(
                f"镜头 {shot.shot_id} 出现三个以上景别（{' -> '.join(sizes)}）；"
                "若需要多阶段景别，请用明确时间窗、主体/焦点交接或内部切点写清顺序。"
            )
        landing = values.get("落幅状态", "")
        if re.search(r"自动复位|恢复初始|回到起点", landing):
            errors.append(f"镜头 {shot.shot_id} 的落幅包含自动复位；动作终点必须保持。")

    if source_text and TRANSITION_SOURCE.search(source_text) and not TRANSITION_BRIDGE.search(normalized):
        errors.append("源剧本含明确转场，但直投版没有识别到声音/动作/物体/遮挡/光影/方向承接。")
    return errors


def validate_director_pair(direct_text: str, director_text: str) -> list[str]:
    errors: list[str] = []
    if "导演审核版" not in director_text[:200]:
        errors.append("导演文件标题必须明确标注“导演审核版”。")
    for section in (
        "项目与事实锁",
        "叙事立场",
        "全局摄影圣经",
        "全局视觉结论",
        "时长预算与计算",
        "人物表演与声音锚点",
    ):
        if f"## {section}" not in director_text:
            errors.append(f"导演审核版缺少“## {section}”。")

    director_scenes = list(DIRECTOR_SCENE_HEADER.finditer(director_text))
    if not director_scenes:
        errors.append("导演审核版至少需要一个“## 场景…：场景名称”章节。")
    for index, scene in enumerate(director_scenes):
        end = director_scenes[index + 1].start() if index + 1 < len(director_scenes) else len(director_text)
        block = director_text[scene.start():end]
        if "### 场景空间与视觉结论" not in block:
            errors.append(f"导演审核版场景“{scene.group('name')}”缺少“场景空间与视觉结论”。")
        asset_prompt = re.search(
            r"(?ms)^### 场景资产图提示词\s*\n(?P<body>.*?)(?=^### |\Z)",
            block,
        )
        if asset_prompt is None or not asset_prompt.group("body").strip():
            errors.append(f"导演审核版场景“{scene.group('name')}”缺少“场景资产图提示词”。")
    direct = [(s.shot_id, s.duration) for s in parse_shots(direct_text)]
    director_matches = list(DIRECTOR_SHOT.finditer(director_text))
    director = [
        (f"S{int(m.group('scene'))}-{int(m.group('number')):02d}", m.group("duration"))
        for m in director_matches
    ]
    if direct != director:
        errors.append(
            "导演审核版与直投版的镜号/顺序/时长不一致；"
            f"直投={direct}，导演={director}。"
        )
    for index, match in enumerate(director_matches):
        end = director_matches[index + 1].start() if index + 1 < len(director_matches) else len(director_text)
        block = director_text[match.end():end]
        shot_id = f"S{int(match.group('scene'))}-{int(match.group('number')):02d}"
        positions: list[int] = []
        for field in DIRECTOR_FIELDS:
            field_match = re.search(rf"(?m)^- {re.escape(field)}：\S", block)
            if field_match is None:
                errors.append(f"导演审核版镜头 {shot_id} 缺少“{field}”。")
            else:
                positions.append(field_match.start())
        if len(positions) == len(DIRECTOR_FIELDS) and positions != sorted(positions):
            errors.append(f"导演审核版镜头 {shot_id} 的结构化字段顺序错误。")
        dialogue_mapping = re.search(r"(?m)^- 台词事实映射：(?P<value>[^\r\n]+)$", block)
        if dialogue_mapping is not None:
            value = dialogue_mapping.group("value")
            if not value.strip():
                errors.append(f"导演审核版镜头 {shot_id} 的台词事实映射不得为空。")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, help="Seedance independent direct Markdown")
    parser.add_argument("--source", type=Path, help="optional source script")
    parser.add_argument("--director", type=Path, help="optional director-review Markdown")
    args = parser.parse_args()

    try:
        direct_text = args.path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        print(f"cannot read {args.path}: {exc}", file=sys.stderr)
        return 2

    source_text = None
    if args.source:
        try:
            source_text = args.source.read_text(encoding="utf-8-sig")
        except OSError as exc:
            print(f"cannot read source {args.source}: {exc}", file=sys.stderr)
            return 2

    errors = validate_direct(direct_text, source_text)
    if args.director:
        try:
            director_text = args.director.read_text(encoding="utf-8-sig")
        except OSError as exc:
            print(f"cannot read director {args.director}: {exc}", file=sys.stderr)
            return 2
        errors.extend(validate_director_pair(direct_text, director_text))

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"delivery valid: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
