#!/usr/bin/env python3
"""Regression tests for model creative sovereignty and engine permissions."""

from creative_engineering_boundary import (
    ENGINE,
    HYBRID,
    MODEL,
    boundary_issues,
    creative_rewrite_issue,
    field_owner,
    repair_executor,
)
from direct_prompt_compiler import compile_direct_prompt
from incremental_validation import classify_issue


def run():
    assert not boundary_issues()
    assert field_owner("full_prompt") == MODEL
    assert field_owner("qa_metadata.performance_contract.mask_leak") == MODEL
    assert field_owner("qa_metadata.scene_tone_palette.tone_palette") == HYBRID
    assert field_owner("shot_id") == ENGINE
    assert field_owner("qa_metadata.dialogue_events[2].text") == ENGINE
    assert repair_executor("full_prompt", "PROMPT_CONTRACT") == MODEL
    assert repair_executor("shot_id", "LOCKED_FIELD") == ENGINE

    oversized = compile_direct_prompt([
        {"kind": "performance", "text": "创作句甲。创作句乙。创作句丙。"},
    ], max_chars=10)
    assert oversized["text"] == "创作句甲。创作句乙。创作句丙。"
    assert oversized["omitted"] == []
    assert oversized["creative_rewrite_required"] is True
    assert any(issue.startswith("CREATIVE_REWRITE_REQUIRED:") for issue in oversized["issues"])

    issue = classify_issue("S1: full_prompt超过平台长度", ["S1"], {"S1": "S1"})
    assert issue["field_owners"]["full_prompt"] == MODEL
    assert issue["repair_executor"] == MODEL

    marker = creative_rewrite_issue("full_prompt", 801, 700, "语义精炼")
    assert marker.startswith("CREATIVE_REWRITE_REQUIRED:full_prompt:801>700")
    print("[CREATIVE BOUNDARY TEST] PASS")


if __name__ == "__main__":
    run()
