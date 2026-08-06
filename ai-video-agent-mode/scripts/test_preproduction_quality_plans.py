#!/usr/bin/env python3
"""Regression coverage for profile routing and pre-composition quality plans."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from dispatch_cache import prepare_dispatch_packets
from episode_director_audit import analyze_package
from prompt_contract import prompt_information_budget_issues, video_texture_contract_issues
from scene_motion_plan import build as build_motion_plan
from scene_texture_plan import build as build_texture_plan
from visual_profile_router import GENERIC_PROFILE, route_visual_profile


def run():
    explicit = route_visual_profile("古代府邸，汉服人物在月光下开门。", {"visual_style": "古风游戏"})
    assert explicit["base_profile"] == "chinese_wuxia_game_cinematic"
    assert explicit["confidence"] == "high" and explicit["user_overrides"]

    weak = route_visual_profile("古装人物站在门边。")
    assert weak["confidence"] == "low" and weak["base_profile"] == GENERIC_PROFILE

    mixed_source = """SCENE 1 古代府邸
古代府邸内，汉服人物在月光下推开木门。
SCENE 2 现代办公室
现代办公室内，西装人物拿起手机，窗光落在桌面。
"""
    mixed = route_visual_profile(mixed_source)
    scene_profiles = {item["base_profile"] for item in mixed["scene_receipts"]}
    assert "period_court_cinematic" in scene_profiles
    assert scene_profiles.intersection({"modern_natural_drama", "modern_cinematic_variant"})
    assert mixed["contradictions"]

    with tempfile.TemporaryDirectory(prefix="preproduction-plans-") as root:
        run_dir = Path(root)
        orchestrator = run_dir / ".cache" / "orchestrator"
        analysis = run_dir / ".cache" / "analysis"
        orchestrator.mkdir(parents=True)
        analysis.mkdir(parents=True)
        config = {
            "canvas": "16:9",
            "visual_style": "古风游戏",
            "target_platform": "即梦",
            "generation_control": {"mode": "t2v", "audio_enabled": True},
            "source_rules": {"style_evidence": explicit},
        }
        _write(run_dir / "project_config.json", config)
        shot_plan = {
            "shots": [
                {"shot_id": "S1", "scene": "府邸", "core_action": "角色A推开木门", "subshots": [
                    {"subshot_id": "S1-1", "duration": 3, "characters": ["角色A"], "base_action": "角色A推开木门", "dialogue_refs": []},
                ]},
                {"shot_id": "S2", "scene": "府邸", "core_action": "角色A停在门内", "subshots": [
                    {"subshot_id": "S2-1", "duration": 3, "characters": ["角色A"], "base_action": "角色A停在门内", "dialogue_refs": []},
                ]},
            ],
            "dialogue_events": {},
            "dialogue_map": {},
        }
        _write(orchestrator / "shot_plan.json", shot_plan)
        locks = {"scenes": [{
            "scene": "府邸", "space_anchor": "木门与长廊", "screen_positions": "角色A位于门内左侧",
            "wardrobe_lock": "角色A沿用确认长袍", "prop_state": "木门半开",
            "light_source": "庭院月光", "light_direction": "从画面右后方", "light_temperature": "冷中性",
            "foreground_layer": "前景门框轻虚", "midground_layer": "中景角色A与木门实焦",
            "background_layer": "后景长廊低对比退后", "genre_visual_signature": "东方府邸木构与自然月色",
            "lived_in_detail": "门槛磨损和长袍自然褶皱", "depth_focus_policy": "门框轻虚、人物实焦、长廊退后",
            "landscape_identity": "秋夜府邸木构长廊", "landscape_composition": "门框纵线与长廊引导线形成留白",
            "natural_motion_system": "开门侧风先进入，衣料稍晚低幅响应",
            "environment_story_arc": "门开前稳定，开门后月光进入，余波在门内停稳",
            "reveal_order": "先见门框，后见人物，最终停在长廊", "light_weather_progression": "月光方向保持不变",
            "breathing_policy": "建立镜交代长廊，人物镜让背景退后", "audio_policy": "原生音频开启",
        }]}
        lock_path = analysis / "scene_locks.json"
        _write(lock_path, locks)

        motion, motion_path = build_motion_plan(str(run_dir))
        assert Path(motion_path).is_file()
        assert motion["scenes"][0]["motion_roles"] == ["initiate", "payoff"]
        assert all(item["response_budget"] <= 2 for item in motion["scenes"][0]["shots"])

        texture, texture_path = build_texture_plan(str(run_dir), str(lock_path))
        assert Path(texture_path).is_file()
        contract = texture["scenes"][0]["video_texture_contract"]
        assert not video_texture_contract_issues({"video_texture_contract": contract})
        assert video_texture_contract_issues({}, required=True)

        packets = prepare_dispatch_packets(str(run_dir), "master_production", batch_size=1)
        packet = _load(Path(packets[0]))
        scaffold = _load(Path(packet["composer_scaffold_path"]))
        assert "scene_motion_plan_path" not in scaffold
        assert "scene_texture_plan_path" not in scaffold
        model_texture = scaffold["shots"][0]["qa_metadata"]["video_texture_contract"]
        assert model_texture and not any(model_texture.values())

    overloaded_budget = {"prompt_information_budget": {
        "profile": "dialogue",
        "primary_render_task": "角色A说出原文台词并停稳",
        "must_render": "角色A说出原文台词；角色A停稳",
        "supporting_visual": "窗光扫过墙面；玻璃产生断续反光",
        "metadata_only": "关系压力升级",
        "visual_enhancer_limit": 1,
        "compression_rule": "先删除辅助视觉，保留台词与终态",
    }}
    assert any("超过声明预算" in issue for issue in prompt_information_budget_issues(overloaded_budget))

    package = {"shots": []}
    for index in range(4):
        package["shots"].append({
            "shot_id": "R%d" % index,
            "subshot_id": "R%d" % index,
            "scene": "同场",
            "duration": 3,
            "full_prompt": "角色A手指压住杯沿，随后停稳。",
            "qa_metadata": {
                "dynamic_aesthetic_contract": {"primary_subject_motion": "角色A手指压住杯沿"},
                "performance_contract": {"primary_expression": "表情%d" % index, "primary_body_action": "角色A手指压住杯沿"},
            },
        })
    audit = analyze_package(package)
    assert any("语义运动家族" in warning for warning in audit["warnings"])
    print("preproduction quality plan regression passed")


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    run()
