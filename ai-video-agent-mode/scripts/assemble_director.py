import re
"""Assemble structured analysis into cinematic-format director_pass.json.
Uses expanded fields from skill-loaded sub-agents to generate detailed cinematic text."""
import json, os, sys

sys.path.insert(0, os.path.dirname(__file__))


def run(emotion_path, scene_path, camera_path, shot_plan_path, output_path,
        canvas="16:9", visual_style="", shared_settings=""):
    emotion = _load_json(emotion_path) if emotion_path and os.path.exists(emotion_path) else None
    scene = _load_json(scene_path) if scene_path and os.path.exists(scene_path) else None
    camera = _load_json(camera_path) if camera_path and os.path.exists(camera_path) else None
    shot_plan = _load_json(shot_plan_path)
    dialogue_map = shot_plan.get("dialogue_map", {})

    emap = {e["subshot_id"]: e for e in (emotion.get("items", []) if emotion else [])}
    smap = {s["subshot_id"]: s for s in (scene.get("items", []) if scene else [])}
    cmap = {c["subshot_id"]: c for c in (camera.get("items", []) if camera else [])}

    items = []
    shot_index = 0
    for shot in shot_plan.get("shots", []):
        for ss in shot.get("subshots", []):
            shot_index += 1
            ssid = ss["subshot_id"]
            ei = emap.get(ssid, {})
            si = smap.get(ssid, {})
            ci = cmap.get(ssid, {})
            item = _assemble_item(shot_index, ss, ei, si, ci, shot, dialogue_map)
            items.append(item)

    negative = shot_plan.get("negative_prompt",
        "画面崩坏，面部扭曲，多余肢体，手指畸形，道具漂移，服饰闪烁错乱，穿模穿帮，现代物件，字幕水印，低清画质，塑料质感")
    full_prompts = _build_full_prompts(items, canvas, visual_style, shared_settings, negative)

    result = {"items": items, "merged_full_prompts": full_prompts}
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("[ASSEMBLE] %d items written" % len(items))
    return result


def _assemble_item(idx, ss, ei, si, ci, shot, dialogue_map=None):
    """Assemble one subshot into detailed cinematic format using expanded fields."""
    ssid = ss["subshot_id"]
    sid = ss.get("shot_id", ssid.rsplit("-", 1)[0])
    dur = ss.get("duration", 0)
    action = ss.get("base_action", "")
    chars = ss.get("characters", [])
    tone = ss.get("emotion_tone", "平静")
    scene_name = shot.get("scene", "")
    refs = ss.get("dialogue_refs", [])

    # ====== CAMERA FIELDS ======
    lens_v = ci.get("camera_lens_mm", 50); lens_raw = str(lens_v).replace("mm","").replace(" ","").strip() if not isinstance(lens_v, (int,float)) else str(lens_v); lens = re.sub(r"[^0-9.-]", "", lens_raw) if lens_raw else "50"
    rel_pos = ci.get("camera_relative_pos", "前方")
    dist_steps = ci.get("camera_distance_steps", "")
    height_rel = ci.get("camera_height_relative", "齐眼")
    angle_str = ci.get("angle_str", "平视")
    facing = ci.get("camera_facing_desc", "")
    mov_type = ci.get("movement_type", "fixed")
    mov_detail = ci.get("movement_detail", "")
    ma_v = ci.get("movement_arc_deg", 0); mov_arc = str(ma_v).replace("°","").strip() if not isinstance(ma_v, (int,float)) else str(ma_v)
    mov_speed = ci.get("movement_speed", "none")
    axis_start = ci.get("axis_start", "")
    axis_end = ci.get("axis_end", "")
    comp = ci.get("composition", "中央")
    char_entry = ci.get("char_entry", "")
    char_exit = ci.get("char_exit", "")
    lens_effect = ci.get("lens_effect", "正常视域")
    body_ext = ci.get("body_extra", "")
    end_state = ci.get("end_state", "")

    # ====== SCENE FIELDS ======
    bgm = si.get("bgm_style", "")
    amb = si.get("ambient_sound", "")
    sfx = si.get("sfx_timing", "")
    afg = si.get("audio_foreground", "")
    amg = si.get("audio_midground", "")
    abg = si.get("audio_background", "")
    char_pos = si.get("char_positions", [])
    char_wardrobes = si.get("char_wardrobes", [])
    bg_fg = si.get("bg_foreground", "")
    bg_mg = si.get("bg_midground", "")
    bg_bg = si.get("bg_background", "")
    light_type = si.get("light_type", "暖黄室内顶光")
    lt_v = si.get("light_temp", 3200); light_temp = str(lt_v).replace("K","").replace(" ","").strip() if not isinstance(lt_v, (int,float)) else lt_v
    light_dir = si.get("light_direction", "侧前方45度")
    light_hard = si.get("light_hardness", "soft")
    light_effect_primary = si.get("light_effect_primary_char", "")
    light_effect_others = si.get("light_effect_other_chars", "")
    contrast = si.get("color_contrast_desc", "")
    mood = si.get("mood_atmosphere", "")

    # ====== EMOTION FIELDS ======
    em_type = ei.get("emotion_type", tone)
    expr_level = ei.get("expression_level", "micro")
    gaze = ei.get("gaze", "forward")
    micro_exp = ei.get("micro_expression", "none")
    body_tension = ei.get("body_tension", "moderate")
    body_parts = ei.get("body_parts_focus", "")
    voice_tone = ei.get("voice_tone", "")
    beat_start = ei.get("action_beat_start", "")
    beat_trans = ei.get("action_beat_transition", "")
    beat_end = ei.get("action_beat_end", "")
    em_trigger = ei.get("emotion_trigger_short", "")
    perf_note = ei.get("performance_note", "")

    # ====== GENERATE TEXT FIELDS ======

    # 景别
    shot_size_text = ci.get("shot_size", ss.get("shot_size", "MS"))

    # 机位 (expanded)
    if isinstance(dist_steps, (int, float)):
        dist_desc = "约%d步" % int(dist_steps) if dist_steps else "约1.5m"
    else:
        dist_desc = str(dist_steps) if dist_steps else "约1.5m"
    camera_pos_text = "%smm镜头，位于目标%s%s位置，%s，%s，%s。%s" % (
        lens, rel_pos, ("（%s）" % dist_desc) if rel_pos else "",
        height_rel, angle_str + ("%s°" % (int(mov_arc) if mov_arc else 0) if str(mov_arc).replace(".","").replace("°","").strip("-").isdigit() and mov_type != "fixed" else ""),
        facing, lens_effect)

    # 运镜 (expanded)
    if mov_detail:
        movement_text = mov_detail
        if mov_speed and mov_speed != "none" and mov_speed not in movement_text:
            movement_text += "，速度%s" % mov_speed
    else:
        mov_map = {"fixed": "固定镜头", "push_in": "缓慢向前推镜（dolly in）", "pull_out": "缓慢向后拉镜（dolly out）",
                    "track": "横向跟随平移", "pan": "水平摇镜", "tilt": "垂直摇镜", "handheld": "手持摄影，极轻呼吸感晃动"}
        movement_text = mov_map.get(mov_type, "固定镜头")
        if mov_arc and mov_type != "fixed":
            movement_text += "，%s°弧线" % int(mov_arc)

    # 轴线与空间 (expanded with bg layers + mood)
    pos_desc = "；".join(char_pos) if char_pos else "%s在画面%s" % (chars[0] if chars else "人物", "中央偏右")
    bg_parts = []
    if bg_fg: bg_parts.append("前景：%s" % bg_fg)
    if bg_mg: bg_parts.append("中景：%s" % bg_mg)
    if bg_bg: bg_parts.append("背景：%s" % bg_bg)
    bg_text = "；".join(bg_parts)
    axis_text = "%s。%s。场景：%s。" % (action, pos_desc, scene_name)
    if bg_text:
        axis_text += " %s。" % bg_text
    if mood:
        axis_text += "氛围：%s。" % mood

    # 可见人物 (expanded with wardrobe)
    if char_wardrobes:
        char_text = "；".join(char_wardrobes)
    elif chars:
        char_text = "；".join(chars)
    else:
        char_text = "（无可见人物）"

    # 动作过程 (expanded with beats + body parts + performance note)
    action_parts = []
    if beat_start:
        action_parts.append("起：%s" % beat_start)
    if beat_trans:
        action_parts.append("承：%s" % beat_trans)
    if beat_end:
        action_parts.append("转：%s" % beat_end)
    action_text = "%s。%s" % (action, " | ".join(action_parts)) if action_parts else "%s。" % action
    if body_parts:
        action_text += "身体语言：%s。" % body_parts
    if body_ext:
        action_text += "动作细节：%s。" % body_ext
    if perf_note:
        action_text += "表演提示：%s。" % perf_note

    # 台词与声音
    has_ov = any("OV" in r for r in refs)
    if refs:
        lines = []
        for r in refs:
            txt = (dialogue_map or {}).get(r, "")
            if txt:
                lines.append("[%s] %s" % (r, txt))
            else:
                lines.append(r)
        dialogue_text = "\n".join(lines)
        dialogue_text += "\n（%s）\n" % ("OV旁白画外音，无口型同步" if has_ov else "日常对话语气")
    else:
        dialogue_text = "无对白。\n"
    if voice_tone and voice_tone not in ("none", "none_无台词", ""):
        vt = voice_tone.replace("none_","").replace("sharp_","").replace("calm_","").replace("flat_","").replace("warm_","").replace("trembling_","").replace("cold_","").replace("_","")
        if vt and vt != "无台词":
            dialogue_text += "语气：%s。" % vt

    # 光照 (expanded with light effects + contrast + mood)
    light_hard_text = {"soft": "柔光", "hard": "硬光", "mixed": "软硬混合"}.get(light_hard, "柔光")
    lt_num = re.sub(r"[^0-9]", "", str(light_temp)) if light_temp else "3200"; lighting_text = "%s（%sK）为主光源，%s，%s。%s" % (light_type, lt_num if lt_num else "3200", tone, light_dir, light_hard_text)
    if light_effect_primary:
        lighting_text += "主光效果：%s。" % light_effect_primary
    if light_effect_others:
        lighting_text += "辅助光效：%s。" % light_effect_others
    if contrast:
        lighting_text += "色彩对比：%s。" % contrast
    if light_hard == "hard":
        lighting_text += "明暗对比强烈，边缘清晰。"
    elif light_hard == "soft":
        lighting_text += "光线柔和过渡，无明显硬阴影。"
    else:
        lighting_text += "层次分明，软硬结合。"

    # 落幅 (expanded)
    if not end_state:
        end_state = "动作完成后维持当前状态"

    # 入口/出口
    entry_text = ""
    if char_entry:
        entry_text = "入画：%s。" % char_entry
    if char_exit:
        entry_text += "出画：%s。" % char_exit

    return {
        "shot_id": sid, "subshot_id": ssid, "duration": dur,
        "shot_size": shot_size_text,
        "camera_position": camera_pos_text,
        "camera": movement_text,
        "axis_space": axis_text,
        "visible_characters": char_text,
        "character_action": action_text,
        "dialogue_audio": dialogue_text,
        "lighting": lighting_text,
        "char_entry_exit": entry_text,
        "end_state": end_state,
        "full_prompt": "",
    }


def _build_full_prompts(items, canvas, visual_style, shared_settings, negative):
    """Build single merged prompt per shot."""
    merged = []
    shot_groups = {}
    for item in items:
        shot_groups.setdefault(item["shot_id"], []).append(item)

    for sid in sorted(shot_groups.keys()):
        subshots = shot_groups[sid]
        parts = ["【镜头 %s】" % sid, "画布/风格：%s" % canvas]
        if visual_style: parts[-1] += "，%s" % visual_style
        if shared_settings: parts.append("共享设定：%s" % shared_settings)
        parts.append("")

        for i, item in enumerate(subshots):
            parts.append("镜头%d（对应子镜头 %s）：" % (i + 1, item["subshot_id"]))
            for label, key in [("景别", "shot_size"), ("机位", "camera_position"), ("运镜", "camera"),
                               ("轴线与空间", "axis_space"), ("可见人物", "visible_characters"),
                               ("动作过程", "character_action"), ("台词与声音", "dialogue_audio"),
                               ("光照", "lighting"), ("出入画", "char_entry_exit"), ("落幅", "end_state")]:
                val = item.get(key, "")
                if val:
                    parts.append("%s：%s" % (label, val))
            parts.append("")

        parts.append("负面提示词：%s" % negative)
        parts.append("")

        full_text = "\n".join(parts)
        total_dur = sum(it["duration"] for it in subshots)
        for item in subshots:
            item["full_prompt"] = full_text

        merged.append({"shot_id": sid, "duration": total_dur, "full_prompt": full_text})

    return merged


def _load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("usage: assemble_director.py <emotion.json> <scene.json> <camera.json> <shot_plan.json> <output.json>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])