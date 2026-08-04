#!/usr/bin/env python3
"""Regression checks for dialogue, OS, OV, and system-audio planning."""

import json
import os
import tempfile

from generate_shotplan import generate
from prompt_contract import dialogue_event_issues


def _write(path, content):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def _generate(source_text):
    temp_dir = tempfile.TemporaryDirectory()
    source_path = os.path.join(temp_dir.name, "source.txt")
    config_path = os.path.join(temp_dir.name, "project_config.json")
    _write(source_path, source_text)
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump({
            "max_shot_duration": 15,
            "source_rules": {
                "characters": ["林岚"],
                "action_keywords": ["到达"],
                "scene_header_pattern": "^SCENE\\s+([0-9]+)",
            },
        }, handle, ensure_ascii=False)
    generate(source_path, temp_dir.name, config_path=config_path)
    with open(os.path.join(temp_dir.name, "shot_plan.draft.json"), "r", encoding="utf-8") as handle:
        return temp_dir, json.load(handle)


def run():
    temp_dir, plan = _generate(
        "SCENE 1 夜 内 电梯\n"
        "系统音：电梯即将到达。\n"
        "林岚（OS）：别停在这一层。\n"
        "旁白（OV）：指示灯停在十三层。\n"
        "林岚：门开了吗？\n"
    )
    try:
        events = list(plan["dialogue_events"].values())
        assert [event["kind"] for event in events] == ["系统音", "OS", "OV", "台词"]
        assert [event["text"] for event in events] == [
            "电梯即将到达。", "别停在这一层。", "指示灯停在十三层。", "门开了吗？",
        ]
        system_ref = events[0]["ref"]
        system_shot = next(
            subshot
            for shot in plan["shots"]
            for subshot in shot["subshots"]
            if system_ref in subshot.get("dialogue_refs", [])
        )
        assert "系统音" not in system_shot["characters"]

        metadata = {"dialogue_refs": [system_ref], "dialogue_events": [{
            **events[0],
            "speaker_visibility": "nonphysical",
            "lip_sync": False,
            "delivery": "中性电子播报，字句清晰",
            "subtext": "设备状态通知",
            "emotion_layer": "无人物情绪",
            "stress_words": ["到达"],
            "breath_pause_plan": "连续播报，无人物换气",
            "time_range": "0.0-1.5秒",
        }]}
        missing_lip_sync = dialogue_event_issues(
            metadata, None, [], "系统音（系统音）: \"电梯即将到达。\"", True, 2
        )
        assert not any("kind只允许" in issue for issue in missing_lip_sync)
        assert any("系统音缺少无口型同步说明" in issue for issue in missing_lip_sync)
    finally:
        temp_dir.cleanup()

    print("speech event regression: PASS")


if __name__ == "__main__":
    run()
