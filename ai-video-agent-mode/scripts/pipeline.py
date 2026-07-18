import json, os, re, sys, time, openpyxl

def generate_dispatches(export_root, shot_plan):
    if not shot_plan or "shots" not in shot_plan or not shot_plan["shots"]:
        print("WARN: shot_plan is empty, skipping dispatch generation")
        return
    """生成紧凑子Agent调度文件到 {export_root}/.cache/dispatch/
    export_root: 用户指定的导出目录（非时间戳运行目录）
    shot_plan: 已加载的 shot_plan dict
    """
    shots = shot_plan.get("shots", [])
    dialogue_map = shot_plan.get("dialogue_map", {}) or {}
    em, sc, ca = [], [], []
    for s in shots:
        sid = s.get("shot_id", "")
        for ss in s.get("subshots", []) or []:
            ssid = ss.get("subshot_id", "")
            chars = ss.get("characters", [])
            act = ss.get("base_action", ss.get("action", ""))
            refs = ss.get("dialogue_refs", []) or []
            diags = [{"ref": r, "t": dialogue_map.get(r, ""), "tone": ss.get("emotion_tone", "")} for r in refs]
            desc = act or ss.get("visual_intent", "") or s.get("core_action", "")
            dur = ss.get("duration", 0)
            em.append({"id": ssid, "shot_id": sid, "chars": chars, "acts": [act] if act else [], "diags": diags, "narrs": [], "desc": desc, "dur": dur})
            sc.append({"id": ssid, "shot_id": sid, "chars": chars, "acts": [act] if act else [], "desc": desc, "emotion_tone": ss.get("emotion_tone", "")})
            ca.append({"id": ssid, "shot_id": sid, "chars": chars, "desc": desc, "dur": dur, "acts": [act] if act else []})
    dd = os.path.join(export_root, ".cache", "dispatch")
    os.makedirs(dd, exist_ok=True)
    for name, data in [("emotion_data.json", em), ("scene_data.json", sc), ("camera_data.json", ca)]:
        with open(os.path.join(dd, name), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"  {name}: {len(json.dumps(data, ensure_ascii=False))} chars")
        # 写入后回读校验
    for name in ["emotion_data.json", "scene_data.json", "camera_data.json"]:
        fpath = os.path.join(dd, name)
        with open(fpath, "r", encoding="utf-8-sig") as f:
            verify = json.load(f)
        expected = sum(len(s.get("subshots", []) or []) for s in shots)
        if len(verify) != expected:
            raise RuntimeError(f"{name}: 写入{expected}个子镜头, 回读{len(verify)}个 —— 数据截断")
        first_subshot = next((ss for shot in shots for ss in shot.get("subshots", []) if ss.get("subshot_id")), None)
        if first_subshot and verify[0]["id"] != first_subshot["subshot_id"]:
            raise RuntimeError(f"{name}: 首镜头ID不匹配")
    print(f"All dispatch files validated ({len(shots)} shots each)")
    print(f"Dispatch files at {dd}")

def clean(d):
    """清洗：角色过滤+占位符+景别标记"""
    p = json.load(open(os.path.join(d, ".cache", "orchestrator", "shot_plan.json"),"r",encoding="utf-8"))
    ps = {s.get("shot_id", ""):s for s in p["shots"]}
    E,S,C = {},{},{}
    for s in json.load(open(os.path.join(d, ".cache", "analysis", "emotion_output.json"),"r",encoding="utf-8")).get("shots",[]): E[s.get("shot_id", "")] = s
    for s in json.load(open(os.path.join(d, ".cache", "analysis", "scene_output.json"),"r",encoding="utf-8")).get("analyses",[]): S[s.get("shot_id", "")] = s
    for s in json.load(open(os.path.join(d, ".cache", "analysis", "camera_output.json"),"r",encoding="utf-8")).get("analyses",[]): C[s.get("shot_id", "")] = s
    c = json.load(open(os.path.join(d, "project_config.json"),"r",encoding="utf-8"))
    STYLE = c.get("visual_style",""); NEG = c.get("global_negative_prompt", "画面崩坏 面部扭曲 多余肢体 手指畸形 道具漂移 服饰闪烁错乱")
    SCR = re.compile(r"\|?(叙事功能|虚实|占画面比例|氛围|动作)[：:][^\|]*")
    FCR = re.compile(r"(标准|广角|长焦|中长焦|微距|超广角)")
    PLH = re.compile(r"→\.\.\.→|正在[待机发]|等待.*→|现在打字→")
    for a in S.values():
        for k in ["前景","中景","背景"]:
            v = a.get("空间分层",{}).get(k,"")
            if isinstance(v,str): a["空间分层"][k] = SCR.sub("",v).strip().rstrip("|").strip()
    for a in C.values():
        fl = a.get("focal_length","")
        if isinstance(fl,str):
            fl = FCR.sub("",fl); fl = re.sub(r"[\u4e00-\u9fff]+","",fl)
            a["focal_length"] = (fl.strip()+"mm") if fl and not fl.endswith("mm") else fl if fl else "50mm"
    NP = ["（消息）","（UI语音）","（UI特效）","（内心独白）"]
    CI = ["面部近景","面部特写","中近景","胸部以上"]
    out = []
    for s in ps.values():
        sid = s.get("shot_id", ""); em = E.get(sid,{}); se = S.get(sid,{}); ca = C.get(sid,{})
        sz = ca.get("shot_size","中景"); a = ca.get("angle","平视"); m = ca.get("movement","固定")
        if isinstance(sz,dict): sz = sz.get("层级","中景")
        if isinstance(a,dict): a = a.get("角度","平视")
        if isinstance(m,dict): m = m.get("类型","固定")
        f = ca.get("focal_length","50mm")
        if isinstance(f,dict): f = f.get("焦段","50mm")
        axis_rule = ca.get("axis_rule", "")
        sp = se.get("空间分层",{})
        fg = (sp.get("前景","") or "")[:30]; mg = (sp.get("中景","") or "")[:40]; bg = (sp.get("背景","") or "")[:30]
        mg = re.sub(r"动作:.*","",mg).strip()
        facial_4d = em.get("facial_4d", {})
        el = em.get("emotion_level","")
        cr = em.get("expression_causality",""); cs = ""
        if isinstance(cr,dict):
            v = []; [v.append(cn+"："+str(ct)[:80]) for cn,ct in cr.items() if not PLH.search(str(ct)) and len(str(ct))>5]
            if v: cs = " | ".join(v)
        elif isinstance(cr,str) and cr not in ("无","剧情推进","") and not PLH.search(cr): cs = cr[:80]
        ir = em.get("intonation",""); istr = ""
        if isinstance(ir,str) and ir and "无台词" not in ir and "复杂" not in ir: istr = ir[:60]
        ld = se.get("光影设计",{}); lds = ""
        if isinstance(ld,dict):
            lp = [ld.get(k,"") for k in ["主光源","色温","光质","情绪光影类别","轮廓光"] if ld.get(k,"")]
            if lp: lds = "，".join([str(x)[:40] for x in lp if x])
        chars = s.get("characters", []); phys = [ch for ch in chars if not any(n in ch for n in NP)]
        mc = phys[0] if phys else ""
        ins = sz in ["特写","大特写","近景"]
        desc = s.get("description","")
        sd = desc
        if "：" in desc:
            sd = desc.split("：")[0].strip(); sd = re.sub(r"（[^）]*）","",sd).strip()
            if len(sd)<6 and cs:
                fp = cs.split("|")[0].strip()
                if "：" in fp: sd = fp.split("：",1)[1][:30]
            if len(sd)<6: sd = desc[:20]
        szc = sz in ["全景","远景"] and any(x in mg for x in CI)
        out.append({"sid":sid,"scene":s.get("scene", "1"),"desc":desc,"dia":"\n".join([d.get("character","")+"\u300c"+d.get("text","")+"\u300d" for d in s.get("dialogues",[])]) if isinstance(s.get("dialogues"),list) else s.get("dialogue",""),"narr":s.get("narrations",s.get("narration",[])),"chars":chars,"phys":phys,"mc":mc,"dur":s.get("duration", 5),"sz":sz,"a":a,"m":m,"f":f,"el":el,"fg":fg,"mg":mg,"bg":bg,"cs":cs,"is":istr,"ld":lds,"sd":sd,"hs":("系统" in desc or "\uff08UI" in str(chars)),"facial_4d":facial_4d,"axis_rule":axis_rule,"ins":ins,"szc":szc,"facial_4d":facial_4d,"ec_full":em.get("expression_causality",""),"intonation_full":em.get("intonation",""),"pause_annotations":em.get("pause_annotations",""),"surface_vs_deep":em.get("surface_vs_deep",""),"scene_atmosphere":se.get("\u573a\u666f\u6c1b\u56f4",""),"color_mood_raw":se.get("\u8272\u5f69\u57fa\u8c03","")})
        # === FIELD MAPPING: resolve dialogue_refs + beat_start/beat_end ====
    dm_p = p.get("dialogue_map", {})
    for item in out:
        sid = item["sid"]
        s_shot = ps.get(sid, {})
        subshots = s_shot.get("subshots", [])

        # --- dia (台词) field: try 3 sources ---
        if not item.get("dia"):
            dia_lines = []
            for ss in subshots:
                refs = ss.get("dialogue_refs", [])
                char = (ss.get("characters") or [""])[0]
                for ref in refs:
                    text = dm_p.get(ref, "")
                    if not text: continue
                    is_os = (ref.startswith("D-MAIN-"))
                    label = char + ("（OS）" if is_os else "")
                    dia_lines.append(label + "\u300c" + text + "\u300d")
            if dia_lines:
                item["dia"] = "\n".join(dia_lines)

        # --- narr (OS/内心独白) field: try 2 sources ---
        if not item.get("narr"):
            narr_items = []
            for ss in subshots:
                refs = ss.get("dialogue_refs", [])
                char = (ss.get("characters") or [""])[0]
                for ref in refs:
                    if ref.startswith("D-MAIN-"):
                        text = dm_p.get(ref, "")
                        if text:
                            narr_items.append({"character": char, "text": text})
            if narr_items:
                item["narr"] = narr_items

        # --- beat_start: from facial_4d -->
        f4d = item.get("facial_4d", {})
        if f4d and isinstance(f4d, dict):
            start_parts = []
            end_parts = []
            for ck, parts in f4d.items():
                if isinstance(parts, dict) and parts.get("\u773c\u795e"):
                    start_parts.append(ck + "\u5904\u4e8e" + parts["\u773c\u795e"])
                elif ck == "\u773c\u795e" and isinstance(parts, str):
                    start_parts.append("\u89d2\u8272\u5904\u4e8e" + parts)
            if start_parts:
                item["beat_start"] = "; ".join(start_parts)
                item["beat_end"] = "\u52a8\u4f5c\u5b8c\u6210\u540e\u7ef4\u6301\u4e0a\u8ff0\u72b6\u6001\uff0c\u81ea\u7136\u8f6c\u5411\u4e0b\u4e00\u955c\u5934"
                item["desc"] = start_parts[0][:40]
            if not item.get("sd"):
                s_shot2 = ps.get(item["sid"], {})
                sub2 = (s_shot2.get("subshots") or [{}])[0]
                item["sd"] = sub2.get("base_action", "") or ""

    
    # === PATCH: populate chars/phys from subshots ====
    for item in out:
        sid = item["sid"]
        s_shot = ps.get(sid, {})
        subshots = s_shot.get("subshots", [])
        chars = list(set(c for ss in subshots for c in ss.get("characters", []) if c))
        phys = [c for c in chars if not any(suf in c for suf in ["(消息)","(UI语音)","(特效)","（消息）","（UI语音）","（特效）"])]
        item["chars"] = chars or phys
        item["phys"] = phys or chars
        if phys:
            item["mc"] = phys[0]
        elif chars:
            item["mc"] = chars[0]

# === VALIDATION: check cleaned.json integrity ====
    warnings = []
    for item in out:
        sid = item["sid"]
        if not item.get("dia"):
            warnings.append(sid + ": dia empty")
        if not item.get("beat_start"):
            warnings.append(sid + ": beat_start empty")
            item["beat_start"] = item.get("cs", "\u5904\u4e8e\u521d\u59cb\u72b6\u6001")
        if not item.get("beat_end"):
            warnings.append(sid + ": beat_end empty")
            item["beat_end"] = "\u81ea\u7136\u7eed\u63a5\u4e0b\u4e00\u955c\u5934"
        chars = item.get("chars", [])
        phys = item.get("phys", [])
        if not chars and not phys:
            warnings.append(sid + ": chars+phys empty")
    if warnings:
        print("[CLEAN WARN] " + str(len(warnings)) + " issues:")
        for w in warnings[:5]:
            print("  " + w)
        if len(warnings) > 5:
            print("  ... +" + str(len(warnings)-5) + " more")
    return out, STYLE, NEG

def group(shots, max_group_duration):
    """自动分组：同场景连续，每组2-4镜，总时长不超过用户输入上限"""
    if not shots: return []
    scenes = {}
    for s in shots:
        scenes.setdefault(s.get("scene", "1"),[]).append(s)
    gid = 1; groups = []
    for sn in sorted(scenes.keys()):
        sc_shots = scenes[sn]
        i = 0
        while i < len(sc_shots):
            g = []; dur = 0; sizes = []
            while i < len(sc_shots) and dur + sc_shots[i]["dur"] <= max_group_duration and len(g) < 4:
                s = sc_shots[i]
                sizes.append(s.get("sz", "中景"))
                # 同一景别连续3镜则拆分
                if len(g) >= 2 and len(set(sizes[-3:])) == 1 and len(g) >= 2:
                    break
                g.append(s); dur += s.get("dur", 0); i += 1
            if g:
                gname = "场景" + str(sn) + "节拍" + str(len(groups)+1)
                groups.append(("G-%02d" % gid, gname, g))
                gid += 1
    return groups

def validate(groups, shots_dict, E, C):
    """语义审查"""
    errs = []
    for gid, gname, subs in groups:
        for s in subs:
            sid = s.get("sid", "")
            if not s.get("mc", "") and s.get("phys", []) == []:
                errs.append(f"[违反] {sid}: 无物理角色可做机位参照（{s['chars']}）")
            if s.get("szc", False):
                errs.append(f"[矛盾] {sid}: camera={s['sz']} 但 scene描述含近景特征")
            if not s.get("cs", "") and s.get("dia",""):
                # 有台词但无因果链——正常，不报错
                pass
        for i in range(len(subs)-1):
            if subs[i]["sz"] == subs[i+1]["sz"]:
                errs.append(f"[重复] {subs[i]['sid']}->{subs[i+1]['sid']}: 同景别（{subs[i]['sz']}）")
    return errs

def _resolve_export_dir(run_dir, cfg=None):
    cfg = cfg or {}
    configured = (
        cfg.get("final_export_dir")
        or cfg.get("export_dir")
        or cfg.get("export_base")
        or cfg.get("output_dir")
        or ""
    )
    export_dir = configured or os.path.join(run_dir, "exports")
    if not os.path.isabs(export_dir):
        export_dir = os.path.abspath(os.path.join(run_dir, export_dir))
    os.makedirs(export_dir, exist_ok=True)
    return export_dir


def export(groups, STYLE, NEG, run_dir, export_dir=None):
    """导出MD+XLSX"""
    export_dir = export_dir or _resolve_export_dir(run_dir)
    DIST_MAP = {"大特写":"约一米","特写":"约两步","近景":"约两步","中近景":"约两步半","中景":"约三步","全景":"约四步"}
    FRAME_MAP = {"大特写":"面部特写","特写":"胸部以上","近景":"胸部以上","中近景":"腰部以上","中景":"膝部以上","全景":"全身"}
    MOV_PARAMS = {"固定":"固定镜头，极轻微呼吸感手持晃动±0.5cm","跟拍":"慢速跟拍","推镜":"匀速缓慢前推约0.1m/3s","拉远":"极缓慢向后拉远约0.05m/s","横摇":"小幅横摇约20-30度","平移":"横向平移约0.3m/s"}
    MD = []
    MD.append("# AI视频提示词全集")
    MD.append(""); MD.append("共 " + str(len(groups)) + " 个镜头")
    MD.append(""); MD.append("---"); MD.append("")
    for gid, gname, subs in groups:
        total = sum(s.get("dur", 0) for s in subs)
        snum = str(subs[0]["scene"])
        loc = subs[0].get("scene_label","场景") + "\u00b7" + subs[0].get("time_from_scene","白天"); axis = subs[0].get("axis_rule", "")
        MD.append("# 镜头 " + gid); MD.append("")
        MD.append("**场景**：" + loc + "  |  **时长**：" + str(float(total)) + "秒")
        MD.append(""); MD.append("---"); MD.append("")
        ss = "/".join([gid + "-" + str(j+1).zfill(2) for j in range(len(subs))])
        MD.append("## 【镜头 " + gid + "｜用途：完整提示词｜包含子镜头 " + ss + "】 16:9横屏，" + STYLE + "，总时长" + str(float(total)) + "秒。")
        MD.append("")
        for i, s in enumerate(subs):
            rs = gid + "-" + str(i+1).zfill(2)
            sz = s.get("sz", "中景"); mc = s.get("mc", ""); pose = "站姿"
            dist = DIST_MAP.get(sz,"约三步"); frame = FRAME_MAP.get(sz,"")
            extra = ""; cd = ""
            if s.get("ins", False):
                if "手机" in s.get("desc", ""): cd = "手机屏幕正面特写，镜头垂直对准屏幕。"
                else: cd = "镜头位于" + mc + "正面偏右" + dist + "，平视高度（" + pose + "），" + s.get("f", "50mm") + "焦距，" + frame + "取景。"
            else:
                if s.get("hs", False): extra = "，右侧预留系统UI特效空间"
                if "手机" in s.get("desc", ""): extra = "，下方保留手机屏幕空间"
                if len(s.get("phys", [])) >= 2: extra += "，双人同框"
                cd = "镜头位于" + mc + "正面偏右" + dist + "，平视高度（" + pose + "），" + s.get("f", "50mm") + "焦距，" + frame + "取景" + extra + "。"
            MD.append(f"### 子镜头 {rs} | 时长{s['dur']}秒 | {s.get('scene_label','')}·{s.get('time_from_scene','午后')}")
            MD.append("- **景别**：" + sz + "。"); MD.append("")
            MD.append("- **机位**：" + cd); MD.append("")
            MD.append("- **运镜**：" + MOV_PARAMS.get(s.get("m", "固定").replace("镜头",""), s.get("m", "固定")+"镜头") + "。"); MD.append("")
            ax = axis if not s.get("ins", False) else (f"特写镜头有严格Eyeline约束——{s.get('mc','角色')}视线指向画右前方。不能出现视线方向断裂的剪切")
            MD.append("轴线与空间：" + ax + "。空间：前景=" + s.get("fg", "") + "；中景=" + s.get("mg", "") + "；背景=" + s.get("bg", "") + "。")
            MD.append("- **可见人物**：" + "/".join(s.get("phys", []) if s.get("phys", []) else s.get("chars", [])) + "。"); MD.append("")
            dur = s.get("dur", 0)
            t_start = max(1, int(dur * 0.2))
            t_mid = dur - max(1, int(dur * 0.15))
            facial = s.get("facial_4d", {})
            ec_full = s.get("ec_full", "")
            atmos = s.get("scene_atmosphere", "")
            char_count = len(s.get("phys", [])) if s.get("phys", []) else len(s.get("chars", []))

            motion_parts = []
            mc = s.get("mc", "")
            # ------- 起幅 -------
            start_desc = []
            if mc in facial and isinstance(facial[mc], dict):
                fd = facial[mc]
                for k in ["\u773c\u795e", "\u9762\u808c"]:
                    v = fd.get(k, "")
                    if v and v != "N/A":
                        start_desc.append(str(v)[:45])
            if start_desc:
                motion_parts.append(f"起\u5e45\u753b\u9762\uff080~{t_start}s\uff09\u2014\u2014{('\uff0c'.join(start_desc[:2]))}\u3002")
            else:
                motion_parts.append(f"起\u5e45\u753b\u9762\uff080~{t_start}s\uff09\u2014\u2014{s['sd'][:30]}\u3002")

            # ------- \u52a8\u4f5c\u63a8\u8fdb -------
            motion_parts.append(f"\u52a8\u4f5c\u63a8\u8fdb\uff08{t_start}~{t_mid}s\uff09\u2014\u2014")
            if char_count >= 2:
                for ch in (s.get("phys", []) if s.get("phys", []) else s.get("chars", [])):
                    ch_parts = []
                    if ch in facial and isinstance(facial[ch], dict):
                        fd = facial[ch]
                        for k in ["\u773c\u795e", "\u5634\u89d2", "\u547c\u5438", "\u9762\u808c"]:
                            v = fd.get(k, "")
                            if v and v not in ("N/A", "\u65e0\u5b9e\u4f53"):
                                ch_parts.append(str(v)[:50])
                    if ch_parts:
                        _frame = s.get("scene_atmosphere","")
                        _pref = _frame + "\u2014\u2014" if (_frame and ch == s.get("mc", "") and len(_frame) > 3) else ""
                        _desc = "\uff0c".join(ch_parts[:3])
                        _svd = s.get("surface_vs_deep","")
                        _tail = ""
                        if ch == s.get("mc", "") and _svd and "\u6df1\u5c42" in _svd:
                            _deep = _svd.split("\u6df1\u5c42")[-1].strip(" \uff1a\u3002").strip()[:30]
                            if _deep:
                                _tail = "\u2014\u2014" + _deep
                        motion_parts.append(f"\u3010{ch}\u3011\uff1a{_pref}{_desc}{_tail}\u3002")
            else:
                ch = s.get("phys", [])[0] if s.get("phys", []) else (s.get("chars", [])[0] if s.get("chars", []) else "")
                ch_parts = []
                if ch and ch in facial and isinstance(facial[ch], dict):
                    fd = facial[ch]
                    for k in ["\u773c\u795e", "\u5634\u89d2", "\u547c\u5438", "\u9762\u808c"]:
                        v = fd.get(k, "")
                        if v and v not in ("N/A", "\u65e0\u5b9e\u4f53"):
                            ch_parts.append(str(v)[:50])
                if ch_parts:
                    _frame = s.get("scene_atmosphere","")
                    _pref = _frame + "\u2014\u2014" if (_frame and ch == s.get("mc", "") and len(_frame) > 3) else ""
                    _desc = "\uff0c".join(ch_parts[:3])
                    _svd = s.get("surface_vs_deep","")
                    _tail = ""
                    if ch == s.get("mc", "") and _svd and "\u6df1\u5c42" in _svd:
                        _deep = _svd.split("\u6df1\u5c42")[-1].strip(" \uff1a\u3002").strip()[:30]
                        if _deep:
                            _tail = "\u2014\u2014" + _deep
                    motion_parts.append(f"\u3010{ch}\u3011\uff1a{_pref}{_desc}{_tail}\u3002")

            # ------- \u53d9\u4e8b\u63a8\u8fdb -------
            if ec_full and len(ec_full) > 8:
                clean_ec = ec_full.replace("\u2192", "\u2192")
                clean_ec = clean_ec.replace("\u3010", "").replace("\u3011", "")
                clean_ec = re.sub(r"\u6b63\u5728\u5f85\u673a\u2192.*", "", clean_ec)
                clean_ec = re.sub(r"\.\.\.\u2192.*", "", clean_ec)
                clean_ec = clean_ec.strip().strip("\uff1b").strip()
                if clean_ec and len(clean_ec) > 5:
                    motion_parts.append(f"\u3010\u53d9\u4e8b\u63a8\u8fdb\u3011\uff1a{clean_ec[:120]}\u3002")

            # ------- \u843d\u5e45 -------
            sd_text = s.get("sd", "")
            motion_parts.append(f"\u843d\u5e45\u753b\u9762\uff08{t_mid}~{dur}s\uff09\u2014\u2014{s['desc'][:30] if s.get('desc') else '\u52a8\u4f5c\u5b8c\u6210'}\uff0c\u81ea\u7136\u63a5\u7eed\u4e0b\u4e00\u955c\u5934\u3002")

            motion = "\n".join(motion_parts)
            MD.append("动作过程：\n" + motion); MD.append(""); MD.append("")
            if s.get("dia", ""): MD.append(f"- **台词**：{s.get("dia", "").replace(chr(10),"; ")}")
            for n in s.get("narr", []):
                if isinstance(n, dict):
                    _nt = n.get("character", "") + "\u300c" + n.get("text", "") + "\u300d"
                else:
                    _nt = str(n)
                MD.append(f"- **画外声音/OS**（无口型同步）：{_nt}"); MD.append("")
            if s.get("ld", ""): MD.append("- **光照**：" + s.get("ld", "")); MD.append("")
            if s.get("szc", False): MD.append("- **注意**：此镜景别标记为" + s.get("sz", "中景") + "但scene分析描述含近景特征，已标记矛盾。")
            MD.append("")
        MD.append("---"); MD.append("")
        MD.append("### 负面提示词"); MD.append("")
        MD.append("> " + NEG); MD.append("")
        MD.append("---"); MD.append("")
        # 写入后回读校验
    md_path = os.path.join(export_dir, "prompts.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(MD))
    with open(md_path, "r", encoding="utf-8-sig") as f:
        verify = f.read()
    if len(verify) < 100:
        raise RuntimeError(f"prompts.md write may have failed: only {len(verify)} chars")
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "子镜头明细"
    ws.append(["镜头组","子镜头","场景位置","时长(s)","情绪等级","景别","运镜","角色","台词","OS/内心独白","注意事项"])
    for gid, gname, subs in groups:
        for idx, s in enumerate(subs, 1):
            rs = s.get("sid") or (gid + "-" + str(idx).zfill(2))
            ws.append([gid, rs, s.get("scene", "1"), s.get("dur", 0), s.get("el", ""), s.get("sz", "中景"), s.get("m", "固定"), "/".join(s.get("phys", []) if s.get("phys", []) else s.get("chars", [])), s.get("dia", "")[:30], "; ".join([n.get("character","")+":"+n.get("text","")[:15] for n in s.get("narr", [])])[:40]])
    xp = os.path.join(export_dir, "prompts.xlsx")
    try:
        if os.path.exists(xp): os.remove(xp)
        wb.save(xp)
        if not os.path.exists(xp) or os.path.getsize(xp) < 100:
            raise RuntimeError(f"prompts.xlsx write failed")
    except Exception as e:
        xp = os.path.join(export_dir, "prompts_" + str(int(time.time())) + ".xlsx")
        wb.save(xp)
        print(f"XLSX saved to alternate path: {xp} (original failed: {e})")
    MD_lines = str(len(MD)); XLSX_name = os.path.basename(xp)
    print(f"MD: {MD_lines} 行")
    print(f"XLSX: {XLSX_name}")

# ---- CLI入口 ----
if __name__ == "__main__":
    if len(sys.argv) < 2: print("用法: python pipeline.py <run_dir> [--clean|--group|--validate|--export|--all]"); sys.exit(1)
    run_dir = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "--all"
    
    if mode in ("--clean","--all"):
        out, STYLE, NEG = clean(run_dir)
        json.dump(out, open(os.path.join(run_dir, ".cache", "cleaned.json"),"w",encoding="utf-8"), ensure_ascii=False)
        print(f"清洗: {len(out)} 镜")
    
    if mode in ("--group","--all"):
        out = json.load(open(os.path.join(run_dir, ".cache", "cleaned.json"),"r",encoding="utf-8"))
        c = json.load(open(os.path.join(run_dir, "project_config.json"),"r",encoding="utf-8"))
        groups = group(out, float(c.get("max_shot_duration") or 15))
        json.dump([[gid, gname, [s.get("sid", "") for s in subs]] for gid,gname,subs in groups],
                  open(os.path.join(run_dir, ".cache", "groups.json"),"w",encoding="utf-8"), ensure_ascii=False)
        print(f"分组: {len(groups)} 镜头")
        for gid, gname, subs in groups:
            sizes = [s.get("sz", "中景") for s in subs]
            print(f"  {gid}: {[s['sid'] for s in subs]} 总{sum(s['dur'] for s in subs)}s 景别={sizes}")
    
    if mode in ("--validate","--all"):
        out = json.load(open(os.path.join(run_dir, ".cache", "cleaned.json"),"r",encoding="utf-8"))
        groups_data = json.load(open(os.path.join(run_dir, ".cache", "groups.json"),"r",encoding="utf-8"))
        shot_map = {s.get("sid", ""):s for s in out}
        groups = [(gid, gname, [shot_map[sid] for sid in sids]) for gid,gname,sids in groups_data if all(sid in shot_map for sid in sids)]
        errs = validate(groups, shot_map, {}, {})
        if errs:
            print(f"审查: 发现 {len(errs)} 个问题")
            for e in errs[:5]: print("  " + e)
            if len(errs) > 5: print(f"  ...还有 {len(errs)-5} 个")
        else: print("审查: 通过")
    
    if mode in ("--export","--all"):
        out = json.load(open(os.path.join(run_dir, ".cache", "cleaned.json"),"r",encoding="utf-8"))
        groups_data = json.load(open(os.path.join(run_dir, ".cache", "groups.json"),"r",encoding="utf-8"))
        shot_map = {s.get("sid", ""):s for s in out}
        groups = [(gid, gname, [shot_map[sid] for sid in sids]) for gid,gname,sids in groups_data if all(sid in shot_map for sid in sids)]
        c = json.load(open(os.path.join(run_dir, "project_config.json"),"r",encoding="utf-8"))
        STYLE = c.get("visual_style",""); NEG = c.get("global_negative_prompt", c.get("negative_prompt", "")); NEG = "画面崩坏 面部扭曲 多余肢体 手指畸形 道具漂移 服饰闪烁错乱 穿模穿帮 字幕水印 低清画质 塑料质感 像素噪点 人物变形 身体融合 脸型混淆 光影闪烁"
        export(groups, STYLE, NEG, run_dir, _resolve_export_dir(run_dir, c))
