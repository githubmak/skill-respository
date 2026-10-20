import argparse,importlib.util,json,re
from pathlib import Path
r=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description='Render reviewed static combat regression fixtures; does not sample a model or validate creative quality.')
parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args();out=args.output_dir;out.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('v',r/'scripts/validate_storyboard.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
cases=json.loads((r/'scripts/fixtures/combat_cases.json').read_text(encoding='utf-8'))
cases[2]['shots'][0]['camera']=cases[2]['shots'][0]['camera'].replace('甩摇向东','甩摇向西')
checks=[]
for c in cases:
 g=c['genre'];total=sum(s['sec'] for s in c['shots']);folder=out/c['name'];folder.mkdir(exist_ok=True)
 (folder/'原始剧本.md').write_text(c['source'],encoding='utf-8')
 a=['# '+{'eastern':'仙侠打斗导演分镜脚本','wuxia':'中国古代武打导演分镜脚本','scifi':'科幻异能战斗导演分镜脚本','western':'西方魔幻战斗导演分镜脚本'}[g],'\n## 轻量设计卡']
 for i,card in enumerate(c['cards'],1):
  a.append(f'\n方案{i}：'+'；'.join(f'{n+1} {x}' for n,x in enumerate(card)))
 a.extend(['\n'+c['choice_reason'],'\n## 全局导演说明',f'> 战斗总基调：{c["style"]}',f'> 角色战前处境与情绪：{c["source"]}', '> 战斗节奏选型：'+c['rhythm'],'> 全片节奏峰值点位：'+c['peak'],f'导演稿总时长：{total}秒',f'### 生成单元 G01｜时长：{total}秒'])
 b=['## 全局正向制作基线',c['style']+' '+c['source']]
 packs=[]
 for i,s in enumerate(c['shots'],1):
  n=f'{i:02d}';a.append(f'\n【镜头 {n}｜攻防核心镜｜{s["sec"]}秒｜{s["title"]}｜{s["emotion"]}】')
  contents=[s['camera'],s['axis']+' '+s['action']+' '+s['emotion'],('【中】' if i==1 else '【重】')+s['fx'],s['result']+' '+s['detail'],s['perform'],s['emotion'],s['prompt']]
  for k,(labels,content) in enumerate(zip(v.A_FIELDS_BY_GENRE[g],contents),1):a.append(f'{k}. **{labels[0]}**：{content}')
  b.extend([f'\n### 工程镜头 E{n}｜对应 A 镜号：{n}｜时长：{s["sec"]}秒',f'【{s["title"]}｜{s["sec"]}秒｜连续运动中保留接触与结果读点】'])
  if g=='eastern':b.append('本镜头底线强制关键词：手持剑不复制、风刃仅一条；不飞行；保留门与双方结局。')
  mechanism=c['mechanism']
  values=[s['axis'],s['props'],s['start']+' 准备来自当前承接，不另加蓄力停顿。',s['start']+' → '+s['action']+' → '+s['result'],s['camera'],'按本镜连续行动的相对速度执行，近景掠过可方向性模糊，关键接触和落幅恢复读点；不以慢镜停住双方。',s['action'],('L1 场地、地标和实际介质：'+c['style']+'；L2 主体/随动：'+s['fx']+'；L3 接触证据：'+s['detail']+'；L4 结果与残留：'+s['result']+'。各层只在本镜实际事件中出现，不依次播放。'),mechanism,s['fx'],s['camera']+' 近处承接触感，中景读取身体/控制，远处地标证明方向与结果，按当前景别取可见内容。',s['detail'],s['light'],s['audio']]
  for labels,value in zip(v.B_FIELDS_BY_GENRE[g],values):b.append(f'【{labels[0]}】：{value}')
  packs.extend([f'\n### 生成单元 G{n}｜对应 A 镜号：{n}｜工程镜号：E{n}｜包时长：{s["sec"]}秒',f'目标：{s["result"]}',f'投喂 Prompt：{s["prompt"]}'])
 if g!='eastern':
  a=[line.replace('角色战前处境与情绪：','战前处境：').replace('战斗节奏选型：','选定打法：').replace('全片节奏峰值点位：','节奏峰值：') for line in a]
 at='\n\n'.join(a)+'\n';bt='\n\n'.join(b+packs)+'\n'
 (folder/'A导演稿.md').write_text(at,encoding='utf-8');(folder/'B工程与投喂包.md').write_text(bt,encoding='utf-8');(folder/'仅投喂提示词.md').write_text('\n\n'.join(packs)+'\n',encoding='utf-8')
 ea=v.validate_a(at,genre=g);eb=v.validate_b(bt,at,genre=g)
 checks.append({'case':c['name'],'seconds':total,'A_errors':ea,'B_errors':eb,'note':'Hand-authored cases; structured fields and final descriptions share the same authored design. Not independent A-to-B model sampling.'})
(out/'四题材结构结果.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'{len(checks)} reviewed static cases rendered; A/B structural failures: {sum(bool(x["A_errors"] or x["B_errors"]) for x in checks)}')
raise SystemExit(any(x['A_errors'] or x['B_errors'] for x in checks))
