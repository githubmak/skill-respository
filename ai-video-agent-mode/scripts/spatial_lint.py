#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''spatial_lint.py — Cross-shot spatial continuity validator.

Four-dimensional check:
  D1: Position continuity — no character teleportation across adjacent shots
  D2: Camera-position consistency — camera movement doesn't contradict character positions
  D3: Action trajectory completeness — every movement action has direction+distance+speed+path
  D4: Fight chain validation — contact point + force direction + receiver reaction

Run after Phase 3 (director_pass assembly). Requires shot_plan.json with spatial_map.

Usage:
    python spatial_lint.py <run_dir>
    python spatial_lint.py <run_dir> --mode [full|camera|action|fight]

Output:
    .cache/spatial/report.json with blocking/warning/info issues
'''

import json, os, re, sys

# === Camera-position constraint matrix ===
CAMERA_POSITION_RULES = {
    # (speaker_zone, camera_movement) -> severity (blocking/warning/ok)
    ('左侧', '大幅度向右横移'): 'blocking',
    ('左侧', '右摇'): 'warning',
    ('右侧', '大幅度向左横移'): 'blocking',
    ('右侧', '左摇'): 'warning',
}

CAMERA_BLOCKING_MOVEMENTS = {
    '大幅度向右横移': ['左侧'],
    '大幅度向左横移': ['右侧'],
    '单向大幅横移': ['左侧', '右侧', '中央'],
}

CAMERA_FIGHT_RULES = {
    '打击瞬间': {'allow': ['固定', '微震', '快速切镜'], 'block': ['慢推拉', '大幅度摇移']},
    '追逐': {'allow': ['跟拍', '侧移跟拍'], 'block': ['固定']},
    '倒地': {'allow': ['固定', '极慢微推'], 'block': ['大幅度摇移', '快速切镜']},
}

# === Action trajectory required fields ===
TRAJECTORY_DIRECTION = r'(?:向左|向右|向前|向后|从[^，。]+到[^，。]+|画左|画右|前方|后方)'
TRAJECTORY_DISTANCE = r'(?:\d+步|\d+\.?\d*米|\d+cm|半步|微|数步|几步)'
TRAJECTORY_SPEED = r'(?:\d+\.?\d*m/s|冲刺|快步|缓步|慢步|奔跑|疾步|踱步)'
TRAJECTORY_PATH = r'(?:直线|弧线|S形|曲线|直线冲刺|绕行|侧闪|翻滚|迂回)'

# === Fight chain required fields ===
FIGHT_CONTACT = r'(?:命中|击中|击打|拳峰|掌心|肘尖|膝盖|脚尖|踢中|踹中|撞上|碰到)'
FIGHT_FORCE_DIRECTION = r'(?:从左向右|从右向左|横向|纵向|向上|向下|斜|水平|垂直)'
FIGHT_RECEIVER_REACTION = r'(?:后退|踉跄|后仰|侧身|格挡|卸力|硬直|倒地|翻滚|后退半步|后退一步|后撤)'

# Characters that don't need spatial tracking
NON_SPATIAL_CHARS = {'系统', 'OV', 'OS', ''}


def _get_characters(ss, known_chars=None):
    '''Get list of spatial-tracked characters in a subshot.'''
    chars = ss.get('characters', [])
    if isinstance(chars, str):
        chars = [c.strip() for c in chars.split(';')]
    return [c for c in chars if c and c not in NON_SPATIAL_CHARS]


def _check_position_continuity(prev_spatial, curr_spatial, prev_chars, curr_chars):
    '''D1: Check no character teleports between adjacent shots.'''
    issues = []

    for ch in set(prev_chars) & set(curr_chars):
        prev_pos = prev_spatial.get(ch, {})
        curr_pos = curr_spatial.get(ch, {})

        prev_x = prev_pos.get('screen_x', 'auto')
        curr_x = curr_pos.get('screen_x', 'auto')

        if prev_x == 'auto' or curr_x == 'auto':
            continue

        # Direct flip without transition
        if prev_x == '左侧' and curr_x == '右侧':
            transition = curr_spatial.get(ch, {}).get('_transition', '')
            if 'cross' not in transition.lower():
                issues.append({
                    'type': 'POSITION_TELEPORT',
                    'severity': 'blocking',
                    'character': ch,
                    'detail': f'{ch}从画面左侧直接跳至右侧，缺少过渡理由(绕行/转身/过肩)'
                })
        elif prev_x == '右侧' and curr_x == '左侧':
            transition = curr_spatial.get(ch, {}).get('_transition', '')
            if 'cross' not in transition.lower():
                issues.append({
                    'type': 'POSITION_TELEPORT',
                    'severity': 'blocking',
                    'character': ch,
                    'detail': f'{ch}从画面右侧直接跳至左侧，缺少过渡理由'
                })

        # Multi-char x-order reversal
        pass  # Requires pairwise comparison across all chars — deferred

    return issues


def _check_camera_position_consistency(spatial_map, camera_movement, speaker=None):
    '''D2: Camera movement must respect character positions.'''
    issues = []

    if not camera_movement or not spatial_map:
        return issues

    # Find all x positions
    all_x = {pos.get('screen_x') for pos in spatial_map.values()
             if pos.get('screen_x') not in ('auto', '未知', None)}

    # Check blocking rules
    for block_movement, blocked_zones in CAMERA_BLOCKING_MOVEMENTS.items():
        if block_movement in camera_movement:
            for zone in blocked_zones:
                if zone in all_x:
                    issues.append({
                        'type': 'CAMERA_POSITION_CONFLICT',
                        'severity': 'blocking',
                        'detail': f'角色在画面{zone}，禁止{block_movement}(会丢失角色)'
                    })

    return issues


def _check_action_trajectory(time_segment, subshot_id):
    '''D3: Every movement action needs direction + distance + speed + path type.'''
    issues = []

    # Check if this shot has character movement
    has_movement = bool(re.search(r'(?:走向|转身|跑|冲刺|移动|后退|前进|侧移|靠近|离开)', time_segment))
    if not has_movement:
        return issues

    checks = {
        '方向': TRAJECTORY_DIRECTION,
        '距离/幅度': TRAJECTORY_DISTANCE,
        '速度': TRAJECTORY_SPEED,
    }

    for label, pattern in checks.items():
        if not re.search(pattern, time_segment):
            issues.append({
                'type': 'ACTION_TRAJECTORY_INCOMPLETE',
                'severity': 'warning',
                'shot': subshot_id,
                'detail': f'动作缺少{label}描述'
            })

    # Path type is nice-to-have, not required for dialogue scenes
    has_path = bool(re.search(TRAJECTORY_PATH, time_segment))
    if not has_path and re.search(r'(?:打斗|冲刺|追逐|闪避)', time_segment):
        issues.append({
            'type': 'ACTION_TRAJECTORY_INCOMPLETE',
            'severity': 'warning',
            'shot': subshot_id,
            'detail': '高速动作缺少轨迹类型(直线/弧线/侧闪)'
        })

    return issues


def _check_fight_chain(time_segment, subshot_id, scene_type):
    '''D4: Fight actions must have contact + force + receiver reaction.'''
    issues = []

    if scene_type != 'fight':
        return issues

    has_strike = bool(re.search(r'(?:出拳|挥拳|踢|踹|肘击|膝撞|头槌|击打|攻击)', time_segment))
    if not has_strike:
        return issues

    checks = {
        '接触面声明': FIGHT_CONTACT,
        '受力方向': FIGHT_FORCE_DIRECTION,
        '受击反应': FIGHT_RECEIVER_REACTION,
    }

    for label, pattern in checks.items():
        if not re.search(pattern, time_segment):
            issues.append({
                'type': 'FIGHT_CHAIN_INCOMPLETE',
                'severity': 'blocking',
                'shot': subshot_id,
                'detail': f'打斗动作缺少{label}'
            })

    return issues


def run(run_dir, mode='full'):
    '''Main entry: run spatial lint checks.

    Returns: (blocking_count, warning_count, info_count, all_issues)
    '''
    plan_path = os.path.join(run_dir, '.cache', 'orchestrator', 'shot_plan.json')
    if not os.path.exists(plan_path):
        plan_path = os.path.join(run_dir, 'shot_plan.draft.json')

    if not os.path.exists(plan_path):
        print(f'[SPATIAL_LINT] ERROR: no shot_plan found')
        return 0, 0, 0, []

    with open(plan_path, 'r', encoding='utf-8-sig') as f:
        sp = json.load(f)

    all_issues = []
    blocking = 0
    warnings = 0
    infos = 0

    # Build flat list of subshots with their spatial data
    subshot_list = []
    for shot in sp.get('shots', []):
        for ss in shot.get('subshots', []):
            subshot_list.append(ss)

    # === D1: Position continuity ===
    if mode in ('full', 'position'):
        for i in range(len(subshot_list) - 1):
            prev = subshot_list[i]
            curr = subshot_list[i + 1]

            prev_chars = _get_characters(prev)
            curr_chars = _get_characters(curr)
            prev_map = prev.get('spatial_map', {})
            curr_map = curr.get('spatial_map', {})

            if not prev_map or not curr_map:
                continue

            issues = _check_position_continuity(prev_map, curr_map, prev_chars, curr_chars)
            for iss in issues:
                iss['prev_shot'] = prev.get('subshot_id', '?')
                iss['curr_shot'] = curr.get('subshot_id', '?')
                if iss['severity'] == 'blocking':
                    blocking += 1
                else:
                    warnings += 1
            all_issues.extend(issues)

    # === D2: Camera-position consistency ===
    if mode in ('full', 'camera'):
        # Load director_pass to get camera movement per subshot
        dp_path = os.path.join(run_dir, '.cache', 'director', 'director_pass.json')
        dp_items = []
        if os.path.exists(dp_path):
            with open(dp_path, 'r', encoding='utf-8-sig') as f:
                dp = json.load(f)
                dp_items = dp.get('items', [])

        dp_by_id = {item.get('subshot_id', ''): item for item in dp_items}

        for ss in subshot_list:
            spatial_map = ss.get('spatial_map', {})
            if not spatial_map:
                continue

            sid = ss.get('subshot_id', '')
            di = dp_by_id.get(sid, {})

            movement = str(di.get('movement_detail', di.get('movement_description', '')))
            mtype = str(di.get('movement_type', ''))

            # Find speaker
            chars = _get_characters(ss)
            speaker = None
            for ch in chars:
                if ch in str(di.get('dialogue_refs', '')):
                    speaker = ch
                    break

            issues = _check_camera_position_consistency(spatial_map, movement + ' ' + mtype, speaker)
            for iss in issues:
                iss['shot'] = sid
                if iss['severity'] == 'blocking':
                    blocking += 1
                else:
                    warnings += 1
            all_issues.extend(issues)

    # === D3: Action trajectory (action/fight scenes only) ===
    if mode in ('full', 'action'):
        action_fight_count = 0
        for ss in subshot_list:
            scene_type = ss.get('scene_type', 'dialogue')
            if scene_type not in ('action', 'fight'):
                continue  # Skip dialogue scenes — no movement trajectory needed
            action_fight_count += 1
            sid = ss.get('subshot_id', '')
            base_action = ss.get('base_action', '')

            issues = _check_action_trajectory(base_action, sid)
            for iss in issues:
                if iss['severity'] == 'blocking':
                    blocking += 1
                else:
                    warnings += 1
            all_issues.extend(issues)

    # === D4: Fight chain (fight scenes only) ===
    if mode in ('full', 'fight'):
        fight_count = 0
        for ss in subshot_list:
            scene_type = ss.get('scene_type', 'dialogue')
            if scene_type != 'fight':
                continue  # Skip non-fight scenes
            fight_count += 1
            sid = ss.get('subshot_id', '')
            base_action = ss.get('base_action', '')

            issues = _check_fight_chain(base_action, sid, scene_type)
            for iss in issues:
                if iss['severity'] == 'blocking':
                    blocking += 1
                else:
                    warnings += 1
            all_issues.extend(issues)

    # Write report
    report_dir = os.path.join(run_dir, '.cache', 'spatial')
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, 'report.json')

    report = {
        'mode': mode,
        'blocking': blocking,
        'warnings': warnings,
        'infos': infos,
        'total_subshots': len(subshot_list),
        'issues': all_issues
    }

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Count by scene type
    dialogue_shots = sum(1 for ss in subshot_list if ss.get('scene_type', 'dialogue') == 'dialogue')
    action_shots = sum(1 for ss in subshot_list if ss.get('scene_type') == 'action')
    fight_shots = sum(1 for ss in subshot_list if ss.get('scene_type') == 'fight')

    print(f'[SPATIAL_LINT] {blocking} blocking, {warnings} warnings, {infos} info')
    print(f'  Scene types: {dialogue_shots} dialogue, {action_shots} action, {fight_shots} fight')
    print(f'  D1+D2: all scenes | D3: action/fight only | D4: fight only')
    print(f'  Report: {report_path}')

    if blocking > 0:
        print(f'  BLOCKING issues (must fix before Phase 6):')
        for iss in all_issues:
            if iss['severity'] == 'blocking':
                print(f'    [{iss["type"]}] {iss.get("detail", iss)}')

    return blocking, warnings, infos, all_issues


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python spatial_lint.py <run_dir> [--mode full|camera|action|fight]')
        sys.exit(2)

    run_dir = sys.argv[1]
    mode = 'full'
    for i, a in enumerate(sys.argv):
        if a == '--mode' and i + 1 < len(sys.argv):
            mode = sys.argv[i + 1]

    b, w, inf, _ = run(run_dir, mode)
    sys.exit(1 if b > 0 else 0)
