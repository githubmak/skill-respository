#!/usr/bin/env python3
"""Record reviewed mannequin screenshots and promote clean spatial references."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import shutil
import struct
from pathlib import Path


SCHEMA_VERSION = 5
RENDER_BACKEND = "pyvista_vtk_offscreen"
RENDER_PROFILE = "proxy_v3_neutral"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DEFAULT_FRAME_CONTRACT = {"width": 1920, "height": 1080, "aspect": "16:9"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_size(path: Path) -> tuple[int, int]:
    """Read dimensions without adding an image-library dependency."""
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if data.startswith(b"\xff\xd8"):
        index = 2
        sof_markers = set(range(0xC0, 0xC4)) | set(range(0xC5, 0xC8)) | set(range(0xC9, 0xCC)) | set(range(0xCD, 0xD0))
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            index += 2
            if marker in {0xD8, 0xD9}:
                continue
            if index + 2 > len(data):
                break
            segment_length = struct.unpack(">H", data[index:index + 2])[0]
            if segment_length < 2 or index + segment_length > len(data):
                break
            if marker in sof_markers and segment_length >= 7:
                height, width = struct.unpack(">HH", data[index + 3:index + 7])
                return width, height
            index += segment_length
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP" and len(data) >= 30 and data[12:16] == b"VP8X":
        width = 1 + int.from_bytes(data[24:27], "little")
        height = 1 + int.from_bytes(data[27:30], "little")
        return width, height
    raise ValueError(f"screenshot is not a readable PNG/JPEG/WebP image: {path}")


def _staging_mannequin_directory(path: str | Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir() or resolved.name != "mannequin" or resolved.parent.name != "staging":
        raise ValueError("screenshot directory must be an existing staging/mannequin directory")
    return resolved


def record_review(
    render_report: str | Path,
    screenshot_dir: str | Path,
    decision: str,
    findings: list[str],
) -> dict:
    if decision not in {"PASS", "REVISE"}:
        raise ValueError("decision must be PASS or REVISE")
    report_path = Path(render_report).expanduser().resolve()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not report.get("pass"):
        raise ValueError("cannot review screenshots from a failed mannequin render")
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("mannequin render report schema is stale")
    if report.get("render_backend") != RENDER_BACKEND:
        raise ValueError("mannequin render report must come from the PyVista/VTK off-screen renderer")
    if report.get("render_profile") != RENDER_PROFILE:
        raise ValueError(f"mannequin render report must use render_profile {RENDER_PROFILE}")
    frame_contract = report.get("frame_contract") or DEFAULT_FRAME_CONTRACT
    expected_width = int(frame_contract.get("width", DEFAULT_FRAME_CONTRACT["width"]))
    expected_height = int(frame_contract.get("height", DEFAULT_FRAME_CONTRACT["height"]))
    if (
        expected_width <= 0
        or expected_height <= 0
        or expected_width * 9 != expected_height * 16
        or str(frame_contract.get("aspect", "")) != "16:9"
    ):
        raise ValueError("mannequin render report has an invalid 16:9 frame contract")
    directory = _staging_mannequin_directory(screenshot_dir)
    screenshot_artifacts: list[dict] = []
    seen_names: set[str] = set()

    outputs = report.get("outputs", [])
    if not outputs:
        raise ValueError("mannequin render report has no outputs")
    for output in outputs:
        if output.get("render_backend") != RENDER_BACKEND:
            raise ValueError("mannequin output backend does not match the report backend")
        views = output.get("views", [])
        if not views:
            raise ValueError("mannequin output has no camera views")
        for view in views:
            camera_index = view.get("camera_index")
            camera_label = view.get("camera_contract", {}).get("label", "")
            screenshots = view.get("screenshots", [])
            if not screenshots:
                raise ValueError(f"camera {camera_index} has no required screenshot mapping")
            required_modes = {(item.get("pose"), item.get("mode")) for item in screenshots}
            poses = {item.get("pose") for item in screenshots}
            if any((pose, mode) not in required_modes for pose in poses for mode in ("audit", "clean")):
                raise ValueError(f"camera {camera_index} requires audit and clean screenshots for every pose")
            for item in screenshots:
                if item.get("render_backend") != RENDER_BACKEND:
                    raise ValueError("screenshot mapping is not a PyVista/VTK direct-rendered image")
                filename = str(item.get("filename", "")).strip()
                if not filename or Path(filename).name != filename:
                    raise ValueError(f"invalid screenshot filename: {filename}")
                if filename in seen_names:
                    raise ValueError(f"duplicate screenshot filename: {filename}")
                seen_names.add(filename)
                path = directory / filename
                if not path.is_file() or path.stat().st_size == 0:
                    raise FileNotFoundError(str(path))
                if path.suffix.lower() not in IMAGE_EXTENSIONS:
                    raise ValueError(f"unsupported mannequin screenshot type: {path.suffix}")
                width, height = image_size(path)
                if (width, height) != (expected_width, expected_height):
                    raise ValueError(
                        f"screenshot must be {expected_width}x{expected_height} (16:9); got {width}x{height}: {path}"
                    )
                screenshot_artifacts.append({
                    "path": str(path),
                    "sha256": sha256_file(path),
                    "shot_id": item.get("shot_id"),
                    "physical_state_index": item.get("physical_state_index"),
                    "physical_phase": item.get("physical_phase", "static"),
                    "camera_index": camera_index,
                    "camera_label": camera_label,
                    "pose": item.get("pose"),
                    "pose_source": item.get("pose_source", "static"),
                    "mode": item.get("mode"),
                    "width": width,
                    "height": height,
                    "render_backend": item.get("render_backend"),
                })

    return {
        "pass": True,
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "shot_group": report.get("shot_group"),
        "frame_contract": frame_contract,
        "reference_role": "mannequin_spatial_action_reference",
        "generation_reference_allowed": decision == "PASS",
        "visual_review": decision,
        "findings": findings,
        "render_backend": RENDER_BACKEND,
        "render_profile": report["render_profile"],
        "renderer_versions": report.get("renderer_versions", {}),
        "screenshot_artifacts": screenshot_artifacts,
        "promotion_allowed": decision == "PASS",
        "review_scope": "model viewed every direct-rendered audit and clean image",
        "primary_storyboard_modified": False,
    }


def promote(review_path: str | Path, delivery_dir: str | Path, replace: bool = False) -> dict:
    review = json.loads(Path(review_path).expanduser().resolve().read_text(encoding="utf-8"))
    if review.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("mannequin review schema is stale")
    if review.get("visual_review") != "PASS" or not review.get("promotion_allowed"):
        raise ValueError("promotion requires visual_review PASS")
    if (
        review.get("reference_role") != "mannequin_spatial_action_reference"
        or review.get("generation_reference_allowed") is not True
    ):
        raise ValueError("review is not an approved mannequin spatial/action reference")
    destination_dir = Path(delivery_dir).expanduser().resolve()
    if "staging" in destination_dir.parts or "reports" in destination_dir.parts:
        raise ValueError("delivery directory cannot be inside staging or reports")
    destination_dir.mkdir(parents=True, exist_ok=True)
    promoted = []
    for item in review.get("screenshot_artifacts", []):
        if item.get("mode") != "clean":
            continue
        source = Path(item.get("path", "")).expanduser().resolve()
        if not source.is_file() or sha256_file(source) != item.get("sha256"):
            raise ValueError(f"reviewed screenshot changed after approval: {source}")
        destination = destination_dir / source.name
        if destination.exists() and not replace:
            raise FileExistsError(f"destination exists; use --replace: {destination}")
        shutil.copy2(source, destination)
        promoted.append({
            "path": str(destination),
            "sha256": sha256_file(destination),
            "shot_id": item.get("shot_id"),
            "physical_state_index": item.get("physical_state_index"),
            "physical_phase": item.get("physical_phase", "static"),
            "camera_index": item.get("camera_index"),
            "camera_label": item.get("camera_label"),
            "pose": item.get("pose"),
            "pose_source": item.get("pose_source", "static"),
            "reference_role": "mannequin_spatial_action_reference",
        })
    if not promoted:
        raise ValueError("review contains no clean mannequin screenshots to promote")
    return {
        "pass": True,
        "shot_group": review.get("shot_group"),
        "promoted": promoted,
        "visual_review": "PASS",
        "reference_role": "mannequin_spatial_action_reference",
        "generation_reference_allowed": True,
        "primary_storyboard_modified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    record = subparsers.add_parser("record")
    record.add_argument("--render-report", required=True)
    record.add_argument("--screenshot-dir", required=True)
    record.add_argument("--decision", choices=("PASS", "REVISE"), required=True)
    record.add_argument("--finding", action="append", default=[])
    record.add_argument("--review", required=True)
    promote_parser = subparsers.add_parser("promote")
    promote_parser.add_argument("--review", required=True)
    promote_parser.add_argument("--delivery-dir", required=True)
    promote_parser.add_argument("--replace", action="store_true")
    for command in (record, promote_parser):
        command.add_argument("--compact", action="store_true")
        command.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    if not args.compact:
        parser.error("--compact is required")
    try:
        if args.command == "record":
            result = record_review(args.render_report, args.screenshot_dir, args.decision, args.finding)
            review_path = Path(args.review).expanduser().resolve()
            review_path.parent.mkdir(parents=True, exist_ok=True)
            review_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            result = promote(args.review, args.delivery_dir, args.replace)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"pass": False, "error": str(exc), "primary_storyboard_modified": False}
    report_path = Path(args.report).expanduser().resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS" if result.get("pass") else "FAIL",
        "shot_group": result.get("shot_group"),
        "screenshot_count": len(result.get("screenshot_artifacts", [])),
        "promotion_count": len(result.get("promoted", [])),
        "report": str(report_path),
    }, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
