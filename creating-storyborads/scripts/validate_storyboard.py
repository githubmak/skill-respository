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
MANUAL = [
    '人工从源稿核对所有发言提取覆盖、说话者/OS/OV归属及非对白关键事实。',
    '人工核对源稿外的重复引语、自然语气与时长、信息到达、取景可见性、物理空间及跨镜状态。',
    '人工评估题材收益、人物专属性、观看节奏、情绪/喜剧兑现及配乐与表演关系。',
    '连续音轨的完整覆盖、口型/后期接续与局部混合配乐边界须人工核对。',
    '未执行动态预演、视频/声音生成和实际混音，不证明成片、无缝或S+爆款。',
]


def dec(s):
    return Decimal(str(s))


def validate(markdown, source_bytes, ledger):
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
    unit_ids, seen_shots, occurrences = [], [], []
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
            sound = re.search(r'^\s*声音[：:]\s*(\S[^\n]*)',block,re.M)
            music = re.search(r'^\s*配乐[：:]\s*(\S[^\n]*)',block,re.M)
            picture = re.split(r'^\s*(?:声音|配乐)[：:]',block,maxsplit=1,flags=re.M)[0]
            if not picture.strip():
                fail('picture_empty',where,'时间窗只有标题，缺少可执行画面。')
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
        # Public dialogue remains natural prose. Optional split allocations live only
        # in the internal ledger; never impose ids or JSON strings on the manuscript.
        allocations = ledger.get('delivery', [])
        targets = [x for x in allocations if x.get('unit') == uid] if allocations else [
            dict(id=k, text=u['text']) for k,u in expected.items() if u['text'] in voice_text]
        located = []
        for item in targets:
            vid, text = item.get('id'), item.get('text')
            if vid not in expected or not isinstance(text,str) or not text:
                fail('delivery_index',uid,'内部台词分配索引无效。')
                continue
            positions = [x.start() for x in re.finditer(re.escape(text),voice_text)]
            if len(positions) != 1:
                fail('dialogue_exact',uid+'/'+vid,'声音栏台词片段缺失或重复；有同句重复时需人工核对归属。')
            for at in positions:
                located.append((at,vid,text))
        occurrences.extend((vid,text) for at,vid,text in sorted(located))
    if len(unit_ids)!=len(set(unit_ids)):
        fail('unit_duplicate','document','生成单元编号重复。')
    for uid in overrides:
        if uid not in unit_ids:
            fail('music_scope',uid,'配乐覆盖指向不存在的单元。')
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
        fail('global_format','document','全局栏目名称、顺序须严格遵循所选原文模板。')
    if not re.match(r'^# 《.+》Seedance 独立直投版\s*$',markdown.splitlines()[0]):
        fail('title_format','document','作品标题须遵循原文模板。')
    if any_music:
        for label in ('配音基线','配乐主题','乐器与音色分工','声层与接续原则'):
            if not re.search(r'^- '+label+r'：\s*\S',header,re.M):
                fail('global_sound','document','全局声音规则缺少'+label+'。')
    scene_names = re.findall(r'^## (.+)$',template.split('# 场景',1)[1],re.M)
    scenes = list(re.finditer(r'^# 场景[^\n]*',markdown,re.M))
    if not scenes:
        fail('scene_format','document','缺少场景标题和场景栏目。')
    for i,scene in enumerate(scenes):
        body=markdown[scene.end():scenes[i+1].start() if i+1<len(scenes) else len(markdown)]
        if re.findall(r'^## (.+)$',body,re.M) != scene_names:
            fail('scene_format',scene.group(),'场景栏目名称或顺序与原文模板不一致。')
        for label in ('拓扑共识','正向提示词','负向约束'):
            if not re.search(r'^- '+label+r'：\s*\S',body,re.M):
                fail('scene_assets',scene.group(),'场景资产缺少'+label+'。')
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
        if args.report and args.report.resolve() in inputs:
            raise ValueError('report path must not overwrite an input')
        report=validate(args.markdown.read_bytes().decode('utf-8'),args.source.read_bytes(),json.loads(args.ledger.read_bytes()))
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
