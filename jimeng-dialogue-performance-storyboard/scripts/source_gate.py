#!/usr/bin/env python3
"""Source-first intake audit for the Jimeng storyboard workflow.

Only unreadable or empty input is blocking.  Weak scene labels, missing
character lists, and sparse visual detail are advisories because the storyboard
workflow is allowed to infer production-safe details from the supplied prose.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


SCENE_RE = re.compile(r"^(?:场景|地点)[：:]|^\d+-\d+\b|^SCENE\b", re.I)
DIALOGUE_RE = re.compile(r"^(?P<speaker>[^：:（）]{1,24}?)(?P<speaker_cue>（[^）]*）)?[：:](?P<body>.+)$")
PERFORMANCE_CUE_LINE_RE = re.compile(
    r"^(?P<speaker>[^：:]{1,24}?)(?P<speaker_cue>（[^）]*）)?[：:](?P<body>.+)$"
)
LEADING_PERFORMANCE_CUE_RE = re.compile(r"^(?P<space>\s*)(?P<cue>（[^）]*）)(?P<dialogue>[\s\S]*)$")
INLINE_SPEAKER_RE = re.compile(
    r"(?:^|[\n。！？；;”’])\s*([\u4e00-\u9fffA-Za-z0-9_·]{1,12})(?:（[^）]*）)?[：:](?=\s*[“\"‘']|[^/\n]{2,})",
    re.M,
)
STRUCTURAL_SPEAKER_LABELS = {
    "人物", "人物表", "角色", "角色表", "场景", "地点", "时间", "画面", "动作", "镜头",
    "旁白", "对白", "台词", "音效", "声音", "备注", "说明", "环境", "道具", "服装",
}
AUDIO_CHANNEL_LABELS = {"旁白", "音效", "声音", "系统音", "系统提示", "广播", "画外音"}
ACTION_RE = re.compile(r"^(?:△|动作[：:])")
RISK_TERMS = {
    "physical_support": ("躺", "坐", "靠", "抱", "扶", "摔", "起身", "翻身", "腾空"),
    "prop_transfer": ("递", "交给", "接过", "接住", "取出", "手机", "付款", "签字"),
    "screen_or_text": ("手机", "屏幕", "聊天", "来电", "文字", "气泡", "付款码"),
    "multi_person": ("两人", "三人", "人群", "路人", "围观", "众人"),
    "lighting_change": ("开门", "车灯", "烛火", "窗光", "云影", "闪烁", "熄灭"),
}
RISK_PATTERNS = {
    "physical_support": (
        re.compile(r"(?:身体|头|肩|背|腰|臀|膝|脚|手)[^。！？；;\n]{0,18}(?:压在|贴住|抵住|支撑|离地|落地)"),
    ),
    "prop_transfer": (
        re.compile(r"(?:把|将)[^，。！？；;\n]{1,16}(?:递给|交给|塞给|放到|收进)"),
        re.compile(r"[^，。！？；;\n]{1,12}(?:被递给|递到|交到|转交|易手)"),
    ),
    "screen_or_text": (
        re.compile(r"(?:面板|终端|投影|界面|显示器)[^。！？；;\n]{0,18}(?:显示|出现|弹出|可读|文字)"),
    ),
    "multi_person": (
        re.compile(r"(?:甲|乙|丙|丁|A|B|C|D)[^。！？；;\n]{0,20}(?:与|和|对|向)(?:甲|乙|丙|丁|A|B|C|D)"),
    ),
    "lighting_change": (
        re.compile(r"(?:光源|灯|火|熔岩|荧光|投影)[^。！？；;\n]{0,18}(?:亮起|熄灭|闪动|转暗|转亮|改变|切换)"),
    ),
}
def inspect_text(text: str) -> dict:
    blocking: list[dict] = []
    advisories: list[dict] = []
    if not isinstance(text, str):
        blocking.append(_issue("SOURCE_TYPE", "源文必须是文本"))
        text = ""
    if "\x00" in text:
        blocking.append(_issue("SOURCE_BINARY", "源文包含二进制空字节"))
    compact = re.sub(r"\s+", "", text)
    if not compact:
        blocking.append(_issue("SOURCE_EMPTY", "源文为空，无法建立场景与状态底图"))

    numbered_lines = [(number, line.strip()) for number, line in enumerate(text.splitlines(), start=1) if line.strip()]
    lines = [line for _, line in numbered_lines]
    scene_lines = [line for line in lines if SCENE_RE.search(line)]
    dialogue_lines = [
        line for line in lines
        if _dialogue_match(line) is not None and not SCENE_RE.search(line)
    ]
    action_lines = [line for line in lines if ACTION_RE.search(line)]
    speakers = []
    for line in dialogue_lines:
        speaker = normalize_speaker(_dialogue_match(line).group("speaker"))
        if speaker and speaker not in speakers:
            speakers.append(speaker)
    for match in INLINE_SPEAKER_RE.finditer(text):
        speaker = normalize_speaker(match.group(1))
        if speaker and speaker not in speakers:
            speakers.append(speaker)
    performance_cues = _performance_cues(numbered_lines)

    if compact and not scene_lines:
        advisories.append(_issue("NO_SCENE_ANCHOR", "未检测到场景标题；按地点、时间和现实层建立空间索引", "advisory"))
    if compact and not dialogue_lines and not action_lines:
        advisories.append(_issue("NO_EXPLICIT_BEAT", "未检测到标准对白/动作行；按段落因果拆节拍", "advisory"))
    if len(text) > 1_000_000:
        advisories.append(_issue("SOURCE_LARGE", "源文较长，先分批读取并冻结跨场景主索引", "advisory"))

    risk_flags: dict[str, list[str]] = {}
    for key in dict.fromkeys((*RISK_TERMS, *RISK_PATTERNS)):
        hits = [term for term in RISK_TERMS.get(key, ()) if term in text]
        for pattern in RISK_PATTERNS.get(key, ()):
            hits.extend(match.group(0) for match in pattern.finditer(text))
        if hits:
            risk_flags[key] = list(dict.fromkeys(hits))[:16]
    if not speakers and dialogue_lines:
        advisories.append(_issue("SPEAKER_UNCERTAIN", "对白存在但说话者标签不稳定；原样保留并在使用说明记录疑点", "advisory"))

    return {
        "pass": not blocking,
        "blocking": blocking,
        "advisories": advisories,
        "stats": {
            "line_count": len(lines),
            "character_count": len(text),
            "scene_line_count": len(scene_lines),
            "dialogue_line_count": len(dialogue_lines),
            "action_line_count": len(action_lines),
            "speaker_count": len(speakers),
            "speakers": speakers[:32],
            "performance_cue_count": len(performance_cues),
        },
        "performance_cues": performance_cues,
        "risk_flags": risk_flags,
        "source_fidelity": {
            "raw_text_preserved": True,
            "dialogue_should_be_copied_verbatim": bool(dialogue_lines),
            "visual_inference_allowed": True,
        },
    }


def _performance_cues(numbered_lines: list[tuple[int, str]]) -> list[dict]:
    """Bind explicit source performance parentheticals to their exact dialogue line."""
    cues: list[dict] = []
    for line_number, line in numbered_lines:
        if SCENE_RE.search(line):
            continue
        match = PERFORMANCE_CUE_LINE_RE.match(line)
        if not match:
            continue
        speaker = normalize_speaker(match.group("speaker"))
        if not speaker:
            continue
        body = match.group("body")
        leading = LEADING_PERFORMANCE_CUE_RE.match(body)
        dialogue = leading.group("dialogue").strip() if leading else body.strip()
        associations = []
        if match.group("speaker_cue"):
            associations.append(("speaker_suffix", match.group("speaker_cue")))
        if leading:
            associations.append(("dialogue_prefix", leading.group("cue")))
        for position, cue in associations:
            cues.append({
                "line_number": line_number,
                "speaker": speaker,
                "cue": cue,
                "cue_text": cue[1:-1],
                "cue_position": position,
                "dialogue": dialogue,
                "source_line": line,
            })
    return cues


def normalize_speaker(raw: str) -> str:
    """Return the canonical actor name, excluding channel/cue and document labels."""
    speaker = re.sub(r"(?:（[^）]*）)\s*$", "", str(raw or "").strip()).strip()
    speaker = re.sub(r"^(?:角色|人物)\s*[-—]\s*", "", speaker).strip()
    if not speaker or speaker in STRUCTURAL_SPEAKER_LABELS or speaker in AUDIO_CHANNEL_LABELS:
        return ""
    return speaker


def _dialogue_match(line: str):
    match = DIALOGUE_RE.match(line)
    if match is None:
        return None
    raw_speaker = re.sub(r"(?:（[^）]*）)\s*$", "", match.group("speaker").strip()).strip()
    return match if raw_speaker in AUDIO_CHANNEL_LABELS or normalize_speaker(match.group("speaker")) else None


def inspect_path(source_path: str, report_path: str | None = None, include_text: bool = False) -> dict:
    path = Path(source_path).expanduser()
    if not path.is_file():
        result = inspect_text("")
        result["blocking"] = [_issue("SOURCE_MISSING", "源文文件不存在或不可读")]
    else:
        try:
            source_text = path.read_text(encoding="utf-8-sig")
            result = inspect_text(source_text)
            if include_text:
                result["_source_text"] = source_text
        except (OSError, UnicodeDecodeError) as exc:
            result = inspect_text("")
            result["blocking"] = [_issue("SOURCE_READ", "读取源文失败：%s" % exc)]
    result["source_path"] = str(path.resolve())
    if path.is_file():
        try:
            result["source_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            result["source_sha256"] = None
    else:
        result["source_sha256"] = None
    if report_path:
        destination = Path(report_path).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["report_path"] = str(destination)
    return result


def _issue(code: str, message: str, severity: str = "blocking") -> dict:
    return {"code": code, "severity": severity, "message": message}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--report")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)
    if not args.compact or not args.report:
        parser.error("legacy source-gate output is disabled; --compact and --report are required")
    result = inspect_path(args.source, args.report)
    if args.compact:
        print(json.dumps({
            "status": "PASS" if result.get("pass") else "FAIL",
            "source": result.get("source_path"),
            "source_sha256": result.get("source_sha256"),
            "risk_flags": sorted(result.get("risk_flags", {})),
            "blocking_count": len(result.get("blocking", [])),
            "advisory_count": len(result.get("advisories", [])),
            "report": result.get("report_path") or args.report,
        }, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
