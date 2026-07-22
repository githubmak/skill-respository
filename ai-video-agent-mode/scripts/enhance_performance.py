"""Performance description quality framework."""
import json, os, re
PERFORMANCE_DIMENSIONS = {
    "character_action": ["面部状态", "呼吸模式", "身体张力", "微动作 / 手势"],
    "lighting": ["光质", "色温", "光源方向", "对演员脸部的具体影响"],
    "dialogue_audio": ["音量", "语调轮廓", "语速与节奏", "气息特征"],
}
VAGUE_PATTERNS = [(r"自然地",""),(r"唯美","光影柔和，构图精致"),(r"氛围感强","光影层次分明，空间纵深清晰"),(r"好看","视觉协调"),(r"漂亮","画面干净")]
SHOT_SIZE_ORDER = {"ECU":1,"CU":2,"MCU":3,"MS":4,"FS":5,"LS":6,"ELS":7}
SHOT_SIZE_CN = {"大特写":1,"特写":2,"中近景":3,"中景":4,"全":5,"全景":6,"大全景":7}
PUSH_IN_KEYWORDS=["push_in","push in","dolly in","推进","推镜","推近","zoom in","向前推","推入","极慢推进"]
MICRO_EXPRESSION_KEYS=["微表情","表情细节","面部肌肉","眼周","口周","瞳孔","眼神","眉间","咬肌","鼻翼","眼角","眼轮匝肌","嘴角","唇","面部细微"]
MICRO_EXPRESSION_MAX_SHOT=3
MICRO_ACTION_KEYS=["微动作","指尖","手指","指节","喉结","吞咽","手部细节","手指微颤","指尖轻敲","手背血管"]
MICRO_ACTION_MAX_SHOT=4
OCULAR_LIGHT_KEYS=["瞳孔反射","眼神光","虹膜","瞳孔中"]
OCULAR_LIGHT_MAX_SHOT=2
LIP_SYNC_KEYS=["唇部","口型","唇齿","张嘴"]
LIP_SYNC_MAX_SHOT=3
OVOS_KEYS=["OV","OS","旁白","画外音","内心独白","内心声"]
NO_LIP_SAFE_KEYS=["无口型","无需口型","不驱动嘴唇","不驱动口型","无嘴唇同步"]
def should_skip_field(field_name,val):
    if not isinstance(val,str) or not val: return True
    if len(val) < 10: return True
    return False

def _parse_shot_size_num(item):
    raw = (item.get("shot_size","") or item.get("shot_size_text","") or "").strip().split("(")[0].strip()
    if raw in SHOT_SIZE_ORDER: return SHOT_SIZE_ORDER[raw]
    if raw in SHOT_SIZE_CN: return SHOT_SIZE_CN[raw]
    for key in SHOT_SIZE_ORDER:
        if key in raw: return SHOT_SIZE_ORDER[key]
    for key in SHOT_SIZE_CN:
        if key in raw: return SHOT_SIZE_CN[key]
    return None

def _has_push_in(item):
    mt = item.get("movement_type","")
    if isinstance(mt,str) and mt.lower() in ("push_in","dolly in","push in"): return True
    cam = item.get("camera","")
    if isinstance(cam,str):
        for kw in PUSH_IN_KEYWORDS:
            if kw in cam.lower(): return True
    pos = item.get("camera_position","")
    if isinstance(pos,str):
        for kw in PUSH_IN_KEYWORDS:
            if kw in pos.lower(): return True
    return False

def _estimate_final_shot_num(item,start_shot_num):
    if start_shot_num is None: return None
    for field in ["movement_detail","movement_type","camera","camera_position","end_state"]:
        text = item.get(field,"")
        if not isinstance(text,str): continue
        for label,num in {**SHOT_SIZE_ORDER,**SHOT_SIZE_CN}.items():
            for p in ["到"+label,"至"+label,"为"+label,"->"+label,"最终"+label]:
                if p in text: return min(num,start_shot_num)
    if start_shot_num <= 2: return start_shot_num
    return max(start_shot_num - 2, 1)

def _shot_num_to_label(num):
    rev_cn = {v:k for k,v in SHOT_SIZE_CN.items()}
    return rev_cn.get(num,"景别%d" % num)


def _check_shot_size_consistency(item):
    issues = []
    start_shot_num = _parse_shot_size_num(item)
    if start_shot_num is None: return issues
    ssid = item.get("subshot_id","?")
    ca = item.get("character_action","")
    lt = item.get("lighting","")
    da_text = str(item.get("dialogue_audio",""))
    has_push = _has_push_in(item)
    effective_shot = _estimate_final_shot_num(item,start_shot_num) if has_push else start_shot_num
    def _check(keys,max_ok,field_text,detail_label,sev_blocking):
        matched = [k for k in keys if k in field_text]
        if not matched: return
        start_label = _shot_num_to_label(start_shot_num)
        if has_push:
            eff_label = _shot_num_to_label(effective_shot)
            if effective_shot <= max_ok:
                issues.append(("shot_size","info","[%s] 检测到镜头推近(%s->%s)，若%s发生在终点景别时则合理。" % (ssid,start_label,eff_label,detail_label)))
                return
            issues.append((field_text,sev_blocking,"[%s] %s（当前标签%s），镜头虽有推近但终点仍为%s，AI仍无法渲染该级细节。建议提升终点景别至%s或更近，或在movement_detail中标注最终落幅景别" % (ssid,detail_label,start_label,eff_label,_shot_num_to_label(max_ok))))
            return
        suggested = _shot_num_to_label(max_ok)
        issues.append((field_text,sev_blocking,"[%s] %s，但景别为%s，AI无法渲染该级细节。建议升级至%s或更近" % (ssid,detail_label,start_label,suggested)))
    _check(MICRO_EXPRESSION_KEYS,MICRO_EXPRESSION_MAX_SHOT,"shot_size","character_action中提到面部/微表情细节","blocking")
    _check(MICRO_ACTION_KEYS,MICRO_ACTION_MAX_SHOT,"shot_size","character_action中提到手部/喉部微动作","blocking")
    _check(OCULAR_LIGHT_KEYS,OCULAR_LIGHT_MAX_SHOT,"shot_size","lighting中提到瞳孔反射/眼神光","warning")
    _check(LIP_SYNC_KEYS,LIP_SYNC_MAX_SHOT,"shot_size","dialogue_audio中提到唇部/口型细节","warning")
    return issues

def _check_ovos_lip_sync(item):
    text = str(item.get("dialogue_audio","")) + "\n" + str(item.get("full_prompt",""))
    refs = item.get("dialogue_refs", [])
    has_ovos = any(k in text for k in OVOS_KEYS) or any(("OV" in str(r) or "OS" in str(r)) for r in refs)
    if not has_ovos:
        return []
    has_lip = any(k in text for k in LIP_SYNC_KEYS)
    safe = any(k in text for k in NO_LIP_SAFE_KEYS)
    if has_lip and not safe:
        return [("dialogue_audio","blocking","OV/OS 被写成需要口型或嘴唇同步，必须改为画外音/内心声无口型同步")]
    return []


def audit(pkg_path):
    if not os.path.exists(pkg_path): return {"error":"File not found: %s" % pkg_path}
    with open(pkg_path,"r",encoding="utf-8-sig") as f: data = json.load(f)
    items = data.get("shots", data.get("items", []))
    flagged = []; vague_hits = 0; shot_size_issues = []
    for item in items:
        ssid = item.get("subshot_id","?")
        metadata = item.get("qa_metadata", {}) if isinstance(item.get("qa_metadata"), dict) else {}
        roles = metadata.get("performance_priority", {}) if isinstance(metadata.get("performance_priority"), dict) else {}
        primary = str(roles.get("primary", "") or "").strip()
        if primary:
            contract = metadata.get("performance_contract", {}) if isinstance(metadata.get("performance_contract"), dict) else {}
            for field in ("trigger_event", "primary_expression", "primary_body_action", "end_residue"):
                if not str(contract.get(field, "") or "").strip():
                    flagged.append((ssid, "performance_contract", "missing: " + field))
        mode = metadata.get("editorial_mode")
        beats = metadata.get("camera_beat_map")
        if mode not in ("continuous_take", "motivated_sequence"):
            flagged.append((ssid, "editorial_mode", "missing_or_invalid"))
        elif mode == "motivated_sequence":
            if not isinstance(beats, list) or not 1 <= len(beats) <= 3:
                flagged.append((ssid, "camera_beat_map", "must_contain_1_to_3_beats"))
            else:
                for index, beat in enumerate(beats):
                    if not isinstance(beat, dict):
                        flagged.append((ssid, "camera_beat_map", "beat_%d_not_object" % index)); continue
                    missing = [key for key in ("trigger", "time_range", "focus_subject", "framing", "axis_relation", "transition_type", "carryover") if not str(beat.get(key, "") or "").strip()]
                    if missing:
                        flagged.append((ssid, "camera_beat_map", "beat_%d_missing: %s" % (index, "; ".join(missing))))
        for field in ["full_prompt"]:
            val = item.get(field,"")
            if isinstance(val,str):
                for pattern,_ in VAGUE_PATTERNS:
                    if pattern and re.search(pattern,val): flagged.append((ssid,field,"vague: "+pattern)); vague_hits += 1
        for iss in _check_ovos_lip_sync(item):
            flagged.append((ssid,iss[0],"[%s] %s" % (iss[1],iss[2])))
    return {"items_flagged":flagged,"total_flagged":len(flagged),"vague_term_hits":vague_hits,"shot_size_issues":shot_size_issues,"shot_size_blocking":[i for i in shot_size_issues if i[1]=="blocking"],"total_items":len(items)}

def enhance(pkg_path,output_path=None,mode="audit"):
    if not os.path.exists(pkg_path): print("[ENHANCE] Input not found: %s" % pkg_path); return None
    with open(pkg_path,"r",encoding="utf-8-sig") as f: data = json.load(f)
    ar = audit(pkg_path)
    if mode == "audit": print("[ENHANCE] Audit: %d items, %d flagged, %d vague hits, %d shot-size issues" % (ar["total_items"],ar["total_flagged"],ar["vague_term_hits"],len(ar["shot_size_issues"]))); return ar
    if mode == "flag":
        out_dir = os.path.dirname(output_path or pkg_path) or "."
        rp = os.path.join(out_dir,"enhancement_audit.json")
        with open(rp,"w",encoding="utf-8") as f: json.dump(ar,f,ensure_ascii=False,indent=2)
        print("[ENHANCE] Audit report: %s" % rp); return ar
    cleaned_count = 0
    for item in data.get("items",[]):
        for field in ["character_action","axis_space","lighting","full_prompt"]:
            val = item.get(field,"")
            if not isinstance(val,str): continue
            result = val
            for pattern,replacement in VAGUE_PATTERNS:
                if pattern: result = re.sub(pattern,replacement,result)
            if result != val: item[field] = result; cleaned_count += 1
    result_path = output_path or pkg_path
    with open(result_path,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)
    print("[ENHANCE] Cleaned %d items in %s" % (cleaned_count,result_path))
    return data

if __name__ == "__main__":
    import sys
    pkg = sys.argv[1] if len(sys.argv) > 1 else None
    if not pkg: print("usage: enhance_performance.py <prompt_package.json> [output.json] [mode]"); sys.exit(1)
    out = sys.argv[2] if len(sys.argv) > 2 else None
    mode = sys.argv[3] if len(sys.argv) > 3 else "audit"
    result = enhance(pkg,out,mode)
    if isinstance(result,dict) and "total_flagged" in result:
        print(json.dumps({k:v for k,v in result.items() if k != "items_flagged"},ensure_ascii=False,indent=2))
