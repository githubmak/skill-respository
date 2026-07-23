"""Validate exported Markdown quality and encoding."""
import json
import os
import re
import sys

if not os.environ.get("PYTHONPYCACHEPREFIX") and not getattr(sys, "pycache_prefix", None):
    sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))
from pycache_policy import block_source_pycache_until_run_dir, ensure_pycache_prefix_from_path

block_source_pycache_until_run_dir()


MOJIBAKE_PATTERNS = ["�", "Ã", "Â", "å", "è", "é", "ç", "æ", "ï¼", "ã€"]
ENGINEERING_TERMS = [
    "JSON", "json", "schema", "field", "字段", "dB", "Hz", "fps", "XYZ",
    "coordinate", "prompt_package", "axis_start", "axis_end",
]
REQUIRED_LABELS = [
    "即梦操作卡", "生成规格", "主体与空间锁定", "主镜头连续规则", "子镜头组", "光照、声音与稳定约束", "负面提示词",
]
CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
LATIN_RE = re.compile(r"[A-Za-z]")


def validate(md_path, pkg_path=None, plan_path=None):
    ensure_pycache_prefix_from_path(md_path)
    issues = []
    text = _read_utf8(md_path, issues)
    if text is None:
        return issues

    for pattern in MOJIBAKE_PATTERNS:
        count = text.count(pattern)
        if count >= 3:
            issues.append(_issue("ENCODING_MOJIBAKE", "found %s x%d" % (pattern, count), "0"))

    chinese_count = len(CHINESE_RE.findall(text))
    latin_count = len(LATIN_RE.findall(text))
    if chinese_count < 100:
        issues.append(_issue("CHINESE_TOO_LOW", chinese_count, ">=100"))
    if chinese_count and latin_count / max(chinese_count, 1) > 0.25:
        issues.append(_issue("LATIN_RATIO_HIGH", "%.2f" % (latin_count / chinese_count), "<=0.25"))

    for label in REQUIRED_LABELS:
        if label not in text:
            issues.append(_issue("LABEL_MISSING", label, "present"))

    if "```" not in text:
        issues.append(_issue("FENCE_MISSING", "no code fence", "present"))

    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith("- **") and (stripped.endswith("：") or stripped.endswith(":")):
            issues.append(_issue("EMPTY_FIELD_LINE", stripped[:80], "field has content"))
            break

    for term in ENGINEERING_TERMS:
        if term in text and term not in ["字段"]:
            issues.append(_issue("ENGINEERING_TERM", term, "not in final MD"))

    if pkg_path:
        issues.extend(_validate_pkg(pkg_path))
    if pkg_path and plan_path:
        issues.extend(_cross_check_ids(text, pkg_path, plan_path))

    return issues


def _read_utf8(path, issues):
    if not os.path.exists(path):
        issues.append(_issue("MD_NOT_FOUND", path, "exists"))
        return None
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return f.read()
    except UnicodeDecodeError as exc:
        issues.append(_issue("UTF8_DECODE_FAILED", str(exc), "valid utf-8"))
        return None


def _validate_pkg(pkg_path):
    issues = []
    if not os.path.exists(pkg_path):
        return [_issue("PKG_NOT_FOUND", pkg_path, "exists")]
    try:
        with open(pkg_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as exc:
        return [_issue("PKG_JSON_PARSE_FAILED", str(exc), "valid json")]
    if set(data) != {"contract_version", "shots"}:
        issues.append(_issue("PKG_TOP_LEVEL_INVALID", sorted(data), ["contract_version", "shots"]))
    if not isinstance(data.get("shots"), list):
        issues.append(_issue("PKG_SHOTS_INVALID", type(data.get("shots")).__name__, "list"))
    for item in data.get("shots", []):
        for key in ["shot_id", "subshot_id", "duration", "full_prompt", "negative_prompt", "qa_metadata", "generation_control"]:
            if item.get(key) in (None, ""):
                issues.append(_issue("PKG_FIELD_EMPTY", "%s.%s" % (item.get("subshot_id", "?"), key), "non-empty"))
    return issues


def _cross_check_ids(text, pkg_path, plan_path):
    issues = []
    with open(pkg_path, "r", encoding="utf-8-sig") as f:
        pkg = json.load(f)
    with open(plan_path, "r", encoding="utf-8-sig") as f:
        plan = json.load(f)
    for shot in plan.get("shots", []):
        sid = shot.get("shot_id", "")
        if sid and sid not in text:
            issues.append(_issue("SHOT_ID_MISSING_IN_MD", sid, "present"))
        for ss in shot.get("subshots", []):
            ssid = ss.get("subshot_id", "")
            if ssid and ssid not in text:
                issues.append(_issue("SUBSHOT_ID_MISSING_IN_MD", ssid, "present"))
    pkg_ids = {item.get("subshot_id", "") for item in pkg.get("shots", [])}
    plan_ids = {ss.get("subshot_id", "") for shot in plan.get("shots", []) for ss in shot.get("subshots", [])}
    for ssid in sorted(plan_ids - pkg_ids):
        issues.append(_issue("SUBSHOT_ID_MISSING_IN_PKG", ssid, "present"))
    return issues


def _issue(check, got, expected):
    return {"check": check, "severity": "blocking", "got": got, "expected": expected}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: validate_markdown_export.py <file.md> [prompt_package.json] [shot_plan.json]")
        sys.exit(1)
    result = validate(
        sys.argv[1],
        sys.argv[2] if len(sys.argv) > 2 else None,
        sys.argv[3] if len(sys.argv) > 3 else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if not result else 1)
