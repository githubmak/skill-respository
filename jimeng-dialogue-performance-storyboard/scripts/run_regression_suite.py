#!/usr/bin/env python3
"""Run every deterministic jimeng storyboard regression on all platforms."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time


SCRIPT_DIR = Path(__file__).resolve().parent
TEST_SCRIPTS = (
    "test_validate_storyboard.py",
    "test_incremental_validate.py",
    "test_source_gate.py",
    "test_runtime_tools.py",
    "test_seedance_target.py",
    "test_review_manifest.py",
    "test_render_blocking_reference.py",
)


def _run(name: str, command: list[str]) -> dict:
    started = time.time()
    completed = subprocess.run(command, text=True, capture_output=True)
    return {
        "name": name,
        "pass": completed.returncode == 0,
        "returncode": completed.returncode,
        "elapsed_seconds": round(time.time() - started, 3),
        "stdout_tail": completed.stdout[-3000:],
        "stderr_tail": completed.stderr[-3000:],
        "command": command,
    }


def main() -> int:
    steps = [
        _run(Path(script).stem, [sys.executable, str(SCRIPT_DIR / script)])
        for script in TEST_SCRIPTS
    ]
    steps.append(_run(
        "review_video_self_test",
        [sys.executable, str(SCRIPT_DIR / "review_video.py"), "--self-test"],
    ))
    result = {"pass": all(step["pass"] for step in steps), "steps": steps}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
