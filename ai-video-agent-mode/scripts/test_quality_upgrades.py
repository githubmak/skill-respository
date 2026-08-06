#!/usr/bin/env python3
"""Focused regression tests for direct-copy and episode-level quality upgrades."""

from pathlib import Path
from tempfile import TemporaryDirectory

from dialogue_timing import analyze_dialogue_timing
from direct_prompt_compiler import compile_direct_prompt, compile_director_card
from check_export import _production_control_export_issues
from episode_director_audit import analyze_package
from export_with_validation import (
    _build_direct_copy_prompt,
    _composition_direct_clause,
    _dynamic_motion_anchor,
    _global_lock_lines,
    _global_negative_prompt,
    _global_quality_control_lines,
    _shot_production_control,
    _terminal_frame_direct_clause,
    _write_master_markdown,
)
from negative_prompts import build_negative_prompt_for_item, support_mode_for_text
from generate_shotplan import (
    _characters_in_source_order,
    _offscreen_character_mention,
    _pack_source_actions_with_interactions,
)
from prompt_contract import (
    aesthetic_directing_contract_issues,
    character_scene_objective_issues,
    cut_decision_contract_issues,
    dialogue_event_issues,
    direct_copy_prompt_issues,
    performance_contract_issues,
    prop_functional_surface_contract_issues,
    skin_tone_protection_contract_issues,
    prompt_information_budget_issues,
    production_control_grounding_issues,
    production_control_grounding_report,
    relationship_emotion_arc_issues,
    sequence_directing_plan_issues,
    sound_directing_plan_issues,
    story_punch_issues,
)


def run():
    skill_root = Path(__file__).resolve().parents[1]
    liveness = (skill_root / "references" / "liveness-motion-grammar.md").read_text(encoding="utf-8")
    aesthetic = (skill_root / "references" / "contracts" / "aesthetic_directing_contract.md").read_text(encoding="utf-8")
    constraints = (skill_root / "references" / "format_constraints.md").read_text(encoding="utf-8")
    profiles = (skill_root / "references" / "visual-direction-profiles.md").read_text(encoding="utf-8")
    assert "动力源 | 起始静止锚点 | 主体触发" in liveness
    assert "at most two low-amplitude, source-coupled responses" in aesthetic
    assert "liveness-motion-grammar.md" in aesthetic
    assert "一条因果响应链" in constraints
    for routing_fact in ("多证据自动适配", "evidence_score", "narrative_modifier", "period_court_cinematic",
                         "rural_lived_in_naturalism", "现代夜景不自动加入霓虹", "低置信回到通用电影化默认"):
        assert routing_fact in profiles, routing_fact

    aesthetic_prompt = (
        "16:9写实电影短片，前景门框压住画面左侧，中景角色A站在粗糙木桌旁。"
        "左侧窗光照亮角色A面部和手背，鼻翼阴影保留细节，暗部不死黑；"
        "低饱和青灰背景与微暖肤色分离，高光不过曝。粗糙木桌吸光，带断续水渍的玻璃杯产生不均匀反光。"
        "门打开后角色A抬眼看向门口，窗帘稍晚轻摆一次，最终角色A右手仍压住桌沿并停稳。"
    )
    aesthetic_metadata = {"visual_bible": {
        "visual_thesis": "门口变化打破角色A的防御，第一落点是压住桌沿的手",
        "palette_system": "主色低饱和青灰落在背景，辅助微暖肤色落在人物，玻璃冷白反光作点缀",
        "light_motivation": "左侧窗光照亮角色A面部、手背与桌沿",
        "contrast_exposure": "暗部保留层次不死黑，高光不过曝",
        "composition_grammar": "前景门框与中景木桌形成关系阻隔",
        "material_world": "粗糙木桌吸光，带水渍玻璃杯产生不均匀反光",
        "atmosphere_rule": "空气保持清晰，只在后景保留轻微空间纵深",
        "imperfection_policy": "玻璃杯保留断续水渍与不均匀反光",
        "reference_policy": "无外部参考，只使用当前场景事实",
        "continuity_lock": "跨镜保持左侧窗光、青灰背景和木桌位置",
    }, "static_aesthetic_contract": {
        "visual_intent": "读清角色A被门口变化打断",
        "composition_hierarchy": "前景门框压住左侧，中景角色A与木桌为第一层",
        "light_design": "左侧窗光照亮角色A面部和手背，鼻翼阴影保留细节",
        "color_grade": "低饱和青灰背景与微暖肤色分离，高光不过曝、黑位可读",
        "lens_rendering": "50mm中近景，焦平面停在手与脸之间",
        "depth_atmosphere": "前景门框轻虚，中景实焦，后景低幅弱化",
        "material_anchor": "粗糙木桌吸光，玻璃杯水渍产生不均匀反光",
        "signature_frame": "角色A右手压住桌沿，目光刚落向门口",
        "aesthetic_exclusions": "不增加无因雾层或装饰辉光",
    }, "dynamic_aesthetic_contract": {
        "motion_thesis": "静态防御被开门声触发，低幅响应后重新稳定",
        "start_state": "角色A右手压住桌沿并看向桌面",
        "trigger": "门打开",
        "primary_subject_motion": "角色A抬眼看向门口",
        "secondary_environment_motion": "窗帘稍晚轻摆一次",
        "camera_path": "摄影机固定在50mm中近景",
        "focus_behavior": "焦点保持在角色A脸与手之间",
        "material_motion": "玻璃杯反光保持稳定",
        "atmosphere_motion": "后景空气层保持静止",
        "tempo_easing": "抬眼动作先快后缓，窗帘余波自行减弱",
        "end_state": "最终角色A右手仍压住桌沿并停稳",
        "stability_fallback": "取消窗帘响应并保持固定机位",
    }, "aesthetic_priority": {
        "visual_thesis": "门口变化打破防御",
        "primary_eye_target": "角色A压住桌沿的右手",
        "secondary_visual_layer": "门口方向的低幅窗帘响应",
        "must_preserve": "角色A身份、手部接触、窗光方向和终态",
        "degrade_first": "先删除窗帘响应和后景空气层",
    }}
    assert not aesthetic_directing_contract_issues(aesthetic_metadata, aesthetic_prompt)
    weak_aesthetic = {key: dict(value) for key, value in aesthetic_metadata.items()}
    weak_aesthetic["visual_bible"]["material_world"] = "所有表面都很高级"
    weak_aesthetic["static_aesthetic_contract"]["light_design"] = "电影感光影"
    weak_issues = aesthetic_directing_contract_issues(weak_aesthetic, aesthetic_prompt)
    assert any("至少两类材质" in issue for issue in weak_issues)
    assert any("光源、方向、受光面和阴影结果" in issue for issue in weak_issues)
    export_task = {
        "full_prompt": aesthetic_prompt,
        "director_card": "16:9写实电影短片。室内长桌前，角色A右手压住桌沿，门打开后抬眼看向门口，窗光照亮脸和手背，固定机位停稳，最终手仍压在桌沿。",
        "qa_metadata": aesthetic_metadata, "shot_id": "A1", "subshot_id": "A1-1",
    }
    global_quality = "\n".join(_global_quality_control_lines({"shots": [export_task]}))
    for label in ("画面质感基线", "光效与曝光连续", "动态美学基线", "表演与情绪基线", "蒙太奇与剪辑基线", "穿帮与抽卡总控"):
        assert label in global_quality, label
    shot_control = _shot_production_control(export_task)
    for label in ("画面质感", "光效与曝光", "动态美学", "表演与情绪", "穿帮控制", "抽卡策略", "蒙太奇与剪辑"):
        assert label + "：" in shot_control, label
    assert "门打开" in shot_control and "最终角色A右手仍压住桌沿并停稳" in shot_control
    assert "最终最终" not in shot_control and "起幅起幅" not in shot_control
    with TemporaryDirectory(prefix="quality-markdown-") as temp_dir:
        markdown_path = Path(temp_dir) / "quality.md"
        markdown_task = dict(export_task, duration=4, negative_prompt="五官漂移", source_subshot_ids=["A1-1"])
        _write_master_markdown(
            str(markdown_path),
            {"shots": [markdown_task]},
            {"project_name": "质量可见性", "canvas": "16:9", "visual_style": "写实电影短片", "shots": [{"shot_id": "A1", "scene": "室内"}]},
            [],
        )
        markdown = markdown_path.read_text(encoding="utf-8")
        assert "## 制作质量总控" in markdown
        assert "【本镜制作控制】" in markdown
        for label in ("画面质感", "光效与曝光", "动态美学", "表演与情绪", "穿帮控制", "抽卡策略", "蒙太奇与剪辑"):
            assert label + "：" in markdown, label
        assert not _production_control_export_issues(markdown)
        placeholder_markdown = markdown.replace("画面质感：门口变化打破防御", "画面质感：已检查，按合同执行")
        assert any("内部占位" in issue for issue in _production_control_export_issues(placeholder_markdown))
    compile_reports = []
    direct_aesthetic = _build_direct_copy_prompt(
        export_task,
        {"canvas": "16:9", "visual_style": "写实电影短片"},
        compile_reports,
    )
    motion_anchor = _dynamic_motion_anchor(aesthetic_metadata)
    assert motion_anchor in direct_aesthetic
    assert "粗糙木桌吸光" in direct_aesthetic and "不均匀反光" in direct_aesthetic
    assert compile_reports and motion_anchor in compile_reports[0]["protected_required_fragments"]
    grounding_report = compile_reports[0]["production_control_grounding"]
    for dimension in ("画面质感", "光效与曝光", "动态美学"):
        assert grounding_report[dimension]["grounded"] is True, (dimension, grounding_report[dimension])

    missing_grounding_metadata = {
        "static_aesthetic_contract": {"composition_hierarchy": "门框压住左侧，角色A位于右侧中景"},
        "reroll_control": {
            "mitigation_steps": ["需要人工首轮检查", "失败后拆镜重试"],
        },
    }
    missing_grounding = production_control_grounding_issues(
        missing_grounding_metadata, "角色A站在房间里，镜头固定。"
    )
    assert any("画面质感" in issue for issue in missing_grounding), missing_grounding
    assert not any("抽卡策略" in issue for issue in missing_grounding), missing_grounding
    grounded = production_control_grounding_report(
        missing_grounding_metadata, "门框压住左侧，角色A位于右侧中景，镜头固定。"
    )
    assert grounded["画面质感"]["grounded"] is True
    reroll_grounding = production_control_grounding_report(
        {"reroll_control": {"mitigation_steps": [
            "锁定可见人数与槽位", "可见结果：双拐始终由卫景耘双手承重"
        ]}},
        "卫景耘站在左侧，双拐始终由卫景耘双手承重。",
    )
    assert reroll_grounding["抽卡策略的可见降级结果"]["candidate_facts"] == ["双拐始终由卫景耘双手承重"]
    assert reroll_grounding["抽卡策略的可见降级结果"]["grounded"] is True

    weak_motion = {key: dict(value) for key, value in aesthetic_metadata.items()}
    weak_motion["dynamic_aesthetic_contract"]["primary_subject_motion"] = "灵动地表现情绪"
    weak_motion["dynamic_aesthetic_contract"]["secondary_environment_motion"] = "窗帘轻摆一次"
    weak_motion["dynamic_aesthetic_contract"]["tempo_easing"] = "自然流畅"
    weak_motion["dynamic_aesthetic_contract"]["end_state"] = "角色A右手仍压住桌沿并站着"
    weak_motion_prompt = (
        aesthetic_prompt.replace("窗帘稍晚轻摆一次", "窗帘轻摆一次")
        .replace("最终角色A右手仍压住桌沿并停稳", "角色A右手仍压住桌沿并站着")
    )
    weak_motion_issues = aesthetic_directing_contract_issues(weak_motion, weak_motion_prompt)
    assert any("可执行身体/视线/重心动作" in issue for issue in weak_motion_issues)
    assert any("时间节拍" in issue for issue in weak_motion_issues)

    overloaded_motion = {key: dict(value) for key, value in aesthetic_metadata.items()}
    overloaded_motion["dialogue_events"] = [
        {"text": "这句话已经足够长，需要把环境响应收敛到唯一一项。"},
        {"text": "另一句继续占用口型与表演容量。"},
    ]
    overloaded_motion["dynamic_aesthetic_contract"].update({
        "secondary_environment_motion": "窗帘稍晚轻摆一次",
        "material_motion": "玻璃杯反光随后移动",
        "atmosphere_motion": "后景空气颗粒最后低幅流动并减弱",
    })
    overloaded_prompt = aesthetic_prompt.replace(
        "窗帘稍晚轻摆一次",
        "窗帘稍晚轻摆一次，玻璃杯反光随后移动，后景空气颗粒最后低幅流动并减弱",
    )
    assert any("超过本镜预算1" in issue for issue in aesthetic_directing_contract_issues(
        overloaded_motion, overloaded_prompt
    ))

    scale_locks = "\n".join(_global_lock_lines({"shots": []}, {"visual_style": "写实"}))
    assert "全局比例与支撑锁定" in scale_locks
    assert "站立时双脚接地" in scale_locks
    assert "行走时步态交替接地" in scale_locks
    assert "腾空时保持起跳、空中与落地轨迹连续" in scale_locks
    assert "两人身高差" in scale_locks
    scale_negative = _global_negative_prompt({"shots": []})
    for term in ("人物忽高忽低", "体型动态变化", "腿部拉长缩短", "无因尺度跳变",
                 "无因浮空", "透视错乱", "穿模", "肢体畸形", "广角畸变"):
        assert term in scale_negative, term
    assert support_mode_for_text("角色站定在门边") == "grounded"
    assert support_mode_for_text("角色沿走廊跑向楼梯") == "locomotion"
    assert support_mode_for_text("角色坐在沙发上") == "supported"
    assert support_mode_for_text("角色施展轻功腾空") == "airborne"
    airborne_negative = build_negative_prompt_for_item({"full_prompt": "角色施展轻功腾空"})
    assert "空中无因悬停" in airborne_negative and "脚底脱离支撑面" not in airborne_negative
    grounded_negative = build_negative_prompt_for_item({"full_prompt": "角色站定在门边"})
    assert "脚底脱离支撑面" in grounded_negative and "空中无因悬停" not in grounded_negative

    budget_metadata = {"prompt_information_budget": {
        "profile": "dialogue", "primary_render_task": "角色A说：别走",
        "must_render": "角色A说：别走；角色B右手握住钥匙",
        "supporting_visual": "窗外车灯扫过墙面", "metadata_only": "关系权力发生逆转",
        "visual_enhancer_limit": 1, "compression_rule": "先整句删除辅助视觉，保留台词与道具",
    }}
    budget_prompt = "角色A说：别走。角色B右手握住钥匙，最终停在门边。"
    assert not prompt_information_budget_issues(budget_metadata, budget_prompt)
    missing_budget_prompt = "角色A说：别走，最终停在门边。"
    assert any("角色B右手握住钥匙" in issue for issue in prompt_information_budget_issues(
        budget_metadata, missing_budget_prompt
    ))
    leaked_budget_prompt = budget_prompt + "关系权力发生逆转。"
    assert any("metadata_only" in issue for issue in prompt_information_budget_issues(
        budget_metadata, leaked_budget_prompt
    ))
    repeated_direct = "窗外侧光照亮角色A手背。窗外侧光照亮角色A手背。"
    assert any("重复执行句" in issue for issue in direct_copy_prompt_issues(
        repeated_direct, require_visual_texture=False
    ))

    dedup = compile_direct_prompt([
        {"kind": "visual_prefix", "text": "16:9动态漫。冷白顶灯。"},
        {"kind": "space", "text": "冷白顶灯。角色A站在画面左侧。"},
        {"kind": "performance", "text": "角色A拇指压住杯沿，句末闭口。"},
    ])
    assert not dedup["issues"]
    assert dedup["text"].count("冷白顶灯") == 1
    assert dedup["removed_duplicate_count"] == 1

    line = '角色A（台词）: "别再骗我。"'
    protected = compile_direct_prompt([
        {"kind": "visual_prefix", "text": "16:9动态漫。"},
        {"kind": "performance", "text": line + " 角色A句末闭口。"},
    ], required_fragments=[line])
    assert not protected["issues"] and line in protected["text"]

    compressed = compile_direct_prompt([
        {"kind": "visual_prefix", "text": "16:9动态漫，冷白长桌空间，角色A位于画面左侧。"},
        {"kind": "cinematic", "text": "辅助电影质感" * 30},
    ], max_chars=80)
    assert compressed["creative_rewrite_required"] is True
    assert compressed["omitted"] == []
    assert len(compressed["text"]) > 80

    hard_overflow = compile_direct_prompt([
        {"kind": "space", "text": "不可删除空间事实" * 30},
    ], max_chars=40)
    assert hard_overflow["issues"] and len(hard_overflow["text"]) > 40

    motion_anchor = "起幅角色A站定，因门响主体抬眼，随后窗帘轻摆，最终角色A停稳。"
    protected_motion = compile_direct_prompt([
        {"kind": "space", "text": "空间硬事实" * 30},
        {"kind": "video_texture", "text": motion_anchor + "；装饰性空气层。"},
    ], required_fragments=[motion_anchor], max_chars=80)
    assert motion_anchor in protected_motion["text"]
    assert protected_motion["issues"]

    negative_camera = compile_direct_prompt([
        {"kind": "visual_prefix", "text": "16:9动态漫。"},
        {"kind": "cinematic", "text": "低幅推近，横移跟拍，禁止环绕。"},
    ])
    assert not any("运镜执行竞争" in issue for issue in negative_camera["issues"])
    competing_camera = compile_direct_prompt([
        {"kind": "visual_prefix", "text": "16:9动态漫。"},
        {"kind": "cinematic", "text": "推近，横移，环绕。"},
    ])
    assert any("运镜执行竞争" in issue for issue in competing_camera["issues"])
    over_budget = compile_direct_prompt([
        {"kind": "visual_prefix", "text": "16:9写实短剧。"},
        {"kind": "video_texture", "text": "跨镜保持低饱和黑位。"},
        {"kind": "cinematic", "text": "前景门框轻虚化。"},
    ], information_budget={"profile": "dialogue", "visual_enhancer_limit": 1})
    assert any("视觉增强层超过" in issue for issue in over_budget["issues"])
    assert over_budget["budget_profile"] == "dialogue"

    # Static light/material anchors are not a monolithic required fragment;
    # clause-level compression may retain the visible light evidence.
    from export_with_validation import _direct_prompt_inputs
    static_only_task = {
        "shot_id": "S1",
        "full_prompt": "生成规格：16:9画幅。\n\n主体与空间锁定：角色A站在室内。\n\n主镜头连续规则：固定机位。\n\n子镜头组：0.0-2.0秒角色A站定。\n\n光照、声音与稳定约束：右上方5600K自然光照亮脸手。",
        "qa_metadata": {
            "dialogue_events": [],
            "prompt_information_budget": {"must_render": "角色A站定"},
            "dynamic_aesthetic_contract": {"start_state": "角色A起幅站定", "primary_subject_motion": "角色A站定", "end_state": "角色A最终站定"},
            "static_aesthetic_contract": {"light_design": "右上方5600K自然光照亮脸手", "color_grade": "低饱和自然日景", "material_anchor": "墙面粗糙纹理"},
        },
        "generation_control": {"audio_enabled": False},
    }
    _segments, required, _budget = _direct_prompt_inputs(static_only_task, {"canvas": "16:9", "visual_style": "3D"})
    assert all("低饱和自然日景" not in item for item in required)

    director_card = compile_director_card([
        {"kind": "visual_prefix", "text": "9:16画幅，写实电影风格，夜雨车站，冷蓝环境光与远处暖色站牌。"},
        {"kind": "space", "text": "前景湿伞边缘，中景角色A站在站牌左侧，后景雨幕和空旷站台形成纵深，保持画面左侧空间。"},
        {"kind": "continuity", "text": "角色A胸口朝画面右侧，右手握住文件袋，固定机位缓慢推近，落幅停在眼神与文件袋之间。"},
        {"kind": "performance", "text": "角色A低声说：我只是想把事情说清楚。说完闭口，指节收紧，角色B在后景弱虚化观察反应。"},
        {"kind": "light", "text": "窗边冷光勾勒肩线，面部保持中性肤色，暖色只落在站牌和湿地反光，雨雾空气层轻微流动。"},
    ], ["我只是想把事情说清楚"], {})
    assert not director_card["issues"], director_card["issues"]
    assert 0 < len(director_card["text"]) <= 500

    terminal_metadata = {
        "static_aesthetic_contract": {
            "composition_hierarchy": "门框前景形成框景，角色A为主焦点，角色B弱化在右后方"
        },
        "terminal_frame_contract": {
            "visible_count": "2人", "final_slot_map": "角色A左侧，角色B右后方",
            "identity_visibility": "两人身份清楚", "face_and_limb_separation": "脸、手和四肢边界分开",
            "prop_and_garment_state": "文件仍归角色A", "support_and_contact": "两人双脚接地",
            "camera_lock": "摄影机减速停稳", "light_exposure_lock": "左侧窗光和曝光保持",
            "no_new_entrant": "不新增人物", "no_duplicate_subject": "不产生重复人物",
            "final_hold": "保持到结束",
        },
    }
    assert _composition_direct_clause(terminal_metadata).startswith("构图骨架：门框前景")
    terminal_clause = _terminal_frame_direct_clause(terminal_metadata)
    for fact in ("最后20%只保留2人", "脸、手和四肢边界分开", "摄影机减速停稳", "不产生重复人物"):
        assert fact in terminal_clause, terminal_clause

    valid_episode = {"shots": [
        _shot("S1", "setup", "全景", "角色A呼吸放慢", "角色A双手垂在身侧"),
        _shot("S2", "rising", "中景", "角色A眉间轻收", "角色A拇指压住杯沿"),
        _shot("S3", "peak", "近景", "角色A下颌绷紧", "角色A手背筋络浮起"),
        _shot("S4", "release", "中近景", "角色A眼睑松开", "角色A肩线缓慢下沉"),
        _shot("S5", "buffer", "远景", "角色A视线移向窗外", "角色A双手离开杯沿"),
    ]}
    valid_result = analyze_package(valid_episode)
    assert valid_result["pass"], valid_result["issues"]
    assert valid_result["summary"]["peak_count"] == 1
    assert valid_result["shots"][3]["shot_size"] == "中近景"

    disabled_move = _shot("N1", "setup", "中景", "角色A视线平稳", "角色A双手自然下垂")
    disabled_move["full_prompt"] += "禁止环绕，不使用甩镜。"
    assert analyze_package({"shots": [disabled_move]})["shots"][0]["camera_energy"] == "still"

    flat = {"shots": [
        _shot("F%d" % index, "peak", "中景", "角色A眉间轻收", "角色A拇指压住杯沿")
        for index in range(1, 5)
    ]}
    for shot in flat["shots"]:
        shot["qa_metadata"]["performance_contract"].update({
            "eye_focus": "角色A视线压住角色B",
            "voice_or_breath_control": "角色A短促吸气后屏住",
            "readable_image_moment": "角色A拇指压住杯沿",
        })
    flat_result = analyze_package(flat)
    assert not flat_result["pass"]
    assert any("连续三镜均为峰值" in issue for issue in flat_result["issues"])
    assert any("重复同一组" in issue for issue in flat_result["issues"])

    repeated_liveness = {"shots": [
        _shot("L%d" % index, "setup", "中景", "角色A视线移向门口%d" % index, "角色A右手停在桌沿%d" % index)
        for index in range(1, 5)
    ]}
    for shot in repeated_liveness["shots"]:
        shot["full_prompt"] += " 摄影机缓慢推近0.2米。"
    liveness_result = analyze_package(repeated_liveness)
    assert any("重复灵动性套路camera_push" in issue for issue in liveness_result["issues"])

    dead_liveness = {"shots": [
        _shot("DL%d" % index, "setup", "中景", "角色A保持克制", "角色A保持原姿态")
        for index in range(1, 5)
    ]}
    for shot in dead_liveness["shots"]:
        shot["qa_metadata"]["performance_contract"].update({
            "eye_focus": "角色A看向门口",
            "voice_or_breath_control": "保持呼吸",
            "readable_image_moment": "角色A保持原姿态",
        })
    dead_result = analyze_package(dead_liveness)
    assert any("没有可辨识的因果运动" in warning for warning in dead_result["warnings"])

    cross_scene_peaks = {"shots": [
        dict(_shot("C%d" % index, "peak", "中景", "角色A眉间轻收", "角色A拇指压住杯沿"), scene="SC%d" % index)
        for index in range(1, 4)
    ]}
    cross_scene_result = analyze_package(cross_scene_peaks)
    assert cross_scene_result["pass"]
    assert any("连续三镜均为峰值" in warning for warning in cross_scene_result["warnings"])

    varied_body = {"shots": [
        _shot("VB1", "setup", "中景", "角色A眉间轻收", "角色A双手垂在身侧"),
        _shot("VB2", "rising", "中近景", "角色A眉头轻轻收拢", "角色A向门边后退一步"),
        _shot("VB3", "peak", "近景", "角色A眉间收紧", "角色A转身面向门口"),
        _shot("VB4", "release", "全景", "角色A眉峰压低", "角色A右手推开房门"),
    ]}
    varied_body_result = analyze_package(varied_body)
    assert varied_body_result["pass"], varied_body_result["issues"]

    dialogue_events = [
        _dialogue("D1", "角色A", "这句话根本说不完。", "0.0-1.0秒"),
        _dialogue("D2", "角色B", "我也不同意。", "0.5-2.0秒"),
    ]
    timing_records, timing_issues = analyze_dialogue_timing(dialogue_events, 3)
    assert len(timing_records) == 2
    assert any("时间窗" in issue for issue in timing_issues)
    assert any("口型窗重叠" in issue for issue in timing_issues)
    near_overlap = [
        _dialogue("N1", "角色A", "好。", "0.0-1.0秒"),
        _dialogue("N2", "角色B", "走。", "0.9-2.0秒"),
    ]
    _records, near_overlap_issues = analyze_dialogue_timing(near_overlap, 3)
    assert any("口型窗重叠" in issue for issue in near_overlap_issues)
    tiny_overlap = [
        _dialogue("T1", "角色A", "好。", "0.0-1.005秒"),
        _dialogue("T2", "角色B", "走。", "1.0-2.0秒"),
    ]
    _records, tiny_overlap_issues = analyze_dialogue_timing(tiny_overlap, 3)
    assert any("口型窗重叠" in issue for issue in tiny_overlap_issues)
    slow = _dialogue("SLOW", "角色A", "我们现在慢慢说。", "0.0-4.0秒")
    slow["delivery"] = "语速偏慢，每秒3字"
    slow_records, _issues = analyze_dialogue_timing([slow], 4)
    assert slow_records[0]["speech_rate_cps"] == 3.0

    dialogue_metadata, dialogue_prompt = _valid_dialogue_case()
    dialogue_issues = dialogue_event_issues(
        dialogue_metadata,
        expected_events=[{
            "ref": "DX1", "kind": "台词", "speaker": "角色A", "text": "你根本没有回来。",
        }],
        visible_characters=["角色A", "角色B"],
        full_prompt=dialogue_prompt,
        audio_enabled=True,
        duration=4,
    )
    assert not dialogue_issues, dialogue_issues

    interrupted, interrupted_prompt = _valid_dialogue_case()
    interrupted["dialogue_events"][0].update({
        "conversation_mode": "interrupted",
        "response_latency": "立即",
        "overlap_or_interrupt_window": "none",
        "conversation_source_basis": "源文以破折号停句",
    })
    interrupted_issues = dialogue_event_issues(
        interrupted, visible_characters=["角色A", "角色B"],
        full_prompt=interrupted_prompt, audio_enabled=True, duration=4,
    )
    assert any("非顺序轮次必须写" in issue for issue in interrupted_issues)

    overlapping, overlapping_prompt = _valid_dialogue_case()
    overlapping["dialogue_events"][0].update({
        "conversation_mode": "overlap",
        "response_latency": "0.1秒",
        "overlap_or_interrupt_window": "1.6-1.8秒",
        "conversation_source_basis": "源文写角色B话音未落，角色A已经开口",
    })
    overlapping_issues = dialogue_event_issues(
        overlapping, visible_characters=["角色A", "角色B"],
        full_prompt=overlapping_prompt, audio_enabled=True, duration=4,
    )
    assert not overlapping_issues, overlapping_issues

    repeated_subtext, repeated_prompt = _valid_dialogue_case()
    repeated_subtext["dialogue_events"][0]["subtext"] = "你根本没有回来。"
    repeated_issues = dialogue_event_issues(
        repeated_subtext, visible_characters=["角色A", "角色B"],
        full_prompt=repeated_prompt, audio_enabled=True, duration=4,
    )
    assert any("subtext不能复述原台词" in issue for issue in repeated_issues)

    false_stress, false_stress_prompt = _valid_dialogue_case()
    false_stress["dialogue_events"][0]["stress_words"] = ["永远"]
    false_stress_issues = dialogue_event_issues(
        false_stress, visible_characters=["角色A", "角色B"],
        full_prompt=false_stress_prompt, audio_enabled=True, duration=4,
    )
    assert any("stress_words必须逐字来自原台词" in issue for issue in false_stress_issues)

    missing_stress_delivery, missing_stress_prompt = _valid_dialogue_case()
    missing_stress_delivery["dialogue_events"][0]["delivery"] = "低声开口，尾音收紧"
    missing_delivery_issues = dialogue_event_issues(
        missing_stress_delivery, visible_characters=["角色A", "角色B"],
        full_prompt=missing_stress_prompt, audio_enabled=True, duration=4,
    )
    assert any("delivery必须说明重音词" in issue for issue in missing_delivery_issues)

    performance_metadata, performance_prompt = _valid_performance_case()
    assert not performance_contract_issues(
        performance_metadata, performance_prompt, ["角色A"]
    )
    wrong_delta = {"performance_contract": dict(performance_metadata["performance_contract"])}
    wrong_delta["performance_contract"]["emotion_delta"] = 0
    wrong_delta_issues = performance_contract_issues(wrong_delta, performance_prompt, ["角色A"])
    assert any("emotion_delta必须等于" in issue for issue in wrong_delta_issues)
    missing_mask = {"performance_contract": dict(performance_metadata["performance_contract"])}
    missing_mask["performance_contract"]["mask_leak"] = "角色A指节短促泛白"
    missing_mask_issues = performance_contract_issues(missing_mask, performance_prompt, ["角色A"])
    assert any("mask_leak未落实到子镜头组" in issue for issue in missing_mask_issues)

    story_metadata, story_prompt = _valid_story_punch_case()
    assert not story_punch_issues(story_metadata, story_prompt, ["角色A", "角色B"])
    generic_composition = {"story_punch_contract": dict(story_metadata["story_punch_contract"])}
    generic_composition["story_punch_contract"]["composition_priority"] = "画面很有电影感"
    generic_composition_issues = story_punch_issues(
        generic_composition, story_prompt, ["角色A", "角色B"]
    )
    assert any("composition_priority" in issue for issue in generic_composition_issues)
    unmotivated_camera = {"story_punch_contract": dict(story_metadata["story_punch_contract"])}
    unmotivated_camera["story_punch_contract"]["camera_motivation"] = "摄影机缓慢推近角色A"
    unmotivated_camera_issues = story_punch_issues(
        unmotivated_camera, story_prompt, ["角色A", "角色B"]
    )
    assert any("必须说明镜头为何响应" in issue for issue in unmotivated_camera_issues)

    directing_metadata, directing_prompt = _valid_directing_contracts()
    assert not character_scene_objective_issues(
        directing_metadata, directing_prompt, ["角色A", "角色B"]
    )
    assert not relationship_emotion_arc_issues(directing_metadata, directing_prompt)
    assert not sequence_directing_plan_issues(directing_metadata, directing_prompt)
    assert not cut_decision_contract_issues(directing_metadata, directing_prompt)
    assert not prompt_information_budget_issues(directing_metadata, directing_prompt)
    assert not sound_directing_plan_issues(
        directing_metadata, directing_prompt, audio_enabled=True
    )

    bad_objective = dict(directing_metadata)
    bad_objective["character_scene_objective_contract"] = dict(
        directing_metadata["character_scene_objective_contract"], tactic_shift="随便变化"
    )
    assert any("tactic_shift" in issue for issue in character_scene_objective_issues(
        bad_objective, directing_prompt, ["角色A", "角色B"]
    ))
    bad_sequence = dict(directing_metadata)
    bad_sequence["sequence_directing_plan"] = dict(
        directing_metadata["sequence_directing_plan"], sequence_position="random"
    )
    assert any("sequence_position" in issue for issue in sequence_directing_plan_issues(
        bad_sequence, directing_prompt
    ))
    bad_cut = dict(directing_metadata)
    bad_cut["cut_decision_contract"] = dict(
        directing_metadata["cut_decision_contract"], cut_mode="reaction", trigger="画面中不存在的钟声"
    )
    assert any("trigger" in issue for issue in cut_decision_contract_issues(bad_cut, directing_prompt))
    bad_budget = dict(directing_metadata)
    bad_budget["prompt_information_budget"] = dict(
        directing_metadata["prompt_information_budget"], visual_enhancer_limit=3
    )
    assert any("visual_enhancer_limit" in issue for issue in prompt_information_budget_issues(
        bad_budget, directing_prompt
    ))

    leaked_analysis = "16:9动态漫，冷白顶灯照亮角色A手背；inner_emotion=害怕失去，角色A在画面左侧闭口。"
    assert any("内部分析" in issue for issue in direct_copy_prompt_issues(leaked_analysis))
    leaked_chinese_analysis = "16:9动态漫，冷白顶灯照亮角色A手背；潜台词：逼对方承认失约。"
    assert any("内部分析" in issue for issue in direct_copy_prompt_issues(leaked_chinese_analysis))
    leaked_conversation_analysis = "16:9动态漫，冷白顶灯照亮角色A手背；conversation_mode=overlap。"
    assert any("内部分析" in issue for issue in direct_copy_prompt_issues(leaked_conversation_analysis))
    leaked_surface_analysis = "16:9动态漫，冷白顶灯照亮男孩手背；content_visibility=hidden。"
    assert any("内部分析" in issue for issue in direct_copy_prompt_issues(leaked_surface_analysis))

    hidden_surface_metadata, hidden_surface_prompt = _valid_hidden_surface_case()
    assert not prop_functional_surface_contract_issues(
        hidden_surface_metadata, hidden_surface_prompt, required=True
    )
    flipped_prompt = hidden_surface_prompt + " 手机屏幕转向镜头，游戏界面清晰可见。"
    assert any("翻向镜头" in issue for issue in prop_functional_surface_contract_issues(
        hidden_surface_metadata, flipped_prompt, required=True
    ))
    assert any("必须提供" in issue for issue in prop_functional_surface_contract_issues(
        {}, hidden_surface_prompt, required=True
    ))

    readable_metadata = {
        "prop_functional_surface_contract": dict(
            hidden_surface_metadata["prop_functional_surface_contract"],
            camera_half_space="摄影机位于男孩右肩后上方，与男孩处于屏幕同一可见侧",
            camera_visible_surface="肩后俯拍可见手机屏幕和双手边缘",
            content_visibility="readable",
            orientation_lock="手机横屏方向稳定，屏幕持续朝向男孩与其右肩后摄影机",
            fallback_shot="本镜已采用肩后俯拍，不需要另拆展示镜头",
        )
    }
    readable_prompt = hidden_surface_prompt.replace(
        "镜头只见手机深色背壳和侧边框",
        "肩后俯拍可见手机屏幕和双手边缘",
    ).replace(
        "手机横屏方向稳定，背壳持续朝向摄影机",
        "手机横屏方向稳定，屏幕持续朝向男孩与其右肩后摄影机",
    )
    assert not prop_functional_surface_contract_issues(
        readable_metadata, readable_prompt, required=True
    )

    clean_face_prompt = (
        "16:9画幅，写实电影级动态漫短剧，冷青灰旧办公室。角色A在画面右侧中近景，"
        "角色A皮肤保持自然暖灰血色；画面右前方柔和中性暖白主光照亮角色A脸部，额头鼻梁颧骨高光柔和不过曝；"
        "低强度中性补光托住角色A眼窝、鼻翼和下颌，暗部保持干净层次；青灰色只留在后景墙面和衣物边缘轮廓反光，"
        "不渗入角色A面中；墙面旧痕、灰尘和薄雾只存在于中后景，不覆盖角色A皮肤。"
    )
    clean_face_contract = {"skin_tone_protection_contract": {
        "applicable": True, "subjects": "角色A", "protection_mode": "natural_protected",
        "source_allowed_skin_marks": "none", "skin_tone_baseline": "角色A皮肤保持自然暖灰血色",
        "face_light_and_exposure": "画面右前方柔和中性暖白主光照亮角色A脸部，额头鼻梁颧骨高光柔和不过曝",
        "face_fill_shadow_policy": "低强度中性补光托住角色A眼窝、鼻翼和下颌，暗部保持干净层次",
        "environment_color_boundary": "青灰色只留在后景墙面和衣物边缘轮廓反光，不渗入角色A面中",
        "texture_atmosphere_boundary": "墙面旧痕、灰尘和薄雾只存在于中后景，不覆盖角色A皮肤",
        "continuity_lock": "同场跨镜保持角色A自然暖灰肤色和右前方主光方向",
        "fallback": "降低环境青灰饱和度，把薄雾退到后景并保留中性补光",
    }}
    assert not skin_tone_protection_contract_issues(clean_face_contract, clean_face_prompt, ["角色A"], required=True)
    contaminated_prompt = clean_face_prompt + " 青绿色渗入脸部，墙面旧痕覆盖脸。"
    assert any("不得迁移" in issue for issue in skin_tone_protection_contract_issues(
        clean_face_contract, contaminated_prompt, ["角色A"], required=True
    ))
    assert any("必须提供" in issue for issue in skin_tone_protection_contract_issues(
        {}, clean_face_prompt, ["角色A"], required=True
    ))
    wound_metadata = {"skin_tone_protection_contract": dict(
        clean_face_contract["skin_tone_protection_contract"], protection_mode="source_authorized_marks",
        source_allowed_skin_marks="源文明确的角色A左颊新鲜擦伤",
        skin_tone_baseline="角色A左颊新鲜擦伤保留，其他皮肤保持自然暖灰血色",
    )}
    wound_prompt = clean_face_prompt.replace(
        "角色A皮肤保持自然暖灰血色", "角色A左颊新鲜擦伤保留，其他皮肤保持自然暖灰血色"
    )
    assert not skin_tone_protection_contract_issues(wound_metadata, wound_prompt, ["角色A"], required=True)
    neon_metadata = {"skin_tone_protection_contract": dict(
        clean_face_contract["skin_tone_protection_contract"], protection_mode="motivated_color_cast",
        environment_color_boundary="洋红与青色霓虹只留在后景招牌和衣物边缘轮廓反光，不渗入角色A面中",
    )}
    neon_prompt = clean_face_prompt.replace(
        "青灰色只留在后景墙面和衣物边缘轮廓反光，不渗入角色A面中",
        "洋红与青色霓虹只留在后景招牌和衣物边缘轮廓反光，不渗入角色A面中",
    )
    assert not skin_tone_protection_contract_issues(neon_metadata, neon_prompt, ["角色A"], required=True)
    tyndall_metadata = {"skin_tone_protection_contract": dict(
        clean_face_contract["skin_tone_protection_contract"],
        texture_atmosphere_boundary="窗缝丁达尔光束和尘粒只在角色A肩后中后景，不覆盖角色A皮肤",
    )}
    tyndall_prompt = clean_face_prompt.replace(
        "墙面旧痕、灰尘和薄雾只存在于中后景，不覆盖角色A皮肤",
        "窗缝丁达尔光束和尘粒只在角色A肩后中后景，不覆盖角色A皮肤",
    )
    assert not skin_tone_protection_contract_issues(tyndall_metadata, tyndall_prompt, ["角色A"], required=True)
    leaked_skin_analysis = "16:9动态漫，skin_tone_protection_contract=natural_protected，角色A在画面左侧。"
    assert any("内部分析" in issue for issue in direct_copy_prompt_issues(leaked_skin_analysis))

    flat_curve = {"shots": [
        _shot("EC%d" % index, "latent", "中近景", "角色A眉间轻收", "角色A拇指压住杯沿")
        for index in range(1, 5)
    ]}
    for shot in flat_curve["shots"]:
        shot["scene"] = "SC-EMOTION"
        shot["qa_metadata"]["performance_contract"].update({
            "start_intensity": 2,
            "end_intensity": 2,
            "emotion_delta": 0,
        })
        shot["qa_metadata"]["story_punch_contract"] = {
            "picture_punctuation": "角色A拇指压住杯沿",
        }
    flat_curve_result = analyze_package(flat_curve)
    assert any("连续四镜情绪变化量为0" in warning for warning in flat_curve_result["warnings"])
    assert any("连续四镜使用同一记忆帧戏眼" in warning for warning in flat_curve_result["warnings"])

    source_beats = [
        {"type": "action", "text": "角色A站在桌左，角色B停在门边。", "scene": "SC1", "source_ids": ["SRC1"]},
        {
            "type": "dialogue_group", "scene": "SC1", "source_ids": ["SRC2", "SRC3"],
            "turns": [
                {"type": "dialogue", "kind": "台词", "speaker": "角色A", "text": "你回来了。", "speech_duration": 1.2, "refs": ["D1"], "source_ids": ["SRC2"]},
                {"type": "dialogue", "kind": "台词", "speaker": "角色B", "text": "只是说清楚。", "speech_duration": 1.4, "refs": ["D2"], "source_ids": ["SRC3"]},
            ],
        },
        {"type": "action", "text": "门外传来母亲的声音。", "scene": "SC1", "source_ids": ["SRC4"]},
        {"type": "narration", "kind": "OV", "speaker": "母亲", "text": "灯怎么还亮着？", "speech_duration": 1.8, "refs": ["D3"], "scene": "SC1", "source_ids": ["SRC5"]},
        {"type": "action", "text": "角色A把文件推到桌面中央。", "scene": "SC1", "source_ids": ["SRC6"]},
        {"type": "dialogue", "kind": "台词", "speaker": "角色A", "text": "还来得及吗？", "speech_duration": 1.6, "refs": ["D4"], "scene": "SC1", "source_ids": ["SRC7"]},
        {"type": "action", "text": "角色B伸出的手停在桌沿前。", "scene": "SC1", "source_ids": ["SRC8"]},
    ]
    packed_source = _pack_source_actions_with_interactions(source_beats, 15)
    assert len(packed_source) == 3, packed_source
    assert packed_source[0]["source_ids"] == ["SRC1", "SRC2", "SRC3"]
    assert packed_source[1]["source_ids"] == ["SRC4", "SRC5", "SRC6"]
    assert packed_source[2]["source_ids"] == ["SRC7", "SRC8"]
    assert _offscreen_character_mention("母亲", "门外传来母亲的声音。")
    assert _characters_in_source_order("角色A先看向角色B", ["角色B", "角色A"]) == ["角色A", "角色B"]
    return "quality upgrade regression passed"


def _shot(shot_id, tension, shot_size, expression, body):
    return {
        "shot_id": shot_id,
        "subshot_id": shot_id,
        "duration": 4,
        "full_prompt": "生成规格：16:9动态漫。%s，固定机位。" % shot_size,
        "qa_metadata": {
            "source_constraint_basemap": {"tension_curve_role": tension},
            "performance_contract": {
                "tension_intent": tension,
                "primary_expression": expression,
                "primary_body_action": body,
                "eye_focus": shot_id + "视线落向不同位置",
                "voice_or_breath_control": shot_id + "呼吸节奏",
                "readable_image_moment": shot_id + "可读瞬间",
            },
            "dramatic_design": {"coverage_role": shot_id + "_role"},
            "dialogue_events": [],
        },
    }


def _dialogue(ref, speaker, text, time_range):
    return {
        "ref": ref,
        "kind": "台词",
        "speaker": speaker,
        "text": text,
        "time_range": time_range,
        "speaker_visibility": "visible",
        "delivery": "压低声音",
        "breath_pause_plan": "句前0.2秒吸气；无中段气口；句末0.3秒收气",
        "lip_sync": True,
    }


def _valid_hidden_surface_case():
    contract = {
        "applicable": True,
        "prop": "手机",
        "functional_surface": "手机屏幕",
        "user": "男孩",
        "user_view_relation": "手机屏幕朝向男孩本人，男孩视线落在屏幕中心",
        "camera_half_space": "摄影机位于手机背壳外侧的男孩左前方",
        "camera_visible_surface": "镜头只见手机深色背壳和侧边框",
        "grip_contact": "男孩双手横握手机左右短边",
        "interaction_evidence": "双拇指在屏幕内侧低幅点击，屏幕冷光映亮眼睑和指尖",
        "content_visibility": "hidden",
        "orientation_lock": "手机横屏方向稳定，背壳持续朝向摄影机",
        "fallback_shot": "若需展示游戏内容，另拆肩后俯拍镜头",
    }
    prompt = (
        "男孩坐在画面左侧中近景，手机屏幕朝向男孩本人，男孩视线落在屏幕中心；"
        "镜头只见手机深色背壳和侧边框，男孩双手横握手机左右短边；"
        "双拇指在屏幕内侧低幅点击，屏幕冷光映亮眼睑和指尖；"
        "手机横屏方向稳定，背壳持续朝向摄影机。"
    )
    return {"prop_functional_surface_contract": contract}, prompt


def _valid_dialogue_case():
    delivery = "低声开口，重读“根本”时下颌压住，尾音收紧"
    breath = "句前0.2秒吸气；无中段气口；句末0.3秒收气"
    facial = "角色A眼睑停半拍"
    body = "角色A指腹压住信封封口"
    evidence = "角色B先看角色A再垂眼看信封"
    line = "你根本没有回来。"
    event = {
        "ref": "DX1",
        "kind": "台词",
        "speaker": "角色A",
        "text": line,
        "time_range": "0.4-3.2秒",
        "speaker_visibility": "visible",
        "facial_state": facial,
        "body_state": body,
        "delivery": delivery,
        "breath_pause_plan": breath,
        "lip_sync": True,
        "line_function": "pressure",
        "subtext": "逼角色B承认这段关系早已失约",
        "stress_words": ["根本"],
        "subtext_visible_evidence": evidence,
        "turn_relation": "initiate",
        "conversation_mode": "clean_turn",
        "response_latency": "0.4秒",
        "overlap_or_interrupt_window": "none",
        "conversation_source_basis": "源文由角色A先开口施压",
    }
    prompt = (
        "生成规格：16:9动态漫。\n\n"
        "主体与空间锁定：角色A在画面左侧，角色B在右后方。\n\n"
        "主镜头连续规则：固定机位。\n\n"
        "子镜头组：【镜头1｜0.0-4.0秒】角色A口型同步；%s；%s；%s；%s；%s；"
        "角色A（台词）: \"%s\"；句末闭口，落幅信封仍未递出。\n\n"
        "光照、声音与稳定约束：冷白窗光照亮信封纸面。"
    ) % (facial, body, evidence, delivery, breath, line)
    return {"dialogue_refs": ["DX1"], "dialogue_events": [event]}, prompt


def _valid_performance_case():
    contract = {
        "tension_intent": "rising",
        "trigger_event": "角色B说出失约事实",
        "trigger_time": "1.0秒",
        "inner_emotion": "角色A害怕被确认已经遭到抛弃",
        "display_intent": "角色A维持冷静质问以夺回谈话主动",
        "mask_leak": "角色A右手指腹突然压紧信封封口",
        "start_intensity": 2,
        "end_intensity": 4,
        "emotion_delta": 2,
        "primary_expression": "角色A眼睑停半拍后下颌压住",
        "primary_body_action": "角色A肩线不动但右手指腹持续加力",
        "eye_focus": "角色A视线从角色B眼睛滑到信封",
        "reaction_delay": "角色A听完后延迟0.3秒才开口",
        "voice_or_breath_control": "角色A句前短吸气并压低音量",
        "viewer_empathy_anchor": "角色A仍护住没有递出的信封",
        "readable_image_moment": "角色A指腹压住信封而角色B没有伸手",
        "visual_progression": "角色A起幅直视角色B，继而垂眼压住信封，落幅没有递出",
        "suppression_or_release": "角色A把追问压成低声并收住肩线",
        "camera_pressure": "固定机位守住两人之间的桌面留白",
        "scene_pressure": "桌面信封把两人隔在画面左右",
        "end_residue": "角色A口型闭合且右手仍压在信封上",
    }
    timeline_values = [
        contract[key] for key in (
            "mask_leak", "primary_expression", "primary_body_action", "eye_focus",
            "reaction_delay", "voice_or_breath_control", "viewer_empathy_anchor",
            "readable_image_moment", "visual_progression", "suppression_or_release", "end_residue",
        )
    ]
    prompt = (
        "生成规格：16:9动态漫。\n\n"
        "主体与空间锁定：%s。\n\n"
        "主镜头连续规则：%s。\n\n"
        "子镜头组：【镜头1｜0.0-4.0秒】%s。\n\n"
        "光照、声音与稳定约束：冷白窗光稳定；%s。"
    ) % (contract["scene_pressure"], contract["camera_pressure"], "；".join(timeline_values), contract["scene_pressure"])
    return {"performance_contract": contract}, prompt


def _valid_story_punch_case():
    contract = {
        "audience_question": "角色A是否会把信封交给角色B",
        "character_pressure": "角色A想求证承诺却怕信封被拒绝",
        "visible_pressure_object": "角色A右手压住桌面中央未递出的信封",
        "dramatic_turn": "角色B视线第一次从角色A移到信封",
        "picture_punctuation": "两人之间的信封停在桌面中央",
        "composition_priority": "角色A实焦占画面左三分之一，角色B在右后景，中央信封与留白隔开两人",
        "camera_motivation": "固定机位守住中央信封，因为角色B视线转向信封才成为关系落点",
        "end_residue": "角色A右手仍压住信封，角色B视线停在信封上",
    }
    prompt = (
        "生成规格：16:9动态漫。\n\n"
        "主体与空间锁定：%s；%s。\n\n"
        "主镜头连续规则：%s。\n\n"
        "子镜头组：【镜头1｜0.0-4.0秒】%s；%s；角色B视线停半拍后移向信封；%s；落幅两人位置不变。\n\n"
        "光照、声音与稳定约束：冷白窗光照亮信封纸面。"
    ) % (
        contract["composition_priority"], contract["visible_pressure_object"],
        contract["camera_motivation"], contract["dramatic_turn"],
        contract["picture_punctuation"], contract["end_residue"],
    )
    return {"story_punch_contract": contract, "dialogue_events": [{"ref": "DX1"}]}, prompt


def _valid_directing_contracts():
    visible_tactic = "角色A把未递出的信封压在桌面中央"
    end_action = "角色A右手仍压住信封，角色B没有接走"
    turn_trigger = "角色B视线第一次落到信封"
    shared_residue = "两人隔着未递出的信封保持距离"
    motif = "中央信封与桌面留白持续隔开两人"
    blocking = "角色A留在画面左侧，摄影机固定守住角色B右侧反应"
    environment = "窗外冷光被云层短暂压暗，桌面反光随之收窄"
    must_render = "角色B延迟半拍才看向信封"
    metadata = {
        "character_scene_objective_contract": {
            "focus_character": "角色A",
            "scene_objective": "逼角色B明确是否接受信封里的承诺",
            "stakes": "若再次被拒绝，角色A将结束这段关系",
            "obstacle": "角色B回避回答并拒绝触碰信封",
            "active_tactic": "角色A用信封作为交换条件施压",
            "visible_tactic_evidence": visible_tactic,
            "tactic_shift": "角色B仍不接信封后，角色A从追问改用沉默等待",
            "knowledge_gap": "角色A不知道角色B已经看过信中内容",
            "power_state_change": "主动由角色A施压转为角色B以沉默掌握",
            "end_action_state": end_action,
        },
        "relationship_emotion_arc": {
            "participants": "角色A与角色B",
            "start_relation_state": "角色A主动求证，角色B防御回避",
            "conflicting_wants": "角色A要明确承诺，角色B要拖延回答",
            "emotional_misalignment": "角色A压住焦急，角色B用冷静掩饰犹豫",
            "turn_trigger": turn_trigger,
            "power_shift": "主动权从角色A的追问转为角色B的沉默",
            "end_relation_state": "二人由正面求证转为隔物僵持",
            "shared_residue": shared_residue,
        },
        "sequence_directing_plan": {
            "scene_visual_argument": "信封逐渐成为二人无法跨越的关系边界",
            "sequence_position": "break",
            "distance_lens_stage": "延续50mm中近景并第一次停止推近",
            "composition_motif_state": motif,
            "rule_break_or_hold": "打破上一镜推近，改为固定观察沉默代价",
            "blocking_camera_coordination": blocking,
            "environment_beat": environment,
            "handoff": "把下一镜注意力交给角色B仍未伸出的手",
        },
        "cut_decision_contract": {
            "cut_mode": "reaction",
            "trigger": turn_trigger,
            "pre_cut_hold": "角色A说完后保留0.3秒闭口等待",
            "information_gain": "切后首次看见角色B知道信封存在却拒绝触碰",
            "sound_strategy": "保留窗外低风声跨越反应切点",
            "economy_reason": "只保留一次反应切换，避免重复覆盖同一沉默",
            "fallback": "若反应切换不稳，固定双人关系构图完成同一信息",
        },
        "prompt_information_budget": {
            "profile": "dialogue",
            "primary_render_task": "读清角色A施压与角色B延迟反应",
            "must_render": must_render,
            "supporting_visual": "只保留信封和窗外冷光变化",
            "metadata_only": "场景目标、知识差、权力判断和剪辑理由不进正文",
            "visual_enhancer_limit": 1,
            "compression_rule": "优先台词口型、反应、信封状态与落幅，删除重复材质修辞",
        },
        "sound_directing_plan": {
            "primary_source": "角色A近距离低声台词与窗外低风声",
            "source_direction_distance": "角色A台词来自画面左侧近距离，角色B方向保持安静",
            "room_environment_response": "办公室短混响，关门后高频轻微衰减",
            "foreground_background_priority": "台词在前景，窗外低风声压到背景",
            "silence_or_drop": "角色A句末闭口后环境声短降0.3秒",
            "lead_lag_strategy": "窗外低风声延后退出并连接角色B反应",
            "cut_support": "用风声尾音跨越角色B视线转向的反应切点",
        },
    }
    prompt = (
        "生成规格：16:9写实动态漫。\n\n"
        "主体与空间锁定：%s；%s；%s。\n\n"
        "主镜头连续规则：%s。\n\n"
        "子镜头组：【镜头1｜0.0-4.0秒】%s；%s；%s；%s；%s。\n\n"
        "光照、声音与稳定约束：%s；角色A台词来自画面左侧近距离，角色B方向保持安静。"
    ) % (motif, blocking, environment, motif, visible_tactic, turn_trigger, must_render, end_action, shared_residue, environment)
    return metadata, prompt


if __name__ == "__main__":
    print(run())
