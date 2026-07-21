import json, os, re, sys
from collections import Counter

NON_CHARACTER_PREFIXES = {
    "场景", "地点", "时间", "动作", "旁白", "说明", "备注", "镜头", "画面",
    "\u25b3", "SCENE", "一道身影", "整个人", "各有各", "各有各的", "那是猎人",
    "对峙", "缓缓"
}

NON_CHARACTER_FRAGMENTS = [
    "脊背", "下颌", "目光", "眼眸", "唇角", "眼底", "身影", "个人",
    "会议", "学院", "空气", "猎人", "猎物", "所有", "周遭", "对峙", "缓缓"
]

SUBJECT_STARTERS = [
    "微微", "单手", "双手", "坐", "立", "踞", "行", "站", "走",
    "扫", "眯", "掀", "侧目", "枕", "陷", "笑", "问", "说", "接话", "顿住",
    "停住", "架"
]

ACTION_KEYWORD_HINTS = [
    "走", "跑", "奔", "冲", "追", "跳", "跃", "翻", "闪", "躲", "避", "推",
    "拉", "拽", "打", "击", "踢", "撞", "摔", "扑", "挥", "举", "拔", "转",
    "停", "顿", "坐", "站", "立", "抬", "落", "扫", "看", "望", "眯"
]

def detect_source_rules(source_path):
    """Auto-detect characters, action keywords, and script format from source text."""
    with open(source_path, "r", encoding="utf-8") as f:
        text = f.read()
    lines = text.strip().split("\n")
    
    # 1. Extract characters from "人物：" lines
    characters = []
    for line in lines:
        line = line.strip()
        m = re.match(r'^人物[\uff1a:]', line)
        if m:
            char_part = line[m.end():].strip()
            chars = re.split(r'[、，, ]+', char_part)
            for c in chars:
                c = c.strip()
                if c and c not in characters:
                    characters.append(c)
    
    # 2. Also extract characters from dialogue prefixes. Chinese scene headers
    # also use colons, so exclude them before matching speakers.
    dialog_speakers = set()
    for line in lines:
        line = line.strip()
        if _is_scene_header(line):
            continue
        dm = re.match(r'^([^\uff1a:]+?)(\uff08([^\uff09]*)\uff09)?[\uff1a:]', line)
        if dm:
            sp = dm.group(1).strip()
            if _looks_like_character_name(sp):
                dialog_speakers.add(sp)
    for sp in sorted(dialog_speakers):
        if sp not in characters:
            characters.append(sp)
    
    # 3. Extract action keywords from action lines
    action_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith("\u25b3") or line.startswith("\u52a8\u4f5c\uff1a"):
            action_lines.append(line)
            for ch in _extract_action_characters(line):
                if ch not in characters:
                    characters.append(ch)
    
    # Find common 2-4 char substrings that appear in action lines but NOT in dialogue lines
    action_ngrams = Counter()
    for al in action_lines:
        clean = re.sub(r'^\u25b3[\uff1a:]?\s*', '', al)
        clean = re.sub(r'^\u52a8\u4f5c\uff1a\s*', '', clean)
        # Extract 3-6 char phrases as potential keywords
        for i in range(0, len(clean)-2):
            for length in [3, 4, 5]:
                if i + length <= len(clean):
                    phrase = clean[i:i+length]
                    if not re.search(r'[，。、；：！？\s]', phrase):
                        action_ngrams[phrase] += 1
    
    # Filter: keep n-grams that appear >=2 times and contain action-like chars
    action_kw = []
    for phrase, count in action_ngrams.most_common(100):
        has_action_hint = any(h in phrase for h in ACTION_KEYWORD_HINTS)
        if count >= 2 and has_action_hint and not any(p in phrase for p in ["?","!","~","我","你","他","她","啦","啊","吗","吧"]):
            # Prefer shorter substrings of longer phrases
            is_sub = any(phrase != p and phrase in p for p in action_kw)
            if not is_sub:
                action_kw.append(phrase)
        if len(action_kw) >= 25:
            break
    
    # 4. Detect scene header pattern
    scene_headers = []
    has_cn_scene_header = False
    for line in lines:
        line = line.strip()
        if re.match(r'^(?:场景|地点)[\uff1a:]', line):
            has_cn_scene_header = True
            scene_headers.append(line)
        if re.match(r'^\d+-\d+', line) and len(line) < 40:
            scene_headers.append(line)
    
    if has_cn_scene_header:
        scene_pattern = r'^(?:场景|地点)[\uff1a:]'
    elif any(re.match(r'^\d+-\d+', h) for h in scene_headers):
        scene_pattern = r'^\d+-\d+'
    else:
        scene_pattern = r'^SCENE'

    # 5. Check for dialogue speakers not declared in scene headers
    scene_char_set = set(characters[:])
    unlisted = dialog_speakers - scene_char_set - {"动作", "\u25b3", "1-1", "1-2"}
    if unlisted:
        print("[DETECT] WARNING: %d dialogue speakers not in character_list: %s" % (len(unlisted), ", ".join(sorted(unlisted))))
        characters.extend(sorted(unlisted))
    
    return {
        "characters": characters,
        "action_keywords": action_kw,
        "scene_header_pattern": scene_pattern,
        "dialogue_pattern_desc": "\u89d2\u8272\u540d\uff08\u8bed\u6c14\uff09\uff1a\u53f0\u8bcd",
        "_detected_from": source_path
    }

def _is_scene_header(line):
    return bool(
        re.match(r'^(?:场景|地点)[\uff1a:]', line)
        or re.match(r'^\d+-\d+\b', line)
        or re.match(r'^SCENE\b', line, re.I)
    )

def _looks_like_character_name(name):
    name = str(name or "").strip()
    if name == "其他所有人":
        return True
    if not name or name in NON_CHARACTER_PREFIXES:
        return False
    if any(fragment in name for fragment in NON_CHARACTER_FRAGMENTS):
        return False
    if re.match(r'^\d+-\d+$', name):
        return False
    if len(name) > 8:
        return False
    return bool(re.search(r'[\u4e00-\u9fffA-Za-z]', name))

def _extract_action_characters(line):
    clean = re.sub(r'^\u25b3[\uff1a:]?\s*', '', line.strip())
    clean = re.sub(r'^\u52a8\u4f5c\uff1a\s*', '', clean)
    found = []
    starter_alt = "|".join(re.escape(v) for v in SUBJECT_STARTERS)
    for sent in re.split(r"[。；，、\n]", clean):
        sent = sent.strip()
        if not sent:
            continue
        m = re.match(r'([\u4e00-\u9fff]{2,3})(?=(?:' + starter_alt + r'))', sent)
        if not m:
            continue
        cand = m.group(1)
        if _looks_like_character_name(cand) and cand not in found:
            found.append(cand)
    return found

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else ""
    if not src or not os.path.exists(src):
        print(json.dumps({"error": "no source"}, ensure_ascii=False))
        sys.exit(1)
    rules = detect_source_rules(src)
    print(json.dumps(rules, ensure_ascii=False, indent=2))
