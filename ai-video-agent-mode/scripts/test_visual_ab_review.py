#!/usr/bin/env python3
"""Regression for real-file blind A/B evidence validation."""

import os
import tempfile

from validate_visual_ab_review import summarize


def main():
    with tempfile.TemporaryDirectory(prefix="visual-ab-review-") as root:
        for name in ("a.mp4", "b.mp4"):
            with open(os.path.join(root, name), "wb") as handle:
                handle.write(b"test-video-evidence")
        scores = {field: 8 for field in (
            "prompt_fidelity", "composition_depth", "motion_stability", "emotion_readability",
            "skin_tone_cleanliness", "artifact_control", "continuity",
        )}
        case = {
            "case_id": "mixed-light-face-01", "video_a": "a.mp4", "video_b": "b.mp4",
            "blind_confirmed": True, "reviewer_id": "reviewer-01", "winner": "b",
            "sealed_mapping": {"a": "before", "b": "after"},
            "prompt_before_sha256": "a" * 64, "prompt_after_sha256": "b" * 64,
            "scores": {"a": dict(scores), "b": dict(scores, skin_tone_cleanliness=9)},
        }
        result = summarize({"cases": [case]}, root)
        assert result["pass"] and result["after_wins"] == 1
        os.remove(os.path.join(root, "b.mp4"))
        assert not summarize({"cases": [case]}, root)["pass"]
    print("visual A/B review validator regression passed")


if __name__ == "__main__":
    main()
