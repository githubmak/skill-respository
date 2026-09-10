#!/usr/bin/env python3
"""Count Unicode characters in one prompt and enforce an optional limit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--text", help="Prompt text to count.")
    source.add_argument("--file", type=Path, help="UTF-8 text file containing one prompt.")
    parser.add_argument("--limit", type=int, default=1024)
    args = parser.parse_args()

    if args.text is not None:
        prompt = args.text
    elif args.file is not None:
        prompt = args.file.read_text(encoding="utf-8")
    else:
        prompt = sys.stdin.read()

    prompt = prompt.rstrip("\r\n")
    count = len(prompt)
    status = "PASS" if count <= args.limit else "FAIL"
    print(f"{status}\tcharacters={count}\tlimit={args.limit}")
    return 0 if count <= args.limit else 1


if __name__ == "__main__":
    raise SystemExit(main())
