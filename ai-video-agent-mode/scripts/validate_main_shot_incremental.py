#!/usr/bin/env python3
"""Validate one completed main shot before the rest of its batch is finished."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from validate_composer_output import validate_composer_output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("batch_path")
    parser.add_argument("--run-dir")
    parser.add_argument("--shot-id", required=True)
    parser.add_argument("--report")
    args = parser.parse_args()
    run_dir = args.run_dir or _infer_run_dir(args.batch_path)
    report_path = args.report or (
        args.batch_path + "." + args.shot_id + ".incremental.validation.json"
    )
    return validate_composer_output(
        args.batch_path,
        run_dir,
        report_path,
        allow_incomplete=True,
        selected_shot_ids=[args.shot_id],
    )


def _infer_run_dir(batch_path):
    absolute = os.path.abspath(batch_path)
    marker = os.sep + ".cache" + os.sep
    return absolute.split(marker, 1)[0] if marker in absolute else os.path.dirname(absolute)


if __name__ == "__main__":
    raise SystemExit(main())
