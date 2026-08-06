"""Write compact on-disk dispatch packets for sub-agent phases.

The main agent can pass these packet paths to workers instead of copying a
large shot list into every prompt. Workers read the packet from disk, write only
their required output file, and retry messages carry only failed subshot ids.
"""
import json
import copy
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
from context_budget import check as check_context_budget
from batch_planner import analysis_chunks as _analysis_chunks, batch_profile as _batch_profile
from batch_planner import dynamic_master_chunks as _plan_dynamic_master_chunks
from batch_planner import editor_review_chunks as _editor_review_chunks
from contract_registry import PROMPT_CONTRACT_VERSION

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
        # Batch boundaries are mechanical: item count, declared chain IDs and
        # serialized context size. Engineering never interprets scene meaning.
        size = max(int(batch_size or 4), 1)
        chunks = _dynamic_master_chunks(items, max_items=size, force_single=(size == 1))
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
            )
            packet_items = [_compact_composer_item(item) for item in chunk]
        retry_context_path = None
        retry_mode = None
        if is_retry and phase == "master_production":
            retry_context_path, retry_mode = _write_retry_context(
                run_dir, phase, packet_items, out_dir, dispatch_tag
            )
        batch_profile = _batch_profile(chunk)
        packet = {
            "contract_version": PROMPT_CONTRACT_VERSION,
            "dispatch_id": dispatch_id,
            "dispatch_group_id": dispatch_group_id,
            "created_at": time.time(),
            "phase": phase,
            "run_dir": run_dir,
            "source_path": source_path,
            "source_sha256": _sha256(source_path),
            "source_snapshot_path": os.path.join(run_dir, ".cache", "orchestrator", "source_snapshot.json"),
            "source_ledger_path": os.path.join(run_dir, ".cache", "orchestrator", "source_ledger.json"),
            "project_config_path": os.path.join(run_dir, "project_config.json"),
            "constraints_path": constraints_path,
            "output_path": public_output,
            "_batch_output_path": batch_output,
            "batch_index": idx,
            "total_batches": len(chunks),
            "batch_size": size,
            "batch_capacity": size,
            "batch_policy": batch_profile["basis"],
            "creative_review_scope": "full_model_review",
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
                "composer_scaffold_path, preserve every locked field, and create exactly one Jimeng task per packet item; the model decides each task's dramatic coverage, internal rhythm, and editorial form; read scene_lock_cache_path once per scene; "
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
            packet["incremental_validation_command"] = [
                sys.executable,
                os.path.join(os.path.dirname(__file__), "validate_main_shot_incremental.py"),
                batch_output,
                "--shot-id",
                "{shot_id}",
            ]
            packet["context_policy"] = {
                "fixed_global_context": [
                    "project_config_path",
                    "constraints_path",
                    "composer_scaffold_path",
                    "scene_lock_cache_path",
                    "source_snapshot_path",
                    "source_ledger_path",
                ],
                "per_shot_context": [
                    "packet.items[] complete model-authored record",
                    "packet.items[].source_subshots complete model-authored children",
                    "packet.items[].dialogue_events locked source facts",
                ],
                "history_policy": "Use the complete bounded scene context needed for directing. Scene locks are model-authored references, not engineering prescriptions.",
                "quality_policy": "Use scaffold structures only when they help the shot. Creative depth is chosen by the model and judged by the model Editor.",
            }
            packet["instruction"] += (
                " Composer batch output top-level must be exactly {\"shots\": [...]}; "
                "omit contract_version. Preserve only scaffold locked_fields; all other creative fields are model-owned. "
                "After each main shot, run incremental_validation_command with its shot id and patch only the reported scope. "
                "Then run the exact full-batch local_validation_command; it must PASS and cannot be replaced by an incremental PASS."
            )
        if retry_context_path:
            packet["retry_context_path"] = retry_context_path
            packet["is_retry"] = True
            packet["instruction"] += (
                " This is a targeted retry: read retry_context_path, repair only its authorized field/shot/window scope, "
                "and preserve all locked fields and already-passing content outside that scope."
            )
            example_paths = _retry_examples(retry_context_path)
            if example_paths:
                packet["example_paths"] = example_paths
                packet["instruction"] += " Read only the listed example_paths; they are structural repair references, never creative templates."
        if scaffold_path:
            packet["composer_scaffold_path"] = scaffold_path
            packet["scene_lock_cache_path"] = scene_lock_cache_path
        if phase == "editor_pass2":
            editor_context_path = _write_editor_creative_context(
                run_dir, source_path, chunk, out_dir, dispatch_tag
            )
            packet["targeted_review"] = bool(wanted)
            packet["target_shot_ids"] = sorted(wanted)
            packet["review_packet_path"] = os.path.join(run_dir, ".cache", "review", "llm_gate_review.md")
            packet["pre_editor_gate_path"] = pre_editor_gate_path
            packet["editor_creative_context_path"] = editor_context_path
            packet["instruction"] += (
                " For editor_pass2, read pre_editor_gate_path and editor_creative_context_path in full. The latter contains the exact, "
                "unclipped model-authored prompts, director cards, creative metadata, plan facts, and adjacent shots for this bounded window. "
                "It also points to the immutable source snapshot and engineering ledger for verbatim source review. "
                "The local gate proves only mechanical validity. Independently judge script interpretation, emotional causality, "
                "performance, shot rhythm, blocking, camera, movement, focus, lighting, palette, Seedance comprehensibility, and final aesthetics. "
                "Do not defer any semantic decision to keyword or regex reports. Every window receives the same full model review standard."
            )
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


def _write_editor_creative_context(run_dir, source_path, windows, out_dir, dispatch_tag):
    """Stage exact bounded creative text for model Editor review."""
    package = _load_json(source_path)
    wanted = set()
    for window in windows:
        if not isinstance(window, dict):
            continue
        for relation in ("previous", "current", "next"):
            item = window.get(relation)
            if isinstance(item, dict) and item.get("shot_id"):
                wanted.add(str(item["shot_id"]))
    shots = [
        item for item in package.get("shots", [])
        if isinstance(item, dict) and str(item.get("shot_id", "")) in wanted
    ]
    plan = _load_optional_json(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"))
    planned = [
        item for item in plan.get("shots", [])
        if isinstance(item, dict) and str(item.get("shot_id", "")) in wanted
    ]
    scene_names = {str(item.get("scene", "")) for item in planned}
    locks = _load_optional_json(os.path.join(run_dir, ".cache", "analysis", "scene_locks.json"))
    scene_locks = [
        item for item in locks.get("scenes", [])
        if isinstance(item, dict) and str(item.get("scene", "")) in scene_names
    ]
    path = os.path.join(out_dir, "editor_creative_context_%s.json" % dispatch_tag)
    os.makedirs(out_dir, exist_ok=True)
    _write_json(path, {
        "authority": "model_editor",
        "semantic_transform": False,
        "source_snapshot_path": os.path.join(run_dir, ".cache", "orchestrator", "source_snapshot.json"),
        "source_ledger_path": os.path.join(run_dir, ".cache", "orchestrator", "source_ledger.json"),
        "target_shot_ids": sorted(wanted),
        "shots": shots,
        "planned_shots": planned,
        "scene_locks": scene_locks,
    })
    return path


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
            if not isinstance(shot, dict):
                continue
            shot_id = shot.get("shot_id", "")
            if isinstance(shot, dict) and "subshots" not in shot and shot.get("subshot_id"):
                ssid = shot.get("subshot_id", "")
                if wanted and ssid not in wanted and shot_id not in wanted:
                    continue
                items.append(copy.deepcopy(shot))
                continue
            for ss in shot.get("subshots", []):
                if not isinstance(ss, dict):
                    continue
                ssid = ss.get("subshot_id", "")
                if wanted and ssid not in wanted and shot_id not in wanted:
                    continue
                source_events = [
                    dict(data.get("dialogue_events", {}).get(ref, {}))
                    for ref in ss.get("dialogue_refs", [])
                    if isinstance(data.get("dialogue_events", {}).get(ref), dict)
                ]
                copied = copy.deepcopy(ss)
                copied.setdefault("shot_id", shot_id)
                copied.setdefault("subshot_id", ssid)
                copied.setdefault("scene", shot.get("scene", ""))
                copied["parent_shot_context"] = copy.deepcopy({
                    key: value for key, value in shot.items() if key != "subshots"
                })
                copied.setdefault("dialogue_events", source_events)
                items.append(copied)
        return items
    items = []
    for item in data.get("items", []):
        if wanted and item.get("subshot_id") not in wanted:
            continue
        if isinstance(item, dict):
            items.append(copy.deepcopy(item))
    return items


def _scene_lock_items(shot_plan):
    """Group full model-authored shot records by the model-declared scene."""
    scenes = {}
    for shot in shot_plan.get("shots", []):
        scene = str(shot.get("scene", "") or "__default__")
        entry = scenes.setdefault(scene, {
            "scene": scene, "scene_type": shot.get("scene_type", ""),
            "shot_ids": [], "subshot_ids": [], "characters": [], "shots": [],
        })
        entry["shot_ids"].append(shot.get("shot_id", ""))
        entry["shots"].append(copy.deepcopy(shot))
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
    boundary = (
        "## 创作主权边界\n\n"
        "剧情、情绪、表演、构图、运镜、光影、声音和语义精炼由大模型负责；"
        "工程层只做结构、计数和交付，不得静默删句、改写Scene Lock或删除创作字段。"
        "需要语义变化时返回 CREATIVE_REWRITE_REQUIRED。完整合同见 "
        "references/creative_engineering_boundary.md。"
    )
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
        f.write(boundary + "\n\n")
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
        "master_production": ("direct_copy_contract.md",),
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
                    "# 模型直投合同定位\n\n"
                    "Master Production 直接创作 seedance_prompt；工程只验证字符数、版本字段并原样导出。"
                    "摄影、表演、光影、动作与 Seedance 语义由模型决定；详规见本文件。\n"
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
        first = copy.deepcopy(children[0])
        first["shot_id"] = key
        first["subshot_id"] = key  # output identity is the main shot
        first["source_subshot_ids"] = [str(child.get("subshot_id", "")) for child in children]
        first["source_subshots"] = copy.deepcopy(children)
        first["duration"] = round(sum(float(child.get("duration", 0) or 0) for child in children), 3)
        first["dialogue_refs"] = [ref for child in children for ref in child.get("dialogue_refs", [])]
        first["dialogue_events"] = [event for child in children for event in child.get("dialogue_events", [])]
        first["master_task"] = True
        masters.append(first)
    return masters


def _dynamic_master_chunks(items, max_items=6, force_single=False):
    return _plan_dynamic_master_chunks(
        items, _compact_composer_item, max_items=max_items, force_single=force_single
    )


def _write_composer_scaffold(
    run_dir, items, dispatch_dir, dispatch_tag, scene_lock_cache_path,
):
    return _write_model_owned_scaffold(
        run_dir, items, dispatch_dir, dispatch_tag, scene_lock_cache_path
    )


def _write_model_owned_scaffold(run_dir, items, dispatch_dir, dispatch_tag, scene_lock_cache_path):
    """Write only mechanical locks; all creative fields remain blank/model-owned."""
    config = _load_optional_json(os.path.join(run_dir, "project_config.json"))
    project_control = config.get("generation_control", {}) if isinstance(config, dict) else {}
    shots = []
    for item in items:
        control = item.get("generation_control") if isinstance(item.get("generation_control"), dict) else project_control
        events = []
        for event in item.get("dialogue_events", []) if isinstance(item.get("dialogue_events"), list) else []:
            if isinstance(event, dict):
                events.append({
                    "ref": event.get("ref", ""), "kind": event.get("kind", ""),
                    "speaker": event.get("speaker", ""), "text": event.get("text", ""),
                })
        shots.append({
            "shot_id": item.get("shot_id", ""),
            "subshot_id": item.get("subshot_id", ""),
            "source_subshot_ids": list(item.get("source_subshot_ids", [item.get("subshot_id", "")]) or []),
            "duration": item.get("duration", 0),
            "full_prompt": "",
            "seedance_prompt": "",
            "seedance_prompt_variants": {},
            "director_card": "",
            "negative_prompt": "",
            "qa_metadata": {
                "dialogue_refs": list(item.get("dialogue_refs", []) or []),
                "dialogue_events": events,
            },
            "generation_control": {
                "mode": "t2v",
                "audio_enabled": bool((control or {}).get("audio_enabled", True)),
            },
            "_scene_lock_ref": str(item.get("scene", "") or "__default__"),
        })
    payload = {
        "contract_version": PROMPT_CONTRACT_VERSION,
        "locked_fields": [
            "shot_id", "subshot_id", "source_subshot_ids", "duration",
            "qa_metadata.dialogue_refs", "qa_metadata.dialogue_events[].ref/kind/speaker/text",
            "generation_control",
        ],
        "creative_authority": "model",
        "scene_lock_cache_path": scene_lock_cache_path,
        "shots": shots,
    }
    path = os.path.join(dispatch_dir, "master_production_%s_scaffold.json" % dispatch_tag)
    _write_json(path, payload)
    return path


def _write_retry_context(run_dir, phase, items, dispatch_dir, dispatch_tag):
    """Expose only validator facts for the retry batch, never prior creative text."""
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
        if not isinstance(issue, dict):
            continue
        field = str(issue.get("field_path", "") or "").strip()
        if field and field not in fields:
            fields.append(field)
    return fields or ["validator_reported_field"]


def _retry_examples(retry_context_path):
    """Engineering does not choose creative examples from issue keywords."""
    del retry_context_path
    return []


def _write_scene_lock_cache(run_dir, items, dispatch_dir, group_tag):
    del items, dispatch_dir, group_tag
    approved_path = os.path.join(run_dir, ".cache", "analysis", "scene_locks.json")
    if os.path.exists(approved_path):
        return approved_path
    raise FileNotFoundError(
        "CREATIVE_AUTHORING_REQUIRED: model-authored scene_locks.json is missing; "
        "engineering cannot synthesize lighting, space, continuity, or visual direction"
    )


def _compact_composer_item(item):
    """Pass the complete model-authored item and append only file references."""
    copied = copy.deepcopy(item)
    copied["scene_lock_ref"] = str(item.get("scene", "") or "__default__")
    copied["composer_scaffold_ref"] = str(item.get("subshot_id", ""))
    return copied


def _compact_source_subshot(source):
    """Retained API: child records are no longer compacted or filtered."""
    return copy.deepcopy(source)


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
