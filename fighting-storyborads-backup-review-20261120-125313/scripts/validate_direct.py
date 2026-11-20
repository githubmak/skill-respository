#!/usr/bin/env python3
"""Check direct-delivery structure; aesthetic and source fidelity need review."""
import argparse,re,sys
from pathlib import Path

def validate(text,scope='all'):
 errors=[]
 def split(kind,prefix):
  pat=re.compile(r'^### '+kind+r' ('+prefix+r'\d+)｜([^\n]+)',re.M)
  ms=list(pat.finditer(text))
  return [(m[1],m[2],text[m.end():ms[i+1].start() if i+1<len(ms) else len(text)]) for i,m in enumerate(ms)]
 engines=split('工程镜头','E'); units=split('生成单元','G')
 for label,rows in [('工程镜头',engines),('生成单元',units)]:
  names=[x[0] for x in rows]
  if len(set(names))!=len(names): errors.append(label+'编号重复')
 if scope!='prompts':
  if not engines: errors.append('缺少工程镜头')
  for key,head,body in engines:
   for field in ['空间与起态','摄影与节奏','连续声画','落幅与接点']:
    if not re.search(re.escape(field)+r'[：:]\s*\S',body):errors.append(key+'缺少'+field)
 if scope!='engineering':
  if not units:errors.append('缺少生成单元')
  refs=[]
  for key,head,body in units:
   duration=re.search(r'(?<!预计)时长[：:]\s*(\d+(?:\.\d+)?)秒',head)
   if not duration or not 0<float(duration[1])<=30:errors.append(key+'时长须在0至30秒内')
   reference=re.search(r'对应工程镜号[：:]\s*(E\d+(?:\s*[,、]\s*E\d+)*)',head)
   if not reference:errors.append(key+'缺少工程引用')
   else:refs.extend(re.findall(r'E\d+',reference[1]))
   for field in ['投喂 Prompt','接缝']:
    if not re.search(re.escape(field)+r'[：:]\s*\S',body):errors.append(key+'缺少'+field)
  if scope=='all':
   ids=[x[0] for x in engines]
   compressed=[v for i,v in enumerate(refs) if i==0 or refs[i-1]!=v]
   if compressed!=ids:errors.append('投喂包覆盖或顺序与工程稿不一致')
 return errors

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('file',type=Path);parser.add_argument('--scope',choices=['all','engineering','prompts'],default='all');args=parser.parse_args()
 errors=validate(args.file.read_text(),args.scope)
 print('\n'.join(errors) if errors else '结构检查通过；观看效果与源稿保真仍需审读。')
 sys.exit(bool(errors))
