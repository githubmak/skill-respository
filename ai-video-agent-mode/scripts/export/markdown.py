"""Merged Markdown export - all shots in one file with scene grouping."""
import json, os, sys


def export(pkg_path, plan_path, md_dir, bn="prompt_package"):
    """Export all shots into a single merged .md file.
    
    Args:
        pkg_path: Path to director_pass.json (has items + merged_full_prompts)
        plan_path: Path to shot_plan.json
        md_dir: Output directory for the .md file
        bn: Base filename (without extension)
    """
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

    lines = []
    lines.append("# %s - 完整提示词包" % project_name)
    lines.append("")
    lines.append("> 画布/风格：%s" % (sp.get("canvas", "16:9") if "canvas" in sp else "16:9"))
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
                lines.append("- **景别**：%s" % ss["shot_size"])
                lines.append("- **机位**：%s" % ss["camera_position"])
                lines.append("- **运镜**：%s" % ss["camera"])
                lines.append("- **动作**：%s" % ss["character_action"])
                lines.append("- **灯光**：%s" % ss["lighting"])
                lines.append("- **落幅**：%s" % ss.get("end_state", ""))
                lines.append("")

            # Full merged prompt
            if sid in merged_map:
                lines.append("**完整提示词：**")
                lines.append("")
                lines.append("```")
                lines.append(merged_map[sid])
                lines.append("```")
                lines.append("")

            lines.append("---")
            lines.append("")

    # Write merged file
    os.makedirs(md_dir, exist_ok=True)
    out_path = os.path.join(md_dir, "%s.md" % bn)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("[MD] Merged file: %s (%d lines)" % (out_path, len(lines)))
    return 1  # One file produced


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("usage: markdown.py <pkg.json> <plan.json> <md_dir> [basename]")
        sys.exit(1)
    bn = sys.argv[4] if len(sys.argv) > 4 else "prompt_package"
    export(sys.argv[1], sys.argv[2], sys.argv[3], bn)