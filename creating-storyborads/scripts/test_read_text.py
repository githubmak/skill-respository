import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("reader", Path(__file__).with_name("read_text.py"))
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


class ReadTextTests(unittest.TestCase):
    def test_exact_coverage_and_budgets(self):
        texts = ["", "\ufeff甲：你好。\r\n\r\n## 标题\r\n" * 50,
                 "超长段落😀" * 150, "甲\n" * 220, "甲\r" * 220,
                 "甲\r\n乙\r丙\n" * 100, "无尾换行\n第二段"]
        for text in texts:
            with self.subTest(text=text[:20]):
                ranges = reader.split_text(text, max_chars=80, max_lines=5)
                self.assertEqual("".join(text[a:b] for a, b in ranges), text)
                for a, b in ranges:
                    self.assertLessEqual(b - a, 80)
                    self.assertLessEqual(len(text[a:b].splitlines()), 5)
                    self.assertFalse(a > 0 and text[a-1:a+1] == "\r\n")

    def test_paragraph_boundary_preferred(self):
        text = "甲" * 35 + "\n\n" + "乙" * 70
        self.assertEqual(reader.split_text(text, 60, 100)[0], (0, 37))

    def test_hash_checks_actual_bytes_and_detects_edits(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "原文.txt"
            path.write_bytes("\ufeff甲\r\n乙".encode("utf-8"))
            text, digest, _ = reader.load_segments(path)
            self.assertEqual(text, "\ufeff甲\r\n乙")
            reader.load_segments(path, expected_sha=digest)
            path.write_bytes("\ufeff甲\n乙".encode("utf-8"))
            with self.assertRaisesRegex(ValueError, "版本已变化"):
                reader.load_segments(path, expected_sha=digest)

    def test_cli_emits_only_requested_segment_and_does_not_modify_source(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "文 本.txt"
            raw = ("甲" * 80 + "\n\n" + "乙" * 80).encode("utf-8")
            path.write_bytes(raw)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(reader.main([str(path), "--max-chars", "100"]), 0)
            output = out.getvalue()
            self.assertIn("甲" * 80, output)
            self.assertNotIn("乙" * 80, output)
            self.assertIn("NEXT:", output)
            self.assertEqual(path.read_bytes(), raw)
            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(reader.main([str(path), "--part", "999"]), 2)
                self.assertEqual(reader.main([str(path), "--expect-sha256", "wrong"]), 2)

    def test_bad_input_fails_without_replacement_or_silent_skipping(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.txt"
            path.write_bytes(b"\xff")
            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(reader.main([str(path)]), 2)
            with self.assertRaises(ValueError):
                reader.split_text("abc", max_chars=0)


if __name__ == "__main__":
    unittest.main()
