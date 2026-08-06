#!/usr/bin/env python3
"""Serialize a prompt package into the canonical envelope without semantic edits."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from contract_registry import PROMPT_CONTRACT_VERSION


def normalize_package(input_path, output_path=None):
    with open(input_path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("shots"), list):
        raise ValueError("current prompt package must contain shots[]")
    if data.get("contract_version") not in (None, PROMPT_CONTRACT_VERSION):
        raise ValueError("contract_version mismatch; engineering cannot relabel an incompatible package")
    if any(isinstance(shot, dict) and "duration_sec" in shot for shot in data["shots"]):
        raise ValueError("duration_sec is obsolete; model must return duration")
    result = {"contract_version": PROMPT_CONTRACT_VERSION, "shots": data["shots"]}
    out = output_path or input_path
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print("[SERIALIZE] %d shots -> %s (creative text unchanged)" % (len(result["shots"]), out))
    return result


def normalize_prompt(prompt):
    """Compatibility helper: creative text is returned byte-for-byte."""
    return prompt if isinstance(prompt, str) else str(prompt or "")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: normalize_prompt_package.py <input.json> [output.json]")
    normalize_package(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
