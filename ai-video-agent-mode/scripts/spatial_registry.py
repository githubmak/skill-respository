#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""spatial_registry.py - Phase 1 spatial coordinate injection + dual-track scene_type."""
import json, os, re, sys

X_PATTERNS = {
    'zuo': [r'(?:在|于|居|站|坐|处)(?:画面)?(?:最)?(?:左|左侧|左方|画左)'],
    'you': [r'(?:在|于|居|站|坐|处)(?:画面)?(?:最)?(?:右|右侧|右方|画右)'],
    'zhong': [r'(?:在|于|居|站|坐|处)(?:画面)?(?:中央|中间|正中|中心)'],


}
Y_PATTERNS = {
    "qian": [r"(?:在|于|居)(?:画面)?(?:最)?(?:前景|近景|近处|前面)"],
    "zhong": [r"(?:在|于|居)(?:画面)?(?:中景|中层)"],
    "hou": [r"(?:在|于|居)(?:画面)?(?:最)?(?:后景|背景|远景|远处|深处|后面)"],
}

FACING_PATTERNS = {
    "zuo": [r"(?:面向|朝向|看向|面对|对着|面朝)(?:画面)?(?:左|左侧|左方)"],
    "you": [r"(?:面向|朝向|看向|面对|对着|面朝)(?:画面)?(?:右|右侧|右方)"],
    "qian": [r"(?:面向|朝向|看向|面对|对着|面朝)(?:画面)?(?:前|前方|正面|镜头)"],
}

ACTION_KEYWORDS = [
    '追逐',
    '追赶',
    '狂奔',
    '奔跑',
    '疾跑',
    '飞跑',
    '冲刺',
    '掠过',
    '穿梭',
    '飞奔',
    '猛冲',
    '翻越',
    '跳跃',
    '跳下',
    '翻身',
    '跃过',
    '跨过',
    '跳过',
    '躲避',
    '避开',
    '闪开',
    '躲避攻击',
    '急速',
    '快步',
    '冲出去',
    '冲进',
    '冲入',
    '箭步',
    '三步并作两步',
    '飙车',
    '追逐战',
    '追车',
]

FIGHT_KEYWORDS = [
    '打斗',
    '出手',
    '出拳',
    '挥拳',
    '踢',
    '踹',
    '肘击',
    '膝撞',
    '头槌',
    '掌击',
    '劈',
    '砍',
    '刺',
    '捘',
    '鞭',
    '棍',
    '剑',
    '刀',
    '击中',
    '命中',
    '击打',
    '重击',
    '连击',
    '反击',
    '格斗',
    '搏斗',
    '搏击',
    '混战',
    '厮打',
    '扭打',
    '缠斗',
    '交手',
    '攻击',
    '袭击',
    '突袭',
    '偷袭',
    '猛攻',
    '摔',
    '摔倒',
    '摔翻',
    '过肩摔',
    '擂倒',
    '按倒',
    '绞',
    '锁喉',
    '擒拿',
    '反擒',
    '制服',
    '撞',
    '撞倒',
    '冲撞',
    '撞上',
    '撞飞',
    '闪避',
    '侧闪',
    '躲开',
    '避开',
    '格挡',
    '挡下',
    '架开',
    '卸力',
    '化解',
    '拨开',
    '推开',
    '推搑',
    '揪住',
    '拽',
    '拉扯',
    '拖',
    '甩开',
    '挟脱',
    '倒地',
    '倒下',
    '按在地上',
    '压制',
    '骑在身上',
    '拔刀',
    '拔剑',
    '抽刀',
    '亮兵器',
    '暗器',
    '拔枪',
    '举枪',
    '瞄准',
    '扣动扳机',
    '冲刺',
    '扑',
    '扑倒',
    '扑上去',
    '飞扑',
    '扑过来',
    '猛扑',
]

NEGATED_ACTION_PREFIX = re.compile(r'(?:不曾|不再|不能|不要|不带|不|没|没有|无|未|并非|绝不).{0,4}$')

def _parse_position(text, patterns):
    for label, pats in patterns.items():
        for pat in pats:
            if re.search(pat, text):
                return label
    return None


def _parse_character_position(text, char_name):
    segments = []
    for sent in re.split(r"[。；\n]", text):
        if char_name in sent:
            segments.append(sent)
    if not segments:
        return None, None, None
    char_text = " ".join(segments)
    x = _parse_position(char_text, X_PATTERNS)
    y = _parse_position(char_text, Y_PATTERNS)
    facing = _parse_position(char_text, FACING_PATTERNS)
    if not facing and x:
        if x == "zuo":
            facing = "you"
        elif x == "you":
            facing = "zuo"
    return x, y, facing


def _detect_scene_type(text):
    if _has_scene_keyword(text, FIGHT_KEYWORDS):
        return "fight"
    if _has_scene_keyword(text, ACTION_KEYWORDS):
        return "action"
    return "dialogue"


def _has_scene_keyword(text, keywords):
    text = str(text or "")
    for kw in keywords:
        start = 0
        while True:
            idx = text.find(kw, start)
            if idx < 0:
                break
            prefix = text[max(0, idx - 8):idx]
            if not NEGATED_ACTION_PREFIX.search(prefix):
                return True
            start = idx + len(kw)
    return False


def _build_spatial_map(base_action, characters):
    if not characters or not base_action:
        return {}, "dialogue", True
    spatial_map = {}
    all_known = True
    for ch in characters:
        if not ch or ch in ("系统", "OV", "OS"):
            continue
        x, y, facing = _parse_character_position(base_action, ch)
        if x or y or facing:
            spatial_map[ch] = {"screen_x": x or "unknown", "screen_y": y or "mid", "facing": facing or "unknown"}
        else:
            spatial_map[ch] = {"screen_x": "auto", "screen_y": "auto", "facing": "auto"}
            all_known = False
    scene_type = _detect_scene_type(base_action)
    return spatial_map, scene_type, all_known


def run(run_dir, shot_plan_path=None):
    if shot_plan_path is None:
        plan_path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")
        if not os.path.exists(plan_path):
            plan_path = os.path.join(run_dir, "shot_plan.draft.json")
    else:
        plan_path = shot_plan_path
    if not os.path.exists(plan_path):
        print("[SPATIAL_REGISTRY] no shot_plan at", plan_path)
        return 1
    with open(plan_path, "r", encoding="utf-8-sig") as f:
        sp = json.load(f)
    backup = plan_path.replace(".json", ".pre_spatial.json")
    with open(backup, "w", encoding="utf-8") as f:
        json.dump(sp, f, ensure_ascii=False, indent=2)
    total = parsed = auto = fight_c = action_c = 0
    for shot in sp.get("shots", []):
        for ss in shot.get("subshots", []):
            total += 1
            chars = ss.get("characters", [])
            if isinstance(chars, str):
                chars = [c.strip() for c in chars.split(";")]
            spatial_map, st, ok = _build_spatial_map(ss.get("base_action", ""), chars)
            ss["spatial_map"] = spatial_map
            ss["scene_type"] = st
            if ok:
                parsed += 1
            else:
                auto += 1
            if st == "fight":
                fight_c += 1
            elif st == "action":
                action_c += 1
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(sp, f, ensure_ascii=False, indent=2)
    print("[SPATIAL_REGISTRY]", total, "subshots")
    print("  Parsed:", parsed, f"({100*parsed//max(total,1)}%)")
    print("  Auto:", auto, f"({100*auto//max(total,1)}%)")
    print("  Fight:", fight_c, "Action:", action_c)
    print("  Backup:", backup)
    return 0


def merge_scene_type(run_dir, agent_scene_types=None):
    plan_path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")
    if not os.path.exists(plan_path):
        plan_path = os.path.join(run_dir, "shot_plan.draft.json")
    if not os.path.exists(plan_path):
        return {}
    with open(plan_path, "r", encoding="utf-8-sig") as f:
        sp = json.load(f)
    if agent_scene_types is None:
        agent_scene_types = {}
        scene_out = os.path.join(run_dir, ".cache", "analysis", "scene_output.json")
        if os.path.exists(scene_out):
            with open(scene_out, "r", encoding="utf-8-sig") as f:
                sd = json.load(f)
            for item in sd.get("items", []):
                sid = item.get("subshot_id", item.get("id", ""))
                st = item.get("scene_type", "")
                if sid and st:
                    agent_scene_types[sid] = st
    priority = {"fight": 3, "action": 2, "dialogue": 1}
    results = {}
    changes = 0
    for shot in sp.get("shots", []):
        for ss in shot.get("subshots", []):
            sid = ss.get("subshot_id", "")
            kt = ss.get("scene_type", "dialogue")
            at = agent_scene_types.get(sid, "dialogue")
            if priority.get(at, 0) > priority.get(kt, 0):
                ss["scene_type"] = at
                results[sid] = (kt, at, at, "agent")
                changes += 1
            else:
                results[sid] = (kt, at, kt, "keyword")
    if changes > 0:
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(sp, f, ensure_ascii=False, indent=2)
    print("[MERGE_SCENE_TYPE]", changes, "Agent upgrades,", len(results), "total")
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 spatial_registry.py <run_dir>")
        sys.exit(2)
    sys.exit(run(sys.argv[1]))
