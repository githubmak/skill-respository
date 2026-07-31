#!/usr/bin/env python3
"""Compile ordered prompt segments into a dense, traceable Jimeng feed."""

import re

from modec_v4 import jimeng_feed_prompt


PROTECTED_KINDS = {"visual_prefix", "space", "continuity", "performance", "light"}
AUXILIARY_KINDS = {"cinematic", "video_texture", "support"}
CAMERA_TERMS = ("推近", "拉远", "横移", "环绕", "摇镜", "跟拍", "拉焦", "变焦", "甩镜")


def compile_direct_prompt(segments, required_fragments=None, max_chars=700):
    """Return text plus a compile report without inventing replacement facts."""
    required_fragments = [str(value).strip() for value in required_fragments or [] if str(value).strip()]
    normalized = []
    seen = set()
    removed_duplicates = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        kind = str(segment.get("kind", "") or "support")
        clauses = []
        for clause in _clauses(jimeng_feed_prompt(segment.get("text", ""))):
            signature = _signature(clause)
            if not signature or signature in seen:
                if clause:
                    removed_duplicates.append(clause)
                continue
            seen.add(signature)
            clauses.append(clause)
        if clauses:
            normalized.append({"kind": kind, "clauses": clauses})

    text = _join(normalized)
    omitted = []
    if len(text) > max_chars:
        normalized, omitted = _fit(normalized, max_chars)
        text = _join(normalized)

    issues = []
    protected_omissions = [item for item in omitted if item["kind"] in PROTECTED_KINDS]
    if protected_omissions:
        issues.append("直投编译需要删除硬事实才能满足字数上限，必须回到Master Production重写规范正文")
    missing = [fragment for fragment in required_fragments if fragment not in text]
    if missing:
        issues.append("直投编译丢失锁定台词/声音文本：" + "、".join(missing[:4]))
    if len(text) > max_chars:
        issues.append("直投编译结果%d字，超过硬上限%d字" % (len(text), max_chars))
    active_camera = [term for term in CAMERA_TERMS if _active_camera_term(text, term)]
    if "横移" in active_camera and "跟拍" in active_camera and re.search(r"横移.{0,4}跟拍", text):
        active_camera.remove("横移")
    if len(active_camera) > 2:
        issues.append("直投正文存在运镜执行竞争：" + "、".join(active_camera))
    return {
        "text": text,
        "issues": issues,
        "removed_duplicate_count": len(removed_duplicates),
        "omitted": omitted,
        "segment_order": [segment["kind"] for segment in normalized],
        "required_fragments": required_fragments,
    }


def _fit(segments, max_chars):
    """Trim whole clauses from low-priority tails; never cut through a clause."""
    result = [{"kind": item["kind"], "clauses": list(item["clauses"])} for item in segments]
    omitted = []
    removal_order = ("cinematic", "video_texture", "support", "light", "continuity", "space", "performance")
    for kind in removal_order:
        while len(_join(result)) > max_chars:
            candidate = next((
                item for item in reversed(result)
                if item["kind"] == kind
                and item["clauses"]
                and (kind in AUXILIARY_KINDS or len(item["clauses"]) > 1)
            ), None)
            if candidate is None:
                break
            clause = candidate["clauses"].pop()
            omitted.append({"kind": kind, "text": clause})
    result = [item for item in result if item["clauses"]]
    return result, omitted


def _clauses(text):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return []
    parts = re.findall(r"[^。！？；;]+[。！？；;]?", text)
    return [part.strip(" ，,") for part in parts if part.strip(" ，,")]


def _signature(clause):
    return re.sub(r"[\s，,。！？；;：:]", "", str(clause or "")).lower()


def _join(segments):
    parts = []
    for segment in segments:
        text = "".join(_terminal(clause) for clause in segment["clauses"])
        if text:
            parts.append(text)
    return " ".join(parts).strip()


def _terminal(clause):
    value = str(clause or "").strip()
    if not value:
        return ""
    return value if value[-1] in "。！？；;" else value + "。"


def _active_camera_term(text, term):
    """Ignore explicitly disabled camera moves when checking control competition."""
    for match in re.finditer(re.escape(term), str(text or "")):
        prefix = str(text or "")[max(0, match.start() - 8):match.start()]
        if re.search(r"(?:禁止|不使用|不要|避免|无|取消|停止)\s*$", prefix):
            continue
        return True
    return False
