
import json, os, re

def generate_dispatch(run_dir):
    sp = json.load(open(run_dir + '/.cache/orchestrator/shot_plan.json', 'r', encoding='utf-8-sig'))
    dm = sp['dialogue_map']
    dispatch_dir = run_dir + '/.cache/dispatch'
    os.makedirs(dispatch_dir, exist_ok=True)

    def full_context(ref_key, shot_desc='', adj_actions=()):
        """Build rich context for emotion analysis including dialogue, scene, and adjacent subshot actions."""
        # Collect dialogue context (existing logic)
        base = ref_key.split('-s')[0] if '-s' in ref_key else ref_key
        children = sorted([k for k in dm if k == base or k.startswith(base + '-s')])
        dia_context = ''
        if len(children) <= 1:
            dia_context = dm.get(ref_key, '')
        else:
            parts = []
            for c in children:
                t = dm.get(c, '')
                if parts and '\uff1a' in t:
                    parts.append(t.split('\uff1a', 1)[-1])
                else:
                    parts.append(t)
            dia_context = ''.join(parts)
        # Build full context
        parts = []
        if shot_desc:
            parts.append(f'[shot] {shot_desc}')
        prev_act, next_act = adj_actions
        if prev_act:
            parts.append(f'[prev] {prev_act}')
        if dia_context:
            parts.append(f'[dia] {dia_context}')
        if next_act:
            parts.append(f'[next] {next_act}')
        return ' | '.join(parts)

    emotion_data, scene_data, camera_data = [], [], []
    for s in sp['shots']:
        for ss in s['subshots']:
            sid = ss['subshot_id']
            chars = ss['characters']
            ba = ss['base_action']
            refs = ss.get('dialogue_refs', [])
            diags, narrs = [], []
            full_ctx = ''
            # Build adjacent subshot actions for context
            subshots = s.get('subshots', [])
            ss_idx = next((i for i, x in enumerate(subshots) if x.get('subshot_id') == sid), -1)
            prev_act = subshots[ss_idx-1].get('base_action', '') if ss_idx > 0 else ''
            next_act = subshots[ss_idx+1].get('base_action', '') if ss_idx >= 0 and ss_idx < len(subshots)-1 else ''
            for ref in refs:
                txt = dm.get(ref, '')
                if '\uff08OS\uff09' in txt or '\uff08\u5185\u5fc3\u72ec\u767d\uff09' in txt:
                    narrs.append({'ref': ref, 'text': txt})
                else:
                    diags.append({'ref': ref, 'text': txt})
                fc = full_context(ref, shot_desc=s.get('description', ''), adj_actions=(prev_act, next_act))
                if len(fc) > len(full_ctx):
                    full_ctx = fc
            acts = [ba] if ba else []
            desc = s.get('description', '')
            dur = ss.get('duration', 0)

            emotion_data.append({
                'id': sid, 'chars': chars, 'acts': acts,
                'diags': diags, 'narrs': narrs,
                'desc': desc, 'dur': dur,
                'full_context': full_ctx if len(full_ctx) > 10 else ''
            })
            scene_data.append({'id': sid, 'chars': chars, 'acts': acts, 'desc': desc, 'emotion_tone': ss.get('emotion_tone', '')})
            camera_data.append({'id': sid, 'chars': chars, 'desc': desc, 'dur': dur, 'acts': acts})

    for name, data in [('emotion_data.json', emotion_data), ('scene_data.json', scene_data), ('camera_data.json', camera_data)]:
        with open(dispatch_dir + '/' + name, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    with_ctx = sum(1 for d in emotion_data if d.get('full_context'))
    print('[DISPATCH] ' + str(len(emotion_data)) + ' emotion, ' + str(len(scene_data)) + ' scene, ' + str(len(camera_data)) + ' camera')
    print('[DISPATCH] full_context injected: ' + str(with_ctx) + '/' + str(len(emotion_data)))
    return emotion_data

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('usage: generate_dispatch.py <run_dir>')
        sys.exit(1)
    generate_dispatch(sys.argv[1])
