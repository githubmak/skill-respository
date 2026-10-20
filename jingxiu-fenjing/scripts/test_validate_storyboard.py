"""Regression checks for content gaps and preservation of accepted input layouts."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('refinement_validator', Path(__file__).with_name('validate_storyboard.py'))
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

def fixture():
    return '''### 生成单元 G1 ｜时长：6秒｜承载：镜头 S1-01｜交还
- 起幅与连续性：
林岚与周远隔桌相对。
- 摄影与构图：
摄影机位于关系轴南侧。
- 光影、环境色彩与材质：
窗光从左侧照入。
- 画面与表演时间线：
0.0—6.0秒｜S1-01｜50mm 中景｜固定
林岚交还书袋，周远接住。
声音：布料接触声。
配乐：钢琴停奏，交还后结束。
- 台词与声音层次：
无对白。
- 落幅状态：
周远持袋，林岚松手。
'''

class RegressionTests(unittest.TestCase):
    def test_valid_block(self):
        self.assertEqual(v.validate(fixture()), [])
    def test_empty_picture(self):
        self.assertTrue(any('画面/表演' in e for e in v.validate(fixture().replace('林岚交还书袋，周远接住。',''))))
    def test_empty_sound(self):
        for text in ['声音：', '声音：\n配乐：停奏。']:
            self.assertTrue(any('实际声音' in e for e in v.validate(fixture().replace('声音：布料接触声。',text))))
    def test_empty_fields(self):
        for content in ['林岚与周远隔桌相对。','摄影机位于关系轴南侧。','窗光从左侧照入。','无对白。','周远持袋，林岚松手。']:
            self.assertTrue(any('字段为空' in e for e in v.validate(fixture().replace(content,''))))
    def test_mapping(self):
        self.assertTrue(any('承载镜号与' in e for e in v.validate(fixture().replace('承载：镜头 S1-01','承载：镜头 S1-02'))))
    def test_actor_movement_cannot_replace_camera(self):
        text=fixture().replace('｜固定','｜切到林岚').replace('林岚交还书袋，周远接住。','林岚推开书袋，周远拉住书袋。')
        self.assertTrue(any('运镜或固定方式' in e for e in v.validate(text)))
    def test_camera_in_body(self):
        text=fixture().replace('｜固定','｜交还').replace('林岚交还书袋','摄影机固定观察。林岚交还书袋')
        self.assertEqual(v.validate(text),[])
    def test_inline_picture_and_sound(self):
        text=fixture().replace('｜固定\n林岚交还书袋，周远接住。\n声音：','｜固定，林岚交还书袋，周远接住。声音：')
        self.assertEqual(v.validate(text),[])
    def test_inline_sound_is_not_picture(self):
        text=fixture().replace('｜固定\n林岚交还书袋，周远接住。\n声音：','｜固定，声音：')
        self.assertTrue(any('画面/表演' in e for e in v.validate(text)))
    def test_total_title_aliases(self):
        for label in ['成片总时长','实际总时长','成片时长','总时长']:
            text=label+'：6秒\n'+fixture()
            self.assertEqual(v.validate(text),[])
            self.assertTrue(any('总时长与' in e for e in v.validate(text.replace('：6秒','：7秒',1))))

    def test_nested_music_preserved(self):
        text=fixture().replace('声音：布料接触声。\n配乐：','声音：布料接触声。配乐：')
        self.assertEqual(v.validate(text),[])
    def test_bom_and_crlf(self):
        self.assertEqual(v.validate('\ufeff'+fixture().replace('\n','\r\n')),[])
    def test_invalid_limit(self):
        for value in [float('nan'),float('inf'),0,-1]:
            self.assertTrue(v.validate(fixture(),max_unit_seconds=value))
    def test_no_borrowing_from_next_scene(self):
        text=fixture().replace('周远持袋，林岚松手。','')+'# 场景二｜花园\n## 场景资产图提示词\n花园。\n'
        self.assertTrue(any('字段为空 落幅状态' in e for e in v.validate(text)))

if __name__ == '__main__':
    unittest.main()
