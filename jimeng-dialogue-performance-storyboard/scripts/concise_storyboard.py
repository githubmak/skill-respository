#!/usr/bin/env python3
"""Create an optional shot/direct-prompt view without changing the primary Markdown."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


SHOT_RE = re.compile(r"【镜号】\s*\n(?P<id>.*?)(?=\n【)", re.S)
DIRECT_RE = re.compile(r"【画面描述｜直接复制】\s*\n(?P<text>.*?)(?=\n【)", re.S)


def extract(text):
    blocks = re.split(r"(?=【镜号】)", text)
    rows = []
    for block in blocks:
        shot = SHOT_RE.search(block)
        direct = DIRECT_RE.search(block)
        if shot and direct:
            rows.append((shot.group("id").strip(), direct.group("text").strip()))
    return rows


def render(source_path, rows):
    lines = ["# 即梦分镜简版", "", "- 主文件：`%s`" % Path(source_path).name, "- 本文件仅用于快速阅读；投喂与验证以主文件为准。", ""]
    for shot, direct in rows:
        lines.extend(["## " + shot, "", direct, ""])
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output", nargs="?")
    args = parser.parse_args(argv)
    source = Path(args.source).expanduser().resolve()
    output = Path(args.output).expanduser().resolve() if args.output else source.with_suffix(".concise.md")
    rows = extract(source.read_text(encoding="utf-8-sig"))
    if not rows:
        raise SystemExit("no storyboard shot/direct-prompt pairs found")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(source, rows), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
