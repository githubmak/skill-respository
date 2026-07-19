import json, os, re, sys

def enforce_camera_detail(run_dir):
    """After Phase 6 composer, inject full camera descriptions from director_pass.json
    into every shot's full_prompt. Returns number of fixes applied."""
    
    composer_path = os.path.join(run_dir, ".cache", "composer", "composer_output.json")
    director_path = os.path.join(run_dir, ".cache", "director", "director_pass.json")
    
    if not os.path.exists(composer_path) or not os.path.exists(director_path):
        print("[ENFORCE] Missing input files")
        return 0
    
    with open(director_path, "r", encoding="utf-8-sig") as f:
        director = json.load(f)
    cam_map = {}
    for item in director.get("items", []):
        cam_map[item["subshot_id"]] = item.get("camera", "")
    
    with open(composer_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)
    
    short_types = ["固定", "推", "拉", "摇", "移", "跟", "升", "降", "俯", "仰", "环绕", "甩", "变焦", "旋转", "手持", "穿梭"]
    shot_sizes = ["大特写", "特写", "中近景", "近景", "中景", "全景", "大远景", "远景"]
    
    total = 0
    for s in pkg["shots"]:
        ssid = s["subshot_id"]
        fp = s["full_prompt"]
        full_cam = cam_map.get(ssid, "")
        if not full_cam:
            continue
        
        for ct in short_types:
            # Pattern: "运镜：X。" -> "运镜：full_cam。"
            old = "运镜：" + ct + "。"
            if old in fp:
                fp = fp.replace(old, "运镜：" + full_cam + "。")
                total += 1
            
            # Pattern: "shot_size。X。" -> "shot_size。full_cam。"
            for sz in shot_sizes:
                old2 = sz + "。" + ct + "。"
                if old2 in fp:
                    fp = fp.replace(old2, sz + "。" + full_cam + "。")
                    total += 1
                    break
        
        s["full_prompt"] = fp
    
    # Save
    with open(composer_path, "w", encoding="utf-8") as f:
        json.dump(pkg, f, ensure_ascii=False, indent=2)
    
    # Self-scan
    remaining = 0
    for s in pkg["shots"]:
        fp = s["full_prompt"]
        for ct in short_types:
            if ("运镜：" + ct + "。") in fp:
                remaining += 1
            for sz in shot_sizes:
                if (sz + "。" + ct + "。") in fp:
                    remaining += 1
    
    if remaining:
        print("[ENFORCE] FAIL - %d short cameras still present" % remaining)
    else:
        print("[ENFORCE] PASS - %d fixes, 0 remaining" % total)
    
    return total

if __name__ == "__main__":
    rd = sys.argv[1] if len(sys.argv) > 1 else "."
    enforce_camera_detail(rd)
