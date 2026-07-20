#!/usr/bin/env python3
"""validate_composer_output.py — Phase 6 后格式门禁。
Run after Prompt Composer agents complete. Returns non-zero exit if any shot fails.
Usage: python validate_composer_output.py <composer_output.json>
"""

import json, sys, re

REQUIRED_TITLES = [
    "人物站位与服装连续",
    "时长运镜场景目的",
    "时间分段叙事",
    "光照方案",
    "环境音设计",
    "负面提示词",
    "自包含验证",
]

NEG_MIN_KEYWORDS = [
    "画面崩坏", "面部扭曲", "五官错位", "多余肢体", "手指畸形",
    "角色换脸", "人物闪烁", "鬼影重叠", "道具漂移", "禁止角色静止站桩",
]

FORBIDDEN_ENGINES = ["C4D", "Octane", "Blender", "Redshift", "Arnold", "Unreal Engine"]

def validate(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    shots = data.get("shots", [])
    issues = []
    
    for s in shots:
        sid = s.get("subshot_id", "?")
        fp = s.get("full_prompt", "")
        
        # B0: duplicate check
    for t in REQUIRED_TITLES:
        cnt = len(re.findall(rf'\n\n{t}[：:]', fp)) + (1 if fp.startswith(t) else 0)
        if cnt > 1:
            issues.append(f"{sid}: title {chr(39)}{t}{chr(39)} appears {cnt}x (must be 1)")

    # B1: newline count
        blank = fp.count("\n\n")
        if blank < 7:
            issues.append(f"{sid}: only {blank} blank lines (need >=7)")
        
        # B2: required titles
        for t in REQUIRED_TITLES:
            if t not in fp:
                issues.append(f"{sid}: missing title '{t}'")
        
        # B3: negative prompt keywords
        for kw in NEG_MIN_KEYWORDS:
            if kw not in fp:
                issues.append(f"{sid}: missing neg keyword '{kw}'")
                break
        
        # B4: forbidden engines
        for eng in FORBIDDEN_ENGINES:
            if eng in fp:
                issues.append(f"{sid}: forbidden engine '{eng}'")
        
        # B5: word count
        if len(fp) < 800:
            issues.append(f"{sid}: only {len(fp)} chars (min 800)")
        if len(fp) > 1800:
            issues.append(f"{sid}: {len(fp)} chars (max 1800)")

    if issues:
        print(f"[VALIDATE] {len(issues)} issue(s):")
        for i in issues[:20]:
            print(f"  - {i}")
        return 1
    print(f"[VALIDATE] PASS - {len(shots)} shots OK")
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: validate_composer_output.py <composer_output.json>")
        sys.exit(2)
    sys.exit(validate(sys.argv[1]))

