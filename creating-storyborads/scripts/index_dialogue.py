#!/usr/bin/env python3
"""Locate once-extracted utterances in source text; never extract or infer attribution.

Input is a JSON list of {id, speaker, kind, text, optional source_start}.
Prints selected source contexts for human review. Repeated matches require offsets.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def build(source_bytes, utterances, music=True, max_unit_seconds=35):
    source=source_bytes.decode('utf-8')
    if type(music) is not bool or not isinstance(max_unit_seconds,(int,float)) or not 0<max_unit_seconds<float('inf'):
        raise ValueError('music must be boolean and max unit seconds positive/finite')
    if not isinstance(utterances,list):
        raise ValueError('input must be a JSON utterance list')
    rows, contexts, seen, cursor = [], [], set(), 0
    for u in utterances:
        if not isinstance(u,dict):
            raise ValueError('each utterance must be an object')
        uid=u.get('id','')
        if not isinstance(uid,str) or not uid.startswith('U') or not uid[1:].isdigit() or uid in seen:
            raise ValueError('unique U<number> id required')
        seen.add(uid)
        text=u.get('text')
        if not isinstance(text,str) or not text or not isinstance(u.get('speaker'),str) or not u['speaker'].strip() or u.get('kind') not in ('对白','OS','OV','旁白'):
            raise ValueError(uid+': nonempty text/speaker and valid kind required')
        start=u.get('source_start')
        if start is None:
            start=source.find(text,cursor)
            if start < 0:
                raise ValueError(uid+': no exact sequential match in source')
            if source.find(text,start+1)>=0:
                raise ValueError(uid+': multiple possible source matches; inspect context and provide source_start explicitly')
        if type(start) is not int or start < cursor or source[start:start+len(text)] != text:
            raise ValueError(uid+': invalid or out-of-order source_start')
        cursor=start+len(text)
        rows.append(dict(id=uid,speaker=u['speaker'],kind=u['kind'],text=text,source_start=start,source_end=cursor))
        contexts.append({'id':uid,'line':source.count('\n',0,start)+1,'source_start':start,'context':source[max(0,start-35):min(len(source),cursor+35)]})
    return dict(version=1,source_sha256=hashlib.sha256(source_bytes).hexdigest(),music=music,unit_music={},max_unit_seconds=max_unit_seconds,utterances=rows),contexts


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('utterances',type=Path)
    p.add_argument('output',type=Path)
    p.add_argument('--music',choices=('on','off'),default='on')
    p.add_argument('--max-unit-seconds',type=float,default=35)
    a=p.parse_args()
    try:
        if a.output.resolve() in (a.source.resolve(),a.utterances.resolve()):
            raise ValueError('output must not overwrite source or extracted utterances')
        ledger,contexts=build(a.source.read_bytes(),json.loads(a.utterances.read_bytes()),a.music=='on',a.max_unit_seconds)
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'indexed':len(contexts),'review_contexts':contexts,'manual_required':'核对提取覆盖、说话者、类型与出处；脚本不推断这些事实。'},ensure_ascii=False,indent=2))
        return 0
    except (OSError,ValueError,TypeError) as exc:
        print(str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':
    sys.exit(main())
