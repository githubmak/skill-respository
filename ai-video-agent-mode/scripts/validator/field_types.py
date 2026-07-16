"""Field type validation."""
import json, os
def validate_field_types(packet_path):
    if not os.path.exists(packet_path): return [(os.path.basename(packet_path),"FILE","","not_found")]
    try:
        with open(packet_path,"r",encoding="utf-8-sig") as f: dp = json.load(f)
    except: return [(os.path.basename(packet_path),"JSON","","parse_error")]
    items = dp.get("items",[]); issues = []
    dict_fields = {"action_beats":["start","transition","contact_or_peak","end_state"],"emotion":["cause","expression_chain","micro_expression","psychology_flow","performance_anchor"],"camera":["lens","angle","movement","axis","transition","virtual_camera"],"performance_plan":["body_action","facial_expression","micro_actions","voice_performance","end_state"],"commercial_quality":["camera_compatibility","continuity_axis","lighting_logic","performance_specificity","action_boundary","shot_size_facing","repair_notes"]}
    for item in items:
        ssid=item.get("subshot_id","?"); sid=item.get("shot_id","")
        if len(sid.split("-"))==3: issues.append((ssid,"shot_id","","two-segment format"))
        for fld,subs in dict_fields.items():
            val=item.get(fld)
            if not isinstance(val,dict): issues.append((ssid,fld,"dict",type(val).__name__))
            else:
                for k in subs:
                    if k not in val: issues.append((ssid,f"{fld}.{k}","exists","missing"))
        da=item.get("dialogue_audio")
        if not isinstance(da,dict): issues.append((ssid,"dialogue_audio","dict",type(da).__name__))
        else:
            t=da.get("timing",{})
            if not isinstance(t,dict): issues.append((ssid,"timing","dict",type(t).__name__))
            else:
                for k in ["char_count","estimated_seconds","available_seconds","status"]:
                    if k not in t: issues.append((ssid,f"timing.{k}","exists","missing"))
            if not isinstance(da.get("dialogue_refs"),list): issues.append((ssid,"dialogue_refs","list",type(da.get("dialogue_refs")).__name__))
    return issues
