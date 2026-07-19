import json, os, re, sys
from collections import Counter

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
    
    # 2. Also extract characters from dialogue prefixes
    dialog_speakers = set()
    for line in lines:
        line = line.strip()
        dm = re.match(r'^([^\uff1a:]+?)(\uff08([^\uff09]*)\uff09)?[\uff1a:]', line)
        if dm:
            sp = dm.group(1).strip()
            if sp and len(sp) <= 6:
                dialog_speakers.add(sp)
    for sp in sorted(dialog_speakers):
        if sp not in characters and sp not in ["动作", "\u25b3", "1-1", "1-2"]:
            characters.append(sp)
    
    # 3. Extract action keywords from action lines
    action_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith("\u25b3") or line.startswith("\u52a8\u4f5c\uff1a"):
            action_lines.append(line)
    
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
        if count >= 2 and not any(p in phrase for p in ["?","!","~","我","你","他","她","啦","啊","吗","吧"]):
            # Prefer shorter substrings of longer phrases
            is_sub = any(phrase != p and phrase in p for p in action_kw)
            if not is_sub:
                action_kw.append(phrase)
        if len(action_kw) >= 25:
            break
    
    # 4. Detect scene header pattern
    scene_headers = []
    for line in lines:
        line = line.strip()
        if re.match(r'^\d+-\d+', line) and len(line) < 40:
            scene_headers.append(line)
    
    scene_pattern = r'^\d+-\d+' if scene_headers else r'^SCENE'
    
    return {
        "characters": characters,
        "action_keywords": action_kw,
        "scene_header_pattern": scene_pattern,
        "dialogue_pattern_desc": "\u89d2\u8272\u540d\uff08\u8bed\u6c14\uff09\uff1a\u53f0\u8bcd",
        "_detected_from": source_path
    }

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else ""
    if not src or not os.path.exists(src):
        print(json.dumps({"error": "no source"}, ensure_ascii=False))
        sys.exit(1)
    rules = detect_source_rules(src)
    print(json.dumps(rules, ensure_ascii=False, indent=2))
