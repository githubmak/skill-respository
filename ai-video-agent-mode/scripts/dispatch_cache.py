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
import hashlib

if not os.environ.get("PYTHONPYCACHEPREFIX") and not getattr(sys, "pycache_prefix", None):
    sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))
from pycache_policy import block_source_pycache_until_run_dir, ensure_pycache_prefix
from shot_semantics import (
    dispatch_risk,
    functional_surface_risk,
    quality_contract,
    temporal_transition_candidate,
    validation_profile,
)
from context_budget import check as check_context_budget
from batch_planner import analysis_chunks as _analysis_chunks, batch_risk as _batch_risk
from batch_planner import dynamic_master_chunks as _plan_dynamic_master_chunks
from batch_planner import editor_review_chunks as _editor_review_chunks
from contract_registry import PROMPT_CONTRACT_VERSION, RISK_GATED_QA_FIELDS
from scene_motion_plan import build as build_scene_motion_plan
from scene_texture_plan import build as build_scene_texture_plan, contract_for_scene

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
        items = build_editor_windows(run_dir, shot_ids=wanted or None)
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
        size = max(int(batch_size or 10), 1)
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
        _motion_plan, scene_motion_plan_path = build_scene_motion_plan(run_dir)
        scene_texture_plan, scene_texture_plan_path = build_scene_texture_plan(run_dir, scene_lock_cache_path)
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
                run_dir, chunk, out_dir, dispatch_tag, scene_lock_cache_path,
                scene_motion_plan_path, scene_texture_plan_path, scene_texture_plan,
            )
            packet_items = [_compact_composer_item(item) for item in chunk]
        retry_context_path = None
        retry_mode = None
        if is_retry and phase == "master_production":
            retry_context_path, retry_mode = _write_retry_context(
                run_dir, phase, packet_items, out_dir, dispatch_tag
            )
        batch_risk = _batch_risk(chunk)
        packet = {
            "contract_version": PROMPT_CONTRACT_VERSION,
            "dispatch_id": dispatch_id,
            "dispatch_group_id": dispatch_group_id,
            "created_at": time.time(),
            "phase": phase,
            "run_dir": run_dir,
            "source_path": source_path,
            "source_sha256": _sha256(source_path),
            "project_config_path": os.path.join(run_dir, "project_config.json"),
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
                "Require the current contract_version from contract_registry and read constraints_path for the full phase contract; "
                "a missing or older contract version requires redispatch. For master_production, start from "
                "composer_scaffold_path, preserve every locked field, and create exactly one Jimeng task per packet item; each task serves one narrative_beat_id only, with any shot_group used only as internal coverage of that beat; read scene_lock_cache_path once per scene; "
                "source_path is fallback context only and must not be read in full unless packet data is insufficient. "
                "Do not paste unchanged source content back into chat."
            ),
        }
        if phase == "master_production":
            packet["local_validation_command"] = [
                sys.executable,
                os.path.join(os.path.dirname(__file__), "validate_composer_output.py"),
                batch_output,
                "--run-dir",
                run_dir,
            ]
            packet["context_policy"] = {
                "fixed_global_context": [
                    "project_config_path",
                    "constraints_path",
                    "composer_scaffold_path",
                    "scene_lock_cache_path",
                ],
                "per_shot_context": [
                    "packet.items[].source_subshots",
                    "packet.items[].dialogue_events",
                    "packet.items[].dramatic_design",
                    "packet.items[].duration_design",
                    "packet.items[].execution_hints",
                ],
                "history_policy": "Do not read full source history by default. Use scene locks plus packet items; cross-shot continuity must come from packet sequence_context, continuity fields, and scaffold locks.",
                "quality_policy": "Fill core fields and scaffold-present risk fields only. Do not recreate omissions; all gates remain mandatory.",
            }
            packet["instruction"] += (
                " Composer batch output top-level must be exactly {\"shots\": [...]}; "
                "do not include contract_version in the batch file. Hard validation notes: "
                "qa_metadata.performance_priority must partition exactly the packet item visible_characters for that shot "
                "(one visible primary, visible-only supporting/background, no offscreen character, no scene roster, no overlap); "
                "negative words, negative headings, and negative instructions must stay only in negative_prompt and never appear in full_prompt; "
                "relationship_blocking or movement_transition coverage cannot use a default fixed mid/mid-close setup unless full_prompt also gives a concrete screen-side, foreground-shoulder, or scene-anchor reason and a responsive camera behavior; "
                "pressure_release_design.release_trigger and story_punch_contract audience question must be visible in full_prompt as a concrete object, action, sound, distance, or end-frame state; "
                "insert shots are allowed only inside shot_group segments with an explicit insert function, never mixed into continuous_take. "
                "Before final response, run the exact local_validation_command from this packet, including --run-dir. "
                "If validation fails, patch only the reported fields and rerun until PASS; do not claim PASS from a partial or different command."
            )
        if retry_context_path:
            packet["retry_context_path"] = retry_context_path
            packet["is_retry"] = True
            packet["instruction"] += (
                " This is a targeted retry: read retry_context_path, repair only its failing fields, "
                "and preserve all locked fields and already-passing content."
            )
            example_paths = _retry_examples(retry_context_path)
            if example_paths:
                packet["example_paths"] = example_paths
                packet["instruction"] += " Read only the listed example_paths; they are structural repair references, never creative templates."
        if scaffold_path:
            packet["composer_scaffold_path"] = scaffold_path
            packet["scene_lock_cache_path"] = scene_lock_cache_path
        if phase == "editor_pass2":
            packet["targeted_review"] = bool(wanted)
            packet["target_shot_ids"] = sorted(wanted)
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
    _write_active_manifest(
        run_dir,
        phase,
        source_path,
        dispatch_group_id,
        paths,
        is_retry=is_retry,
        target_ids=sorted(wanted),
    )
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


def active_packet_paths(run_dir, phase):
    """Return the current effective packet queue for a phase.

    The dispatch directory is append-only for auditability.  This manifest is
    the small mutable index that tells the runner which packet files still
    belong to the current attempt.  If an older run lacks the manifest, callers
    can fall back to scanning the directory.
    """
    manifest = _load_optional_json(_active_manifest_path(run_dir, phase))
    if manifest.get("phase") != phase:
        return []
    paths = []
    for entry in manifest.get("packets", []):
        if isinstance(entry, dict) and entry.get("effective") is False:
            continue
        path = entry.get("packet_path") if isinstance(entry, dict) else ""
        if path and os.path.exists(path):
            paths.append(path)
    return paths


def _active_manifest_path(run_dir, phase):
    safe_phase = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(phase or "unknown"))
    return os.path.join(run_dir, ".cache", "dispatch", "active_%s_manifest.json" % safe_phase)


def _write_active_manifest(run_dir, phase, source_path, dispatch_group_id, packet_paths, is_retry=False, target_ids=None):
    target_ids = set(target_ids or [])
    packet_path_set = {os.path.abspath(path) for path in packet_paths or []}
    current = _load_optional_json(_active_manifest_path(run_dir, phase))
    entries = current.get("packets", []) if isinstance(current.get("packets"), list) else []
    entries = [
        entry for entry in entries
        if isinstance(entry, dict) and os.path.exists(str(entry.get("packet_path", "") or ""))
        and os.path.abspath(str(entry.get("packet_path", "") or "")) not in packet_path_set
    ]
    superseded = current.get("superseded_packets", []) if isinstance(current.get("superseded_packets"), list) else []
    attempt = int(current.get("attempt", 0) or 0) + 1
    if is_retry and target_ids:
        # Keep original mixed batches because they may contain unaffected shots,
        # but drop older retry packets that are fully covered by this newer
        # retry target set.  New retry packets are appended so merge order lets
        # them override original fields.
        new_retry_fields = _retry_fields_for_paths(packet_paths)
        filtered = []
        for entry in entries:
            ids = set(entry.get("shot_ids", [])) if isinstance(entry, dict) else set()
            previous_retry = bool(entry.get("is_retry")) if isinstance(entry, dict) else False
            previous_fields = _retry_fields_for_entry(entry) if previous_retry else {}
            if previous_retry and ids and ids <= target_ids and _retry_fields_covered(previous_fields, new_retry_fields, ids):
                superseded.append(_superseded_manifest_entry(entry, attempt, "retry_replaced_by_newer_target"))
                continue
            filtered.append(entry)
        entries = filtered
    elif not is_retry:
        for entry in entries:
            if isinstance(entry, dict):
                superseded.append(_superseded_manifest_entry(entry, attempt, "fresh_dispatch_group"))
        entries = []
    source_sha256 = _sha256(source_path) if source_path and os.path.isfile(source_path) else ""
    for packet_path in packet_paths:
        packet = _load_json(packet_path)
        entries.append({
            "packet_path": os.path.abspath(packet_path),
            "dispatch_id": packet.get("dispatch_id", ""),
            "dispatch_group_id": packet.get("dispatch_group_id", dispatch_group_id),
            "created_at": packet.get("created_at"),
            "is_retry": bool(packet.get("is_retry") or packet.get("retry_context_path")),
            "retry_fields_by_shot": _json_retry_fields(_retry_fields_for_packet(packet)),
            "shot_ids": _packet_shot_ids(packet),
            "source_sha256": packet.get("source_sha256", source_sha256),
            "attempt": attempt,
            "effective": True,
        })
    active_shot_ids = sorted({
        shot_id
        for entry in entries if isinstance(entry, dict)
        for shot_id in entry.get("shot_ids", [])
        if str(shot_id).strip()
    })
    _write_json(_active_manifest_path(run_dir, phase), {
        "contract_version": PROMPT_CONTRACT_VERSION,
        "phase": phase,
        "source_path": source_path,
        "source_sha256": source_sha256,
        "dispatch_group_id": dispatch_group_id,
        "updated_at": time.time(),
        "attempt": attempt,
        "active_packet_count": len(entries),
        "active_retry_packet_count": sum(1 for entry in entries if isinstance(entry, dict) and entry.get("is_retry")),
        "active_shot_ids": active_shot_ids,
        "superseded_packet_count": len(superseded),
        "superseded_packets": superseded[-200:],
        "packets": entries,
    })


def _superseded_manifest_entry(entry, attempt, reason):
    copied = dict(entry)
    copied["effective"] = False
    copied["superseded_at"] = time.time()
    copied["superseded_by_attempt"] = attempt
    copied["superseded_reason"] = reason
    return copied


def _retry_fields_for_paths(packet_paths):
    result = {}
    for path in packet_paths or []:
        try:
            packet = _load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        for shot_id, fields in _retry_fields_for_packet(packet).items():
            bucket = result.setdefault(shot_id, set())
            bucket.update(fields)
    return result


def _retry_fields_for_entry(entry):
    if not isinstance(entry, dict):
        return {}
    scoped = entry.get("retry_fields_by_shot")
    if isinstance(scoped, dict) and scoped:
        return {
            str(shot_id): set(str(field) for field in fields if str(field).strip())
            for shot_id, fields in scoped.items() if isinstance(fields, list)
        }
    path = str(entry.get("packet_path", "") or "")
    if not path or not os.path.exists(path):
        return {}
    try:
        return _retry_fields_for_packet(_load_json(path))
    except (OSError, json.JSONDecodeError):
        return {}


def _retry_fields_for_packet(packet):
    context_path = packet.get("retry_context_path") if isinstance(packet, dict) else ""
    if not context_path or not os.path.exists(context_path):
        return {}
    try:
        context = _load_json(context_path)
    except (OSError, json.JSONDecodeError):
        return {}
    fields_by_shot = context.get("fields_by_main_shot", {}) if context.get("mode") == "field_patch" else {}
    result = {}
    for shot_id, fields in fields_by_shot.items() if isinstance(fields_by_shot, dict) else []:
        result[str(shot_id)] = set(str(field) for field in fields if str(field).strip()) if isinstance(fields, list) else set()
    return result


def _json_retry_fields(fields_by_shot):
    return {
        shot_id: sorted(fields)
        for shot_id, fields in (fields_by_shot or {}).items()
    }


def _retry_fields_covered(previous_fields, new_fields, shot_ids):
    """Only replace an older retry when the newer retry covers its field scope."""
    if not previous_fields:
        return True
    for shot_id in shot_ids:
        previous = set(previous_fields.get(str(shot_id), set()))
        if not previous:
            continue
        current = set(new_fields.get(str(shot_id), set()))
        if not previous <= current:
            return False
    return True


def _packet_shot_ids(packet):
    ids = []
    for item in packet.get("items", []) if isinstance(packet.get("items"), list) else []:
        if not isinstance(item, dict):
            continue
        shot_id = str(item.get("shot_id", "") or item.get("subshot_id", "") or "").strip()
        if shot_id and shot_id not in ids:
            ids.append(shot_id)
    return ids


def _extract_items(data, wanted):
    if "shots" in data:
        items = []
        for shot in data.get("shots", []):
            shot_id = shot.get("shot_id", "")
            if isinstance(shot, dict) and "subshots" not in shot and shot.get("subshot_id"):
                ssid = shot.get("subshot_id", "")
                if wanted and ssid not in wanted and shot_id not in wanted:
                    continue
                copied = dict(shot)
                copied.setdefault("visible_characters", copied.get("characters", []))
                items.append(copied)
                continue
            for ss in shot.get("subshots", []):
                ssid = ss.get("subshot_id", "")
                if wanted and ssid not in wanted and shot_id not in wanted:
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


def _read_text_if_exists(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return f.read().strip()
    except OSError:
        return ""


def _phase_note_text(skill_dir, phase):
    """Load dispatch role notes from references/dispatch.

    The Python fallback below keeps older installs recoverable, but maintained
    phase instructions live in Markdown so quality rules are reviewable without
    editing dispatcher code.
    """
    note_files = {
        "scene_lock": "scene_lock_note.md",
        "master_production": "master_production_note.md",
        "editor_pass2": "editor_pass2_note.md",
    }
    filename = note_files.get(phase)
    if not filename:
        return ""
    return _read_text_if_exists(os.path.join(skill_dir, "references", "dispatch", filename))


def _write_constraints_sidecar(run_dir, phase, dispatch_dir, dispatch_tag):
    skill_dir = os.path.dirname(os.path.dirname(__file__))
    source = os.path.join(skill_dir, "references", "format_constraints.md")
    out_path = os.path.join(dispatch_dir, "%s_%s_constraints.md" % (phase, dispatch_tag))
    phase_note = _phase_note_text(skill_dir, phase) or {
        "scene_lock": "专业角色：场景锁定 Agent。请返回扁平 scene lock JSON；不得写提示词正文、运镜或人物表演。",
        "master_production": "专业角色：AI 短剧导演与提示词监督。遵守本 sidecar 的 T2V-only、source basemap、质量合同、直投密度和 provenance 规则。",
        "editor_pass2": "使用 §B/§C 作为审查上下文。不要改写纯格式问题；只返回语义审查 JSON。",
    }.get(phase, "遵守所引用阶段的契约。")
    with open(source, "r", encoding="utf-8-sig") as f:
        body = f.read()
    selected_contract = _select_contract_sections(body, phase)
    contract_slices = _phase_contract_slice_text(skill_dir, phase)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Dispatch Constraints\n\n")
        f.write("phase: %s\n\n" % phase)
        f.write(phase_note + "\n\n")
        f.write(selected_contract)
        if contract_slices:
            f.write("\n" + contract_slices)
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
        # Scene Lock is governed by scene_lock_note.md.  §A is an archive-only
        # analysis format and must never be injected into a current dispatch.
        "scene_lock": (),
        "master_production": ("B",),
        "editor_pass2": (),
    }.get(phase, tuple(sections))
    selected = [sections[key] for key in wanted if key in sections]
    # Composer needs the executable prompt contract, not B4's advisory prose or
    # unrelated specialty branches.  Keeping the sidecar narrow reduces Agent
    # context without changing any locked packet/scaffold fields.
    if phase == "master_production" and "B" in sections:
        selected = [_select_b_subsections(sections["B"], {"B2", "B5", "B6"})]
    return "\n\n".join([preamble] + selected) + "\n"


def _phase_contract_slice_text(skill_dir, phase):
    """Load compact decision slices only for phases that create prompts."""
    slice_files = {
        "master_production": (
            "direct_copy_contract.md",
            "source_basemap_contract.md",
            "visual_quality_contract.md",
            "aesthetic_directing_contract.md",
        ),
    }.get(phase, ())
    parts = []
    for filename in slice_files:
        relative = os.path.join("references", "contracts", filename)
        text = _read_text_if_exists(os.path.join(skill_dir, relative))
        if text:
            if filename == "direct_copy_contract.md":
                # §B0 is already included verbatim. Keep this sidecar a locator
                # for the fast contract instead of duplicating its full prose.
                text = (
                    "# 快速直投合同定位\n\n"
                    "直投正文由 direct_prompt_compiler.py 从同一事实源编译；必须保留可见构图、单一路径运镜、"
                    "对白口型、光影材质和最后20%终端锁定，不写内部合同名或负向概念；详规见本文件。\n"
                )
            parts.append("# Included Contract Slice: %s\n\n%s" % (relative, text))
    return "\n\n".join(parts).rstrip() + ("\n" if parts else "")


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


def _dynamic_master_chunks(items, force_single=False):
    return _plan_dynamic_master_chunks(items, _compact_composer_item, force_single=force_single)


def _write_composer_scaffold(
    run_dir, items, dispatch_dir, dispatch_tag, scene_lock_cache_path,
    scene_motion_plan_path="", scene_texture_plan_path="", scene_texture_plan=None,
):
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
                "story_punch_contract": {
                    "audience_question": "",
                    "character_pressure": "",
                    "visible_pressure_object": "",
                    "dramatic_turn": "",
                    "picture_punctuation": "",
                    "composition_priority": "",
                    "camera_motivation": "",
                    "end_residue": "",
                },
                "duration_design": dict(item.get("duration_design", {}) or {}),
                "source_constraint_basemap": {
                    "space_basis": "",
                    "state_prop_basis": "",
                    "character_orientation_basis": "",
                    "tension_curve_role": "",
                    "sound_lip_sync_basis": "",
                    "screen_text_policy": "",
                    "performance_baseline_lock": "none",
                    "emotion_micro_chain": "",
                    "dialogue_performance_kernel": "none",
                    "emotion_residue_contract": "none",
                    "viewpoint_motion_lock": "none",
                    "premium_director_polish": "",
                    "creative_profile": "balanced",
                    "single_shot_risk": "",
                },
                "scene_tone_palette": {
                    "space_id": "",
                    "space_master_sentence": "",
                    "tone_palette": "",
                    "light_texture_purpose": "",
                    "visual_scene_prefix": "",
                    "foreground_layer": "",
                    "midground_layer": "",
                    "background_layer": "",
                    "genre_visual_signature": "",
                    "lived_in_detail": "",
                    "depth_focus_policy": "",
                    "landscape_identity": "",
                    "landscape_composition": "",
                    "natural_motion_system": "",
                    "environment_story_arc": "",
                    "reveal_order": "",
                    "light_weather_progression": "",
                    "breathing_policy": "",
                },
                "visual_bible": {
                    "visual_thesis": "",
                    "palette_system": "",
                    "light_motivation": "",
                    "contrast_exposure": "",
                    "composition_grammar": "",
                    "material_world": "",
                    "atmosphere_rule": "",
                    "imperfection_policy": "",
                    "reference_policy": "none",
                    "continuity_lock": "",
                },
                "static_aesthetic_contract": {
                    "visual_intent": "",
                    "composition_hierarchy": "",
                    "light_design": "",
                    "color_grade": "",
                    "lens_rendering": "",
                    "depth_atmosphere": "",
                    "material_anchor": "",
                    "signature_frame": "",
                    "aesthetic_exclusions": "",
                },
                "dynamic_aesthetic_contract": {
                    "motion_thesis": "",
                    "start_state": "",
                    "trigger": "",
                    "primary_subject_motion": "",
                    "secondary_environment_motion": "",
                    "camera_path": "",
                    "focus_behavior": "",
                    "material_motion": "",
                    "atmosphere_motion": "",
                    "tempo_easing": "",
                    "end_state": "",
                    "stability_fallback": "",
                },
                "aesthetic_priority": {
                    "visual_thesis": "",
                    "primary_eye_target": "",
                    "secondary_visual_layer": "",
                    "must_preserve": "",
                    "degrade_first": "",
                },
                "video_texture_contract": contract_for_scene(
                    scene_texture_plan or {}, str(item.get("scene", "") or "__default__")
                ),
                "character_scene_objective_contract": {
                    "focus_character": "",
                    "scene_objective": "",
                    "stakes": "",
                    "obstacle": "",
                    "active_tactic": "",
                    "visible_tactic_evidence": "",
                    "tactic_shift": "",
                    "knowledge_gap": "",
                    "power_state_change": "",
                    "end_action_state": "",
                },
                "relationship_emotion_arc": {
                    "participants": "",
                    "start_relation_state": "",
                    "conflicting_wants": "",
                    "emotional_misalignment": "",
                    "turn_trigger": "",
                    "power_shift": "",
                    "end_relation_state": "",
                    "shared_residue": "",
                },
                "sequence_directing_plan": {
                    "scene_visual_argument": "",
                    "sequence_position": "",
                    "distance_lens_stage": "",
                    "composition_motif_state": "",
                    "rule_break_or_hold": "",
                    "blocking_camera_coordination": "",
                    "environment_beat": "",
                    "handoff": "",
                },
                "cut_decision_contract": {
                    "cut_mode": "",
                    "trigger": "",
                    "pre_cut_hold": "",
                    "information_gain": "",
                    "sound_strategy": "",
                    "economy_reason": "",
                    "fallback": "",
                },
                "prompt_information_budget": {
                    "profile": str((item.get("quality_contract", {}) or {}).get("profile", "") or ""),
                    "primary_render_task": "",
                    "must_render": "",
                    "supporting_visual": "",
                    "metadata_only": "",
                    "visual_enhancer_limit": 1,
                    "compression_rule": "",
                },
                "sound_directing_plan": {
                    "primary_source": "",
                    "source_direction_distance": "",
                    "room_environment_response": "",
                    "foreground_background_priority": "",
                    "silence_or_drop": "",
                    "lead_lag_strategy": "",
                    "cut_support": "",
                },
                "screen_text_policy": {
                    "mode": "none",
                    "text_refs": [],
                    "render_rule": "",
                    "safe_area": "",
                    "perspective_rule": "",
                },
                "tension_curve_role": "",
                "performance_priority": {"primary": "", "supporting": [], "background": []},
                "action_budget": {
                    "primary_action_count": 0,
                    "emotion_turn_count": 0,
                    "supporting_reaction_count": 0,
                    "physical_camera_move_count": 0,
                    "editorial_response_count": 0,
                },
                "editorial_mode": item.get("editorial_mode", "continuous_take"),
                "emotion_driver": {
                    "trigger": "",
                    "start_state": "",
                    "visible_leak": "",
                    "face_or_eyeline": "",
                    "voice_or_breath": "",
                    "end_residue": "",
                    "tension_intent": "",
                    "empathy_anchor": "",
                },
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
                "ai_model_readiness_score": {
                    "scene_space": {"score": 0, "reason": ""},
                    "continuity_risk": {"score": 0, "reason": ""},
                    "emotion_readability": {"score": 0, "reason": ""},
                    "tension_pressure": {"score": 0, "reason": ""},
                    "camera_emotion_fit": {"score": 0, "reason": ""},
                    "prop_continuity": {"score": 0, "reason": ""},
                    "visual_beauty": {"score": 0, "reason": ""},
                    "overall": {"score": 0, "weakest_point": "", "first_pass_check": ""},
                },
                "pressure_release_design": {
                    "pressure_source": "",
                    "pressure_object": "",
                    "escalation_steps": [],
                    "release_trigger": "",
                    "release_mode": "",
                    "release_result": "",
                    "split_threshold": "",
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
                    "inner_emotion": "",
                    "display_intent": "",
                    "mask_leak": "",
                    "start_intensity": 0,
                    "end_intensity": 0,
                    "emotion_delta": 0,
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
                        "line_function": "",
                        "subtext": "",
                        "stress_words": [],
                        "subtext_visible_evidence": "",
                        "turn_relation": "",
                        "conversation_mode": "clean_turn",
                        "response_latency": "",
                        "overlap_or_interrupt_window": "none",
                        "conversation_source_basis": "",
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
        profile = validation_profile(item)
        metadata = shots[-1]["qa_metadata"]
        for field, profile_key in RISK_GATED_QA_FIELDS.items():
            if not profile.get(profile_key, False):
                metadata.pop(field, None)
        if functional_surface_risk(item):
            shots[-1]["qa_metadata"]["prop_functional_surface_contract"] = {
                "applicable": True,
                "prop": "",
                "functional_surface": "",
                "user": "",
                "user_view_relation": "",
                "camera_half_space": "",
                "camera_visible_surface": "",
                "grip_contact": "",
                "interaction_evidence": "",
                "content_visibility": "hidden",
                "orientation_lock": "",
                "fallback_shot": "",
            }
        if validation_profile(item)["skin_tone_protection_contract"]:
            shots[-1]["qa_metadata"]["skin_tone_protection_contract"] = {
                "applicable": True,
                "subjects": "",
                "protection_mode": "natural_protected",
                "source_allowed_skin_marks": "none",
                "skin_tone_baseline": "",
                "face_light_and_exposure": "",
                "face_fill_shadow_policy": "",
                "environment_color_boundary": "",
                "texture_atmosphere_boundary": "",
                "continuity_lock": "",
                "fallback": "",
            }
        profile = validation_profile(item)
        if profile["prop_lifecycle_contract"]:
            shots[-1]["qa_metadata"]["prop_lifecycle_contract"] = {
                "prop": "", "purpose": "", "visible_surface": "", "start_location": "",
                "contact_owner": "", "contact_mode": "", "motion_path": "",
                "end_location": "", "end_orientation": "", "next_shot_state": "",
            }
        if profile["perspective_scale_contract"]:
            shots[-1]["qa_metadata"]["perspective_scale_contract"] = {
                "subjects_depth": "", "support_plane": "", "projection_scale_rule": "",
                "body_ratio_lock": "", "motion_scaling": "", "prop_scale_lock": "",
                "grounding_evidence": "", "fallback": "",
            }
        if profile["lighting_topology_contract"]:
            shots[-1]["qa_metadata"]["lighting_topology_contract"] = {
                "motivated_source": "", "source_direction": "", "temperature_range": "",
                "face_light_layer": "", "environment_light_layer": "",
                "shadow_exposure_policy": "", "volume_light_boundary": "",
                "conflict_resolution": "",
            }
    payload = {
        "contract_version": PROMPT_CONTRACT_VERSION,
        "locked_fields": [
            "shot_id", "subshot_id", "duration", "negative_prompt",
            "source_subshot_ids",
            "qa_metadata.dialogue_refs", "qa_metadata.dialogue_events[].ref/kind/speaker/text",
            "generation_control",
        ],
        "scene_lock_cache_path": scene_lock_cache_path,
        "scene_motion_plan_path": scene_motion_plan_path,
        "scene_texture_plan_path": scene_texture_plan_path,
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
        "contract_version": PROMPT_CONTRACT_VERSION,
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
        for token in ("full_prompt", "negative_prompt", "generation_control", "qa_metadata", "dialogue_events", "performance_contract", "character_scene_objective_contract", "relationship_emotion_arc", "sequence_directing_plan", "cut_decision_contract", "prompt_information_budget", "sound_directing_plan", "prop_functional_surface_contract", "skin_tone_protection_contract", "continuity_contract", "reroll_control", "camera_beat_map"):
            if token in text and token not in fields:
                fields.append(token)
    return fields or ["validator_reported_field"]


def _retry_examples(retry_context_path):
    """Return only structural examples relevant to the failed retry fields."""
    context = _load_optional_json(retry_context_path)
    fields = set()
    for item in context.get("items", []) if isinstance(context.get("items"), list) else []:
        fields.update(str(value) for value in item.get("repair_fields", []) or [])
    for values in context.get("fields_by_main_shot", {}).values() if isinstance(context.get("fields_by_main_shot"), dict) else []:
        fields.update(str(value) for value in values or [])
    skill_root = os.path.dirname(os.path.dirname(__file__))
    paths = []
    if fields & {"full_prompt", "camera_beat_map", "dramatic_design", "coverage_role"}:
        paths.append(os.path.join(skill_root, "references", "format_example.txt"))
    if fields & {"performance_contract", "continuity_contract", "reroll_control", "qa_metadata"}:
        paths.append(os.path.join(skill_root, "references", "quality_exemplar", "S2-03_high_quality_example.txt"))
    return [path for path in paths if os.path.isfile(path)]


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
    _write_json(path, {"contract_version": PROMPT_CONTRACT_VERSION, "scenes": scenes})
    return path


def _compact_composer_item(item):
    # The Composer scaffold carries locked structural fields and Phase-1
    # ledgers.  The packet item should be a compact execution index plus the
    # source facts the worker must visibly realize.  Keeping the full master
    # dict here duplicated scaffold data and pushed stable 50-shot dialogue
    # runs from 10-shot light batches down to 2-shot packets.
    sources = [
        source for source in item.get("source_subshots", [item])
        if isinstance(source, dict)
    ]
    compact_sources = (
        [_compact_source_subshot(source) for source in sources]
        if len(sources) > 1
        else []
    )
    scene_delta = {
        "lighting": str(item.get("lighting", "") or ""),
        "spatial": str(item.get("axis_space", item.get("spatial_map", "")) or ""),
        "continuity": dict(item.get("scene_continuity", {}) or {}) if isinstance(item.get("scene_continuity"), dict) else {},
    }
    visible_characters = list(item.get("visible_characters", item.get("characters", [])) or [])
    characters = list(item.get("characters", []) or [])
    copied = {
        "shot_id": item.get("shot_id", ""),
        "subshot_id": item.get("subshot_id", ""),
        "scene": item.get("scene", ""),
        "duration": item.get("duration", 0),
        "base_action": item.get("base_action", ""),
        "visible_characters": visible_characters,
        "dialogue_refs": list(item.get("dialogue_refs", []) or []),
        "dialogue_events": [
            dict(event)
            for event in item.get("dialogue_events", []) or []
            if isinstance(event, dict)
        ],
        "source_subshot_ids": list(item.get("source_subshot_ids", [item.get("subshot_id", "")]) or []),
        "editorial_mode": item.get("editorial_mode", "continuous_take"),
        "source_subshots": compact_sources,
        "scene_lock_ref": str(item.get("scene", "") or "__default__"),
        "composer_scaffold_ref": str(item.get("subshot_id", "")),
        "execution_hints": _compact_execution_hints(_composer_execution_hints(item)),
    }
    if characters and characters != visible_characters:
        copied["characters"] = characters
    if not copied["source_subshots"]:
        copied.pop("source_subshots", None)
    if not any(scene_delta.values()):
        copied.pop("scene_delta", None)
    else:
        copied["scene_delta"] = scene_delta
    if not copied["dialogue_refs"]:
        copied.pop("dialogue_refs", None)
    if not copied["source_subshot_ids"]:
        copied.pop("source_subshot_ids", None)
    return copied


def _compact_execution_hints(hints):
    required_contracts = [
        value for value in list(hints.get("required_contracts", []) or [])
        if value not in {
            "skin_tone_protection_contract", "prop_lifecycle_contract",
            "perspective_scale_contract", "lighting_topology_contract",
        }
    ]
    compacted = {
        "template": hints.get("template", ""),
        "risk": hints.get("risk", "standard"),
        "reasons": list(hints.get("reasons", []) or []),
        "visible": list(hints.get("visible", []) or []),
        # The skin contract is already present in each applicable scaffold and
        # enforced locally; do not duplicate its long name in every packet item.
        "required_contracts": required_contracts,
    }
    return compacted


def _compact_source_subshot(source):
    """Keep child-shot facts needed for timeline assembly without duplicating
    the full master item inside every packet item.

    The Composer scaffold carries locked output fields, while packet.items
    carries source facts.  A one-child master previously embedded an almost
    identical child dict, doubling every light task and forcing 10-shot
    capacity batches down to 2-shot packets.  Preserve source identity,
    dialogue, visible cast, duration and dramatic/duration ledgers; omit
    repeated top-level mirrors such as quality_contract and execution hints.
    """
    keep = (
        "shot_id",
        "subshot_id",
        "scene",
        "duration",
        "base_action",
        "characters",
        "visible_characters",
        "dialogue_refs",
        "dialogue_events",
        "emotion_tone",
        "editorial_mode",
        "source_ids",
    )
    compacted = {key: source.get(key) for key in keep if key in source}
    compacted["scene_delta"] = {
        "lighting": str(source.get("lighting", "") or ""),
        "spatial": str(source.get("axis_space", source.get("spatial_map", "")) or ""),
        "continuity": (
            dict(source.get("scene_continuity", {}) or {})
            if isinstance(source.get("scene_continuity"), dict)
            else {}
        ),
    }
    return compacted


def _composer_execution_hints(item):
    risk = dispatch_risk(item)
    sources = item.get("source_subshots")
    sources = sources if isinstance(sources, list) and sources else [item]
    visible = _visible_characters(item, sources)
    dialogue_events = [
        event for source in sources if isinstance(source, dict)
        for event in source.get("dialogue_events", []) or []
        if isinstance(event, dict)
    ]
    dialogue_text_length = sum(len(str(event.get("text", "") or "")) for event in dialogue_events)
    duration = _safe_float(item.get("duration", 0))
    reasons = risk.get("reasons", [])
    editorial_mode = str(item.get("editorial_mode", "continuous_take") or "continuous_take")
    template = _composer_template(reasons, visible, dialogue_events, item)
    return {
        "template": template["name"],
        "risk": risk.get("tier", "standard"),
        "reasons": reasons,
        "duration_mode": _duration_mode(duration, reasons),
        "visible": visible,
        "risk_gated_contracts": _risk_gated_contracts(item, visible, dialogue_events, reasons, editorial_mode),
        "required_contracts": [
            key for key, required in validation_profile(item, item.get("qa_metadata", {}), visible).items()
            if key not in ("profile", "risk_tier") and required
        ],
        "fill_order": template["fill_order"],
        "checks": _composer_preflight_checks(editorial_mode, visible, dialogue_events, reasons, dialogue_text_length),
    }


def _risk_gated_contracts(item, visible, dialogue_events, reasons, editorial_mode):
    profile = validation_profile(item, item.get("qa_metadata", {}), visible)
    return {
        field: bool(profile.get(profile_key, False))
        for field, profile_key in RISK_GATED_QA_FIELDS.items()
    }


def _item_tension_intent(item):
    for key in ("performance_contract", "emotion_driver", "performance_causality"):
        value = item.get(key)
        if isinstance(value, dict) and value.get("tension_intent"):
            return str(value.get("tension_intent", "") or "")
    metadata = item.get("qa_metadata")
    if isinstance(metadata, dict):
        for key in ("performance_contract", "emotion_driver", "performance_causality"):
            value = metadata.get(key)
            if isinstance(value, dict) and value.get("tension_intent"):
                return str(value.get("tension_intent", "") or "")
    return str(item.get("tension_intent", "") or "")


def _composer_template(reasons, visible, dialogue_events, item):
    if "fight_or_force" in reasons:
        return {
            "name": "fight_causal_unit",
            "fill_order": ["initiator", "direction", "contact_or_judgment", "feedback", "end_lock"],
        }
    if "prop_transfer" in reasons:
        return {
            "name": "prop_information_transfer",
            "fill_order": ["prop_start", "transfer_or_refusal", "detail", "recipient_state", "carryover"],
        }
    if "shot_group" in reasons or item.get("editorial_mode") == "shot_group":
        return {
            "name": "motivated_shot_group",
            "fill_order": ["beat_subject", "beat_trigger", "one_hand_off_or_reframe", "beat_residue", "same_narrative_lock"],
        }
    if dialogue_events and len(visible) > 1:
        return {
            "name": "dialogue_relationship_lock",
            "fill_order": [
                "line_function", "turn_relation", "subtext", "stress_words", "speaker", "listener",
                "subtext_visible_evidence", "delayed_listener_reaction", "screen_lr", "mouth_boundary", "residue",
            ],
        }
    if dialogue_events:
        return {
            "name": "single_speaker_performance",
            "fill_order": [
                "line_function", "turn_relation", "subtext", "stress_words", "speaker", "face",
                "body", "subtext_visible_evidence", "breath", "voice", "mouth_boundary", "residue",
            ],
        }
    if len(visible) > 1:
        return {
            "name": "relationship_blocking_or_movement",
            "fill_order": ["primary", "supporting_pos", "one_change", "screen_dir", "residue"],
        }
    return {
        "name": "stable_insert_or_single_action",
        "fill_order": ["subject", "scene_anchor", "one_action_or_state", "camera", "residue"],
    }


def _duration_mode(duration, reasons):
    if "fight_or_force" in reasons:
        return "fight_one_causal_unit"
    if duration <= 2.5:
        return "single_micro_action"
    if duration <= 6:
        return "one_or_two_linked_actions"
    return "continuous_dialogue_or_process"


def _composer_preflight_checks(editorial_mode, visible, dialogue_events, reasons, dialogue_text_length):
    checks = [
        "top=shots",
        "priority=visible",
        "quality_evidence=literal_fragments",
        "contracts_visible_in_prompt",
    ]
    if editorial_mode == "continuous_take":
        checks.append("continuous_take=one_range")
    else:
        checks.append("shot_group=2-3_ranges_one_narrative_beat")
    if dialogue_events:
        checks.append("dialogue_exact+subtext+stress+breath+mouth_close")
    if dialogue_text_length >= 32:
        checks.append("long_dialogue=no_extra_plot")
    if "fight_or_force" in reasons:
        checks.append("fight_continuity=start_contact_end")
    return checks


def _visible_characters(item, sources):
    values = item.get("visible_characters", item.get("characters", [])) or []
    if not values:
        values = [
            character for source in sources if isinstance(source, dict)
            for character in (source.get("visible_characters", source.get("characters", [])) or [])
        ]
    if isinstance(values, str):
        values = [part.strip() for part in re.split(r"[;；,，、/]+", values) if part.strip()]
    return list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


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


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
