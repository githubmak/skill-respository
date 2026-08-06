#!/usr/bin/env python3
"""Normalize current-contract prompt packages without duplicating prompt data."""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from negative_prompts import PLACEHOLDER, build_negative_prompt_for_item
from contract_registry import PROMPT_CONTRACT_VERSION
from shot_semantics import disabled_risk_gated_fields
from validate_modec import _main_shot_expectations


def normalize_package(input_path, output_path=None):
    with open(input_path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)

    shots = data.get("shots", [])
    if not isinstance(shots, list):
        raise ValueError("current prompt package must contain shots[]")
    expected = _load_main_shot_expectations(input_path)
    normalized = []
    for shot in shots:
        item = dict(shot)
        if "duration_sec" in item:
            raise ValueError("duration_sec is obsolete; use duration")
        original = str(item.get("full_prompt", ""))
        item["full_prompt"] = normalize_prompt(original)
        _normalize_expectation_anchor(item)
        disabled = _disabled_risk_field_issues(
            item, expected.get(str(item.get("shot_id", "") or ""), {})
        )
        if disabled:
            raise ValueError(
                "SCHEMA_CONFLICT:模型返回了scaffold未授权字段，工程层不得静默删除；请定向重生成："
                + "、".join(disabled)
            )

        current_negative = str(item.get("negative_prompt", "") or "").strip()
        if current_negative in ("", PLACEHOLDER) or PLACEHOLDER in current_negative:
            item["negative_prompt"] = build_negative_prompt_for_item(item)
        else:
            item["negative_prompt"] = current_negative
        normalized.append(item)

    result = {
        "contract_version": PROMPT_CONTRACT_VERSION,
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


def _normalize_expectation_anchor(item):
    metadata = item.get("qa_metadata")
    if not isinstance(metadata, dict) or "expectation_anchor" not in metadata:
        return
    anchor = metadata.get("expectation_anchor")
    if anchor in ({}, None):
        metadata.pop("expectation_anchor", None)
        return
    if isinstance(anchor, dict) and "applicable" not in anchor:
        raise ValueError(
            "SCHEMA_CONFLICT:qa_metadata.expectation_anchor缺少applicable；工程层不得猜测或删除模型语义"
        )


def _disabled_risk_field_issues(item, plan_item):
    metadata = item.get("qa_metadata")
    if not isinstance(metadata, dict):
        return []
    visible = plan_item.get("visible_characters", plan_item.get("characters", [])) if isinstance(plan_item, dict) else []
    return disabled_risk_gated_fields(plan_item, metadata, visible)


def _load_main_shot_expectations(input_path):
    absolute = os.path.abspath(input_path)
    marker = os.sep + ".cache" + os.sep
    if marker not in absolute:
        return {}
    run_dir = absolute.split(marker, 1)[0]
    plan_path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")
    try:
        with open(plan_path, "r", encoding="utf-8-sig") as handle:
            plan = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return _main_shot_expectations(plan if isinstance(plan, dict) else {})


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: normalize_prompt_package.py <input.prompt_package.json> [output.prompt_package.json]")
        sys.exit(2)
    normalize_package(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
