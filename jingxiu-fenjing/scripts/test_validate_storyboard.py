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
主光设计5000—5500K，偏冷白窗光从左侧照入。
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
        for content in ['林岚与周远隔桌相对。','摄影机位于关系轴南侧。','主光设计5000—5500K，偏冷白窗光从左侧照入。','无对白。','周远持袋，林岚松手。']:
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


def project(music=False):
    block = fixture()
    if not music:
        block = block.replace('配乐：钢琴停奏，交还后结束。\n', '')
    return ("# 《交还》Seedance 独立直投版\n"
            "## 项目直投参数\n成片总时长：6秒，横屏。\n"
            "## 项目共用视觉规则\n写实质感，保留资产固有色。\n"
            + ("## 全局配音、配乐与声音规则\n钢琴主题，人物声音优先。\n" if music else "")
            + "## 全局正向提示词\n身份连续。\n"
            "## 全局负面提示词\n无肢体畸形。\n"
            "# 场景一｜书房·日\n"
            "## 场景摄影规则\n关系轴南侧，中等景深。\n"
            "## 场景光色与影调基线\n主光设计5000—5500K，偏冷白，中间调，柔和反差，暗部保留木纹。\n"
            "## 场景资产图提示词\n书桌临窗，保持材质。\n"
            "## 道具资产图提示词\n书袋，布质。\n"
            "## 场景空间位置关系\n两人隔桌相对。\n"
            "## Seedance 独立直投生成单元\n" + block)

class CurrentFormatTests(unittest.TestCase):
    def test_scoped_scene_without_project_header(self):
        text = '# 场景一' + project(False).split('# 场景一', 1)[1]
        self.assertEqual(v.validate(text), [])

    def test_current_music_and_detail(self):
        for music in [True, False]:
            for schema in ['auto', 'current']:
                self.assertEqual(v.validate(project(music), schema=schema), [])
    def test_each_scene_requires_own_rules(self):
        extra = project(False).split('# 场景一', 1)[1]
        extra = '# 场景二' + extra.replace('G1', 'G2').replace('S1-01', 'S2-01')
        extra = extra.replace('## 场景摄影规则\n关系轴南侧，中等景深。\n', '')
        text = project(False).replace('总时长：6秒', '总时长：12秒') + extra
        self.assertTrue(any('场景二' in e and '场景摄影规则' in e for e in v.validate(text)))
    def test_missing_and_empty_scene_light(self):
        text = project().replace('## 场景光色与影调基线', '## 光色备注')
        self.assertTrue(any('缺少场景栏目 场景光色与影调基线' in e for e in v.validate(text)))
        text = project().replace('主光设计5000—5500K，偏冷白，中间调，柔和反差，暗部保留木纹。', '')
        self.assertTrue(any('场景栏目为空 场景光色与影调基线' in e for e in v.validate(text)))
    def test_scene_order(self):
        text = project().replace('## 场景摄影规则', '## TEMP').replace('## 场景光色与影调基线', '## 场景摄影规则').replace('## TEMP', '## 场景光色与影调基线')
        self.assertTrue(any('场景栏目顺序' in e for e in v.validate(text)))
    def test_old_global_header_requires_migration(self):
        text = project().replace('项目共用视觉规则', '全局摄影规则')
        self.assertTrue(any('项目共用视觉规则' in e for e in v.validate(text)))
    def test_unit_light_is_local(self):
        text = project().replace('主光设计5000—5500K，偏冷白窗光从左侧照入。', '沿用本场。')
        self.assertTrue(any('G1：光影栏缺少' in e for e in v.validate(text)))
    def test_light_exceptions_and_locked_value(self):
        for light in ['主光锁定5000K，白光。', '纯色光为红光，仅照门边。', '无有效照明，完全黑暗。']:
            self.assertEqual(v.validate(project().replace('主光设计5000—5500K，偏冷白窗光从左侧照入。', light)), [])
    def test_music_header_requires_every_window_music(self):
        text = project(True).replace('配乐：钢琴停奏，交还后结束。', '')
        self.assertTrue(any('每个时间窗须写配乐状态' in e for e in v.validate(text)))
    def test_music_window_requires_project_music_header(self):
        text = project(False).replace('声音：布料接触声。', '声音：布料接触声。\n配乐：停奏。')
        self.assertTrue(any('配乐版缺少全局' in e for e in v.validate(text)))
    def test_generic_explicitly_preserves_locked_template(self):
        text = project(False).replace('项目共用视觉规则', '自定义视觉设定').replace('场景摄影规则', '自定义摄影设定')
        self.assertEqual(v.validate(text, schema='generic'), [])

if __name__ == '__main__':
    unittest.main()
