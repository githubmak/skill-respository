#!/usr/bin/env python3
import json, re, sys
from pathlib import Path

PAUSE = {'，': .10, '。': .20, '；': .30, '：': .20, '？': .20, '！': .20, '、': .08}
NON_SPEECH = ('环境音', '音效', '呼吸声', '脚步声', '关门声', '衣料摩擦', '水声', '风声', '音乐', 'BGM')

def spoken_parts(text):
    quoted = re.findall(r'[“"]([^”"]+)[”"]', text or '')
    if quoted:
        return quoted
    if any(k in (text or '') for k in NON_SPEECH):
        return []
    spoken = re.sub(r'^.*?[：:]', '', text or '', count=1)
    return [spoken] if spoken else []

def speech_seconds(text, pace='normal'):
    parts = spoken_parts(text)
    if not parts:
        return 0.0
    rate = {'normal': 4.5, 'fast': 5.0, 'slow': 4.0}.get(pace, 4.5)
    total = 0.0
    for spoken in parts:
        chars = len(re.findall(r'[\u4e00-\u9fff]', spoken))
        pauses = sum(PAUSE.get(ch, 0) for ch in spoken)
        pauses += .35 * spoken.count('——')
        pauses += .25 * len(re.findall(r'…+', spoken))
        total += chars / rate + pauses
    if len(parts) > 1:
        total += .25 * (len(parts) - 1)
    return round(total, 1)

def validate(data):
    issues = []
    for shot in data.get('shots', []):
        sid, duration = shot.get('id', '?'), float(shot.get('duration', 0) or 0)
        subs = shot.get('subframes') or []
        if not subs:
            issues.append(f'{sid}: 缺少子镜头/阶段时间窗')
            continue
        ordered = sorted(subs, key=lambda s: float(s.get('time_start', 0) or 0))
        cursor = 0.0
        for sub in ordered:
            start = float(sub.get('time_start', 0) or 0)
            end = float(sub.get('time_end', 0) or 0)
            if abs(start - cursor) > .05:
                issues.append(f'{sid}/{sub.get("id")}: 时间窗不连续，期望{cursor:.1f}，实际{start:.1f}')
            if end <= start:
                issues.append(f'{sid}/{sub.get("id")}: 结束时间必须大于开始时间')
            window = max(0, end - start)
            pace = sub.get('speech_pace', 'slow' if 'OS' in str(sub.get('dialogue', '')) else 'normal')
            spoken = speech_seconds(str(sub.get('dialogue', '')), pace)
            padding = float(sub.get('performance_padding', .5) or 0)
            if spoken and spoken + padding > window + .05:
                issues.append(f'{sid}/{sub.get("id")}: 口播{spoken:.1f}s+余量{padding:.1f}s > 时间窗{window:.1f}s')
            cursor = end
        if abs(cursor - duration) > .05:
            issues.append(f'{sid}: 子镜头结束{cursor:.1f}s != 主镜头时长{duration:.1f}s')
    return issues

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: validate_timing.py analysis.json')
    data = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'))
    problems = validate(data)
    if problems:
        print('\n'.join(problems))
        raise SystemExit(1)
    print('Timing validation passed.')
