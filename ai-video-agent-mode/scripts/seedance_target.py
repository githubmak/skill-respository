#!/usr/bin/env python3
"""Deterministic Seedance target normalization and export adaptation."""

import os
import re


TARGETS = ("auto", "2.0", "2.5", "both")
ALIASES = {
    "auto": "auto", "automatic": "auto", "自动": "auto", "兼容": "auto",
    "2": "2.0", "2.0": "2.0", "seedance2.0": "2.0", "seedance 2.0": "2.0",
    "2.5": "2.5", "seedance2.5": "2.5", "seedance 2.5": "2.5",
    "both": "both", "双版本": "both", "两个": "both", "2.0+2.5": "both",
}

TARGET_LABELS = {
    "auto": "Seedance 2.0/2.5 双兼容",
    "2.0": "Seedance 2.0 优化",
    "2.5": "Seedance 2.5 优化",
}

LIGHTING_PREFIXES = {
    "auto": "人物主要受光面清晰，背光侧保留有层次的中等阴影；眼睛、嘴部与表情可辨，暗部保留细节，不使用无来源的正面均匀补光。",
    "2.0": "人物面部主受光清晰，背光侧保留浅至中等阴影；光源关系简洁稳定，眼睛、嘴部与活动手容易辨认。",
    "2.5": "动机光塑造中深明暗层次，背光侧仍保留细节；局部环境色只落在有来源的受光区，黑位稳定，高光柔和滚降。",
}


def normalize_target(value):
    text = str(value or "auto").strip().lower()
    normalized = ALIASES.get(text, text)
    if normalized not in TARGETS:
        raise ValueError("seedance_target must be auto, 2.0, 2.5, or both")
    return normalized


def render_targets(value):
    target = normalize_target(value)
    return ("2.0", "2.5") if target == "both" else (target,)


def adapt_lighting_text(text, target):
    """Preserve canonical facts while adding one bounded model-specific light rule."""
    target = normalize_target(target)
    if target == "both":
        raise ValueError("adapt_lighting_text requires a concrete render target")
    body = adapt_visual_prefix(text, target)
    prefix = LIGHTING_PREFIXES[target]
    if target == "auto" and not body:
        return ""
    if target == "auto" and body:
        return body
    if prefix in body:
        return body
    return prefix + ("；" + body.lstrip("；，。 ") if body else "")


def adapt_visual_prefix(text, target):
    """Rewrite known conservative/deep-light phrases without adding new facts."""
    target = normalize_target(target)
    if target == "both":
        raise ValueError("adapt_visual_prefix requires a concrete render target")
    body = re.sub(r"\s+", " ", str(text or "")).strip()
    if target == "2.0":
        body = body.replace("中深阴影", "浅至中等阴影").replace("深阴影", "中等阴影")
        body = body.replace("高反差", "中等对比")
        return body
    body = body.replace("脸部受光均匀", "人物主要受光面清晰")
    if target == "auto":
        body = re.sub(r"(?:只)?保留浅阴影|只留([^，。；]{0,8})浅阴影", lambda match: "保留有层次的中等" + (match.group(1) or "") + "阴影", body)
    else:
        body = re.sub(r"(?:只)?保留浅阴影|只留([^，。；]{0,8})浅阴影", lambda match: "保留中深" + (match.group(1) or "") + "阴影层次，暗部细节可辨", body)
    return body


def variant_paths(markdown_path, target):
    """Return feed paths and the optional non-feed index path."""
    destination = os.path.abspath(markdown_path)
    target = normalize_target(target)
    if target != "both":
        return {target: destination}, ""
    directory = os.path.dirname(destination)
    stem, extension = os.path.splitext(os.path.basename(destination))
    extension = extension or ".md"
    return {
        "2.0": os.path.join(directory, stem + "_Seedance2.0" + extension),
        "2.5": os.path.join(directory, stem + "_Seedance2.5" + extension),
    }, os.path.join(directory, "00_双版本索引.md")
