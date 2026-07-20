"""generate_shotplan.py - Phase 1 shot plan generation from source script.
Usage: python generate_shotplan.py <source.txt> <output_dir> [--config config.json] [--max-dur 15]

Reads project-specific rules (characters, action keywords) from project_config.json.
No hardcoded project data. Auto-detection via detect_source_rules.py feeds the config.
"""
import json, os, re, sys

def generate(source_path, output_dir, config_path=None, max_shot_duration=15):
    sys.path.insert(0, os.path.dirname(__file__))
    from build_shotplan import split_dialogue

    # Load config if provided, else use defaults
    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8-sig") as f:
            cfg = json.load(f)
    else:
        cfg_path = os.path.join(output_dir, "project_config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
        else:
            cfg = {}

    source_rules = cfg.get("source_rules", {})
    characters_list = source_rules.get("characters", [])
    action_kw = source_rules.get("action_keywords", [])
    scene_pattern = source_rules.get("scene_header_pattern", r"^\d+-\d+")

    with open(source_path, "r", encoding="utf-8") as f:
        text = f.read()
    lines = text.strip().split("\n")

    scenes, current_scene = [], None
    scene_char_map = {}  # scene_name -> [chars]
    dialogue_counter, dialogue_map, beats = 1, {}, []

    for line in lines:
        line = line.strip()
        if not line: continue

        # Scene header detection using config pattern
        m = re.match(scene_pattern, line)
        if m:
            if current_scene:
                scenes.append(current_scene)
            # Extract scene name (rest of line after pattern match)
            name = line[m.end():].strip()
            scene_id = m.group(1) if m.lastindex else m.group(0)
            # Build scene char map: extract chars separated by multiple spaces
            scene_chars_list = [c.strip() for c in __import__("re").split(r'\s{2,}', name) if c.strip()]
            current_scene = {"id": scene_id, "name": name if name else scene_id}
            if scene_chars_list:
                scene_char_map[name] = scene_chars_list
            continue

        # Skip character list lines
        if re.match(r"^人物[\uff1a:]", line):
            continue

        # Action lines (△ prefix or 动作：prefix)
        if line.startswith("\u25b3"):
            beats.append({
                "type": "action",
                "text": re.sub(r"^\u25b3[\uff1a:]?\s*", "", line),
                "scene": current_scene["name"] if current_scene else ""
            })
            continue
        if line.startswith("\u52a8\u4f5c\uff1a"):
            beats.append({
                "type": "action",
                "text": line[3:].strip(),
                "scene": current_scene["name"] if current_scene else ""
            })
            continue

        # Dialogue detection
        dm = re.match(r"^([^\uff1a:]+?)(\uff08([^\uff09]*)\uff09)?[\uff1a:](.+)", line)
        if dm:
            speaker = dm.group(1).strip()
            tone = dm.group(3) or ""
            content = dm.group(4).strip()

            # Check if this is actually an action line (config-driven keyword match)
            is_action = bool(action_kw) and any(kw in line for kw in action_kw)
            oral = ["我", "你", "啦", "啊", "吗", "吧", "!", "?", "~"]
            if is_action and not any(kw in content for kw in oral):
                beats.append({
                    "type": "action",
                    "text": line,
                    "scene": current_scene["name"] if current_scene else ""
                })
                continue

            is_narr = bool(tone and ("OS" in tone or "\u5185\u5fc3\u72ec\u767d" in tone))
            segments = split_dialogue(content, max_chars_per_segment=50)
            entries = {}
            for i, (seg, dur) in enumerate(segments):
                k = f"D{dialogue_counter + i}"
                entries[k] = seg
            for k, v in entries.items():
                dialogue_map[k] = v
            refs = list(entries.keys())
            beats.append({
                "type": "narration" if is_narr else "dialogue",
                "speaker": speaker,
                "text": content,
                "tone": tone,
                "refs": refs,
                "scene": current_scene["name"] if current_scene else ""
            })
            dialogue_counter += len(entries)
            continue

    if current_scene:
        scenes.append(current_scene)

    # Merge adjacent same-speaker beats
    merged = []
    for beat in beats:
        if beat["type"] == "action":
            merged.append(beat)
            continue
        if (merged and merged[-1]["type"] == beat["type"]
                and merged[-1].get("speaker") == beat.get("speaker")
                and merged[-1].get("scene") == beat.get("scene")):
            merged[-1]["refs"].extend(beat["refs"])
        else:
            merged.append(beat)

    # Generate shots with character detection
    shots = []
    for beat in merged:
        beat_chars = []
        full_text = beat.get("text", "")
        tone = beat.get("tone", "")
        speaker = beat.get("speaker", "")
        scene_name = beat.get("scene", "")

        if beat["type"] in ("dialogue", "narration"):
            if speaker:
                beat_chars.append(speaker)
            if tone:
                for c in characters_list:
                    if c in tone and c not in beat_chars:
                        beat_chars.append(c)
        else:
            for c in characters_list:
                if c in full_text and c not in beat_chars:
                    beat_chars.append(c)
            if not beat_chars:
                beat_chars = [characters_list[0]] if characters_list else ["\u4e3b\u89d2"]

        shot_num = len(shots) + 1
        refs = beat.get("refs", [])

        if beat["type"] == "action":
            dur = max(2.0, min(6.0, len(full_text) / 5))
            shots.append({
                "shot_id": f"S1-{shot_num:02d}",
                "scene": scene_name,
                "core_action": full_text[:50],
                "subshots": [{
                    "subshot_id": f"S1-{shot_num:02d}-01",
                    "duration": round(dur, 1),
                    "characters": beat_chars,
                    "dialogue_refs": [],
                    "base_action": full_text[:80]
                }]
            })
            continue

        subshots = []
        for j, ref in enumerate(refs):
            seg_text = dialogue_map.get(ref, "")
            seg_dur = max(2.5, min(5.0, len(seg_text) / 4.5 + 0.5))
            subshots.append({
                "subshot_id": f"S1-{shot_num:02d}-{j + 1:02d}",
                "duration": round(seg_dur, 1),
                "characters": beat_chars,
                "dialogue_refs": [ref],
                "base_action": seg_text[:80]
            })
        shots.append({
            "shot_id": f"S1-{shot_num:02d}",
            "scene": scene_name,
            "core_action": f"{speaker}:{full_text[:30]}",
            "subshots": subshots
        })

    draft = {
        "project_name": cfg.get("project_name", ""),
        "canvas": cfg.get("canvas", "16:9"),
        "visual_style": cfg.get("visual_style", ""),
        "max_shot_duration": max_shot_duration,
        "scenes": [{"id": s["id"], "name": s["name"]} for s in scenes],
        "dialogue_map": dialogue_map,
        "shots": shots,
        "total_shots": len(shots)
    }

    draft_path = os.path.join(output_dir, "shot_plan.draft.json")
    os.makedirs(os.path.dirname(draft_path), exist_ok=True)
    with open(draft_path, "w", encoding="utf-8") as f:
        json.dump(draft, f, ensure_ascii=False, indent=2)
    return draft_path, len(shots), sum(len(s["subshots"]) for s in shots)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: generate_shotplan.py <source.txt> <output_dir> [--config config.json] [--max-dur 15]")
        sys.exit(1)
    config = None
    max_dur = 15
    args = sys.argv[3:]
    i = 0
    while i < len(args):
        if args[i] == "--config" and i + 1 < len(args):
            config = args[i + 1]
            i += 2
        elif args[i].startswith("--max-dur"):
            max_dur = int(args[i].split("=")[-1]) if "=" in args[i] else int(args[i + 1])
            i += 2 if "=" not in args[i] else 1
        else:
            i += 1
    path, shots, subshots = generate(sys.argv[1], sys.argv[2], config, max_dur)
    print(f"[SHOTPLAN] Generated: {path} ({shots} shots, {subshots} subshots)")
