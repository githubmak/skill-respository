#!/usr/bin/env python3
"""Read one bounded, verbatim UTF-8 segment; never cache or infer read coverage."""

import argparse
from bisect import bisect_right
import hashlib
import json
from pathlib import Path
import re
import shlex
import sys

LINEBREAK = re.compile(r"\r\n|\r|\n")
NEWLINE = r"(?:\r\n|\r(?!\n)|(?<!\r)\n)"


def split_text(text, max_chars=6000, max_lines=100):
    """Return contiguous character ranges, preferring paragraph/line boundaries."""
    if max_chars < 1 or max_lines < 1:
        raise ValueError("分段字符数与行数必须为正数")
    ranges = []
    line_ends = [m.end() for m in LINEBREAK.finditer(text)]
    start = 0
    while start < len(text):
        limit = min(start + max_chars, len(text))
        boundary = bisect_right(line_ends, start) + max_lines - 1
        if boundary < len(line_ends):
            limit = min(limit, line_ends[boundary])
        # Never separate the two characters of a CRLF sequence.
        if limit < len(text) and text[limit - 1:limit + 1] == "\r\n":
            limit -= 1
        if limit <= start:
            raise ValueError("字符预算太小，无法完整容纳CRLF换行；请增大--max-chars")
        end = limit
        if limit < len(text):
            block = text[start:limit]
            boundaries = [m.end() for m in re.finditer(NEWLINE + r"[ \t]*" + NEWLINE, block)]
            boundaries += [m.start() for m in re.finditer(r"(?m)^#{1,6}[ \t]+", block)]
            useful = [n for n in boundaries if n >= len(block) / 2]
            if useful:
                end = start + max(useful)
            else:
                breaks = list(LINEBREAK.finditer(block))
                if breaks:
                    end = start + breaks[-1].end()
        ranges.append((start, end))
        start = end
    return ranges or [(0, 0)]


def load_segments(path, max_chars=6000, max_lines=100, expected_sha=None):
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha is not None and digest != expected_sha.lower():
        raise ValueError("文件版本已变化：SHA256不匹配；停止续读，请从第1段重新确认")
    # Keep BOM and CRLF: source character offsets must not be normalized.
    text = raw.decode("utf-8")
    return text, digest, split_text(text, max_chars, max_lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="UTF-8文本文件，不会修改")
    parser.add_argument("--part", type=int, default=1, help="读取第几段，从1开始")
    parser.add_argument("--max-chars", type=int, default=6000)
    parser.add_argument("--max-lines", type=int, default=100)
    parser.add_argument("--expect-sha256", help="续读时核对前一段报告的文件哈希")
    args = parser.parse_args(argv)
    try:
        path = args.path.resolve(strict=True)
        text, digest, ranges = load_segments(
            path, args.max_chars, args.max_lines, args.expect_sha256
        )
        if not 1 <= args.part <= len(ranges):
            raise ValueError(f"段号越界：文件共{len(ranges)}段，实际请求{args.part}")
        start, end = ranges[args.part - 1]
        line_ends = [m.end() for m in LINEBREAK.finditer(text)]
        meta = {
            "file": str(path), "sha256": digest,
            "part": args.part, "parts": len(ranges),
            "characters": len(text), "range_start": start, "range_end": end,
            "first_line": bisect_right(line_ends, start) + 1,
            "last_line": bisect_right(line_ends, max(start, end - 1)) + 1,
            "starts_mid_line": start > 0 and start not in line_ends,
            "ends_mid_line": end < len(text) and end not in line_ends,
            "reaches_eof": end == len(text),
            "note": "仅输出本段原文；到文件末尾不证明此前各段已读或已理解。",
        }
        print(json.dumps(meta, ensure_ascii=False))
        print("--- BEGIN VERBATIM TEXT ---")
        sys.stdout.write(text[start:end])
        print("\n--- END VERBATIM TEXT ---")
        if args.part < len(ranges):
            command = [
                "python3", str(Path(__file__).resolve()), str(path),
                "--part", str(args.part + 1),
                "--max-chars", str(args.max_chars),
                "--max-lines", str(args.max_lines), "--expect-sha256", digest,
            ]
            print("NEXT: " + shlex.join(command))
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"读取失败：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
