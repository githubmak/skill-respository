#!/usr/bin/env python3
"""Create a non-destructive field-level prompt repair preview artifact."""

import argparse
import json
import os

from pipeline_runtime import atomic_json
from production_intelligence import build_repair_preview


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("--field", action="append", default=[])
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    preview = build_repair_preview(args.before, args.after, args.field)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    atomic_json(args.out, preview)
    print(json.dumps(preview, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
