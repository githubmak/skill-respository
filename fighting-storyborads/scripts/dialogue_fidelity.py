#!/usr/bin/env python3
"""Exact dialogue verification against immutable source spans (stdlib only).

The source index must be extracted and attributed from the original text, then
reviewed by a person. This verifier cannot establish extraction completeness or
speaker truth from arbitrary narrative prose. Each delivery layer is checked
separately so engineering/Prompt duplication does not count as repeated speech.
"""
import hashlib
import re

NUM = r'\d+(?:\.\d+)?'
RANGE = rf'({NUM})\s*(?:秒\s*)?[—–~～-]\s*({NUM})\s*秒'

QUOTES = {'“':'”', '「':'」', '『':'』', '"':'"'}
NOTE_LABELS = {'说明','演绎说明','读法','语气','口型','停连','备注','提示','注意','声音','配乐'}


def quoted_end(line, start):
    """Find the closing quote, respecting nested Chinese quotes and escapes."""
    stack = [QUOTES[line[start]]]
    at = start + 1
    while at < len(line):
        char = line[at]
        if char == '\\':
            at += 2
            continue
        if char == stack[-1]:
            stack.pop()
            if not stack:
                return at + 1
        elif char in QUOTES:
            stack.append(QUOTES[char])
        at += 1
    return None


def attributed_header(prefix, speakers):
    prefix = re.sub(r'^[ \t]*[-*][ \t]+', '', prefix).strip()
    prefix = re.sub(rf'^{RANGE}[ \t]*[｜，,][ \t]*', '', prefix)
    for speaker in sorted(set(speakers), key=len, reverse=True):
        if prefix.startswith(speaker):
            meta = prefix[len(speaker):]
            if not meta or meta[0] in ' \t（(在' or re.match(r'对白|OS|OV|旁白|说',meta,re.I):
                return speaker, meta
    # Prompts naturally place an attributed line after an action clause.
    # Require an explicit speech/type marker; do not guess "甲看向乙" as 乙 speaking.
    for speaker in sorted(set(speakers), key=len, reverse=True):
        for boundary in re.finditer(r'[，,]\s*(' + re.escape(speaker) + r')', prefix):
            tail = prefix[boundary.start(1):]
            header = attributed_header(tail, speakers)
            if header and re.search(r'说|对白|OS|OV|旁白', header[1], re.I):
                return header
    match = re.fullmatch(
        rf'(?P<speaker>[\w·]+?)(?P<meta>[ \t]*(?:(?:对白|OS|OV|旁白|说)'
        rf'(?=[ \t（(]|$)|在(?=\d)|[（(]).*)', prefix, re.I)
    if match:
        return match['speaker'], match['meta']
    if re.fullmatch(r'[\w·]+', prefix):
        return prefix, ''
    return None


def voice_records(text, speakers, issues=None):
    """Parse top-level attributions, not colons/quotes inside notes or speech.

    Quoted records may share a line. Unquoted prose remains line-scoped;
    ambiguous attributions are reported for human review, never guessed.
    """
    records = []
    for number, line in enumerate(text.splitlines(), 1):
        at, segment, brackets = 0, 0, []
        while at < len(line):
            char = line[at]
            if char in '（(':
                brackets.append(char)
            elif char in '）)' and brackets:
                brackets.pop()
            elif not brackets and char in QUOTES:
                # Unattributed quotations in performance notes are not dialogue.
                at = quoted_end(line, at) or len(line)
                continue
            elif not brackets and char in '；;。！？!?｜':
                # A timestamp prefix contains ｜; keep it until its first colon.
                if char != '｜' or not re.match(rf'^[ \t]*{RANGE}',line[segment:at]):
                    segment = at + 1
            elif not brackets and char in '：:':
                prefix = line[segment:at].strip()
                header = attributed_header(prefix, speakers)
                value = at + 1
                while value < len(line) and line[value] in ' \t':
                    value += 1
                if prefix in NOTE_LABELS and prefix not in speakers:
                    break
                if header is None:
                    if value < len(line) and line[value] in QUOTES and issues is not None:
                        issues.append((number,'引语前归属无法可靠解析，需人工核对。'))
                    segment = at + 1
                    at += 1
                    continue
                speaker, meta = header
                if value < len(line) and line[value] in QUOTES:
                    end = quoted_end(line, value)
                    if end is None:
                        if issues is not None:
                            issues.append((number,'话语引号未闭合，需人工核对。'))
                        break
                    words = line[value+1:end-1]
                else:
                    # A bare unknown label followed by prose could be a note.
                    if speaker not in speakers and not meta.strip():
                        if issues is not None:
                            issues.append((number,'未标类型的非来源名称与未加引号正文，需人工确认是否发言。'))
                        break
                    end = len(line)
                    words = line[value:end].strip()
                kind = ('OS' if re.search(r'(?<![A-Za-z])OS(?![A-Za-z])|内心独白',meta,re.I) else
                        'OV' if re.search(r'(?<![A-Za-z])OV(?![A-Za-z])',meta,re.I) else
                        '旁白' if '旁白' in meta or speaker == '旁白' else '对白')
                records.append(dict(speaker=speaker,kind=kind,text=words,raw_text=line[value:end].strip()))
                at, segment = end, end
                continue
            at += 1
        if brackets and issues is not None:
            issues.append((number,'括号未闭合，话语归属可能未解析，需人工核对。'))
    return records


def source_utterances(source_bytes, ledger):
    if not isinstance(ledger, dict) or ledger.get('version') != 1:
        raise ValueError('台词索引须为version=1的对象')
    if hashlib.sha256(source_bytes).hexdigest() != ledger.get('source_sha256'):
        raise ValueError('原文快照哈希不一致；确认原文版本，不修改索引迎合成稿')
    source = source_bytes.decode('utf-8')
    rows = ledger.get('utterances')
    if not isinstance(rows, list):
        raise ValueError('utterances须为列表；原文无台词时使用空列表并人工确认覆盖')
    seen, end = set(), -1
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('每条原文台词须为对象')
        uid = row.get('id')
        if not isinstance(uid, str) or not re.fullmatch(r'U\d+', uid) or uid in seen:
            raise ValueError('原文台词ID须为唯一U编号')
        seen.add(uid)
        if (not isinstance(row.get('speaker'), str) or not row['speaker'].strip() or
                row.get('kind') not in ('对白', 'OS', 'OV', '旁白')):
            raise ValueError(uid + '缺说话人或有效话语类型')
        a, b, words = row.get('source_start'), row.get('source_end'), row.get('text')
        if (type(a) is not int or type(b) is not int or not isinstance(words, str) or
                not words or not 0 <= a < b <= len(source) or source[a:b] != words):
            raise ValueError(uid + '台词与原文字符区间不一致')
        if a < end:
            raise ValueError(uid + '原文区间重叠或逆序')
        end = b
    return rows


def spoken_text(text):
    # A matching outer quote pair is presentation; punctuation inside is exact.
    if text and text[0] in QUOTES and quoted_end(text, 0) == len(text):
        return text[1:-1]
    return text


def verify_layers(layers, source_bytes, ledger):
    """layers: [(label, [(unit_or_shot_id, authoritative_dialogue_text), ...])].

    Consecutive fragments may span shots/units; concatenation, speaker, kind,
    occurrence count and source order must all match. Existing creating ledgers
    are accepted; old delivery/unit/music settings do not redefine the source.
    """
    rows = source_utterances(source_bytes, ledger)
    errors, notes = [], []
    speakers = [row['speaker'] for row in rows]
    for label, chunks in layers:
        at, offset = 0, 0
        if not chunks:
            errors.append(label + '没有可定位的台词承载正文，不能报告核对通过')
            continue
        for location, text in chunks:
            issues = []
            records = voice_records(text, speakers, issues)
            for number, message in issues:
                notes.append(f'{label}/{location}/第{number}行：{message}')
            if issues:
                errors.append(f'{label}/{location}话语解析有待核项，原文核对未完成')
            for record in records:
                where = f'{label}/{location}'
                if at >= len(rows):
                    errors.append(where + '存在原文外新增或重复台词')
                    continue
                expected = rows[at]
                if record['speaker'] != expected['speaker'] or record['kind'] != expected['kind']:
                    errors.append(where + '/' + expected['id'] + '说话人、对白/OS/OV类型或顺序与原文不符')
                    continue
                whole, part = spoken_text(expected['text']), record['text']
                if not part or not whole[offset:].startswith(part):
                    errors.append(where + '/' + expected['id'] + '台词改字、漏字、重复或顺序与原文不符')
                    continue
                offset += len(part)
                if offset == len(whole):
                    at, offset = at + 1, 0
        if at < len(rows):
            errors.append(label + '/' + rows[at]['id'] + '起的原文台词未完整交付；跨镜片段须按原顺序精确拼接')
    return {'errors': errors, 'notes': notes, 'source_utterances': len(rows)}
