#!/usr/bin/env python3
"""Resolve source and user style evidence into compact, auditable profiles.

The router is deterministic and intentionally conservative. It chooses a
profile only from independent evidence channels, records contradictions, and
falls back to a generic cinematic baseline when evidence is weak. The receipt
is production metadata; profile names are never model-facing prompt text.
"""

from __future__ import annotations

import re
from typing import Any


ROUTER_VERSION = "visual-profile-router-v1"
GENERIC_PROFILE = "general_cinematic"

STYLE_CHANNELS = {
    "era_reality": ("古代", "古装", "历史", "武侠", "仙侠", "现代", "当代", "都市"),
    "place_architecture": ("宫廷", "府邸", "朝堂", "江湖", "客厅", "办公室", "咖啡馆", "夜车", "乡村", "小镇"),
    "wardrobe_identity": ("汉服", "长袍", "铠甲", "道袍", "西装", "大衣", "制服", "粗布"),
    "technology": ("手机", "电脑", "汽车", "马车", "电梯", "霓虹", "烛火", "火盆"),
    "weather_light": ("月光", "窗光", "雨", "雪", "雾", "阴天", "车灯", "天光"),
    "physical_action": ("拔剑", "骑马", "追逐", "轻功", "施法", "奔跑", "下车", "开门"),
}

PROFILE_TERMS = {
    "chinese_wuxia_game_cinematic": (
        "古风游戏", "国风武侠游戏", "武侠游戏质感", "江湖", "武侠", "拔剑", "轻功", "骑马",
    ),
    "grounded_historical_wuxia": (
        "写实古风", "历史武侠", "江湖烟火", "历史", "古代", "粗布", "马车",
    ),
    "painterly_elegant_wuxia": (
        "写意古风", "华丽武侠", "诗意江湖", "仙侠", "施法", "道袍",
    ),
    "period_court_cinematic": (
        "宫廷", "府邸", "朝堂", "古装关系戏", "礼制", "长袍", "汉服",
    ),
    "modern_natural_drama": (
        "现代剧", "自然电影感", "生活化质感", "现代", "当代", "客厅", "家庭日常",
    ),
    "modern_cinematic_variant": (
        "都市情感", "职场", "咖啡馆", "夜车", "都市", "办公室", "汽车", "电梯",
    ),
    "rural_lived_in_naturalism": (
        "乡村", "小镇", "自然生活", "家庭日常", "粗布", "田野", "院子",
    ),
}

EXPLICIT_PROFILE_TERMS = {
    "chinese_wuxia_game_cinematic": ("古风游戏", "国风武侠游戏", "武侠游戏质感"),
    "grounded_historical_wuxia": ("写实古风", "历史武侠", "江湖烟火"),
    "painterly_elegant_wuxia": ("写意古风", "华丽武侠", "诗意江湖", "仙侠"),
    "period_court_cinematic": ("宫廷", "府邸", "朝堂", "古装关系戏"),
    "modern_natural_drama": ("现代剧", "自然电影感", "生活化质感"),
    "modern_cinematic_variant": ("都市情感", "职场", "咖啡馆", "夜车"),
    "rural_lived_in_naturalism": ("乡村", "小镇", "自然生活", "家庭日常"),
}

MODIFIER_TERMS = {
    "suspense_restraint": ("悬疑", "试探", "信息遮蔽", "隐瞒", "证物"),
    "intimate_warmth": ("亲密", "重逢", "关系缓和", "和解"),
    "comic_clarity": ("喜剧错位", "尴尬", "误会", "笑"),
    "melancholic_distance": ("失落", "离别", "压抑", "告别"),
    "kinetic_pressure": ("追逐", "冲突", "动作升压", "奔跑", "打斗"),
}

ANCIENT_TERMS = ("古代", "古装", "宫廷", "府邸", "朝堂", "汉服", "长袍", "马车", "烛火", "火盆", "武侠", "仙侠")
MODERN_TERMS = ("现代", "当代", "都市", "手机", "电脑", "汽车", "电梯", "办公室", "咖啡馆")
SCENE_HEADER_FALLBACK_RE = re.compile(r"^(?:场景|地点)[：:]|^\d+-\d+\b|^SCENE\b", re.I)


def route_visual_profile(text: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return one project receipt plus conservative per-scene overrides."""
    config = config if isinstance(config, dict) else {}
    text = str(text or "")
    user_style = " ".join(
        str(config.get(key, "") or "").strip()
        for key in ("visual_style", "genre")
        if str(config.get(key, "") or "").strip()
    )
    project = _resolve_receipt(text, user_style=user_style)
    scene_pattern = str((config.get("source_rules") or {}).get("scene_header_pattern", "") or "")
    scene_chunks = split_scene_texts(text, scene_pattern)
    scenes = []
    for name, scene_text in scene_chunks:
        local = _resolve_receipt(scene_text, user_style="")
        override = (
            local["confidence"] == "high"
            and local["base_profile"] != GENERIC_PROFILE
            and local["base_profile"] != project["base_profile"]
        )
        if not override:
            local["base_profile"] = project["base_profile"]
            local["narrative_modifier"] = local["narrative_modifier"] or project["narrative_modifier"]
        local["scene"] = name
        local["inherited_or_overridden"] = "overridden" if override else "inherited"
        scenes.append(local)
    return {
        "router_version": ROUTER_VERSION,
        **project,
        "scene_receipts": scenes,
        "routing_only": True,
    }


def split_scene_texts(text: str, scene_pattern: str = "") -> list[tuple[str, str]]:
    """Split source with the configured scene header without inventing scenes."""
    try:
        configured = re.compile(scene_pattern) if scene_pattern else None
    except re.error:
        configured = None
    chunks: list[tuple[str, list[str]]] = []
    current_name = ""
    current_lines: list[str] = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        match = configured.match(line) if configured else None
        is_header = bool(match or SCENE_HEADER_FALLBACK_RE.search(line))
        if is_header:
            if current_name or current_lines:
                chunks.append((current_name or "__project__", current_lines))
            if match:
                remainder = line[match.end():].strip()
                current_name = remainder or match.group(0)
            else:
                current_name = re.sub(r"^(?:场景|地点)[：:]\s*", "", line, flags=re.I).strip() or line
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_name or current_lines:
        chunks.append((current_name or "__project__", current_lines))
    if len(chunks) == 1 and chunks[0][0] == "__project__":
        return []
    return [(name, "\n".join(lines)) for name, lines in chunks]


def _resolve_receipt(text: str, user_style: str = "") -> dict[str, Any]:
    hits = _channel_hits(text)
    score = len(hits) * 2
    confidence = "high" if len(hits) >= 3 and score >= 6 else "medium" if len(hits) >= 2 else "low"
    explicit_profile = _first_profile(user_style, EXPLICIT_PROFILE_TERMS)
    source_profile = _best_source_profile(text)
    contradictions = _contradictions(text)
    if explicit_profile:
        base_profile = explicit_profile
        confidence = "high"
    elif confidence == "high" and source_profile:
        base_profile = source_profile
    elif confidence == "medium" and source_profile:
        base_profile = source_profile
    else:
        base_profile = GENERIC_PROFILE
    if contradictions and not explicit_profile:
        confidence = "medium" if confidence == "high" else "low"
        if confidence == "low":
            base_profile = GENERIC_PROFILE
    modifier = _first_profile(text, MODIFIER_TERMS) or "none"
    applied_layers = {
        "high": ["space", "light", "color", "material", "motion"],
        "medium": ["space", "light", "material"],
        "low": ["general_cinematic_baseline"],
    }[confidence]
    return {
        "channels": hits,
        "independent_channel_count": len(hits),
        "evidence_score": score,
        "confidence": confidence,
        "base_profile": base_profile,
        "narrative_modifier": modifier,
        "matched_evidence": sorted({term for values in hits.values() for term in values}),
        "contradictions": contradictions,
        "applied_layers": applied_layers,
        "user_overrides": [user_style] if user_style else [],
        "inherited_or_overridden": "project",
    }


def _channel_hits(text: str) -> dict[str, list[str]]:
    return {
        channel: [term for term in terms if term in text]
        for channel, terms in STYLE_CHANNELS.items()
        if any(term in text for term in terms)
    }


def _first_profile(text: str, mapping: dict[str, tuple[str, ...]]) -> str:
    for profile, terms in mapping.items():
        if any(term in str(text or "") for term in terms):
            return profile
    return ""


def _best_source_profile(text: str) -> str:
    scored = []
    for order, (profile, terms) in enumerate(PROFILE_TERMS.items()):
        matched = {term for term in terms if term in text}
        scored.append((len(matched), -order, profile))
    score, _order, profile = max(scored)
    return profile if score else ""


def _contradictions(text: str) -> list[str]:
    ancient = [term for term in ANCIENT_TERMS if term in text]
    modern = [term for term in MODERN_TERMS if term in text]
    if ancient and modern:
        return ["时代/技术证据并存：古代=%s；现代=%s" % ("、".join(ancient[:4]), "、".join(modern[:4]))]
    return []

