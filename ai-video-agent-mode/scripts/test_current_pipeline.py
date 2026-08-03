"""Deterministic contract regression for the current pipeline's file boundaries."""
import json
import os
import sys
import tempfile
import hashlib

from context_budget import check, editor_items_fit, size as context_size
from editor_scene_windows import build
from prompt_contract import continuity_contract_issues, coverage_role_issues, cinematic_image_contract_issues, cinematic_realism_prompt_issues, dialogue_event_issues, direct_copy_prompt_issues, direct_feed_prompt_issues, expectation_anchor_issues, insert_shot_issues, jimeng_feed_prompt, listener_reaction_issues, physical_transition_chain_issues, prompt_state_machine_issues, scene_tone_palette_issues, screen_text_policy_issues, screen_text_policy_metadata_issues, shot_group_handoff_issues, source_constraint_basemap_issues, state_transition_replay_issues, story_punch_issues, temporal_transition_contract_issues, tension_curve_role_issues, visible_people_gate_issues, visual_texture_issues, video_texture_contract_issues
from pipeline_runtime import atomic_json, cache_artifact, patch_only, record_issues
from emotion_camera_audit import audit as emotion_camera_audit
from episode_state_graph import analyze_package
from spatial_storyboard import build_spatial_storyboard_reference
from current_keyframe import build_current_shot_keyframe_reference
from validate_scene_locks import validate
from shot_semantics import dispatch_risk, functional_surface_risk, temporal_transition_candidate, validation_profile
from dispatch_cache import _compact_composer_item, _composer_execution_hints, _dynamic_master_chunks, _editor_review_chunks, _retry_examples, _write_composer_scaffold, _write_constraints_sidecar, active_packet_paths, prepare_dispatch_packets
from contract_registry import (
    AGENT_PHASE_NAMES, LOCAL_PHASE_NAMES, PHASE_BATCH_SIZE,
    PHASE_TIMEOUT_SECONDS, PIPELINE_CONTRACT_VERSION, PIPELINE_PHASES,
    PROMPT_CONTRACT_VERSION,
    QA_REQUIRED_FIELDS, RISK_GATED_QA_FIELDS, SHOT_REQUIRED_FIELDS, machine_contract_issues,
    pipeline_gates,
)
from dispatch_receipts import heartbeat as receipt_heartbeat, issue as issue_receipt, load_and_verify as verify_dispatch_receipt
from pipeline_state import PHASE_ORDER, load_state, record_heartbeat as state_heartbeat, save_state, set_agent_id
from record_batch_provenance import record as record_provenance, verify as verify_provenance
from merge_agent_outputs import merge_agent_outputs, _normalize_retry_patch_fields
from pipeline_templates import GATES
from pipeline_runner import _local_phase_valid, _materialize, _review_target_shot_ids, run as pipeline_runner_run
from prepare_master_retry import prepare as prepare_master_retry
from redispatch_incomplete_master import redispatch as redispatch_incomplete_master
from check_export import INTERNAL_TITLE_LEAK, _direct_export_blocks, _export_check, _plan_index as export_plan_index, _source_dialogue_events as export_source_dialogue_events
from export_with_validation import _build_direct_copy_prompt, _build_direct_constraint_block, _global_lock_lines, _high_risk_direct_blocks_enabled, _scene_state_lines
from validate_modec import _main_shot_expectations as validate_main_shot_expectations, _source_dialogue_events as validate_source_dialogue_events
from preflight_check import PLACEHOLDER_CHARACTER_NAMES
from pre_editor_gate import run as pre_editor_gate
from validate_durations import _estimate_action_seconds
from build_shotplan import _estimate_dialogue_seconds as split_dialogue_seconds
from validate_durations import _estimate_dialogue_seconds as validated_dialogue_seconds
from generate_shotplan import _dramatic_design, _pack_action_beats, _pack_interaction_beats, _register_dramatic_beats
from validate_composer_output import validate_composer_output
from performance_budget import report as performance_report
from benchmark_core_pipeline import evaluate as evaluate_benchmark
from create_benchmark_fixtures import create as create_benchmark_fixtures
from audit_pipeline_invariants import audit as audit_pipeline_invariants
from check_rule_consistency import check as check_rule_consistency
from route_task import ROUTES as TASK_ROUTES, route as task_route


def run():
    with tempfile.TemporaryDirectory() as run_dir:
        heavy_contracts = {
            "references/format_constraints.md",
            "references/production_quality_knowledge.md",
            "references/contracts/aesthetic_directing_contract.md",
        }
        for route_name, route_spec in TASK_ROUTES.items():
            assert {"read_first", "read_on_demand", "run_only"}.issubset(route_spec)
            assert not heavy_contracts.intersection(route_spec["read_first"])
        context_outcome = task_route("full", os.path.join(run_dir, "context-plan"), intent="new")
        assert context_outcome["context_plan"]["preload_full_contracts"] is False
        assert context_outcome["context_plan"]["read_first"] == ["references/stage_gates.md"]
        os.makedirs(os.path.join(run_dir, ".cache", "analysis"))
        os.makedirs(os.path.join(run_dir, ".cache", "composer"))
        os.makedirs(os.path.join(run_dir, ".cache", "orchestrator"))
        locks = {"scenes": [{"scene": "场景A", "space_anchor": "门与长桌", "screen_positions": "甲左乙右",
                               "wardrobe_lock": "沿用确认设定", "prop_state": "文件夹在桌中央",
                               "light_source": "顶灯", "light_direction": "上方", "light_temperature": "4500K",
                               "foreground_layer": "前景桌角轻虚化形成低位框景",
                               "midground_layer": "中景长桌承载人物与文件夹活动区",
                               "background_layer": "后景右侧门与资料柜形成纵深且弱虚化",
                               "genre_visual_signature": "都市关系短剧的克制室内陈设与冷白夜灯",
                               "lived_in_detail": "桌沿细划痕与文件纸边轻微起毛",
                               "depth_focus_policy": "人物与文件夹实焦，前景桌角轻虚，后景低对比退后",
                               "landscape_identity": "冬季夜间都市办公区，玻璃与旧木形成冷硬生活质感",
                               "landscape_composition": "长桌横线压住中景，右后门形成纵深引导，左侧留白给人物关系",
                               "natural_motion_system": "空调弱风只让文件纸角低幅颤动，窗外散光缓慢移动",
                               "environment_story_arc": "起态办公室安静，文件被推动后纸角颤动，余波停在未关的右后门",
                               "reveal_order": "先见长桌与人物距离，后发现中央文件，最终停在右后门",
                               "light_weather_progression": "冬夜冷白窗光保持方向，顶灯随剧情不跳色",
                               "breathing_policy": "建立镜交代长桌纵深，人物镜只保留纸角与门口呼吸",
                               "audio_policy": "原生音频关闭"}]}
        lock_path = os.path.join(run_dir, ".cache", "analysis", "scene_locks.json")
        _write(lock_path, locks)
        assert not validate(lock_path)
        rich_locks_path = os.path.join(run_dir, ".cache", "analysis", "rich_scene_locks.json")
        rich_locks = {"scenes": [dict(
            locks["scenes"][0],
            space_id="SP-A",
            space_master_sentence="门在画面右后，长桌横贯中景，甲左乙右",
            entrance_exit="右后门进出",
            prop_activity_zone="文件夹只在桌中央到甲右手之间活动",
            tone_palette="冷白顶灯、低饱和青灰",
            light_texture_purpose="让手与文件夹边缘有浅阴影",
        )]}
        _write(rich_locks_path, rich_locks)
        assert not validate(rich_locks_path)
        broken_rich_locks_path = os.path.join(run_dir, ".cache", "analysis", "broken_rich_scene_locks.json")
        broken_rich_locks = {"scenes": [dict(rich_locks["scenes"][0], space_id="SP-A", space_master_sentence={"bad": True})]}
        _write(broken_rich_locks_path, broken_rich_locks)
        assert any("space_master_sentence must be a non-empty flat string" in issue for issue in validate(broken_rich_locks_path))
        nested_locks_path = os.path.join(run_dir, ".cache", "analysis", "nested_scene_locks.json")
        nested_locks = {"scenes": [dict(locks["scenes"][0], light_source={"kind": "顶灯"})]}
        _write(nested_locks_path, nested_locks)
        assert any("light_source must be a non-empty flat string" in issue for issue in validate(nested_locks_path))
        assert _estimate_action_seconds("我看见你了", {"dialogue_refs": ["D1"]}) == 0.0
        long_dialogue = "我最近砸资源的那个男明星跟我告白了，现在我有两个男朋友了，怎么办宝宝？"
        assert split_dialogue_seconds(long_dialogue) == validated_dialogue_seconds(long_dialogue)
        plan = {"shots": [{"shot_id": "S1", "scene": "场景A", "subshots": [{"subshot_id": "S1-01"}]},
                          {"shot_id": "S2", "scene": "场景A", "subshots": [{"subshot_id": "S2-01"}]}]}
        package = {"shots": [{"shot_id": "S1", "source_subshot_ids": ["S1-01"], "duration": 4, "full_prompt": "x", "qa_metadata": {}},
                             {"shot_id": "S2", "source_subshot_ids": ["S2-01"], "duration": 4, "full_prompt": "y", "qa_metadata": {}}]}
        _write(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"), plan)
        _write(os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json"), package)
        main_contract_plan = {"dialogue_events": {"D1": {"ref": "D1", "kind": "台词", "speaker": "甲", "text": "到这里。"}}, "shots": [
            {"shot_id": "S10", "scene": "室内", "subshots": [
                {"subshot_id": "S10-01", "characters": ["甲"], "dialogue_refs": ["D1"], "shot_size": "中景"}
            ]}
        ]}
        export_index, _scene_index, expected_source_ids = export_plan_index(main_contract_plan)
        validate_index = validate_main_shot_expectations(main_contract_plan)
        assert expected_source_ids == {"S10-01"}
        assert export_index["S10"]["characters"] == ["甲"]
        assert validate_index["S10"]["dialogue_refs"] == ["D1"]
        assert export_source_dialogue_events(main_contract_plan, {"dialogue_refs": ["D1"]})[0]["text"] == "到这里。"
        assert validate_source_dialogue_events(main_contract_plan, {"dialogue_refs": ["D1"]})[0]["speaker"] == "甲"
        export_fixture = os.path.join(run_dir, "export_contract.md")
        direct_copy_fixture = "16:9画幅，动态漫，冷白顶灯下的长桌空间。角色A在画面左侧，手机玻璃边缘有低亮反光，背景弱虚化。"
        with open(export_fixture, "w", encoding="utf-8") as handle:
            handle.write(
                "S10-01\n## 使用说明\n## 全局锁定\n"
                "## 制作质量总控\n"
                "画面质感基线：长桌构图，人物实焦，手机玻璃保留低亮反光。\n"
                "光效与曝光连续：冷白顶灯照亮手背，背景暗部保持可读。\n"
                "动态美学基线：起幅稳定，动作触发后低幅响应并停稳。\n"
                "表演与情绪基线：触发后以眼神和呼吸泄露，结尾保留余波。\n"
                "蒙太奇与剪辑基线：动作或反应切点必须增加新信息并保持声桥。\n"
                "穿帮与抽卡总控：锁定身份、支撑、手机朝向、口型和稳定终态。\n"
                "## 通用负面提示词｜直接复制\n## 场景状态表\n## 分镜投喂卡\n"
                "【画面参数】\n16:9，动态漫，冷白长桌色卡。\n"
                "【画面描述｜直接复制】\n"
                + direct_copy_fixture
                + "\n【运镜描述】\n固定镜头。\n【光影描述】\n冷白顶灯照亮手背。\n【负面提示词｜直接复制】\n手指畸形\n【表演与声音】\n无台词。\n【状态继承】\n手机仍在桌边。\n"
                "【本镜制作控制】\n"
                "画面质感：手机边缘反光是第一视觉落点，背景弱虚化。\n"
                "光效与曝光：冷白顶灯从上方照亮手背，暗部保持可读。\n"
                "动态美学：起幅手机静止，手部触发后低幅响应，固定镜头记录稳定落幅。\n"
                "表演与情绪：无可见人物表演，环境和手机状态承接当前余波。\n"
                "穿帮控制：手机仍在桌边，玻璃功能面朝向和桌面接触保持稳定。\n"
                "抽卡策略：低风险；固定机位和单一道具状态；按常规首轮检查。\n"
                "蒙太奇与剪辑：非蒙太奇；保持镜头以手机状态提供信息增量，无额外声桥。\n"
            )
        with open(os.path.splitext(export_fixture)[0] + ".xlsx", "wb") as handle:
            handle.write(b"PK")
        assert _direct_export_blocks(open(export_fixture, encoding="utf-8").read()) == [direct_copy_fixture]
        assert _export_check(export_fixture, False, {"S10-01"})[0] is True
        assert not direct_copy_prompt_issues(direct_copy_fixture, max_chars=700, require_visual_texture=True)
        bad_direct_fixture = export_fixture + ".bad.md"
        with open(bad_direct_fixture, "w", encoding="utf-8") as handle:
            handle.write(
                "S10-01\n## 使用说明\n## 全局锁定\n## 通用负面提示词｜直接复制\n## 场景状态表\n## 分镜投喂卡\n"
                "【画面参数】\n16:9。\n【画面描述｜直接复制】\n"
                "延续上一镜，角色A站着说话，电影感。\n【运镜描述】\n固定。\n【光影描述】\n电影感。\n【负面提示词｜直接复制】\n手指畸形\n【表演与声音】\n无。\n【状态继承】\n无。\n"
            )
        with open(os.path.splitext(bad_direct_fixture)[0] + ".xlsx", "wb") as handle:
            handle.write(b"PK")
        assert _export_check(bad_direct_fixture, False, {"S10-01"})[0] is False
        packet_paths = prepare_dispatch_packets(run_dir, "master_production", 6)
        assert packet_paths
        assert active_packet_paths(run_dir, "master_production") == packet_paths
        packet = _read(packet_paths[0])
        assert packet.get("source_sha256")
        assert "local_validation_command" in packet and packet["local_validation_command"][-2] == "--run-dir"
        assert os.path.abspath(packet["local_validation_command"][0]) == os.path.abspath(sys.executable)
        assert packet.get("context_policy", {}).get("quality_policy", "").startswith("Fill core fields")
        assert all("execution_hints" in item for item in packet.get("items", []))
        with open(packet["constraints_path"], encoding="utf-8") as handle:
            constraints_text = handle.read()
        assert "可见人数闸门" in constraints_text
        assert "镜头组件" in constraints_text
        assert "制作级影调色卡" in constraints_text
        assert "情绪微表演链" in constraints_text
        assert "角色表演基线" in constraints_text
        assert "特殊视角" in constraints_text
        assert len(constraints_text.encode("utf-8")) < 50000
        assert "### B2. full_prompt 五段" in constraints_text
        assert "### B1. 顶层与 shot 结构" not in constraints_text
        assert "### B7. qa_metadata" not in constraints_text
        assert "Included Contract Slice" in constraints_text
        editor_constraints_path = _write_constraints_sidecar(
            run_dir, "editor_pass2", os.path.dirname(packet["constraints_path"]), "context-budget"
        )
        with open(editor_constraints_path, encoding="utf-8") as handle:
            editor_constraints_text = handle.read()
        assert len(editor_constraints_text.encode("utf-8")) < 5000
        assert "Editor Pass 2 Semantic Review Contract" in editor_constraints_text
        assert "## §B" not in editor_constraints_text
        assert "## §C" not in editor_constraints_text
        retry_review = os.path.join(run_dir, ".cache", "review", "llm_gate_result_retry_fixture.json")
        os.makedirs(os.path.dirname(retry_review), exist_ok=True)
        _write(retry_review, {"contract_version": PROMPT_CONTRACT_VERSION, "windows": [
            {"window_id": "W001", "pass": False, "blocking": ["站位冲突"],
             "repair_targets": [{"shot_id": "S1", "field": "full_prompt"}]}
        ]})
        retry_packets = prepare_master_retry(run_dir, retry_review)
        assert retry_packets
        active_after_s1_retry = active_packet_paths(run_dir, "master_production")
        assert set(packet_paths).issubset(set(active_after_s1_retry))
        assert set(retry_packets).issubset(set(active_after_s1_retry))
        retry_packet = _read(retry_packets[0])
        assert [item["shot_id"] for item in retry_packet["items"]] == ["S1"]
        retry_context = _read(retry_packet["retry_context_path"])
        assert retry_context["fields_by_main_shot"] == {"S1": ["full_prompt", "qa_metadata.quality_evidence"]}
        _write(retry_review, {"contract_version": PROMPT_CONTRACT_VERSION, "windows": [
            {"window_id": "W002", "pass": False, "blocking": [{"shot_id": "S2", "field_path": "review_contracts.reroll_control.mitigation_steps[1]"}],
             "repair_targets": [{"shot_id": "S2", "field_path": "review_contracts.reroll_control.mitigation_steps[1]"}]}
        ]})
        retry_packets = prepare_master_retry(run_dir, retry_review)
        active_after_s2_retry = active_packet_paths(run_dir, "master_production")
        assert set(retry_packets).issubset(set(active_after_s2_retry))
        retry_context = _read(_read(retry_packets[0])["retry_context_path"])
        assert retry_context["fields_by_main_shot"] == {"S2": ["review_contracts.reroll_control.mitigation_steps[1]"]}
        duplicate_retry_packets = prepare_master_retry(run_dir, retry_review)
        active_after_duplicate_retry = active_packet_paths(run_dir, "master_production")
        assert duplicate_retry_packets == retry_packets
        assert active_after_duplicate_retry == active_after_s2_retry
        active_manifest = _read(os.path.join(run_dir, ".cache", "dispatch", "active_master_production_manifest.json"))
        assert active_manifest["active_packet_count"] == len(active_after_duplicate_retry)
        assert active_manifest["active_retry_packet_count"] >= 2
        assert all(entry.get("effective") is True for entry in active_manifest.get("packets", []))
        assert not any(
            entry.get("packet_path") == os.path.abspath(retry_packets[0])
            and entry.get("superseded_reason") == "retry_replaced_by_newer_target"
            for entry in active_manifest.get("superseded_packets", [])
        )
        _write(retry_review, {"contract_version": PROMPT_CONTRACT_VERSION, "windows": [
            {"window_id": "W002", "pass": False, "blocking": [{"shot_id": "S2", "field_path": "full_prompt"}],
             "repair_targets": [{"shot_id": "S2", "field_path": "full_prompt"}]}
        ]})
        second_round_retry_packets = prepare_master_retry(run_dir, retry_review)
        active_after_second_round = active_packet_paths(run_dir, "master_production")
        assert set(second_round_retry_packets).issubset(set(active_after_second_round))
        # Newer retry packets inherit earlier field scopes, so they can safely
        # replace older same-shot retries without dropping unrelated fixes.
        assert not set(retry_packets) & set(active_after_second_round)
        assert _read(second_round_retry_packets[0])["batch_size"] == 1
        assert _read(_read(second_round_retry_packets[0])["retry_context_path"])["fields_by_main_shot"] == {
            "S2": ["full_prompt", "qa_metadata.quality_evidence", "review_contracts.reroll_control.mitigation_steps[1]"]
        }
        active_manifest = _read(os.path.join(run_dir, ".cache", "dispatch", "active_master_production_manifest.json"))
        assert not any(
            entry.get("packet_path") == os.path.abspath(second_round_retry_packets[0])
            and entry.get("superseded_reason") == "retry_replaced_by_newer_target"
            for entry in active_manifest.get("superseded_packets", [])
        )
        assert any(
            entry.get("packet_path") == os.path.abspath(retry_packets[0])
            and entry.get("superseded_reason") == "retry_replaced_by_newer_target"
            and entry.get("effective") is False
            for entry in active_manifest.get("superseded_packets", [])
        )
        previous = {"qa_metadata": {"reroll_control": {"mitigation_steps": ["keep", "left hand"]}}}
        replacement = {"qa_metadata": {"reroll_control": {"mitigation_steps": ["keep", "right hand"]}}}
        patched = patch_only(previous, replacement, ["review_contracts.reroll_control.mitigation_steps[1]"])
        assert patched["qa_metadata"]["reroll_control"]["mitigation_steps"] == ["keep", "right hand"]
        assert _normalize_retry_patch_fields(["full_prompt.生成规格"]) == ["full_prompt", "qa_metadata.quality_evidence"]
        patched_prompt = patch_only(
            {
                "full_prompt": "生成规格：16:9横屏。",
                "qa_metadata": {"quality_evidence": {"axis_continuity": {"fragment": "同侧轴线"}}},
                "locked": "keep",
            },
            {
                "full_prompt": "生成规格：9:16竖屏。",
                "qa_metadata": {"quality_evidence": {"axis_continuity": {"fragment": "画面左侧保持"}}},
                "locked": "changed",
            },
            _normalize_retry_patch_fields(["full_prompt.生成规格"]),
        )
        assert "9:16" in patched_prompt["full_prompt"]
        assert patched_prompt["qa_metadata"]["quality_evidence"]["axis_continuity"]["fragment"] == "画面左侧保持"
        assert patched_prompt["locked"] == "keep"
        os.makedirs(os.path.join(run_dir, ".cache", "review"), exist_ok=True)
        _write(os.path.join(run_dir, ".cache", "review", "pre_editor_gate.json"),
               {"pass": True, "package_sha256": "stale"})
        state = load_state(run_dir)
        state["current_phase"] = "editor_pass1"
        state["phases"]["editor_pass1"]["status"] = "done"
        save_state(run_dir, state)
        stale_outcome = pipeline_runner_run(run_dir)
        assert stale_outcome["action"] == "local_action_required"
        assert load_state(run_dir)["phases"]["editor_pass1"]["status"] == "pending"
        assert "grid_storyboard" not in GATES
        assert "grid_storyboard" not in PHASE_ORDER
        assert tuple(PHASE_ORDER) == PIPELINE_PHASES
        assert GATES == pipeline_gates()
        assert not machine_contract_issues()
        assert AGENT_PHASE_NAMES == frozenset({"scene_lock", "master_production", "editor_pass2"})
        assert LOCAL_PHASE_NAMES == frozenset(set(PIPELINE_PHASES) - set(AGENT_PHASE_NAMES))
        assert PHASE_TIMEOUT_SECONDS["master_production"] == 720
        assert PHASE_BATCH_SIZE["master_production"] == 6
        assert load_state(run_dir)["pipeline_contract_version"] == PIPELINE_CONTRACT_VERSION
        assert not any("execution_hints" in shot for shot in package["shots"])
        windows = build(run_dir)
        assert len(windows) == 2 and windows[0]["current"]["shot_id"] == "S1" and windows[1]["previous"]["shot_id"] == "S1"
        targeted_windows = build(run_dir, shot_ids=["S2"])
        assert len(targeted_windows) == 1
        assert targeted_windows[0]["current"]["shot_id"] == "S2"
        assert targeted_windows[0]["previous"]["shot_id"] == "S1"
        assert windows[0]["capsule_version"] == "editor-review-v1"
        assert "prompt_digest" in windows[0]["current"]
        assert "full_prompt" not in windows[0]["current"]
        assert "full_prompt" not in windows[0]["next"]
        assert editor_items_fit(windows)
        assert check({"items": [{"shot_id": "S1"}]}) > 0
        assert {"shot_id", "subshot_id", "duration", "full_prompt", "negative_prompt", "qa_metadata", "generation_control"} == SHOT_REQUIRED_FIELDS
        assert "temporal_transition_contract" in QA_REQUIRED_FIELDS
        assert "story_punch_contract" not in QA_REQUIRED_FIELDS
        assert RISK_GATED_QA_FIELDS["story_punch_contract"] == "story_punch_contract"
        retry_context_path = os.path.join(run_dir, "retry_context.json")
        _write(retry_context_path, {"items": [{"repair_fields": ["full_prompt"]}]})
        assert [os.path.basename(path) for path in _retry_examples(retry_context_path)] == ["format_example.txt"]
        _write(retry_context_path, {"items": [{"repair_fields": ["performance_contract"]}]})
        assert [os.path.basename(path) for path in _retry_examples(retry_context_path)] == ["S2-03_high_quality_example.txt"]
        _write(retry_context_path, {"items": [{"repair_fields": ["full_prompt", "qa_metadata"]}]})
        assert {os.path.basename(path) for path in _retry_examples(retry_context_path)} == {"format_example.txt", "S2-03_high_quality_example.txt"}
        assert INTERNAL_TITLE_LEAK.search("S02 | S1-02 | | 11.6s | dialogue | latent")
        assert not INTERNAL_TITLE_LEAK.search("### S1-02｜11.6秒")
        assert "主角" in PLACEHOLDER_CHARACTER_NAMES
        beat_records = []
        beat_ids = _register_dramatic_beats(
            beat_records,
            {"type": "action", "source_ids": ["SRC0001"]},
            "S1-01-01",
            ["侍卫拖拽穿越女", "衣料擦过地砖"],
        )
        design = _dramatic_design({"type": "action"}, "侍卫拖拽穿越女", ["侍卫", "穿越女"], beat_ids)
        assert design["narrative_beat_id"] == beat_ids[0]
        assert {record["narrative_beat_id"] for record in beat_records} == {beat_ids[0]}
        separated_actions = _pack_action_beats([
            {"type": "action", "scene": "殿内", "text": "侍卫拖拽穿越女向殿门移动", "source_ids": ["SRC0001"]},
            {"type": "action", "scene": "殿内", "text": "皇后冷漠看向殿门", "source_ids": ["SRC0002"]},
        ], 10, ["侍卫", "穿越女", "皇后"])
        assert len(separated_actions) == 2
        packed_dialogue = _pack_interaction_beats([
            {"type": "dialogue", "scene": "殿内", "speaker": "角色A", "text": "你来迟了。", "refs": ["D1"], "speech_duration": 1.0, "source_ids": ["SRC0003"]},
            {"type": "dialogue", "scene": "殿内", "speaker": "角色B", "text": "我没有选择。", "refs": ["D2"], "speech_duration": 1.2, "source_ids": ["SRC0004"]},
            {"type": "dialogue", "scene": "殿内", "speaker": "角色A", "text": "那就承担后果。", "refs": ["D3"], "speech_duration": 1.2, "source_ids": ["SRC0005"]},
        ], 10)
        assert len(packed_dialogue) == 2 and packed_dialogue[0]["type"] == "dialogue_group"
        benchmark_dialogue = _pack_interaction_beats([
            {"type": "dialogue", "scene": "殿内", "speaker": "角色A", "text": "你来迟了。", "refs": ["D1"], "speech_duration": 1.0, "source_ids": ["SRC0003"]},
            {"type": "dialogue", "scene": "殿内", "speaker": "角色B", "text": "我没有选择。", "refs": ["D2"], "speech_duration": 1.2, "source_ids": ["SRC0004"]},
            {"type": "dialogue", "scene": "殿内", "speaker": "角色A", "text": "那就承担后果。", "refs": ["D3"], "speech_duration": 1.2, "source_ids": ["SRC0005"]},
        ], 10, force_single_dialogue=True)
        assert len(benchmark_dialogue) == 3 and all(item["type"] == "dialogue" for item in benchmark_dialogue)
        atomic_json(os.path.join(run_dir, ".cache", "control.json"), {"ok": True})
        assert _read(os.path.join(run_dir, ".cache", "control.json"))["ok"] is True
        cache_artifact(run_dir, "test", {"value": 1})
        record_issues(run_dir, "first", ["a"])
        record_issues(run_dir, "second", ["b"])
        assert set(_read(os.path.join(run_dir, ".cache", "issues.json"))) == {"first", "second"}
        receipt_packet = {
            "contract_version": PROMPT_CONTRACT_VERSION, "run_dir": run_dir, "phase": "master_production",
            "dispatch_id": "receipt-test", "_batch_output_path": os.path.join(run_dir, "worker.json"),
        }
        receipt_packet_path = os.path.join(run_dir, "receipt_packet.json")
        _write(receipt_packet_path, receipt_packet)
        issue_receipt(receipt_packet_path, receipt_packet, "agent-receipt-test")
        try:
            verify_dispatch_receipt(receipt_packet_path, receipt_packet, "agent-receipt-test")
            raise AssertionError("dispatch receipt gate accepted a worker without a heartbeat")
        except ValueError as error:
            assert "heartbeat" in str(error)
        receipt_heartbeat(receipt_packet_path, receipt_packet, "agent-receipt-test")
        assert verify_dispatch_receipt(receipt_packet_path, receipt_packet, "agent-receipt-test")[0]["heartbeat_count"] == 1
        gate_packet_path = prepare_dispatch_packets(run_dir, "scene_lock")[0]
        gate_packet = _read(gate_packet_path)
        with open(gate_packet["constraints_path"], "r", encoding="utf-8-sig") as handle:
            scene_lock_constraints = handle.read()
        assert '`{"scenes":[' in scene_lock_constraints
        assert "归档分析记录" not in scene_lock_constraints
        assert '"items": []' not in scene_lock_constraints
        assert "只允许 `items`" not in scene_lock_constraints
        batch_path = gate_packet["_batch_output_path"]
        gate_dispatch_id = gate_packet["dispatch_id"]
        issue_receipt(gate_packet_path, gate_packet, "agent-gate-test")
        set_agent_id(run_dir, "scene_lock", "agent-gate-test", dispatch_id=gate_dispatch_id)
        _write(batch_path, locks)
        state_heartbeat(run_dir, "scene_lock", "agent-gate-test", gate_dispatch_id)
        receipt_heartbeat(gate_packet_path, gate_packet, "agent-gate-test")
        record_provenance(gate_packet_path)
        assert verify_provenance(batch_path)[0] is True
        invariant_result = audit_pipeline_invariants(run_dir)
        assert invariant_result["pass"] is True
        broken_state = _read(os.path.join(run_dir, ".cache", "pipeline_state.json"))
        broken_state["phases"]["scene_lock"]["dispatches"][gate_dispatch_id]["recorded_at"] = 0
        _write(os.path.join(run_dir, ".cache", "pipeline_state.json"), broken_state)
        assert any("recorded_at早于spawn_time" in issue for issue in audit_pipeline_invariants(run_dir)["issues"])
        broken_state["phases"]["scene_lock"]["dispatches"][gate_dispatch_id]["recorded_at"] = load_state(run_dir)["phases"]["scene_lock"]["dispatches"][gate_dispatch_id]["heartbeat_at"] + 1
        _write(os.path.join(run_dir, ".cache", "pipeline_state.json"), broken_state)
        assert audit_pipeline_invariants(run_dir)["pass"] is True
        # Batch provenance is not phase completion: the runner must still
        # materialize every verified batch before it can advance.
        assert load_state(run_dir)["phases"]["scene_lock"]["status"] == "waiting"
        try:
            merge_agent_outputs(os.path.join(run_dir, "forbidden_merge.json"), batch_path, require_provenance=False)
            raise AssertionError("public merge accepted an unguarded provenance mode")
        except ValueError as error:
            assert "DISPATCH_GATE" in str(error)
        canonical = "生成规格：规格\n\n主体与空间锁定：空间\n\n主镜头连续规则：规则\n\n子镜头组：【镜头1｜0.0-1.0秒】画面\n\n光照、声音与稳定约束：光声"
        assert "生成规格：" not in jimeng_feed_prompt(canonical)
        feed_meta_prompt = canonical.replace("主镜头连续规则：规则", "主镜头连续规则：承接上一镜，下一镜继承手中手机，尾帧位置不变，切到角色A")
        feed = jimeng_feed_prompt(feed_meta_prompt)
        assert "上一镜" not in feed and "继承" not in feed and "尾帧" not in feed and "切到" not in feed
        assert not direct_feed_prompt_issues(feed_meta_prompt)
        unsafe_ui_prompt = canonical.replace("画面", "手机聊天消息以绿色气泡显示：你到了吗？")
        assert screen_text_policy_issues(unsafe_ui_prompt)
        safe_ui_prompt = canonical.replace("画面", "手机聊天消息以绿色气泡显示：你到了吗？文字为独立二维浮层，位于画面右侧安全区，不跟随手机透视")
        assert not screen_text_policy_issues(safe_ui_prompt)
        visible_gate_metadata = {
            "source_constraint_basemap": {
                "visible_people_gate": {
                    "visible_count": 1,
                    "clear": "林夏清晰入画",
                    "offscreen": "顾辰门外右侧画外声源不入画",
                },
            },
            "dialogue_events": [{"speaker": "顾辰", "speaker_visibility": "offscreen"}],
        }
        visible_gate_prompt = (
            "生成规格：9:16画幅。\n\n"
            "主体与空间锁定：本镜画面内可见人数：1人；林夏清晰入画，顾辰为门外右侧画外声源不入画。\n\n"
            "主镜头连续规则：林夏视线压向右侧门口声源，顾辰不生成实体人物。\n\n"
            "子镜头组：【镜头1｜0.0-2.0秒】林夏闭口听完画外声，手指压住文件夹边缘。\n\n"
            "光照、声音与稳定约束：冷白顶灯照亮林夏脸侧和纸面。"
        )
        assert not visible_people_gate_issues(visible_gate_metadata, visible_gate_prompt, ["林夏"])
        assert visible_people_gate_issues(
            {"dialogue_events": [{"speaker": "顾辰", "speaker_visibility": "offscreen"}]},
            visible_gate_prompt, ["林夏"],
        )
        invalid_offscreen_target = visible_gate_prompt.replace("右侧门口声源", "顾辰")
        assert any("不得作为看向" in issue for issue in visible_people_gate_issues(
            visible_gate_metadata, invalid_offscreen_target, ["林夏"]
        ))
        formal_metadata = {
            "source_constraint_basemap": {
                "space_basis": "甲左乙右，门在右后",
                "state_prop_basis": "手机起幅在桌右前角",
                "character_orientation_basis": "甲面向右，乙面向左",
                "tension_curve_role": "升压",
                "sound_lip_sync_basis": "甲说台词，乙闭口倾听",
                "screen_text_policy": "AI二维浮层",
                "performance_baseline_lock": "甲克制冷感，优先泄露部位为眼睑和手指，动作低幅，爆发阈值为关系决裂，禁用夸张捂嘴",
                "dialogue_performance_kernel": "台词功能为求证，甲口型同步，关键词后停半拍，乙闭口低幅反应，句末闭口，落幅手停文件边缘",
                "emotion_residue_contract": "触发前克制，泄露在眼睑和手指，压抑为移开视线，尾帧残留为手仍压住文件",
                "viewpoint_motion_lock": "none",
                "premium_director_polish": "按即梦友好导演卡排序，保留色卡、台词反应、低幅推近和文件边缘反光",
                "creative_profile": "balanced",
                "single_shot_risk": "对白加手机屏幕，控制为中风险",
            },
            "scene_tone_palette": {
                "space_id": "SP-A",
                "space_master_sentence": "门在右后，长桌横贯中景，甲左乙右",
                "tone_palette": "冷白顶灯、低饱和青灰",
                "light_texture_purpose": "让手机玻璃边缘有低亮反光",
                "visual_scene_prefix": "冷白顶灯下的长桌空间",
                "foreground_layer": "前景桌角轻虚化形成低位框景",
                "midground_layer": "中景长桌承载甲乙与手机活动区",
                "background_layer": "后景右侧门与资料柜形成纵深且弱虚化",
                "genre_visual_signature": "都市关系短剧的克制室内陈设与冷白夜灯",
                "lived_in_detail": "桌沿细划痕与手机玻璃指印",
                "depth_focus_policy": "人物与手机实焦，前景桌角轻虚，后景低对比退后",
                "landscape_identity": "冬季夜间都市办公室，玻璃、旧木与文件构成克制职业气味",
                "landscape_composition": "长桌横向分割中景，右后门形成纵深引导，人物间中央留白",
                "natural_motion_system": "空调弱风只让纸角低幅颤动，窗外散光缓慢移动",
                "environment_story_arc": "起态空间安静，手机亮起后玻璃反光增强，余波落在未关的门",
                "reveal_order": "先见人物和长桌距离，后发现手机，最终停在右后门",
                "light_weather_progression": "冬夜冷白窗光保持方向，顶灯不跳色",
                "breathing_policy": "人物镜只保留纸角和门口低幅环境呼吸",
            },
            "screen_text_policy": {
                "mode": "ai_overlay",
                "text_refs": ["UI1"],
                "render_rule": "聊天消息由AI作为独立二维浮层生成",
                "safe_area": "画面右侧安全区",
                "perspective_rule": "不贴手机背面，不跟随手机透视",
            },
            "tension_curve_role": "升压",
        }
        assert not source_constraint_basemap_issues(formal_metadata)
        assert not scene_tone_palette_issues(formal_metadata)
        layered_prompt = (
            "生成规格：16:9画幅，都市关系短剧。\n\n"
            "主体与空间锁定：前景桌角轻虚化形成低位框景，中景长桌承载甲乙与手机活动区，"
            "后景右侧门与资料柜低对比退后；长桌横向分割中景，右后门形成纵深引导，人物间中央留白。\n\n"
            "主镜头连续规则：人物与手机实焦，背景弱虚化不抢焦。\n\n"
            "子镜头组：【镜头1｜0.0-4.0秒】甲把手机停在桌边，乙闭口看着。\n\n"
            "光照、声音与稳定约束：冷白夜灯照亮桌沿细划痕与手机玻璃指印。"
        )
        assert not scene_tone_palette_issues(formal_metadata, layered_prompt)
        assert any("至少两层" in issue for issue in scene_tone_palette_issues(
            formal_metadata,
            layered_prompt.replace("前景桌角轻虚化形成低位框景，", "").replace("后景右侧门与资料柜低对比退后", "空背景"),
        ))
        assert not screen_text_policy_metadata_issues(formal_metadata, safe_ui_prompt)
        assert not tension_curve_role_issues(formal_metadata)
        repeated_palette_lines = _global_lock_lines({"shots": [
            {"shot_id": "S10", "qa_metadata": {"scene_tone_palette": formal_metadata["scene_tone_palette"]}},
            {"shot_id": "S11", "qa_metadata": {"scene_tone_palette": dict(formal_metadata["scene_tone_palette"], visual_scene_prefix="冷白顶灯下的长桌空间，手机玻璃低亮反光")}},
        ]}, {"visual_style": "动态漫"})
        palette_section = repeated_palette_lines[repeated_palette_lines.index("- 本集影调色卡索引："):]
        assert sum(1 for line in palette_section if line.startswith("- SP-A：")) == 1
        assert any("手机玻璃低亮反光" in line for line in repeated_palette_lines)
        scene_rows = _scene_state_lines(
            {"shots": [{"shot_id": "S10", "qa_metadata": {"scene_tone_palette": formal_metadata["scene_tone_palette"]}}]},
            {"shots": [{"shot_id": "S10", "scene": "场景A"}]},
        )
        assert "前中后景层次" in scene_rows[0] and "题材与生活质感" in scene_rows[0]
        assert "风景身份与构图" in scene_rows[0] and "环境演进与呼吸" in scene_rows[0]
        assert "前景桌角" in scene_rows[1] and "都市关系短剧" in scene_rows[1] and "人物与手机实焦" in scene_rows[1]
        assert "长桌横向分割" in scene_rows[1] and "手机亮起后" in scene_rows[1]
        bad_formal = json.loads(json.dumps(formal_metadata, ensure_ascii=False))
        bad_formal["source_constraint_basemap"]["tension_curve_role"] = "乱写"
        assert source_constraint_basemap_issues(bad_formal)
        bad_profile = json.loads(json.dumps(formal_metadata, ensure_ascii=False))
        bad_profile["source_constraint_basemap"]["creative_profile"] = "wild"
        assert any("creative_profile" in issue for issue in source_constraint_basemap_issues(bad_profile))
        bad_ui_policy = json.loads(json.dumps(formal_metadata, ensure_ascii=False))
        bad_ui_policy["screen_text_policy"]["safe_area"] = ""
        assert screen_text_policy_metadata_issues(bad_ui_policy, unsafe_ui_prompt)
        fixed_medium = canonical.replace("规则", "中近景，固定机位")
        assert coverage_role_issues({"dramatic_design": {"coverage_role": "relationship_blocking"}}, fixed_medium)
        assert not coverage_role_issues({"dramatic_design": {"coverage_role": "dialogue_performance"}}, fixed_medium)
        figurative_prompt = canonical.replace("画面", "庭前花枝对着空门，风吹花瓣落向门槛；画面保持空门与花枝，空门仍未有人归来")
        figurative_anchor = {"expectation_anchor": {
            "applicable": True, "semantic_mode": "figurative_personification", "anchor_type": "space",
            "anchor": "庭前花枝", "expecting_subject": "庭前花枝", "source_interpretation": "将花等归人按环境意象处理",
            "start_state": "庭前花枝对着空门", "progress_event": "风吹花瓣落向门槛",
            "detail_cut_rule": "保持同镜头", "return_reaction": "画面保持空门与花枝", "end_state": "空门仍未有人归来",
        }}
        assert not expectation_anchor_issues(figurative_anchor, figurative_prompt)
        dialogue_metadata = {"dialogue_refs": ["D-01"], "dialogue_events": [{
            "ref": "D-01", "kind": "OV", "speaker": "旁白", "text": "门外一直没有脚步声。",
            "time_range": "0.0-3.0秒", "speaker_visibility": "offscreen", "facial_state": "N/A，画外旁白",
            "body_state": "N/A，画外旁白", "delivery": "低声说到“没有”时压低重音，句末轻收",
            "breath_pause_plan": "句前0.2秒吸气；无中段气口；句末0.3秒收气", "lip_sync": False,
            "line_function": "narrate", "subtext": "用门外寂静强调等待落空", "stress_words": ["没有"],
            "subtext_visible_evidence": "N/A，无可见承接人物", "turn_relation": "bridge",
        }]}
        assert not dialogue_event_issues(dialogue_metadata, None, [], canonical, False, 3)
        dialogue_metadata["dialogue_events"][0]["breath_pause_plan"] = ""
        assert any("breath_pause_plan" in issue for issue in dialogue_event_issues(dialogue_metadata, None, [], canonical, False, 3))
        audible_dialogue_metadata = {"dialogue_refs": ["D-02"], "dialogue_events": [{
            "ref": "D-02", "kind": "台词", "speaker": "角色A", "text": "你来迟了。",
            "time_range": "0.0-1.8秒", "speaker_visibility": "visible", "facial_state": "角色A视线压住角色B",
            "body_state": "角色A肩线不动", "delivery": "低声说到“迟了”时压住重音，尾音收短",
            "breath_pause_plan": "句前0.2秒吸气；无中段气口；句末0.3秒收气", "lip_sync": True,
            "line_function": "challenge", "subtext": "责问对方为何直到现在才出现", "stress_words": ["迟了"],
            "subtext_visible_evidence": "角色A视线压住角色B", "turn_relation": "initiate",
        }]}
        audible_prompt = canonical.replace(
            "画面",
            "角色A（台词）: \"你来迟了。\" 角色A视线压住角色B，角色A肩线不动，低声说到“迟了”时压住重音，尾音收短，句前0.2秒吸气；无中段气口；句末0.3秒收气，口型同步并句末闭口，落幅仍看向角色B",
        )
        assert not dialogue_event_issues(audible_dialogue_metadata, None, ["角色A"], audible_prompt, True, 2)
        bad_audible_prompt = audible_prompt.replace("角色A（台词）: \"你来迟了。\"", "角色A（台词）：“你来迟了。”")
        assert any("半角格式" in issue for issue in dialogue_event_issues(audible_dialogue_metadata, None, ["角色A"], bad_audible_prompt, True, 2))
        listener_prompt = canonical.replace("主镜头连续规则：规则", "主镜头连续规则：固定机位保持角色B低幅反应").replace("画面", "角色B在画面右侧中景，角色B视线停在角色A脸上，拇指在杯沿轻收一次，不起身、不转向抢画面；角色B口型闭合，手仍停在杯沿，视线留在角色A方向")
        listener_metadata = {"performance_priority": {"primary": "角色A", "supporting": ["角色B"], "background": []}, "dialogue_events": [{"kind": "台词", "speaker": "角色A", "speaker_visibility": "visible"}], "listener_reaction_plan": {"speaker": "角色A", "listener": "角色B", "trigger": "角色A说到关键事实", "time_range": "0.2-0.8秒", "visual_evidence": "角色B视线停在角色A脸上，拇指在杯沿轻收一次", "motion_limit": "不起身、不转向抢画面", "lip_sync": False, "end_residue": "角色B口型闭合，手仍停在杯沿，视线留在角色A方向"}}
        assert not listener_reaction_issues(listener_metadata, listener_prompt)
        flat_story_metadata = {"performance_priority": {"primary": "角色A", "supporting": [], "background": []}, "dialogue_events": [{"kind": "台词", "speaker": "角色A"}], "story_punch_contract": {"audience_question": "气氛是否紧张", "character_pressure": "紧张", "visible_pressure_object": "气氛紧张", "dramatic_turn": "情绪变化", "picture_punctuation": "表情复杂", "end_residue": "保持状态"}}
        assert story_punch_issues(flat_story_metadata, audible_prompt, ["角色A"])
        bland_prompt = canonical.replace("画面", "角色A看向角色B，角色A肩线保持不动；角色B看向角色A，落幅两人位置不变，下一镜继承两人位置")
        bland_story_metadata = {"performance_priority": {"primary": "角色A", "supporting": ["角色B"], "background": []}, "dialogue_events": [{"kind": "台词", "speaker": "角色A"}], "story_punch_contract": {"audience_question": "角色A是否会回应角色B的沉默", "character_pressure": "角色A面对角色B的沉默不知道如何回应", "visible_pressure_object": "角色A看向角色B", "dramatic_turn": "角色B看向角色A", "picture_punctuation": "角色A肩线保持不动", "end_residue": "下一镜继承两人位置"}}
        assert any("可见戏剧尖刺" in issue for issue in story_punch_issues(bland_story_metadata, bland_prompt, ["角色A", "角色B"]))
        sharp_story_metadata = {"performance_priority": {"primary": "角色A", "supporting": ["角色B"], "background": []}, "dialogue_events": [{"kind": "台词", "speaker": "角色A"}], "story_punch_contract": {"audience_question": "角色B是否被角色A这句迟到指责刺中", "character_pressure": "角色B听见指责后压住反应，不让自己抢台词", "visible_pressure_object": "拇指在杯沿轻收一次", "dramatic_turn": "角色B视线停在角色A脸上", "picture_punctuation": "拇指在杯沿轻收一次", "composition_priority": "角色B在画面右侧中景", "camera_motivation": "固定机位保持角色B低幅反应", "end_residue": "视线留在角色A方向"}}
        assert not story_punch_issues(sharp_story_metadata, listener_prompt, ["角色A", "角色B"])
        spatial_prop_prompt = (
            "生成规格：规格\n\n"
            "主体与空间锁定：角色A在画面左侧中景，身体朝向画面右侧；角色B在画面右侧中景，身体朝向画面左侧；角色C在画面中间偏后景，身体朝向画面前侧略偏左。药瓶在桌面右前角，瓶口朝画面左，未被任何人接触。\n\n"
            "主镜头连续规则：单一剧情问题围绕角色A是否说出真相；角色A抬眼触发压力。空间保持A左、B右、C中后方，药瓶起始位于桌面右前角、瓶口朝画面左、无人接触，落幅仍在桌面右前角并由下一镜继承。主要运镜固定，禁止人物穿过A与B之间的屏幕空间线。\n\n"
            "子镜头组：【镜头1｜0.0-1.0秒】角色A在画面左侧中景，视线落向角色B；药瓶仍在桌面右前角，未被任何人接触。角色A只抬眼停住半拍，固定机位保持中景，落幅药瓶仍在桌面右前角，下一镜继承，不离开桌面。\n\n"
            "光照、声音与稳定约束：同源光照保持"
        )
        spatial_prop_metadata = {"continuity_contract": {"prop_state": "药瓶在桌面右前角，瓶口朝画面左，未被任何人接触"}}
        assert not prompt_state_machine_issues(spatial_prop_metadata, spatial_prop_prompt, ["角色A", "角色B", "角色C"])
        vague_prop_prompt = canonical.replace("空间", "角色A在角色B旁边，角色C在后面").replace("画面", "角色A看向角色B，药瓶突然到手上")
        assert prompt_state_machine_issues(spatial_prop_metadata, vague_prop_prompt, ["角色A", "角色B", "角色C"])
        transfer_prompt = (
            "生成规格：规格\n\n"
            "主体与空间锁定：角色A在画面左侧中景，身体朝向画面右侧；手机起幅在桌面右前角。\n\n"
            "主镜头连续规则：角色A要接起电话，手机从桌面右前角转移到角色A右手，手先伸向手机、指尖接触后拿起，落幅手机在角色A右手中，下一镜继承。\n\n"
            "子镜头组：【镜头1｜0.0-1.0秒】角色A在画面左侧中景，视线落向手机，右手从身侧伸向桌面右前角手机，指尖接触手机边缘后拿起，落幅手机在角色A右手中，下一镜继承。\n\n"
            "光照、声音与稳定约束：同源光照保持"
        )
        transfer_metadata = {"continuity_contract": {
            "start_anchor": "手机起幅在桌面右前角",
            "end_anchor": "落幅手机在角色A右手中",
            "position_continuity": "角色A在画面左侧中景",
            "eyeline_continuity": "视线落向手机",
            "prop_state": "手机从桌面右前角转移到角色A右手",
            "lighting_continuity": "同源光照保持",
            "next_carryover": "手机在角色A右手中，下一镜继承",
            "state_change": True,
            "state_transitions": [{
                "subject": "手机",
                "from_state": "手机起幅在桌面右前角",
                "intermediate_state": "右手从身侧伸向桌面右前角手机，指尖接触手机边缘后拿起",
                "to_state": "落幅手机在角色A右手中",
                "cause": "角色A要接起电话",
                "time_range": "0.0-1.0秒",
            }],
        }}
        transfer_issues = continuity_contract_issues(transfer_metadata, transfer_prompt, ["角色A"])
        assert not transfer_issues, transfer_issues
        assert not physical_transition_chain_issues(transfer_metadata, transfer_prompt)
        episode_graph = analyze_package({"contract_version": PROMPT_CONTRACT_VERSION, "shots": [
            {
                "shot_id": "S1", "subshot_id": "S1", "source_subshot_ids": ["SRC-1"],
                "qa_metadata": {
                    "dialogue_refs": ["D1"],
                    "scene_tone_palette": {
                        "space_id": "SP-A", "space_master_sentence": "门在右后，长桌横贯中景",
                        "tone_palette": "冷白顶灯、低饱和青灰",
                    },
                    "continuity_contract": {
                        "start_anchor": "手机在桌面右前角", "end_anchor": "手机在角色A右手中亮屏",
                        "next_carryover": "手机在角色A右手中亮屏",
                        "state_transitions": transfer_metadata["continuity_contract"]["state_transitions"],
                    },
                },
            },
            {
                "shot_id": "S2", "subshot_id": "S2", "source_subshot_ids": ["SRC-2"],
                "qa_metadata": {
                    "dialogue_refs": [],
                    "scene_tone_palette": {
                        "space_id": "SP-A", "space_master_sentence": "门在右后，长桌横贯中景",
                        "tone_palette": "冷白顶灯、低饱和青灰",
                    },
                    "continuity_contract": {
                        "start_anchor": "手机在角色A右手中亮屏", "end_anchor": "手机仍在角色A右手中亮屏",
                        "next_carryover": "手机仍在角色A右手中亮屏", "state_transitions": [],
                    },
                },
            },
        ]})
        assert episode_graph["pass"] is True
        assert episode_graph["summary"]["edge_count"] == 1
        assert episode_graph["nodes"][0]["semantic_lineage"]["source_refs"] == ["SRC-1"]
        hand_conflict = json.loads(json.dumps(episode_graph, ensure_ascii=False))
        conflict_package = {"contract_version": PROMPT_CONTRACT_VERSION, "shots": [
            {
                "shot_id": "S1", "subshot_id": "S1", "source_subshot_ids": ["SRC-1"],
                "qa_metadata": {"scene_tone_palette": {"space_id": "SP-A", "space_master_sentence": "长桌横贯中景", "tone_palette": "冷白"},
                                "continuity_contract": {"end_anchor": "手机在角色A右手中", "next_carryover": "手机在角色A右手中", "state_transitions": []}},
            },
            {
                "shot_id": "S2", "subshot_id": "S2", "source_subshot_ids": ["SRC-2"],
                "qa_metadata": {"scene_tone_palette": {"space_id": "SP-A", "space_master_sentence": "长桌横贯中景", "tone_palette": "冷白"},
                                "continuity_contract": {"start_anchor": "手机无动作直接出现在角色A左手中", "state_transitions": []}},
            },
        ]}
        hand_conflict = analyze_package(conflict_package)
        assert hand_conflict["pass"] is False
        assert any("hand" in issue for issue in hand_conflict["issues"])
        duplicate_source = json.loads(json.dumps(conflict_package, ensure_ascii=False))
        duplicate_source["shots"][1]["source_subshot_ids"] = ["SRC-1"]
        assert any("重复消费" in issue for issue in analyze_package(duplicate_source)["issues"])
        abstract_visual_prompt = canonical.replace("光声", "电影感，高级质感，真实感")
        assert visual_texture_issues(abstract_visual_prompt)
        grounded_visual_prompt = canonical.replace("光声", "4300K冷白顶灯从上方落下，角色A手背受光，手机玻璃边缘有低亮反光，背景弱虚化")
        assert not visual_texture_issues(grounded_visual_prompt)
        synthetic_cg_prompt = (
            "16:9画幅，动态漫电影分镜，雨夜走廊，水面像镜子一样完美反射，墙面过度干净，"
            "雨线均匀，灯管过曝，整体CG感强。"
        )
        assert cinematic_realism_prompt_issues(synthetic_cg_prompt, require_live_action_style=True)
        cinematic_prompt = (
            "16:9画幅，写实电影剧照，雨夜蓝黑旧走廊。低机位贴近湿地面，右侧门框形成前景遮挡，"
            "走廊墙线向远端红色出口灯收束；焦平面落在门缝冷白光与中段水汽，远端背景轻雾化。"
            "顶灯只照亮中段，暗部保留黑位，亮部不过曝；冷白灯与远端暗红灯做低饱和色彩分离。"
            "空气里有逆光雨雾和细小尘粒，墙皮起皮、瓷砖水渍、地面积水反光断续不规则，落幅只保留门缝光和粗糙湿地反光。"
        )
        assert not cinematic_realism_prompt_issues(cinematic_prompt, require_live_action_style=True)
        cinematic_metadata = {"cinematic_image_contract": {
            "composition_anchor": "低机位贴近湿地面，右侧门框形成前景遮挡，走廊墙线向远端收束",
            "lens_depth": "焦平面落在门缝冷白光与中段水汽，远端背景轻雾化",
            "exposure_contrast": "顶灯只照亮中段，暗部保留黑位，亮部不过曝",
            "color_separation": "冷白灯与远端暗红灯做低饱和色彩分离",
            "atmosphere_layer": "逆光雨雾和细小尘粒形成空气层",
            "material_detail": "墙皮起皮、瓷砖水渍、地面积水断续反光",
            "imperfection_map": "水渍、反光和雨痕都不均匀，表面有旧痕和粗糙颗粒",
            "realism_risk": "避免镜面水面、塑料墙、均匀雨线、过曝灯管和虚拟摄影棚感",
            "signature_frame": "门缝冷白光压在粗糙湿地反光上，远端红灯被水汽压暗",
        }}
        assert not cinematic_image_contract_issues(cinematic_metadata, cinematic_prompt)
        bad_cinematic_metadata = json.loads(json.dumps(cinematic_metadata, ensure_ascii=False))
        bad_cinematic_metadata["cinematic_image_contract"]["imperfection_map"] = ""
        assert cinematic_image_contract_issues(bad_cinematic_metadata, cinematic_prompt)
        video_texture_metadata = {"video_texture_contract": {
            "look_profile": "全片统一为写实影视级PBR物理渲染和低饱和胶片基调",
            "exposure_policy": "所有镜头保留暗部黑位，灯罩亮部不过曝，高光只落在受光面边缘",
            "material_motion_policy": "墙面、地面、金属和积水在运动中保持粗糙材质、断续反光和不均匀高光",
            "atmosphere_motion_policy": "雨雾尘和水汽只做缓慢贴地扩散或断续飘动，不形成均匀粒子层",
            "camera_stability_policy": "镜头以固定或低幅缓慢运动为主，不摇晃、不快速推拉、不临时变焦",
            "continuity_carryover": "跨镜保持同一光色、黑位、湿度和材质颗粒，不重置空间质感不跳变",
            "risk_controls": "避免镜面水面、塑料墙、均匀雨线、过曝灯管、贴图跳变和廉价CG感",
        }}
        video_texture_prompt = (
            "生成规格：16:9画幅，高端3D CG写实影视级PBR物理渲染。\n\n"
            "主体与空间锁定：雨夜旧走廊，右侧门框前景遮挡，左墙墙皮起皮，地面积水断续反光。\n\n"
            "主镜头连续规则：镜头固定，低幅缓慢推近，保持同一光色和黑位不跳变。\n\n"
            "子镜头组：0-2秒雨雾贴地扩散，积水涟漪让高光断续移动；2-4秒门缝冷光轻微增强，墙面粗糙划痕保持稳定。\n\n"
            "光照、声音与稳定约束：顶灯亮部不过曝，暗部保留黑位，雨雾颗粒不均匀，水面不做完整镜面。"
        )
        assert not video_texture_contract_issues(video_texture_metadata, video_texture_prompt)
        bad_video_texture_metadata = json.loads(json.dumps(video_texture_metadata, ensure_ascii=False))
        bad_video_texture_metadata["video_texture_contract"]["camera_stability_policy"] = ""
        assert video_texture_contract_issues(bad_video_texture_metadata, video_texture_prompt)
        direct_task = {
            "full_prompt": grounded_visual_prompt.replace(
                "主体与空间锁定：空间",
                "主体与空间锁定：甲在画面左侧，乙在画面右侧，手机起幅在桌右前角",
            ).replace(
                "主镜头连续规则：规则",
                "主镜头连续规则：锁定甲左乙右；手机始终只在桌右前角，未被触碰，落幅位置不变",
            ),
            "negative_prompt": "肢体畸形，手指错误，屏幕文字漂移，光影突变",
            "qa_metadata": dict(
                formal_metadata,
                video_texture_contract=video_texture_metadata["video_texture_contract"],
                continuity_contract={
                    "start_anchor": "手机起幅在桌右前角",
                    "prop_state": "手机仍在桌右前角，未被触碰",
                    "end_anchor": "手机仍在桌右前角",
                    "next_carryover": "手机仍在桌右前角",
                    "state_change": True,
                },
                reroll_control={
                    "risk_level": "high",
                    "manual_first_pass_check": True,
                    "mitigation_steps": ["锁定甲左乙右", "锁定手机只在桌右前角"],
                },
                editorial_mode="continuous_take",
            ),
        }
        direct_copy = _build_direct_copy_prompt(direct_task, {"canvas": "16:9", "visual_style": "动态漫"})
        assert direct_copy.startswith("16:9画幅，动态漫，冷白顶灯下的长桌空间")
        assert len(direct_copy) <= 700
        assert not direct_copy_prompt_issues(direct_copy, max_chars=700, require_visual_texture=True)
        assert "视频质感约束" in direct_copy
        assert _high_risk_direct_blocks_enabled(direct_task)
        assert "手机仍在桌右前角" in _build_direct_constraint_block(direct_task)
        parking_lot_direct_copy = (
            "9:16画幅，写实电影级动态漫短剧，地下停车场入口，冷青灰工业影调。"
            "主体为保安；双人中景，保安手掌与顾辰肩前空隙实焦，前景承重柱边缘轻度虚化。"
            "顶部冷白灯压在承重柱与湿地面上，湿地面低位反射托住手部和关键道具，黑位保留，高光收住。"
        )
        assert not direct_copy_prompt_issues(parking_lot_direct_copy, max_chars=700, require_visual_texture=True)
        meeting_room_direct_copy = (
            "9:16画幅，写实电影级动态漫短剧，冷白会议室长桌，冷白浅灰影调。"
            "主体为顾辰；中近景，顾辰上半身和文件夹边缘实焦，桌面中央手机在前景轻度虚化。"
            "顶部冷白面光自上方略偏前方垂直压下，桌面玻璃反光托住手机和白纸文件，右后方门口漏光保持外部威胁，黑位收住。"
        )
        assert not direct_copy_prompt_issues(meeting_room_direct_copy, max_chars=700, require_visual_texture=True)
        jump_transfer_prompt = canonical.replace(
            "画面",
            "角色A把银行卡递给角色B，落幅角色B拿着银行卡"
        )
        assert physical_transition_chain_issues(transfer_metadata, jump_transfer_prompt)
        bad_transfer = json.loads(json.dumps(transfer_metadata, ensure_ascii=False))
        bad_transfer["continuity_contract"]["state_transitions"][0].pop("intermediate_state")
        assert any("intermediate_state" in issue for issue in continuity_contract_issues(bad_transfer, transfer_prompt, ["角色A"]))
        assert any("intermediate_state" in issue for issue in physical_transition_chain_issues(bad_transfer, transfer_prompt))
        phone_previous = {"end_state": "手机持续亮屏显示来电", "continuity_contract": {"next_carryover": "手机亮屏的来电状态"}}
        phone_replay = "手机屏幕亮起或震动，显示来电界面"
        assert state_transition_replay_issues(phone_previous, "手机屏幕亮起显示来电", {}, phone_replay)
        assert not state_transition_replay_issues(phone_previous, "手机屏幕亮起显示来电", {}, "手机已亮屏，沈星雨直接抬手贴耳接听")
        assert shot_group_handoff_issues({"editorial_mode": "shot_group", "camera_beat_map": [{"focus_owner": "角色A"}, {"focus_owner": "角色B"}, {"focus_owner": "角色A"}]})
        insert_prompt = canonical.replace(
            "【镜头1｜0.0-1.0秒】画面",
            "【镜头1｜0.0-1.0秒】角色A画面左侧面向角色B，前景桌沿作为场景锚点，落幅手停在桌边"
            "【镜头2｜1.0-4.0秒】插入功能：信息补充，切到文件道具特写，文件角露出新线索，承接插入前桌面光源与画面左侧关系，随后切回角色A手停在桌边",
        )
        insert_metadata = {
            "editorial_mode": "shot_group",
            "reroll_control": {
                "risk_level": "medium",
                "risk_reason": "文件特写插入存在切入连续性风险",
                "mitigation_steps": [
                    "锁定插入前落幅：角色A手停在桌边",
                    "锁定插入主体：文件角的新线索",
                    "插入后切回到主线人物角色A手停在桌边",
                    "用环境声作为声音桥承接切入前后",
                ],
            },
        }
        assert not insert_shot_issues(insert_metadata, insert_prompt, 4, ["角色A"])
        decorative_insert = canonical.replace(
            "画面",
            "插入功能：节奏切割，切入回忆插入镜，装饰性空镜只为丰富画面",
        )
        assert any("时空意象插入" in issue or "装饰性" in issue for issue in insert_shot_issues(
            {"editorial_mode": "shot_group", "reroll_control": {"risk_reason": "插入风险", "mitigation_steps": []}},
            decorative_insert,
            4,
            ["角色A"],
        ))
        risky = {"full_prompt": canonical.replace("空间", "甲画左、乙画右，酒店入口" ).replace("画面", "甲走向乙并递出手机"), "qa_metadata": {"dialogue_events": [{"speaker": "甲"}, {"speaker": "乙"}]}}
        assert build_spatial_storyboard_reference(risky, {"scene": "大堂"}) is not None
        dramatic_keyframe_task = {
            "full_prompt": spatial_prop_prompt.replace("单一剧情问题围绕角色A是否说出真相", "单一剧情问题围绕角色A是否揭示药瓶真相，药瓶形成压迫"),
            "qa_metadata": {
                "dramatic_goal": "角色A是否揭示药瓶真相",
                "dialogue_events": [{"speaker": "角色A", "kind": "台词", "text": "你知道这是什么。"}],
                "dramatic_design": {"narrative_weight": "high", "information_gain": "药瓶真相逼近"},
                "pressure_release_design": {"pressure_source": "药瓶真相", "pressure_object": "桌面药瓶", "release_trigger": "角色A看向药瓶"},
                "continuity_contract": {"end_anchor": "药瓶仍在桌面右前角，角色A视线压向角色B"},
            },
        }
        keyframe = build_current_shot_keyframe_reference(dramatic_keyframe_task, {"scene": "审讯室"}, "16:9", "动态漫")
        assert keyframe and "当前镜头剧情关键帧" in keyframe["keyframe_prompt"]
        assert "不分格" in keyframe["keyframe_prompt"] and "九宫格" in keyframe["negative_prompt"]
        _write(os.path.join(run_dir, ".cache", "composer", "prompt_package.json"), {"shots": []})
        audit_result, _audit_path = emotion_camera_audit(run_dir)
        assert isinstance(audit_result.get("pass"), bool) and isinstance(audit_result.get("shots"), list)
        package_path = os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json")
        os.makedirs(os.path.join(run_dir, ".cache", "validate"), exist_ok=True)
        _write(os.path.join(run_dir, ".cache", "validate", "result.json"), {
            "pass": True, "package_sha256": "stale",
        })
        assert not _local_phase_valid(run_dir, "validate")
        _write(os.path.join(run_dir, ".cache", "validate", "result.json"), {
            "pass": True, "package_sha256": _sha256(package_path),
        })
        assert _local_phase_valid(run_dir, "validate")
        export_md = os.path.join(run_dir, "delivery.md")
        with open(export_md, "w", encoding="utf-8") as handle:
            handle.write("ok")
        os.makedirs(os.path.join(run_dir, ".cache", "export"), exist_ok=True)
        _write(os.path.join(run_dir, ".cache", "export", "result.json"), {
            "pass": True, "markdown_path": export_md, "markdown_sha256": _sha256(export_md),
            "package_sha256": _sha256(package_path),
        })
        state = load_state(run_dir)
        state["current_phase"] = "export"
        state["phases"]["export"]["status"] = "done"
        save_state(run_dir, state)
        assert pipeline_runner_run(run_dir)["action"] == "completed"
        performance_path, performance = performance_report(run_dir)
        assert os.path.exists(performance_path)
        assert "dispatch_summary" in performance
        assert performance["elapsed_seconds_basis"] == "slo_active_phase_seconds"
        assert "local_compute_seconds" in performance["time_breakdown"]
        assert "local_pause_seconds" in performance["time_breakdown"]
        assert "worker_wait_wall_seconds" in performance["time_breakdown"]
        assert "manifest_superseded_packet_count" in performance["dispatch_summary"]
        assert "stale_or_superseded_packet_count" in performance["dispatch_summary"]
        with tempfile.TemporaryDirectory() as paused_run:
            os.makedirs(os.path.join(paused_run, ".cache", "orchestrator"), exist_ok=True)
            _write(os.path.join(paused_run, ".cache", "orchestrator", "shot_plan.json"), {
                "shots": [{"shot_id": "S%02d" % i} for i in range(1, 51)]
            })
            _write(os.path.join(paused_run, ".cache", "pipeline_state.json"), {
                "pipeline_started_at": 1000.0,
                "current_phase": "validate",
                "phase_order": PHASE_ORDER,
                "phases": {
                    "user_confirm": {"status": "done", "completed_at": 1000.0},
                    "orchestrator": {"status": "done", "completed_at": 1001.0, "elapsed_seconds": 0.5},
                    "scene_lock": {"status": "done", "completed_at": 1101.0, "elapsed_seconds": 100.0},
                    "master_production": {"status": "done", "completed_at": 1301.0, "elapsed_seconds": 200.0},
                    "editor_pass1": {"status": "done", "completed_at": 1426.0, "elapsed_seconds": 125.0},
                    "editor_pass2": {"status": "done", "completed_at": 1476.0, "elapsed_seconds": 50.0},
                    "validate": {"status": "done", "completed_at": 1546.0, "elapsed_seconds": 70.0},
                    "export": {"status": "pending"},
                },
            })
            _paused_path, paused_performance = performance_report(paused_run)
            assert paused_performance["elapsed_seconds"] == 470.5
            assert paused_performance["time_breakdown"]["wall_clock_seconds"] == 546.0
            assert paused_performance["time_breakdown"]["local_pause_seconds"] == 75.0
            assert paused_performance["within_target"] is True
        benchmark_root = os.path.join(run_dir, "synthetic_benchmark")
        benchmark_runs = create_benchmark_fixtures(benchmark_root)
        benchmark = evaluate_benchmark(benchmark_runs)
        assert benchmark["pass"] is True
        assert benchmark["real_slo_pass"] is False
        assert benchmark["synthetic_fixture_count"] == 6
        assert benchmark["normal_scenarios"] == ["action", "dialogue", "mixed"]
        assert benchmark["fault_injection_scenarios"] == ["action", "dialogue", "mixed"]
        assert benchmark["missing_matrix_cells"] == []
        assert benchmark["coverage_matrix"]["dialogue"]["0"]["count"] == 1
        assert benchmark["coverage_matrix"]["mixed"]["0.1"]["count"] == 1
        assert benchmark["dispatch_p95"] is not None
        assert benchmark["retry_p95"] is not None
        gate_result, _gate_path = pre_editor_gate(run_dir)
        assert "validator_sha256" in gate_result
        merged_fixture = os.path.join(run_dir, "merged_contract_version.prompt_package.json")
        merged_report = os.path.join(run_dir, "merged_contract_version.report.json")
        _write(merged_fixture, {"contract_version": PROMPT_CONTRACT_VERSION, "shots": []})
        # An empty package still fails downstream completeness, but must not
        # fail solely because merge_agent_outputs adds the version envelope.
        assert validate_composer_output(merged_fixture, report_path=merged_report) == 1
        assert not any("batch顶层" in issue for issue in _read(merged_report)["issues"])
        with tempfile.TemporaryDirectory() as aspect_run:
            _write(os.path.join(aspect_run, "project_config.json"), {"canvas": "9:16"})
            aspect_fixture = os.path.join(aspect_run, "bad_aspect.prompt_package.json")
            aspect_report = os.path.join(aspect_run, "bad_aspect.report.json")
            _write(aspect_fixture, {"shots": [{
                "shot_id": "A1",
                "subshot_id": "A1",
                "source_subshot_ids": ["A1"],
                "duration": 4,
                "full_prompt": "生成规格：16:9画幅，横屏短剧镜头。\n\n主体与空间锁定：同侧轴线保持。\n\n主镜头连续规则：固定。\n\n子镜头组：【镜头1｜0.0-4.0秒】角色站定。\n\n光照、声音与稳定约束：顶灯照亮手背。",
                "negative_prompt": "PLACEHOLDER_COMMON_NEGATIVE_PROMPT",
                "qa_metadata": {
                    "scene_tone_palette": {"visual_scene_prefix": "16:9横屏写实短剧"},
                    "source_constraint_basemap": {"single_shot_risk": "同侧轴线保持"},
                    "performance_causality": {"hold_strategy": "轴线稳定"},
                    "reroll_control": {"camera_anchor": "不越轴"},
                },
                "generation_control": {},
            }]})
            assert validate_composer_output(aspect_fixture, run_dir=aspect_run, report_path=aspect_report) == 1
            aspect_issues = "\n".join(_read(aspect_report)["issues"])
            assert "项目画幅9:16" in aspect_issues
            assert "比例：16:9" in aspect_issues
            assert "不得在full_prompt写横屏" in aspect_issues
            assert "工程/审核文本泄漏：同侧轴线" in aspect_issues
            assert "visual_scene_prefix出现冲突画幅：16:9" in aspect_issues
            assert "source_constraint_basemap.single_shot_risk含不可投喂/交付的镜头术语" in aspect_issues
        light_items = [_master_item("E%02d" % index, "环境", non_character=True) for index in range(1, 11)]
        light_risk = dispatch_risk(light_items[0])
        assert light_risk["tier"] == "light" and light_risk["batch_capacity"] == 10
        assert [len(batch) for batch in _dynamic_master_chunks(light_items)] == [10]
        realistic_dialogue_items = [_realistic_dialogue_master_item(index) for index in range(1, 11)]
        assert max(context_size(_compact_composer_item(item)) for item in realistic_dialogue_items) < 1000
        assert [len(batch) for batch in _dynamic_master_chunks(realistic_dialogue_items)] == [10]
        with tempfile.TemporaryDirectory() as redispatch_dir:
            os.makedirs(os.path.join(redispatch_dir, ".cache", "orchestrator"))
            shot_plan = {"shots": [
                {
                    "shot_id": "RD%02d" % index,
                    "scene": "场景A",
                    "subshots": [dict(_realistic_dialogue_master_item(index)["source_subshots"][0])],
                }
                for index in range(1, 13)
            ]}
            _write(os.path.join(redispatch_dir, ".cache", "orchestrator", "shot_plan.json"), shot_plan)
            redispatch_packets = prepare_dispatch_packets(redispatch_dir, "master_production")
            assert len(redispatch_packets) == 2
            recovery = redispatch_incomplete_master(redispatch_dir, "unit-test recovery batching")
            assert len(recovery["missing_shot_ids"]) == 12
            recovery_sizes = [len(_read(path)["items"]) for path in recovery["new_packets"]]
            assert recovery_sizes == [10, 2], recovery_sizes
        high_items = [_master_item("F%02d" % index, "两人打斗后互相格挡") for index in range(1, 6)]
        high_risk = dispatch_risk(high_items[0])
        assert high_risk["tier"] == "high" and high_risk["batch_capacity"] == 2
        assert [len(batch) for batch in _dynamic_master_chunks(high_items)] == [2, 2, 1]
        low_hint = _composer_execution_hints({"subshot_id": "L1", "visible_characters": ["甲"], "duration": 2, "editorial_mode": "continuous_take"})
        assert not low_hint["risk_gated_contracts"]["ai_model_readiness_score"]
        assert not low_hint["risk_gated_contracts"]["pressure_release_design"]
        light_profile = validation_profile({
            "subshot_id": "ENV-01", "shot_type": "environment", "non_character_confirmed": True,
            "visual_intent": "雨夜空走廊", "base_action": "", "characters": [],
        })
        assert light_profile["profile"] == "environment"
        assert not any(light_profile[key] for key in (
            "performance_causality", "performance_contract", "story_punch_contract",
            "ai_model_readiness_score", "pressure_release_design", "listener_reaction_plan",
            "character_scene_objective_contract", "relationship_emotion_arc",
        ))
        assert light_profile["sequence_directing_plan"] and light_profile["cut_decision_contract"]
        assert light_profile["prompt_information_budget"]
        assert light_profile["sound_directing_plan"]
        dialogue_profile = validation_profile({
            "subshot_id": "D-01", "characters": ["甲", "乙"], "visible_characters": ["甲", "乙"],
            "dialogue_refs": ["D1"], "dialogue_events": [{"speaker": "甲", "text": "别再骗我。"}],
            "base_action": "甲盯住乙说话", "duration": 4,
        })
        assert dialogue_profile["performance_contract"] and dialogue_profile["story_punch_contract"]
        assert dialogue_profile["listener_reaction_plan"]
        assert dialogue_profile["character_scene_objective_contract"]
        assert dialogue_profile["relationship_emotion_arc"]
        # 清晰人物表演镜必须有肤色保护合同，纯环境/物件镜不增加该负担。
        assert dialogue_profile["skin_tone_protection_contract"] is True
        peak_profile = validation_profile(
            {"subshot_id": "P-01", "characters": ["甲"], "visible_characters": ["甲"], "base_action": "甲伸手拿起药瓶"},
            {"emotion_driver": {"tension_intent": "peak"}}, ["甲"],
        )
        assert peak_profile["pressure_release_design"]
        high_profile = validation_profile({
            "subshot_id": "H-01", "characters": ["甲", "乙"], "visible_characters": ["甲", "乙"],
            "base_action": "甲将手机递给乙", "duration": 5,
        })
        assert high_profile["ai_model_readiness_score"]
        phone_game = {
            "subshot_id": "PHONE-01", "characters": ["男孩"], "visible_characters": ["男孩"],
            "base_action": "男孩双手横握手机玩游戏", "duration": 4,
        }
        assert functional_surface_risk(phone_game)
        assert validation_profile(phone_game)["prop_functional_surface_contract"] is True
        assert not functional_surface_risk({"base_action": "男孩把手机递给父亲"})
        assert not functional_surface_risk({"base_action": "手机静置在桌面右侧"})
        assert validation_profile({
            "subshot_id": "ENV-PHONE", "shot_type": "object", "non_character_confirmed": True,
            "visual_intent": "桌面上的手机", "base_action": "手机静置在桌面右侧", "characters": [],
        })["prop_functional_surface_contract"] is False
        assert validation_profile({
            "subshot_id": "ENV-SKIN", "shot_type": "object", "non_character_confirmed": True,
            "visual_intent": "空置窗边", "base_action": "窗帘轻晃", "characters": [],
        })["skin_tone_protection_contract"] is False
        high_hint = _composer_execution_hints({"subshot_id": "H1", "visible_characters": ["甲", "乙"], "duration": 5, "editorial_mode": "shot_group", "emotion_driver": {"tension_intent": "rising"}})
        assert high_hint["risk_gated_contracts"]["ai_model_readiness_score"]
        assert high_hint["risk_gated_contracts"]["pressure_release_design"]
        scaffold_packets = prepare_dispatch_packets(run_dir, "master_production", 1, ["S1"])
        scaffold_packet = _read(scaffold_packets[0])
        scaffold = _read(scaffold_packet["composer_scaffold_path"])
        scaffold_metadata = scaffold["shots"][0]["qa_metadata"]
        assert "source_constraint_basemap" in scaffold_metadata
        assert "emotion_micro_chain" in scaffold_metadata["source_constraint_basemap"]
        assert "performance_baseline_lock" in scaffold_metadata["source_constraint_basemap"]
        assert "dialogue_performance_kernel" in scaffold_metadata["source_constraint_basemap"]
        assert "emotion_residue_contract" in scaffold_metadata["source_constraint_basemap"]
        assert "premium_director_polish" in scaffold_metadata["source_constraint_basemap"]
        assert scaffold_metadata["source_constraint_basemap"]["creative_profile"] == "balanced"
        assert "viewpoint_motion_lock" in scaffold_metadata["source_constraint_basemap"]
        assert "scene_tone_palette" in scaffold_metadata
        assert "landscape_identity" in scaffold_metadata["scene_tone_palette"]
        assert "environment_story_arc" in scaffold_metadata["scene_tone_palette"]
        assert "sequence_directing_plan" in scaffold_metadata
        assert "cut_decision_contract" in scaffold_metadata
        assert "prompt_information_budget" in scaffold_metadata
        assert "sound_directing_plan" in scaffold_metadata
        light_scaffold_path = _write_composer_scaffold(
            run_dir,
            [light_items[0]],
            os.path.join(run_dir, ".cache", "dispatch"),
            "light_contract_test",
            lock_path,
        )
        light_scaffold_metadata = _read(light_scaffold_path)["shots"][0]["qa_metadata"]
        assert all(field not in light_scaffold_metadata for field in RISK_GATED_QA_FIELDS)
        high_scaffold_path = _write_composer_scaffold(
            run_dir,
            [high_items[0]],
            os.path.join(run_dir, ".cache", "dispatch"),
            "high_contract_test",
            lock_path,
        )
        high_scaffold_metadata = _read(high_scaffold_path)["shots"][0]["qa_metadata"]
        high_scaffold_profile = validation_profile(high_items[0])
        for field, profile_key in RISK_GATED_QA_FIELDS.items():
            assert (field in high_scaffold_metadata) is bool(high_scaffold_profile.get(profile_key, False))
        phone_scaffold_path = _write_composer_scaffold(
            run_dir,
            [_master_item("PHONE01", "男孩玩手机游戏")],
            os.path.join(run_dir, ".cache", "dispatch"),
            "phone_surface_test",
            lock_path,
        )
        phone_scaffold = _read(phone_scaffold_path)
        assert "prop_functional_surface_contract" in phone_scaffold["shots"][0]["qa_metadata"]
        assert "skin_tone_protection_contract" in phone_scaffold["shots"][0]["qa_metadata"]
        assert check_rule_consistency(os.path.dirname(os.path.dirname(__file__)))["pass"] is True
        assert "screen_text_policy" in scaffold_metadata
        assert "tension_curve_role" in scaffold_metadata
        dialogue_items = [_master_item("D%02d" % index, "角色A说了一段很长的解释台词，角色B保持倾听") for index in range(1, 7)]
        for item in dialogue_items:
            item["source_subshots"][0]["dialogue_refs"] = ["DIALOGUE"]
            item["source_subshots"][0]["dialogue_events"] = [{"text": "这是一段超过三十二个字的对白，用来证明单纯长对白不会被拆到复杂动作级别。"}]
            item["source_subshots"][0]["duration"] = 9
        dialogue_risk = dispatch_risk(dialogue_items[0])
        assert dialogue_risk["tier"] == "high" and dialogue_risk["batch_capacity"] == 3
        assert [len(batch) for batch in _dynamic_master_chunks(dialogue_items)] == [3, 3]
        large_items = [_master_item("L%02d" % index, "动作" + "x" * 5000) for index in range(1, 3)]
        assert [len(batch) for batch in _dynamic_master_chunks(large_items)] == [1, 1]
        editor_windows = [dict(windows[0], review_tier="light") for _ in range(10)]
        light_editor_batches = _editor_review_chunks(editor_windows)
        assert sum(len(batch) for batch in light_editor_batches) == 10
        assert all(1 <= len(batch) <= 10 for batch in light_editor_batches)
        oversized_windows = [dict(windows[0], current=dict(windows[0]["current"], full_prompt="x" * 5000)) for _ in range(3)]
        assert [len(batch) for batch in _editor_review_chunks(oversized_windows)] == [1, 1, 1]
        event_transition = _master_item("T01", "梦境崩塌后，角色A在现实中苏醒")
        candidate = temporal_transition_candidate(event_transition)
        assert candidate["eligible"] is True and candidate["kind"] == "story_event_transition"
        assert dispatch_risk(event_transition)["tier"] == "high"
        memory = _master_item("T02", "他想起当年二人在雨中告白")
        memory_candidate = temporal_transition_candidate(memory)
        assert memory_candidate["eligible"] is True and memory_candidate["kind"] == "memory_flashback"
        transition_prompt = canonical.replace("画面", "梦境画面的裂纹收束成一次暗切，钟声尾音作为声音桥接，角色A闭口在现实中睁眼")
        transition_metadata = {"reroll_control": {"risk_level": "high", "manual_first_pass_check": True}, "temporal_transition_contract": {
            "enabled": True, "kind": "story_event_transition", "source_trigger": candidate["source_trigger"],
            "decision_reason": "梦境崩塌需要体现意识回归", "time_range": "0.8-1.6秒", "effect": "裂纹收束暗切", "effect_source_basis": "源文的梦境崩塌", "from_state": "梦境中的角色A", "to_state": "现实中苏醒的角色A", "audio_bridge": "钟声尾音作为声音桥接", "lip_sync": False, "prompt_anchor": "梦境画面的裂纹收束成一次暗切", "fallback": "split_with_matched_cut",
        }}
        assert not temporal_transition_contract_issues(transition_metadata, transition_prompt, 4, {"kind": candidate["kind"], "source_trigger": candidate["source_trigger"]})
        transition_metadata["temporal_transition_contract"]["effect"] = "裂纹收束暗切+烟雾"
        assert any("唯一视觉效果" in issue for issue in temporal_transition_contract_issues(transition_metadata, transition_prompt, 4, {"kind": candidate["kind"], "source_trigger": candidate["source_trigger"]}))
        assert GATES["editor_pass2"]["output"] == [".cache/review/llm_gate_result.json"]
        editor_batch = os.path.join(run_dir, "editor_batch.json")
        _write(editor_batch, {"windows": [{"window_id": "W001", "pass": False,
                                             "blocking": ["连续性断裂"], "repair_targets": ["S1"]}]})
        editor_output = os.path.join(run_dir, ".cache", "review", "llm_gate_result.json")
        _materialize("editor_pass2", editor_output, [editor_batch])
        review = _read(editor_output)
        assert review["pass"] is False and review["blocking"] == ["连续性断裂"] and review["repair_targets"] == ["S1"]
        assert _review_target_shot_ids(review) == ["S1"]
        dict_target_review = {"repair_targets": [{"shot_id": "S2", "field": "full_prompt"}, {"subshot_id": "S1"}]}
        assert _review_target_shot_ids(dict_target_review) == ["S1", "S2"]
        prose_target_review = {"repair_targets": [
            "S1-03：将手机起幅改为已亮屏，删除再次亮屏触发。",
            "在 S1-09 起幅补足从 S1-08 落幅继承的视线。",
        ]}
        assert _review_target_shot_ids(prose_target_review) == ["S1-03", "S1-09"]
        blocking_target_review = {"windows": [
            {"window_id": "W003", "pass": False, "blocking": ["S1-03仍有再次亮屏触发"], "repair_targets": ["删除短促电子提示音"]},
            {"window_id": "W009", "pass": False, "blocking": ["S1-09服装锚点冲突"], "repair_targets": ["current.review_contracts.reroll_control.identity_anchor"]},
        ]}
        assert _review_target_shot_ids(blocking_target_review) == ["S1-03", "S1-09"]
    return "current pipeline contract regression passed"


def _write(path, value):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False)


def _read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _master_item(shot_id, action, non_character=False):
    source = {
        "shot_id": shot_id, "subshot_id": shot_id + "-01", "base_action": action,
        "duration": 4, "shot_type": "环境" if non_character else "动作",
        "visual_intent": "门外的空间锚点" if non_character else "人物动作",
        "non_character_confirmed": non_character,
        "characters": [] if non_character else ["角色A", "角色B"],
    }
    return {
        "shot_id": shot_id,
        "subshot_id": shot_id,
        "base_action": action,
        "duration": 4,
        "characters": [] if non_character else ["角色A", "角色B"],
        "visible_characters": [] if non_character else ["角色A", "角色B"],
        "source_subshots": [source],
    }


def _realistic_dialogue_master_item(index):
    shot_id = "RD%02d" % index
    source = {
        "shot_id": shot_id,
        "subshot_id": shot_id + "-01",
        "scene": "场景A",
        "duration": 4.6,
        "base_action": "角色A：别再往前走，文件已经说明问题。",
        "characters": ["角色A"],
        "visible_characters": ["角色A"],
        "dialogue_refs": ["D%02d" % index],
        "dialogue_events": [{
            "ref": "D%02d" % index,
            "kind": "台词",
            "speaker": "角色A",
            "text": "别再往前走，文件已经说明问题。",
            "source_tone": "压住情绪",
        }],
        "dialogue_raw_text": "别再往前走，文件已经说明问题。",
        "editorial_mode": "continuous_take",
        "dramatic_design": {
            "shot_function": "dialogue",
            "coverage_role": "dialogue_performance",
            "narrative_weight": "medium",
            "information_gain": "角色A阻止对方继续靠近",
            "reaction_ownership": "",
            "narrative_beat_id": "B%04d" % index,
            "dramatic_beat_ids": ["B%04d" % index],
            "visual_punctuation": [],
        },
        "duration_design": {
            "duration_strategy": "pack_toward_limit",
            "justified_content_duration": 4.6,
            "utilization_ratio": 0.92,
            "duration_rationale": "continuous_dialogue",
            "dramatic_beats": ["B%04d" % index],
        },
        "quality_contract": {
            "profile": "dialogue",
            "required_analysis": ["scene_lock", "master_production"],
            "required_evidence": [
                "composition_readability",
                "source_light_continuity",
                "camera_execution",
                "end_state_carryover",
                "exact_dialogue_boundary",
                "delivery_and_lip_sync",
                "axis_continuity",
            ],
        },
        "spatial_map": {},
        "props": [],
    }
    item = dict(source)
    item["subshot_id"] = shot_id
    item["source_subshot_ids"] = [source["subshot_id"]]
    item["source_subshots"] = [dict(source)]
    item["master_task"] = True
    return item


if __name__ == "__main__":
    print(run())
