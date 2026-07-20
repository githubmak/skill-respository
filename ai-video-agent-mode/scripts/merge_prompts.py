"""Merge all prompt packages into a single unified output."""
import json, os, sys, re, re


def run(export_dir):
    """Merge all .prompt_package.json files from composer cache.

    Scans .cache/composer/ for all prompt packages, merges them into
    a single merged.json with items sorted by shot_id and a
    merged_full_prompts array keyed by shot_id.

    Args:
        export_dir: Run export directory (contains .cache/)

    Returns:
        Merged data dict, or None if no prompts found
    """
    composer_dir = os.path.join(export_dir, ".cache", "composer")
    if not os.path.isdir(composer_dir):
        print("[MERGE] No composer cache found")
        return None

    all_items = []
    shot_map = {}

    for fn in sorted(os.listdir(composer_dir)):
        if not (fn.endswith(".prompt_package.json") or fn == "prompt_package.json" or fn == "merged.prompt_package.json"):
            continue
        fp = os.path.join(composer_dir, fn)
        try:
            with open(fp, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            print("[MERGE] WARN: Skipping unreadable %s" % fn)
            continue

        items = data.get("items", [])
        all_items.extend(items)

        for item in items:
            sid = item.get("shot_id", "?")
            if sid not in shot_map:
                shot_map[sid] = []
            shot_map[sid].append(item)

    if not all_items:
        print("[MERGE] No items found")
        return None

    # Build merged_full_prompts (one per shot_id)
    # Phase 7: convert 【板块N-标题】 to **标题** section headers
    for item in all_items:
        fp = item.get("full_prompt", "")
        fp = re.sub(r'【板块\d+-(\S+)】\s*', r'\n**\1**\n', fp)
        fp = re.sub(r'【板块\d+[^】]*】\s*', '', fp)
        item["full_prompt"] = fp

    merged_full_prompts = []
    for sid in sorted(shot_map.keys()):
        subshots = shot_map[sid]
        combined = "\n\n---\n\n".join(ss.get("full_prompt", "") for ss in subshots)
        total_dur = sum(ss.get("duration", 0) for ss in subshots)
        merged_full_prompts.append({
            "shot_id": sid,
            "duration": total_dur,
            "duration_sec": total_dur,
            "full_prompt": combined,
        })

    result = {
        "items": all_items,
        "merged_full_prompts": merged_full_prompts,
    }

    out_dir = os.path.join(export_dir, ".cache", "editor")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "merged.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("[MERGE] Merged %d items into %d shot prompts" % (len(all_items), len(merged_full_prompts)))
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: merge_prompts.py <export_dir>")
        sys.exit(1)
    run(sys.argv[1])

