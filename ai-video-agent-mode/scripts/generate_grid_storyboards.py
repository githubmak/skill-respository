"""Derive optional nine-panel story packages from an approved T2V prompt package."""

import json
import os
import re
import sys

from handler_registry import register_handler


OUTPUT_RELATIVE_PATH = ".cache/grid_storyboard/packages.json"
HIGH_RISK = {"high", "reference_required"}
TENSION_KEYWORDS = ("rising", "peak", "release", "压住", "触发", "泄露", "对视", "逼近", "阻挡")
ACTION_KEYWORDS = ("打", "追", "跑", "拦", "躲", "推", "拉", "夺", "逼近", "后退", "转身", "对峙")


def generate(run_dir):
    config = _load(os.path.join(run_dir, "project_config.json"))
    grid_config = config.get("storyboard_grid", {})
    if not isinstance(grid_config, dict) or grid_config.get("enabled") is not True:
        raise RuntimeError("storyboard_grid.enabled is not true")

    package = _load(_find_package(run_dir))
    plan = _load(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"))
    director = _load(os.path.join(run_dir, ".cache", "director", "director_pass.json"))
    by_id = {shot.get("subshot_id", ""): shot for shot in package.get("shots", [])}
    director_by_id = {item.get("subshot_id", ""): item for item in director.get("items", [])}
    threshold = _as_int(grid_config.get("minimum_score"), 4)
    max_per_scene = max(1, _as_int(grid_config.get("max_chains_per_scene"), 2))

    candidates = []
    for master in plan.get("shots", []):
        subshots = [by_id.get(item.get("subshot_id", "")) for item in master.get("subshots", [])]
        subshots = [item for item in subshots if isinstance(item, dict)]
        if not subshots:
            continue
        score, reasons = _score_chain(master, subshots)
        if score < threshold:
            continue
        candidates.append({
            "score": score,
            "reasons": reasons,
            "master": master,
            "subshots": subshots,
        })

    selected = _limit_by_scene(candidates, max_per_scene)
    packages = [
        _build_package(candidate, config, director_by_id)
        for candidate in selected
    ]
    result = {
        "schema_version": "grid-storyboard-v1",
        "enabled": True,
        "selection_mode": "auto",
        "packages": packages,
    }
    output_path = os.path.join(run_dir, OUTPUT_RELATIVE_PATH)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print("[GRID] selected %d chain(s) -> %s" % (len(packages), output_path))
    return result


def validate(path):
    data = _load(path)
    if data.get("schema_version") != "grid-storyboard-v1" or data.get("enabled") is not True:
        return ["九宫格剧情包根字段无效"]
    packages = data.get("packages")
    if not isinstance(packages, list):
        return ["九宫格剧情包packages必须是数组"]
    issues = []
    seen = set()
    for package in packages:
        chain_id = package.get("chain_id", "")
        if not chain_id or chain_id in seen:
            issues.append("九宫格剧情包chain_id缺失或重复")
        seen.add(chain_id)
        beats = package.get("beats", [])
        if not isinstance(beats, list) or len(beats) != 9:
            issues.append("%s必须包含9个剧情节拍" % chain_id)
        elif [beat.get("panel_id") for beat in beats] != ["P%02d" % number for number in range(1, 10)]:
            issues.append("%s剧情节拍必须按P01-P09顺序" % chain_id)
        if not str(package.get("grid_prompt", "")).strip():
            issues.append("%s缺少九宫格总图提示词" % chain_id)
    return issues


def _score_chain(master, subshots):
    score = 0
    reasons = []
    characters = _characters(master, subshots)
    if len(characters) >= 2:
        score += 2
        reasons.append("多人关系与站位需要连续预演")
    if len(subshots) >= 2:
        score += 1
        reasons.append("同一主镜包含多个连续节拍")
    total_duration = sum(_as_float(shot.get("duration")) for shot in subshots)
    if total_duration >= 6:
        score += 1
        reasons.append("连续时长较长")

    blob = " ".join(_chain_text(master, subshots))
    if any(keyword in blob for keyword in TENSION_KEYWORDS):
        score += 2
        reasons.append("存在可视的情绪递进")
    if any(keyword in blob for keyword in ACTION_KEYWORDS):
        score += 2
        reasons.append("存在高风险动作或关系调度")
    if any(_risk_level(shot) in HIGH_RISK for shot in subshots):
        score += 1
        reasons.append("T2V抽卡风险较高")
    start = _state(subshots[0], "start")
    end = _state(subshots[-1], "end")
    if start and end and start != end:
        score += 1
        reasons.append("起止状态存在可见转移")
    return score, reasons


def _build_package(candidate, config, director_by_id):
    master = candidate["master"]
    subshots = candidate["subshots"]
    chain_id = master.get("shot_id", "")
    scene = master.get("scene", "场景")
    characters = _characters(master, subshots)
    beats = _build_beats(subshots)
    visual_style = str(config.get("visual_style", "") or "当前项目已确认视觉风格").strip()
    canvas = str(config.get("canvas", "") or "当前项目画幅").strip()
    lighting = _first_text(director_by_id.get(subshots[0].get("subshot_id", ""), {}).get("lighting", ""))
    prompt = _build_grid_prompt(canvas, visual_style, scene, characters, lighting, beats)
    negatives = _unique_negative_terms(subshots)
    return {
        "chain_id": chain_id,
        "scene": scene,
        "subshot_ids": [shot.get("subshot_id", "") for shot in subshots],
        "selection_score": candidate["score"],
        "selection_reasons": candidate["reasons"],
        "grid_prompt": prompt,
        "negative_prompt": negatives,
        "beats": beats,
    }


def _build_beats(subshots):
    first = subshots[0]
    last = subshots[-1]
    goal = _state(first, "goal") or _state(last, "goal") or "完成当前剧情关系变化"
    trigger = _state(first, "trigger") or _state(last, "trigger") or "剧情触发发生"
    start = _state(first, "start") or "继承上一镜起始状态"
    end = _state(last, "end") or "保留下一镜需要继承的终态"
    source_index = lambda position: min(len(subshots) - 1, int(position * len(subshots) / 9))
    templates = [
        "起始构图：%s" % start,
        "压住反应：保持起始站位，只出现可见的低幅生命迹象",
        "触发临近：%s" % trigger,
        "身体先反应：手、肩背或重心先出现与触发一致的变化",
        "情绪泄露：在当前景别可见的眉眼、视线或呼吸中出现短暂变化",
        "关系或主动作推进：%s" % goal,
        "结果确认：人物、道具与空间关系完成本段可见转移",
        "余波回稳：保留事件造成的视线、姿态或道具残留",
        "落幅构图：%s" % end,
    ]
    beats = []
    for index, description in enumerate(templates):
        source = subshots[source_index(index)]
        beats.append({
            "panel_id": "P%02d" % (index + 1),
            "source_subshot_id": source.get("subshot_id", ""),
            "description": _clean(description),
        })
    return beats


def _build_grid_prompt(canvas, style, scene, characters, lighting, beats):
    character_text = "、".join(characters) if characters else "当前镜头可见人物"
    panels = "；".join("%d【%s】" % (index + 1, beat["description"]) for index, beat in enumerate(beats))
    light_text = "；光线继承当前场景已确认主光源关系" + ("，%s" % lighting if lighting else "")
    return _clean(
        "生成一张3×3九宫格连续剧情分镜总图，%s，%s；同一场景%s，同一组人物%s，"
        "人物身份、五官、发型、已确认服装、体型、场景结构、道具状态和光影色调全程一致%s。"
        "九格按左上到右下的行优先顺序连续叙事：%s。"
        "每格构图独立但保持同一摄影轴线与空间逻辑，动作是前一格的自然延续；九格之间保留极细无文字留白，"
        "无编号、无对话框、无水印、无新增人物或服装细节。" % (canvas, style, scene, character_text, light_text, panels)
    )


def _limit_by_scene(candidates, limit):
    selected = []
    counts = {}
    for candidate in sorted(candidates, key=lambda item: (-item["score"], item["master"].get("shot_id", ""))):
        scene = candidate["master"].get("scene", "场景")
        if counts.get(scene, 0) >= limit:
            continue
        counts[scene] = counts.get(scene, 0) + 1
        selected.append(candidate)
    return selected


def _characters(master, subshots):
    values = master.get("characters", [])
    if not values:
        values = []
        for shot in subshots:
            metadata = shot.get("qa_metadata", {}) if isinstance(shot.get("qa_metadata"), dict) else {}
            roles = metadata.get("performance_priority", {}) if isinstance(metadata.get("performance_priority"), dict) else {}
            values.append(roles.get("primary", ""))
            supporting = roles.get("supporting", [])
            if isinstance(supporting, str):
                values.extend(re.split(r"[，,、/；;]+", supporting))
            elif isinstance(supporting, list):
                values.extend(supporting)
    if isinstance(values, str):
        values = re.split(r"[，,、/；;]+", values)
    return list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _chain_text(master, subshots):
    values = [master.get("purpose", ""), master.get("base_action", "")]
    for shot in subshots:
        metadata = shot.get("qa_metadata", {}) if isinstance(shot.get("qa_metadata"), dict) else {}
        values.extend([
            shot.get("full_prompt", ""), metadata.get("dramatic_goal", ""),
            json.dumps(metadata.get("performance_contract", {}), ensure_ascii=False),
            json.dumps(metadata.get("performance_causality", {}), ensure_ascii=False),
        ])
    return [str(value or "") for value in values]


def _risk_level(shot):
    metadata = shot.get("qa_metadata", {}) if isinstance(shot.get("qa_metadata"), dict) else {}
    reroll = metadata.get("reroll_control", {}) if isinstance(metadata.get("reroll_control"), dict) else {}
    return str(reroll.get("risk_level", "") or "").strip()


def _state(shot, kind):
    metadata = shot.get("qa_metadata", {}) if isinstance(shot.get("qa_metadata"), dict) else {}
    contract = metadata.get("performance_contract", {}) if isinstance(metadata.get("performance_contract"), dict) else {}
    causality = metadata.get("performance_causality", {}) if isinstance(metadata.get("performance_causality"), dict) else {}
    mapping = {
        "start": (metadata.get("start_state"), contract.get("start_state")),
        "end": (metadata.get("end_state"), contract.get("end_residue")),
        "goal": (metadata.get("dramatic_goal"), contract.get("audience_empathy_anchor")),
        "trigger": (causality.get("trigger"), contract.get("trigger_event")),
    }
    return _first_text(*mapping[kind])


def _unique_negative_terms(subshots):
    terms = []
    for shot in subshots:
        terms.extend(re.split(r"[，,；;\n]+", str(shot.get("negative_prompt", "") or "")))
    terms = list(dict.fromkeys(term.strip() for term in terms if term.strip()))
    return "，".join(terms[:18])


def _find_package(run_dir):
    for relative in (
        ".cache/composer/merged.prompt_package.json",
        ".cache/composer/prompt_package.json",
        ".cache/prompt_package.json",
    ):
        path = os.path.join(run_dir, relative)
        if os.path.exists(path):
            return path
    raise FileNotFoundError("Missing normalized prompt package")


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _first_text(*values):
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _clean(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _as_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _as_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@register_handler("grid_storyboard")
def _grid_storyboard_handler(run_dir):
    return generate(run_dir)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: generate_grid_storyboards.py <run_dir>")
        sys.exit(2)
    generate(sys.argv[1])
