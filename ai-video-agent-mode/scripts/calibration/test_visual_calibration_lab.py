#!/usr/bin/env python3
"""Independent regression for the offline real-video calibration sidecar."""

import json
import os
import shutil
import subprocess
import tempfile

from visual_calibration_lab import (
    CalibrationError,
    SCORE_FIELDS,
    finalize_case,
    prepare_case,
    promote_reports,
)


def _read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _metrics(path, drift=0.01):
    return {
        "path": os.path.abspath(path),
        "metrics": {
            "duration_seconds": 5.0,
            "source_width": 1920,
            "source_height": 1080,
            "sample_count": 18,
            "luminance_mean": 0.5,
            "luminance_drift": drift,
            "highlight_clipping_mean": 0.01,
            "highlight_clipping_max": 0.02,
            "shadow_crush_mean": 0.01,
            "shadow_crush_max": 0.02,
            "red_blue_balance_mean": 0.0,
            "red_blue_balance_drift": drift,
            "detail_energy_mean": 0.12,
            "detail_energy_flicker": drift,
            "frame_delta_mean": 0.08,
            "frame_delta_std": 0.01,
            "frame_delta_max": 0.12,
            "horizontal_edge_proxy_position_drift": drift,
        },
    }


def _fake_analyzer(paths, _sample_count):
    return [_metrics(path) for path in paths]


def _make_source_files(root):
    paths = {}
    contents = {
        "before.mp4": b"real-before-video-placeholder",
        "after.mp4": b"real-after-video-placeholder-with-different-content",
        "before.txt": b"baseline prompt",
        "after.txt": b"candidate prompt",
        "strategy.md": b"strategy-v1: per-shot light and motion curve",
    }
    for name, content in contents.items():
        path = os.path.join(root, name)
        with open(path, "wb") as handle:
            handle.write(content)
        paths[name] = path
    return paths


def _complete_case(root, sources, index, winner_generation="after"):
    case_dir = os.path.join(root, "case-%02d" % index)
    result = prepare_case(
        sources["before.mp4"],
        sources["after.mp4"],
        sources["before.txt"],
        sources["after.txt"],
        sources["strategy.md"],
        case_dir,
        "case-%02d" % index,
        "per-shot-light-motion-v1",
        "dialogue" if index % 2 else "exterior_action",
        "model-seed-set-a" if index % 2 else "model-seed-set-b",
        ["light_color_quality", "material_realism", "motion_liveness"],
    )
    review = _read(result["blind_review"])
    sealed = _read(result["sealed_mapping"])
    assert "mapping" not in review and "strategy_id" not in review
    assert {sealed["mapping"]["a"], sealed["mapping"]["b"]} == {"before", "after"}
    for label in ("a", "b"):
        generation = sealed["mapping"][label]
        base = 7 if generation == "before" else 8
        review["scores"][label] = {field: base for field in SCORE_FIELDS}
    review["blind_confirmed"] = True
    review["reviewer_id"] = "reviewer-%02d" % index
    review["winner"] = next(
        label for label, generation in sealed["mapping"].items()
        if generation == winner_generation
    )
    _write(result["blind_review"], review)
    report_path = os.path.join(case_dir, "calibration_report.json")
    report = finalize_case(
        result["blind_review"],
        result["sealed_mapping"],
        report_path,
        analyzer=_fake_analyzer,
    )
    assert report["evidence"]["winner_generation"] == winner_generation
    assert report["subjective"]["deltas"]["motion_liveness"] == 1
    return result, report_path


def main():
    swift_path = os.path.join(os.path.dirname(__file__), "visual_metrics.swift")
    swift = subprocess.run(
        ["/usr/bin/swift", swift_path, "--self-test"],
        text=True,
        capture_output=True,
    )
    assert swift.returncode == 0, swift.stderr
    assert json.loads(swift.stdout)["pass"] is True

    with tempfile.TemporaryDirectory(prefix="visual-calibration-") as root:
        sources = _make_source_files(root)
        first, first_report = _complete_case(root, sources, 1)

        incomplete = _read(first["blind_review"])
        incomplete["scores"]["a"]["motion_liveness"] = None
        incomplete_path = os.path.join(root, "incomplete_review.json")
        _write(incomplete_path, incomplete)
        try:
            finalize_case(
                incomplete_path,
                first["sealed_mapping"],
                os.path.join(root, "should-not-exist.json"),
                analyzer=_fake_analyzer,
            )
            raise AssertionError("incomplete blind review was accepted")
        except CalibrationError as exc:
            assert "motion_liveness" in str(exc)

        sealed = _read(first["sealed_mapping"])
        candidate_a = sealed["media"]["a"]["neutral_path"]
        with open(candidate_a, "ab") as handle:
            handle.write(b"tampered")
        try:
            finalize_case(
                first["blind_review"],
                first["sealed_mapping"],
                os.path.join(root, "tampered-report.json"),
                analyzer=_fake_analyzer,
            )
            raise AssertionError("tampered candidate was accepted")
        except CalibrationError as exc:
            assert "SHA256" in str(exc) or "不一致" in str(exc)
        source_generation = sealed["media"]["a"]["generation"]
        shutil.copyfile(sources[source_generation + ".mp4"], candidate_a)

        reports = [first_report]
        for index in range(2, 5):
            _, report_path = _complete_case(root, sources, index)
            reports.append(report_path)
        registry_path = os.path.join(root, "validated_registry.json")
        registry = promote_reports(reports, registry_path)
        assert len(registry["validated_strategies"]) == 1
        assert not registry["rejected_candidates"]
        assert registry["validated_strategies"][0]["after_win_rate"] == 1.0
        assert registry["auto_consumed_by_production"] is False

        tampered_report = _read(first_report)
        tampered_report["evidence"]["winner_generation"] = "before"
        tampered_report_path = os.path.join(root, "tampered-final-report.json")
        _write(tampered_report_path, tampered_report)
        try:
            promote_reports([tampered_report_path] + reports[1:], os.path.join(root, "bad.json"))
            raise AssertionError("tampered final report was accepted")
        except CalibrationError as exc:
            assert "完整性" in str(exc)

        low_reports = []
        for index in range(5, 9):
            _, report_path = _complete_case(root, sources, index, winner_generation="before")
            low_reports.append(report_path)
        rejected = promote_reports(low_reports, os.path.join(root, "rejected_registry.json"))
        assert not rejected["validated_strategies"]
        assert rejected["rejected_candidates"][0]["status"] == "insufficient_evidence"
        assert any("胜率" in reason for reason in rejected["rejected_candidates"][0]["reasons"])

    print("offline visual calibration sidecar regression passed")


if __name__ == "__main__":
    main()
