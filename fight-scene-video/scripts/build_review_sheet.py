#!/usr/bin/env python3
"""Build an ordered contact sheet and JSON manifest from review keyframes."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError as exc:
    raise SystemExit(
        "Pillow is required. Use the Codex workspace Python runtime returned by "
        "codex_app__load_workspace_dependencies, or install Pillow."
    ) from exc


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def natural_key(path: Path) -> list[object]:
    parts = re.split(r"(\d+(?:\.\d+)?)", path.name.lower())
    return [float(part) if re.fullmatch(r"\d+(?:\.\d+)?", part) else part for part in parts]


def find_font(size: int):
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def collect_images(input_dir: Path | None, files: list[Path]) -> list[Path]:
    candidates = list(files)
    if input_dir:
        if not input_dir.is_dir():
            raise ValueError(f"Input directory does not exist: {input_dir}")
        candidates.extend(path for path in input_dir.iterdir() if path.is_file())

    unique: dict[Path, None] = {}
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved.suffix.lower() in IMAGE_SUFFIXES:
            unique[resolved] = None

    images = sorted(unique, key=natural_key)
    if not images:
        raise ValueError("No supported image files were found.")
    missing = [path for path in images if not path.is_file()]
    if missing:
        raise ValueError(f"Image does not exist: {missing[0]}")
    return images


def fit_frame(image, width: int, height: int, background: tuple[int, int, int]):
    image = ImageOps.exif_transpose(image).convert("RGB")
    contained = ImageOps.contain(image, (width, height), method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), background)
    offset = ((width - contained.width) // 2, (height - contained.height) // 2)
    canvas.paste(contained, offset)
    return canvas


def build_sheet(args: argparse.Namespace) -> tuple[Path, Path]:
    images = collect_images(args.input_dir, args.files)
    columns = max(1, args.columns)
    rows = math.ceil(len(images) / columns)
    cell_width = args.width + args.padding * 2
    cell_height = args.height + args.label_height + args.padding * 2
    title_height = args.title_height if args.title else 0
    sheet = Image.new(
        "RGB",
        (columns * cell_width, title_height + rows * cell_height),
        (22, 24, 28),
    )
    draw = ImageDraw.Draw(sheet)
    label_font = find_font(args.font_size)
    title_font = find_font(args.title_font_size)

    if args.title:
        draw.rectangle((0, 0, sheet.width, title_height), fill=(13, 15, 18))
        draw.text((args.padding, 16), args.title, fill=(244, 246, 248), font=title_font)

    manifest_frames = []
    for index, path in enumerate(images):
        row, column = divmod(index, columns)
        x = column * cell_width
        y = title_height + row * cell_height
        frame_x = x + args.padding
        frame_y = y + args.padding

        with Image.open(path) as source:
            original_width, original_height = source.size
            frame = fit_frame(source, args.width, args.height, (5, 6, 8))
        sheet.paste(frame, (frame_x, frame_y))

        label_y = frame_y + args.height + 8
        label = f"{index:02d}  {path.name}"
        draw.text((frame_x, label_y), label, fill=(232, 235, 240), font=label_font)
        size_label = f"{original_width}x{original_height}"
        draw.text(
            (frame_x, label_y + args.font_size + 4),
            size_label,
            fill=(150, 158, 170),
            font=label_font,
        )

        manifest_frames.append(
            {
                "index": index,
                "file": str(path),
                "label": path.name,
                "width": original_width,
                "height": original_height,
            }
        )

    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="PNG", optimize=True)

    manifest = args.manifest.expanduser().resolve() if args.manifest else output.with_suffix(".json")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "title": args.title,
                "frame_count": len(images),
                "columns": columns,
                "sheet": str(output),
                "frames": manifest_frames,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return output, manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a fight-video review contact sheet from ordered image frames."
    )
    parser.add_argument("files", nargs="*", type=Path, help="Frame image files.")
    parser.add_argument("--input-dir", type=Path, help="Directory containing frame images.")
    parser.add_argument("--output", type=Path, default=Path("review-sheet.png"))
    parser.add_argument("--manifest", type=Path, help="Optional JSON manifest path.")
    parser.add_argument("--title", default="Fight Video Review Frames")
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--width", type=int, default=480)
    parser.add_argument("--height", type=int, default=270)
    parser.add_argument("--padding", type=int, default=14)
    parser.add_argument("--label-height", type=int, default=58)
    parser.add_argument("--title-height", type=int, default=68)
    parser.add_argument("--font-size", type=int, default=18)
    parser.add_argument("--title-font-size", type=int, default=28)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        output, manifest = build_sheet(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(output)
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
