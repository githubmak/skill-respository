#!/usr/bin/env python3
"""Build and validate an episode-wide continuity and semantic-lineage graph."""

import json
import os
import re
import sys

from contract_registry import PROMPT_CONTRACT_VERSION
from pipeline_runtime import atomic_json


FACT_PATTERNS = {
    "hand": (("左手",), ("右手",)),
    "screen_side": (("画面左", "画左"), ("画面右", "画右")),
    "phone_screen": (("亮屏", "屏幕亮", "来电界面"), ("熄屏", "黑屏", "屏幕关闭")),
    "door_state": (("门打开", "门已开", "开着的门"), ("门关闭", "门已关", "关着的门")),
    "body_level": (("站立", "站稳", "站着"), ("坐着", "坐稳", "坐在"), ("躺着", "躺在", "平躺")),
}


def build_episode_state_graph(run_dir, output_path=None):
    package_path = _find_package(run_dir)
    package = _load(package_path) if package_path else {}
    graph = analyze_package(package)
    output_path = output_path or os.path.join(run_dir, ".cache", "validate", "episode_state_graph.json")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    atomic_json(output_path, graph)
    return graph, output_path


def analyze_package(package):
    shots = package.get("shots", []) if isinstance(package, dict) else []
    shots = shots if isinstance(shots, list) else []
    issues, warnings, nodes, edges = [], [], [], []
    space_locks, source_owners, subject_states = {}, {}, {}
    previous = None

    for index, shot in enumerate(shots):
        if not isinstance(shot, dict):
            issues.append("shots[%d]必须是对象" % index)
            continue
        sid = str(shot.get("subshot_id", shot.get("shot_id", "")) or "?")
        metadata = shot.get("qa_metadata", {}) if isinstance(shot.get("qa_metadata"), dict) else {}
        continuity = metadata.get("continuity_contract", {}) if isinstance(metadata.get("continuity_contract"), dict) else {}
        palette = metadata.get("scene_tone_palette", {}) if isinstance(metadata.get("scene_tone_palette"), dict) else {}
        space_id = str(palette.get("space_id", "") or "")
        source_refs = _string_list(shot.get("source_subshot_ids", [shot.get("subshot_id", "")]))
        dialogue_refs = _string_list(metadata.get("dialogue_refs", []))
        transitions = continuity.get("state_transitions", [])
        transitions = transitions if isinstance(transitions, list) else []

        for source_ref in source_refs:
            owner = source_owners.setdefault(source_ref, sid)
            if owner != sid:
                issues.append("来源%s被主镜%s与%s重复消费" % (source_ref, owner, sid))

        _check_space_lock(space_locks, space_id, palette, sid, issues)
        node = {
            "index": index,
            "shot_id": str(shot.get("shot_id", "") or ""),
            "subshot_id": sid,
            "space_id": space_id,
            "start_anchor": str(continuity.get("start_anchor", "") or ""),
            "end_anchor": str(continuity.get("end_anchor", "") or ""),
            "next_carryover": str(continuity.get("next_carryover", "") or ""),
            "semantic_lineage": {
                "source_refs": source_refs,
                "scene_lock_ref": space_id,
                "dialogue_refs": dialogue_refs,
                "derived_contracts": _active_contracts(metadata),
            },
            "state_transitions": transitions,
        }
        nodes.append(node)

        if previous is not None:
            conflict = _fact_conflicts(previous["next_carryover"] or previous["end_anchor"], node["start_anchor"])
            edge = {
                "from": previous["subshot_id"], "to": sid,
                "carryover": previous["next_carryover"], "start_anchor": node["start_anchor"],
                "fact_conflicts": conflict,
            }
            edges.append(edge)
            if conflict:
                issues.append("%s→%s起幅与承接存在明确事实冲突：%s" % (
                    previous["subshot_id"], sid, "、".join(conflict)
                ))
            elif previous["next_carryover"] and node["start_anchor"] and not _shares_anchor(previous["next_carryover"], node["start_anchor"]):
                warnings.append("%s→%s承接与起幅缺少可自动匹配的共同锚点，需Editor Pass 2语义复核" % (
                    previous["subshot_id"], sid
                ))

        for transition in transitions:
            if not isinstance(transition, dict):
                continue
            subject = str(transition.get("subject", "") or "").strip()
            if not subject:
                continue
            key = (space_id, subject)
            from_state = str(transition.get("from_state", "") or "")
            to_state = str(transition.get("to_state", "") or "")
            prior = subject_states.get(key)
            if prior:
                conflict = _fact_conflicts(prior["state"], from_state)
                if conflict:
                    issues.append("%s在%s的长程状态与%s起态冲突：%s" % (
                        subject, prior["shot_id"], sid, "、".join(conflict)
                    ))
            if to_state:
                subject_states[key] = {"shot_id": sid, "state": to_state}
        previous = node

    return {
        "contract_version": PROMPT_CONTRACT_VERSION,
        "graph_version": "episode-state-graph-v1",
        "pass": bool(nodes) and not issues,
        "issues": issues,
        "warnings": warnings,
        "summary": {
            "shot_count": len(nodes),
            "edge_count": len(edges),
            "space_count": len(space_locks),
            "source_ref_count": len(source_owners),
            "tracked_subject_count": len(subject_states),
        },
        "nodes": nodes,
        "edges": edges,
    }


def _check_space_lock(space_locks, space_id, palette, sid, issues):
    if not space_id:
        return
    current = {
        "space_master_sentence": str(palette.get("space_master_sentence", "") or "").strip(),
        "tone_palette": str(palette.get("tone_palette", "") or "").strip(),
    }
    locked = space_locks.setdefault(space_id, {"shot_id": sid, **current})
    for field, label in (("space_master_sentence", "空间主锁定"), ("tone_palette", "影调色卡")):
        if locked.get(field) and current.get(field) and locked[field] != current[field]:
            issues.append("空间%s在%s与%s的%s不一致" % (space_id, locked["shot_id"], sid, label))


def _active_contracts(metadata):
    names = (
        "source_constraint_basemap", "performance_contract", "continuity_contract",
        "story_punch_contract", "reroll_control", "pressure_release_design",
        "cinematic_image_contract", "video_texture_contract",
    )
    return [name for name in names if isinstance(metadata.get(name), dict) and metadata.get(name)]


def _fact_conflicts(left, right):
    conflicts = []
    for label, alternatives in FACT_PATTERNS.items():
        left_values = _matched_alternatives(left, alternatives)
        right_values = _matched_alternatives(right, alternatives)
        if left_values and right_values and left_values.isdisjoint(right_values):
            conflicts.append(label)
    return conflicts


def _matched_alternatives(text, alternatives):
    value = str(text or "")
    return {index for index, tokens in enumerate(alternatives) if any(token in value for token in tokens)}


def _shares_anchor(left, right):
    left_tokens = set(_anchor_tokens(left))
    right_tokens = set(_anchor_tokens(right))
    return bool(left_tokens & right_tokens)


def _anchor_tokens(text):
    return [token for token in re.findall(r"[\u4e00-\u9fff]{2,8}|[A-Za-z0-9_-]+", str(text or "")) if token not in {"下一镜", "落幅", "保持", "画面"}]


def _string_list(value):
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _find_package(run_dir):
    for relative in (
        ".cache/composer/merged.prompt_package.json",
        ".cache/composer/prompt_package.json",
        ".cache/prompt_package.json",
    ):
        path = os.path.join(run_dir, relative)
        if os.path.isfile(path):
            return path
    return ""


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit("usage: episode_state_graph.py <run_dir> [output.json]")
    result, path = build_episode_state_graph(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)
    print("[EPISODE STATE GRAPH] %s: %s" % ("PASS" if result["pass"] else "FAIL", path))
    for issue in result["issues"]:
        print("- " + issue)
    raise SystemExit(0 if result["pass"] else 1)
