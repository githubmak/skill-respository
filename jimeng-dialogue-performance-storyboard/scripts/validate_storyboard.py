#!/usr/bin/env python3
"""Fast structural validator for jimeng-dialogue-performance-storyboard outputs."""

from __future__ import annotations

import re
import sys
from pathlib import Path


CHILD_FIELDS = ["【镜号】", "【画面描述｜直接复制】", "【表演与声音】", "【状态继承】"]
REQUIRED_TOP_SECTIONS = [
    "## 使用说明",
    "## 全局锁定",
    "## 通用负面提示词｜直接复制",
    "## 场景状态表",
    "## 分镜投喂卡",
]
DEPRECATED_HEADINGS = [
    "## 全局锁帧模板", "## 负面提示词｜直接复制", "## 角色锁定表",
    "## 人物位置与拍摄侧锁定表", "## 场景与道具锁定表", "## 分镜正式投喂表",
    "【画面描述｜直接复制投喂（含空间/表演/台词/运镜）】", "【画面描述｜直接复制投喂】",
    "【导演校验记录】", "【主体与空间锁定】", "【摄影合同】", "【运镜/推拉/反打时机】",
    "【情绪与表演时间轴】", "【台词/OS/系统声与语气】",
]
BANNED_DIRECT = [
    "继承", "延续上一镜", "空间保持", "位置继承", "物理座位不变", "剪辑", "切到", "反打到",
    "下一镜执行", "声音语气：", "表情：", "动作：", "情绪：", "脑海浮现", "后期插入", "左外",
    "当前主角", "当前对话者", "视情况",
]
NEGATIVE_NEEDLE = "人物僵硬、全身静止、无眨眼"
CUTAWAY_NEEDLES = ("镜头不拍人物", "空镜", "空椅", "门缝", "水纹", "走廊灯光")
SHOT_SIZE_TERMS = ("特写", "近景", "中近景", "中景", "中远景", "全景", "远景")
CAMERA_TERMS = ("镜头", "相机", "机位", "平视", "俯视", "仰视", "侧后方", "斜前方")
CAMERA_STATE_TERMS = ("固定", "保持", "静止", "推", "拉", "摇", "移", "跟", "转焦", "拉焦", "上摇", "下摇")
RELATION_TERMS = ("面对", "相对", "身侧", "身后", "前方", "后方", "之间", "隔着", "挽着", "肩线", "右手", "左手", "朝向", "背对", "侧身")
FACING_TERMS = ("面向", "背向", "身体朝向", "身体仍朝", "上身朝向", "头部转向", "头部偏向")
POST_AUDIO_TERMS = ("OS", "OV", "系统音", "内心独白", "画外", "后期", "配音", "旁白")
VISIBLE_SPEECH_TERMS = ("可见口型", "可见说话者", "开口", "说：", "说:", "说“", "问：", "问:", "喊：", "喊:", "低语", "回应", "反问")


def compact_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def iter_groups(text: str):
    header = r"^####\s+(S\d+-\d+)(?:｜镜头组总时长：(\d+(?:\.\d+)?)s)?\s*$"
    pattern = re.compile(
        header + r"([\s\S]*?)(?=" + header + r"|^##\s|\Z)",
        re.M,
    )
    yield from pattern.finditer(text)


def iter_children(group_block: str):
    pattern = re.compile(r"【镜号】\n\s*([^\n]+)\n([\s\S]*?)(?=\n【镜号】\n|\Z)")
    yield from pattern.finditer(group_block)


def extract(block: str, field: str, next_field: str | None = None) -> str:
    if next_field:
        m = re.search(re.escape(field) + r"\n([\s\S]*?)(?=\n\n" + re.escape(next_field) + r")", block)
    else:
        m = re.search(re.escape(field) + r"\n([\s\S]*)", block)
    return m.group(1).strip() if m else ""


def extract_optional_field(block: str, field: str) -> str:
    m = re.search(re.escape(field) + r"\n([\s\S]*?)(?=\n\n【|\Z)", block)
    return m.group(1).strip() if m else ""


def direct_sentence(state_change: str, label: str) -> str:
    m = re.search(re.escape(label) + r"[：:]\s*([^\n；;]+)", state_change)
    return m.group(1).strip() if m else ""


def quoted_lines(text: str) -> list[str]:
    return [line.strip() for line in re.findall(r"“([^”]+)”", text) if line.strip()]


def visible_dialogue_quotes(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        if not any(q in raw_line for q in ("“", "”")):
            continue
        if any(term in raw_line for term in POST_AUDIO_TERMS) and not any(term in raw_line for term in VISIBLE_SPEECH_TERMS):
            continue
        if any(term in raw_line for term in VISIBLE_SPEECH_TERMS):
            lines.extend(quoted_lines(raw_line))
    return lines


def validate_child(group_id: str, number: int, header: str, block: str, issues: list[str]) -> None:
    sid = f"{group_id}-{number}"
    if not re.match(rf"^{number}\s*，\s*\d+(?:\.\d+)?s\s*，\s*(普通|复杂)。?$", header):
        issues.append(f"{sid}: 镜号应为“{number}，时长s，普通/复杂。” -> {header}")
    for field in CHILD_FIELDS[1:]:
        if field not in block:
            issues.append(f"{sid}: missing {field}")
    if "【出现人物】" in block:
        issues.append(f"{sid}: cast belongs only at group level")

    direct = extract(block, "【画面描述｜直接复制】", "【表演与声音】")
    if not direct:
        issues.append(f"{sid}: missing direct prompt body")
        return
    performance = extract(block, "【表演与声音】", "【状态继承】")
    mouth_window = extract_optional_field(block, "【口型分窗】")
    if compact_len(direct) > 500:
        issues.append(f"{sid}: direct prompt over 500 chars -> {compact_len(direct)}")
    if (
        compact_len(direct) < 120
        and not any(term in direct for term in ("手部特写", "特写", "空镜", "只拍", "镜头不拍人物"))
        and "无台词" not in performance
    ):
        issues.append(f"{sid}: ordinary dialogue/drama direct prompt looks too thin -> {compact_len(direct)} chars")
    if not any(term in direct for term in SHOT_SIZE_TERMS):
        issues.append(f"{sid}: direct prompt missing shot size")
    if not any(term in direct for term in CAMERA_TERMS):
        issues.append(f"{sid}: direct prompt missing camera placement or angle")
    if not any(term in direct for term in CAMERA_STATE_TERMS):
        issues.append(f"{sid}: direct prompt missing static state or one camera path")
    if not any(term in direct for term in RELATION_TERMS):
        issues.append(f"{sid}: direct prompt missing body or prop relationship")
    if not any(term in direct for term in FACING_TERMS):
        issues.append(f"{sid}: direct prompt missing body-facing anchor")
    if re.search(r"(?:身体|上身)朝(?:左|右)(?!侧)", direct):
        issues.append(f"{sid}: body direction must name a person or fixed anchor, not only left/right")
    if ("只拍" in direct or "只保留" in direct) and re.search(r"中景|中近景|中远景|全景|远景", direct):
        issues.append(f"{sid}: hand/object-only frame conflicts with medium or wide shot size")

    duration_match = re.search(r"，\s*(\d+(?:\.\d+)?)s\s*，", header)
    spoken_chars = sum(len(re.sub(r"\s+", "", line)) for line in re.findall(r"“([^”]+)”", direct))
    if duration_match and spoken_chars:
        duration = float(duration_match.group(1))
        min_duration = spoken_chars / 6.5 + 0.5
        if duration + 0.01 < min_duration:
            issues.append(
                f"{sid}: visible dialogue duration too short -> {duration:g}s for {spoken_chars} chars, need about {min_duration:.1f}s"
            )
    hits = [word for word in BANNED_DIRECT if word in direct]
    if hits:
        issues.append(f"{sid}: banned direct-prompt terms -> {','.join(hits)}")
    direct_quotes = set(quoted_lines(direct))
    for line in visible_dialogue_quotes(performance) + visible_dialogue_quotes(mouth_window):
        if line not in direct_quotes:
            issues.append(f"{sid}: visible dialogue must appear in direct prompt by default -> “{line}”")
    if any(word in direct for word in CUTAWAY_NEEDLES):
        handoff = extract_optional_field(block, "【剪辑衔接】")
        in_place_focus = any(word in direct for word in ("焦点从", "焦点落到", "拉焦", "转焦"))
        if not handoff and not in_place_focus:
            issues.append(f"{sid}: standalone cutaway needs 【剪辑衔接】 with independent-generation sound bridge")

    state_change = extract_optional_field(block, "【镜内状态转换】")
    if state_change:
        for label in ("终态直投句", "尾帧直投句"):
            sentence = direct_sentence(state_change, label)
            if not sentence:
                issues.append(f"{sid}: 【镜内状态转换】 missing {label}")
            elif sentence not in direct:
                issues.append(f"{sid}: {label} must appear verbatim in direct prompt -> {sentence}")

    camera_execution = extract_optional_field(block, "【镜头执行】")
    if mouth_window:
        priority = "优先级：口型 > 听者反应 > 运镜"
        if priority not in mouth_window:
            issues.append(f"{sid}: 【口型分窗】 missing dialogue priority declaration")
        if camera_execution and re.search(r"推|拉|移|摇|跟拍|环绕|转焦|拉焦", camera_execution):
            if not any(term in mouth_window for term in ("听者保持", "听者不动", "听者静止", "仅呼吸", "仅视线")):
                issues.append(f"{sid}: lip-sync with camera move needs listener hold declaration in 【口型分窗】")


def camera_signature(direct: str) -> str:
    size = next((term for term in SHOT_SIZE_TERMS if term in direct), "")
    moving = any(term in direct for term in ("推", "拉", "摇", "移", "跟", "转焦", "拉焦"))
    return f"{size}:{'move' if moving else 'static'}"


def validate(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    issues: list[str] = []
    for section in REQUIRED_TOP_SECTIONS:
        if section not in text:
            issues.append(f"missing top section {section}")
    hits = [heading for heading in DEPRECATED_HEADINGS if heading in text]
    if hits:
        issues.append("deprecated headings not allowed -> " + ",".join(hits))
    if NEGATIVE_NEEDLE not in text:
        issues.append("missing anti-stiffness negative prompt")

    group_count = child_count = 0
    for match in iter_groups(text):
        group_count += 1
        group_id, group_total, block = match.group(1), match.group(2), match.group(3)
        if group_total is None:
            issues.append(f"{group_id}: group heading must include summed duration -> #### {group_id}｜镜头组总时长：Xs")
        before_first_child = block.split("【镜号】", 1)[0]
        cast = extract_optional_field(before_first_child, "【出现人物】")
        if not cast:
            issues.append(f"{group_id}: missing group-level 【出现人物】")
        for line in [x.strip() for x in cast.splitlines() if x.strip()]:
            if any(sep in line for sep in "、，；;"):
                issues.append(f"{group_id}: cast line should contain one visible character/group only -> {line}")
        children = list(iter_children(block))
        if not children:
            issues.append(f"{group_id}: no child shots found")
        for expected_number, child in enumerate(children, start=1):
            child_count += 1
            validate_child(group_id, expected_number, child.group(1).strip(), child.group(0), issues)
        child_durations = []
        for child in children:
            duration_match = re.search(r"，\s*(\d+(?:\.\d+)?)s\s*，", child.group(1))
            if duration_match:
                child_durations.append(float(duration_match.group(1)))
        if group_total is not None and child_durations:
            summed = sum(child_durations)
            if abs(float(group_total) - summed) > 0.01:
                issues.append(f"{group_id}: group duration {float(group_total):g}s != child sum {summed:g}s")
        signatures = []
        for child in children:
            direct = extract(child.group(0), "【画面描述｜直接复制】", "【表演与声音】")
            signatures.append(camera_signature(direct))
        for index in range(2, len(signatures)):
            if signatures[index] == signatures[index - 1] == signatures[index - 2] and signatures[index].endswith(":static"):
                issues.append(f"{group_id}: three consecutive identical static camera tasks -> {signatures[index]}")

    if group_count == 0:
        issues.append("no shot groups found; use #### S1-01 with group-level 【出现人物】")
    if child_count == 0:
        issues.append("no child shots found")
    return issues


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: validate_storyboard.py <file.md> [more.md ...]", file=sys.stderr)
        return 2
    failed = False
    for raw in argv[1:]:
        path = Path(raw)
        issues = validate(path)
        print(f"{path}: {'OK' if not issues else 'FAIL'}")
        for issue in issues:
            print(f"  - {issue}")
        failed = failed or bool(issues)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
