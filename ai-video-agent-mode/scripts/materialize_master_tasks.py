#!/usr/bin/env python3
"""Derive one Jimeng T2V generation task per planned main shot.

Composer produces one main-shot task directly.  This legacy-named helper is
kept only as a compatibility reader for already-canonical packages; it never
joins separate child prompts or rewrites delivery content.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from modec_v4 import PROMPT_LABELS, jimeng_shot_group_issues, split_sections


def materialize(run_dir, source_path=None, output_path=None):
    source_path = source_path or os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json")
    output_path = output_path or os.path.join(run_dir, ".cache", "composer", "jimeng_master_tasks.json")
    plan_path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")
    package = _load(source_path)
    plan = _load(plan_path)
    existing = package.get("shots", []) if isinstance(package, dict) else []
    if existing and all(isinstance(item, dict) and item.get("source_subshot_ids") for item in existing):
        result = {"contract_version": "jimeng-t2v-v1", "shots": existing}
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
        return output_path, result
    by_id = {item.get("subshot_id", ""): item for item in existing if isinstance(item, dict)}
    masters, issues = [], []
    for planned in plan.get("shots", []):
        source_ids = [item.get("subshot_id", "") for item in planned.get("subshots", [])]
        children = [by_id.get(identifier) for identifier in source_ids]
        if not source_ids or any(child is None for child in children):
            issues.append("%s: missing composed child" % planned.get("shot_id", "?"))
            continue
        if len(children) > 3:
            issues.append("%s: more than three child shots" % planned.get("shot_id", "?"))
            continue
        master = _master_task(planned, children, plan)
        issues.extend("%s: %s" % (master["shot_id"], issue) for issue in jimeng_shot_group_issues(master["full_prompt"], master["qa_metadata"]["editorial_mode"]))
        masters.append(master)
    if issues:
        raise ValueError("; ".join(issues))
    result = {"contract_version": "jimeng-t2v-v1", "shots": masters}
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    return output_path, result


def _master_task(planned, children, plan):
    sections = [split_sections(child.get("full_prompt", ""), PROMPT_LABELS) for child in children]
    first = sections[0]
    offset, beats = 0.0, []
    for index, (child, section) in enumerate(zip(children, sections), 1):
        duration = float(child.get("duration", 0) or 0)
        content = _offset_ranges(section.get("子镜头组", ""), offset)
        content = re.sub(r"【镜头\d+[^】]*】", "", content).strip()
        beats.append("【镜头%d｜%.1f-%.1f秒｜%s】%s" % (index, offset, offset + duration, child.get("subshot_id", ""), _compact(content)))
        offset += duration
    mode = "shot_group" if len(children) > 1 else "continuous_take"
    full_prompt = "\n\n".join([
        "生成规格：" + _compact(first.get("生成规格", "")),
        "主体与空间锁定：" + "；".join(_compact(section.get("主体与空间锁定", "")) for section in sections),
        "主镜头连续规则：同一戏剧目标、同一场景光源和人物关系；" + "；".join(_compact(section.get("主镜头连续规则", "")) for section in sections),
        "子镜头组：" + "\n".join(beats),
        "光照、声音与稳定约束：" + "；".join(_compact(section.get("光照、声音与稳定约束", "")) for section in sections),
    ])
    dialogue_events = []
    for child in children:
        metadata = child.get("qa_metadata", {}) if isinstance(child.get("qa_metadata"), dict) else {}
        dialogue_events.extend(metadata.get("dialogue_events", []) if isinstance(metadata.get("dialogue_events"), list) else [])
    control = dict(children[0].get("generation_control", {}) or {})
    return {
        "shot_id": planned.get("shot_id", ""),
        "subshot_id": planned.get("shot_id", ""),
        "source_subshot_ids": [child.get("subshot_id", "") for child in children],
        "duration": round(offset, 3),
        "full_prompt": full_prompt,
        "negative_prompt": _merge_negative(children),
        "generation_control": control,
        "qa_metadata": {"editorial_mode": mode, "dialogue_events": dialogue_events, "source_subshot_ids": [child.get("subshot_id", "") for child in children]},
    }


def _merge_negative(children):
    terms = []
    for child in children:
        for term in re.split(r"[，,；;\n]+", str(child.get("negative_prompt", "") or "")):
            term = term.strip()
            if term and term not in terms:
                terms.append(term)
    return "，".join(terms[:8])


def _offset_ranges(text, offset):
    return re.sub(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)秒", lambda match: "%.1f-%.1f秒" % (float(match.group(1)) + offset, float(match.group(2)) + offset), str(text or ""))


def _compact(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit("usage: materialize_master_tasks.py <run_dir> [output_path]")
    path, result = materialize(sys.argv[1], output_path=sys.argv[2] if len(sys.argv) == 3 else None)
    print("[MASTER TASKS] %s (%d tasks)" % (path, len(result["shots"])))
