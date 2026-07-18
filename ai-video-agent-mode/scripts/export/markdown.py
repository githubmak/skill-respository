import json, os, re
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.dirname(__file__))
import sys
sys.path.insert(0, SCRIPT_DIR)


def _extract_section(text, section_name, end_markers=None):
    if end_markers is None:
        end_markers = ["\u3010", "\n\n"]
    # Match section that may be on same line or next line
    pattern = rf"\u3010{re.escape(section_name)}\u3011[ \t]*\n?(.+?)(?={"|".join(re.escape(m) for m in end_markers)}|\Z)"
    m = re.search(pattern, text, re.S)
    return m.group(1).strip() if m else ""


def _extract_line_tag(text, tag):
    pattern = rf"\u3010{re.escape(tag)}\u3011([^\n]+)"
    m = re.search(pattern, text)
    return m.group(1).strip() if m else ""


def _parse_scene_layers(mp):
    scene = _extract_section(mp, "\u573a\u666f\u63cf\u8ff0", ["\u3010\u89d2\u8272\u63cf\u8ff0", "\n\n"])
    layers = {}
    if not scene:
        return layers
    for k in ["\u524d\u666f", "\u4e2d\u666f", "\u80cc\u666f"]:
        m = re.search(rf"{k}[\uff1a:](\s*[^|]+)", scene)
        if m:
            val = m.group(1).strip().rstrip("|").strip()
            if val and val != "\u65e0":
                layers[k] = val
    scene_name = re.search(r"\u573a\u666f[\uff1a:](\s*[^|]+)", scene)
    if scene_name:
        layers["scene_name"] = scene_name.group(1).strip().rstrip("|").strip()
    return layers


def _parse_char_actions(mp):
    char_section = _extract_section(mp, "\u89d2\u8272\u63cf\u8ff0", ["\u3010\u673a\u4f4d\u63cf\u8ff0", "\u3010\u53f0\u8bcd", "\n\n"])
    if not char_section:
        return []
    chars = re.findall(r"\u3010([^\u3011]+)\u3011(.+?)(?=\n\u3010|\Z)", char_section, re.S)
    result = []
    for ch_name, ch_desc in chars:
        info = {"character": ch_name.strip()}
        for subk in ["\u4f4d\u7f6e\u6784\u56fe", "\u670d\u9970", "\u9762\u90e8", "\u80a2\u4f53\u7ec6\u8282"]:
            m = re.search(rf"{subk}[\uff1a:]([^\uff1b]+)", ch_desc)
            if m:
                info[subk] = m.group(1).strip()
        action = re.search(r"\u52a8\u4f5c\u8fc7\u7a0b[\uff08(]\u8d77\u5e45\u2192\u63a8\u8fdb\u2192\u843d\u5e45[\uff09)][\uff1a:]([^\uff1b]+)", ch_desc)
        if action:
            beats = action.group(1).split("\u2192")
            info["beat_start"] = beats[0].strip() if len(beats) > 0 else ""
            info["beat_transition"] = beats[1].strip() if len(beats) > 1 else ""
            info["beat_end"] = beats[2].strip() if len(beats) > 2 else ""
        micro = re.search(r"\u5fae\u8868\u60c5[\uff1a:]([^\uff1b]+)", ch_desc)
        if micro:
            info["micro_expression"] = micro.group(1).strip()
        result.append(info)
    return result


def _clean_visible_characters(vc):
    """Clean visible_characters from Python-like list string."""
    if isinstance(vc, list):
        return "；".join(vc) if vc else ""
    if not vc:
        return vc
    # Extract all (single-)quoted strings
    chars = re.findall(r"'([^']+)'", vc)
    if not chars:
        chars = re.findall(r'"([^"]+)"', vc)
    if chars:
        cleaned = [c.strip().rstrip(",").strip() for c in chars]
        return ", ".join(cleaned)
    return vc.strip().rstrip(",").strip()

_CHAR_NAME_PAT = re.compile(r"^[^：:]{1,6}[：:]")

def _format_beat(character, beat_text, label=""):
    """Format a beat line, avoid duplicating character name."""
    text = beat_text.strip()
    if not text:
        return ""
    # If text already starts with any character name prefix (Name：), dont re-prefix
    if _CHAR_NAME_PAT.match(text):
        if label:
            return f"{label}：{text}"
        return text
    prefix = character if not label else label
    return f"{prefix}：{text}"

def _is_placeholder(text):
    """Check if text is just a placeholder like 落幅，无动作，etc."""
    placeholders = ["落幅", "无动作", "无", "不变"]
    t = text.strip()
    return not t or t in placeholders or len(t) <= 2


def export(pkg_path, plan_path, md_dir, bn="prompt_package",
           emotion_path=None, scene_path=None):
    with open(pkg_path, "r", encoding="utf-8-sig") as f:
        pp = json.load(f)
    with open(plan_path, "r", encoding="utf-8-sig") as f:
        sp = json.load(f)

    dialogue_map = sp.get("dialogue_map", {})
    plan_subshot_index = {}
    for shot in sp.get("shots", []):
        for ss in shot.get("subshots", []):
            plan_subshot_index[ss["subshot_id"]] = ss

    emo_index = {}
    if emotion_path and os.path.exists(emotion_path):
        with open(emotion_path, "r", encoding="utf-8-sig") as f:
            emo_data = json.load(f)
        for e in emo_data.get("items", []):
            emo_index[e.get("subshot_id", "")] = e

    scene_index = {}
    if scene_path and os.path.exists(scene_path):
        with open(scene_path, "r", encoding="utf-8-sig") as f:
            scene_data = json.load(f)
        for s in scene_data.get("items", []):
            scene_index[s.get("subshot_id", "")] = s
        # Also read from "analyses" array format (scene_output.json)
        if not scene_index:
            for a in scene_data.get("analyses", []):
                scene_index[a.get("shot_id", a.get("subshot_id", ""))] = a

    # ==== Director pass fallback ====
    # When prompt_package items lack rendering fields, fall back to director_pass
    dp_index = {}
    dp_path = os.path.join(os.path.dirname(os.path.dirname(plan_path)), "director", "director_pass.json")
    if os.path.exists(dp_path):
        try:
            with open(dp_path, "r", encoding="utf-8-sig") as _f:
                dp_data = json.load(_f)
            for _item in dp_data.get("items", []):
                dp_index[_item.get("subshot_id", "")] = _item
        except Exception:
            pass

    # Fields to enrich from director_pass when missing in prompt_package
    _DP_FIELDS = [
        "axis_space", "camera_position", "camera", "character_action",
        "lighting", "char_entry_exit", "dialogue_audio", "movement_type",
        "movement_detail", "axis_start", "axis_end", "full_prompt",
        "shot_size", "visible_characters", "end_state"
    ]

    items = pp.get("items", [])
    for _ss in items:
        _sid = _ss.get("subshot_id", "")
        _dp = dp_index.get(_sid, {})
        if _dp:
            for _f in _DP_FIELDS:
                _val = _dp.get(_f, "")
                if _val:
                    existing = _ss.get(_f, "")
                    if not existing:
                        _ss[_f] = _val
                    elif _f == "character_action" and isinstance(existing, str) and len(_val) > len(existing):
                        _ss[_f] = _val  # director_pass has richer action descriptions
    scene_shots = {}
    for s in sp.get("shots", []):
        scene_shots.setdefault(s.get("scene", "?"), []).append(s["shot_id"])
    shot_items = {}
    for item in items:
        shot_items.setdefault(item["shot_id"], []).append(item)

    lines = []
    project_name = sp.get("project_name", "")
    if not project_name:
        pcfg = os.path.join(os.path.dirname(os.path.dirname(plan_path)), "project_config.json")
        if os.path.exists(pcfg):
            try:
                with open(pcfg, "r", encoding="utf-8-sig") as _f:
                    cfg = json.load(_f)
                project_name = cfg.get("project_name", "")
            except Exception:
                pass
    if not project_name:
        # plan_path is at: .../project_dir/_run_TIMESTAMP/.cache/orchestrator/shot_plan.json
        # Go up: orchestrator -> .cache -> _run -> project_dir
        p = os.path.dirname(os.path.dirname(os.path.dirname(plan_path)))
        run_parent = os.path.dirname(p)
        project_name = os.path.basename(run_parent) or "项目"
    canvas = sp.get("canvas", "16:9")
    visual_style = sp.get("visual_style", "") or pp.get("visual_style", "")
    if not visual_style and items:
        first_line = items[0].get("merged_full_prompt", "").split("\n")[0]
        if first_line.startswith("\u89c6\u89c9\u98ce\u683c\uff1a"):
            visual_style = first_line.replace("\u89c6\u89c9\u98ce\u683c\uff1a", "").strip()
    style_short = visual_style[:40] + "..." if len(visual_style) > 40 else visual_style

    lines.append(f"# {project_name} AI\u89c6\u9891\u63d0\u793a\u8bcd\u5305")
    lines.append("")
    lines.append(f"\u753b\u5e45\uff1a{canvas} | \u98ce\u683c\uff1a{style_short}")
    lines.append(f"\u4e3b\u955c\u5934\uff1a{len(sp.get('shots',[]))} | \u5b50\u955c\u5934\uff1a{len(items)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for scene, sids in scene_shots.items():
        lines.append(f"## {scene}")
        lines.append("")
        for sid in sids:
            subs = shot_items.get(sid, [])
            if not subs:
                continue
            dur_total = round(sum(float(ss.get("duration", 0) or 0) for ss in subs), 1)
            lines.append(f"### {sid}\uff08{dur_total}s\uff0c{len(subs)}\u4e2a\u955c\u5934\uff09")
            lines.append("")

            for ss in subs:
                mp = ss.get("merged_full_prompt", "") or ss.get("full_prompt", "")
                dur = float(ss.get("duration", 0))
                ssid = ss["subshot_id"]

                dialogue_text = _extract_line_tag(mp, "\u53f0\u8bcd")
                tone_text = _extract_line_tag(mp, "\u53f0\u8bcd\u8bed\u6c14")
                char_actions = _parse_char_actions(mp)
                scene_layers = _parse_scene_layers(mp)

                # Negative prompt: directly from mp
                neg_prompt = ""
                neg_idx = mp.find("\u3010\u8d1f\u9762\u63d0\u793a\u8bcd\u3011")
                if neg_idx >= 0:
                    neg_prompt = mp[neg_idx + 7:].strip()
                    # Find next section or end
                    next_idx = re.search(r"\u3010[^\u3011]+\u3011", neg_prompt)
                    if next_idx:
                        neg_prompt = neg_prompt[:next_idx.start()].strip()
                neg_prompt = neg_prompt.replace("\n", " ").strip()
                # Fallback: use global_negative from item
                if not neg_prompt:
                    neg_prompt = (ss.get("global_negative", "") or "").strip()

                # Dialogue fallback via dialogue_map
                if not dialogue_text:
                    pss = plan_subshot_index.get(ssid, {})
                    drefs = pss.get("dialogue_refs", [])
                    resolved = []
                    for dr in drefs:
                        dt = dialogue_map.get(dr, "")
                        if dt:
                            resolved.append(dt)
                    if resolved:
                        dialogue_text = "\uff1b".join(resolved)

                # Atmosphere label
                atmos = "\u00b7\u5348\u540e"
                if tone_text and "\u00b7" in tone_text:
                    parts = tone_text.split("\u00b7")
                    if len(parts) > 1 and len(parts[1]) <= 6:
                        atmos = "\u00b7" + parts[1]

                # --- Build output ---
                lines.append(f"#### **\u5b50\u955c\u5934 {ssid}** **\u65f6\u957f**\uff1a{int(dur)}\u79d2 | {atmos}")

                # Shot size
                sz = (ss.get("shot_size", "") or "").strip()
                if sz:
                    lines.append(f"> **\u666f\u522b**\uff1a{sz}\u3002")
                    lines.append(f">")

                # Camera position
                cp = (ss.get("camera_position", "") or "").strip()
                if cp:
                    lines.append(f"> **\u673a\u4f4d**\uff1a{cp}\u3002")
                    lines.append(f">")

               # Camera movement
                # Prefer movement_type + movement_detail over generic "camera" field
                mt = (ss.get("movement_type", "") or "").strip()
                md = (ss.get("movement_detail", "") or "").strip()
                if mt and mt != "fixed" and md:
                    cam = f"{md}"
                else:
                    cam = (ss.get("camera", "") or "").strip()
                if cam:
                    lines.append(f"> **\u8fd0\u955c**\uff1a{cam}\u3002")
                    lines.append(f">")

                # Axis + space
                axis = (ss.get("axis_space", "") or "").strip()
                space_parts = []
                if axis:
                    space_parts.append(axis)
                if scene_layers.get("scene_name"):
                    space_parts.append(f"\u573a\u666f\uff1a{scene_layers['scene_name']}")
                if space_parts:
                    lines.append(f"> **\u8f74\u7ebf\u4e0e\u7a7a\u95f4**\uff1a{' | '.join(space_parts)}\u3002")
                               # Scene layers
                layer_parts = []
                # Enrich from scene_index spatial_layers if available
                if ssid in scene_index and scene_index[ssid].get("spatial_layers"):
                    scene_sl = scene_index[ssid]["spatial_layers"]
                    key_map = {"foreground": "前景", "midground": "中景", "background": "背景"}
                    for eng, zh in key_map.items():
                        val = scene_sl.get(eng, "")
                        if val and zh not in scene_layers:
                            scene_layers[zh] = val
                for lk in ["前景", "中景", "背景"]:
                    val = scene_layers.get(lk, "")
                    if val:
                        layer_parts.append(f"{lk}={val}")
                if layer_parts:
                    lines.append(f">")
                    lines.append(f"> **场景层次**：{' | '.join(layer_parts)}。")
                lines.append(f">")

# Visible characters
                vc = _clean_visible_characters(ss.get("visible_characters", "") or "")
                entry_exit = ss.get("char_entry_exit", "") or ""
                if vc:
                    vc_text = vc
                    if entry_exit:
                        vc_text += f" (\u5165\u51fa\u753b\uff1a{entry_exit})"
                    lines.append(f"> **\u53ef\u89c1\u4eba\u7269**\uff1a{vc_text}\u3002")
                    lines.append(f">")

                # Action process
                lines.append(f"> **\u52a8\u4f5c\u8fc7\u7a0b**\uff1a")
                if char_actions:
                    t_start = max(1, int(dur * 0.2))
                    t_end = max(1, int(dur * 0.15))
                    t_mid = max(t_start + 1, int(dur - t_end))

                    # \u8d77\u5e45
                    start_parts = []
                    for ch in char_actions:
                        bs = ch.get("beat_start", "")
                        if bs:
                            formatted = _format_beat(ch["character"], bs)
                            if formatted:
                                start_parts.append(formatted)
                    if start_parts:
                        lines.append(f"> \u8d77\u5e45\u753b\u9762\uff080~{t_start}s\uff09\u2014\u2014{'  '.join(start_parts[:3])}\u3002")
                    else:
                        lines.append(f"> \u8d77\u5e45\u753b\u9762\uff080~{t_start}s\uff09\u2014\u2014\u89d2\u8272\u5904\u4e8e\u521d\u59cb\u59ff\u6001\u3002")

                    # \u52a8\u4f5c\u63a8\u8fdb
                    lines.append(f"> \u52a8\u4f5c\u63a8\u8fdb\uff08{t_start}~{t_mid}s\uff09\u2014\u2014")
                    for ch in char_actions:
                        ch_parts = []
                        bt = ch.get("beat_transition", "")
                        if bt:
                            ch_parts.append(bt)
                        face = ch.get("\u9762\u90e8", "")
                        if face:
                            ch_parts.append(f"\u8868\u60c5\uff1a{face}")
                        me = ch.get("micro_expression", "")
                        if me:
                            ch_parts.append(f"\u5fae\u8868\u60c5\uff1a{me}")
                        bd = ch.get("\u80a2\u4f53\u7ec6\u8282", "")
                        if bd:
                            ch_parts.append(f"\u80a2\u4f53\uff1a{bd}")
                        if ch_parts:
                            lines.append(f"> \u3010{ch['character']}\u3011\uff1a{'  '.join(ch_parts)}\u3002")
                    # Narrative
                    all_beats = [c.get("beat_transition", "") for c in char_actions]
                    narrative = " \u2192 ".join([b for b in all_beats if b])
                    if narrative:
                        lines.append(f"> \u3010\u53d9\u4e8b\u63a8\u8fdb\u3011\uff1a{narrative}\u3002")

                    # \u843d\u5e45
                    end_parts = []
                    for ch in char_actions:
                        be = ch.get("beat_end", "")
                        if be and not _is_placeholder(be):
                            formatted = _format_beat(ch["character"], be)
                            if formatted:
                                end_parts.append(formatted)
                    end_state = ss.get("end_state", "") or ""
                    end_text = f"\u2014\u2014{'  '.join(end_parts[:3])}"
                    if end_state:
                        end_text += f" | \u843d\u5e45\u72b6\u6001\uff1a{end_state}"
                    lines.append(f"> \u843d\u5e45\u753b\u9762\uff08{t_mid}~{int(dur)}s\uff09{end_text}\u3002")
                else:
                    ca = ss.get("character_action", "") or ""
                    if not ca:
                        fgp = ss.get("full_video_generation_prompt", "") or ""
                        if fgp:
                            m2 = re.search(r"动作过程[：:](.*?)(?=\n\S|\Z)", fgp, re.S)
                            if m2:
                                ca = m2.group(1).strip()
                if ca:
                    lines.append(f"> {ca}")
                else:
                    lines.append(f"> 无动作过程数据。")
                lines.append(f">")

                # End state / 落幅
                es = ss.get("end_state", "") or ""
                if es:
                    lines.append(f"> **落幅**：{es}。")
                    lines.append(f">")

                # Dialogue - try to extract actual text from merged_full_prompt
                dialogue_body = ""
                if mp:
                    dia_section = _extract_section(mp, "台词")
                    if dia_section:
                        # Extract the actual spoken text (after the character/tone prefix)
                        dia_lines = [l.strip() for l in dia_section.splitlines() if l.strip()]
                        dialogue_body = " ".join(dia_lines)
                if not dialogue_body and dialogue_text:
                    dialogue_body = dialogue_text

                has_os_in_audio = False
                tone_label = ""
                dia_audio = ss.get("dialogue_audio", "") or ""
                if dia_audio:
                    import re as _re_da
                    tone_match = _re_da.search(r"语气[：:]([^\\n]+)", dia_audio)
                    if tone_match:
                        tone_label = tone_match.group(1).strip()
                    has_os_in_audio = "OV/OS" in dia_audio or "无口型同步" in dia_audio
                
                if dialogue_body:
                    dt = dialogue_body
                    if dt.endswith("。"):
                        dt = dt[:-1]
                    # Determine speaker: prefer dialogue_refs + dialogue_map over visible_characters
                    speaker = ""
                    refs_list = ss.get("dialogue_refs", [])
                    for dr in refs_list:
                        dt_entry = dialogue_map.get(dr, "")
                        if dt_entry and "：" in dt_entry:
                            speaker = dt_entry.split("：")[0].strip()
                            break
                    if not speaker:
                        # Fallback: visible_characters[0]
                        vc = ss.get("visible_characters", "") or ""
                        raw_parts = [c.strip() for c in vc.replace("；", ";").split(";") if c.strip()]
                        # Clean: "沈星雨：白色衬衫..." -> "沈星雨"
                        chars_list = []
                        import re as _re_sp
                        for p in raw_parts:
                            name = _re_sp.split(r"[：:]", p)[0].strip()
                            if name:
                                chars_list.append(name)
                        speaker = chars_list[0] if chars_list else ""
                    # Refine: OS/OV handling
                    if has_os_in_audio:
                        if any(r.startswith("D-SYS-") for r in refs_list):
                            speaker = "系统"
                        label = f"**OS（{speaker}）**" if speaker else "**OS**"
                        lines.append(f"> {label}：{dt}。（无口型同步暗示）")
                    else:
                        is_msg = any("消息" in dt or "打字" in dt or "手机" in dt for dt in refs_list for k in ["消息","打字","手机"])
                        label = f"**对白声音（{speaker}）**" if speaker else "**对白声音**"
                        lines.append(f"> {label}：{dt}。")
                    if tone_label:
                        tl = tone_label.rstrip("。")
                        lines.append(f"> **语气**：{tl}。")
                    lines.append(f">")

                # Lighting
                lighting = (ss.get("lighting", "") or "").strip()
                if not lighting:
                    fgp2 = ss.get("full_video_generation_prompt", "") or ""
                    if fgp2:
                        m3 = re.search(r"光照[：:](.*?)(?=\
\S|\Z)", fgp2, re.S)
                        if m3:
                            lighting = m3.group(1).strip()
                if not lighting:
                    scene_full = _extract_section(mp, "\u573a\u666f\u63cf\u8ff0", ["\u3010\u89d2\u8272\u63cf\u8ff0", "\n\n"])
                    if scene_full:
                        light_match = re.search(r"\u5149\u7ebf[\uff1a:]([^|]+)", scene_full)
                        if light_match:
                            lighting = light_match.group(1).strip()
                if lighting:
                    lines.append(f"> **\u5149\u7167**\uff1a{lighting}\u3002")
                    lines.append(f">")

                # Negative prompt
                if neg_prompt:
                    lines.append(f"> **\u8d1f\u9762\u63d0\u793a\u8bcd**\uff1a{neg_prompt}\u3002")

                lines.append("")

            lines.append("---")
            lines.append("")

    os.makedirs(md_dir, exist_ok=True)
    out_path = os.path.join(md_dir, bn + ".md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[MD] {out_path} ({len(lines)} lines, {len(items)} subshots)")
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("usage: markdown.py <pkg.json> <plan.json> <md_dir> [basename] [--emotion <json>] [--scene <json>]")
        sys.exit(1)
    bn = "prompt_package"
    if len(sys.argv) > 4 and not sys.argv[4].startswith("--"):
        bn = sys.argv[4]
    emotion_path = None
    scene_path = None
    i = 5
    while i < len(sys.argv):
        if sys.argv[i] == "--emotion" and i + 1 < len(sys.argv):
            emotion_path = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--scene" and i + 1 < len(sys.argv):
            scene_path = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    export(sys.argv[1], sys.argv[2], sys.argv[3], bn, emotion_path, scene_path)
