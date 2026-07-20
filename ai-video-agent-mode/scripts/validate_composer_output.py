#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''validate_composer_output.py - Phase 6 format gate + per-character action coverage.
Run after Prompt Composer agents complete. Returns non-zero exit if any shot fails.
Usage: python validate_composer_output.py <composer_output.json> [--run-dir <run_dir>]
       When --run-dir is provided, also validates per-character action coverage
       by cross-referencing with shot_plan.json visible_characters.
'''

import json, sys, re, os

REQUIRED_TITLES = [
    '人物站位与服装连续',
    '时长运镜场景目的',
    '时间分段叙事',
    '光照方案',
    '环境音设计',
    '负面提示词',
    '自包含验证',
]

NEG_MIN_KEYWORDS = [
    '画面崩坏', '面部扭曲', '五官错位', '多余肢体', '手指畸形',
    '角色换脸', '人物闪烁', '鬼影重叠', '道具漂移', '禁止角色静止站桩',
]

FORBIDDEN_ENGINES = ['C4D', 'Octane', 'Blender', 'Redshift', 'Arnold', 'Unreal Engine']

ACTION_VERBS = [
    '走向', '转身', '抬手', '迈步', '注视', '看向', '移动', '微动', '呼吸',
    '重心', '肩', '头', '手', '脚', '身体', '步伐', '抬头', '低头', '回头',
    '侧身', '弯腰', '踏步', '往前', '向前', '向后', '向左', '向右', '靠近',
    '走开', '离开', '抬腿', '站起', '坐下', '后退', '扭头', '回身', '进入',
    '走出', '挥手', '提起', '放下', '紧握', '摇头', '点头', '抬眸', '抬眉',
    '微侧', '微偏', '睁眼', '闭眼', '眨眼', '抬起', '下沉', '绷紧', '放松',
    '收缩', '扩张', '上扬', '下压', '抿紧', '微启', '咬紧', '松开', '鼓胀',
    '滚动', '眯起', '瞪大', '扫视', '打量', '盯着', '瞥', '瞧着'
]

CHAR_NAMES = ['沈星洲', '沈星雨', '向云初', '江训', '陆序', '许承']


def validate_composer_output(path, run_dir=None):
    with open(path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    shots = data.get('shots', [])
    issues = []

    # Load shot_plan for per-character validation if run_dir provided
    shot_plan = None
    if run_dir:
        plan_path = os.path.join(run_dir, '.cache', 'orchestrator', 'shot_plan.json')
        if os.path.exists(plan_path):
            with open(plan_path, 'r', encoding='utf-8-sig') as f:
                shot_plan = json.load(f)

    # Build subshot_id -> characters map from shot_plan
    subshot_chars = {}
    if shot_plan:
        for shot in shot_plan.get('shots', []):
            for ss in shot.get('subshots', []):
                chars = ss.get('characters', [])
                if isinstance(chars, str):
                    chars = [c.strip() for c in chars.split(';')]
                subshot_chars[ss['subshot_id']] = [c for c in chars if c in CHAR_NAMES]

    for s in shots:
        sid = s.get('subshot_id', '?')
        fp = s.get('full_prompt', '')

        # B0: duplicate title check
        for t in REQUIRED_TITLES:
            cnt = len(re.findall(rf'\n\n{t}', fp)) + (1 if fp.startswith(t) else 0)
            if cnt > 1:
                issues.append(f"{sid}: title '{t}' appears {cnt}x (must be 1)")

        # B1: newline count
        blank = fp.count('\n\n')
        if blank < 7:
            issues.append(f'{sid}: only {blank} blank lines (need >=7)')

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
            issues.append(f'{sid}: only {len(fp)} chars (min 800)')
        if len(fp) > 1800:
            issues.append(f'{sid}: {len(fp)} chars (max 1800)')

        # === NEW: Per-character action coverage (only for multi-char shots) ===
        if subshot_chars and sid in subshot_chars:
            chars = subshot_chars[sid]
            if len(chars) >= 2:
                neg_idx = fp.find('负面提示词')
                content = fp[:neg_idx] if neg_idx > 0 else fp

                frozen = []
                for ch in chars:
                    sentences = re.split(r'[。；\n]', content)
                    char_sents = [s for s in sentences if ch in s]
                    has_action = any(
                        any(verb in s for verb in ACTION_VERBS)
                        for s in char_sents
                    )
                    if not has_action:
                        frozen.append(ch)

                if frozen and len(chars) >= 2:
                    issues.append(
                        f'{sid}: FROZEN CHARS {frozen} — '
                        f'multi-char shot ({len(chars)} chars) but {frozen} '
                        f'have zero action verbs in content'
                    )

    if issues:
        frozen_count = sum(1 for i in issues if 'FROZEN' in i)
        other_count = len(issues) - frozen_count
        print(f'[VALIDATE] {len(issues)} issue(s) ({frozen_count} frozen-char, {other_count} format):')
        for i in issues[:30]:
            print(f'  - {i}')
        return 1

    print(f'[VALIDATE] PASS - {len(shots)} shots OK')
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: validate_composer_output.py <composer_output.json> [--run-dir <run_dir>]')
        sys.exit(2)
    run_dir = None
    args = [a for a in sys.argv if not a.startswith('--run-dir')]
    for i, a in enumerate(sys.argv):
        if a == '--run-dir' and i + 1 < len(sys.argv):
            run_dir = sys.argv[i + 1]
    sys.exit(validate_composer_output(args[1], run_dir))
