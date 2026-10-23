#!/usr/bin/env python3
"""Structural checks for four-genre A/B storyboards; semantic review remains required."""
from __future__ import annotations
import argparse
import re
import subprocess
import sys
from pathlib import Path

LIMIT = 35.0
HEADER = re.compile(r'^\s*(?:#{1,6}\s*)?【?镜头\s*(\d+)\s*[｜|]([^\n]+)', re.M)
UNIT = re.compile(r'^\s*#{1,6}\s*生成单元\s+(G\d+)\s*[｜|]([^\n]+)',re.M)
ENGINE = re.compile(r'^\s*#{1,6}\s*工程镜头\s+(E\d+)\s*[｜|]([^\n]+)',re.M)
TIME = re.compile(r'(?<![\d.])([+-]?\d+(?:\.\d+)?)\s*(?:秒|s)(?!\w)',re.I)

def duration(text):
    m=TIME.search(text)
    return float(m[1]) if m else None

def sections(text,pattern):
    matches=list(pattern.finditer(text))
    return [(m,text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)]) for i,m in enumerate(matches)]

def clean(text):
    return re.sub(r'[*_`>【】\[\]]','',text)

def ids(text,prefix=''):
    return [f'{prefix}{int(n):02d}' for n in re.findall(r'(?<!\d)(?:'+prefix+r')?(\d+)(?!\d)',text)]

def field(body,label):
    m=re.search(r'(?m)^\s*'+re.escape(label)+r'[^：:\n]*[：:][^\S\n]*(.*)',clean(body))
    if not m:return ''
    rest=clean(body)[m.end():]
    stop=re.search(r'(?m)^\s*(?:#{1,6}\s|[^\n：:]{1,25}[：:])',rest)
    return (m[1]+'\n'+(rest[:stop.start()] if stop else rest)).strip()

def check_duration(value,label,errors,cap):
    if value is None or value<=0:errors.append(f'{label}缺少有效时长（使用秒或 s）。')
    elif value>cap+1e-6:errors.append(f'{label}时长 {value:g} 秒超过 {cap:g} 秒上限。')

A_FIELDS_BY_GENRE = {
    'eastern': [('机位&景别&运镜',), ('人物调度与专属身法/战术设计',), ('招式与奇观意象',), ('动作结果与反馈',), ('人物表演细节',), ('情绪锚点', '情绪锚点方法论'), ('画面完整描述',)],
}
for _genre in ('wuxia', 'scifi', 'western'):
    A_FIELDS_BY_GENRE[_genre] = [('机位、景别与运镜',), ('人物调度与专属打法',), ('招式与视觉母题',), ('动作结果与反馈',), ('人物表演细节',), ('情绪锚点',), ('画面完整描述',)]
B_FIELDS_BY_GENRE = {}
for _genre, _mechanism in [('eastern', '仙侠招式/真元特征'), ('wuxia', '武学与兵器特征'), ('scifi', '异能/科技机制'), ('western', '法术/武器机制')]:
    _eastern = _genre == 'eastern'
    B_FIELDS_BY_GENRE[_genre] = [
        ('人物面向与轴线',), ('道具归属与状态',), ('预动作微细节',),
        ('三段体态参考｜起始体态-中段过渡体态-落幅结束体态',) if _eastern else ('三段体态｜起始—过渡—落幅',),
        ('运镜',), ('镜头变速与动态模糊强度',) if _eastern else ('速度与动态模糊',),
        ('画面动作',), ('标准化特效层级',) if _eastern else ('视觉与环境层级',),
        (_mechanism,), ('粒子分级说明',) if _eastern else ('碎屑/粒子说明',),
        ('特效景深分层说明',) if _eastern else ('景深与遮挡',),
        ('物理打击反馈',), ('光影色彩',), ('音效参考',) if _eastern else ('声音参考',),
    ]

def normalized_label(label):
    return re.sub(r'\s+', '', clean(label)).replace('‑', '-').replace('－', '-')

def has_engineering_field(body, variants):
    # Stop before packages/footer: a field in another section cannot fill this shot.
    body = re.split(r'(?m)^\s*#{1,6}\s*(?:生成单元|工程校验|第\s*(?:1\.5|2|3)\s*部分)', body)[0]
    lines = clean(body).splitlines()
    wanted = {normalized_label(v) for v in variants}
    for i, line in enumerate(lines):
        match = re.match(r'^\s*([^：:]+)[：:](.*)$', line)
        if not match or normalized_label(match[1]) not in wanted:
            continue
        if match[2].strip():
            return True
        for continuation in lines[i+1:]:
            if not continuation.strip():
                continue
            if re.match(r'^\s*#{1,6}\s|^\s*[^：:]{1,60}[：:]', continuation):
                break
            return True
    return False

def validate_a(text,cap=LIMIT,genre="eastern"):
    errors=[]; shots=sections(text,HEADER); units=sections(text,UNIT)
    global_labels=('战斗总基调','角色战前处境与情绪','战斗节奏选型','全片节奏峰值点位') if genre=='eastern' else ('战斗总基调','战前处境','选定打法','节奏峰值')
    overview=re.split(r'(?m)^\s*(?:#{1,6}\s*生成单元|【?镜头\s*\d+)',text)[0]
    for label in global_labels:
        if not re.search(re.escape(label)+r'\s*[：:]\s*[^\s\n]',clean(overview)):
            errors.append(f'A 缺少非空全局说明：{label}。')
    if not shots:errors.append('缺少导演镜头标题。')
    seen=[]; times={}
    for m,body in shots:
        body=re.split(r'(?m)^\s*#{1,6}\s*生成单元\b',body)[0]
        key=f'{int(m[1]):02d}';seen.append(key);value=duration(m[2]);times[key]=value
        check_duration(value,f'A 镜头 {key}',errors,float('inf'))
        # Seven numbered fields, not arbitrary occurrences in prose.
        numbered=list(re.finditer(r'(?m)^\s*([1-7])[.、．]\s*(.+)',clean(body)))
        if [int(x[1]) for x in numbered]!=list(range(1,8)):
            errors.append(f'A 镜头 {key}须依次完整列出 1–7 项。');continue
        for i,x in enumerate(numbered):
            segment=clean(body)[x.end():numbered[i+1].start() if i<6 else len(clean(body))]
            label=x[2].split('：')[0].split(':')[0]
            if normalized_label(label) not in {normalized_label(k) for k in A_FIELDS_BY_GENRE[genre][i]}:errors.append(f'A 镜头 {key}第 {i+1} 项名称不符。')
            if not segment.strip() and not re.search(r'[：:]\s*\S',x[2]):errors.append(f'A 镜头 {key}第 {i+1} 项为空。')
    if len(seen)!=len(set(seen)):errors.append('A 镜号重复，可能重复附了全文。')
    if '【可复制存档区' in text:errors.append('A 不再附独立存档块，正文即完整源稿。')
    if not units:errors.append('A 缺少生成单元及其时长，无法检查 35 秒分组。')
    used=[]; spans={}; direct_used=[]
    for m,body in units:
        value=duration(m[2]);check_duration(value,m[1],errors,cap)
        local=[(x,duration(x[2])) for x in HEADER.finditer(body)]
        span = re.search(r'承载镜号[：:]\s*(\d+)\s*[｜|]\s*成片区间[：:]\s*(\d+(?:\.\d+)?)\s*[—–-]\s*(\d+(?:\.\d+)?)\s*秒', m[2])
        if local and span:
            errors.append(f'{m[1]}不得同时重复列镜头全文与长镜片段映射。')
        if span:
            key=f'{int(span[1]):02d}';start=float(span[2]);end=float(span[3])
            spans.setdefault(key,[]).append((start,end));used.append(key)
            if key not in times or end<=start or start<0 or (times.get(key) is not None and end>times[key]+0.05):
                errors.append(f'{m[1]}长镜片段区间无效或引用无源镜号。')
            if value is not None and abs(end-start-value)>0.05:
                errors.append(f'{m[1]}包时长与成片区间不一致。')
        else:
            if not local:errors.append(f'{m[1]}没有导演镜头或长镜片段映射。')
            local_ids=[f'{int(x[1]):02d}' for x,_ in local]
            used.extend(local_ids);direct_used.extend(local_ids)
            if value is not None and all(v is not None for _,v in local) and abs(sum(v for _,v in local)-value)>0.05:
                errors.append(f'{m[1]}单元时长与镜头合计不一致。')
    if set(direct_used) & set(spans):
        errors.append("同一镜头不能同时按完整镜长分组又按片段重复计时。")
    for key, intervals in spans.items():
        previous=0.0
        for start,end in intervals:
            if abs(start-previous)>0.05:errors.append(f'A 镜头 {key}分包区间重叠、倒序或有缺口。')
            previous=end
        if times.get(key) is not None and abs(previous-times[key])>0.05:
            errors.append(f'A 镜头 {key}分包未覆盖完整镜长。')
    if set(used)!=set(seen):errors.append('A 有镜头未分配到生成单元。')
    if len({m[1] for m,_ in units})!=len(units):errors.append('生成单元编号重复。')
    total=re.search(r'导演稿总时长\s*[：:]\s*([^\n]+)',text)
    if not total:errors.append('缺少导演稿总时长。')
    if total and all(v is not None for v in times.values()):
        v=duration(total[1])
        if v is None or abs(v-sum(times.values()))>0.05:errors.append('导演稿总时长与逐镜合计不一致。')
    return errors

def mapping_totals(left_times, right_times, links, label, errors):
    """Check duration conservation per connected mapping component, including merges/splits."""
    graph={}
    for left, rights in links.items():
        for right in rights:
            a=('l',left); b=('r',right)
            graph.setdefault(a,set()).add(b); graph.setdefault(b,set()).add(a)
    visited=set()
    for first in graph:
        if first in visited:continue
        pending=[first]; component=set()
        while pending:
            node=pending.pop()
            if node in component:continue
            component.add(node); pending.extend(graph[node]-component)
        visited.update(component)
        left=[key for side,key in component if side=='l']
        right=[key for side,key in component if side=='r']
        lv=[left_times.get(key) for key in left]; rv=[right_times.get(key) for key in right]
        if all(v is not None for v in lv+rv) and abs(sum(lv)-sum(rv))>0.05:
            errors.append(f'{label}时长不守恒：{",".join(sorted(left))} 与 {",".join(sorted(right))} 合计不一致。')

def validate_b(text,source,cap=LIMIT,genre='eastern'):
    errors=[];engines=sections(text,ENGINE);packs=sections(text,UNIT)
    if not engines:errors.append('缺少逐镜工程分镜。')
    if not packs:errors.append('缺少实际投喂包。')
    if not re.search(r'正向提示词|全局正向制作基线',text):errors.append('缺少全局正向制作基线。')
    source_ids={f'{int(m[1]):02d}' for m in HEADER.finditer(source)} if source else set()
    if not source_ids:errors.append('B 完整校验须提供含完整镜号的 --source-a。')
    else:
        errors.extend('A 源稿无效：'+error for error in validate_a(source,LIMIT,genre))
    estate={}; mapped=[]
    for m,body in engines:
        body=re.split(r'(?m)^\s*#{1,6}\s*生成单元\b',body)[0]
        eid=m[1];header=m[2];a=re.search(r'对应 A 镜号[：:]\s*([^｜|\n]+)',header)
        aid=ids(a[1]) if a else []
        if eid in estate:errors.append(f'工程镜号 {eid} 重复。')
        estate[eid]=(aid,duration(header));mapped+=aid
        check_duration(duration(header),eid,errors,float('inf'))
        if not aid:errors.append(f'{eid}缺对应 A 镜号。')
        if len(aid)!=len(set(aid)):errors.append(f'{eid}的 A 镜号重复。')
        for variants in B_FIELDS_BY_GENRE[genre]:
            if not has_engineering_field(body,variants):errors.append(f'{eid}缺少工程字段：{variants[0]}。')
        if genre=='eastern' and '本镜头底线强制关键词' not in body:errors.append(f'{eid}缺玄幻规范的底线关键词。')
    if set(mapped)!=source_ids:errors.append('工程稿对 A 源镜号覆盖不完整或存在无源镜号。')
    source_times={f'{int(m[1]):02d}':duration(m[2]) for m in HEADER.finditer(source)}
    mapping_totals({eid:value[1] for eid,value in estate.items()},source_times,{eid:value[0] for eid,value in estate.items()},'工程→A',errors)
    covered=[];pack_ids=[];pack_times={};pack_links={}
    for m,body in packs:
        pid=m[1];pack_ids.append(pid);check_duration(duration(m[2]),pid,errors,cap)
        header=m[2];e=re.search(r'工程镜号[：:]\s*([^｜|\n]+)',header);a=re.search(r'对应 A 镜号[：:]\s*([^｜|\n]+)',header)
        eids=ids(e[1],'E') if e else []; aids=ids(a[1]) if a else []
        pack_times[pid]=duration(header);pack_links[pid]=eids
        if len(eids)!=len(set(eids)) or len(aids)!=len(set(aids)):errors.append(f'{pid}的映射编号重复。')
        if not eids:errors.append(f'{pid}缺工程镜号。')
        if not field(body,'目标'):errors.append(f'{pid}缺目标。')
        expected=set()
        for eid in eids:
            if eid not in estate:errors.append(f'{pid}引用不存在的 {eid}。')
            else:expected.update(estate[eid][0])
            covered.append(eid)
        if set(aids)!=expected:errors.append(f'{pid}的 A 镜号与工程镜号映射不一致。')
        prompt=field(body,'投喂 Prompt')
        if not prompt:errors.append(f'{pid}缺完整投喂 Prompt。')
        elif re.search(r'同上|沿用上一镜',prompt):errors.append(f'{pid}的实际 Prompt 含跨包替代语。')
    if set(covered)!=set(estate):errors.append('投喂包未覆盖全部工程镜号。')
    if len(pack_ids)!=len(set(pack_ids)):errors.append('投喂包单元编号重复。')
    mapping_totals(pack_times,{eid:value[1] for eid,value in estate.items()},pack_links,'投喂→工程',errors)
    return errors

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path',type=Path)
    parser.add_argument('--mode',required=True,choices=['a','b','units','single','rapid','refined'])
    parser.add_argument('--genre',choices=['eastern','wuxia','scifi','western'],default='eastern')
    parser.add_argument('--source-a',type=Path)
    parser.add_argument('--max-unit-seconds',type=float,default=LIMIT)
    parser.add_argument('--max-segment-seconds',type=float,default=LIMIT)
    parser.add_argument('--require-focal-length',action='store_true')
    args=parser.parse_args()
    if args.mode in ['units','single','rapid','refined']:
        return subprocess.call([sys.executable,'-X','utf8',str(Path(__file__).with_name('validate_legacy_storyboard.py')),*sys.argv[1:]])
    if not 0<args.max_unit_seconds<=LIMIT:parser.error('当前 A/B 上限必须大于 0 且不得超过 35 秒。')
    try:
        text=args.path.read_text(encoding='utf-8-sig')
        source=args.source_a.read_text(encoding='utf-8-sig') if args.source_a else ''
    except OSError as exc:parser.error(str(exc))
    errors=validate_a(text,args.max_unit_seconds,args.genre) if args.mode=='a' else validate_b(text,source,args.max_unit_seconds,args.genre)
    for e in errors:print('ERROR:',e,file=sys.stderr)
    if not errors:print('结构检查通过；剧情、受力、空间、时序语义及成片效果仍须审读。')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
