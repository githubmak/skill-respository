#!/usr/bin/env python3
"""Focused regression tests for direct-copy and episode-level quality upgrades."""

from dialogue_timing import analyze_dialogue_timing
from direct_prompt_compiler import compile_direct_prompt
from episode_director_audit import analyze_package
from generate_shotplan import (
    _characters_in_source_order,
    _offscreen_character_mention,
    _pack_source_actions_with_interactions,
)
from modec_v4 import (
    dialogue_event_issues,
    direct_copy_prompt_issues,
    performance_contract_issues,
    story_punch_issues,
)


def run():
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
    assert not compressed["issues"]
    assert compressed["omitted"] and compressed["omitted"][0]["kind"] == "cinematic"
    assert len(compressed["text"]) <= 80

    hard_overflow = compile_direct_prompt([
        {"kind": "space", "text": "不可删除空间事实" * 30},
    ], max_chars=40)
    assert hard_overflow["issues"] and len(hard_overflow["text"]) > 40

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

    leaked_analysis = "16:9动态漫，冷白顶灯照亮角色A手背；inner_emotion=害怕失去，角色A在画面左侧闭口。"
    assert any("内部分析" in issue for issue in direct_copy_prompt_issues(leaked_analysis))
    leaked_chinese_analysis = "16:9动态漫，冷白顶灯照亮角色A手背；潜台词：逼对方承认失约。"
    assert any("内部分析" in issue for issue in direct_copy_prompt_issues(leaked_chinese_analysis))

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


if __name__ == "__main__":
    print(run())
