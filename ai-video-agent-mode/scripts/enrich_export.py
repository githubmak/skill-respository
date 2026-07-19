import json, os, re, sys

def run(d):
    p = json.load(open(d+"/shot_plan.json","r",encoding="utf-8-sig"))
    shots = {s["shot_id"]:s for s in p["shots"]}
    E = {}; S = {}; C = {}
    for s in json.load(open(d+"/emotion_output.json","r",encoding="utf-8-sig")).get("shots",[]): E[s["shot_id"]] = s
    for s in json.load(open(d+"/scene_output.json","r",encoding="utf-8-sig")).get("analyses",[]): S[s["shot_id"]] = s
    c = json.load(open(d+"/project_config.json","r",encoding="utf-8-sig"))
    st = c.get("visual_style","")
    neg = "画面崩坏面部扭曲多余肢体手指畸形道具漂移服饰闪烁错乱穿模穿帮字幕水印低清画质塑料质感"
    sc = re.compile(r"\|?(叙事功能|虚实|占画面比例|氛围|动作)[：:][^\|]*")
    fc = re.compile(r"(标准|广角|长焦|中长焦|微距|超广角)")
    placeholder = re.compile(r'^正在[待机发].*→.*→|→...→|^等待.*→|现在打字→')
    for a in S.values():
        for k in ["前景","中景","背景"]:
            v = a.get("空间分层",{}).get(k,"")
            if isinstance(v,str): a["空间分层"][k] = sc.sub("",v).strip().rstrip("|").strip()
    for a in C.values():
        fl = a.get("focal_length","")
        if isinstance(fl,str):
            fl = fc.sub("",fl); fl = re.sub(r"[\u4e00-\u9fff]+","",fl)
            a["focal_length"] = (fl.strip()+"mm") if fl and not fl.endswith("mm") else fl if fl else "50mm"
    # 非物理角色后缀列表
    NON_PHYSICAL = ["（消息）","（UI语音）","（UI特效）","（内心独白）"]
    INSERT_SIZES = ["特写","大特写","近景"]
    
    out = []
    for s in shots.values():
        sid = s["shot_id"]; em = E.get(sid,{}); se = S.get(sid,{}); ca = C.get(sid,{})
        sz = ca.get("shot_size","中景"); a = ca.get("angle","平视"); m = ca.get("movement","固定")
        if isinstance(sz,dict): sz = sz.get("层级","中景")
        if isinstance(a,dict): a = a.get("角度","平视")
        if isinstance(m,dict): m = m.get("类型","固定")
        f = ca.get("focal_length","50mm")
        if isinstance(f,dict): f = f.get("焦段","50mm")
        sp = se.get("空间分层",{})
        fg = (sp.get("前景","") or "")[:30]; mg = (sp.get("中景","") or "")[:40]; bg = (sp.get("背景","") or "")[:30]
        mg = re.sub(r"动作:.*","",mg).strip()
        el = em.get("emotion_level","")
        # 因果链过滤占位符
        cr = em.get("expression_causality",""); cs = ""
        if isinstance(cr,dict):
            # 过滤掉值为占位符的条目
            valid = []
            for cn,ct in cr.items():
                ct_str = str(ct)
                if not placeholder.match(ct_str) and len(ct_str) > 5:
                    valid.append(cn+"："+ct_str[:80])
            if valid: cs = " | ".join(valid)
        elif isinstance(cr,str) and cr not in ("无","剧情推进","") and not placeholder.match(cr):
            cs = cr[:80]
        ir = em.get("intonation",""); istr = ""
        if isinstance(ir,str) and ir != "无台词": istr = ir[:60]
        ld = se.get("光影设计",{}); ldesc = ""
        if isinstance(ld,dict):
            lp = [ld.get(k,"") for k in ["主光源","色温","光质","情绪光影类别","轮廓光"] if ld.get(k,"")]
            if lp: ldesc = "，".join([str(x)[:40] for x in lp if x])
        chars = s["characters"]
        # 过滤非物理角色
        phys_chars = [ch for ch in chars if not any(n in ch for n in NON_PHYSICAL)]
        main_ch = phys_chars[0] if phys_chars else ""
        is_insert = any(sz.startswith(ins) for ins in INSERT_SIZES)
        desc = s.get("description","")
        sd = desc
        if "：" in desc:
            sd = desc.split("：")[0].strip()
            sd = re.sub(r"（[^）]*）","",sd).strip()
            if len(sd)<6 and cs:
                fp = cs.split("|")[0].strip()
                if "：" in fp: sd = fp.split("：",1)[1][:30]
            if len(sd)<6: sd = desc[:20]
        out.append({"sid":sid,"scene":s["scene"],"desc":desc,"dia":s.get("dialogue",""),"narr":s.get("narration",[]),"chars":chars,"phys_chars":phys_chars,"main_ch":main_ch,"dur":s["duration"],"sz":sz,"a":a,"m":m,"f":f,"el":el,"fg":fg,"mg":mg,"bg":bg,"cs":cs,"istr":istr,"ldesc":ldesc,"sd":sd,"hs":("系统" in desc or "（UI" in str(chars)),"is_insert":is_insert,"sz_conflict":(sz in ["全景","远景"] and any(x in mg for x in ["面部近景","面部特写","中近景","胸部以上"]))})
    return out, st, neg
if __name__=="__main__":
    if len(sys.argv)<2: print("用法: python enrich_export.py <run_dir>"); sys.exit(1)
    out, st, neg = run(sys.argv[1])
    print(f'处理完成: {len(out)} 镜')
    for s in out[:3]: print(f'{s["sid"]} | 主体={s["main_ch"]} | 特写={s["is_insert"]} | 因果有效={bool(s["cs"])}')
