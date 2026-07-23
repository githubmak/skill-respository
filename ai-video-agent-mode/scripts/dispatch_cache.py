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
from shot_semantics import dispatch_risk, quality_contract, temporal_transition_candidate, workload_units
from context_budget import check as check_context_budget, composer_items_fit, editor_items_fit

block_source_pycache_until_run_dir()


PHASE_OUTPUTS = {
    "scene_lock": ".cache/analysis/scene_locks.json",
    "master_production": ".cache/composer/merged.prompt_package.json",
    "editor_pass2": ".cache/review/llm_gate_result.json",
}

PHASE_INPUTS = {
    "scene_lock": ".cache/orchestrator/shot_plan.json",
    "master_production": ".cache/orchestrator/shot_plan.json",
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
    if phase == "editor_pass2":
        from editor_scene_windows import build as build_editor_windows
        from pre_editor_gate import run as run_pre_editor_gate
        pre_editor_result, pre_editor_gate_path = run_pre_editor_gate(run_dir)
        if not pre_editor_result.get("pass"):
            raise ValueError("Pre-Editor local gate failed; repair Composer output before semantic review")
        items = build_editor_windows(run_dir)
    if phase == "master_production" and wanted:
        # A child-level validator finding is repaired inside its owning main
        # task. Reload just that task's siblings so the rebuilt T2V timeline
        # remains continuous instead of emitting a broken fragment.
        all_items = _extract_items(data, set())
        owner_ids = {item.get("shot_id") for item in items}
        items = [item for item in all_items if item.get("shot_id") in owner_ids]
    if phase == "scene_lock":
        items = _scene_lock_items(data)
    if not items:
        return []

    is_retry = bool(wanted)
    if phase == "master_production":
        # Composer owns the Jimeng delivery unit.  Earlier phases may retain
        # subshots for analysis, but they are changes inside one main-shot
        # task—not independently generated videos.
        items = _to_master_tasks(items)
        # Risk tiers control capacity, not quality: high-risk tasks remain in
        # 4-shot (or smaller) batches, normal tasks in 6, and truly stable
        # tasks can reach 8–10 without carrying complex context.
        size = max(int(batch_size or 4), 1)
        chunks = _dynamic_master_chunks(items, force_single=(size == 1))
    elif phase == "editor_pass2":
        chunks = _editor_review_chunks(items, batch_size)
    elif batch_size is not None:
        size = max(int(batch_size), 1)
        chunks = _analysis_chunks(items, size, phase)
    else:
        size = max(len(items), 1)
        chunks = [items]
    out_dir = os.path.join(run_dir, ".cache", "dispatch")
    os.makedirs(out_dir, exist_ok=True)
    dispatch_group_id = str(uuid.uuid4())
    group_tag = dispatch_group_id.split("-")[0]
    constraints_path = _write_constraints_sidecar(run_dir, phase, out_dir, group_tag)
    scene_lock_cache_path = None
    if phase == "master_production":
        scene_lock_cache_path = _write_scene_lock_cache(run_dir, items, out_dir, group_tag)
    paths = []

    for idx, chunk in enumerate(chunks, 1):
        dispatch_id = str(uuid.uuid4())
        dispatch_tag = dispatch_id.split("-")[0]
        public_output = os.path.join(run_dir, PHASE_OUTPUTS.get(phase, ".cache/%s_output.json" % phase))
        batch_output = _batch_output_path(public_output, phase, idx, len(chunks), dispatch_tag)
        scaffold_path = None
        packet_items = chunk
        if phase == "master_production":
            scaffold_path = _write_composer_scaffold(
                run_dir, chunk, out_dir, dispatch_tag, scene_lock_cache_path
            )
            packet_items = [_compact_composer_item(item) for item in chunk]
        retry_context_path = None
        retry_mode = None
        if is_retry:
            retry_context_path, retry_mode = _write_retry_context(
                run_dir, phase, packet_items, out_dir, dispatch_tag
            )
        batch_risk = _batch_risk(chunk)
        packet = {
            "contract_version": "jimeng-t2v-v1",
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
            "batch_capacity": batch_risk["batch_capacity"],
            "risk_tier": batch_risk["tier"],
            "risk_reasons": batch_risk["reasons"],
            "review_scope": batch_risk["review_scope"],
            "total_item_count": len(items),
            "subshot_count": sum(len(item.get("source_subshots", [item])) for item in chunk),
            "master_shot_count": len(chunk),
            "context_item_count": len(chunk),
            "items": packet_items,
            "instruction": (
                "Process only packet.items and write exactly one JSON file "
                "to _batch_output_path. Do not write output_path; the main agent merges batch files. "
                "Require contract_version=jimeng-t2v-v1 and read constraints_path for the full phase contract; "
                "a missing or older contract version requires redispatch. For master_production, start from "
                "composer_scaffold_path, preserve every locked field, and create exactly one Jimeng task per packet item; read scene_lock_cache_path once per scene; "
                "source_path is fallback context only and must not be read in full unless packet data is insufficient. "
                "Do not paste unchanged source content back into chat."
            ),
        }
        if retry_context_path:
            packet["retry_context_path"] = retry_context_path
            packet["retry_mode"] = retry_mode
            packet["is_retry"] = True
            packet["instruction"] += (
                " This is a targeted retry: read retry_context_path, repair only its failing fields, "
                "and preserve all locked fields and already-passing content."
            )
        if scaffold_path:
            packet["composer_scaffold_path"] = scaffold_path
            packet["scene_lock_cache_path"] = scene_lock_cache_path
        if phase == "editor_pass2":
            packet["review_packet_path"] = os.path.join(run_dir, ".cache", "review", "llm_gate_review.md")
            packet["pre_editor_gate_path"] = pre_editor_gate_path
            packet["emotion_camera_audit_path"] = pre_editor_result["semantic_audit_path"]
            packet["instruction"] += " For editor_pass2, read pre_editor_gate_path and emotion_camera_audit_path first. The local gate has already completed deterministic checks; review every listed performance, expectation-anchor, cut-motivation, camera-competition, and continuity issue without changing locked source facts. Light review_tier still requires a pass for its current shot and carryover; high review_tier requires the complete scene window. "
        check_context_budget(packet)
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
                    "performance_chain": ss.get("performance_chain", {}),
                    "editorial_mode": ss.get("editorial_mode", "continuous_take"),
                    "camera_beat_map": ss.get("camera_beat_map", []),
                    "sequence_context": ss.get("sequence_context", {}),
                    "dramatic_design": dict(ss.get("dramatic_design", {}) or {}),
                    "duration_design": dict(ss.get("duration_design", {}) or {}),
                    "quality_contract": quality_contract(ss),
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
            copied.setdefault("visible_characters", copied.get("characters", []))
            items.append(copied)
    return items


def _scene_lock_items(shot_plan):
    """Collapse a shot plan into one immutable lock request per scene."""
    scenes = {}
    for shot in shot_plan.get("shots", []):
        scene = str(shot.get("scene", "") or "__default__")
        entry = scenes.setdefault(scene, {
            "scene": scene, "scene_type": shot.get("scene_type", ""),
            "shot_ids": [], "subshot_ids": [], "characters": [],
        })
        entry["shot_ids"].append(shot.get("shot_id", ""))
        for subshot in shot.get("subshots", []):
            entry["subshot_ids"].append(subshot.get("subshot_id", ""))
            for character in subshot.get("characters", []):
                if character not in entry["characters"]:
                    entry["characters"].append(character)
    return list(scenes.values())


def _batch_output_path(public_output, phase, idx, total, dispatch_tag):
    """Return the only file a worker may write for this packet."""
    directory = os.path.dirname(public_output)
    if phase == "master_production":
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
        "scene_lock": (
            "Professional role: Scene Lock Agent. Return {\"scenes\":[{\"scene\":\"...\",\"space_anchor\":\"...\",\"screen_positions\":\"...\",\"wardrobe_lock\":\"...\",\"prop_state\":\"...\",\"light_source\":\"...\",\"light_direction\":\"...\",\"light_temperature\":\"...\",\"audio_policy\":\"...\"}]} with one immutable lock per packet item. Every required value is one non-empty flat string: do not nest lighting, wardrobe, props, positions, or audio objects. Never write subshot analysis, camera design, performance, dialogue, or prompts."
        ),
        "master_production": (
            "Professional role: You are a short-drama AI video director and prompt supervisor. "
            "Create one risk-controlled current-contract shot per subshot with a strict action budget and primary/supporting/background performance priority; "
            "do not invent plot, rewrite dialogue, redesign clothing, add unconfirmed props, or expose engineering fields. "
            "Do not force characters to face the lens: distinguish camera-front position from character-facing direction, and only write direct-to-camera eyeline when explicitly sourced. Read qa_metadata.dramatic_design.coverage_role before choosing framing: only dialogue_performance or reaction may use the low-risk fallback of a medium/medium-close fixed frame. establish_space needs readable space, relationship_blocking needs the relationship geometry, prop_information needs the information-bearing prop or hand detail, movement_transition needs motivated movement coverage, power_reversal needs a motivated reframing or angle response, and environment_bridge needs environmental continuity. This is a narrative reason, not a shot-size quota; do not overwrite the locked coverage_role. "
            "Execute the Director's performance_chain before inventing shot language: trigger, facial control, detail/prop leak, body follow-through, voice/breath landing, then residue. In shot_group, natural reaction/detail cuts and reframes are allowed only at those declared beats; preserve identity, prop state, axis, light, and the previous beat's residue. A single T2V task may hand attention from A to B once, never return B to A; any return cut is a new T2V task joined in post from the declared carryover. When a visible speaker has a supporting listener, fill listener_reaction_plan with one causal, low-amplitude closed-mouth reaction grounded in the timeline; do not freeze the listener or give them a competing action. Fight contexts use fight_continuity instead: both participants must react through the same action→force/judgment→result chain, not listener reactions. "
            "Before writing the performance contract, semantically interpret any packet expectation_anchor instead of relying on its type label: distinguish a literal human/character expectation, figurative personification, need-or-lack, or symbolic association; only literal agents can be staged as intentional performers, and absent satisfaction objects must not be shown as present. Bind only source-supported visible progress, camera decision, return reaction, and unresolved end state. Never cut to a static object merely because a character expects it; a detail cut or reframe needs that declared progress event. "
            "For every shot with visible physical characters, fill qa_metadata.performance_causality with calibrated tension intent, trigger, ordered response, physical logic, motion boundary, hold strategy, and end residue. "
            "Also fill qa_metadata.performance_contract, qa_metadata.continuity_contract, and qa_metadata.reroll_control before writing full_prompt: performance_contract must bind expression, body action, eyeline, reaction delay, voice/breath control, one viewer empathy anchor, one readable image moment, a visible start-to-end progression (or justified intentional hold with 1-2 life signs), camera pressure, scene pressure, and end residue into the subshot group; stable framing never authorizes a frozen performer. Each dialogue/OS/OV event also needs a literal breath_pause_plan with timed pre-utterance breath and end release; add a timed mid-line pause only at an actual clause, thought, or emotional turn, never mechanically at every punctuation mark. continuity_contract must preserve start/end anchors, eyelines, prop state, light, and next carryover. Any position, eyeline or movable-prop change must set state_change=true and record subject/from_state/to_state/cause/time_range; cause must be a visible action or explicit transition. reroll_control must score T2V identity, costume, screen-side, action, camera, and lip-sync risk, list concrete mitigation steps, and set manual_first_pass_check for rising/peak character shots. "
            "If qa_metadata.temporal_transition_contract.kind is not none, obey its source trigger exactly. It is a candidate, not an instruction to decorate: either write one bounded in-model transition whose single effect is derived from this scene's actual event, or record a source-faithful reason to use a normal cut. An enabled transition needs a bounded time range, one effect and its source basis, explicit before/after states, one literal prompt anchor, audio bridge, closed-mouth/OS-OV boundary, and a fallback. Never stack effects, fabricate a past event, or change face, costume, scene, or period without the declared transition state. Treat every enabled temporal transition as high reroll risk with manual first-pass review. "
            "Copy the locked quality_contract exactly. Fill qa_metadata.quality_evidence for every required_evidence key as {section, fragment}; section is one of 主体与空间锁定/主镜头连续规则/子镜头组/光照、声音与稳定约束 and fragment is a 3+ character literal phrase that appears in that section. This applies equally to environment and object inserts. "
            "For every locked dialogue event, preserve ref/kind/speaker/text exactly and fill its time_range, speaker_visibility, facial_state, body_state, delivery, and lip_sync. Dialogue/OS text must never be rewritten. "
            "Use §B-§E in this sidecar, then read packet.format_example_path and packet.quality_exemplar_path exactly once. "
            "Examples are structure-only: absorb causal performance chains, prop-state transfer, timeline continuity, system-text safe zones, dialogue/lip-sync boundaries, end residue, and reroll controls, but never inherit example genre, soft-light rhythm, hotel/urban setting, manhwa style, clothing, character relationships, or specific prop events unless the current source/config provides them. "
            "This is Jimeng T2V-only: never include I2V/R2V, reference assets, image handles, or fabricated locks. Preserve identity through concise recurring identity anchors, costume, screen-left/right placement, facing direction, scene anchor, and previous end state. For fight shots, reduce reroll risk by limiting speed, amplitude, contact beats, and camera shake, then split overly complex choreography into locked consecutive clips. "
            "Start from packet.composer_scaffold_path and preserve all locked fields. Read packet.scene_lock_cache_path once per scene instead of rediscovering shared light, space, costume, canvas, style, or generation settings. "
            "full_prompt contains exactly 生成规格/主体与空间锁定/主镜头连续规则/子镜头组/光照、声音与稳定约束; "
            "Within every time range, lead with one in-focus subject and screen position, then one trigger/action, one visible performance proof, voice/lip-sync boundary, and only the stability controls needed now. Do not repeat already-locked style, wardrobe, light, space, or generic prohibitions. Replace abstract outcome language with visible evidence; do not spend duration or characters on filler. "
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
        "scene_lock": ("A",),
        "master_production": ("B",),
        "editor_pass2": ("B", "C"),
    }.get(phase, tuple(sections))
    selected = [sections[key] for key in wanted if key in sections]
    # Composer needs the executable prompt contract, not B4's advisory prose or
    # unrelated specialty branches.  Keeping the sidecar narrow reduces Agent
    # context without changing any locked packet/scaffold fields.
    if phase == "master_production" and "B" in sections:
        selected = [_select_b_subsections(sections["B"], {"B0", "B1", "B2", "B3", "B5", "B6", "B7"})]
    return "\n\n".join([preamble] + selected) + "\n"


def _select_b_subsections(section, wanted):
    matches = list(__import__("re").finditer(r"(?m)^### (B\d+)\.", section))
    if not matches:
        return section
    preamble = section[:matches[0].start()].rstrip()
    parts = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        if match.group(1) in wanted:
            parts.append(section[match.start():end].rstrip())
    return "\n\n".join([preamble] + parts)


def _composer_chunks(items, max_items, respect_chains=True):
    """Keep continuity groups intact while shrinking high-context batches."""
    shot_groups = []
    for item in items:
        group_id = _composer_group_id(item) if respect_chains else str(item.get("subshot_id", ""))
        if shot_groups and shot_groups[-1][0] == group_id:
            shot_groups[-1][1].append(item)
        else:
            shot_groups.append([group_id, [item]])
    chunks = []
    current = []
    current_weight = 0
    weight_budget = max_items * 3
    item_cap = max_items * 2
    for _, group in shot_groups:
        group_weight = sum(workload_units(item, "master_production") for item in group)
        if current and (len(current) + len(group) > item_cap or current_weight + group_weight > weight_budget):
            chunks.append(current)
            current = []
            current_weight = 0
        current.extend(group)
        current_weight += group_weight
        if len(current) >= item_cap or current_weight >= weight_budget:
            chunks.append(current)
            current = []
            current_weight = 0
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


def _to_master_tasks(items):
    """Fold Director subshots into the one generation task users submit.

    A retry selected by a child id expands only to its owning main shot, which
    prevents impossible partial rewrites of a single continuous T2V task.
    """
    groups, order = {}, []
    for item in items:
        key = str(item.get("shot_id", "") or item.get("subshot_id", ""))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(item)
    masters = []
    for key in order:
        children = groups[key]
        first = dict(children[0])
        first["shot_id"] = key
        first["subshot_id"] = key  # output identity is the main shot
        first["source_subshot_ids"] = [str(child.get("subshot_id", "")) for child in children]
        first["source_subshots"] = children
        first["duration"] = round(sum(float(child.get("duration", 0) or 0) for child in children), 3)
        first["editorial_mode"] = "shot_group" if len(children) > 1 else children[0].get("editorial_mode", "continuous_take")
        first["dialogue_refs"] = [ref for child in children for ref in child.get("dialogue_refs", [])]
        first["dialogue_events"] = [event for child in children for event in child.get("dialogue_events", [])]
        first["temporal_transition_candidate"] = temporal_transition_candidate(first)
        first["master_task"] = True
        masters.append(first)
    return masters


def _analysis_chunks(items, max_items, phase):
    """Bound both item count and complexity so simple inserts batch efficiently."""
    weight_budget = {
        "scene_lock": max_items * 2,
        "master_production": max_items * 2,
    }.get(phase, max_items * 2)
    item_cap = max_items * 2
    chunks, current, current_weight = [], [], 0
    for item in items:
        weight = workload_units(item, phase)
        if current and (len(current) >= item_cap or current_weight + weight > weight_budget):
            chunks.append(current)
            current, current_weight = [], 0
        current.append(item)
        current_weight += weight
    if current:
        chunks.append(current)
    return chunks or [items]


def _dynamic_master_chunks(items, force_single=False):
    """Batch consecutive main tasks by their strictest risk capacity.

    Never split a declared continuity chain merely to fill a larger low-risk
    batch.  Such an oversized chain is intentionally retained as one batch and
    marked high risk, preserving its shared context.
    """
    if force_single:
        return [[item] for item in items]
    groups = []
    for item in items:
        group_id = _composer_group_id(item)
        if groups and groups[-1][0] == group_id:
            groups[-1][1].append(item)
        else:
            groups.append([group_id, [item]])
    chunks, current, capacity = [], [], 10
    for _group_id, group in groups:
        group_risk = _batch_risk(group)
        group_capacity = group_risk["batch_capacity"]
        next_capacity = min(capacity, group_capacity) if current else group_capacity
        compact_candidate = [_compact_composer_item(item) for item in current + group]
        if current and (
            len(current) + len(group) > next_capacity
            or not composer_items_fit(compact_candidate)
        ):
            chunks.append(current)
            current, capacity = [], 10
            next_capacity = group_capacity
        if not current and not composer_items_fit([_compact_composer_item(item) for item in group]):
            raise ValueError(
                "single Master Production task exceeds the packet context budget; "
                "split that main shot during Phase 1 instead of truncating its source facts"
            )
        current.extend(group)
        capacity = next_capacity
        if len(current) >= capacity:
            chunks.append(current)
            current, capacity = [], 10
    if current:
        chunks.append(current)
    return chunks or [items]


def _editor_review_chunks(windows, batch_size=None):
    """Batch complete review capsules without exceeding their context budget."""
    tiers = {"light": 10, "standard": 6, "high": 4}
    requested = max(int(batch_size), 1) if batch_size is not None else None
    chunks, current, capacity = [], [], 10
    for window in windows:
        tier = str(window.get("review_tier", "standard"))
        window_capacity = tiers.get(tier, 6)
        if requested is not None:
            window_capacity = min(window_capacity, requested)
        next_capacity = min(capacity, window_capacity) if current else window_capacity
        if current and (len(current) >= next_capacity or not editor_items_fit(current + [window])):
            chunks.append(current)
            current, capacity, next_capacity = [], 10, window_capacity
        if not editor_items_fit([window]):
            raise ValueError("single Editor review capsule exceeds context budget; split the main shot")
        current.append(window)
        capacity = next_capacity
    if current:
        chunks.append(current)
    return chunks or [windows]


def _batch_risk(items):
    tiers = {"light": 0, "standard": 1, "high": 2}
    risks = [dispatch_risk(item) for item in items]
    selected = max(risks, key=lambda risk: tiers.get(risk.get("tier"), 1)) if risks else dispatch_risk({})
    reasons = []
    for risk in risks:
        for reason in risk.get("reasons", []):
            if reason not in reasons:
                reasons.append(reason)
    return {
        "tier": selected.get("tier", "standard"),
        "reasons": reasons or ["normal_contract"],
        "batch_capacity": int(selected.get("batch_capacity", 6)),
        "review_scope": selected.get("review_scope", "bounded_scene_window"),
    }


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
            "mode": "t2v",
            "audio_enabled": bool(control.get("audio_enabled", True)),
        }
        duration = item.get("duration", 0)
        shots.append({
            "shot_id": item.get("shot_id", ""),
            "subshot_id": item.get("subshot_id", ""),
            "duration": duration,
            "full_prompt": "生成规格：\n\n主体与空间锁定：\n\n主镜头连续规则：\n\n子镜头组：\n\n光照、声音与稳定约束：",
            "negative_prompt": "{{NEGATIVE_PROMPT_AUTO_INJECT}}",
            "qa_metadata": {
                "dramatic_goal": "",
                "dramatic_design": dict(item.get("dramatic_design", {}) or {}),
                "duration_design": dict(item.get("duration_design", {}) or {}),
                "performance_priority": {"primary": "", "supporting": [], "background": []},
                "action_budget": {
                    "primary_action_count": 0,
                    "emotion_turn_count": 0,
                    "supporting_reaction_count": 0,
                    "physical_camera_move_count": 0,
                    "editorial_response_count": 0,
                },
                "editorial_mode": item.get("editorial_mode", "continuous_take"),
                "camera_beat_map": list(item.get("camera_beat_map", []) or []),
                "sequence_context": dict(item.get("sequence_context", {}) or {}),
                "viewpoint": item.get("viewpoint", "objective"),
                "visual_hierarchy": item.get("visual_hierarchy", ""),
                "entry_strategy": item.get("entry_strategy", "none"),
                "reveal_strategy": item.get("reveal_strategy", "direct"),
                "focus_strategy": item.get("focus_strategy", "single_plane"),
                "temporal_transition_contract": _transition_contract_scaffold(item),
                "quality_contract": dict(item.get("quality_contract", {}) or {}),
                "quality_evidence": {},
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
                    "visual_progression": "",
                    "suppression_or_release": "",
                    "camera_pressure": "",
                    "scene_pressure": "",
                    "end_residue": "",
                },
                "expectation_anchor": {
                    "applicable": False,
                    "semantic_mode": "none",
                    "anchor_type": "none",
                    "anchor": "N/A",
                    "expecting_subject": "N/A",
                    "source_interpretation": "N/A",
                    "start_state": "N/A",
                    "progress_event": "N/A",
                    "detail_cut_rule": "N/A",
                    "return_reaction": "N/A",
                    "end_state": "N/A",
                },
                "continuity_contract": {
                    "start_anchor": "",
                    "end_anchor": "",
                    "position_continuity": "",
                    "eyeline_continuity": "",
                    "prop_state": "",
                    "lighting_continuity": "",
                    "next_carryover": "",
                    "state_change": False,
                    "state_transitions": [],
                },
                "reroll_control": {
                    "risk_level": "",
                    "identity_anchor": "",
                    "motion_anchor": "",
                    "scene_anchor": "",
                    "camera_anchor": "",
                    "risk_reason": "",
                    "mitigation_steps": [],
                    "manual_first_pass_check": False,
                },
                "listener_reaction_plan": {},
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
                        "breath_pause_plan": "",
                        "lip_sync": None,
                    }
                    for event in item.get("dialogue_events", [])
                    if isinstance(event, dict)
                ],
                "dialogue_refs": list(item.get("dialogue_refs", []) or []),
            },
            "generation_control": control,
            "_scene_lock_ref": str(item.get("scene", "") or "__default__"),
            "source_subshot_ids": list(item.get("source_subshot_ids", [item.get("subshot_id", "")])),
            "source_subshots": [
                {"subshot_id": child.get("subshot_id", ""), "duration": child.get("duration", 0),
                 "scene_delta": {"lighting": child.get("lighting", ""), "spatial": child.get("spatial_map", {})},
                 "base_action": child.get("base_action", ""), "camera_beat_map": child.get("camera_beat_map", [])}
                for child in item.get("source_subshots", [item])
            ],
        })
    payload = {
        "contract_version": "jimeng-t2v-v1",
        "locked_fields": [
            "shot_id", "subshot_id", "duration", "negative_prompt",
            "source_subshot_ids",
            "qa_metadata.dialogue_refs", "qa_metadata.dialogue_events[].ref/kind/speaker/text",
            "qa_metadata.editorial_mode", "qa_metadata.camera_beat_map", "qa_metadata.sequence_context",
            "qa_metadata.quality_contract", "qa_metadata.dramatic_design", "qa_metadata.duration_design",
            "qa_metadata.viewpoint", "qa_metadata.visual_hierarchy", "qa_metadata.entry_strategy",
            "qa_metadata.reveal_strategy", "qa_metadata.focus_strategy",
            "generation_control",
        ],
        "scene_lock_cache_path": scene_lock_cache_path,
        "shots": shots,
    }
    path = os.path.join(dispatch_dir, "master_production_%s_scaffold.json" % dispatch_tag)
    _write_json(path, payload)
    return path


def _transition_contract_scaffold(item):
    candidate = temporal_transition_candidate(item)
    return {
        "enabled": False,
        "kind": candidate.get("kind", "none"),
        "source_trigger": candidate.get("source_trigger", ""),
        "decision_reason": "",
        "time_range": "",
        "effect": "",
        "effect_source_basis": "",
        "from_state": "",
        "to_state": "",
        "audio_bridge": "",
        "lip_sync": False,
        "prompt_anchor": "",
        "fallback": "split_with_matched_cut",
    }


def _write_retry_context(run_dir, phase, items, dispatch_dir, dispatch_tag):
    """Expose only validator facts for the retry batch, never the full prior output."""
    sources = _load_optional_json(os.path.join(run_dir, ".cache", "sources.json"))
    selected = []
    max_retries = 0
    for item in items:
        subshot_id = str(item.get("subshot_id", "") or "")
        record = sources.get(subshot_id, {}) if isinstance(sources, dict) else {}
        retries = int(record.get("retries", 0) or 0)
        max_retries = max(max_retries, retries)
        selected.append({
            "subshot_id": subshot_id,
            "issues": record.get("qa_issues", []),
            "passed_phases": record.get("passed_phases", []),
            "repair_fields": _repair_fields(record.get("qa_issues", [])),
        })
    mode = "validator_targeted" if max_retries <= 1 else "single_subshot_field_repair"
    payload = {
        "contract_version": "jimeng-t2v-v1",
        "phase": phase,
        "retry_mode": mode,
        "repair_scope": "only listed subshots and validator fields",
        "items": selected,
    }
    path = os.path.join(dispatch_dir, "%s_%s_retry.json" % (phase, dispatch_tag))
    _write_json(path, payload)
    return path, mode


def _repair_fields(issues):
    fields = []
    for issue in issues if isinstance(issues, list) else []:
        text = str(issue)
        for token in ("full_prompt", "negative_prompt", "generation_control", "qa_metadata", "dialogue_events", "performance_contract", "continuity_contract", "reroll_control", "camera_beat_map"):
            if token in text and token not in fields:
                fields.append(token)
    return fields or ["validator_reported_field"]


def _write_scene_lock_cache(run_dir, items, dispatch_dir, group_tag):
    approved_path = os.path.join(run_dir, ".cache", "analysis", "scene_locks.json")
    if os.path.exists(approved_path):
        return approved_path
    config = _load_optional_json(os.path.join(run_dir, "project_config.json"))
    scenes = {}
    for item in items:
        scene = str(item.get("scene", "") or "__default__")
        entry = scenes.setdefault(scene, {
            "scene": scene,
            "canvas": config.get("canvas", ""),
            "visual_style": config.get("visual_style", ""),
            "performance_direction": config.get("performance_direction", {}),
            "costumes": _scene_costumes(config.get("costume_map", {}), scene),
            "generation_control": config.get("generation_control", {}),
            "shared_light_anchors": [],
            "lighting_by_subshot": {},
            "spatial_by_subshot": {},
            "continuity_by_subshot": {},
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
        continuity = item.get("scene_continuity", {})
        if isinstance(continuity, dict) and any(str(value or "").strip() for value in continuity.values()):
            entry["continuity_by_subshot"][sid] = continuity
    path = os.path.join(dispatch_dir, "master_production_%s_scene_locks.json" % group_tag)
    _write_json(path, {"contract_version": "jimeng-t2v-v1", "scenes": scenes})
    return path


def _compact_composer_item(item):
    copied = dict(item)
    # The scene lock carries immutable facts once per scene.  The compact item
    # carries only per-subshot changes, preventing every Composer worker from
    # rediscovering or rephrasing the same environment and lighting setup.
    copied["scene_delta"] = {
        "lighting": str(item.get("lighting", "") or ""),
        "spatial": str(item.get("axis_space", item.get("spatial_map", "")) or ""),
        "continuity": dict(item.get("scene_continuity", {}) or {}) if isinstance(item.get("scene_continuity"), dict) else {},
    }
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
