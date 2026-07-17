"""Merged Markdown export - all shots in one file with scene grouping."""
import json, os, sys

SCRIPT_DIR = os.path.dirname(os.path.dirname(__file__))
if not os.environ.get("PYTHONPYCACHEPREFIX") and not getattr(sys, "pycache_prefix", None):
    sys.dont_write_bytecode = True
sys.path.insert(0, SCRIPT_DIR)
from pycache_policy import block_source_pycache_until_run_dir, ensure_pycache_prefix_from_path
from validate_markdown_export import validate as validate_markdown_export

block_source_pycache_until_run_dir()


REQUIRED_MD_FIELDS = [
    ("景别", "shot_size"),
    ("机位", "camera_position"),
    ("运镜", "camera"),
    ("轴线与空间", "axis_space"),
    ("可见人物", "visible_characters"),
    ("动作过程", "character_action"),
    ("台词与声音", "dialogue_audio"),
    ("灯光", "lighting"),
    ("出入画", "char_entry_exit"),
    ("落幅", "end_state"),
]


def export(pkg_path, plan_path, md_dir, bn="prompt_package"):
    """Export all shots into a single merged .md file.
    
    Args:
        pkg_path: Path to director_pass.json (has items + merged_full_prompts)
        plan_path: Path to shot_plan.json
        md_dir: Output directory for the .md file
        bn: Base filename (without extension)
    """
    ensure_pycache_prefix_from_path(pkg_path)
    with open(pkg_path, "r", encoding="utf-8-sig") as f:
        pp = json.load(f)
    with open(plan_path, "r", encoding="utf-8-sig") as f:
        sp = json.load(f)

    items = pp.get("items", [])
    merged = pp.get("merged_full_prompts", [])
    project_name = sp.get("project_name", "Untitled")

    # Group subshots by shot_id
    shot_subshots = {}
    for item in items:
        sid = item["shot_id"]
        shot_subshots.setdefault(sid, []).append(item)

    # Build scene -> shot map
    scene_shots = {}
    for shot in sp.get("shots", []):
        scene = shot.get("scene", "?")
        scene_shots.setdefault(scene, []).append(shot["shot_id"])

    # Build merged map
    merged_map = {m["shot_id"]: m["full_prompt"] for m in merged}
    scene_lookup = {}
    for shot in sp.get("shots", []):
        scene_lookup[shot.get("shot_id", "")] = shot.get("scene", "?")

    lines = []
    lines.append("# %s - 完整提示词包" % project_name)
    lines.append("")
    lines.append("> 画布/风格：%s" % (sp.get("canvas", "16:9") if "canvas" in sp else "16:9"))
    lines.append("> 镜头数：%d；子镜头数：%d" % (len(scene_lookup), len(items)))
    lines.append("")
    lines.append("---")
    lines.append("")

    shot_counter = 0
    for scene, sids in scene_shots.items():
        lines.append("## 场景：%s" % scene)
        lines.append("")

        for sid in sids:
            shot_counter += 1
            subshots = shot_subshots.get(sid, [])
            dur = sum(ss.get("duration", 0) for ss in subshots)

            lines.append("### %s (%.1fs)" % (sid, dur))
            lines.append("")

            for i, ss in enumerate(subshots):
                lines.append("#### 子镜头 %s" % ss["subshot_id"])
                lines.append("")
                for label, key in REQUIRED_MD_FIELDS:
                    val = _format_value(ss.get(key, ""))
                    if val:
                        lines.append("- **%s**：%s" % (label, val))
                lines.append("")

            # Full merged prompt
            if sid in merged_map:
                lines.append("**完整提示词：**")
                lines.append("")
                lines.append("```")
                lines.append(merged_map[sid])
                lines.append("```")
                lines.append("")
            else:
                lines.append("> ⚠ 缺少 merged_full_prompts 中的完整提示词。")
                lines.append("")

            lines.append("---")
            lines.append("")

    # Write merged file
    os.makedirs(md_dir, exist_ok=True)
    out_path = os.path.join(md_dir, "%s.md" % bn)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    issues = validate_markdown_text("\n".join(lines), pp, sp)
    issues.extend(validate_markdown_export(out_path, pkg_path, plan_path))
    print("[MD] Merged file: %s (%d lines)" % (out_path, len(lines)))
    if issues:
        print("[MD][WARN] %d issue(s): %s" % (len(issues), issues[:5]))
    else:
        print("[MD] quality check PASS")
    return 1  # One file produced


def validate_markdown_text(text, prompt_package, shot_plan):
    """Lightweight export-level MD QA."""
    issues = []
    items = prompt_package.get("items", [])
    merged = prompt_package.get("merged_full_prompts", [])
    shot_ids = [shot.get("shot_id", "") for shot in shot_plan.get("shots", [])]
    subshot_ids = [item.get("subshot_id", "") for item in items]
    merged_ids = {item.get("shot_id", "") for item in merged}

    for sid in shot_ids:
        if "### %s " % sid not in text and "### %s(" % sid not in text:
            issues.append("missing shot heading: %s" % sid)
        if sid not in merged_ids:
            issues.append("missing merged prompt: %s" % sid)
    for ssid in subshot_ids:
        if "#### 子镜头 %s" % ssid not in text:
            issues.append("missing subshot heading: %s" % ssid)
    for label, _key in REQUIRED_MD_FIELDS[:8]:
        if "**%s**" % label not in text:
            issues.append("missing field label: %s" % label)
    if "```" not in text:
        issues.append("missing fenced full prompt")
    if "负面提示词" not in text:
        issues.append("missing negative prompt")
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith("- **") and (stripped.endswith("：") or stripped.endswith(":")):
                issues.append("empty action-like line: %s" % line[:80])
                break
    return issues


def _format_value(value):
    if isinstance(value, (list, tuple)):
        return "；".join(str(v) for v in value if str(v).strip())
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value or "").strip()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("usage: markdown.py <pkg.json> <plan.json> <md_dir> [basename]")
        sys.exit(1)
    bn = sys.argv[4] if len(sys.argv) > 4 else "prompt_package"
    export(sys.argv[1], sys.argv[2], sys.argv[3], bn)
