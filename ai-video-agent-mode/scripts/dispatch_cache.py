"""Write compact on-disk dispatch packets for sub-agent phases.

The main agent can pass these packet paths to workers instead of copying a
large shot list into every prompt. Workers read the packet from disk, write only
their required output file, and retry messages carry only failed subshot ids.
"""
import json
import os
import re
import sys
import time
import uuid

if not os.environ.get("PYTHONPYCACHEPREFIX") and not getattr(sys, "pycache_prefix", None):
    sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))
from pycache_policy import block_source_pycache_until_run_dir, ensure_pycache_prefix

block_source_pycache_until_run_dir()


PHASE_OUTPUTS = {
    "emotion_analysis": ".cache/analysis/emotion_output.json",
    "scene_analysis": ".cache/analysis/scene_output.json",
    "camera_movement": ".cache/analysis/camera_output.json",
    "prompt_composer": ".cache/composer/merged.prompt_package.json",
    "editor_pass2": ".cache/review/llm_gate_result.json",
}

PHASE_INPUTS = {
    "emotion_analysis": ".cache/orchestrator/shot_plan.json",
    "scene_analysis": ".cache/orchestrator/shot_plan.json",
    "camera_movement": ".cache/orchestrator/shot_plan.json",
    "prompt_composer": ".cache/director/director_pass.json",
    "editor_pass2": ".cache/composer/merged.prompt_package.json",
}


def prepare_dispatch_packets(run_dir, phase, batch_size=None, subshot_ids=None):
    """Materialize one or more phase input packets and return their paths.

    Each packet contains only the items for that batch. The full source_path is
    still included so a worker can recover surrounding context when needed, but
    packet.items is the authority for what the worker may write.
    """
    ensure_pycache_prefix(run_dir)
    source_path = os.path.join(run_dir, PHASE_INPUTS.get(phase, ""))
    if not source_path or not os.path.isfile(source_path):
        return []

    data = _load_json(source_path)
    wanted = set(subshot_ids or [])
    items = _extract_items(data, wanted)
    if not items:
        return []

    is_retry = bool(wanted)
    if phase == "prompt_composer":
        size = max(int(batch_size or 4), 1)
        chunks = _composer_chunks(items, size, respect_chains=not is_retry)
    elif batch_size is not None:
        size = max(int(batch_size), 1)
        chunks = [items[i:i + size] for i in range(0, len(items), size)]
    else:
        size = max(len(items), 1)
        chunks = [items]
    out_dir = os.path.join(run_dir, ".cache", "dispatch")
    os.makedirs(out_dir, exist_ok=True)
    dispatch_group_id = str(uuid.uuid4())
    group_tag = dispatch_group_id.split("-")[0]
    constraints_path = _write_constraints_sidecar(run_dir, phase, out_dir, group_tag)
    scene_lock_cache_path = None
    if phase == "prompt_composer":
        scene_lock_cache_path = _write_scene_lock_cache(run_dir, items, out_dir, group_tag)
    paths = []

    for idx, chunk in enumerate(chunks, 1):
        dispatch_id = str(uuid.uuid4())
        dispatch_tag = dispatch_id.split("-")[0]
        public_output = os.path.join(run_dir, PHASE_OUTPUTS.get(phase, ".cache/%s_output.json" % phase))
        batch_output = _batch_output_path(public_output, phase, idx, len(chunks), dispatch_tag)
        scaffold_path = None
        packet_items = chunk
        if phase == "prompt_composer":
            scaffold_path = _write_composer_scaffold(
                run_dir, chunk, out_dir, dispatch_tag, scene_lock_cache_path
            )
            packet_items = [_compact_composer_item(item) for item in chunk]
        packet = {
            "contract_version": "modec-v4",
            "dispatch_id": dispatch_id,
            "dispatch_group_id": dispatch_group_id,
            "created_at": time.time(),
            "phase": phase,
            "run_dir": run_dir,
            "source_path": source_path,
            "project_config_path": os.path.join(run_dir, "project_config.json"),
            "format_example_path": os.path.join(os.path.dirname(os.path.dirname(__file__)), "references", "format_example.txt"),
            "quality_exemplar_path": os.path.join(os.path.dirname(os.path.dirname(__file__)), "references", "quality_exemplar", "S2-03_high_quality_example.txt"),
            "constraints_path": constraints_path,
            "output_path": public_output,
            "_batch_output_path": batch_output,
            "batch_index": idx,
            "total_batches": len(chunks),
            "batch_size": size,
            "total_item_count": len(items),
            "subshot_count": len(chunk),
            "context_item_count": len(chunk),
            "items": packet_items,
            "instruction": (
                "Process only packet.items and write exactly one JSON file "
                "to _batch_output_path. Do not write output_path; the main agent merges batch files. "
                "Require contract_version=modec-v4 and read constraints_path for the full phase contract; "
                "a missing or older contract version requires redispatch. For prompt_composer, start from "
                "composer_scaffold_path, preserve every locked field, and read scene_lock_cache_path once per scene; "
                "source_path is fallback context only and must not be read in full unless packet data is insufficient. "
                "Do not paste unchanged source content back into chat."
            ),
        }
        if scaffold_path:
            packet["composer_scaffold_path"] = scaffold_path
            packet["scene_lock_cache_path"] = scene_lock_cache_path
            packet["retry_mode"] = is_retry
        suffix = "" if len(chunks) == 1 else "_batch%03d" % idx
        out_path = os.path.join(out_dir, "%s%s_%s_packet.json" % (phase, suffix, dispatch_tag))
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(packet, f, ensure_ascii=False, indent=2)
        paths.append(out_path)
    return paths


def prepare_dispatch_packet(run_dir, phase, batch_size=None, subshot_ids=None):
    """Materialize a phase input packet and return its path.

    The packet intentionally stores file paths plus compact subshot metadata.
    A worker should read source files from the paths in the packet instead of
    receiving full source text in the spawn message.
    """
    paths = prepare_dispatch_packets(run_dir, phase, batch_size, subshot_ids)
    return paths[0] if paths else None


def prepare_parallel_dispatch(run_dir, phases, batch_sizes=None):
    batch_sizes = batch_sizes or {}
    return {
        phase: prepare_dispatch_packets(run_dir, phase, batch_sizes.get(phase))
        for phase in phases
    }


def _extract_items(data, wanted):
    if "shots" in data:
        items = []
        for shot in data.get("shots", []):
            if isinstance(shot, dict) and "subshots" not in shot and shot.get("subshot_id"):
                ssid = shot.get("subshot_id", "")
                if wanted and ssid not in wanted:
                    continue
                copied = dict(shot)
                copied.setdefault("duration_sec", copied.get("duration", 0))
                copied.setdefault("visible_characters", copied.get("characters", []))
                items.append(copied)
                continue
            for ss in shot.get("subshots", []):
                ssid = ss.get("subshot_id", "")
                if wanted and ssid not in wanted:
                    continue
                source_events = [
                    dict(data.get("dialogue_events", {}).get(ref, {}))
                    for ref in ss.get("dialogue_refs", [])
                    if isinstance(data.get("dialogue_events", {}).get(ref), dict)
                ]
                items.append({
                    "shot_id": shot.get("shot_id", ""),
                   "subshot_id": ssid,
                   "scene": shot.get("scene", ""),
                   "scene_type": shot.get("scene_type", "") or ss.get("scene_type", ""),
                   "duration": ss.get("duration", 0),
                   "duration_sec": ss.get("duration", 0),
                   "shot_size": ss.get("shot_size", ""),
                    "base_action": ss.get("base_action", ""),
                    "shot_type": ss.get("shot_type", "") or ss.get("visual_type", "") or ss.get("purpose", ""),
                    "visual_intent": ss.get("visual_intent", "") or ss.get("image_subject", "") or ss.get("atmosphere", ""),
                    "characters": ss.get("characters", []),
                    "visible_characters": ss.get("visible_characters", ss.get("characters", [])),
                    "dialogue_refs": ss.get("dialogue_refs", []),
                    "dialogue_events": source_events,
                    "dialogue_raw_text": "\n".join(str(event.get("text", "") or "") for event in source_events),
                    "emotion_tone": ss.get("emotion_tone", ""),
                    "spatial_map": ss.get("spatial_map", {}),
                    "props": ss.get("props", []),
                })
        return items
    items = []
    for item in data.get("items", []):
        if wanted and item.get("subshot_id") not in wanted:
            continue
        if isinstance(item, dict):
            copied = dict(item)
            copied.setdefault("duration_sec", copied.get("duration", 0))
            copied.setdefault("visible_characters", copied.get("characters", []))
            items.append(copied)
    return items


def _batch_output_path(public_output, phase, idx, total, dispatch_tag):
    """Return the only file a worker may write for this packet."""
    directory = os.path.dirname(public_output)
    if phase == "prompt_composer":
        return os.path.join(directory, "composer_b%03d_%s.prompt_package.json" % (idx, dispatch_tag))
    if total == 1:
        base = os.path.basename(public_output).replace(".json", "_b001_%s.json" % dispatch_tag)
    else:
        base = os.path.basename(public_output).replace(".json", "_b%03d_%s.json" % (idx, dispatch_tag))
    return os.path.join(directory, base)


def _load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _write_constraints_sidecar(run_dir, phase, dispatch_dir, dispatch_tag):
    skill_dir = os.path.dirname(os.path.dirname(__file__))
    source = os.path.join(skill_dir, "references", "format_constraints.md")
    out_path = os.path.join(dispatch_dir, "%s_%s_constraints.md" % (phase, dispatch_tag))
    phase_note = {
        "emotion_analysis": (
            "Professional role: You are a film performance director and emotion-analysis Agent. "
            "Only analyze emotion triggers, facial/body performance, voice tone, and per-character reaction causality; "
            "do not invent plot, rewrite dialogue, design clothing, choose camera lenses, or rewrite scene art. "
            "Use §A, especially A1/A2/A3. Output only {\"items\": [...]} to packet._batch_output_path."
        ),
        "scene_analysis": (
            "Professional role: You are a production designer, lighting director, and scene-analysis Agent. "
            "Only analyze spatial layers, character placement, scene grounding, light source direction/color temperature continuity, "
            "and environmental audio; do not invent plot, rewrite dialogue, choose camera movement, or create clothing details. "
            "Use §A, especially A1/A2/A4. Output only {\"items\": [...]} to packet._batch_output_path."
        ),
        "camera_movement": (
            "Professional role: You are a director of photography and camera-movement Agent. "
            "Only analyze shot size, focal length, camera position, axis, composition, movement trajectory, entry/exit, and end frame; "
            "do not invent plot, rewrite dialogue, design clothing, or rewrite scene art. "
            "Do not confuse camera position with character facing: unless the source explicitly requires direct-to-camera/selfie/viewer address, "
            "characters must keep story-correct eyelines toward opponents, speakers, doorways, props, or spatial focal points, not face the lens for frontal composition. "
            "A continuous interaction may hand attention from A to B once inside the same dramatic objective; choose only fixed+rack-focus, one unidirectional reframe, or actor blocking with a fixed camera. "
            "Use §A, especially A1/A2/A5. Output only {\"items\": [...]} to packet._batch_output_path."
        ),
        "prompt_composer": (
            "Professional role: You are a short-drama AI video director and prompt supervisor. "
            "Create one low-reroll Mode C v4 shot per subshot with a strict action budget and primary/supporting/background performance priority; "
            "do not invent plot, rewrite dialogue, redesign clothing, add unconfirmed props, or expose engineering fields. "
            "Do not force characters to face the lens: distinguish camera-front position from character-facing direction, and only write direct-to-camera eyeline when explicitly sourced. "
            "For one causal A-to-B attention handoff, use exactly one strategy and record qa_metadata.attention_handoff; never stack physical movement, zoom, and rack focus. "
            "For every shot with visible physical characters, fill qa_metadata.performance_causality with calibrated tension intent, trigger, ordered response, physical logic, motion boundary, hold strategy, and end residue. "
            "Also fill qa_metadata.performance_contract, qa_metadata.continuity_contract, and qa_metadata.reroll_control before writing full_prompt: performance_contract must bind expression, body action, eyeline, reaction delay, voice/breath control, one viewer empathy anchor, one readable image moment, camera pressure, scene pressure, and end residue into the timeline; continuity_contract must preserve start/end anchors, eyelines, prop state, light, and next carryover; reroll_control must score T2V/I2V/R2V risk, state reference needs, and list concrete mitigation steps. "
            "For every locked dialogue event, preserve ref/kind/speaker/text exactly and fill its time_range, speaker_visibility, facial_state, body_state, delivery, and lip_sync. Dialogue/OS text must never be rewritten. "
            "Use §B-§E in this sidecar, then read packet.format_example_path and packet.quality_exemplar_path exactly once. "
            "Examples are structure-only: absorb causal performance chains, prop-state transfer, timeline continuity, system-text safe zones, dialogue/lip-sync boundaries, end residue, and reroll controls, but never inherit example genre, soft-light rhythm, hotel/urban setting, manhwa style, clothing, character relationships, or specific prop events unless the current source/config provides them. "
            "For confirmed I2V/R2V with real reference assets, use only platform handles confirmed in reference_assets and add an identity-continuity lock; never invent handles. For fight shots, reduce reroll risk by limiting speed, amplitude, contact beats, and camera shake, then split overly complex choreography into locked consecutive clips. "
            "Start from packet.composer_scaffold_path and preserve all locked fields. Read packet.scene_lock_cache_path once per scene instead of rediscovering shared light, space, costume, canvas, style, or generation settings. "
            "full_prompt contains exactly 画面锁定/镜头设计/表演时间轴/光照与声音; "
            "negative_prompt is a sibling field containing only {{NEGATIVE_PROMPT_AUTO_INJECT}}; QA and generation-control data stay in sibling objects. "
            "The performance timeline uses 2-3 continuous decimal ranges from 0.0 to exact duration. Never invent reference-asset paths."
        ),
        "editor_pass2": "Use §B/§C for review context. Do not rewrite format-only issues; return semantic review JSON only.",
    }.get(phase, "Follow the referenced phase contract.")
    with open(source, "r", encoding="utf-8-sig") as f:
        body = f.read()
    selected_contract = _select_contract_sections(body, phase)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Dispatch Constraints\n\n")
        f.write("phase: %s\n\n" % phase)
        f.write(phase_note + "\n\n")
        f.write(selected_contract)
    return out_path


def _select_contract_sections(body, phase):
    """Select verbatim authoritative sections needed by one Agent phase."""
    matches = list(__import__("re").finditer(r"(?m)^## §([A-E])\b", body))
    if not matches:
        return body
    preamble = body[:matches[0].start()].rstrip()
    sections = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections[match.group(1)] = body[match.start():end].rstrip()
    wanted = {
        "emotion_analysis": ("A", "E"),
        "scene_analysis": ("A", "E"),
        "camera_movement": ("A", "E"),
        "prompt_composer": ("B", "C", "D", "E"),
        "editor_pass2": ("B", "C", "D", "E"),
    }.get(phase, tuple(sections))
    return "\n\n".join([preamble] + [sections[key] for key in wanted if key in sections]) + "\n"


def _composer_chunks(items, max_items, respect_chains=True):
    """Keep continuity groups intact and avoid one-item tail batches."""
    shot_groups = []
    for item in items:
        group_id = _composer_group_id(item) if respect_chains else str(item.get("subshot_id", ""))
        if shot_groups and shot_groups[-1][0] == group_id:
            shot_groups[-1][1].append(item)
        else:
            shot_groups.append([group_id, [item]])
    chunks = []
    current = []
    for _, group in shot_groups:
        if current and len(current) + len(group) > max_items:
            chunks.append(current)
            current = []
        current.extend(group)
        if len(current) >= max_items:
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)
    if len(chunks) > 1 and len(chunks[-1]) == 1:
        donor = chunks[-2]
        donor_group_start = _last_group_start(donor, respect_chains)
        movable = donor[donor_group_start:]
        if len(donor) - len(movable) >= 2 and len(movable) + 1 <= max_items:
            chunks[-2] = donor[:donor_group_start]
            chunks[-1] = movable + chunks[-1]
    return chunks or [items]


def _composer_group_id(item):
    """Return an explicit continuity-chain id, falling back to main shot id."""
    metadata = item.get("qa_metadata", {}) if isinstance(item.get("qa_metadata"), dict) else {}
    fight = item.get("fight_continuity", metadata.get("fight_continuity", {}))
    if isinstance(fight, dict) and fight.get("sequence_id"):
        return "fight:%s" % fight["sequence_id"]
    for key in (
        "continuous_interaction_id", "interaction_chain_id", "continuous_chain_id",
        "sequence_id", "performance_chain_id",
    ):
        value = item.get(key, metadata.get(key))
        if value:
            return "chain:%s" % value
    return "shot:%s" % str(item.get("shot_id", "") or item.get("subshot_id", ""))


def _last_group_start(items, respect_chains):
    if not items:
        return 0
    last_id = _composer_group_id(items[-1]) if respect_chains else str(items[-1].get("subshot_id", ""))
    index = len(items) - 1
    while index > 0:
        current_id = _composer_group_id(items[index - 1]) if respect_chains else str(items[index - 1].get("subshot_id", ""))
        if current_id != last_id:
            break
        index -= 1
    return index


def _write_composer_scaffold(run_dir, items, dispatch_dir, dispatch_tag, scene_lock_cache_path):
    config = _load_optional_json(os.path.join(run_dir, "project_config.json"))
    project_control = config.get("generation_control", {})
    shots = []
    for item in items:
        control = item.get("generation_control")
        if not isinstance(control, dict):
            control = project_control if isinstance(project_control, dict) else {}
        control = {
            "mode": control.get("mode", "t2v"),
            "audio_enabled": bool(control.get("audio_enabled", False)),
            "reference_assets": list(control.get("reference_assets", []) or []),
        }
        duration = item.get("duration", item.get("duration_sec", 0))
        shots.append({
            "shot_id": item.get("shot_id", ""),
            "subshot_id": item.get("subshot_id", ""),
            "duration": duration,
            "full_prompt": "画面锁定：\n\n镜头设计：\n\n表演时间轴：\n\n光照与声音：",
            "negative_prompt": "{{NEGATIVE_PROMPT_AUTO_INJECT}}",
            "qa_metadata": {
                "dramatic_goal": "",
                "performance_priority": {"primary": "", "supporting": [], "background": []},
                "action_budget": {
                    "primary_action_count": 0,
                    "emotion_turn_count": 0,
                    "supporting_reaction_count": 0,
                    "camera_move_count": 0,
                },
                "start_state": "",
                "end_state": "",
                "performance_causality": {
                    "tension_intent": "",
                    "trigger": "",
                    "response_order": [],
                    "physical_logic": "",
                    "motion_boundary": "",
                    "hold_strategy": "",
                    "end_residue": "",
                },
                "performance_contract": {
                    "tension_intent": "",
                    "trigger_event": "",
                    "trigger_time": "",
                    "primary_expression": "",
                    "primary_body_action": "",
                    "eye_focus": "",
                    "reaction_delay": "",
                    "voice_or_breath_control": "",
                    "viewer_empathy_anchor": "",
                    "readable_image_moment": "",
                    "suppression_or_release": "",
                    "camera_pressure": "",
                    "scene_pressure": "",
                    "end_residue": "",
                },
                "continuity_contract": {
                    "start_anchor": "",
                    "end_anchor": "",
                    "position_continuity": "",
                    "eyeline_continuity": "",
                    "prop_state": "",
                    "lighting_continuity": "",
                    "next_carryover": "",
                },
                "reroll_control": {
                    "risk_level": "",
                    "identity_anchor": "",
                    "motion_anchor": "",
                    "scene_anchor": "",
                    "camera_anchor": "",
                    "risk_reason": "",
                    "mitigation_steps": [],
                    "needs_reference": False,
                },
                "dialogue_events": [
                    {
                        "ref": event.get("ref", ""),
                        "kind": event.get("kind", ""),
                        "speaker": event.get("speaker", ""),
                        "text": event.get("text", ""),
                        "time_range": "",
                        "speaker_visibility": "",
                        "facial_state": "",
                        "body_state": "",
                        "delivery": "",
                        "lip_sync": None,
                    }
                    for event in item.get("dialogue_events", [])
                    if isinstance(event, dict)
                ],
                "dialogue_refs": list(item.get("dialogue_refs", []) or []),
            },
            "generation_control": control,
            "_scene_lock_ref": str(item.get("scene", "") or "__default__"),
        })
    payload = {
        "contract_version": "modec-v4",
        "locked_fields": [
            "shot_id", "subshot_id", "duration", "negative_prompt",
            "qa_metadata.dialogue_refs", "qa_metadata.dialogue_events[].ref/kind/speaker/text", "generation_control",
        ],
        "scene_lock_cache_path": scene_lock_cache_path,
        "shots": shots,
    }
    path = os.path.join(dispatch_dir, "prompt_composer_%s_scaffold.json" % dispatch_tag)
    _write_json(path, payload)
    return path


def _write_scene_lock_cache(run_dir, items, dispatch_dir, group_tag):
    config = _load_optional_json(os.path.join(run_dir, "project_config.json"))
    scenes = {}
    for item in items:
        scene = str(item.get("scene", "") or "__default__")
        entry = scenes.setdefault(scene, {
            "scene": scene,
            "canvas": config.get("canvas", ""),
            "visual_style": config.get("visual_style", ""),
            "costumes": _scene_costumes(config.get("costume_map", {}), scene),
            "generation_control": config.get("generation_control", {}),
            "shared_light_anchors": [],
            "lighting_by_subshot": {},
            "spatial_by_subshot": {},
        })
        sid = str(item.get("subshot_id", ""))
        lighting = str(item.get("lighting", "") or "")
        if lighting:
            entry["lighting_by_subshot"][sid] = lighting
            for anchor in _light_anchors(lighting):
                if anchor not in entry["shared_light_anchors"]:
                    entry["shared_light_anchors"].append(anchor)
        spatial = str(item.get("axis_space", item.get("spatial_map", "")) or "")
        if spatial:
            entry["spatial_by_subshot"][sid] = spatial
    path = os.path.join(dispatch_dir, "prompt_composer_%s_scene_locks.json" % group_tag)
    _write_json(path, {"contract_version": "modec-v4", "scenes": scenes})
    return path


def _compact_composer_item(item):
    copied = dict(item)
    copied.pop("full_prompt", None)
    copied.pop("lighting", None)
    copied.pop("axis_space", None)
    copied.pop("generation_control", None)
    copied["scene_lock_ref"] = str(item.get("scene", "") or "__default__")
    copied["composer_scaffold_ref"] = str(item.get("subshot_id", ""))
    return copied


def _scene_costumes(costume_map, scene):
    if not isinstance(costume_map, dict):
        return {}
    result = {}
    for character, mapping in costume_map.items():
        if isinstance(mapping, dict):
            value = mapping.get(scene)
            if value is not None:
                result[character] = value
    return result


def _light_anchors(text):
    anchors = []
    for value in re.findall(r"\d{4}K", text):
        if value not in anchors:
            anchors.append(value)
    for sentence in re.split(r"[。；;]", text):
        if any(token in sentence for token in ("主光源", "主光", "顶灯", "窗光")):
            compact = sentence.strip()
            if compact and compact not in anchors:
                anchors.append(compact)
    return anchors[:4]


def _load_optional_json(path):
    if not os.path.exists(path):
        return {}
    return _load_json(path)


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def _append_reference_file(handle, path, title):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8-sig") as ref:
        handle.write("\n\n# %s\n\n" % title)
        handle.write(ref.read())


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: dispatch_cache.py <run_dir> <phase> [batch_size] [subshot_id ...]")
        sys.exit(2)
    run_directory = sys.argv[1]
    phase_name = sys.argv[2]
    if phase_name not in PHASE_INPUTS:
        print("ERROR: unsupported phase %s; choose one of: %s" % (
            phase_name, ", ".join(sorted(PHASE_INPUTS))
        ))
        sys.exit(2)
    size = None
    remaining = sys.argv[3:]
    if remaining and remaining[0].isdigit():
        size = int(remaining.pop(0))
    packet_paths = prepare_dispatch_packets(
        run_directory,
        phase_name,
        batch_size=size,
        subshot_ids=remaining or None,
    )
    if not packet_paths:
        print("ERROR: no dispatch items found; verify the phase input exists and contains subshots")
        sys.exit(1)
    for packet_path in packet_paths:
        print(packet_path)
