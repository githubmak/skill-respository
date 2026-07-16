import re, json, os, sys


def extract(source_path, characters=None):
    """Parse source text and extract dialogue_map.

    Args:
        source_path: Path to .txt source file
        characters: List of known character names. If None, auto-detect

    Returns:
        dict: dialogue_map {ref_id: dialogue_text}
    """
    if characters is None:
        characters = ["秦展", "秦成伟", "徐慧", "秦昕", "沈星雨", "陆序", "沈星洲"]

    with open(source_path, "r", encoding="utf-8-sig") as f:
        text = f.read()

    lines = text.split("\n")
    dialogue_map = {}
    d_count = 0
    ov_count = 0
    exclude_prefixes = ["动作", "场景", "镜头", "时间", "画布"]

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Skip non-dialogue lines
        skip = False
        for prefix in exclude_prefixes:
            if line.startswith(prefix):
                skip = True
                break
        if skip:
            continue

        # Match: 角色名：内容 or 角色名（语气）：内容
        for char in characters + ["旁白"]:
            if line.startswith(char + "：") or line.startswith(char + "（"):
                colon_pos = line.find("：")
                if colon_pos >= 0:
                    text = line[colon_pos + 1:].strip()
                    if char == "旁白":
                        ov_count += 1
                        dialogue_map["OV-%02d" % ov_count] = char + "：" + text
                    else:
                        d_count += 1
                        dialogue_map["D-%02d" % d_count] = char + "：" + text
                    break

    print("[DIALOGUE] Extracted %d dialogue + %d OV lines" % (d_count, ov_count))
    return dialogue_map


def merge_to_shot_plan(shot_plan_path, dialogue_map):
    """Merge dialogue_map into shot_plan.json."""
    with open(shot_plan_path, "r", encoding="utf-8-sig") as f:
        sp = json.load(f)
    sp["dialogue_map"] = dialogue_map
    with open(shot_plan_path, "w", encoding="utf-8") as f:
        json.dump(sp, f, ensure_ascii=False, indent=2)
    print("[DIALOGUE] Merged into %s" % shot_plan_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: extract_dialogue.py <source.txt> [shot_plan.json]")
        sys.exit(1)
    source = sys.argv[1]
    result = extract(source)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if len(sys.argv) > 2:
        merge_to_shot_plan(sys.argv[2], result)
