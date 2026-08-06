#!/usr/bin/env python3
"""Check the creative minimum before engineering validation becomes the goal.

The checker is deliberately conservative: it reports a score and only blocks
high-confidence generic substitutions in strict mode. It never rewrites prompts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from validate_storyboard import (
    camera_motion_family,
    detect_shot_type,
    direct_prompt,
    emotion_depth_issues,
    extract,
    extract_optional_field,
    group_cast_names,
    intentional_static_camera,
    iter_children,
    iter_groups,
    motivated_camera_move,
    reflective_light_transport_issues,
    scene_camera_design_issues,
    semantic_ambiguity_issues,
)


FOCUS_TERMS = ("第一焦点", "唯一视觉落点", "焦点落在", "焦点锁")
RELATION_TERMS = ("面向", "视线", "听见", "看见", "回应", "转向", "靠近", "退开", "递", "接住", "隔着", "停住")
LIGHT_TERMS = ("主光", "光源", "灯光", "光线", "受光", "阴影", "光影")
LIGHT_DUTY_TERMS = (
    "显露", "遮蔽", "隔离", "吸引", "映出", "映入", "压暗", "扫过", "切开", "照亮关系", "暴露",
    "斜落", "勾亮", "提亮", "低亮反光", "窄高光", "亮度低于", "受光侧脸", "黑位",
)
CAMERA_TERMS = ("景别", "机位", "摄影机", "镜头", "构图")
CAMERA_SERVICE_TERMS = ("看清", "信息", "距离", "遮挡", "关系", "轴线", "焦点", "视线")
ENDING_TERMS = ("最后", "落幅", "余像", "停在", "停住", "保持", "结束")
GENERIC_TERMS = ("固定中景", "固定中近景", "轻推", "微推", "皱眉", "抬眼", "停稳", "电影感", "高级感")
MECHANISM_TERMS = ("遮挡", "门框", "门槛", "倒影", "水光", "影子", "反射", "火光", "雾气", "视觉通道", "距离拉开", "距离缩短")


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def score_prompt(prompt: str) -> dict[str, object]:
    checks = {
        "focus": _has_any(prompt, FOCUS_TERMS),
        "relationship_or_cause": _has_any(prompt, RELATION_TERMS),
        "lighting_duty": _has_any(prompt, LIGHT_TERMS) and _has_any(prompt, LIGHT_DUTY_TERMS),
        "camera_service": _has_any(prompt, CAMERA_TERMS) and _has_any(prompt, CAMERA_SERVICE_TERMS),
        "ending_residue": _has_any(prompt, ENDING_TERMS),
        "distinctive_mechanism": _has_any(prompt, MECHANISM_TERMS),
    }
    return {"checks": checks, "score": sum(bool(value) for value in checks.values())}


def lint_markdown(markdown: str) -> dict[str, object]:
    shots: list[dict[str, object]] = []
    findings: list[dict[str, object]] = []
    groups: list[dict[str, object]] = []
    camera_records: list[tuple[int, str, str, list[str]]] = []
    for group in iter_groups(markdown):
        group_id = group.group(1)
        before_first_child = group.group(3).split("【镜号】", 1)[0]
        cast_names = group_cast_names(extract_optional_field(before_first_child, "【出现人物】"))
        group_scores: list[int] = []
        group_has_light_duty = False
        for number, child in enumerate(iter_children(group.group(3)), start=1):
            shot_id = f"{group_id}-{number}"
            prompt = direct_prompt(child.group(0))
            if not prompt:
                continue
            result = score_prompt(prompt)
            if reflective_light_transport_issues(prompt):
                result["checks"]["distinctive_mechanism"] = False
                result["score"] = sum(bool(value) for value in result["checks"].values())
            score = int(result["score"])
            checks = result["checks"]
            group_scores.append(score)
            group_has_light_duty = group_has_light_duty or bool(checks["lighting_duty"])
            scene_number = int(group_id[1:].split("-", 1)[0])
            camera_records.append((scene_number, shot_id, prompt, cast_names))
            performance = extract(child.group(0), "【表演与声音】", "【状态继承】")
            shot_type = detect_shot_type(prompt, child.group(1), cast_names)
            for issue in semantic_ambiguity_issues(prompt, cast_names):
                findings.append({
                    "shot_id": shot_id,
                    "code": "SEEDANCE_SEMANTIC_AMBIGUITY",
                    "message": issue,
                })
            for issue in emotion_depth_issues(prompt, performance, shot_type):
                findings.append({
                    "shot_id": shot_id,
                    "code": "EMOTION_CAUSE_CHAIN_THIN",
                    "message": issue,
                })
            shots.append({
                "shot_id": shot_id,
                **result,
                "camera_mode": camera_motion_family(prompt),
                "camera_gain": motivated_camera_move(prompt) or intentional_static_camera(prompt),
            })
            generic_only = _has_any(prompt, GENERIC_TERMS) and not _has_any(prompt, MECHANISM_TERMS)
            if score <= 2 or generic_only:
                findings.append({
                    "shot_id": shot_id,
                    "code": "CREATIVE_CORE_THIN",
                    "score": score,
                    "message": "创意载荷过薄：需要补回源文专属焦点、关系/因果、光影职责或结束余像，不能只靠通用中景/微表情/轻推。",
                })
        if group_scores and not group_has_light_duty:
            findings.append({
                "shot_id": group_id,
                "code": "GROUP_LIGHTING_DUTY_MISSING",
                "message": "本镜头组没有可见的光影叙事职责；补充显露、遮蔽、隔离、吸引注意或关系转折中的一项，不能只写氛围色。",
            })
        groups.append({
            "group_id": group_id,
            "shot_count": len(group_scores),
            "min_score": min(group_scores) if group_scores else None,
            "max_score": max(group_scores) if group_scores else None,
            "has_lighting_duty": group_has_light_duty,
        })
    for message in scene_camera_design_issues(camera_records):
        if "摄影机响应不足" in message:
            code = "CAMERA_ARC_MISSING"
        elif "运镜缺少" in message:
            code = "CAMERA_GAIN_MISSING"
        elif "连续四镜固定" in message:
            code = "STATIC_DEFAULT_CHAIN"
        else:
            code = "CAMERA_MECHANISM_REPEAT"
        findings.append({
            "shot_id": message.split(":", 1)[0],
            "code": code,
            "message": message,
        })
    return {"shots": shots, "groups": groups, "findings": findings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("storyboard")
    parser.add_argument("--advisory", action="store_true", help="report findings without failing")
    parser.add_argument("--report")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)
    if not args.compact or not args.report:
        parser.error("legacy creative-preflight output is disabled; --compact and --report are required")
    try:
        path = Path(args.storyboard).expanduser().resolve()
        report = lint_markdown(path.read_text(encoding="utf-8-sig"))
        findings = report["findings"]
        result = {
            **report,
            "pass": args.advisory or not findings,
            "mode": "advisory" if args.advisory else "strict",
            "storyboard": str(path),
            "primary_storyboard_modified": False,
        }
    except (OSError, ValueError) as exc:
        result = {"pass": False, "error": str(exc), "primary_storyboard_modified": False}
    if args.report:
        report = Path(args.report).expanduser().resolve()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.compact:
        print(json.dumps({
            "status": "PASS" if result.get("pass") else "FAIL",
            "mode": result.get("mode"),
            "finding_count": len(result.get("findings", [])),
            "shot_count": len(result.get("shots", [])),
            "report": str(Path(args.report).expanduser().resolve()) if args.report else None,
        }, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
