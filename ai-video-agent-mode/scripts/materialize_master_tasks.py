#!/usr/bin/env python3
"""Copy an already canonical model-authored main-shot package for export."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from contract_registry import PROMPT_CONTRACT_VERSION


def materialize(run_dir, source_path=None, output_path=None):
    source_path = source_path or os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json")
    output_path = output_path or os.path.join(run_dir, ".cache", "composer", "jimeng_master_tasks.json")
    with open(source_path, "r", encoding="utf-8-sig") as handle:
        package = json.load(handle)
    shots = package.get("shots", []) if isinstance(package, dict) else []
    if not shots or not all(isinstance(item, dict) and item.get("source_subshot_ids") for item in shots):
        raise ValueError(
            "CREATIVE_REWRITE_REQUIRED: Master Production must author one complete main-shot task; "
            "engineering cannot merge child prompts"
        )
    result = {"contract_version": PROMPT_CONTRACT_VERSION, "shots": shots}
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    return output_path, result


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit("usage: materialize_master_tasks.py <run_dir> [output_path]")
    path, result = materialize(sys.argv[1], output_path=sys.argv[2] if len(sys.argv) == 3 else None)
    print("[MASTER TASKS] %s (%d model-authored tasks)" % (path, len(result["shots"])))
