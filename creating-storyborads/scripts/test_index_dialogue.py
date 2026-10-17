import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('indexer',Path(__file__).with_name('index_dialogue.py'))
i=importlib.util.module_from_spec(spec)
spec.loader.exec_module(i)

class IndexTests(unittest.TestCase):
    def test_exact_unicode_and_crlf(self):
        source='甲：好。\r\n乙OS：走吧。'.encode()
        rows=[dict(id='U001',speaker='甲',kind='对白',text='好。'),dict(id='U002',speaker='乙',kind='OS',text='走吧。')]
        ledger,contexts=i.build(source,rows,music=False,max_unit_seconds=8)
        self.assertFalse(ledger['music'])
        self.assertEqual(contexts[1]['line'],2)
        for row in ledger['utterances']:
            self.assertEqual(source.decode()[row['source_start']:row['source_end']],row['text'])
    def test_original_repetition_requires_explicit_occurrences(self):
        source='甲：好。\n乙：好。'.encode()
        row=dict(id='U001',speaker='甲',kind='对白',text='好。')
        with self.assertRaises(ValueError): i.build(source,[row])
        text=source.decode()
        rows=[dict(row,source_start=text.index('好。')),dict(row,id='U002',speaker='乙',source_start=text.rindex('好。'))]
        ledger,_=i.build(source,rows)
        self.assertEqual(len(ledger['utterances']),2)
    def test_missing_or_reversed_text_fails(self):
        with self.assertRaises(ValueError): i.build(b'', [dict(id='U001',speaker='甲',kind='对白',text='好。')])
        source='甲：好。乙：再见。'.encode()
        with self.assertRaises(ValueError):
            i.build(source,[dict(id='U001',speaker='乙',kind='对白',text='再见。'),dict(id='U002',speaker='甲',kind='对白',text='好。')])
if __name__=='__main__': unittest.main()
