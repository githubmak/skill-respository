#!/usr/bin/env python3
"""Cross-platform objective video metrics backed by FFmpeg/FFprobe."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys


ANALYZER_VERSION = "ffmpeg-rgb24-v1"
MAX_FRAME_WIDTH = 96
MAX_FRAME_HEIGHT = 54


class MetricError(RuntimeError):
    pass


def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _standard_deviation(values):
    if len(values) <= 1:
        return 0.0
    average = _mean(values)
    return math.sqrt(_mean([(value - average) ** 2 for value in values]))


def _rounded(value):
    scaled = value * 1_000_000
    rounded = math.floor(scaled + 0.5) if scaled >= 0 else math.ceil(scaled - 0.5)
    return rounded / 1_000_000


def _frame_stats(frame):
    width = frame["width"]
    height = frame["height"]
    luminance = frame["luminance"]
    count = len(luminance)
    if not count:
        return {
            "luminance_mean": 0.0,
            "highlight_clipping": 0.0,
            "shadow_crush": 0.0,
            "red_blue_balance": 0.0,
            "detail_energy": 0.0,
            "horizontal_edge_position": 0.0,
        }

    highlights = sum(value >= 0.96 for value in luminance)
    shadows = sum(value <= 0.04 for value in luminance)
    detail_sum = 0.0
    detail_count = 0
    row_edges = [0.0] * height
    if width > 1 and height > 1:
        for y in range(height):
            for x in range(width):
                index = y * width + x
                if x > 0:
                    detail_sum += abs(luminance[index] - luminance[index - 1])
                    detail_count += 1
                if y > 0:
                    edge = abs(luminance[index] - luminance[index - width])
                    detail_sum += edge
                    detail_count += 1
                    row_edges[y] += edge
    strongest_row = max(range(height), key=row_edges.__getitem__) if height else 0
    edge_position = strongest_row / (height - 1) if height > 1 else 0.0
    return {
        "luminance_mean": _mean(luminance),
        "highlight_clipping": highlights / count,
        "shadow_crush": shadows / count,
        "red_blue_balance": frame["red_blue_balance"],
        "detail_energy": detail_sum / detail_count if detail_count else 0.0,
        "horizontal_edge_position": edge_position,
    }


def _frame_delta(first, second):
    if first["width"] != second["width"] or first["height"] != second["height"]:
        return None
    return _mean([abs(a - b) for a, b in zip(first["luminance"], second["luminance"])])


def _read_ppm(payload):
    index = 0

    def token():
        nonlocal index
        while index < len(payload):
            if payload[index] == 35:
                while index < len(payload) and payload[index] not in (10, 13):
                    index += 1
            elif payload[index] in b" \t\r\n":
                index += 1
            else:
                break
        start = index
        while index < len(payload) and payload[index] not in b" \t\r\n":
            index += 1
        if start == index:
            raise MetricError("invalid PPM header")
        return payload[start:index]

    if token() != b"P6":
        raise MetricError("FFmpeg did not return a binary PPM frame")
    try:
        width = int(token())
        height = int(token())
        maximum = int(token())
    except ValueError as exc:
        raise MetricError("invalid PPM dimensions") from exc
    if maximum != 255 or width <= 0 or height <= 0:
        raise MetricError("unsupported PPM frame")
    if index >= len(payload) or payload[index] not in b" \t\r\n":
        raise MetricError("missing PPM pixel separator")
    if payload[index:index + 2] == b"\r\n":
        index += 2
    else:
        index += 1

    expected = width * height * 3
    pixels = payload[index:index + expected]
    if len(pixels) != expected:
        raise MetricError("incomplete PPM pixel payload")
    luminance = []
    red_blue_sum = 0.0
    for offset in range(0, len(pixels), 3):
        red = pixels[offset] / 255.0
        green = pixels[offset + 1] / 255.0
        blue = pixels[offset + 2] / 255.0
        luminance.append(0.2126 * red + 0.7152 * green + 0.0722 * blue)
        red_blue_sum += red - blue
    return {
        "width": width,
        "height": height,
        "luminance": luminance,
        "red_blue_balance": red_blue_sum / (width * height),
    }


def _resolve_tool(env_name, command_name, sibling_of=None):
    configured = os.environ.get(env_name, "").strip()
    if configured:
        resolved = os.path.abspath(os.path.expanduser(configured))
        if os.path.isfile(resolved):
            return resolved
        raise MetricError(f"{env_name} does not point to a file: {resolved}")
    found = shutil.which(command_name)
    if found:
        return found
    for candidate in _common_install_candidates(command_name):
        if os.path.isfile(candidate):
            return candidate
    if sibling_of:
        suffix = ".exe" if os.name == "nt" else ""
        sibling = os.path.join(os.path.dirname(sibling_of), command_name + suffix)
        if os.path.isfile(sibling):
            return sibling
    raise MetricError(
        f"{command_name} was not found; install FFmpeg or set {env_name} to its executable"
    )


def _common_install_candidates(command_name):
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            local_app_data = str(Path.home() / "AppData" / "Local")
        return [
            os.path.join(
                local_app_data,
                "Programs",
                "ffmpeg",
                "bin",
                command_name + ".exe",
            )
        ]
    if sys.platform == "darwin":
        return [
            os.path.join(prefix, "bin", command_name)
            for prefix in ("/opt/homebrew", "/usr/local", "/opt/local")
        ]
    return []


def resolve_tools():
    ffmpeg = _resolve_tool("AI_VIDEO_FFMPEG", "ffmpeg")
    ffprobe = _resolve_tool("AI_VIDEO_FFPROBE", "ffprobe", sibling_of=ffmpeg)
    return ffmpeg, ffprobe


def _run(command, timeout_seconds=60):
    try:
        return subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MetricError(f"media tool failed: {exc}") from exc


def _probe_video(path, ffprobe):
    command = [
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries",
        "stream=width,height,duration:stream_tags=rotate:stream_side_data=rotation:format=duration",
        "-of", "json",
        path,
    ]
    proc = _run(command)
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()
        raise MetricError(f"FFprobe failed: {detail}")
    try:
        payload = json.loads(proc.stdout.decode("utf-8"))
        stream = payload["streams"][0]
        width = int(stream["width"])
        height = int(stream["height"])
        duration = float(stream.get("duration") or payload.get("format", {}).get("duration"))
    except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise MetricError("FFprobe returned incomplete video metadata") from exc
    if not math.isfinite(duration) or duration <= 0 or width <= 0 or height <= 0:
        raise MetricError("video duration or dimensions are invalid")

    rotation = stream.get("tags", {}).get("rotate", 0)
    for side_data in stream.get("side_data_list", []):
        if "rotation" in side_data:
            rotation = side_data["rotation"]
            break
    try:
        rotation = int(float(rotation)) % 360
    except (TypeError, ValueError):
        rotation = 0
    if rotation in (90, 270):
        width, height = height, width
    return duration, width, height


def _decode_frame(path, seconds, ffmpeg):
    scale = (
        f"scale={MAX_FRAME_WIDTH}:{MAX_FRAME_HEIGHT}:"
        "force_original_aspect_ratio=decrease:flags=bilinear"
    )
    command = [
        ffmpeg,
        "-nostdin",
        "-v", "error",
        "-i", path,
        "-ss", f"{seconds:.9f}",
        "-map", "0:v:0",
        "-frames:v", "1",
        "-vf", scale,
        "-f", "image2pipe",
        "-vcodec", "ppm",
        "pipe:1",
    ]
    proc = _run(command)
    if proc.returncode != 0 or not proc.stdout:
        return None
    try:
        return _read_ppm(proc.stdout)
    except MetricError:
        return None


def analyze_video(path, samples=18, tools=None):
    absolute_path = str(Path(path).expanduser().resolve())
    if not os.path.isfile(absolute_path):
        raise MetricError(f"video does not exist: {absolute_path}")
    if not 4 <= samples <= 120:
        raise MetricError("--samples must be between 4 and 120")
    ffmpeg, ffprobe = tools or resolve_tools()
    duration, source_width, source_height = _probe_video(absolute_path, ffprobe)
    frames = []
    for index in range(samples):
        seconds = duration * (index + 0.5) / samples
        frame = _decode_frame(absolute_path, seconds, ffmpeg)
        if frame is not None:
            frames.append(frame)
    if len(frames) < max(3, samples // 2):
        raise MetricError(f"too few decodable sample frames: {len(frames)}/{samples}")

    stats = [_frame_stats(frame) for frame in frames]
    deltas = []
    for first, second in zip(frames, frames[1:]):
        delta = _frame_delta(first, second)
        if delta is not None:
            deltas.append(delta)
    luminance = [item["luminance_mean"] for item in stats]
    highlights = [item["highlight_clipping"] for item in stats]
    shadows = [item["shadow_crush"] for item in stats]
    color_balance = [item["red_blue_balance"] for item in stats]
    detail = [item["detail_energy"] for item in stats]
    horizontal_edge = [item["horizontal_edge_position"] for item in stats]
    return {
        "path": absolute_path,
        "metrics": {
            "duration_seconds": _rounded(duration),
            "source_width": source_width,
            "source_height": source_height,
            "sample_count": len(frames),
            "luminance_mean": _rounded(_mean(luminance)),
            "luminance_drift": _rounded(_standard_deviation(luminance)),
            "highlight_clipping_mean": _rounded(_mean(highlights)),
            "highlight_clipping_max": _rounded(max(highlights, default=0.0)),
            "shadow_crush_mean": _rounded(_mean(shadows)),
            "shadow_crush_max": _rounded(max(shadows, default=0.0)),
            "red_blue_balance_mean": _rounded(_mean(color_balance)),
            "red_blue_balance_drift": _rounded(_standard_deviation(color_balance)),
            "detail_energy_mean": _rounded(_mean(detail)),
            "detail_energy_flicker": _rounded(_standard_deviation(detail)),
            "frame_delta_mean": _rounded(_mean(deltas)),
            "frame_delta_std": _rounded(_standard_deviation(deltas)),
            "frame_delta_max": _rounded(max(deltas, default=0.0)),
            "horizontal_edge_proxy_position_drift": _rounded(
                _standard_deviation(horizontal_edge)
            ),
        },
    }


def self_test():
    width = 12
    height = 8
    first_values = [0.2] * (width * height)
    second_values = list(first_values)
    for y in range(3, height):
        for x in range(width):
            first_values[y * width + x] = 0.8
    for y in range(4, height):
        for x in range(width):
            second_values[y * width + x] = 1.0
    first = {
        "width": width,
        "height": height,
        "luminance": first_values,
        "red_blue_balance": 0.0,
    }
    second = {
        "width": width,
        "height": height,
        "luminance": second_values,
        "red_blue_balance": 0.0,
    }
    stats_a = _frame_stats(first)
    stats_b = _frame_stats(second)
    delta = _frame_delta(first, second) or 0.0
    checks = {
        "highlight_increase": stats_b["highlight_clipping"] > stats_a["highlight_clipping"],
        "edge_proxy_moves": (
            stats_a["horizontal_edge_position"] != stats_b["horizontal_edge_position"]
        ),
        "frame_delta_positive": delta > 0,
    }
    ppm = _read_ppm(b"P6\n2 1\n255\n" + bytes([255, 0, 0, 0, 0, 255]))
    checks["ppm_rgb24_decode"] = (
        ppm["width"] == 2
        and ppm["height"] == 1
        and len(ppm["luminance"]) == 2
        and abs(ppm["red_blue_balance"]) < 1e-12
    )
    return {"pass": all(checks.values()), "checks": checks}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--samples", type=int, default=18)
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)
    if args.self_test:
        result = self_test()
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result["pass"] else 1
    if not args.paths:
        print(json.dumps({"pass": False, "videos": [], "errors": ["provide at least one video path"]}))
        return 1
    if not 4 <= args.samples <= 120:
        print(json.dumps({"pass": False, "videos": [], "errors": ["--samples must be between 4 and 120"]}))
        return 1

    videos = []
    errors = []
    try:
        tools = resolve_tools()
    except MetricError as exc:
        tools = None
        errors.append(str(exc))
    if tools:
        for path in args.paths:
            try:
                videos.append(analyze_video(path, args.samples, tools=tools))
            except MetricError as exc:
                errors.append(f"{path}: {exc}")
    payload = {
        "pass": not errors,
        "analyzer_version": ANALYZER_VERSION,
        "videos": videos,
        "errors": errors,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
