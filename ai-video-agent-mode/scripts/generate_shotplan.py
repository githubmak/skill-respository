"""generate_shotplan.py - Orchestrator shot-plan generation from source script.
Usage: python3 generate_shotplan.py <source.txt> <output_dir> [--config config.json] [--max-dur N]

Reads project-specific rules (characters, action keywords) from project_config.json.
No hardcoded project data. Auto-detection via detect_source_rules.py feeds the config.
"""
import json, os, re, sys

def generate(source_path, output_dir, config_path=None, max_shot_duration=None):
    sys.path.insert(0, os.path.dirname(__file__))
    from build_shotplan import split_dialogue
    from validate_durations import _estimate_action_seconds, _estimate_dialogue_seconds

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
    lines = text.splitlines()

    scenes, current_scene = [], None
    scene_char_map = {}  # scene_name -> [chars]
    dialogue_counter, dialogue_map, dialogue_event_map, dialogue_duration_map, beats = 1, {}, {}, {}, []
    source_units = []

    for line_number, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line: continue
        source_id = "SRC%04d" % (len(source_units) + 1)
        source_unit = {
            "source_id": source_id,
            "source_path": os.path.abspath(source_path),
            "line": line_number,
            "type": "unclassified",
            "scene": current_scene["name"] if current_scene else "",
            "text": line,
        }
        source_units.append(source_unit)

        # Scene header detection using config pattern
        m = _match_scene_header(line, scene_pattern)
        if m:
            source_unit["type"] = "scene_header"
            if current_scene:
                scenes.append(current_scene)
            # Extract scene name (rest of line after pattern match)
            name = line[m.end():].strip()
            scene_id = m.group(1) if m.lastindex else m.group(0)
            # Build scene char map: extract chars separated by multiple spaces
            scene_chars_list = [c.strip() for c in __import__("re").split(r'\s{2,}', name) if c.strip()]
            current_scene = {"id": scene_id, "name": name if name else scene_id}
            source_unit["scene"] = current_scene["name"]
            if scene_chars_list:
                scene_char_map[name] = scene_chars_list
            continue

        # Skip character list lines
        if re.match(r"^人物[\uff1a:]", line):
            source_unit["type"] = "character_list"
            continue

        # Action lines (△ prefix or 动作：prefix)
        if line.startswith("\u25b3"):
            source_unit["type"] = "action"
            beats.append({
                "type": "action",
                "text": re.sub(r"^\u25b3[\uff1a:]?\s*", "", line),
                "scene": current_scene["name"] if current_scene else "",
                "source_ids": [source_id],
            })
            continue
        if line.startswith("\u52a8\u4f5c\uff1a"):
            source_unit["type"] = "action"
            beats.append({
                "type": "action",
                "text": line[3:].strip(),
                "scene": current_scene["name"] if current_scene else "",
                "source_ids": [source_id],
            })
            continue

        # Dialogue detection
        dm = re.match(r"^([^\uff1a:]+?)(\uff08([^\uff09]*)\uff09)?[\uff1a:](.+)", line)
        if dm:
            source_unit["type"] = "dialogue"
            speaker = dm.group(1).strip()
            tone = dm.group(3) or ""
            content = dm.group(4).strip()

            # Colons also introduce timestamps, URLs, camera directions and
            # state labels. Only treat the line as dialogue when its prefix is
            # a known character or an explicit OS/OV marker.
            if not _looks_like_dialogue_prefix(speaker, tone, content, characters_list):
                source_unit["type"] = "action"
                beats.append({
                    "type": "action", "text": line,
                    "scene": current_scene["name"] if current_scene else "",
                    "source_ids": [source_id],
                })
                continue

            # Check if this is actually an action line (config-driven keyword match)
            is_action = bool(action_kw) and any(kw in line for kw in action_kw)
            oral = ["我", "你", "啦", "啊", "吗", "吧", "!", "?", "~"]
            if is_action and not any(kw in content for kw in oral):
                source_unit["type"] = "action"
                beats.append({
                    "type": "action",
                    "text": line,
                    "scene": current_scene["name"] if current_scene else "",
                    "source_ids": [source_id],
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
            segments = split_dialogue(content, max_seconds=max_shot_duration, reserve_seconds=0.5)
            entries = {}
            for i, (seg, dur) in enumerate(segments):
                k = f"D{dialogue_counter + i}"
                entries[k] = seg
                dialogue_duration_map[k] = _estimate_dialogue_seconds(seg, tone)
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
                    "kind": speech_kind,
                    "speaker": speaker,
                    "text": seg,
                    "tone": tone,
                    "refs": [ref],
                    "speech_duration": dialogue_duration_map[ref],
                    "scene": current_scene["name"] if current_scene else "",
                    "source_ids": [source_id],
                })
            dialogue_counter += len(entries)
            continue
        # Plain screenplay prose is production content, not disposable context.
        # Preserve it as an action/state/sound beat so every source fact can be
        # traced into a planned shot even when the script omits a △ prefix.
        source_unit["type"] = "action"
        beats.append({
            "type": "action",
            "text": line,
            "scene": current_scene["name"] if current_scene else "",
            "source_ids": [source_id],
        })

    if current_scene:
        scenes.append(current_scene)

    # Pack only dialogue/action fragments that still belong to one narrative
    # beat.  Clip capacity is never a reason to merge a second event goal,
    # reaction ownership, or action chain into the same master shot.
    # Narration/OV/OS remains separate because it has a different lip-sync
    # boundary.
    force_single_dialogue = bool(
        cfg.get("benchmark", {}).get("force_single_dialogue_shots")
        or source_rules.get("pack_dialogue_turns") is False
    )
    merged = _pack_interaction_beats(
        beats,
        max_shot_duration,
        force_single_dialogue=force_single_dialogue,
    )
    merged = _pack_source_actions_with_interactions(merged, max_shot_duration)
    merged = _pack_action_beats(merged, max_shot_duration, characters_list)

    # Generate shots with character detection
    shots = []
    dramatic_beat_records = []
    for beat in merged:
        beat_chars = []
        full_text = beat.get("text", "")
        tone = beat.get("tone", "")
        speaker = beat.get("speaker", "")
        scene_name = beat.get("scene", "")

        if beat["type"] in ("dialogue", "narration", "dialogue_group", "mixed_interaction"):
            for turn in beat.get("turns", [beat]):
                if turn.get("type") == "action":
                    turn_text = str(turn.get("text", "") or "")
                    for c in _characters_in_source_order(turn_text, characters_list):
                        if c not in beat_chars and not _offscreen_character_mention(c, turn_text):
                            beat_chars.append(c)
                    continue
                turn_speaker = turn.get("speaker", "")
                turn_tone = turn.get("tone", "")
                # OV is a sound source, never a visible-character lock. OS may
                # still use its on-screen speaker with closed lips.
                if turn.get("kind") != "OV" and turn_speaker and turn_speaker not in beat_chars:
                    beat_chars.append(turn_speaker)
                if turn_tone:
                    for c in characters_list:
                        if c in turn_tone and c not in beat_chars:
                            beat_chars.append(c)
        else:
            for c in _characters_in_source_order(full_text, characters_list):
                if c not in beat_chars and not _offscreen_character_mention(c, full_text):
                    beat_chars.append(c)
            if _has_group_reaction(full_text):
                group_name = _group_character_name(characters_list)
                if group_name and group_name not in beat_chars:
                    beat_chars.append(group_name)
            if not beat_chars and characters_list:
                beat_chars = [characters_list[0]]

        shot_num = len(shots) + 1
        refs = beat.get("refs", [])

        if beat["type"] in ("action", "action_group"):
            # Use the same lower-bound model as preflight.  The former
            # character-count heuristic made Orchestrator knowingly under-budget
            # compound actions, then required repeated repair cycles.
            dur = max(2.0, min(max_shot_duration, _estimate_action_seconds(full_text) + 0.5))
            subshot_id = f"S1-{shot_num:02d}-01"
            visible_beats = [
                {"text": action.get("text", ""), "source_ids": action.get("source_ids", [])}
                for action in beat.get("actions", [])
            ] if beat.get("actions") else _visible_beat_texts(full_text)
            beat_ids = _register_dramatic_beats(
                dramatic_beat_records, beat, subshot_id, visible_beats
            )
            dramatic_design = _dramatic_design(beat, full_text, beat_chars, beat_ids)
            duration_design = _duration_design(
                dur, max_shot_duration, beat_ids,
                "continuous_action" if len(beat_ids) > 1 else "simple_action",
            )
            shots.append({
                "shot_id": f"S1-{shot_num:02d}",
                "scene": scene_name,
                "core_action": full_text,
                "subshots": [{
                    "subshot_id": subshot_id,
                    "duration": round(dur, 1),
                    "characters": beat_chars,
                    "dialogue_refs": [],
                    "base_action": full_text,
                    "source_ids": list(beat.get("source_ids", [])),
                    "dramatic_design": dramatic_design,
                    "duration_design": duration_design,
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
        subshot_id = f"S1-{shot_num:02d}-01"
        beat_texts = []
        for turn in beat.get("turns", [beat]):
            speaker_prefix = (turn.get("speaker", "") + "：") if turn.get("speaker") else ""
            beat_texts.extend({
                "text": speaker_prefix + part,
                "source_ids": turn.get("source_ids", []),
            } for part in _visible_beat_texts(turn.get("text", "")))
        beat_ids = _register_dramatic_beats(
            dramatic_beat_records, beat, subshot_id, beat_texts
        )
        rationale = "continuous_interaction" if len(beat.get("turns", [beat])) > 1 else "continuous_dialogue"
        dramatic_design = _dramatic_design(beat, "；".join(turn_summaries), beat_chars, beat_ids)
        duration_design = _duration_design(seg_dur, max_shot_duration, beat_ids, rationale)
        subshots = [{
            "subshot_id": subshot_id,
            "duration": round(seg_dur, 1),
            "characters": beat_chars,
            "dialogue_refs": refs,
            "base_action": "；".join(turn_summaries)[:160],
            "source_ids": list(beat.get("source_ids", [])),
            "dramatic_design": dramatic_design,
            "duration_design": duration_design,
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
    with open(os.path.join(output_dir, "source_ledger.json"), "w", encoding="utf-8") as f:
        json.dump({"source_path": os.path.abspath(source_path), "units": source_units}, f, ensure_ascii=False, indent=2)
    with open(os.path.join(output_dir, "dramatic_beat_ledger.json"), "w", encoding="utf-8") as f:
        json.dump({"beats": dramatic_beat_records}, f, ensure_ascii=False, indent=2)
    return draft_path, len(shots), sum(len(s["subshots"]) for s in shots)


def _visible_beat_texts(text):
    # Source punctuation provides ordered, non-invented beats for long
    # dialogue. This lets duration validation distinguish real rhetorical
    # progression from a line stretched with atmosphere or residue.
    parts = [part.strip() for part in re.split(r"[。！？；;，、]+", str(text or "")) if part.strip()]
    return parts[:3] or [str(text or "").strip()]


def _offscreen_character_mention(character, text):
    """Return True when a named character is present only as a sound source."""
    character = str(character or "").strip()
    text = str(text or "")
    if not character or character not in text:
        return False
    sound_patterns = (
        rf"(?:门外|画外|窗外|电话里|听筒里|隔墙|墙外|门那边|电话那头)[^。；，,]{{0,24}}{re.escape(character)}[^。；，,]{{0,16}}(?:声音|说话声|喊声|哭声|笑声|说)",
        rf"(?:他|她|对方|那边)[^。；，,]{{0,12}}(?:在门外|在墙外|在电话里|隔着墙)[^。；，,]{{0,12}}(?:说|喊|哭|笑)[^。；]*{re.escape(character)}?",
        rf"{re.escape(character)}的(?:声音|说话声|喊声|哭声|笑声)[^。；，,]{{0,16}}(?:传来|响起|出现)",
    )
    return any(re.search(pattern, text) for pattern in sound_patterns)


def _characters_in_source_order(text, characters):
    """Return mentioned characters ordered by first appearance in this beat."""
    text = str(text or "")
    candidates = [str(character).strip() for character in characters or [] if str(character).strip() and str(character).strip() in text]
    found = []
    occupied = []
    # Prefer the longest configured name when one name is a substring of
    # another (林 vs 林岚), but retain a shorter name when it appears elsewhere.
    for character in sorted(candidates, key=lambda value: (-len(value), text.find(value))):
        starts = [match.start() for match in re.finditer(re.escape(character), text)]
        if not starts:
            continue
        usable = [
            start for start in starts
            if not any(start < end and start + len(character) > begin for begin, end in occupied)
        ]
        if usable:
            found.append(character)
            occupied.extend((start, start + len(character)) for start in usable)
    return sorted(found, key=lambda character: (text.find(character), len(character)))


def _looks_like_dialogue_prefix(speaker, tone, content, characters):
    speaker = str(speaker or "").strip()
    content = str(content or "").strip()
    if not speaker or not content:
        return False
    if speaker in {"时间", "地点", "场景", "动作", "镜头", "画面", "状态", "说明", "备注", "系统", "提示"}:
        return False
    if re.match(r"^(?:https?://|ftp://|www\.)", content, re.I) or re.match(r"^\d{1,2}:\d{2}(?::\d{2})?$", content):
        return False
    if speaker in {str(value).strip() for value in characters or []}:
        return True
    tone_upper = str(tone or "").upper()
    if any(token in tone_upper for token in ("OS", "OV")) or any(token in str(tone or "") for token in ("旁白", "内心")):
        return True
    # Preserve unlisted natural-language speakers while rejecting metadata
    # prefixes and path-like content above.
    return bool(re.search(r"[。！？“”‘’！？，,]", content)) or len(content) >= 2


def _match_scene_header(line, pattern):
    match = re.match(pattern, line)
    if match:
        return match
    return re.match(
        r"^(?:第\s*\d+\s*场|场\s*\d+|\d+\.\s*(?:INT\.|EXT\.)|(?:INT\.|EXT\.)\s+)",
        line,
        re.I,
    )


def _register_dramatic_beats(records, beat, owner_subshot_id, texts):
    beat_ids = []
    source_ids = list(dict.fromkeys(beat.get("source_ids", []) or []))
    narrative_beat_id = ""
    for value in texts:
        text = value.get("text", "") if isinstance(value, dict) else value
        record_source_ids = (
            list(dict.fromkeys(value.get("source_ids", []) or []))
            if isinstance(value, dict) else source_ids
        )
        if not str(text or "").strip():
            continue
        beat_id = "B%04d" % (len(records) + 1)
        if not narrative_beat_id:
            narrative_beat_id = beat_id
        records.append({
            "beat_id": beat_id,
            "narrative_beat_id": narrative_beat_id,
            "beat_role": "primary" if beat_id == narrative_beat_id else "supporting",
            "source_ids": record_source_ids,
            "type": beat.get("type", "action"),
            "text": str(text).strip(),
            "owner_subshot_id": owner_subshot_id,
            "reserved_by": [],
        })
        beat_ids.append(beat_id)
    return beat_ids


def _dramatic_design(beat, text, characters, beat_ids):
    content = str(text or "")
    if any(token in content for token in ("进入", "走入", "出场", "现身")):
        function = "entrance"
    elif any(token in content for token in ("揭开", "显露", "发现", "看清")):
        function = "reveal"
    elif beat.get("type") in ("dialogue", "dialogue_group", "narration", "mixed_interaction"):
        function = "dialogue"
    elif any(token in content for token in ("反应", "回望", "转头")):
        function = "reaction"
    else:
        function = "action"
    explicit_weight = str(beat.get("narrative_weight", "") or "").strip().lower()
    if explicit_weight in ("low", "medium", "high", "critical"):
        weight = explicit_weight
    else:
        critical_markers = (
            "权力关系逆转", "改写权力关系", "身份反转", "真相揭晓", "局势彻底改变",
        )
        high_markers = (
            "首次出场", "第一次出现", "关键人物", "核心人物", "重要人物",
            "身份揭示", "信息反转", "压住全场", "局势改变",
        )
        if any(marker in content for marker in critical_markers):
            weight = "critical"
        elif any(marker in content for marker in high_markers):
            weight = "high"
        else:
            weight = "medium"
    visual_punctuation = []
    if function == "entrance" and weight in ("high", "critical"):
        candidates = (
            ("occlusion_reveal", ("遮挡", "门后", "阴影中")),
            ("low_angle_scale", ("低机位", "仰视", "仰拍")),
            ("foreground_reaction", ("前景反应", "众人反应", "众人转头")),
            ("light_reveal", ("轮廓光", "转面光", "光线揭示")),
            ("rack_focus", ("拉焦", "焦点转移")),
            ("camera_follow", ("进入", "走入", "现身", "跟随")),
            ("stop_mark", ("停", "站定", "顿住")),
        )
        for device, markers in candidates:
            if any(marker in content for marker in markers):
                visual_punctuation.append(device)
            if len(visual_punctuation) == 2:
                break
        if not visual_punctuation:
            visual_punctuation.append("camera_follow")
    reaction_owner = characters[1] if len(characters) > 1 else ""
    coverage_role = _coverage_role(function, content, characters, weight)
    return {
        "shot_function": function,
        "coverage_role": coverage_role,
        "narrative_weight": weight,
        "information_gain": content[:120],
        "reaction_ownership": reaction_owner,
        "narrative_beat_id": beat_ids[0] if beat_ids else "",
        "dramatic_beat_ids": beat_ids,
        "visual_punctuation": visual_punctuation,
    }


def _coverage_role(function, content, characters, weight):
    """Choose the visual job before any camera language is generated.

    This is intentionally a source-led classification, not a quota.  It gives
    Composer a concrete reason to vary coverage when the story needs space,
    blocking, movement or an information reveal, while leaving close stable
    coverage available for actual dialogue and low-amplitude reactions.
    """
    if function == "dialogue":
        # A multi-speaker exchange carries relationship geometry, listening
        # and attention transfer.  Treating it as a single-person dialogue
        # close-up was the primary source of repetitive fixed medium shots.
        return "relationship_blocking" if len(characters) >= 2 else "dialogue_performance"
    if function == "reaction":
        return "reaction"
    if function == "entrance":
        return "establish_space" if weight in ("high", "critical") else "movement_transition"
    if function == "reveal":
        if any(token in content for token in ("手机", "屏幕", "来电", "短信", "信", "文件", "照片", "钥匙", "证据", "礼物")):
            return "prop_information"
        return "power_reversal"
    if any(token in content for token in ("环境", "街景", "天空", "门外", "走廊", "空镜", "建筑", "人群")):
        return "environment_bridge"
    if len(characters) >= 2 and any(token in content for token in ("递", "接", "拦", "靠近", "对峙", "拉住", "推开", "并排", "相对")):
        return "relationship_blocking"
    return "movement_transition"


def _duration_design(duration, capacity, beat_ids, rationale):
    duration = round(float(duration), 1)
    capacity = float(capacity)
    return {
        "duration_strategy": "pack_toward_limit",
        "justified_content_duration": duration,
        "utilization_ratio": round(duration / capacity, 3) if capacity > 0 else 0,
        "duration_rationale": rationale,
        "dramatic_beats": beat_ids,
    }


def _has_group_reaction(text):
    text = str(text or "")
    return any(kw in text for kw in ["所有人", "众人", "几人", "成员", "几道视线", "视线同时", "集体", "每一张面孔", "室内"])


def _group_character_name(characters):
    for name in characters or []:
        if any(kw in str(name) for kw in ["其他所有人", "众人", "成员", "其余几人"]):
            return name
    return "其他所有人"


def _interaction_duration(turns, reserve_seconds=0.5):
    turns = list(turns or [])
    speech = sum(float(turn.get("speech_duration", 0) or 0) for turn in turns)
    from validate_durations import _estimate_action_seconds
    action = sum(
        max(0.0, float(_estimate_action_seconds(turn.get("text", ""))) - 2.0)
        for turn in turns if turn.get("type") == "action"
    )
    return round(max(2.5, speech + action + reserve_seconds), 1)


def _pack_interaction_beats(beats, max_shot_duration, force_single_dialogue=False):
    packed = []
    group = []

    def flush():
        nonlocal group
        if not group:
            return
        refs = [ref for turn in group for ref in turn.get("refs", [])]
        packed.append({
            "type": "dialogue_group" if len(group) > 1 else group[0].get("type", "dialogue"),
            "kind": group[0].get("kind", "台词"),
            "scene": group[0].get("scene", ""),
            "speaker": group[0].get("speaker", ""),
            "tone": group[0].get("tone", ""),
            "text": "".join(turn.get("text", "") for turn in group),
            "refs": refs,
            "turns": list(group),
            "source_ids": list(dict.fromkeys(
                source_id for turn in group for source_id in turn.get("source_ids", [])
            )),
        })
        group = []

    for beat in beats:
        if beat.get("type") != "dialogue":
            flush()
            packed.append(beat)
            continue
        if force_single_dialogue:
            flush()
            if _interaction_duration([beat]) > max_shot_duration + 1e-6:
                raise ValueError(
                    "single dialogue semantic unit exceeds user-confirmed max_shot_duration: %s"
                    % beat.get("text", "")
                )
            group = [beat]
            flush()
            continue
        if group and beat.get("scene", "") != group[0].get("scene", ""):
            flush()
        if group and len(group) >= 2:
            # A master shot may cover one short exchange, but a third turn is
            # usually a new decision/reaction beat and should start the next
            # generation task instead of being packed for duration utilization.
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


def _pack_source_actions_with_interactions(beats, max_shot_duration):
    """Attach only low-risk adjacent source actions to their speech beat.

    This preserves unprefixed screenplay action lines without turning every
    setup, sound cue, listener reaction, or unfinished prop move into a new
    main shot. Strong motion and force remain independent action shots.
    """
    speech_types = {"dialogue", "dialogue_group", "narration", "mixed_interaction"}
    result = []
    index = 0
    while index < len(beats):
        current = beats[index]
        group = []
        if (
            current.get("type") == "action"
            and _action_attachable_to_speech(current)
            and index + 1 < len(beats)
            and beats[index + 1].get("type") in speech_types
            and current.get("scene", "") == beats[index + 1].get("scene", "")
        ):
            group = [current, beats[index + 1]]
            index += 2
        elif current.get("type") in speech_types:
            group = [current]
            index += 1
        else:
            result.append(current)
            index += 1
            continue

        if (
            index < len(beats)
            and beats[index].get("type") == "action"
            and _action_attachable_to_speech(beats[index])
            and group[-1].get("scene", "") == beats[index].get("scene", "")
            and not _action_cues_following_speech(
                beats[index], beats[index + 1] if index + 1 < len(beats) else None
            )
        ):
            candidate = group + [beats[index]]
            if _mixed_turn_duration(candidate) <= max_shot_duration + 1e-6:
                group = candidate
                index += 1

        if len(group) == 1:
            result.append(group[0])
            continue
        if _mixed_turn_duration(group) > max_shot_duration + 1e-6:
            result.extend(group)
            continue
        turns = []
        for item in group:
            turns.extend(item.get("turns", [item]))
        refs = [ref for turn in turns for ref in turn.get("refs", [])]
        result.append({
            "type": "mixed_interaction",
            "kind": next((turn.get("kind") for turn in turns if turn.get("kind")), "台词"),
            "scene": group[0].get("scene", ""),
            "speaker": next((turn.get("speaker") for turn in turns if turn.get("speaker")), ""),
            "tone": next((turn.get("tone") for turn in turns if turn.get("tone")), ""),
            "text": "；".join(str(turn.get("text", "") or "") for turn in turns),
            "refs": refs,
            "turns": turns,
            "source_ids": list(dict.fromkeys(
                source_id for turn in turns for source_id in turn.get("source_ids", [])
            )),
        })
    return result


def _mixed_turn_duration(items):
    turns = []
    for item in items:
        turns.extend(item.get("turns", [item]))
    return _interaction_duration(turns)


def _action_attachable_to_speech(action):
    text = str(action.get("text", "") or "")
    strong_motion = (
        "打", "踢", "撞", "摔", "扑", "冲", "追", "奔", "跳", "翻越",
        "扭打", "拉扯", "拖拽", "制服", "抢夺", "爆炸", "坍塌",
    )
    if any(term in text for term in strong_motion):
        return False
    from validate_durations import _estimate_action_seconds
    return _estimate_action_seconds(text) <= 4.5 and len(_visible_beat_texts(text)) <= 3


def _action_cues_following_speech(action, following):
    """Keep an offscreen/sound cue with the line it introduces."""
    if not isinstance(following, dict) or following.get("type") not in {"narration", "mixed_interaction"}:
        return False
    text = str(action.get("text", "") or "")
    speaker = str(following.get("speaker", "") or "")
    is_sound_cue = any(term in text for term in ("门外", "画外", "窗外", "电话里", "声音", "脚步声", "敲门声", "传来", "响起"))
    return is_sound_cue and (not speaker or speaker in text or following.get("kind") == "OV")


def _pack_action_beats(beats, max_shot_duration, characters):
    """Pack only demonstrably causal actions that share one narrative beat."""
    packed = []
    group = []

    def action_duration(action_group):
        text = "；".join(item.get("text", "") for item in action_group)
        from validate_durations import _estimate_action_seconds
        return max(2.0, _estimate_action_seconds(text) + 0.5)

    def compatible(previous, current):
        if previous.get("scene", "") != current.get("scene", ""):
            return False
        previous_text = str(previous.get("text", "") or "")
        current_text = str(current.get("text", "") or "")
        shared_character = any(
            character and character in previous_text and character in current_text
            for character in characters or []
        )
        causal_start = current_text.startswith((
            "随后", "接着", "同时", "这时", "于是", "继而", "转而",
            "停下", "继续", "紧接着", "下一刻",
        ))
        if _separate_reaction_beat(previous_text, current_text, causal_start):
            return False
        return (shared_character and _same_action_family(previous_text, current_text)) or causal_start

    def flush():
        nonlocal group
        if not group:
            return
        if len(group) == 1:
            packed.append(group[0])
        else:
            packed.append({
                "type": "action_group",
                "scene": group[0].get("scene", ""),
                "text": "；".join(item.get("text", "") for item in group),
                "source_ids": list(dict.fromkeys(
                    source_id for item in group for source_id in item.get("source_ids", [])
                )),
                "actions": list(group),
            })
        group = []

    for beat in beats:
        if beat.get("type") != "action":
            flush()
            packed.append(beat)
            continue
        if group and len(group) >= 3:
            flush()
        if group and not compatible(group[-1], beat):
            flush()
        candidate = group + [beat]
        if group and action_duration(candidate) > max_shot_duration + 1e-6:
            flush()
            candidate = [beat]
        if action_duration(candidate) > max_shot_duration + 1e-6:
            raise ValueError(
                "single action semantic unit exceeds user-confirmed max_shot_duration "
                "and cannot be safely compressed: %s" % beat.get("text", "")
            )
        group = candidate
    flush()
    return packed


def _separate_reaction_beat(previous_text, current_text, causal_start):
    """Return True when the next action is likely a new reaction beat.

    This deliberately catches the common over-pack case: a physical action
    such as "侍卫拖拽穿越女" followed by a separate observer reaction such as
    "皇后冷漠看待".  Immediate impact/feedback marked by clear causal words can
    still remain inside the same action beat.
    """
    if causal_start:
        return False
    force_markers = ("拖", "拽", "抓", "按", "推", "撞", "打", "踢", "制服", "拉扯", "扭打", "抢")
    reaction_markers = ("看", "望", "注视", "冷眼", "冷漠", "旁观", "沉默", "皱眉", "愣", "怔", "回头", "转头")
    return any(marker in previous_text for marker in force_markers) and any(marker in current_text for marker in reaction_markers)


def _same_action_family(previous_text, current_text):
    """Avoid using one shared character as the only reason to merge beats."""
    force_markers = ("拖", "拽", "抓", "按", "推", "撞", "打", "踢", "制服", "拉扯", "扭打", "抢")
    dialogue_like_markers = ("说", "问", "回答", "解释", "喊", "低声")
    reaction_markers = ("看", "望", "注视", "冷眼", "冷漠", "旁观", "沉默", "皱眉", "愣", "怔", "回头", "转头")
    families = (force_markers, dialogue_like_markers, reaction_markers)
    previous_families = {index for index, markers in enumerate(families) if any(marker in previous_text for marker in markers)}
    current_families = {index for index, markers in enumerate(families) if any(marker in current_text for marker in markers)}
    if not previous_families or not current_families:
        return True
    return bool(previous_families & current_families)


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
