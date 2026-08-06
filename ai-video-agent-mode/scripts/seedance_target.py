#!/usr/bin/env python3
"""Deterministic Seedance target normalization and output path mapping."""

import os


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

def normalize_target(value):
    text = str(value or "auto").strip().lower()
    normalized = ALIASES.get(text, text)
    if normalized not in TARGETS:
        raise ValueError("seedance_target must be auto, 2.0, 2.5, or both")
    return normalized


def render_targets(value):
    target = normalize_target(value)
    return ("2.0", "2.5") if target == "both" else (target,)


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
