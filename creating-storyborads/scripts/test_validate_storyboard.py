import copy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

spec=importlib.util.spec_from_file_location('validator',Path(__file__).with_name('validate_storyboard.py'))
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def fixture(music=True):
    source='林岚：不来了。\n周远OS：原来如此。'.encode()
    text=source.decode()
    utterances=[]
    for uid,sp,kind,line in [('U001','林岚','对白','不来了。'),('U002','周远','OS','原来如此。')]:
        at=text.index(line)
        utterances.append(dict(id=uid,speaker=sp,kind=kind,text=line,source_start=at,source_end=at+len(line)))
    ledger=dict(version=1,source_sha256=hashlib.sha256(source).hexdigest(),music=music,unit_music={},max_unit_seconds=35,utterances=utterances)
    bgm='配乐：钢琴短音型持续，字头减薄；场末收束。\n' if music else ''
    sound='## 全局配音、配乐与声音规则\n- 配音基线：人声优先。\n- 配乐主题：克制。\n- 乐器与音色分工：钢琴。\n- 声层与接续原则：避让对白。\n' if music else ''
    template=(Path(v.__file__).parent.parent/'references/output-detail.md').read_text().split('```')[1]
    scene='## '+template.split('# 场景',1)[1].split('## ',1)[1].split('### 生成单元',1)[0]
    scene=scene.replace('- 拓扑共识：','- 拓扑共识：二人隔桌相对。').replace('- 正向提示词：','- 正向提示词：房间。').replace('- 负向约束：','- 负向约束：不增加人物。')
    md=f'''# 《测试》Seedance 独立直投版
## 项目直投参数
- 成片总时长：6秒
- 生成单元数：1
- 成片镜头数：1
- 生成单元时长上限：35秒
- 背景配乐：{'开启' if music else '关闭'}
## 全局摄影规则
轴线南侧。
## 全局光色与影调基线
日光。
{sound}## 全局正向提示词
二维漫剧。
## 全局负面提示词
不增加人物。
# 场景一｜房间·日
{scene}
### 生成单元 G1 ｜时长：6 秒｜承载：镜头 S1-01｜交还
- 起幅与连续性：
林岚与周远相对站定。
- 摄影与构图：
摄影机在关系轴南侧，二人侧面可见。
- 光影、环境色彩与材质：
左侧窗光，未指定人物外观。
- 画面与表演时间线：
0.0—6.0秒｜S1-01｜50mm 中景｜固定
林岚将书袋交还，周远接住。
声音：话语U001后接U002，布料接触声。
{bgm}- 台词与声音层次：
林岚在0.2—1.8秒说：“不来了。”自然说完；嘴部可见同步口型。
周远在2.0—4.0秒OS：“原来如此。”不生成口型，不被林岚听见。
- 落幅状态：
周远持袋，林岚已松手。
'''
    return md,source,ledger


class ValidationTests(unittest.TestCase):
    def run_case(self,md,source,ledger):
        return v.validate(md,source,ledger)
    def assert_code(self,result,code):
        self.assertIn(code,[x['code'] for x in result['errors']])
    def test_music_on_and_off(self):
        for music in (True,False):
            r=self.run_case(*fixture(music))
            self.assertTrue(r['static_pass'],r)
            self.assertTrue(r['manual_required'])
    def test_off_rejects_background_line(self):
        md,s,l=fixture(False)
        self.assert_code(self.run_case(md.replace('- 台词与声音层次：','配乐：持续。\n- 台词与声音层次：'),s,l),'music_disabled')
    def test_music_required_per_window(self):
        md,s,l=fixture()
        md=md.replace('配乐：钢琴短音型持续，字头减薄；场末收束。\n','')
        self.assert_code(self.run_case(md,s,l),'music_missing')
    def test_source_change_and_invalid_span(self):
        md,s,l=fixture()
        self.assert_code(self.run_case(md,s+b'!',l),'source_hash')
        l['utterances'][0]['source_start']+=1
        self.assert_code(self.run_case(md,s,l),'source_span')
    def test_dialogue_drop_change_duplicate_and_attribution(self):
        md,s,l=fixture()
        self.assert_code(self.run_case(md.replace('不来了。','不来。'),s,l),'dialogue_exact')
        line=next(x for x in md.splitlines() if x.startswith('林岚在'))
        self.assert_code(self.run_case(md.replace(line+'\n',''),s,l),'dialogue_exact')
        self.assert_code(self.run_case(md.replace(line,line+'\n'+line),s,l),'dialogue_exact')
    def test_time_gap_and_duration(self):
        md,s,l=fixture()
        self.assert_code(self.run_case(md.replace('0.0—6.0秒｜','1.0—6.0秒｜'),s,l),'time_coverage')
        l['max_unit_seconds']=5
        self.assert_code(self.run_case(md,s,l),'unit_duration')
    def test_lens_and_mapping_and_stats(self):
        md,s,l=fixture()
        for before,after,code in [('50mm','0mm','lens'),('50mm','长焦','lens'),('承载：镜头 S1-01','承载：镜头 S1-02','shot_mapping'),('成片镜头数：1','成片镜头数：2','statistics')]:
            self.assert_code(self.run_case(md.replace(before,after),s,l),code)
    def test_missing_fields_and_empty_picture(self):
        md,s,l=fixture()
        self.assert_code(self.run_case(md.replace('- 落幅状态：','- 结果：'),s,l),'fields')
        self.assert_code(self.run_case(md.replace('林岚将书袋交还，周远接住。',''),s,l),'picture_empty')
    def test_missing_global_and_scene_columns(self):
        md,s,l=fixture()
        self.assert_code(self.run_case(md.replace('## 全局摄影规则','## 摄影'),s,l),'global_format')
        self.assert_code(self.run_case(md.replace('## 场景空间位置关系','## 空间'),s,l),'scene_format')
    def test_off_has_no_extra_sound_heading(self):
        md,s,l=fixture(False)
        self.assertNotIn('## 全局配音',md)
        self.assert_code(self.run_case(md.replace('## 全局正向提示词','## 全局配音与声音规则\n人声优先。\n## 全局正向提示词'),s,l),'global_format')
    def test_split_allocations_stay_internal(self):
        md,s,l=fixture()
        l['delivery']=[dict(id='U001',unit='G1',text='不来了。'),dict(id='U002',unit='G1',text='原来如此。')]
        self.assertTrue(self.run_case(md,s,l)['static_pass'])
        l['delivery'][0]['text']='不来'
        self.assert_code(self.run_case(md,s,l),'dialogue_exact')

    def test_cli_report_does_not_overwrite_input(self):
        md,s,l=fixture()
        import json
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'main.md').write_text(md)
            (p/'source.txt').write_bytes(s)
            (p/'ledger.json').write_text(json.dumps(l,ensure_ascii=False))
            cmd=[sys.executable,str(Path(v.__file__)),str(p/'main.md'),'--source',str(p/'source.txt'),'--ledger',str(p/'ledger.json')]
            run=subprocess.run(cmd+['--report',str(p/'source.txt')],capture_output=True)
            self.assertEqual(run.returncode,2)
            self.assertEqual((p/'source.txt').read_bytes(),s)
            run=subprocess.run(cmd+['--report',str(p/'report.json')],capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertTrue(json.loads((p/'report.json').read_text())['static_pass'])

if __name__=='__main__':
    unittest.main()
