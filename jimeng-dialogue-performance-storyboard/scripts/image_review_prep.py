#!/usr/bin/env python3
"""Prepare low-context image evidence before any original-resolution review."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def _dimensions(path: Path) -> tuple[int | None, int | None]:
    """Read dimensions without decoding pixels when macOS sips is available."""
    sips = shutil.which("sips")
    if sips:
        completed = subprocess.run(
            [sips, "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
            capture_output=True, text=True, check=False,
        )
        values: list[int] = []
        for line in completed.stdout.splitlines():
            if ":" not in line:
                continue
            value = line.rsplit(":", 1)[1].strip()
            if value.isdigit():
                values.append(int(value))
        if len(values) >= 2:
            return values[-2], values[-1]
    return None, None


def prepare(directory: str | Path, output_dir: str | Path, max_size: int = 320) -> dict:
    source_dir = Path(directory).expanduser().resolve()
    thumb_dir = Path(output_dir).expanduser().resolve()
    if not source_dir.is_dir():
        raise FileNotFoundError(str(source_dir))
    thumb_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(source_dir.glob("*.png"))
    records = []
    sips = shutil.which("sips")
    magick = shutil.which("magick") or shutil.which("convert")
    for source in files:
        width, height = _dimensions(source)
        thumb = thumb_dir / source.name
        method = "metadata_only"
        if sips:
            completed = subprocess.run(
                [sips, "-Z", str(max_size), str(source), "--out", str(thumb)],
                capture_output=True, text=True, check=False,
            )
            if completed.returncode == 0 and thumb.is_file():
                method = "sips"
        elif magick:
            completed = subprocess.run(
                [magick, str(source), "-thumbnail", f"{max_size}x{max_size}", str(thumb)],
                capture_output=True, text=True, check=False,
            )
            if completed.returncode == 0 and thumb.is_file():
                method = "imagemagick"
        records.append({
            "source": str(source),
            "thumbnail": str(thumb) if thumb.is_file() else None,
            "width": width,
            "height": height,
            "method": method,
        })
    return {
        "pass": True,
        "source_directory": str(source_dir),
        "thumbnail_directory": str(thumb_dir),
        "image_count": len(records),
        "thumbnail_count": sum(item["thumbnail"] is not None for item in records),
        "records": records,
        "original_resolution_review": "only_after_thumbnail_suspect",
        "primary_output_modified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-size", type=int, default=320)
    parser.add_argument("--report")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)
    if not args.compact or not args.report:
        parser.error("legacy image-review output is disabled; --compact and --report are required")
    try:
        result = prepare(args.directory, args.output_dir, args.max_size)
    except (OSError, ValueError) as exc:
        result = {"pass": False, "error": str(exc), "primary_output_modified": False}
    if args.report:
        report = Path(args.report).expanduser().resolve()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.compact:
        print(json.dumps({
            "status": "PASS" if result.get("pass") else "FAIL",
            "image_count": result.get("image_count", 0),
            "thumbnail_count": result.get("thumbnail_count", 0),
            "thumbnail_directory": result.get("thumbnail_directory"),
            "report": str(Path(args.report).expanduser().resolve()) if args.report else None,
        }, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
