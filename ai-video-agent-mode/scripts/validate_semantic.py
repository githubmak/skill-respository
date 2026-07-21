import json
import os
import re
import sys


def _first_existing(run_dir, *paths):
    for path in paths:
        p = path if os.path.isabs(path) else os.path.join(run_dir, path)
        if os.path.exists(p):
            return p
    return os.path.join(run_dir, paths[0])


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _index_items(data, preferred):
    items = data.get("items")
    if items is None:
        items = data.get(preferred, [])
    result = {}
    for item in items:
        key = item.get("subshot_id") or item.get("shot_id")
        if key:
            result[key] = item
    return result


def validate(run_dir):
    """Semantic validation for the cache-based, subshot-aligned pipeline."""
    errors = []
    plan = _load(_first_existing(run_dir, ".cache/orchestrator/shot_plan.json", "shot_plan.json"))
    emotion = _load(_first_existing(run_dir, ".cache/analysis/emotion_output.json", "emotion_output.json"))
    scene = _load(_first_existing(run_dir, ".cache/analysis/scene_output.json", "scene_output.json"))
    camera = _load(_first_existing(run_dir, ".cache/analysis/camera_output.json", "camera_output.json"))

    emap = _index_items(emotion, "shots")
    smap = _index_items(scene, "analyses")
    cmap = _index_items(camera, "analysis")

    non_physical = ["（消息）", "（UI语音）", "（UI特效）", "（内心独白）"]
    close_indicators = ["面部近景", "面部特写", "中近景", "胸部以上"]

    ordered = []
    for shot in plan.get("shots", []):
        subshots = shot.get("subshots", []) or [{"subshot_id": shot.get("shot_id", ""), "characters": shot.get("characters", [])}]
        for ss in subshots:
            ssid = ss.get("subshot_id") or shot.get("shot_id", "")
            ordered.append((shot, ss, ssid))
            ca = cmap.get(ssid, {})
            se = smap.get(ssid, {})
            em = emap.get(ssid, {})
            if not ca and not se and not em:
                continue

            chars = ss.get("characters", [])
            phys = [c for c in chars if not any(n in c for n in non_physical)]
            if not phys and chars:
                errors.append("[违反规则] %s: 所有出场角色均为非物理实体（%s），机位将无合理参照物" % (ssid, chars))

            shot_size = ca.get("shot_size", "")
            if isinstance(shot_size, dict):
                shot_size = shot_size.get("层级", "")
            midground = ""
            layer = se.get("空间分层", {})
            if isinstance(layer, dict):
                midground = layer.get("中景", "") or ""
            midground = midground or se.get("bg_midground", "")
            if shot_size in ["全景", "远景"] and any(x in midground for x in close_indicators):
                errors.append("[景别矛盾] %s: camera_output 标 %s，但 scene_output 中景描述含 \"%s...\"" % (ssid, shot_size, midground[:20]))

            causality = em.get("expression_causality", "")
            values = causality.values() if isinstance(causality, dict) else [causality]
            for value in values:
                text = str(value)
                if re.search(r"→\.\.\.→|正在[待机发]|等待.*→|现在打字→", text):
                    errors.append("[占位文本] %s: 因果链含有疑似占位描述 \"%s...\"" % (ssid, text[:40]))

            intonation = em.get("intonation", "")
            if isinstance(intonation, str) and intonation and intonation != "无台词":
                if "复杂" in intonation or "无特别" in intonation or "带着复杂" in intonation:
                    errors.append("[占位语调] %s: 语调标注含有泛化描述 \"%s...\"" % (ssid, intonation[:30]))

    # Mode C v4 allows adjacent shots to keep the same shot size. Repetition is
    # only a semantic issue when framing, action, and dramatic function are all
    # duplicated; that judgment belongs to Editor Pass 2, not a string rule.

    return errors


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 validate_semantic.py <run_dir>")
        sys.exit(1)
    errs = validate(sys.argv[1])
    if errs:
        print("[QA 失败] 发现 %d 个语义问题：" % len(errs))
        for e in errs:
            print("  " + e)
        sys.exit(1)
    print("[QA 通过] 未发现语义问题")
