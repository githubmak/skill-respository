"""generate_shotplan.py - Phase 1 shot plan generation from source script.
Usage: python3 generate_shotplan.py <source.txt> <output_dir> [--config config.json] [--max-dur N]

Reads project-specific rules (characters, action keywords) from project_config.json.
No hardcoded project data. Auto-detection via detect_source_rules.py feeds the config.
"""
import json, os, re, sys

def generate(source_path, output_dir, config_path=None, max_shot_duration=None):
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

    if max_shot_duration is None:
        max_shot_duration = cfg.get("max_shot_duration")
    if not isinstance(max_shot_duration, (int, float)) or isinstance(max_shot_duration, bool) or max_shot_duration < 2.5:
        raise ValueError("max_shot_duration must be user-confirmed in project_config.json or passed with --max-dur")
    max_shot_duration = float(max_shot_duration)

    source_rules = cfg.get("source_rules", {})
    characters_list = source_rules.get("characters", [])
    action_kw = source_rules.get("action_keywords", [])
    scene_pattern = source_rules.get("scene_header_pattern", r"^\d+-\d+")

    with open(source_path, "r", encoding="utf-8") as f:
        text = f.read()
    lines = text.strip().split("\n")

    scenes, current_scene = [], None
    scene_char_map = {}  # scene_name -> [chars]
    dialogue_counter, dialogue_map, dialogue_event_map, dialogue_duration_map, beats = 1, {}, {}, {}, []

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

            tone_upper = tone.upper()
            if "OS" in tone_upper or "\u5185\u5fc3\u72ec\u767d" in tone or "\u5185\u5fc3" in tone:
                speech_kind = "OS"
            elif "OV" in tone_upper or "\u65c1\u767d" in tone or speaker == "\u65c1\u767d":
                speech_kind = "OV"
            else:
                speech_kind = "\u53f0\u8bcd"
            is_narr = speech_kind in ("OS", "OV")
            segments = split_dialogue(content, max_seconds=max_shot_duration, reserve_seconds=0.8)
            entries = {}
            for i, (seg, dur) in enumerate(segments):
                k = f"D{dialogue_counter + i}"
                entries[k] = seg
                dialogue_duration_map[k] = dur
            for k, v in entries.items():
                dialogue_map[k] = v
                dialogue_event_map[k] = {
                    "ref": k,
                    "kind": speech_kind,
                    "speaker": speaker,
                    "text": v,
                    "source_tone": tone,
                }
            for ref, seg in entries.items():
                beats.append({
                    "type": "narration" if is_narr else "dialogue",
                    "speaker": speaker,
                    "text": seg,
                    "tone": tone,
                    "refs": [ref],
                    "speech_duration": dialogue_duration_map[ref],
                    "scene": current_scene["name"] if current_scene else ""
                })
            dialogue_counter += len(entries)
            continue

    if current_scene:
        scenes.append(current_scene)

    # Pack adjacent dialogue turns into one actual generation unit when they
    # form one scene-local interaction and fit the user-confirmed duration.
    # Narration/OV/OS remains separate because it has a different lip-sync
    # boundary. Actions remain explicit Orchestrator beats.
    merged = _pack_interaction_beats(beats, max_shot_duration)

    # Generate shots with character detection
    shots = []
    for beat in merged:
        beat_chars = []
        full_text = beat.get("text", "")
        tone = beat.get("tone", "")
        speaker = beat.get("speaker", "")
        scene_name = beat.get("scene", "")

        if beat["type"] in ("dialogue", "narration", "dialogue_group"):
            for turn in beat.get("turns", [beat]):
                turn_speaker = turn.get("speaker", "")
                turn_tone = turn.get("tone", "")
                if turn_speaker and turn_speaker not in beat_chars:
                    beat_chars.append(turn_speaker)
                if turn_tone:
                    for c in characters_list:
                        if c in turn_tone and c not in beat_chars:
                            beat_chars.append(c)
        else:
            for c in characters_list:
                if c in full_text and c not in beat_chars:
                    beat_chars.append(c)
            if _has_group_reaction(full_text):
                group_name = _group_character_name(characters_list)
                if group_name and group_name not in beat_chars:
                    beat_chars.append(group_name)
            if not beat_chars:
                beat_chars = [characters_list[0]] if characters_list else ["\u4e3b\u89d2"]

        shot_num = len(shots) + 1
        refs = beat.get("refs", [])

        if beat["type"] == "action":
            dur = max(2.0, min(max_shot_duration, len(full_text) / 5))
            shots.append({
                "shot_id": f"S1-{shot_num:02d}",
                "scene": scene_name,
                "core_action": full_text,
                "subshots": [{
                    "subshot_id": f"S1-{shot_num:02d}-01",
                    "duration": round(dur, 1),
                    "characters": beat_chars,
                    "dialogue_refs": [],
                    "base_action": full_text
                }]
            })
            continue

        seg_dur = _interaction_duration(beat.get("turns", [beat]))
        if seg_dur > max_shot_duration + 1e-6:
            raise ValueError(
                "packed interaction exceeds user max_shot_duration: %s=%gs"
                % ("/".join(refs), seg_dur)
            )
        turn_summaries = [
            "%s%s" % ((turn.get("speaker", "") + "：") if turn.get("speaker") else "", turn.get("text", ""))
            for turn in beat.get("turns", [beat])
        ]
        subshots = [{
            "subshot_id": f"S1-{shot_num:02d}-01",
            "duration": round(seg_dur, 1),
            "characters": beat_chars,
            "dialogue_refs": refs,
            "base_action": "；".join(turn_summaries)[:160]
        }]
        shots.append({
            "shot_id": f"S1-{shot_num:02d}",
            "scene": scene_name,
            "core_action": "连续互动：" + "；".join(turn_summaries)[:120],
            "subshots": subshots
        })

    over_limit = [
        (shot.get("shot_id"), sum(float(ss.get("duration", 0) or 0) for ss in shot.get("subshots", [])))
        for shot in shots
        if sum(float(ss.get("duration", 0) or 0) for ss in shot.get("subshots", [])) > max_shot_duration + 1e-6
    ]
    if over_limit:
        raise ValueError(
            "generated main shot exceeds user max_shot_duration; Orchestrator must split: %s"
            % ", ".join("%s=%gs" % pair for pair in over_limit)
        )

    draft = {
        "project_name": cfg.get("project_name", ""),
        "canvas": cfg.get("canvas", "16:9"),
        "visual_style": cfg.get("visual_style", ""),
        "max_shot_duration": max_shot_duration,
        "scenes": [{"id": s["id"], "name": s["name"]} for s in scenes],
        "dialogue_map": dialogue_map,
        "dialogue_events": dialogue_event_map,
        "shots": shots,
        "total_shots": len(shots)
    }

    draft_path = os.path.join(output_dir, "shot_plan.draft.json")
    os.makedirs(os.path.dirname(draft_path), exist_ok=True)
    with open(draft_path, "w", encoding="utf-8") as f:
        json.dump(draft, f, ensure_ascii=False, indent=2)
    return draft_path, len(shots), sum(len(s["subshots"]) for s in shots)


def _has_group_reaction(text):
    text = str(text or "")
    return any(kw in text for kw in ["所有人", "众人", "几人", "成员", "几道视线", "视线同时", "集体", "每一张面孔", "室内"])


def _group_character_name(characters):
    for name in characters or []:
        if any(kw in str(name) for kw in ["其他所有人", "众人", "成员", "其余几人"]):
            return name
    return "其他所有人"


def _interaction_duration(turns, reserve_seconds=0.8, turn_pause=0.35):
    turns = list(turns or [])
    speech = sum(float(turn.get("speech_duration", 0) or 0) for turn in turns)
    return round(max(2.5, speech + reserve_seconds + max(0, len(turns) - 1) * turn_pause), 1)


def _pack_interaction_beats(beats, max_shot_duration):
    packed = []
    group = []

    def flush():
        nonlocal group
        if not group:
            return
        refs = [ref for turn in group for ref in turn.get("refs", [])]
        packed.append({
            "type": "dialogue_group" if len(group) > 1 else group[0].get("type", "dialogue"),
            "scene": group[0].get("scene", ""),
            "speaker": group[0].get("speaker", ""),
            "tone": group[0].get("tone", ""),
            "text": "".join(turn.get("text", "") for turn in group),
            "refs": refs,
            "turns": list(group),
        })
        group = []

    for beat in beats:
        if beat.get("type") != "dialogue":
            flush()
            packed.append(beat)
            continue
        if group and beat.get("scene", "") != group[0].get("scene", ""):
            flush()
        candidate = group + [beat]
        if group and _interaction_duration(candidate) > max_shot_duration + 1e-6:
            flush()
            candidate = [beat]
        if _interaction_duration(candidate) > max_shot_duration + 1e-6:
            raise ValueError(
                "single dialogue semantic unit exceeds user-confirmed max_shot_duration: %s"
                % beat.get("text", "")
            )
        group = candidate
    flush()
    return packed


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: generate_shotplan.py <source.txt> <output_dir> [--config config.json] [--max-dur N]")
        sys.exit(1)
    config = None
    max_dur = None
    args = sys.argv[3:]
    i = 0
    while i < len(args):
        if args[i] == "--config" and i + 1 < len(args):
            config = args[i + 1]
            i += 2
        elif args[i].startswith("--max-dur"):
            max_dur = float(args[i].split("=")[-1]) if "=" in args[i] else float(args[i + 1])
            i += 2 if "=" not in args[i] else 1
        else:
            i += 1
    path, shots, subshots = generate(sys.argv[1], sys.argv[2], config, max_dur)
    print(f"[SHOTPLAN] Generated: {path} ({shots} shots, {subshots} subshots)")
