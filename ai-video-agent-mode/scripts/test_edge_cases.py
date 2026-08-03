#!/usr/bin/env python3
"""Regression coverage for parser and context-budget boundary cases."""

import json
import os
import tempfile

from build_shotplan import split_dialogue
from context_budget import MAX_EFFECTIVE_CONTEXT_CHARS, check
from generate_shotplan import (
    _characters_in_source_order,
    _offscreen_character_mention,
    generate,
)
from shot_semantics import disabled_risk_gated_fields, functional_surface_risk


def main():
    assert _characters_in_source_order("林岚看向她", ["林", "林岚"]) == ["林岚"]
    assert _offscreen_character_mention("林岚", "隔墙传来林岚的声音。")
    assert _offscreen_character_mention("周启", "电话那头的周启说。")
    assert not _offscreen_character_mention("林岚", "林岚走进房间。")

    assert not functional_surface_risk({"base_action": "他看见手机掉在地上"})
    assert not functional_surface_risk({"base_action": "镜头看手机屏幕反光"})
    assert functional_surface_risk({"base_action": "她滑动手机屏幕"})

    light = {"shot_type": "object", "non_character_confirmed": True,
             "visual_intent": "桌面静物", "base_action": "手机静置", "characters": []}
    metadata = {"emotion_driver": {}, "story_punch_contract": {}}
    assert "emotion_driver" in disabled_risk_gated_fields(light, metadata, [])
    assert "story_punch_contract" in disabled_risk_gated_fields(light, metadata, [])

    with tempfile.TemporaryDirectory(prefix="ai-video-edge-") as root:
        config = {
            "max_shot_duration": 15,
            "source_rules": {"characters": ["角色A"], "scene_header_pattern": r"^SCENE"},
        }
        config_path = os.path.join(root, "project_config.json")
        with open(config_path, "w", encoding="utf-8") as handle:
            json.dump(config, handle, ensure_ascii=False)
        source_path = os.path.join(root, "source.txt")
        with open(source_path, "w", encoding="utf-8") as handle:
            handle.write("时间：23:15\n镜头：从门口推进\n角色A：收到。\n")
        draft_path, _, _ = generate(source_path, root, config_path=config_path, max_shot_duration=15)
        with open(draft_path, encoding="utf-8") as handle:
            draft = json.load(handle)
        units = {unit["text"]: unit["type"] for unit in json.load(open(os.path.join(root, "source_ledger.json"), encoding="utf-8"))["units"]}
        assert units["时间：23:15"] == "action"
        assert units["镜头：从门口推进"] == "action"
        assert units["角色A：收到。"] == "dialogue"
        assert draft["shots"]

        short_source = os.path.join(root, "short.txt")
        with open(short_source, "w", encoding="utf-8") as handle:
            handle.write("△他坐下并拿起手机然后走向门口\n")
        try:
            generate(short_source, root, config_path=config_path, max_shot_duration=2.5)
        except ValueError as error:
            assert "exceeds user-confirmed max_shot_duration" in str(error)
        else:
            raise AssertionError("compound action must not be compressed into a 2.5s shot")

        sidecar = os.path.join(root, "sidecar.txt")
        with open(sidecar, "w", encoding="utf-8") as handle:
            handle.write("x" * MAX_EFFECTIVE_CONTEXT_CHARS)
        try:
            check({"items": [], "constraints_path": sidecar})
        except ValueError as error:
            assert "effective worker context" in str(error)
        else:
            raise AssertionError("external sidecar must count toward effective context")
    print("edge-case regression passed")


if __name__ == "__main__":
    main()
