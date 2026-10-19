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
    template=(Path(v.__file__).parent.parent/'references/output-detail.md').read_text(encoding='utf-8').split('```')[1]
    scene='## '+template.split('# 场景',1)[1].split('## ',1)[1].split('### 生成单元',1)[0]
    scene=scene.replace('- 拓扑共识：','- 拓扑共识：二人隔桌相对。').replace('- 正向提示词：','- 正向提示词：房间。').replace('- 负向约束：','- 负向约束：不增加人物。')
    scene=scene.replace('## 场景空间位置关系\n', '## 场景空间位置关系\n二人隔桌相对，摄影机在轴线南侧。\n')
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

    def test_empty_sound_and_global_items_do_not_consume_next_line(self):
        md,s,l=fixture()
        self.assert_code(self.run_case(md.replace('声音：话语U001后接U002，布料接触声。','声音：'),s,l),'sound')
        self.assert_code(self.run_case(md.replace('- 配音基线：人声优先。','- 配音基线：'),s,l),'global_sound')
        self.assert_code(self.run_case(md.replace('轴线南侧。\n## 全局光色','\n## 全局光色'),s,l),'global_empty')

    def test_empty_document_returns_errors_not_traceback(self):
        _,s,l=fixture()
        self.assert_code(self.run_case('',s,l),'no_units')
        self.assert_code(self.run_case('',s,l),'title_format')

    def test_new_explicit_speaker_is_not_silently_ignored(self):
        md,s,l=fixture()
        for line in ['陌生人 对白（4.0—5.0秒）：「新增一句。」',
                     '陌生人在4.0—5.0秒说：“新增一句。”',
                     '林岚母亲 对白（4.0—5.0秒）：「新增一句。」']:
            self.assert_code(self.run_case(md.replace('- 落幅状态：',line+'\n- 落幅状态：'),s,l),'dialogue_exact')
        l['utterances']=[]
        start=md.index('- 台词与声音层次：')+len('- 台词与声音层次：')
        end=md.index('- 落幅状态：',start)
        md=md[:start]+'\n陌生人 对白：「新增一句。」\n'+md[end:]
        self.assert_code(self.run_case(md,s,l),'dialogue_exact')

    def test_first_assets_cannot_borrow_prop_labels(self):
        md,s,l=fixture()
        md=md.replace('- 正向提示词：房间。','- 正向提示词：',1)
        self.assert_code(self.run_case(md,s,l),'scene_assets')

    def test_reused_scene_accepts_change_only_assets(self):
        md,s,l=fixture()
        scene=md[md.index('# 场景一｜'):]
        scene=scene.replace('# 场景一｜房间·日','# 场景二｜房间·夜').replace('G1','G2').replace('S1-01','S2-01')
        start=scene.index('## 场景资产图提示词')
        content_start=scene.index('\n',start)+1
        end=scene.index('## 道具资产图提示词',content_start)
        scene=scene[:content_start]+'\n复用房间，仅改为夜晚窗光。\n'+scene[end:]
        start=scene.index('- 台词与声音层次：')+len('- 台词与声音层次：')
        end=scene.index('- 落幅状态：',start)
        scene=scene[:start]+'\n无新增对白。\n'+scene[end:]
        md=md.replace('成片总时长：6秒','成片总时长：12秒').replace('生成单元数：1','生成单元数：2').replace('成片镜头数：1','成片镜头数：2')+scene
        self.assertTrue(self.run_case(md,s,l)['static_pass'],self.run_case(md,s,l))
        # An empty final scene must not pass merely by copying its headings.
        empty=scene[:scene.index('### 生成单元')]
        self.assert_code(self.run_case(md+empty.replace('场景二','场景三'),s,l),'scene_units')
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


    def custom_dialogue(self, entries, allocated=False):
        md, _, ledger = fixture()
        source_text = '\n'.join(sp + ('OS' if kind == 'OS' else '') + '：' + words for sp, kind, words in entries)
        source = source_text.encode('utf-8')
        ledger['source_sha256'] = hashlib.sha256(source).hexdigest()
        ledger['utterances'] = []
        cursor = 0
        lines = []
        for number, (speaker, kind, words) in enumerate(entries, 1):
            start = source_text.index(words, cursor)
            cursor = start + len(words)
            ledger['utterances'].append(dict(id=f'U{number:03}', speaker=speaker, kind=kind, text=words, source_start=start, source_end=cursor))
            lines.append(f'{speaker}在0.2—1.8秒' + ('OS' if kind == 'OS' else '说') + f'：“{words}”自然说完。')
        start = md.index('- 台词与声音层次：') + len('- 台词与声音层次：')
        end = md.index('- 落幅状态：', start)
        md = md[:start] + '\n' + '\n'.join(lines) + '\n' + md[end:]
        if allocated:
            ledger['delivery'] = [dict(id=u['id'], unit='G1', text=u['text']) for u in ledger['utterances']]
        return md, source, ledger

    def test_punctuation_and_short_utterances_are_whole_records(self):
        for allocated in (False, True):
            for long, short in [('你来吗？', '？'), ('等等……好吧。', '……'), ('真的好。', '好。')]:
                with self.subTest(allocated=allocated, short=short):
                    case = self.custom_dialogue([('林岚', '对白', long), ('周远', '对白', short)], allocated)
                    self.assertTrue(self.run_case(*case)['static_pass'], self.run_case(*case))
                    md, source, ledger = case
                    line = next(x for x in md.splitlines() if x.startswith('周远在'))
                    self.assert_code(self.run_case(md.replace(line, ''), source, ledger), 'dialogue_exact')

    def test_real_repetitions_consumed_once(self):
        for allocated in (False, True):
            md, source, ledger = self.custom_dialogue([('林岚', '对白', '好。'), ('林岚', '对白', '好。')], allocated)
            self.assertTrue(self.run_case(md, source, ledger)['static_pass'])
            line = next(x for x in md.splitlines() if x.startswith('林岚在'))
            self.assert_code(self.run_case(md.replace(line, '', 1), source, ledger), 'dialogue_exact')
            self.assert_code(self.run_case(md.replace(line, line+'\n'+line, 1), source, ledger), 'dialogue_exact')

    def test_wrong_speaker_and_kind(self):
        md, source, ledger = fixture()
        for before, after in [('林岚在0.2', '周远在0.2'), ('秒OS：', '秒说：')]:
            self.assert_code(self.run_case(md.replace(before, after), source, ledger), 'dialogue_exact')

    def test_notes_and_nested_quotes(self):
        md, source, ledger = self.custom_dialogue([('林岚', '对白', '他说“走吧”。')])
        self.assertTrue(self.run_case(md, source, ledger)['static_pass'])
        md = md.replace('自然说完。', '自然说完；“他说“走吧”。”是演绎说明中的引用。')
        self.assertTrue(self.run_case(md, source, ledger)['static_pass'])

    def test_colons_in_parenthetical_performance_notes(self):
        md,s,l=fixture()
        for header in ['林岚（0.2—1.8秒，语气：平静）说：',
                       '林岚 (0.2—1.8秒，读法: 自然(不抢话))说：']:
            case=md.replace('林岚在0.2—1.8秒说：',header)
            self.assertTrue(self.run_case(case,s,l)['static_pass'],self.run_case(case,s,l))

    def test_bare_new_speaker_and_same_line_extra_speech(self):
        md,s,l=fixture()
        self.assert_code(self.run_case(md.replace('- 落幅状态：','陌生人：“新增一句。”\n- 落幅状态：'),s,l),'dialogue_exact')
        line=next(x for x in md.splitlines() if x.startswith('林岚在'))
        self.assert_code(self.run_case(md.replace(line,line+' 陌生人说：“新增一句。”'),s,l),'dialogue_exact')

    def test_same_line_source_dialogue_and_timestamp_first(self):
        md,s,l=fixture()
        one=next(x for x in md.splitlines() if x.startswith('林岚在'))
        two=next(x for x in md.splitlines() if x.startswith('周远在'))
        case=md.replace(one+'\n'+two,one+' '+two)
        self.assertTrue(self.run_case(case,s,l)['static_pass'],self.run_case(case,s,l))
        case=md.replace(one,'0.2—1.8秒｜林岚 对白：“不来了。”自然说完。')
        self.assertTrue(self.run_case(case,s,l)['static_pass'],self.run_case(case,s,l))

    def test_attributed_quotes_inside_notes_are_not_extra_speech(self):
        md,s,l=fixture()
        suffix='\n演绎说明：“陌生人说：‘新增一句。’”只是引用示例。\n读法：“不来了。”应当自然。\n'
        case=md.replace('- 落幅状态：',suffix+'- 落幅状态：')
        self.assertTrue(self.run_case(case,s,l)['static_pass'],self.run_case(case,s,l))
        line=next(x for x in md.splitlines() if x.startswith('林岚在'))
        case=md.replace(line,line+' 演绎说明：“陌生人说：新增一句。”')
        self.assertTrue(self.run_case(case,s,l)['static_pass'],self.run_case(case,s,l))

    def test_ambiguous_quotes_produce_explicit_manual_notes(self):
        md,s,l=fixture()
        for extra in ['一个人 在背后低声回答：“新增一句。”',
                      '陌生人 对白：“未闭合。',
                      '陌生人（语气：平静：新句']:
            case=md.replace('- 落幅状态：',extra+'\n- 落幅状态：')
            result=self.run_case(case,s,l)
            self.assertIn('voice_parse_manual',[x['code'] for x in result['notes']])

    def test_markdown_bom_and_windows_newlines(self):
        md, source, ledger = fixture()
        self.assertTrue(self.run_case('\ufeff'+md.replace('\n', '\r\n'), source, ledger)['static_pass'])

    def test_cross_unit_split(self):
        md, source, ledger = self.custom_dialogue([('林岚', '对白', '不来了。')], True)
        start = md.index('### 生成单元 G1')
        unit = md[start:]
        first = unit.replace('：“不来了。”', '：“不来”')
        second = unit.replace('G1', 'G2').replace('S1-01', 'S1-02').replace('：“不来了。”', '：“了。”')
        md = md[:start].replace('成片总时长：6秒', '成片总时长：12秒').replace('生成单元数：1', '生成单元数：2').replace('成片镜头数：1', '成片镜头数：2') + first + '\n' + second
        ledger['delivery'] = [dict(id='U001', unit='G1', text='不来'), dict(id='U001', unit='G2', text='了。')]
        self.assertTrue(self.run_case(md, source, ledger)['static_pass'], self.run_case(md, source, ledger))
        self.assert_code(self.run_case(md.replace('：“了。”', '：“了”'), source, ledger), 'dialogue_exact')

    def test_split_allocation_can_mix_with_unsplit_utterance(self):
        md,source,ledger=fixture()
        start=md.index('### 生成单元 G1'); unit=md[start:]
        line=next(x for x in unit.splitlines() if x.startswith('周远在'))
        first=unit.replace('：“不来了。”','：“不来”').replace(line,'')
        second=unit.replace('G1','G2').replace('S1-01','S1-02').replace('：“不来了。”','：“了。”')
        md=md[:start].replace('成片总时长：6秒','成片总时长：12秒').replace('生成单元数：1','生成单元数：2').replace('成片镜头数：1','成片镜头数：2')+first+'\n'+second
        ledger['delivery']=[dict(id='U001',unit='G1',text='不来'),dict(id='U001',unit='G2',text='了。')]
        self.assertTrue(self.run_case(md,source,ledger)['static_pass'],self.run_case(md,source,ledger))
        self.assert_code(self.run_case(md.replace(line,''),source,ledger),'dialogue_exact')

    def test_cli_report_does_not_overwrite_input(self):
        md,s,l=fixture()
        import json
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'main.md').write_text(md,encoding='utf-8')
            (p/'source.txt').write_bytes(s)
            (p/'ledger.json').write_text(json.dumps(l,ensure_ascii=False),encoding='utf-8')
            cmd=[sys.executable,str(Path(v.__file__)),str(p/'main.md'),'--source',str(p/'source.txt'),'--ledger',str(p/'ledger.json')]
            run=subprocess.run(cmd+['--report',str(p/'source.txt')],capture_output=True)
            self.assertEqual(run.returncode,2)
            self.assertEqual((p/'source.txt').read_bytes(),s)
            run=subprocess.run(cmd+['--report',str(p/'report.json')],capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr)
            report=json.loads((p/'report.json').read_text(encoding='utf-8'))
            self.assertTrue(report['static_pass'])
            paths={'markdown':p/'main.md','source':p/'source.txt','ledger':p/'ledger.json'}
            for name,path in paths.items():
                self.assertEqual(report['input_sha256'][name],hashlib.sha256(path.read_bytes()).hexdigest())
            # An innocuous edit still invalidates the old report's fingerprint.
            before=report['input_sha256']['markdown']
            (p/'main.md').write_bytes((p/'main.md').read_bytes()+b'\n')
            self.assertNotEqual(before,hashlib.sha256((p/'main.md').read_bytes()).hexdigest())
            run=subprocess.run(cmd+['--report',str(p/'report.json')],capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr)
            current=json.loads((p/'report.json').read_text(encoding='utf-8'))
            self.assertNotEqual(before,current['input_sha256']['markdown'])
            self.assertEqual(current['input_sha256']['source'],report['input_sha256']['source'])
            self.assertEqual(current['input_sha256']['ledger'],report['input_sha256']['ledger'])
            # Different path names can still be the same input inode.
            hardlink=p/'linked-report.json'
            hardlink.hardlink_to(p/'source.txt')
            run=subprocess.run(cmd+['--report',str(hardlink)],capture_output=True)
            self.assertEqual(run.returncode,2,run.stderr)
            self.assertEqual((p/'source.txt').read_bytes(),s)

if __name__=='__main__':
    unittest.main()
