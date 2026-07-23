#!/usr/bin/env python3
"""Normalize current-contract prompt packages without duplicating prompt data."""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from negative_prompts import PLACEHOLDER, build_negative_prompt_for_item


def normalize_package(input_path, output_path=None):
    with open(input_path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)

    shots = data.get("shots", [])
    if not isinstance(shots, list):
        raise ValueError("current prompt package must contain shots[]")
    normalized = []
    for shot in shots:
        item = dict(shot)
        if "duration_sec" in item:
            raise ValueError("duration_sec is obsolete; use duration")
        original = str(item.get("full_prompt", ""))
        item["full_prompt"] = normalize_prompt(original)

        current_negative = str(item.get("negative_prompt", "") or "").strip()
        if current_negative in ("", PLACEHOLDER) or PLACEHOLDER in current_negative:
            item["negative_prompt"] = build_negative_prompt_for_item(item)
        else:
            item["negative_prompt"] = current_negative
        normalized.append(item)

    result = {
        "contract_version": "jimeng-t2v-v1",
        "shots": normalized,
    }

    out = output_path or input_path
    out_dir = os.path.dirname(out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print("[NORMALIZE] %d shots -> %s" % (len(normalized), out))
    return result


def normalize_prompt(prompt):
    text = str(prompt or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"(\d+(?:\.\d+)?)\s+K\b", r"\1K", text)
    text = re.sub(r"(\d+(?:\.\d+)?)\s+m/s\b", r"\1m/s", text)
    text = text.replace(PLACEHOLDER, "").strip()
    return text


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: normalize_prompt_package.py <input.prompt_package.json> [output.prompt_package.json]")
        sys.exit(2)
    normalize_package(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
