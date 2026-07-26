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
from shot_semantics import dispatch_risk, quality_contract, temporal_transition_candidate
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
                "quality_policy": "Execution hints are speed aids only. They cannot remove required qa_metadata fields, Composer validation, provenance, Editor passes, final validation, export checks, or grid_storyboard behavior.",
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
            "专业角色：场景锁定 Agent。请返回 {\"scenes\":[{\"scene\":\"...\",\"space_anchor\":\"...\",\"screen_positions\":\"...\",\"wardrobe_lock\":\"...\",\"prop_state\":\"...\",\"light_source\":\"...\",\"light_direction\":\"...\",\"light_temperature\":\"...\",\"audio_policy\":\"...\"}]}，每个 packet item 对应一条不可变场景锁定。所有必填值都必须是非空的扁平字符串；不要嵌套 lighting、wardrobe、props、positions 或 audio 对象。禁止写子镜分析、运镜设计、人物表演、台词或提示词正文。"
        ),
        "master_production": (
            "专业角色：你是 AI 短剧导演与提示词监督。"
            "每个 packet item 只生成一个符合当前契约的主镜头任务，并且只服务一个 narrative_beat_id；必须使用严格动作预算，并区分 primary/supporting/background 表演优先级。"
            "禁止虚构剧情、改写台词、重新设计服装、添加未确认道具或把工程字段写进模型提示词。"
            "不要强迫角色面向镜头：要区分“角色在画面前侧”和“角色脸朝镜头”。只有源文明确授权自拍、直播、对观众说话或看镜头内设备时，才写直视镜头。选择景别前先读取 qa_metadata.dramatic_design.coverage_role：只有 dialogue_performance（台词表演）或 reaction（反应镜）可以默认用中景/中近景固定机位。establish_space 表示建立空间，relationship_blocking 表示关系站位，prop_information 表示道具信息，movement_transition 表示移动承接，power_reversal 表示权力反转，environment_bridge 表示环境承接。它们是剧情职责，不是景别配额；不得覆盖已锁定的 coverage_role。"
            "互动镜只有在源文压力支持时，才使用心理距离景别反差：焦虑、急迫、被逼问或被压迫的一方可用更紧景别、呼吸和手部证据表现压力；松弛、掌控或回避的一方保留中景/宽景空间。插入镜只能作为同一 narrative_beat_id 内的辅助证据：补充信息、放大情绪证据、切分节奏、引导视线、缓冲转场或保留环境残压。优先使用已确认且稳定的道具、手部、空间边界或环境残留，少用重复脸部特写；每个插入镜必须带来新信息、道具状态、关系压力或残留，并继承轴线、光源、画面左右、场景锚点和插入前后的动作状态。禁止装饰性空镜。回忆、幻想或时空切换插入必须使用 temporal_transition_contract 或拆成独立主镜。插入镜默认有抽卡风险，必须写缓解。"
            "先执行 Director 的 performance_chain，再设计镜头语言：触发原因、表情控制、细节/道具泄露、身体承接、语气/呼吸落点、终态残留。先填写 qa_metadata.emotion_driver 作为运镜输入合同：trigger、start_state、visible_leak、face_or_eyeline、voice_or_breath、end_residue、tension_intent、empathy_anchor。然后只能从 emotion_driver、coverage_role、continuity_contract 以及已确认的道具/台词触发点推导 camera_beat_map；没有这些触发依据，不得添加镜头运动。shot_group 中，自然反应、细节切入和重构图只能作为同一 narrative_beat_id 的起势/承接/转折/落幅覆盖；必须保留身份、道具状态、轴线、光源和上一节拍残留。每个 camera_beat_map item 必须包含 time_range、focus_owner、focus_subject、framing、trigger、camera_response、camera_position、camera_movement、transition_type、screen_lock、axis_relation、axis_carryover、carryover、end_frame。单个 T2V 任务只允许一次 A→B 注意力交接，不能 B→A 回切；第二个剧情节拍、回切或独立反应结论必须拆成下一条 T2V，并用已声明的承接状态交给后期剪辑。可见说话者同框存在 supporting 倾听者时，必须填写 listener_reaction_plan：只给一个由台词或动作触发的低幅闭口反应，不能让听者冻结，也不能让听者抢戏。打斗镜改用 fight_continuity：双方都按“动作→受力/判断→结果”连续反应，不使用 listener_reaction_plan。"
            "写 performance_contract 前，先语义判断 packet 中的 expectation_anchor：它是字面人物期待、拟人修辞、需求/缺失，还是象征联想。只有字面人物可以被安排成有意图的表演主体；尚未出现的满足物不能被拍成已经在场。只绑定源文支持的可见进展、镜头决策、返回反应和未完成终态。不要因为角色期待某物就切静态物件；细节切入或重构图必须由已声明的进展事件触发。"
            "每个有可见物理角色的镜头，都必须填写 qa_metadata.performance_causality：校准后的张力意图、触发点、反应顺序、物理逻辑、运动边界、停顿策略和终态残留。"
            "写 full_prompt 前，还必须填写 qa_metadata.performance_contract、qa_metadata.continuity_contract 和 qa_metadata.reroll_control：performance_contract 必须把表情、身体动作、视线、反应延迟、语气/呼吸控制、一个观众共情锚点、一个可读画面瞬间、从起幅到落幅的可见推进（或有理由的静止与 1-2 个生命迹象）、运镜压力、场景压力和终态残留落实到子镜头组。稳定构图不等于人物可以冻结。每条台词/OS/OV 事件都必须有 breath_pause_plan：写开口前气口、句末收气；只有在真实分句、思考或情绪转折处才加中段停顿，不按每个标点机械停顿。continuity_contract 必须保留起止锚点、视线、道具状态、光源和下一镜承接。任何位置、视线或可移动道具变化，都必须设置 state_change=true，并记录 subject/from_state/to_state/cause/time_range；cause 必须是可见动作或明确转场。reroll_control 必须评估 T2V 身份、服装、画面左右、动作、运镜和口型同步风险，列出具体缓解方式，并为 rising/peak 人物镜设置 manual_first_pass_check。"
            "如果 qa_metadata.temporal_transition_contract.kind 不是 none，必须精确遵守它的源文触发。它只是候选，不是装饰命令：要么写一个有边界的模型内转场，其唯一效果来自当前源文事件；要么记录忠于源文的正常切换理由。启用转场时，必须写有效时间窗、唯一效果及其源文依据、前后状态、逐字提示词锚点、声音桥、闭口/OS/OV 边界和降级方案。禁止叠加特效、虚构过去事件，或在合同外改变脸、服装、场景和时代。启用的时空转场一律视为高抽卡风险并需要人工首轮验证。"
            "精确复制已锁定的 quality_contract。为每个 required_evidence 填写 qa_metadata.quality_evidence，格式为 {section, fragment}；section 只能是 主体与空间锁定/主镜头连续规则/子镜头组/光照、声音与稳定约束，fragment 必须是该段中真实出现的 3 个以上字符短语。环境镜和物件插入镜同样适用。"
            "每条已锁定的台词事件，都必须逐字保留 ref/kind/speaker/text，并填写 time_range、speaker_visibility、facial_state、body_state、delivery、lip_sync。台词和 OS 原文绝对不能改写；OS 表示内心独白，OV 表示旁白或画外声，二者都不驱动口型同步。"
            "只使用本 sidecar 中选出的契约段落。首轮不要读取示例。重试时若 packet.example_paths 存在，只读取这些文件，并且只用于修复指定失败字段。"
            "示例只迁移结构：因果表演链、道具状态转移、时间线连续、系统文字安全区、台词/口型边界、终态残留和抽卡控制；不得继承示例的题材、柔光节奏、酒店/都市场景、漫画风格、服装、人物关系或具体道具事件，除非当前源文或配置明确提供。"
            "本流程只适用于即梦 T2V：不得包含 I2V/R2V、参考素材、图片句柄或虚构锁定。通过简洁重复身份锚点、服装、画面左右、身体朝向、场景锚点和上一镜终态保持一致性。打斗镜通过限制速度、幅度、接触节拍和镜头抖动降低抽卡风险；过复杂的编舞必须拆成连续锁定片段。"
            "从 packet.composer_scaffold_path 开始写，并保留所有已锁定字段。每个场景只读取一次 packet.scene_lock_cache_path，不要重新推导共享光源、空间、服装、画幅、风格或生成设置。"
            "full_prompt 必须且只能包含五段：生成规格/主体与空间锁定/主镜头连续规则/子镜头组/光照、声音与稳定约束。"
            "每个时间窗先写一个实焦主体和屏幕位置，再写一个触发/动作、一个可见表演证据、声音/口型边界，以及当前必要的稳定控制。不要重复已锁定的风格、服装、光源、空间或通用禁令。用可见证据替代抽象效果词；不要用时长或字数填充废话。"
            "negative_prompt 是同级字段，只能包含 {{NEGATIVE_PROMPT_AUTO_INJECT}}；QA 和 generation_control 数据必须留在同级对象中。"
            "continuous_take 使用从 0.0 到准确时长的连续小数秒时间线；shot_group 使用 2-3 个连续时间段。禁止虚构参考素材路径。"
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
        "fill_order": template["fill_order"],
        "checks": _composer_preflight_checks(editorial_mode, visible, dialogue_events, reasons, dialogue_text_length),
    }


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
