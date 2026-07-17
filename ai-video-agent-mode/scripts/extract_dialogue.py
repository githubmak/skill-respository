import re, json, os, sys

EXCLUDE_PREFIXES = ["动作", "场景", "镜头", "时间", "画布"]


def _auto_detect_characters(text):
    chars = set()
    for line in text.split("\n"):
        line = line.strip()
        if not line: continue
        skip = False
        for prefix in EXCLUDE_PREFIXES:
            if line.startswith(prefix + "："):
                skip = True; break
        if skip: continue
        m = re.match(r"^([^：]+)：", line)
        if m:
            name = m.group(1).strip()
            if name and len(name) <= 6 and not re.search(r"[0-9\s]", name):
                chars.add(name)
    return sorted(chars)


def extract(source_path, characters=None, project_config_path=None):

    with open(source_path, "r", encoding="utf-8-sig") as f:
        text = f.read()

    if characters is None and project_config_path and os.path.exists(project_config_path):
        try:
            with open(project_config_path, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
            cl = cfg.get("character_list", [])
            if cl: characters = cl
        except: pass

    if characters is None: characters = _auto_detect_characters(text)

    lines = text.split("\n")
    dialogue_map = {}
    d_count = 0
    ov_count = 0

    for line in lines:
        line = line.strip()
        if not line: continue
        skip = False
        for prefix in EXCLUDE_PREFIXES:
            if line.startswith(prefix):
                skip = True; break
        if skip: continue
        for char in characters + ["旁白"]:
            if line.startswith(char + "：") or line.startswith(char + "（"):
                colon_pos = line.find("：")
                if colon_pos >= 0:
                    t = line[colon_pos + 1:].strip()
                    if char == "旁白":
                        ov_count += 1
                        dialogue_map["OV-%02d" % ov_count] = char + "：" + t
                    else:
                        d_count += 1
                        dialogue_map["D-%02d" % d_count] = char + "：" + t
                    break

    print("[DIALOGUE] Extracted %d dialogue + %d OV lines" % (d_count, ov_count))
    return dialogue_map


def merge_to_shot_plan(shot_plan_path, dialogue_map):
    with open(shot_plan_path, "r", encoding="utf-8-sig") as f:
        sp = json.load(f)
    sp["dialogue_map"] = dialogue_map
    with open(shot_plan_path, "w", encoding="utf-8") as f:
        json.dump(sp, f, ensure_ascii=False, indent=2)
    print("[DIALOGUE] Merged into %s" % shot_plan_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: extract_dialogue.py <source.txt> [shot_plan.json] [project_config.json]")
        sys.exit(1)
    source = sys.argv[1]
    pcfg = sys.argv[3] if len(sys.argv) > 3 else None
    result = extract(source, project_config_path=pcfg)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if len(sys.argv) > 2: merge_to_shot_plan(sys.argv[2], result)
