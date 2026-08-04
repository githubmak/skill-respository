#!/usr/bin/env python3
"""Validate each newly generated shot before committing the full storyboard.

This is an additive preflight. It reuses the authoritative shot validators and
never replaces the final validate_storyboard.py file/bundle gates.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import validate_storyboard as validator


FIELD_LABELS = (
    "【镜号】",
    "【出现人物】",
    "【画面描述｜直接复制】",
    "【表演与声音】",
    "【状态继承】",
    "【本镜制作控制】",
    "【关键帧生图提示】",
    "【即梦视频提示｜配合关键帧】",
    "【空间与道具锁定】",
    "【镜头执行】",
    "【口型分窗】",
    "【镜内状态转换】",
    "【剪辑衔接】",
    "【本镜必要约束｜直接复制】",
    "【本镜补充负面提示词｜直接复制】",
)


def analyze(text: str, current_shot: str | None = None) -> dict:
    records = _shot_records(text)
    issues: list[dict] = []
    by_scene: dict[int, list[dict]] = {}
    by_group: dict[str, list[dict]] = {}
    for record in records:
        by_scene.setdefault(record["scene_number"], []).append(record)
        by_group.setdefault(record["group_id"], []).append(record)
        local: list[str] = []
        validator.validate_child(
            record["group_id"], record["number"], record["header"],
            record["block"], record["cast_names"], local,
        )
        for message in local:
            issues.append(_issue(message, "field", [record["shot_id"]]))
        if not record["cast"] and record["number"] == 1:
            issues.append(_issue(
                f'{record["group_id"]}: missing group-level 【出现人物】',
                "field", [record["shot_id"]],
            ))

    for scene_records in by_scene.values():
        for previous, current in zip(scene_records, scene_records[1:]):
            if validator.orientation_jump(previous["state"], current["direct"]):
                issues.append(_issue(
                    f'{current["shot_id"]}: 上一镜状态与当前镜头朝向跳变；先写转身、肩线转正或双脚停稳',
                    "pair", [previous["shot_id"], current["shot_id"]],
                ))
            jumped_props = validator.prop_state_jump(previous["state"], current["direct"])
            if jumped_props:
                issues.append(_issue(
                    f'{current["shot_id"]}: 上一镜物品状态与当前镜头不一致 -> {",".join(jumped_props)}',
                    "pair", [previous["shot_id"], current["shot_id"]],
                ))
            if validator.posture_support_jump(previous["state"], current["direct"]):
                issues.append(_issue(
                    f'{current["shot_id"]}: 上一镜人体支撑点未在当前镜头重写',
                    "pair", [previous["shot_id"], current["shot_id"]],
                ))

    for group_records in by_group.values():
        for index in range(2, len(group_records)):
            window = group_records[index - 2:index + 1]
            signatures = [validator.camera_signature(item["direct"]) for item in window]
            if signatures[0] == signatures[1] == signatures[2] and signatures[2].endswith(":static"):
                issues.append(_issue(
                    f'{window[-1]["shot_id"]}: 连续三镜使用相同静态景别/角度任务 -> {signatures[2]}',
                    "window", [item["shot_id"] for item in window],
                ))
        for previous, current in zip(group_records, group_records[1:]):
            first_actor = validator.shoulder_actor(previous["direct"])
            second_actor = validator.shoulder_actor(current["direct"])
            if first_actor and first_actor == second_actor:
                issues.append(_issue(
                    f'{current["shot_id"]}: 连续肩后镜使用同一前景肩线人物',
                    "pair", [previous["shot_id"], current["shot_id"]],
                ))

    known_shots = {record["shot_id"] for record in records}
    if current_shot and current_shot not in known_shots:
        issues.append({
            "code": "SHOT_NOT_FOUND",
            "repair_scope": "shot",
            "shot_ids": [current_shot],
            "fields": ["【镜号】"],
            "message": current_shot + ": current shot was not found in the incremental draft",
        })
    elif not current_shot and not records:
        issues.append({
            "code": "SHOT_NOT_FOUND",
            "repair_scope": "shot",
            "shot_ids": [],
            "fields": ["【镜号】"],
            "message": "no shot blocks found in the incremental draft",
        })
    if current_shot:
        issues = [item for item in issues if current_shot in item["shot_ids"]]
    counts = Counter(item["repair_scope"] for item in issues)
    return {
        "pass": not issues,
        "mode": "incremental-shot-preflight",
        "current_shot": current_shot or "",
        "checked_shot_count": len(records),
        "issue_count": len(issues),
        "repair_scope_counts": dict(sorted(counts.items())),
        "issues": issues,
        "final_full_validation_required": True,
        "primary_output_modified": False,
    }


def _shot_records(text: str) -> list[dict]:
    records: list[dict] = []
    for group in validator.iter_groups(text):
        group_id, block = group.group(1), group.group(3)
        scene_number = int(group_id[1:].split("-", 1)[0])
        before_first_child = block.split("【镜号】", 1)[0]
        cast = validator.extract_optional_field(before_first_child, "【出现人物】")
        cast_names = validator.group_cast_names(cast)
        for number, child in enumerate(validator.iter_children(block), start=1):
            child_block = child.group(0)
            records.append({
                "shot_id": f"{group_id}-{number}",
                "group_id": group_id,
                "scene_number": scene_number,
                "number": number,
                "header": child.group(1).strip(),
                "block": child_block,
                "cast_names": cast_names,
                "cast": cast,
                "direct": validator.direct_prompt(child_block),
                "state": validator.extract_optional_field(child_block, "【状态继承】"),
            })
    return records


def _issue(message: str, default_scope: str, shot_ids: list[str]) -> dict:
    scope = _repair_scope(message, default_scope)
    return {
        "code": _issue_code(message),
        "repair_scope": scope,
        "shot_ids": shot_ids,
        "fields": _repair_fields(message, scope),
        "message": message,
    }


def _repair_scope(message: str, default_scope: str) -> str:
    if any(term in message for term in ("上一镜", "跨镜头组", "物品状态", "支撑点", "连续肩后镜")):
        return "pair"
    if any(term in message for term in ("连续三镜", "three consecutive")):
        return "window"
    if any(term in message for term in ("overload", "任务过载", "split", "拆镜", "long action chain")):
        return "shot"
    return default_scope


def _issue_code(message: str) -> str:
    rules = (
        (("missing 【", "镜号应为"), "FIELD_STRUCTURE"),
        (("over 500",), "DIRECT_PROMPT_LENGTH"),
        (("OS/OV/系统音", "口型", "visible dialogue"), "SPEECH_CONTRACT"),
        (("关键帧", "KEYFRAME"), "KEYFRAME_CONTRACT"),
        (("制作控制", "未转译", "quality"), "QUALITY_GROUNDING"),
        (("物品状态", "prop transfer", "holder", "道具"), "PROP_CONTINUITY"),
        (("朝向", "orientation", "body-facing"), "ORIENTATION_CONTINUITY"),
        (("支撑", "posture"), "SUPPORT_CONTINUITY"),
        (("连续三镜", "three consecutive", "肩后镜"), "CAMERA_VARIETY"),
        (("可选字段功能超过预算",), "OPTIONAL_FIELD_BUDGET"),
        (("semantic contract incomplete",), "SEMANTIC_COMPLETENESS"),
    )
    for terms, code in rules:
        if any(term in message for term in terms):
            return code
    return "SHOT_CONTRACT"


def _repair_fields(message: str, scope: str) -> list[str]:
    fields = [label for label in FIELD_LABELS if label in message]
    if not fields:
        if any(term in message for term in ("口型", "台词", "OS/OV/系统音", "声音")):
            fields = ["【画面描述｜直接复制】", "【表演与声音】"]
        elif any(term in message for term in ("物品状态", "支撑点", "朝向", "上一镜")):
            fields = ["【画面描述｜直接复制】", "【状态继承】"]
        elif "制作控制" in message or "未转译" in message:
            fields = ["【画面描述｜直接复制】", "【本镜制作控制】"]
        elif "镜号" in message:
            fields = ["【镜号】"]
        else:
            fields = ["【画面描述｜直接复制】"] if scope != "pair" else ["【画面描述｜直接复制】", "【状态继承】"]
    return list(dict.fromkeys(fields))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("draft")
    parser.add_argument("--current-shot")
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    path = Path(args.draft).expanduser().resolve()
    result = analyze(path.read_text(encoding="utf-8-sig"), args.current_shot)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        report = Path(args.report).expanduser().resolve()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
