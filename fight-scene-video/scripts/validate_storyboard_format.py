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
LEGACY_DOCUMENT = re.compile(rf"\A{BLOCK}(?:\n\n{BLOCK})*\n?\Z")
SEGMENT_HEADER = r"生成段 \d{2}｜[^｜\r\n]+｜\d+(?:\.\d+)?s"
SEGMENT = rf"{SEGMENT_HEADER}\n\n{BLOCK}(?:\n\n{BLOCK})*"
MASTER_DOCUMENT = re.compile(rf"\A{SEGMENT}(?:\n\n{SEGMENT})*\n?\Z")
SEGMENT_LINE = re.compile(
    r"(?m)^生成段 (?P<number>\d{2})｜(?P<name>[^｜\r\n]+)｜"
    r"(?P<duration>\d+(?:\.\d+)?)s$"
)
SHOT = re.compile(
    rf"(?P<header>{HEADER})\n\n"
    r"画面内容：(?P<visual>[^\r\n]+)\n\n"
    r"特效：(?P<vfx>[^\r\n]+)\n\n"
    r"光影：(?P<light>[^\r\n]+)\n\n"
    r"音效：(?P<audio>[^\r\n]+)\n\n"
    r"台词：(?P<dialogue>[^\r\n]+)"
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
CLOSE_SHOT = re.compile(r"中近景|近景|特写|大特写")
WIDE_SHOT = re.compile(r"远景|大远景|超远景|大全景")
CLOSE_RANGE_CONFLICT = re.compile(
    r"完整全身|全身路径|全身轨迹|完整路径|战场尺度|群体阵型|大范围追逐|"
    r"多人相对方位|全场位置|宏大尺度"
)
WIDE_DETAIL_CONFLICT = re.compile(
    r"微表情|瞳孔|眼睫|嘴角|唇角|指尖细节|手指细节|细微眼神|眼神细节|"
    r"细小伤口|符纹细节"
)
IMPOSSIBLE_CAMERA_PATH = re.compile(
    r"(?:摄影机|镜头)[^。；;，,\n]{0,24}(?:穿过墙|穿过墙体|穿墙|穿过柱|穿过人物身体|"
    r"穿过人物|穿过武器|穿过实体|穿过爆炸中心|穿入爆炸核心)"
)
VFX_OCCLUDES_ACTION = re.compile(
    r"(?:特效|光幕|爆炸|强光|白闪|烟尘)[^。；;，,\n]{0,24}"
    r"(?:遮住|吞没|盖住)[^。；;，,\n]{0,24}(?:接触点|动作路径|人物剪影|落点|源点|战果)"
)
DEPTH_BACKGROUND = re.compile(r"后景|背景|后侧|身后|背后|画面后侧|后方|远处|右上方|左上方|高位观察者")
FACE_TO_FACE = re.compile(r"正面朝向镜头|正面对(?:着|向)|面向镜头|面对面|对峙|正面相对")
DEPTH_CONTINUITY_CONFLICT = re.compile(
    rf"(?:{FACE_TO_FACE.pattern}).{{0,100}}(?:{DEPTH_BACKGROUND.pattern})|"
    rf"(?:{DEPTH_BACKGROUND.pattern}).{{0,100}}(?:{FACE_TO_FACE.pattern})"
)
PROP_DRIFT = re.compile(
    r"(?:道具|剑|刀|枪|琴|笛|扇|书|笔|符|令牌|杯|碗|伞|鞭|铃|法器|武器)"
    r"[^。；;，,\n]{0,30}"
    r"(?:突然|无因|莫名|凭空|自动|不知何时)"
    r"[^。；;，,\n]{0,30}"
    r"(?:出现|消失|回到|变成|换到|落在|插在|打开|闭合|破损|碎裂|染血|发光)|"
    r"(?:左手|右手)[^。；;，,\n]{0,24}(?:突然|无因|莫名|凭空|自动|不知何时)"
    r"[^。；;，,\n]{0,24}(?:右手|左手|换手)"
)
CAMERA_ANCHOR = re.compile(
    r"固定|定机位|稳定|推进|推近|后退|拉远|横移|平移|升降|拉升|下降|摇移|"
    r"跟随|侧跟|贴身追随|绕行|过肩|贴地|俯冲|急停|加速|低机位|高机位|俯角|仰角|平视|鸟瞰|俯视|"
    r"仰视|正面|侧面|背面|侧前方|侧后方|前方|后方|上方|下方|轴线|纵深|"
    r"横向|门口|墙边|柱后|台阶|桥面|屋顶|地面|肩侧|手边|脚边|轨道|"
    r"稳定器|手持|长焦|广角|现实摄影机|增强虚拟摄影机|虚拟摄影机|转场摄影机|"
    r"遮挡转场|媒介转场|烟尘转场|粒子转场|能量表面"
)
PHYSICAL_CHEAT_CAMERA = re.compile(
    r"全知视角|瞬移视角|无限小镜头|同时看清|全程看清|清楚可见|"
    r"镜头穿梭|创意运镜|"
    r"(?:(?:镜头|摄影机)[^。；;，,\n]{0,24}(?:穿入|钻入|进入|穿过|穿越)"
    r"[^。；;，,\n]{0,24}(?:瞳孔|眼睛|身体|胸口|伤口|墙|墙体|柱|人物|"
    r"武器|实体|爆炸中心|爆炸核心))"
)
COMPOSITE_VIEW_TASK = re.compile(
    r"(?:同时|全程|一镜到底)[^。；;，,\n]{0,80}"
    r"(?:微表情|眼神细节|手指细节|指尖|脸部反应|瞳孔)[^。；;，,\n]{0,80}"
    r"(?:全身路径|全身位移|群体|全场|战场|落点|环境结果|VFX源点|接触点)|"
    r"(?:同时|全程|一镜到底)[^。；;，,\n]{0,80}"
    r"(?:全身路径|全身位移|群体|全场|战场|落点|环境结果|VFX源点|接触点)"
    r"[^。；;，,\n]{0,80}(?:微表情|眼神细节|手指细节|指尖|脸部反应|瞳孔)"
)


def validate(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    errors: list[str] = []
    is_master = normalized.startswith("生成段 ")
    document_pattern = MASTER_DOCUMENT if is_master else LEGACY_DOCUMENT
    if not document_pattern.fullmatch(normalized):
        errors.append(
            "正文未严格匹配固定格式：新版多段文件须由生成段标题和镜头块组成；"
            "旧版单段文件可直接由镜头块组成。镜头标题后依次为画面内容、特效、光影、音效、台词，字段间一个空行。"
        )
        return errors

    if is_master:
        segment_headers = list(SEGMENT_LINE.finditer(normalized))
        segment_numbers = [int(match.group("number")) for match in segment_headers]
        expected_segments = list(range(1, len(segment_numbers) + 1))
        if segment_numbers != expected_segments:
            errors.append(
                f"生成段编号必须从01开始连续递增；当前为 {segment_numbers}。"
            )

        segments: list[tuple[int, str, float, str]] = []
        for index, match in enumerate(segment_headers):
            body_start = match.end() + 2
            body_end = (
                segment_headers[index + 1].start() - 2
                if index + 1 < len(segment_headers)
                else len(normalized)
            )
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
        segments = [(1, "单生成段", -1.0, normalized.rstrip("\n"))]

    numbers = [int(value) for value in re.findall(r"(?m)^镜号 (\d{2})｜", normalized)]
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        errors.append(f"镜号必须从01开始连续递增；当前为 {numbers}。")

    for segment_number, segment_name, declared_duration, segment_body in segments:
        durations = [
            float(value)
            for value in re.findall(
                r"(?m)^镜号 \d{2}｜[^｜\r\n]+｜[^｜\r\n]+｜(\d+(?:\.\d+)?)s$",
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

    for shot_index, match in enumerate(SHOT.finditer(normalized), start=1):
        header_parts = match.group("header").split("｜")
        shot_size = header_parts[1] if len(header_parts) > 1 else ""
        camera_header = header_parts[2] if len(header_parts) > 2 else ""
        body = " ".join(
            match.group(name)
            for name in ("visual", "vfx", "light", "audio", "dialogue")
        )
        physical_text = f"{match.group('header')} {body}"
        if not CAMERA_ANCHOR.search(camera_header):
            errors.append(
                f"镜号 {shot_index:02d} 的运镜/机位栏“{camera_header}”缺少可验证的现实或虚拟机位、角度或路径锚点；"
                "请写明摄影机类型、固定/推进/后退/横移/升降/俯冲/转场等路径，以及相对人物、地标、轴线、高度或媒介的位置。"
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

        if CLOSE_SHOT.search(shot_size) and CLOSE_RANGE_CONFLICT.search(physical_text):
            errors.append(
                f"镜号 {shot_index:02d} 的景别“{shot_size}”疑似承担了全身路径、群体阵型或战场尺度；"
                "请改为中全景/全景/远景，或拆出可拍的路径/规模镜。"
            )

        if WIDE_SHOT.search(shot_size) and WIDE_DETAIL_CONFLICT.search(physical_text):
            errors.append(
                f"镜号 {shot_index:02d} 的景别“{shot_size}”疑似承担了微表情、手指或细节读取；"
                "请补近景/特写，或删除该景别无法读取的细节任务。"
            )

        impossible_path = IMPOSSIBLE_CAMERA_PATH.search(physical_text)
        if impossible_path:
            errors.append(
                f"镜号 {shot_index:02d} 含空间不成立的摄影机路径“{impossible_path.group(0)}”；"
                "请改为绕行、增强虚拟路径、内切、遮挡/VFX转场或重新设定机位；透明烟尘、粒子和非实体能量可作为明确媒介。"
            )

        occlusion = VFX_OCCLUDES_ACTION.search(physical_text)
        if occlusion:
            errors.append(
                f"镜号 {shot_index:02d} 含VFX遮挡主事件风险“{occlusion.group(0)}”；"
                "宏大特效不得遮掉接触点、动作路径、源点、落点或战果。"
            )

        cheat = PHYSICAL_CHEAT_CAMERA.search(physical_text)
        if cheat:
            errors.append(
                f"镜号 {shot_index:02d} 含无空间桥或全知摄影表述“{cheat.group(0)}”；"
                "请改成现实摄影机、可解释的增强虚拟路径、明确媒介转场、内切或拆镜，不得用全知/无桥穿梭/同时看清解决观看矛盾。"
            )

        composite = COMPOSITE_VIEW_TASK.search(physical_text)
        if composite:
            errors.append(
                f"镜号 {shot_index:02d} 疑似把互斥观看任务压进同一镜“{composite.group(0)}”；"
                "请保留一个第一读点，将脸部/手部细节、全身路径、群体关系、VFX源点、接触点或环境结果拆到相邻镜。"
            )

        depth_conflict = DEPTH_CONTINUITY_CONFLICT.search(physical_text)
        if depth_conflict and CLOSE_SHOT.search(shot_size):
            errors.append(
                f"镜号 {shot_index:02d} 出现对峙深度关系冲突“{depth_conflict.group(0)}”；"
                "近景/特写里不要让一人做正面主角、另一人退成后景轮廓仍维持同一面对面关系；"
                "请改为反打、过肩、双人中景或拆成单人反应镜。"
            )

        prop_drift = PROP_DRIFT.search(physical_text)
        if prop_drift:
            errors.append(
                f"镜号 {shot_index:02d} 含明显道具漂移表述“{prop_drift.group(0)}”；"
                "关键道具的归属、左右手、放置点、开合、破损、染血、发光或残留变化必须有可见交接/掉落/击飞/打开/破损原因。"
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
