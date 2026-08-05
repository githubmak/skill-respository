#!/usr/bin/env python3
"""Check the creative minimum before engineering validation becomes the goal.

The checker is deliberately conservative: it reports a score and only blocks
high-confidence generic substitutions in strict mode. It never rewrites prompts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from validate_storyboard import direct_prompt, iter_children, iter_groups


FOCUS_TERMS = ("第一焦点", "唯一视觉落点", "焦点落在", "焦点锁")
RELATION_TERMS = ("面向", "视线", "听见", "看见", "回应", "转向", "靠近", "退开", "递", "接住", "隔着", "停住")
LIGHT_TERMS = ("主光", "光源", "灯光", "光线", "受光", "阴影", "光影")
LIGHT_DUTY_TERMS = ("显露", "遮蔽", "隔离", "吸引", "映出", "映入", "压暗", "扫过", "切开", "照亮关系", "暴露")
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
    for group in iter_groups(markdown):
        group_id = group.group(1)
        group_scores: list[int] = []
        group_has_light_duty = False
        for number, child in enumerate(iter_children(group.group(3)), start=1):
            shot_id = f"{group_id}-{number}"
            prompt = direct_prompt(child.group(0))
            if not prompt:
                continue
            result = score_prompt(prompt)
            score = int(result["score"])
            checks = result["checks"]
            group_scores.append(score)
            group_has_light_duty = group_has_light_duty or bool(checks["lighting_duty"])
            shots.append({"shot_id": shot_id, **result})
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
    return {"shots": shots, "groups": groups, "findings": findings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("storyboard")
    parser.add_argument("--advisory", action="store_true", help="report findings without failing")
    args = parser.parse_args(argv)
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
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
