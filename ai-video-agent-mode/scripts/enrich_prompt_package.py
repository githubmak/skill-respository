"""
enrich_prompt_package.py - Post-process prompt_package.json after Prompt Composer.
Fixes shot_id, overrides camera/movement/axis/visible_chars from director_pass.
"""
import json, os, sys

def enrich(run_dir):
    pp_path = _find_prompt_package(run_dir)
    dp_path = os.path.join(run_dir, ".cache", "director", "director_pass.json")
    sp_path = os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json")

    if not os.path.exists(pp_path):
        print(f"[ENRICH] No prompt_package.json at {pp_path}")
        return

    pp = json.load(open(pp_path, "r", encoding="utf-8-sig"))
    dp = json.load(open(dp_path, "r", encoding="utf-8-sig")) if os.path.exists(dp_path) else None
    sp = json.load(open(sp_path, "r", encoding="utf-8-sig")) if os.path.exists(sp_path) else None

    dp_idx = {i["subshot_id"]: i for i in dp["items"]} if dp else {}
    
    fixed_shot_id = 0
    fixed_camera = 0
    fixed_axis = 0
    fixed_vis = 0

    for item in pp.get("items", []):
        ssid = item.get("subshot_id", "")
        # Fix 1: Derive shot_id from subshot_id
        parts = ssid.rsplit("-", 1)
        if len(parts) == 2 and item.get("shot_id") != parts[0]:
            item["shot_id"] = parts[0]
            fixed_shot_id += 1

        if ssid not in dp_idx:
            continue
        d = dp_idx[ssid]

        # Fix 2: Camera/movement from director_pass (structural fields)
        for k in ["camera", "movement_type", "movement_detail"]:
            v = d.get(k, "")
            if v and item.get(k) != v:
                item[k] = v
                fixed_camera += 1

        # Fix 3: Axis/space and visible characters (content fields)
        for k in ["axis_space", "visible_characters", "char_entry_exit"]:
            v = d.get(k, "")
            if v and item.get(k, "").strip() != v.strip():
                item[k] = v
                if "axis" in k: fixed_axis += 1
                else: fixed_vis += 1

    json.dump(pp, open(pp_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[ENRICH] shot_id={fixed_shot_id} camera={fixed_camera} axis={fixed_axis} vis={fixed_vis}")


def _find_prompt_package(run_dir):
    candidates = [
        os.path.join(run_dir, ".cache", "composer", "merged.prompt_package.json"),
        os.path.join(run_dir, ".cache", "composer", "prompt_package.json"),
        os.path.join(run_dir, ".cache", "prompt_package.json"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: enrich_prompt_package.py <run_dir>")
        sys.exit(1)
    enrich(sys.argv[1])

# Register as pipeline phase handler
from handler_registry import register_handler
@register_handler("enrich_prompt")
def _enrich_handler(run_dir):
    enrich(run_dir)
