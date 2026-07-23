"""Deterministic contract regression for the current pipeline's file boundaries."""
import json
import os
import tempfile

from context_budget import check
from editor_scene_windows import build
from modec_v4 import dialogue_event_issues, expectation_anchor_issues, jimeng_feed_prompt, listener_reaction_issues, shot_group_handoff_issues
from pipeline_runtime import atomic_json, cache_artifact, record_issues
from adapt_nine_panel_storyboard import adapt
from emotion_camera_audit import audit as emotion_camera_audit
from spatial_storyboard import build_spatial_storyboard_reference
from validate_scene_locks import validate
from shot_semantics import dispatch_risk
from dispatch_cache import _dynamic_master_chunks
from pipeline_templates import GATES
from pipeline_runner import _materialize


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
        plan = {"shots": [{"shot_id": "S1", "scene": "场景A", "subshots": [{"subshot_id": "S1-01"}]},
                          {"shot_id": "S2", "scene": "场景A", "subshots": [{"subshot_id": "S2-01"}]}]}
        package = {"shots": [{"shot_id": "S1", "source_subshot_ids": ["S1-01"], "duration": 4, "full_prompt": "x", "qa_metadata": {}},
                             {"shot_id": "S2", "source_subshot_ids": ["S2-01"], "duration": 4, "full_prompt": "y", "qa_metadata": {}}]}
        _write(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"), plan)
        _write(os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json"), package)
        windows = build(run_dir)
        assert len(windows) == 2 and windows[0]["current"]["shot_id"] == "S1" and windows[1]["previous"]["shot_id"] == "S1"
        assert check({"items": [{"shot_id": "S1"}]}) > 0
        atomic_json(os.path.join(run_dir, ".cache", "control.json"), {"ok": True})
        assert _read(os.path.join(run_dir, ".cache", "control.json"))["ok"] is True
        cache_artifact(run_dir, "test", {"value": 1})
        record_issues(run_dir, "first", ["a"])
        record_issues(run_dir, "second", ["b"])
        assert set(_read(os.path.join(run_dir, ".cache", "issues.json"))) == {"first", "second"}
        canonical = "生成规格：规格\n\n主体与空间锁定：空间\n\n主镜头连续规则：规则\n\n子镜头组：【镜头1｜0.0-1.0秒】画面\n\n光照、声音与稳定约束：光声"
        assert "生成规格：" not in jimeng_feed_prompt(canonical)
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
        light_items = [_master_item("E%02d" % index, "环境", non_character=True) for index in range(1, 11)]
        light_risk = dispatch_risk(light_items[0])
        assert light_risk["tier"] == "light" and light_risk["batch_capacity"] == 10
        assert [len(batch) for batch in _dynamic_master_chunks(light_items)] == [10]
        high_items = [_master_item("F%02d" % index, "两人打斗后互相格挡") for index in range(1, 6)]
        high_risk = dispatch_risk(high_items[0])
        assert high_risk["tier"] == "high" and high_risk["batch_capacity"] == 4
        assert [len(batch) for batch in _dynamic_master_chunks(high_items)] == [4, 1]
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
