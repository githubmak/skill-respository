"""Content quality checks."""
import json, os, re
TH = {"character_action":50,"lighting":30,"audio_design":20,"axis_space":30,"camera_position":20,"micro_actions":15}
def quality_check_director(packet_path):
    if not os.path.exists(packet_path): return [(os.path.basename(packet_path),"FILE",0,"not_found")]
    try:
        with open(packet_path,"r",encoding="utf-8-sig") as f: dp = json.load(f)
    except: return [(os.path.basename(packet_path),"JSON",0,"valid_json")]
    items=dp.get("items",[]); issues=[]
    if os.path.getsize(packet_path)<len(items)*1500: issues.append(("ALL","file_size",os.path.getsize(packet_path),">=N*1500"))
    for item in items:
        ssid=item.get("subshot_id","?")
        ab=item.get("action_beats",{})
        if isinstance(ab,dict):
            for k in ["start","transition","contact_or_peak","end_state"]:
                v=ab.get(k,"")
                if isinstance(v,str) and len(v)>0 and len(v)<10: issues.append((ssid,f"ab.{k}",len(v),">=10"))
        for fld in ["axis_space","camera_position","composition","character_action"]:
            v=item.get(fld,"")
            if isinstance(v,str) and re.search(r"X\s*[:=]\s*-?\d+",v): issues.append((ssid,fld+"[XYZ]",0,"use screen dir"))
        for fld,ml in TH.items():
            v=item.get(fld,""); vs=str(v) if v else ""
            if len(vs)<ml: issues.append((ssid,fld,len(vs),f">={ml}"))
        em=item.get("emotion",{})
        if isinstance(em,dict):
            ec=em.get("expression_chain","")
            if len(ec)<15: issues.append((ssid,"emotion.ec",len(ec),">=15"))
    return issues
def quality_check_prompt(path,minc=500):
    if not os.path.exists(path): return [(os.path.basename(path),"FILE",0,"not_found")]
    try:
        with open(path,"r",encoding="utf-8-sig") as f: d=json.load(f)
    except: return [(os.path.basename(path),"JSON",0,"valid_json")]
    issues=[]
    for item in d.get("items",[]):
        ssid=item.get("subshot_id","?"); fp=item.get("full_prompt","")
        if len(fp)<minc: issues.append((ssid,"fp.len",len(fp),f">={minc}"))
    return issues
