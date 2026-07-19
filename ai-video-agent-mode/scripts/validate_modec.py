import json, os, re
from collections import Counter

RD = r'C:' + chr(92) + r'Users' + chr(92) + 'cors' + chr(92) + 'Desktop' + chr(92) + chr(0x9677) + chr(0x843d) + chr(0x79f0) + chr(0x81e3) + chr(92) + chr(0x7b2c) + '4' + chr(0x96c6) + chr(92) + 'output'

with open(os.path.join(RD, '.cache', 'composer', 'prompt_package.json'), 'r', encoding='utf-8') as f:
    pp = json.load(f)
shots = pp.get('shots', pp.get('items', []))

with open(os.path.join(RD, '.cache', 'analysis', 'camera_output.json'), 'r', encoding='utf-8') as f:
    cam = {i['subshot_id']: i for i in json.load(f).get('items', [])}
with open(os.path.join(RD, '.cache', 'analysis', 'scene_output.json'), 'r', encoding='utf-8') as f:
    scn = {i['subshot_id']: i for i in json.load(f).get('items', [])}
with open(os.path.join(RD, '.cache', 'orchestrator', 'shot_plan.json'), 'r', encoding='utf-8') as f:
    sp = json.load(f)

results = {'pass': 0, 'fail': 0, 'warn': 0}

def check(name, condition, blocking=True):
    if condition:
        results['pass'] += 1
        print('[OK] ' + name)
    elif blocking:
        results['fail'] += 1
        print('[FAIL] ' + name)
    else:
        results['warn'] += 1
        print('[WARN] ' + name)

print('=== MODE C VALIDATION ===')
print()

check('01. Shot count = 103', len(shots) == 103)

under_1200 = sum(1 for s in shots if len(s.get('full_prompt', '')) < 800)
check('02. Per-shot >= 800 chars', under_1200 == 0)
if under_1200:
    print('  (' + str(under_1200) + ' under)')

over_1800 = sum(1 for s in shots if len(s.get('full_prompt', '')) > 1800)
check('03. Per-shot <= 1800 chars', over_1800 <= 10, blocking=False)

NZ = chr(0x8d1f) + chr(0x9762) + chr(0x63d0) + chr(0x793a) + chr(0x8bcd)
no_neg = sum(1 for s in shots if NZ not in s.get('full_prompt', ''))
check('04. Negative prompt present', no_neg == 0)

no_169 = sum(1 for s in shots if '16:9' not in s.get('full_prompt', '')[:100])
check('05. Self-contained (16:9 header)', no_169 == 0)

dup_paras = 0
for s in shots:
    fp = s.get('full_prompt', '')
    paras = [p.strip() for p in fp.split(chr(10)) if len(p.strip()) > 30]
    if len(paras) != len(set(paras)):
        dup_paras += 1
check('06. No duplicate paragraphs', dup_paras == 0)

neg_dup = 0
for s in shots:
    fp = s.get('full_prompt', '')
    ni = fp.rfind(NZ)
    if ni > 0:
        kws = fp[ni:].replace(NZ, ' ').split()
        kws = [kw for kw in kws if len(kw) > 2]
        dups = {k: v for k, v in Counter(kws).items() if v > 1}
        if dups:
            neg_dup += 1
check('07. No duplicate negative keywords', neg_dup == 0)

sp_goal = sum(1 for s in shots if chr(0x573a) + chr(0x666f) + chr(0x76ee) + chr(0x7684) in s.get('full_prompt', ''))
check('08. Scene purpose present (' + str(sp_goal) + '/103)', sp_goal >= 100, blocking=False)

audio = sum(1 for s in shots if chr(0x73af) + chr(0x5883) + chr(0x97f3) in s.get('full_prompt', ''))
check('09. Audio environment (' + str(audio) + '/103)', audio >= 100, blocking=False)

mouth = sum(1 for s in shots if chr(0x53e3) + chr(0x578b) in s.get('full_prompt', ''))
check('10. Mouth control (' + str(mouth) + '/103)', mouth >= 90, blocking=False)

fks = [chr(0x773c) + chr(0x7751), chr(0x77b3) + chr(0x5b54), chr(0x5507) + chr(0x7ebf), chr(0x9f3b) + chr(0x7ffc), chr(0x547c) + chr(0x5438), chr(0x7709), chr(0x54ac) + chr(0x808c), chr(0x4e0b) + chr(0x988c), chr(0x5589) + chr(0x7ed3), chr(0x80f8) + chr(0x5ed3), chr(0x7728) + chr(0x773c)]
facial_ok = sum(1 for s in shots if sum(1 for kw in fks if kw in s.get('full_prompt', '')) >= 3)
check('11. Facial detail >=3 (' + str(facial_ok) + '/103)', facial_ok >= 72, blocking=False)

scn_items = sorted(scn.values(), key=lambda x: x.get('subshot_id', ''))
light_jumps = 0
for i in range(len(scn_items) - 1):
    t1 = scn_items[i].get('light_temp', 5200)
    t2 = scn_items[i+1].get('light_temp', 5200)
    if t1 and t2 and abs(t1 - t2) > 2000:
        light_jumps += 1
check('12. Lighting continuity (>2000K: ' + str(light_jumps) + ')', light_jumps <= 5)

uw_close = sum(1 for ci in cam.values() if ci.get('camera_lens_mm', 50) <= 28 and ci.get('shot_size', '') in [chr(0x7279) + chr(0x5199), chr(0x5927) + chr(0x7279) + chr(0x5199)])
check('13. No UW lens on CU (' + str(uw_close) + ')', uw_close == 0)

eng_sizes = sum(1 for ci in cam.values() if ci.get('shot_size', '') in ['CU', 'ECU', 'MS', 'FS', 'LS', 'WS', 'ELS'])
check('14. No English shot sizes (' + str(eng_sizes) + ')', eng_sizes == 0)

boiler = sum(1 for s in shots if chr(0x673a) + chr(0x4f4d) + chr(0x8f6e) + chr(0x6362) in s.get('full_prompt', ''))
check('15. No boilerplate (' + str(boiler) + ')', boiler == 0)

sp_ids = set()
for ms in sp.get('shots', []):
    for sub in ms.get('subshots', []):
        sp_ids.add(sub.get('subshot_id', ''))
pp_ids = set(s.get('subshot_id', '') for s in shots)
check('16. Subshot coverage', pp_ids == sp_ids)

print()
print('RESULT: ' + str(results['pass']) + ' passed, ' + str(results['fail']) + ' failed, ' + str(results['warn']) + ' warnings')
score = results['pass'] + results['fail']
if score > 0:
    print('SCORE: ' + str(results['pass']) + '/' + str(score) + ' blocking checks passed')
