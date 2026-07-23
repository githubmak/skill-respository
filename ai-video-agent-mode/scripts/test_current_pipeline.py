"""Deterministic contract regression for the current pipeline's file boundaries."""
import json
import os
import tempfile
import hashlib

from context_budget import check, editor_items_fit
from editor_scene_windows import build
from modec_v4 import coverage_role_issues, dialogue_event_issues, expectation_anchor_issues, jimeng_feed_prompt, listener_reaction_issues, shot_group_handoff_issues, state_transition_replay_issues, temporal_transition_contract_issues
from pipeline_runtime import atomic_json, cache_artifact, record_issues
from adapt_nine_panel_storyboard import adapt
from emotion_camera_audit import audit as emotion_camera_audit
from spatial_storyboard import build_spatial_storyboard_reference
from validate_scene_locks import validate
from shot_semantics import dispatch_risk, temporal_transition_candidate
from dispatch_cache import _dynamic_master_chunks, _editor_review_chunks, _retry_examples
from contract_registry import QA_REQUIRED_FIELDS, SHOT_REQUIRED_FIELDS
from dispatch_receipts import heartbeat as receipt_heartbeat, issue as issue_receipt, load_and_verify as verify_dispatch_receipt
from pipeline_state import load_state, record_heartbeat as state_heartbeat, set_agent_id
from record_batch_provenance import record as record_provenance, verify as verify_provenance
from merge_agent_outputs import merge_agent_outputs
from pipeline_templates import GATES
from pipeline_runner import _local_phase_valid, _materialize
from check_export import INTERNAL_TITLE_LEAK
from preflight_check import PLACEHOLDER_CHARACTER_NAMES
from validate_durations import _estimate_action_seconds
from build_shotplan import _estimate_dialogue_seconds as split_dialogue_seconds
from validate_durations import _estimate_dialogue_seconds as validated_dialogue_seconds


def run():
    with tempfile.TemporaryDirectory() as run_dir:
        os.makedirs(os.path.join(run_dir, ".cache", "analysis"))
        os.makedirs(os.path.join(run_dir, ".cache", "composer"))
        os.makedirs(os.path.join(run_dir, ".cache", "orchestrator"))
        locks = {"scenes": [{"scene": "场景A", "space_anchor": "门与长桌", "screen_positions": "甲左乙右",
                               "wardrobe_lock": "沿用确认设定", "prop_state": "文件夹在桌中央",
                               "light_source": "顶灯", "light_direction": "上方", "light_temperature": "4500K", "audio_policy": "原生音频关闭"}]}
        lock_path = os.path.join(run_dir, ".cache", "analysis", "scene_locks.json")
        _write(lock_path, locks)
        assert not validate(lock_path)
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
        windows = build(run_dir)
        assert len(windows) == 2 and windows[0]["current"]["shot_id"] == "S1" and windows[1]["previous"]["shot_id"] == "S1"
        assert windows[0]["capsule_version"] == "editor-review-v1"
        assert "full_prompt" in windows[0]["current"]
        assert "full_prompt" not in windows[0]["next"]
        assert editor_items_fit(windows)
        assert check({"items": [{"shot_id": "S1"}]}) > 0
        assert {"shot_id", "subshot_id", "duration", "full_prompt", "negative_prompt", "qa_metadata", "generation_control"} == SHOT_REQUIRED_FIELDS
        assert "temporal_transition_contract" in QA_REQUIRED_FIELDS
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
        atomic_json(os.path.join(run_dir, ".cache", "control.json"), {"ok": True})
        assert _read(os.path.join(run_dir, ".cache", "control.json"))["ok"] is True
        cache_artifact(run_dir, "test", {"value": 1})
        record_issues(run_dir, "first", ["a"])
        record_issues(run_dir, "second", ["b"])
        assert set(_read(os.path.join(run_dir, ".cache", "issues.json"))) == {"first", "second"}
        receipt_packet = {
            "contract_version": "jimeng-t2v-v1", "run_dir": run_dir, "phase": "master_production",
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
        batch_path = os.path.join(run_dir, "scene_worker.json")
        gate_packet = {
            "contract_version": "jimeng-t2v-v1", "run_dir": run_dir, "phase": "scene_lock",
            "dispatch_id": "gate-test", "created_at": 1, "_batch_output_path": batch_path,
        }
        gate_packet_path = os.path.join(run_dir, "gate_packet.json")
        _write(gate_packet_path, gate_packet)
        issue_receipt(gate_packet_path, gate_packet, "agent-gate-test")
        set_agent_id(run_dir, "scene_lock", "agent-gate-test", dispatch_id="gate-test")
        _write(batch_path, locks)
        state_heartbeat(run_dir, "scene_lock", "agent-gate-test", "gate-test")
        receipt_heartbeat(gate_packet_path, gate_packet, "agent-gate-test")
        record_provenance(gate_packet_path)
        assert verify_provenance(batch_path)[0] is True
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
            "time_range": "0.0-2.0秒", "speaker_visibility": "offscreen", "facial_state": "N/A，画外旁白",
            "body_state": "N/A，画外旁白", "delivery": "低声、句末轻收", "breath_pause_plan": "句前0.2秒吸气；无中段气口；句末0.3秒收气", "lip_sync": False,
        }]}
        assert not dialogue_event_issues(dialogue_metadata, None, [], canonical, False, 2)
        dialogue_metadata["dialogue_events"][0]["breath_pause_plan"] = ""
        assert any("breath_pause_plan" in issue for issue in dialogue_event_issues(dialogue_metadata, None, [], canonical, False, 2))
        listener_prompt = canonical.replace("画面", "角色B视线停在角色A脸上，拇指在杯沿轻收一次，不起身、不转向抢画面；角色B口型闭合，手仍停在杯沿，视线留在角色A方向")
        listener_metadata = {"performance_priority": {"primary": "角色A", "supporting": ["角色B"], "background": []}, "dialogue_events": [{"kind": "台词", "speaker": "角色A", "speaker_visibility": "visible"}], "listener_reaction_plan": {"speaker": "角色A", "listener": "角色B", "trigger": "角色A说到关键事实", "time_range": "0.2-0.8秒", "visual_evidence": "角色B视线停在角色A脸上，拇指在杯沿轻收一次", "motion_limit": "不起身、不转向抢画面", "lip_sync": False, "end_residue": "角色B口型闭合，手仍停在杯沿，视线留在角色A方向"}}
        assert not listener_reaction_issues(listener_metadata, listener_prompt)
        phone_previous = {"end_state": "手机持续亮屏显示来电", "continuity_contract": {"next_carryover": "手机亮屏的来电状态"}}
        phone_replay = "手机屏幕亮起或震动，显示来电界面"
        assert state_transition_replay_issues(phone_previous, "手机屏幕亮起显示来电", {}, phone_replay)
        assert not state_transition_replay_issues(phone_previous, "手机屏幕亮起显示来电", {}, "手机已亮屏，沈星雨直接抬手贴耳接听")
        assert shot_group_handoff_issues({"editorial_mode": "shot_group", "camera_beat_map": [{"focus_owner": "角色A"}, {"focus_owner": "角色B"}, {"focus_owner": "角色A"}]})
        risky = {"full_prompt": canonical.replace("空间", "甲画左、乙画右，酒店入口" ).replace("画面", "甲走向乙并递出手机"), "qa_metadata": {"dialogue_events": [{"speaker": "甲"}, {"speaker": "乙"}]}}
        assert build_spatial_storyboard_reference(risky, {"scene": "大堂"}) is not None
        board = {"source_summary": "角色相遇", "panels": [_panel(index) for index in range(1, 10)]}
        board_path = os.path.join(run_dir, "nine.json")
        packages_path = os.path.join(run_dir, ".cache", "grid_storyboard", "packages.json")
        _write(board_path, board)
        assert len(adapt(board_path, packages_path)["packages"]) == 1
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
        light_items = [_master_item("E%02d" % index, "环境", non_character=True) for index in range(1, 11)]
        light_risk = dispatch_risk(light_items[0])
        assert light_risk["tier"] == "light" and light_risk["batch_capacity"] == 10
        assert [len(batch) for batch in _dynamic_master_chunks(light_items)] == [10]
        high_items = [_master_item("F%02d" % index, "两人打斗后互相格挡") for index in range(1, 6)]
        high_risk = dispatch_risk(high_items[0])
        assert high_risk["tier"] == "high" and high_risk["batch_capacity"] == 4
        assert [len(batch) for batch in _dynamic_master_chunks(high_items)] == [4, 1]
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


def _panel(index):
    return {"panel_id": "%02d" % index, "camera_setup": "中景", "camera_motion": "Static", "visual_description": "人物与场景", "ai_motion_control": "人物小幅动作", "narrative_tag": "节拍"}


def _master_item(shot_id, action, non_character=False):
    source = {
        "shot_id": shot_id, "subshot_id": shot_id + "-01", "base_action": action,
        "duration": 4, "shot_type": "环境" if non_character else "动作",
        "visual_intent": "门外的空间锚点" if non_character else "人物动作",
        "non_character_confirmed": non_character,
        "characters": [] if non_character else ["角色A", "角色B"],
    }
    return {"shot_id": shot_id, "subshot_id": shot_id, "source_subshots": [source]}


if __name__ == "__main__":
    print(run())
