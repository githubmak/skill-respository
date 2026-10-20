#!/usr/bin/env python3
"""Reproducible structural regression and boundary tests; not a creative-quality evaluator."""
import argparse,importlib.util,json,random,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('validator',ROOT/'scripts/validate_storyboard.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

def a_doc(genre, times=(8,10), groups=None):
    if groups is None:groups=[list(range(len(times)))]
    globals=('战斗总基调','角色战前处境与情绪','战斗节奏选型','全片节奏峰值点位') if genre=='eastern' else ('战斗总基调','战前处境','选定打法','节奏峰值')
    lines=[f'{label}：守方护门，刀背带开来刃，接触与退距有强弱变化。' for label in globals]+[f'导演稿总时长：{sum(times):g}秒']
    for gi,group in enumerate(groups,1):
        lines.append(f'### 生成单元 G{gi:02d}｜时长：{sum(times[i] for i in group):g}秒')
        for i in group:
            lines.append(f'【镜头 {i+1:02d}｜攻防核心镜｜{times[i]:g}秒｜挡线｜守住出口】')
            for k,labels in enumerate(v.A_FIELDS_BY_GENRE[genre],1):
                lines.append(f'{k}. **{labels[0]}**：守方右手持剑在门东侧偏身格开来刃，后脚承重续接侧移。')
    return '\n'.join(lines)+'\n'

def b_doc(genre, engines=None, packs=None):
    if engines is None:engines=[('E01',['01'],8),('E02',['02'],10)]
    if packs is None:packs=[('G01',['01'],['E01'],8),('G02',['02'],['E02'],10)]
    lines=['## 全局正向制作基线','冷色雨巷，双方装备、伤势及出口不变。']
    for eid,aids,sec in engines:
        lines.extend([f'### 工程镜头 {eid}｜对应 A 镜号：{",".join(aids)}｜时长：{sec:g}秒','本镜头底线强制关键词：武器不换主。'])
        for labels in v.B_FIELDS_BY_GENRE[genre]:lines.append(f'【{labels[0]}】：守方在门东侧右手持剑，南侧摄影，接触后侧移卸力，双方无新伤。')
    for gid,aids,eids,sec in packs:
        lines.extend([f'### 生成单元 {gid}｜对应 A 镜号：{",".join(aids)}｜工程镜号：{",".join(eids)}｜包时长：{sec:g}秒','目标：格开刀锋守住出口。','投喂 Prompt：冷色雨巷，南侧中景。守方右手持剑侧身格刀，后脚承重，刀锋滑向门外，出口完整。'])
    return '\n'.join(lines)+'\n'

def run():
    records=[]
    def check(name,actual,valid):
        okay=(not actual)==valid
        records.append({'case':name,'expected':'accept' if valid else 'reject','passed':okay,'errors':actual})
    for g in v.A_FIELDS_BY_GENRE:
        a=a_doc(g);b=b_doc(g)
        for name,aa,bb,valid in [
            ('valid',a,b,True),
            ('invalid_source_missing_fields',re.sub(r'(?m)^3\..*\n','',a),b,False),
            ('source_time_mismatch',a,b.replace('时长：8秒','时长：9秒'),False),
            ('missing_target',a,b.replace('目标：格开刀锋守住出口。\n',''),False),
            ('unknown_engine',a,b.replace('工程镜号：E01','工程镜号：E99'),False),
            ('duplicate_map',a,b.replace('工程镜号：E01','工程镜号：E01,E01'),False),
            ('duplicate_engine',a,b.replace('工程镜头 E02','工程镜头 E01'),False),
            ('missing_engine_field',a,re.sub(r'(?m)^【道具归属与状态】.*\n','',b),False),
            ('empty_engine_field',a,b.replace('【道具归属与状态】：守方在门东侧右手持剑，南侧摄影，接触后侧移卸力，双方无新伤。','【道具归属与状态】：'),False),
            ('missing_prompt',a,b.replace('投喂 Prompt：冷色雨巷，南侧中景。守方右手持剑侧身格刀，后脚承重，刀锋滑向门外，出口完整。',''),False),
            ('cross_package_shorthand',a,b.replace('投喂 Prompt：冷色雨巷','投喂 Prompt：同上，冷色雨巷'),False),
            ('no_source','',b,False),
            ('hidden_six_fields_absent',a,b,True),
            ('merged_package',a,b_doc(g,packs=[('G01',['01','02'],['E01','E02'],18)]),True),
            ('merged_package_short',a,b_doc(g,packs=[('G01',['01','02'],['E01','E02'],17)]),False),
            ('merged_engine',a,b_doc(g,engines=[('E01',['01','02'],18)],packs=[('G01',['01','02'],['E01'],18)]),True),
            ('split_engine',a,b_doc(g,engines=[('E01',['01'],3),('E02',['01'],5),('E03',['02'],10)],packs=[('G01',['01'],['E01'],3),('G02',['01'],['E02'],5),('G03',['02'],['E03'],10)]),True),
            ('split_package',a,b_doc(g,packs=[('G01',['01'],['E01'],3),('G02',['01'],['E01'],5),('G03',['02'],['E02'],10)]),True),
            ('split_package_repeats_duration',a,b_doc(g,packs=[('G01',['01'],['E01'],8),('G02',['01'],['E01'],8),('G03',['02'],['E02'],10)]),False),
        ]:check(g+'/B/'+name,v.validate_b(bb,aa,genre=g),valid)
        check(g+'/B/short_output_cap_preserves_valid_long_A_group',v.validate_b(b,a,cap=10,genre=g),True)
        for sec,valid in [(0,False),(-1,False),(0.1,True),(34.99,True),(35,True),(35.01,False),(36,False)]:
            check(g+f'/A/duration/{sec}',v.validate_a(a_doc(g,(sec,)),genre=g),valid)
        for name,aa,valid in [
            ('missing_global',re.sub(r'(?m)^战斗总基调.*\n','',a),False),
            ('missing_total',a.replace('导演稿总时长：18秒\n',''),False),
            ('wrong_total',a.replace('导演稿总时长：18秒','导演稿总时长：17秒'),False),
            ('empty_last_field_before_next_unit',a_doc(g,(8,10),[[0],[1]]).replace('7. **画面完整描述**：守方右手持剑在门东侧偏身格开来刃，后脚承重续接侧移。','7. **画面完整描述**：',1),False),
            ('orphan_shot',a.replace('### 生成单元 G01｜时长：18秒\n',''),False),
            ('duplicate_shot',a.replace('镜头 02','镜头 01'),False),
            ('long_battle_split',a_doc(g,(20,20),[[0],[1]]),True),
            ('long_unit_unsplit',a_doc(g,(20,20)),False),
            ('decimal_time',a_doc(g,(8.25,9.75)),True),
            ('local_cap_10',a_doc(g,(8,10),[[0],[1]]),True),
        ]:check(g+'/A/'+name,v.validate_a(aa,cap=10 if name=='local_cap_10' else 35,genre=g),valid)
    # Stable parser acceptance under reproducible whitespace, line-ending and markdown variants.
    variants=[]
    rng=random.Random(20261020)
    for i in range(30):
        g=list(v.A_FIELDS_BY_GENRE)[i%4];a=a_doc(g);b=b_doc(g)
        if i%2:a=a.replace('\n','\r\n');b=b.replace('\n','\r\n')
        if i%3==0:a=a.replace('：',':');b=b.replace('：',':')
        if i%5==0:a=a.replace('**','');b=b.replace('【','').replace('】','')
        variants.append((g,a,b))
    first=[(v.validate_a(a,genre=g),v.validate_b(b,a,genre=g)) for g,a,b in variants]
    for i,errs in enumerate(first):check(f'stability/format_variant/{i}',errs[0]+errs[1],True)
    repeated=all(first==[(v.validate_a(a,genre=g),v.validate_b(b,a,genre=g)) for g,a,b in variants] for _ in range(20))
    check('stability/20_repeat_batches',[] if repeated else ['non deterministic'],True)
    # Existing documentation and internal anchor resolution.
    broken=[]
    for p in ROOT.rglob('*.md'):
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8-sig')):
            target,_,anchor=link.partition('#')
            if '://' in target or target.startswith('$'):continue
            q=p.parent/target if target else p
            if not q.exists():broken.append(str(q));continue
            if anchor.startswith('c') and re.fullmatch(r'c\d+',anchor) and f'id="{anchor}"' not in q.read_text(encoding='utf-8-sig'):broken.append(str(q)+'#'+anchor)
    check('documentation/local_links_and_C_anchors',broken,True)
    return records

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--json',type=Path);args=parser.parse_args()
    records=run();failed=[r for r in records if not r['passed']]
    report={'scope':'Structural tests and parser repeatability only; not independent model sampling or video validation.','passed':len(records)-len(failed),'total':len(records),'records':records}
    if args.json:args.json.parent.mkdir(parents=True,exist_ok=True);args.json.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    for row in failed:print(json.dumps(row,ensure_ascii=False))
    print(f'{len(records)-len(failed)}/{len(records)} structural and boundary checks passed; parser repeated 20 batches of 30 variants.')
    raise SystemExit(bool(failed))
