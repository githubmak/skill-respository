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
from shot_semantics import dispatch_risk, quality_contract, temporal_transition_candidate, validation_profile
from context_budget import check as check_context_budget
from batch_planner import analysis_chunks as _analysis_chunks, batch_risk as _batch_risk
from batch_planner import dynamic_master_chunks as _plan_dynamic_master_chunks
from batch_planner import editor_review_chunks as _editor_review_chunks

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
        if is_retry and phase == "master_production":
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
                "Require contract_version=jimeng-t2v-v1 and read constraints_path for the full phase contract; "
                "a missing or older contract version requires redispatch. For master_production, start from "
                "composer_scaffold_path, preserve every locked field, and create exactly one Jimeng task per packet item; each task serves one narrative_beat_id only, with any shot_group used only as internal coverage of that beat; read scene_lock_cache_path once per scene; "
                "source_path is fallback context only and must not be read in full unless packet data is insufficient. "
                "Do not paste unchanged source content back into chat."
            ),
        }
        if phase == "master_production":
            packet["local_validation_command"] = [
                "python3",
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
                "quality_policy": "Execution hints are speed aids only. They cannot remove required qa_metadata fields, Composer validation, provenance, Editor passes, final validation, or export checks.",
            }
            packet["instruction"] += (
                " Composer batch output top-level must be exactly {\"shots\": [...]}; "
                "do not include contract_version in the batch file. Before final response, run local_validation_command. "
                "If validation fails, patch only the reported fields and rerun until PASS."
            )
        if retry_context_path:
            packet["retry_context_path"] = retry_context_path
            packet["retry_mode"] = retry_mode
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
        path = entry.get("packet_path") if isinstance(entry, dict) else ""
        if path and os.path.exists(path):
            paths.append(path)
    return paths


def _active_manifest_path(run_dir, phase):
    safe_phase = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(phase or "unknown"))
    return os.path.join(run_dir, ".cache", "dispatch", "active_%s_manifest.json" % safe_phase)


def _write_active_manifest(run_dir, phase, source_path, dispatch_group_id, packet_paths, is_retry=False, target_ids=None):
    target_ids = set(target_ids or [])
    current = _load_optional_json(_active_manifest_path(run_dir, phase))
    entries = current.get("packets", []) if isinstance(current.get("packets"), list) else []
    superseded = current.get("superseded_packets", []) if isinstance(current.get("superseded_packets"), list) else []
    attempt = int(current.get("attempt", 0) or 0) + 1
    if is_retry and target_ids:
        # Keep original mixed batches because they may contain unaffected shots,
        # but drop older retry packets that are fully covered by this newer
        # retry target set.  New retry packets are appended so merge order lets
        # them override original fields.
        filtered = []
        for entry in entries:
            ids = set(entry.get("shot_ids", [])) if isinstance(entry, dict) else set()
            previous_retry = bool(entry.get("is_retry")) if isinstance(entry, dict) else False
            if previous_retry and ids and ids <= target_ids:
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
            "shot_ids": _packet_shot_ids(packet),
            "source_sha256": packet.get("source_sha256", source_sha256),
            "attempt": attempt,
        })
    active_shot_ids = sorted({
        shot_id
        for entry in entries if isinstance(entry, dict)
        for shot_id in entry.get("shot_ids", [])
        if str(shot_id).strip()
    })
    _write_json(_active_manifest_path(run_dir, phase), {
        "contract_version": "jimeng-t2v-v1",
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
    copied["superseded_at"] = time.time()
    copied["superseded_by_attempt"] = attempt
    copied["superseded_reason"] = reason
    return copied


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


def _write_constraints_sidecar(run_dir, phase, dispatch_dir, dispatch_tag):
    skill_dir = os.path.dirname(os.path.dirname(__file__))
    source = os.path.join(skill_dir, "references", "format_constraints.md")
    out_path = os.path.join(dispatch_dir, "%s_%s_constraints.md" % (phase, dispatch_tag))
    phase_note = {
        "scene_lock": (
            "专业角色：场景锁定 Agent。请返回 {\"scenes\":[{\"scene\":\"...\",\"space_anchor\":\"...\",\"screen_positions\":\"...\",\"wardrobe_lock\":\"...\",\"prop_state\":\"...\",\"light_source\":\"...\",\"light_direction\":\"...\",\"light_temperature\":\"...\",\"audio_policy\":\"...\"}]}，每个 packet item 对应一条不可变场景锁定。所有必填值都必须是非空的扁平字符串；不要嵌套 lighting、wardrobe、props、positions 或 audio 对象。可按同样扁平字符串补充 space_id、space_master_sentence、entrance_exit、prop_activity_zone、tone_palette、light_texture_purpose，用于全集空间索引和影调索引；不得重排同一地点的左右、入口或道具活动区。禁止写子镜分析、运镜设计、人物表演、台词或提示词正文。"
        ),
        "master_production": (
            "专业角色：你是 AI 短剧导演与提示词监督。"
            "每个 packet item 只生成一个主镜头任务，只服务一个 narrative_beat_id；从 packet.composer_scaffold_path 开始写，保留锁定字段，并只从 scene_lock_cache_path 读取共享场景事实。"
            "禁止虚构剧情、改写台词、重设服装、添加未确认道具、使用 I2V/R2V/参考素材，或把 QA/工程字段写进 full_prompt。"
            "仅当 packet.items[].execution_hints.required_contracts 包含 story_punch_contract 时，先填观众问题、人物压力、可见压力物、剧情转折、画面标点和尾帧残留；人物/对白/道具变化镜缺少戏眼时必须先补戏眼，不得只机械填字段。"
            "按 risk_tier 控制复杂度：light 镜只写适用的硬门槛与一个落幅残留；standard 镜落实适用的质量合同；high 镜再补 ai_model_readiness_score、pressure_release_design 和必要拆镜建议。"
            "先满足不穿帮硬门槛，再追求创作表现：人物位置、身体面向、道具归属、口型、尾帧继承、单镜动作预算和状态变化中间态不稳时，必须降低运镜、补定位镜头或拆镜。"
            "写镜前先在 qa_metadata.source_constraint_basemap 中压缩锁定本镜源头底图：空间/状态道具/人物朝向/张弛功能/声音口型/UI文字策略/单镜风险；它是防返工底图，不得投喂到 full_prompt。"
            "同一地点必须复用 Scene Lock 的 space_id、space_master_sentence、入口出口和道具活动区；同一场景的影调只从 tone_palette/light_texture_purpose 消费，单镜只选本镜需要的一个光影或构图锚点。"
            "写作目标不是堆形容词，而是让 AI 视频大模型能稳定执行且有戏：空间坐标、道具生命周期、情绪触发、运镜响应、戏剧尖刺和落幅继承必须逐项可见。"
            "画面质感必须可见，不得只写电影感/高级感/质感；按本镜任务选择1-2个锚点，写清光源方向或色温、脸/手/道具受光面、浅阴影/反光、背景虚化或剧情相关材质。"
            "直接投喂即梦的文本不得保留上一镜/继承/尾帧/剪辑/切到/反打到等元叙述；canonical full_prompt 可用于验证落幅，但导出 feed 会转成当前可见事实，因此 Composer 必须优先写可见起幅和落幅。"
            "手机聊天、来电名称、通知弹窗等 UI 文字若交给 AI 生成，必须写成独立二维浮层、安全区、不属于手机屏幕、不贴手机背面、不跟随手机透视；否则把具体文字留到后期文字表。"
            "多人清晰入画时，非说话重要人物必须分配受击反应、观察反应或降为肩线/边缘虚化；OS/OV/系统音/内心声必须绑定可见闭口反应，不生成口型。"
            "每镜标记 tension_curve_role：铺垫、升压、峰值、释放或缓冲；不要连续强推近、强表情、强停顿，关键台词后优先给被击中者余波或关系定格。"
            "道具交接、转身、起身、开门、离场、手腕控制等物理变化必须写起始状态、接近/接触、移动/受力、释放或稳定终态；若动作强，运镜只能固定或低幅推近。"
            "rising/peak 镜必须设计压力链：压力来源、一个压力物或压力机制、1-2个可见升级点、释放触发、释放结果和拆镜阈值；释放可以是动作完成、被打断、注意力转移、代价逼近或落幅悬置，不能只写气氛变紧。"
            "字段接力固定为 emotion_driver → camera_beat_map → full_prompt；Camera 只响应可见表演重音、道具状态、视线或台词落点，Composer 只能翻译已声明的镜头设计。"
            "必须填写 packet.items[].execution_hints.required_contracts 中列出的质量合同；continuity_contract、reroll_control、quality_contract、quality_evidence、dialogue_events 与状态变化记录仍按适用的硬门槛执行。未列出的增强合同保持空对象，不要为了凑字段写长自评。"
            "full_prompt 只能包含五段：生成规格/主体与空间锁定/主镜头连续规则/子镜头组/光照、声音与稳定约束。子镜头组按状态机写，台词/OS/OV 在原生音频开启时必须写成 {人物}（台词/OS/OV）: \"逐字原文\"。"
            "需要 ai_model_readiness_score 时，按场景空间、穿帮风险、情绪可读、张力压迫、运镜服务、道具连续、画面美感七项逐项打 1-10 分，并写一句弱点或人工首轮检查点；不得全写空泛好评。"
            "temporal_transition_contract 不是装饰命令；启用时只使用合同内唯一源文效果，未启用时正常切换。"
            "只使用本 sidecar 中选出的契约段落；首轮不要读取示例。重试时若 packet.example_paths 存在，只读取这些文件且只修复指定失败字段。"
            "示例只迁移结构，不继承示例题材、场景、光线、服装、人物关系或具体道具事件，除非当前源文或配置明确提供。"
        ),
        "editor_pass2": "使用 §B/§C 作为审查上下文。不要改写纯格式问题；只返回语义审查 JSON。",
    }.get(phase, "遵守所引用阶段的契约。")
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
                "story_punch_contract": {
                    "audience_question": "",
                    "character_pressure": "",
                    "visible_pressure_object": "",
                    "dramatic_turn": "",
                    "picture_punctuation": "",
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
                    "single_shot_risk": "",
                },
                "scene_tone_palette": {
                    "space_id": "",
                    "space_master_sentence": "",
                    "tone_palette": "",
                    "light_texture_purpose": "",
                    "visual_scene_prefix": "",
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
    copied["execution_hints"] = _composer_execution_hints(item)
    return copied


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
        "ai_model_readiness_score": profile["ai_model_readiness_score"],
        "pressure_release_design": profile["pressure_release_design"],
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
            "fill_order": ["speaker", "listener", "one_listener_reaction", "screen_lr", "mouth_boundary", "residue"],
        }
    if dialogue_events:
        return {
            "name": "single_speaker_performance",
            "fill_order": ["speaker", "face", "body", "breath", "voice", "residue"],
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
        checks.append("dialogue_exact+breath")
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
