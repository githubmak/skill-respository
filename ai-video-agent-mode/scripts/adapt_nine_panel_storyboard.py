#!/usr/bin/env python3
"""Adapt nine-panel-video-storyboard JSON into this skill's export package."""

import json
import os
import sys


def adapt(input_path, output_path):
    with open(input_path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    boards = data.get("storyboards", []) if isinstance(data, dict) else []
    if isinstance(data, dict) and isinstance(data.get("panels"), list):
        boards = [data]
    packages = []
    for index, board in enumerate(boards, 1):
        panels = board.get("panels", []) if isinstance(board, dict) else []
        _validate_panels(panels)
        chain_id = str(board.get("chain_id", "GRID-%03d" % index) or "GRID-%03d" % index)
        scene = str(board.get("scene", board.get("source_summary", "当前场景")) or "当前场景")
        packages.append({
            "chain_id": chain_id,
            "scene": scene,
            "source_subshot_ids": list(board.get("source_subshot_ids", []) or []),
            "grid_prompt": _grid_prompt(board, panels),
            "negative_prompt": "重复构图, 连续相同姿势, 人物身份漂移, 服装变化, 道具消失, 左右站位颠倒, 肢体变形, 手指异常, 场景闪烁, 标签重叠",
            "beats": [
                {"panel_id": panel["panel_id"], "source_subshot_id": str(panel.get("source_subshot_id", "")), "description": str(panel.get("visual_description", ""))}
                for panel in panels
            ],
            "nine_panel_storyboard": board,
        })
    result = {"contract_version": "jimeng-t2v-v1", "packages": packages}
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    return result


def _validate_panels(panels):
    if not isinstance(panels, list) or len(panels) != 9:
        raise ValueError("nine-panel storyboard must contain exactly 9 panels")
    expected = ["%02d" % number for number in range(1, 10)]
    actual = [str(panel.get("panel_id", "")) for panel in panels if isinstance(panel, dict)]
    if actual != expected:
        raise ValueError("panel_id must be ordered 01 through 09")
    required = ("camera_setup", "camera_motion", "visual_description", "ai_motion_control", "narrative_tag")
    for panel in panels:
        missing = [field for field in required if not str(panel.get(field, "") or "").strip()]
        if missing:
            raise ValueError("panel %s missing %s" % (panel.get("panel_id", "?"), ", ".join(missing)))


def _grid_prompt(board, panels):
    style = str(board.get("visual_style", "") or "")
    source = str(board.get("source_summary", "") or "")
    header = "16:9横向九宫格剧情分镜图，9个连续画格，统一人物身份、服装、主色调、光源方向和空间轴线"
    if style:
        header += "，" + style
    if source:
        header += "。剧情：" + source
    beats = []
    for panel in panels:
        beats.append("第%s格[%s]：%s；%s；%s" % (
            panel["panel_id"], panel.get("narrative_tag", ""), panel.get("camera_setup", ""),
            panel.get("visual_description", ""), panel.get("ai_motion_control", ""),
        ))
    return header + "。" + "。".join(beats) + "。第05格为唯一核心定格，所有格保持人物左右位置、道具状态和光线连续。"


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: adapt_nine_panel_storyboard.py <nine_panel.json> <packages.json>")
    result = adapt(sys.argv[1], sys.argv[2])
    print("[NINE PANEL ADAPT] %d package(s)" % len(result["packages"]))
