#!/usr/bin/env python3
"""Source-first intake audit for the Jimeng storyboard workflow.

Only unreadable or empty input is blocking.  Weak scene labels, missing
character lists, and sparse visual detail are advisories because the storyboard
workflow is allowed to infer production-safe details from the supplied prose.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SCENE_RE = re.compile(r"^(?:场景|地点)[：:]|^\d+-\d+\b|^SCENE\b", re.I)
DIALOGUE_RE = re.compile(r"^([^：:]{1,24})(?:（[^）]*）)?[：:](.+)$")
INLINE_SPEAKER_RE = re.compile(
    r"(?:^|[\n。！？；;”’])\s*([\u4e00-\u9fffA-Za-z0-9_·]{1,12})(?:（[^）]*）)?[：:](?=\s*[“\"‘']|[^/\n]{2,})",
    re.M,
)
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
STYLE_CHANNELS = {
    "era_reality": ("古代", "古装", "历史", "武侠", "仙侠", "现代", "都市"),
    "place_architecture": ("宫廷", "府邸", "江湖", "客厅", "办公室", "咖啡馆", "乡村", "小镇"),
    "wardrobe_identity": ("汉服", "长袍", "铠甲", "西装", "大衣", "制服", "粗布"),
    "technology": ("手机", "电脑", "汽车", "马车", "电梯", "霓虹", "烛火"),
    "weather_light": ("月光", "窗光", "雨", "雪", "雾", "阴天", "车灯", "天光"),
    "physical_action": ("拔剑", "骑马", "追逐", "轻功", "施法", "奔跑", "下车", "开门"),
}
STYLE_PATTERNS = {
    "era_reality": (re.compile(r"(?:纪元|年代|王朝|未来|近未来|架空|当代|末世)"),),
    "place_architecture": (re.compile(r"[\u4e00-\u9fff]{1,8}(?:舱|殿|厅|室|站|塔|城|村|院|馆|窟|岛)"),),
    "wardrobe_identity": (re.compile(r"[\u4e00-\u9fff]{1,8}(?:服|袍|甲|裙|衣|制服|装甲)"),),
    "technology": (re.compile(r"(?:终端|全息|机械|飞船|舱门|机器人|义体|装置|引擎)"),),
    "weather_light": (re.compile(r"(?:晨|昼|暮|夜|雨|雪|风|云|雾|光|阴影|闪电|极光)"),),
    "physical_action": (re.compile(r"(?:跨过|穿过|推开|拉开|跃下|攀爬|潜入|撤退|逼近|停步)"),),
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

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    scene_lines = [line for line in lines if SCENE_RE.search(line)]
    dialogue_lines = [line for line in lines if DIALOGUE_RE.match(line) and not SCENE_RE.search(line)]
    action_lines = [line for line in lines if ACTION_RE.search(line)]
    speakers = []
    for line in dialogue_lines:
        speaker = DIALOGUE_RE.match(line).group(1).strip()
        if speaker not in speakers:
            speakers.append(speaker)
    for match in INLINE_SPEAKER_RE.finditer(text):
        speaker = match.group(1).strip()
        if speaker not in speakers:
            speakers.append(speaker)

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
    if len(speakers) >= 2:
        risk_flags.setdefault("multi_person", []).append("multiple_named_speakers")
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
        },
        "risk_flags": risk_flags,
        "style_evidence": _style_evidence(text),
        "source_fidelity": {
            "raw_text_preserved": True,
            "dialogue_should_be_copied_verbatim": bool(dialogue_lines),
            "visual_inference_allowed": True,
        },
    }


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
    if report_path:
        destination = Path(report_path).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["report_path"] = str(destination)
    return result


def _issue(code: str, message: str, severity: str = "blocking") -> dict:
    return {"code": code, "severity": severity, "message": message}


def _style_evidence(text: str) -> dict:
    hits: dict[str, list[str]] = {}
    for channel in dict.fromkeys((*STYLE_CHANNELS, *STYLE_PATTERNS)):
        channel_hits = [term for term in STYLE_CHANNELS.get(channel, ()) if term in text]
        for pattern in STYLE_PATTERNS.get(channel, ()):
            channel_hits.extend(match.group(0) for match in pattern.finditer(text))
        if channel_hits:
            hits[channel] = list(dict.fromkeys(channel_hits))[:12]
    score = len(hits) * 2
    confidence = "high" if len(hits) >= 3 and score >= 6 else "medium" if len(hits) >= 2 else "low"
    return {
        "channels": hits,
        "independent_channel_count": len(hits),
        "evidence_score": score,
        "confidence": confidence,
        "routing_only": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    result = inspect_path(args.source, args.report)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
