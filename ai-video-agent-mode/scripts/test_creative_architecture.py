#!/usr/bin/env python3
"""Architecture regression: code preserves creativity and proves only facts."""

import json
import os
import tempfile

from batch_planner import batch_profile
from contract_registry import PROMPT_CONTRACT_VERSION
from dispatch_cache import (
    _write_composer_scaffold,
    _write_editor_creative_context,
    _write_scene_lock_cache,
    prepare_dispatch_packets,
)
from export_with_validation import _build_direct_copy_prompt, _build_director_card, _write_master_markdown
from validate_deterministic_package import validate_package


def _write(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def run():
    with tempfile.TemporaryDirectory(prefix="creative-architecture-") as run_dir:
        plan = {
            "dialogue_events": {
                "D1": {"ref": "D1", "kind": "台词", "speaker": "甲", "text": "你回来了。"},
            },
            "shots": [{
                "shot_id": "S1",
                "model_unknown_shot_field": {"rhythm": ["停顿", "回切"], "aesthetic": "模型自定"},
                "subshots": [
                    {
                        "subshot_id": "S1-1", "duration": 4, "dialogue_refs": ["D1"],
                        "model_unknown_child_field": {"camera": "模型自定", "emotion": [1, 2, 3]},
                    },
                    {
                        "subshot_id": "S1-2", "duration": 3, "dialogue_refs": [],
                        "model_unknown_child_field": {"montage": True},
                    },
                ],
            }],
        }
        _write(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"), plan)
        _write(os.path.join(run_dir, "project_config.json"), {"seedance_target": "auto"})
        _write(os.path.join(run_dir, ".cache", "review", "llm_gate_result.json"), {
            "pass": True, "blocking": [], "windows": [{
                "window_id": "W001", "pass": True, "blocking": [],
                "reviewed_shot_ids": ["S1"],
            }],
        })
        creative = "摄影机保持克制的重复构图；甲说“你回来了。”；这一选择由导演判断，不需要关键词证明。"
        shot = {
            "shot_id": "S1", "subshot_id": "S1", "source_subshot_ids": ["S1-1", "S1-2"],
            "duration": 7, "full_prompt": "模型完整导演表达", "seedance_prompt": creative,
            "seedance_prompt_variants": {}, "director_card": "模型导演卡原文",
            "negative_prompt": "模型负面词原文",
            "qa_metadata": {
                "dialogue_refs": ["D1"],
                "dialogue_events": [{
                    "ref": "D1", "kind": "台词", "speaker": "甲", "text": "你回来了。",
                    "delivery": "模型自由设计的表演",
                }],
                "scene_tone_palette": {"freeform": "模型自由创作的色卡"},
            },
            "generation_control": {"mode": "t2v", "audio_enabled": True},
        }
        package_path = os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json")
        _write(package_path, {"contract_version": PROMPT_CONTRACT_VERSION, "shots": [shot]})
        result = validate_package(package_path, run_dir=run_dir, require_editor=True)
        assert result["pass"], result["issues"]
        assert _build_direct_copy_prompt(shot, {}) == creative
        assert _build_director_card(shot, {}) == "模型导演卡原文"
        markdown_path = os.path.join(run_dir, "delivery.md")
        _write_master_markdown(
            markdown_path,
            {"contract_version": PROMPT_CONTRACT_VERSION, "shots": [shot]},
            dict(plan, project_name="测试", canvas="16:9", visual_style="模型风格"),
            [], "auto",
        )
        markdown = open(markdown_path, encoding="utf-8").read()
        assert creative in markdown and "模型导演卡原文" in markdown and "你回来了。" in markdown
        context_path = _write_editor_creative_context(
            run_dir, package_path,
            [{"window_id": "W001", "shot_ids": ["S1"]}],
            os.path.join(run_dir, ".cache", "dispatch"), "test",
        )
        context = json.load(open(context_path, encoding="utf-8"))
        assert context["semantic_transform"] is False
        assert context["shots"][0]["seedance_prompt"] == creative
        assert context["shots"][0]["qa_metadata"]["scene_tone_palette"] == {"freeform": "模型自由创作的色卡"}
        scaffold_path = _write_composer_scaffold(
            run_dir,
            [{
                "shot_id": "S1", "subshot_id": "S1", "source_subshot_ids": ["S1-1"],
                "duration": 7, "dialogue_refs": ["D1"],
                "dialogue_events": list(plan["dialogue_events"].values()),
            }],
            os.path.join(run_dir, ".cache", "dispatch"), "minimal", "scene-locks.json",
        )
        scaffold = json.load(open(scaffold_path, encoding="utf-8"))
        assert scaffold["creative_authority"] == "model"
        assert set(scaffold["shots"][0]["qa_metadata"]) == {"dialogue_refs", "dialogue_events"}
        assert "negative_prompt" not in scaffold["locked_fields"]

        # Identical structure must batch identically regardless of scene words.
        assert batch_profile([{"base_action": "打斗、追逐、强烈情绪"}]) == batch_profile([
            {"base_action": "庭院静止、人物沉默"}
        ])
        scene_locks_path = os.path.join(run_dir, ".cache", "analysis", "scene_locks.json")
        _write(scene_locks_path, {
            "scenes": [{
                "scene": "__default__", "space_id": "SPACE-1",
                "creative_scene_contract": {"model_freeform": "模型场景设计"},
            }]
        })
        packets = prepare_dispatch_packets(run_dir, "master_production", batch_size=6)
        packet = json.load(open(packets[0], encoding="utf-8"))
        assert packet["batch_policy"] == "item_count_chain_ids_and_context_size"
        assert packet["creative_review_scope"] == "full_model_review"
        assert packet["checkpoint_policy"]["checkpoint_after_each_item"] is True
        assert packet["checkpoint_policy"]["partial_checkpoint_is_completion"] is False
        assert packet["progress_command_template"][-2:] == ["{packet_path}", "{agent_id}"]
        assert packet["checkpoint_command_template"][-2:] == ["--item-id", "{item_id}"]
        assert os.path.isfile(packet["source_evidence_path"])
        assert "source_snapshot_path" not in packet["context_policy"]["fixed_global_context"]
        assert "cacheable_context" not in packet
        assert "risk_tier" not in packet and "risk_reasons" not in packet
        packet_item = packet["items"][0]
        assert "editorial_mode" not in packet_item
        assert "shot_group" not in packet["instruction"]
        assert set(packet_item) == {
            "shot_id", "subshot_id", "source_subshot_ids", "duration",
            "scene_lock_ref", "composer_scaffold_ref",
        }
        master_context = json.load(open(packet["master_creative_context_path"], encoding="utf-8"))
        record = master_context["records"][0]
        assert record["model_unknown_shot_field"] == plan["shots"][0]["model_unknown_shot_field"]
        assert record["subshots"][0]["model_unknown_child_field"] == plan["shots"][0]["subshots"][0]["model_unknown_child_field"]
        assert record["subshots"][1]["model_unknown_child_field"] == plan["shots"][0]["subshots"][1]["model_unknown_child_field"]
        assert "parent_shot_context" not in json.dumps(master_context, ensure_ascii=False)
        assert "source_subshots" not in json.dumps(master_context, ensure_ascii=False)
        os.remove(scene_locks_path)
        try:
            _write_scene_lock_cache(run_dir, [], "", "")
        except FileNotFoundError as exc:
            assert "CREATIVE_AUTHORING_REQUIRED" in str(exc)
        else:
            raise AssertionError("engineering synthesized a missing Scene Lock")

        both = dict(shot)
        both["seedance_prompt"] = ""
        both["seedance_prompt_variants"] = {"2.0": "二点零模型原文：你回来了。", "2.5": "二点五模型原文：你回来了。"}
        _write(os.path.join(run_dir, "project_config.json"), {"seedance_target": "both"})
        _write(package_path, {"contract_version": PROMPT_CONTRACT_VERSION, "shots": [both]})
        assert validate_package(package_path, run_dir=run_dir)["pass"]
        assert _build_direct_copy_prompt(both, {}, seedance_target="2.0") == "二点零模型原文：你回来了。"
        assert _build_direct_copy_prompt(both, {}, seedance_target="2.5") == "二点五模型原文：你回来了。"

        missing = dict(both)
        missing["seedance_prompt_variants"] = {"2.0": "二点零模型原文：你回来了。"}
        _write(package_path, {"contract_version": PROMPT_CONTRACT_VERSION, "shots": [missing]})
        failed = validate_package(package_path, run_dir=run_dir)
        assert not failed["pass"] and any("CREATIVE_REWRITE_REQUIRED" in issue for issue in failed["issues"])

        mismatch = dict(shot)
        mismatch["duration"] = 16
        mismatch["qa_metadata"] = dict(shot["qa_metadata"])
        mismatch["qa_metadata"]["dialogue_events"] = [dict(shot["qa_metadata"]["dialogue_events"][0], text="改字")]
        _write(os.path.join(run_dir, "project_config.json"), {"seedance_target": "auto"})
        _write(package_path, {"contract_version": PROMPT_CONTRACT_VERSION, "shots": [mismatch]})
        failed = validate_package(package_path, run_dir=run_dir)
        assert any("15 seconds" in issue for issue in failed["issues"])
        assert any("source ledger" in issue for issue in failed["issues"])
    print("creative architecture regression passed")


if __name__ == "__main__":
    run()
