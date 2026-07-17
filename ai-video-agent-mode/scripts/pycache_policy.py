"""Runtime pycache policy for ai-video-agent-mode.

All generated Python bytecode must live under the current run/export directory,
never inside the skill source directory.
"""
import os
import sys


def block_source_pycache_until_run_dir():
    """Prevent local __pycache__ writes before the run directory is known."""
    if not os.environ.get("PYTHONPYCACHEPREFIX") and not getattr(sys, "pycache_prefix", None):
        sys.dont_write_bytecode = True


def ensure_pycache_prefix(run_dir):
    """Route pyc files to <run_dir>/.cache/pycache for this process."""
    if not run_dir:
        return None
    prefix = os.path.abspath(os.path.join(run_dir, ".cache", "pycache"))
    os.makedirs(prefix, exist_ok=True)
    os.environ["PYTHONPYCACHEPREFIX"] = prefix
    sys.pycache_prefix = prefix
    sys.dont_write_bytecode = False
    return prefix


def ensure_pycache_prefix_from_path(path):
    """Infer run_dir from a path under <run_dir>/.cache/... and apply policy."""
    run_dir = infer_run_dir(path)
    return ensure_pycache_prefix(run_dir) if run_dir else None


def infer_run_dir(path):
    if not path:
        return None
    current = os.path.abspath(path)
    if not os.path.isdir(current):
        current = os.path.dirname(current)
    parts = current.split(os.sep)
    if ".cache" in parts:
        idx = parts.index(".cache")
        if idx > 0:
            return os.sep.join(parts[:idx])
    return current

