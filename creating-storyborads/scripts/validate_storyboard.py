#!/usr/bin/env python3
"""Read-only static checks for the creating-storyborads delivery contract.

No model, network or dependencies. Exit 0 static pass, 1 violations, 2 input error.
Source utterance extraction/attribution and artistic/physical quality need review.
"""
import argparse
from collections import defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys

NUM = r'\d+(?:\.\d+)?'
RANGE = rf'({NUM})\s*(?:秒\s*)?[—–~～-]\s*({NUM})\s*秒'
UNIT = re.compile(rf'^###\s+生成单元\s+(G\d+)\s*｜\s*时长[：:]\s*({NUM})\s*秒\s*｜\s*承载[：:]([^\n]+)', re.M)
WINDOW = re.compile(rf'^\s*{RANGE}\s*｜\s*(?:镜头\s*)?(S\d+-\d+)\s*｜([^\n]+)', re.M)
FIELDS = ['起幅与连续性','摄影与构图','光影、环境色彩与材质','画面与表演时间线','台词与声音层次','落幅状态']
FIELD = re.compile(r'^\s*-\s*('+'|'.join(FIELDS+['本生成单元特殊正向约束','本生成单元特殊负面约束'])+r')[：:]\s*', re.M)
LENS = re.compile(rf'({NUM})\s*(?:mm|毫米)', re.I)
MOVEMENTS = re.compile(r"固定|静止|推|拉|移|跟拍|跟随|环绕|短弧|升降|升机|降机|后退|前移|摇|俯仰|甩|穿越|变焦|手持|轨道|航拍|锁定|急停")
MANUAL = [
    '人工从源稿核对所有发言提取覆盖、说话者/OS/OV归属及非对白关键事实。',
    '人工核对源稿外的重复引语、自然语气与时长、信息到达、取景可见性、物理空间及跨镜状态。',
    '人工评估题材收益、人物专属性、观看节奏、情绪/喜剧兑现及配乐与表演关系。',
    '连续音轨的完整覆盖、口型/后期接续与局部混合配乐边界须人工核对。',
    '人工核对本场摄影/光色没有混入其他房间条件，参考图指代确为生成端已提供素材；结构检查不能证明其语义正确。',
    '未执行动态预演、视频/声音生成和实际混音，不证明成片、无缝或S+爆款。',
]


def dec(s):
    return Decimal(str(s))


QUOTES = {'“':'”', '「':'」', '『':'』', '"':'"'}
NOTE_LABELS = {'说明','演绎说明','读法','语气','口型','停连','备注','提示','注意','声音','配乐'}


def quoted_end(line, start):
    """Find the closing quote, respecting nested Chinese quotes and escapes."""
    stack = [QUOTES[line[start]]]
    at = start + 1
    while at < len(line):
        char = line[at]
        if char == '\\':
            at += 2
            continue
        if char == stack[-1]:
            stack.pop()
            if not stack:
                return at + 1
        elif char in QUOTES:
            stack.append(QUOTES[char])
        at += 1
    return None


def attributed_header(prefix, speakers):
    prefix = re.sub(r'^[ \t]*[-*][ \t]+', '', prefix).strip()
    prefix = re.sub(rf'^{RANGE}[ \t]*｜[ \t]*', '', prefix)
    for speaker in sorted(set(speakers), key=len, reverse=True):
        if prefix.startswith(speaker):
            meta = prefix[len(speaker):]
            if not meta or meta[0] in ' \t（(在' or re.match(r'对白|OS|OV|旁白|说',meta,re.I):
                return speaker, meta
    match = re.fullmatch(
        rf'(?P<speaker>[\w·]+?)(?P<meta>[ \t]*(?:(?:对白|OS|OV|旁白|说)'
        rf'(?=[ \t（(]|$)|在(?=\d)|[（(]).*)', prefix, re.I)
    if match:
        return match['speaker'], match['meta']
    if re.fullmatch(r'[\w·]+', prefix):
        return prefix, ''
    return None


def voice_records(text, speakers, issues=None):
    """Parse top-level attributions, not colons/quotes inside notes or speech.

    Quoted records may share a line. Unquoted prose remains line-scoped;
    ambiguous attributions are reported for human review, never guessed.
    """
    records = []
    for number, line in enumerate(text.splitlines(), 1):
        at, segment, brackets = 0, 0, []
        while at < len(line):
            char = line[at]
            if char in '（(':
                brackets.append(char)
            elif char in '）)' and brackets:
                brackets.pop()
            elif not brackets and char in QUOTES:
                # Unattributed quotations in performance notes are not dialogue.
                at = quoted_end(line, at) or len(line)
                continue
            elif not brackets and char in '；;。！？!?｜':
                # A timestamp prefix contains ｜; keep it until its first colon.
                if char != '｜' or not re.match(rf'^[ \t]*{RANGE}',line[segment:at]):
                    segment = at + 1
            elif not brackets and char in '：:':
                prefix = line[segment:at].strip()
                header = attributed_header(prefix, speakers)
                value = at + 1
                while value < len(line) and line[value] in ' \t':
                    value += 1
                if prefix in NOTE_LABELS and prefix not in speakers:
                    break
                if header is None:
                    if value < len(line) and line[value] in QUOTES and issues is not None:
                        issues.append((number,'引语前归属无法可靠解析，需人工核对。'))
                    segment = at + 1
                    at += 1
                    continue
                speaker, meta = header
                if value < len(line) and line[value] in QUOTES:
                    end = quoted_end(line, value)
                    if end is None:
                        if issues is not None:
                            issues.append((number,'话语引号未闭合，需人工核对。'))
                        break
                    words = line[value+1:end-1]
                else:
                    # A bare unknown label followed by prose could be a note.
                    if speaker not in speakers and not meta.strip():
                        if issues is not None:
                            issues.append((number,'未标类型的非来源名称与未加引号正文，需人工确认是否发言。'))
                        break
                    end = len(line)
                    words = line[value:end].strip()
                kind = ('OS' if re.search(r'(?<![A-Za-z])OS(?![A-Za-z])|内心独白',meta,re.I) else
                        'OV' if re.search(r'(?<![A-Za-z])OV(?![A-Za-z])',meta,re.I) else
                        '旁白' if '旁白' in meta or speaker == '旁白' else '对白')
                records.append(dict(speaker=speaker,kind=kind,text=words,raw_text=line[value:end].strip()))
                at, segment = end, end
                continue
            at += 1
        if brackets and issues is not None:
            issues.append((number,'括号未闭合，话语归属可能未解析，需人工核对。'))
    return records


def validate(markdown, source_bytes, ledger):
    # Normalize presentation newlines only; source bytes/offsets stay untouched.
    markdown = markdown.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n')
    errors, notes = [], []
    def fail(code, where, message):
        errors.append({'code':code, 'where':where, 'message':message})
    if not isinstance(ledger, dict) or ledger.get('version') != 1:
        raise ValueError('ledger.version must be 1')
    if type(ledger.get('music')) is not bool:
        raise ValueError('ledger.music must be boolean')
    overrides = ledger.get('unit_music', {})
    if not isinstance(overrides, dict) or any(type(v) is not bool for v in overrides.values()):
        raise ValueError('unit_music must map unit ids to booleans')
    limit = dec(ledger.get('max_unit_seconds', 35))
    if not limit.is_finite() or limit <= 0:
        raise ValueError('max_unit_seconds must be positive and finite')
    source = source_bytes.decode('utf-8')
    if hashlib.sha256(source_bytes).hexdigest() != ledger.get('source_sha256'):
        fail('source_hash','source','来源快照哈希不一致；确认工作稿版本，不以修改索引迁就成稿。')
    utterances = ledger.get('utterances')
    if not isinstance(utterances, list):
        raise ValueError('utterances must be a list (empty for a silent source)')
    expected, last_end = {}, -1
    for u in utterances:
        if not isinstance(u,dict):
            raise ValueError('each utterance must be an object')
        uid = u.get('id','')
        if not isinstance(uid,str) or not re.fullmatch(r'U\d+',uid) or uid in expected:
            raise ValueError('utterance ids must be unique U<number>')
        if not isinstance(u.get('speaker'),str) or not u['speaker'].strip() or u.get('kind') not in ('对白','OS','OV','旁白'):
            raise ValueError(uid+': missing speaker or invalid kind')
        start, end = u.get('source_start'), u.get('source_end')
        if type(start) is not int or type(end) is not int or not isinstance(u.get('text'),str) or not u['text']:
            raise ValueError(uid+': nonempty text and integer source offsets required')
        if not 0 <= start < end <= len(source) or source[start:end] != u['text']:
            fail('source_span',uid,'台词与源稿字符区间不一致。')
        if start < last_end:
            fail('source_order',uid,'来源区间重叠或逆序。')
        last_end = end
        expected[uid] = u
    matches = list(UNIT.finditer(markdown))
    if not matches:
        fail('no_units','document','未识别到生成单元，不能报告静态通过。')
    raw_unit_headers = re.findall(r'^###\s+生成单元[^\n]*',markdown,re.M)
    if len(raw_unit_headers) != len(matches):
        fail('unit_syntax','document','存在无法解析的生成单元标题。')
    allocations = ledger.get('delivery', [])
    if not isinstance(allocations, list):
        raise ValueError('delivery must be a list')
    for item in allocations:
        if (not isinstance(item, dict) or item.get('id') not in expected or
                not isinstance(item.get('unit'), str) or
                not isinstance(item.get('text'), str) or not item['text']):
            raise ValueError('invalid delivery allocation')
    allocated_ids = {item['id'] for item in allocations}
    unit_ids, seen_shots, occurrences = [], [], []
    consumed = set()
    focal_end, last_shot = {}, None
    total = Decimal(0)
    for i,m in enumerate(matches):
        uid, duration = m[1], dec(m[2])
        unit_ids.append(uid)
        if i and int(uid[1:]) <= int(unit_ids[i-1][1:]):
            fail('unit_order',uid,'G编号须唯一递增。')
        total += duration
        if duration <= 0 or duration > limit:
            fail('unit_duration',uid,'时长必须为正且不超过有效单元上限。')
        end = matches[i+1].start() if i+1 < len(matches) else len(markdown)
        next_scene = re.search(r'^# 场景[^\n]*', markdown[m.end():end], re.M)
        if next_scene:
            end = m.end() + next_scene.start()
        body = markdown[m.end():end]
        fs = list(FIELD.finditer(body))
        fields = {}
        names = []
        for n,f in enumerate(fs):
            name = f[1]
            content = body[f.end():fs[n+1].start() if n+1 < len(fs) else len(body)]
            if name in fields:
                fail('field_duplicate',uid,name+'重复。')
            fields[name] = content
            if name in FIELDS:
                names.append(name)
                if not content.strip():
                    fail('field_empty',uid,name+'为空。')
        if names != FIELDS:
            fail('fields',uid,'必需栏目缺失或顺序错误。')
        timeline = fields.get('画面与表演时间线','')
        windows = list(WINDOW.finditer(timeline))
        if not windows:
            fail('no_windows',uid,'时间线缺少可解析时间窗。')
        # Every apparent timeline line must parse; malformed lines cannot be ignored.
        apparent = re.findall(r'^\s*\d[^\n]*｜[^\n]*',timeline,re.M)
        if len(apparent) != len(windows):
            fail('window_syntax',uid,'存在无法解析的时间窗。')
        clock, unit_shots = Decimal(0), []
        music_on = overrides.get(uid,ledger['music'])
        for wi,w in enumerate(windows):
            a,b,shot,details = dec(w[1]),dec(w[2]),w[3],w[4]
            where = uid+'/'+shot+'/'+str(a)
            if a != clock or b <= a:
                fail('time_coverage',where,'时间窗须首尾相接且正向，不能空档/重叠。')
            clock = b
            if b > duration:
                fail('window_bounds',where,'时间窗超出单元。')
            if last_shot != shot:
                if shot in seen_shots:
                    fail('shot_reentry',where,'已结束镜号重新出现；明确剪切应使用新镜号。')
                seen_shots.append(shot)
            last_shot = shot
            if shot not in unit_shots:
                unit_shots.append(shot)
            lenses = [dec(x) for x in LENS.findall(details)]
            if not lenses or any(x <= 0 for x in lenses):
                fail('lens',where,'缺少正数mm/毫米焦段。')
            else:
                zoom = '变焦' in details
                if len(lenses)>1 and not zoom:
                    fail('zoom',where,'多个焦段必须明确连续变焦；剪切另编镜号。')
                if zoom and len(lenses)<2:
                    fail('zoom_range',where,'连续变焦须明确起止焦段。')
                if shot in focal_end and focal_end[shot] != lenses[0]:
                    fail('lens_continuity',where,'同一镜头的焦段接点漂移。')
                focal_end[shot] = lenses[-1]
            if not any(s in details for s in ('大远景','远景','全景','中全景','中景','中近景','近景','特写')):
                fail('shot_size',where,'焦段之后须同时指定景别。')
            block=timeline[w.end():windows[wi+1].start() if wi+1<len(windows) else len(timeline)]
            sound = re.search(r'^[ \t]*声音[：:][ \t]*(\S[^\n]*)',block,re.M)
            music = re.search(r'^[ \t]*配乐[：:][ \t]*(\S[^\n]*)',block,re.M)
            picture = re.split(r'^\s*(?:声音|配乐)[：:]',block,maxsplit=1,flags=re.M)[0]
            if not picture.strip():
                fail('picture_empty',where,'时间窗只有标题，缺少可执行画面。')
            camera_parts = re.split(r'[｜|]', details, maxsplit=1)
            camera_text = camera_parts[1] if len(camera_parts) > 1 else ''
            camera_lines = re.findall(r'(?:摄影机|摄像机|镜头)(?:[^。\n]*)(?:固定|静止|推进|推近|拉远|后退|横移|侧移|跟拍|环绕|摇摄|升降)[^。\n]*', picture)
            if not MOVEMENTS.search(camera_text + ' '.join(camera_lines)):
                fail('camera_mode',where,'须明确运镜或固定方式；剪切与人物推拉动作不能代替摄影说明。')
            if not sound:
                fail('sound',where,'缺少实际声音/有因静默说明。')
            if music_on and not music:
                fail('music_missing',where,'开启范围缺少配乐状态/有因静默。')
            if not music_on and re.search(r'^\s*配乐[：:]',block,re.M):
                fail('music_disabled',where,'关闭范围仍输出逐窗背景配乐。')
        if windows and clock != duration:
            fail('timeline_end',uid,'时间线末点不等于标题时长。')
        mapped = list(dict.fromkeys(re.findall(r'S\d+-\d+',m[3].split('｜')[0])))
        if mapped != unit_shots:
            fail('shot_mapping',uid,'标题承载镜号与时间线镜号或顺序不一致。')
        voice_text = fields.get('台词与声音层次','')
        # Match complete attributed records once, in their actual delivery order.
        # A lone "？" cannot match a question mark inside a longer utterance.
        targets = ([x for x in allocations if x['unit'] == uid] +
                   [dict(id=k, text=u['text']) for k,u in expected.items()
                    if k not in allocated_ids and k not in consumed])
        used = set()
        voice_issues = []
        for record in voice_records(voice_text, [u['speaker'] for u in expected.values()], voice_issues):
            candidates = [n for n,item in enumerate(targets) if n not in used and
                          item['text'] in (record['raw_text'], record['text']) and
                          record['speaker'] == expected[item['id']]['speaker'] and
                          record['kind'] == expected[item['id']]['kind']]
            if not candidates:
                fail('dialogue_exact',uid,'存在未匹配的完整话语、重复发言、改字或说话人/OS归属不符。')
                continue
            at = candidates[0]
            used.add(at)
            item = targets[at]
            consumed.add(item['id'])
            occurrences.append((item['id'], item['text']))
        for line_number, message in voice_issues:
            notes.append({'code':'voice_parse_manual','where':f'{uid}/声音栏第{line_number}行',
                          'message':message})
        if allocations:
            for at,item in enumerate(targets):
                if item.get('unit') == uid and at not in used:
                    fail('dialogue_exact',uid+'/'+item['id'],'该次完整话语或原文片段未出现，或归属不符。')
    if len(unit_ids)!=len(set(unit_ids)):
        fail('unit_duplicate','document','生成单元编号重复。')
    for uid in overrides:
        if uid not in unit_ids:
            fail('music_scope',uid,'配乐覆盖指向不存在的单元。')
    for item in allocations:
        if item['unit'] not in unit_ids:
            fail('delivery_index',item['unit'],'台词分配指向不存在的生成单元。')
    groups, order = defaultdict(list), []
    for vid,text in occurrences:
        groups[vid].append(text)
        if not order or order[-1]!=vid:
            order.append(vid)
    if order != list(expected):
        fail('utterance_order','document','话语发生顺序/覆盖不一致，或被非连续重复生成。')
    for vid,u in expected.items():
        if ''.join(groups[vid]) != u['text']:
            fail('dialogue_exact',vid,'分配片段拼接不等于来源原文，存在漏字、改写或重复。')
    values={'成片总时长':total,'生成单元数':len(matches),'成片镜头数':len(set(seen_shots)),'生成单元时长上限':limit}
    header=markdown.split('# 场景',1)[0]
    for key,value in values.items():
        vals=re.findall(rf'{key}[：:]\s*({NUM})',header)
        if len(vals)!=1 or dec(vals[0])!=value:
            fail('statistics',key,'项目统计缺失、重复或与正文/配置不一致。')
    any_music=any(overrides.get(uid,ledger['music']) for uid in unit_ids)
    contract = Path(__file__).resolve().parent.parent/'references'/('output-music.md' if any_music else 'output-detail.md')
    template = contract.read_text(encoding='utf-8').split('```')[1]
    global_names = re.findall(r'^## (.+)$', template.split('# 场景',1)[0],re.M)
    actual = re.findall(r'^## (.+)$',header,re.M)
    if actual != global_names:
        fail('global_format','document','项目共用栏目名称、顺序须遵循当前输出合同。')
    global_sections = list(re.finditer(r'^## (.+)$', header, re.M))
    for i, section in enumerate(global_sections):
        end = global_sections[i+1].start() if i+1 < len(global_sections) else len(header)
        if not header[section.end():end].strip():
            fail('global_empty',section[1],'全局栏目为空。')
    first_line = markdown.splitlines()[0] if markdown.splitlines() else ''
    if not re.match(r'^# 《.+》Seedance 独立直投版\s*$',first_line):
        fail('title_format','document','作品标题须遵循当前输出合同。')
    if any_music:
        for label in ('配音基线','配乐主题','乐器与音色分工','声层与接续原则'):
            if not re.search(r'^- '+label+r'：[ \t]*\S',header,re.M):
                fail('global_sound','document','全局声音规则缺少'+label+'。')
    scene_names = re.findall(r'^## (.+)$',template.split('# 场景',1)[1],re.M)
    scenes = list(re.finditer(r'^# 场景[^\n]*',markdown,re.M))
    if not scenes:
        fail('scene_format','document','缺少场景标题和场景栏目。')
    established_scenes = set()
    for i,scene in enumerate(scenes):
        body=markdown[scene.end():scenes[i+1].start() if i+1<len(scenes) else len(markdown)]
        if re.findall(r'^## (.+)$',body,re.M) != scene_names:
            fail('scene_format',scene.group(),'场景栏目名称或顺序与当前输出合同不一致；每场须有“场景摄影规则”和“场景光色与影调基线”。')
        sections = list(re.finditer(r'^## (.+)$', body, re.M))
        contents = {}
        for si, section in enumerate(sections):
            end = sections[si+1].start() if si+1 < len(sections) else len(body)
            content = body[section.end():end]
            contents[section[1]] = content
            if not content.strip():
                fail('scene_empty',scene.group()+'/'+section[1],'场景栏目为空。')
        if not UNIT.search(body):
            fail('scene_units',scene.group(),'场景没有生成单元。')
        asset_name = next((name for name in scene_names if name.startswith('场景资产图提示词')), '')
        asset = contents.get(asset_name, '')
        identity = scene.group().split('｜', 1)[-1].rsplit('·', 1)[0].strip()
        reused = identity in established_scenes
        explicit_reuse = '复用' in asset and i > 0
        missing = [label for label in ('拓扑共识','正向提示词','负向约束')
                   if not re.search(r'^- '+label+r'：[ \t]*\S',asset,re.M)]
        if missing and not (reused or explicit_reuse):
            for label in missing:
                fail('scene_assets',scene.group(),'首次场景资产缺少'+label+'。')
        elif missing and explicit_reuse and not reused:
            notes.append({'code':'scene_reuse_manual','where':scene.group(),
                          'message':'复用名称不同；人工确认引用的是此前已建立资产，变化说明完整。'})
        established_scenes.add(identity)
    return {'static_pass':not errors,'errors':errors,'notes':notes,'counts':{'units':len(matches),'shots':len(set(seen_shots)),'seconds':str(total),'source_utterances':len(expected)},'manual_required':MANUAL}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('markdown',type=Path)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--ledger',required=True,type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    try:
        inputs=[args.markdown.resolve(),args.source.resolve(),args.ledger.resolve()]
        if args.report:
            if args.report.resolve() in inputs or (args.report.exists() and
                    any(args.report.samefile(path) for path in inputs)):
                raise ValueError('report path must not overwrite an input (including hard links)')
        # Read once: validation and fingerprints must describe the same bytes.
        snapshots = {name: path.read_bytes() for name, path in
                     [('markdown', args.markdown), ('source', args.source), ('ledger', args.ledger)]}
        report=validate(snapshots['markdown'].decode('utf-8'),snapshots['source'],json.loads(snapshots['ledger']))
        report['input_sha256'] = {name: hashlib.sha256(data).hexdigest()
                                  for name, data in snapshots.items()}
        result=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
        if args.report:
            args.report.parent.mkdir(parents=True,exist_ok=True)
            args.report.write_text(result,encoding='utf-8')
        print(result,end='')
        return 0 if report['static_pass'] else 1
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
        print(json.dumps({'input_error':str(exc)},ensure_ascii=False),file=sys.stderr)
        return 2

if __name__=='__main__':
    sys.exit(main())
