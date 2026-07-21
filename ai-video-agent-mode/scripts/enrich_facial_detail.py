"""Enrich director_pass with facial detail from emotion_output.

Called by check_export.py when Check 16 (Facial detail < 70%) fails.
Reads emotion_output.json and merges micro_expression data into director_pass character_action.
"""

import json, os, sys

def enrich_facial_detail(run_dir):
    """Enrich director_pass.json character_action with emotion data."""
    
    emo_path = os.path.join(run_dir, ".cache", "analysis", "emotion_output.json")
    dp_path = os.path.join(run_dir, ".cache", "director", "director_pass.json")
    
    if not os.path.exists(emo_path):
        print("[ENRICH] emotion_output.json not found - cannot enrich")
        return 0
    
    with open(emo_path, "r", encoding="utf-8") as f:
        emo = json.load(f)
    with open(dp_path, "r", encoding="utf-8") as f:
        dp = json.load(f)
    
    emo_map = {item["subshot_id"]: item for item in emo["items"]}
    
    def build_facial_block(emo_item):
        parts = []
        me = emo_item.get("micro_expression", "")
        if me and len(me) > 5:
            parts.append(f"面部细节：{me}")
        for pc in emo_item.get("per_char_actions", []):
            ch = pc.get("character", "")
            ch_me = pc.get("micro_expression", "")
            ch_bpf = pc.get("body_parts_focus", "")
            if ch_me or ch_bpf:
                details = ";".join(filter(None, [ch_me, ch_bpf]))
                parts.append(f"【{ch}】{details}")
        return "。".join(parts) + "。" if parts else ""
    
    facial_kw = ["眼睑","瞳孔","唇线","鼻翼","呼吸","眉毛","嘴角","下颌","睫毛","眼球"]
    enriched = 0
    
    for item in dp.get("items", dp.get("shots", [])):
        ssid = item.get("subshot_id", "")
        e_data = emo_map.get(ssid)
        if not e_data:
            continue
        action = str(item.get("character_action", ""))
        existing = sum(1 for kw in facial_kw if kw in action)
        if existing >= 3:
            continue
        block = build_facial_block(e_data)
        if block:
            item["character_action"] = (action.rstrip("。") + "。" + block) if action else block
            enriched += 1
    
    with open(dp_path, "w", encoding="utf-8") as f:
        json.dump(dp, f, ensure_ascii=False, indent=2)
    
    rich = sum(1 for item in dp.get("items", dp.get("shots", [])) if sum(1 for kw in facial_kw if kw in str(item.get("character_action",""))) >= 3)
    print(f"[ENRICH] {enriched} items enriched, rich={rich}/{len(dp.get('items',dp.get('shots',[])))} ({100*rich/max(1,len(dp.get('items',dp.get('shots',[])))):.0f}%)")
    return enriched


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        enrich_facial_detail(sys.argv[1])
    else:
        print("Usage: python3 enrich_facial_detail.py <run_dir>")
