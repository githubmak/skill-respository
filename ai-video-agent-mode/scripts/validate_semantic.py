import json, os, re, sys

def validate(run_dir):
    """语义验证：检查合并后的提示词是否存在逻辑冲突"""
    errors = []
    plan = json.load(open(run_dir+"/shot_plan.json","r",encoding="utf-8"))
    E = {}; S = {}; C = {}
    for s in json.load(open(run_dir+"/emotion_output.json","r",encoding="utf-8")).get("shots",[]): E[s["shot_id"]] = s
    for s in json.load(open(run_dir+"/scene_output.json","r",encoding="utf-8")).get("analyses",[]): S[s["shot_id"]] = s
    for s in json.load(open(run_dir+"/camera_output.json","r",encoding="utf-8")).get("analysis",[]): C[s["shot_id"]] = s
    
    NON_PHYSICAL = ["（消息）","（UI语音）","（UI特效）","（内心独白）"]
    CLOSE_IND = ["面部近景","面部特写","中近景","胸部以上"]
    
    for s in plan["shots"]:
        sid = s["shot_id"]; ca = C.get(sid,{}); se = S.get(sid,{}); em = E.get(sid,{})
        if not ca and not se and not em: continue
        
        # 1. 非物理角色作为机位主体
        chars = s.get("characters",[])
        phys = [c for c in chars if not any(n in c for n in NON_PHYSICAL)]
        if not phys and chars:
            errors.append(f"[违反规则] {sid}: 所有出场角色均为非物理实体（{chars}），机位将无合理参照物")
        
        # 2. 景别矛盾
        sz = ca.get("shot_size","")
        if isinstance(sz,dict): sz = sz.get("层级","")
        mg = se.get("空间分层",{}).get("中景","") or ""
        if sz in ["全景","远景"] and any(x in mg for x in CLOSE_IND):
            errors.append(f"[景别矛盾] {sid}: camera_output 标 {sz}，但 scene_output 中景描述含 \"{mg[:20]}...\"（暗示近景景别）")
        
        # 3. 占位文本残留
        cr = em.get("expression_causality","")
        if isinstance(cr,dict):
            for cn,ct in cr.items():
                ct_str = str(ct)
                if re.search(r"→\.\.\.→|正在[待机发]|等待.*→|现在打字→", ct_str):
                    errors.append(f"[占位文本] {sid}: 因果链含有疑似占位描述 \"{ct_str[:40]}...\"")
        elif isinstance(cr,str) and len(cr) > 5:
            if re.search(r"→\.\.\.→|正在[待机发]", cr):
                errors.append(f"[占位文本] {sid}: 因果链含有疑似占位描述 \"{cr[:40]}...\"")
        
        # 4. 语调占位
        ir = em.get("intonation","")
        if isinstance(ir,str) and ir and ir != "无台词":
            if "复杂" in ir or "无特别" in ir or "带着复杂" in ir:
                errors.append(f"[占位语调] {sid}: 语调标注含有泛化描述 \"{ir[:30]}...\"")
    
    # 5. 连续镜头同景别（需要分组信息，此处简单检查shot_id连续对）
    sorted_shots = sorted(plan["shots"], key=lambda x: x["shot_id"])
    for i in range(len(sorted_shots)-1):
        s1, s2 = sorted_shots[i], sorted_shots[i+1]
        if s1["scene"] != s2["scene"]: continue
        c1 = C.get(s1["shot_id"],{}); c2 = C.get(s2["shot_id"],{})
        sz1 = c1.get("shot_size",""); sz2 = c2.get("shot_size","")
        if isinstance(sz1,dict): sz1 = sz1.get("层级","")
        if isinstance(sz2,dict): sz2 = sz2.get("层级","")
        if sz1 and sz2 and sz1 == sz2:
            errors.append(f"[连续重复] {s1['shot_id']}->{s2['shot_id']}: 连续两镜景别相同（{sz1}），建议至少调整一个镜头的角度")
    
    return errors

if __name__ == "__main__":
    if len(sys.argv) < 2: print("用法: python validate_semantic.py <run_dir>"); sys.exit(1)
    errs = validate(sys.argv[1])
    if errs:
        print(f"[QA 失败] 发现 {len(errs)} 个语义问题：")
        for e in errs: print("  " + e)
        sys.exit(1)
    else:
        print("[QA 通过] 未发现语义问题")
