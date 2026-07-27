#!/usr/bin/env python3
"""Fast structural validator for jimeng-dialogue-performance-storyboard outputs."""

from __future__ import annotations

import re
import sys
from pathlib import Path


CHILD_FIELDS = ["【镜号】", "【画面描述｜直接复制】", "【表演与声音】", "【状态继承】"]
KEYFRAME_IMAGE_FIELD = "【关键帧生图提示】"
KEYFRAME_VIDEO_FIELD = "【即梦视频提示｜配合关键帧】"
DIRECT_NEXT_FIELDS = (KEYFRAME_IMAGE_FIELD, KEYFRAME_VIDEO_FIELD, "【表演与声音】")
REQUIRED_TOP_SECTIONS = [
    "## 使用说明",
    "## 全局锁定",
    "## 通用负面提示词｜直接复制",
    "## 场景状态表",
    "## 分镜投喂卡",
]
DEPRECATED_HEADINGS = [
    "## 全局锁帧模板", "## 负面提示词｜直接复制", "## 角色锁定表",
    "## 人物位置与拍摄侧锁定表", "## 场景与道具锁定表", "## 分镜正式投喂表",
    "【画面描述｜直接复制投喂（含空间/表演/台词/运镜）】", "【画面描述｜直接复制投喂】",
    "【画面描述｜直接复制｜无关键帧T2V】", "【即梦视频提示｜配合关键帧I2V】",
    "【导演校验记录】", "【主体与空间锁定】", "【摄影合同】", "【运镜/推拉/反打时机】",
    "【情绪与表演时间轴】", "【台词/OS/系统声与语气】",
]
BANNED_DIRECT = [
    "继承", "延续上一镜", "空间保持", "位置继承", "物理座位不变", "剪辑", "切到", "反打到",
    "下一镜执行", "声音语气：", "表情：", "动作：", "情绪：", "脑海浮现", "后期插入", "左外",
    "当前主角", "当前对话者", "视情况", "出场人物", "所有人物", "全部人物", "所有出场人物",
]
NEGATIVE_NEEDLE = "人物僵硬、全身静止、无眨眼"
CUTAWAY_NEEDLES = ("镜头不拍人物", "空镜", "空椅", "门缝", "水纹", "走廊灯光")
SHOT_SIZE_TERMS = ("特写", "近景", "中近景", "中景", "中远景", "全景", "远景")
CAMERA_TERMS = ("镜头", "相机", "机位", "平视", "俯视", "仰视", "侧后方", "斜前方")
CAMERA_STATE_TERMS = ("固定", "保持", "静止", "推", "拉", "摇", "移", "跟", "转焦", "拉焦", "上摇", "下摇")
RELATION_TERMS = ("面对", "相对", "身侧", "身后", "前方", "后方", "之间", "隔着", "挽着", "肩线", "右手", "左手", "朝向", "背对", "侧身")
FACING_TERMS = ("面向", "背向", "身体朝向", "身体仍朝", "上身朝向", "头部转向", "头部偏向")
POST_AUDIO_TERMS = ("OS", "OV", "系统音", "内心独白", "画外", "后期", "配音", "旁白")
POST_AUDIO_LABEL_TERMS = ("OS", "OV", "系统音", "内心独白", "旁白")
VISIBLE_SPEECH_TERMS = ("可见口型", "可见说话者", "开口", "说：", "说:", "说“", "问：", "问:", "喊：", "喊:", "低语", "回应", "反问")
BLAND_EXPRESSION_TERMS = ("眼神复杂", "神色复杂", "表情平淡", "神色变化", "微微皱眉", "闭口看着")
FACIAL_DETAIL_TERMS = ("眼睑", "睫毛", "眉尾", "嘴角", "下颌", "喉咙", "呼吸", "唇", "屏息")
BODY_PROP_EMOTION_TERMS = ("肩", "背", "手", "指", "道具", "手机", "卡", "衣", "后退", "靠近", "距离", "遮挡", "门", "桌")
PROP_TRANSFER_TERMS = ("递", "交给", "接过", "接住", "松手", "刷卡", "签字", "付款", "取出", "拿出", "塞给")
CONTACT_TERMS = ("握住", "抓住", "拽住", "牵住", "拉住", "按住", "扶住", "扣住")
MOVE_TERMS = ("走到", "走近", "上前", "后退", "转身", "离开", "入场", "进门", "出门", "坐下", "站起")
CAMERA_MOVE_TERMS = ("推", "拉", "摇", "移", "跟拍", "环绕", "转焦", "拉焦", "上摇", "下摇")
PROP_CONTINUITY_TERMS = ("右手", "左手", "手中", "掌中", "桌面", "台面", "包内", "口袋", "外袋", "胸前", "腰侧", "松手", "接触", "握住")
REVERSE_SHOT_RE = re.compile(r"机位在([^，。；;]{1,12})肩后")
ORIENTATION_LOCK_TERMS = ("背向", "背对", "侧身", "身体面向柜台", "身体面向入口", "身体面向出口", "身体面向道路", "身体面向门口", "身体面向车门", "身体面向手机", "身体面向屏幕", "身体面向签字台", "身体面向缴费台")
ORIENTATION_TURN_TERMS = ("转身", "转向", "回身", "侧身转正", "肩线转正", "双脚停稳", "身体从")
TRACKED_PROPS = ("手机", "银行卡", "卡片", "卡", "杯子", "茶盏", "瓷盏", "笔", "签字笔", "文件", "外套", "手包", "包", "钥匙", "餐盘", "照片", "纸")
PROP_STATE_HINTS = ("右手", "左手", "手中", "掌中", "包内", "口袋", "外袋", "胸前", "腰侧", "桌面", "台面", "签字台", "柜台", "手边")
STRONG_PROP_STATE_HINTS = ("右手", "左手", "包内", "口袋", "外袋", "胸前", "腰侧", "桌面", "台面", "签字台", "柜台", "掌中", "手中")
PROP_TRANSFER_CHAIN_TERMS = ("取出", "拿出", "拿起", "递", "递到", "交给", "接触", "接过", "接住", "握住", "松手", "放下", "放到", "移动")
ACTION_CHAIN_TERMS = (
    "转身", "转向", "回身", "走到", "走近", "上前", "后退", "取出", "拿出", "拿起",
    "抬", "递", "递到", "接触", "握住", "接过", "接住", "松手", "放下", "放到",
    "离开", "坐下", "站起", "伸", "按下", "挂断",
)
POSTURE_RISK_TERMS = (
    "躺", "伏", "趴", "靠在", "靠到", "抱住", "搂住", "扶住", "拉住", "拽住",
    "摔倒", "倒向", "倒到", "翻身", "坐起", "起身", "蹲下", "跪下", "弯腰",
    "前倾", "抱起", "背起", "腿上", "怀里",
)
POSTURE_STRUCTURE_TERMS = (
    "头", "脸", "肩", "背", "腰", "臀", "腿", "膝", "脚", "手撑", "撑住",
    "座垫", "座椅", "沙发", "床", "地面", "支撑", "接触点", "贴", "枕",
    "压", "蜷", "非接触", "没有跨坐", "没有缠绕",
)
GARMENT_RISK_TERMS = ("披", "穿上", "脱下", "外套滑落", "衣摆")
GARMENT_STRUCTURE_TERMS = ("领口", "袖", "肩", "臂弯", "衣摆", "双臂", "哪只手", "左手", "右手", "垂")
DOOR_RISK_TERMS = ("开门", "关门", "推门", "拉门", "开车门", "关车门", "下车", "上车", "门把", "把手")
DOOR_STRUCTURE_TERMS = ("把手", "门边", "打开", "关闭", "半掩", "车外", "车内", "路沿", "门槛", "踏", "站在")
UI_RISK_TERMS = ("来电", "转账", "聊天记录", "付款码", "屏幕显示", "清晰文字", "文字")
UI_STRUCTURE_TERMS = ("后期叠字", "安全区", "模糊", "不生成清晰文字", "斜向", "正对", "屏幕")
CROWD_RISK_TERMS = ("人群", "围观", "混混", "路人", "宾客", "群众")
CROWD_STRUCTURE_TERMS = ("后方", "背景", "虚化", "不靠近", "不抢焦", "不产生可见口型", "远处")


def compact_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def iter_groups(text: str):
    header = r"^####\s+(S\d+-\d+)(?:｜镜头组总时长：(\d+(?:\.\d+)?)s)?\s*$"
    pattern = re.compile(
        header + r"([\s\S]*?)(?=" + header + r"|^##\s|\Z)",
        re.M,
    )
    yield from pattern.finditer(text)


def iter_children(group_block: str):
    pattern = re.compile(r"【镜号】\n\s*([^\n]+)\n([\s\S]*?)(?=\n【镜号】\n|\Z)")
    yield from pattern.finditer(group_block)


def extract(block: str, field: str, next_field: str | None = None) -> str:
    if next_field:
        m = re.search(re.escape(field) + r"\n([\s\S]*?)(?=\n\n" + re.escape(next_field) + r")", block)
    else:
        m = re.search(re.escape(field) + r"\n([\s\S]*)", block)
    return m.group(1).strip() if m else ""


def extract_until_any(block: str, field: str, next_fields: tuple[str, ...]) -> str:
    alternatives = "|".join(re.escape(next_field) for next_field in next_fields)
    pattern = re.escape(field) + r"\n([\s\S]*?)(?=\n\n(?:" + alternatives + r")|\Z)"
    m = re.search(pattern, block)
    return m.group(1).strip() if m else ""


def direct_prompt(block: str) -> str:
    return extract_until_any(block, "【画面描述｜直接复制】", DIRECT_NEXT_FIELDS)


def extract_optional_field(block: str, field: str) -> str:
    m = re.search(re.escape(field) + r"\n([\s\S]*?)(?=\n\n【|\Z)", block)
    return m.group(1).strip() if m else ""


def direct_sentence(state_change: str, label: str) -> str:
    m = re.search(re.escape(label) + r"[：:]\s*([^\n；;]+)", state_change)
    return m.group(1).strip() if m else ""


def quoted_lines(text: str) -> list[str]:
    return [line.strip() for line in re.findall(r"“([^”]+)”", text) if line.strip()]


def visible_dialogue_quotes(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        if not any(q in raw_line for q in ("“", "”")):
            continue
        if any(term in raw_line for term in POST_AUDIO_TERMS) and not any(term in raw_line for term in VISIBLE_SPEECH_TERMS):
            continue
        if any(term in raw_line for term in VISIBLE_SPEECH_TERMS):
            lines.extend(quoted_lines(raw_line))
    return lines


def post_audio_format_issues(text: str) -> list[str]:
    issues: list[str] = []
    label_pattern = r"(?:OS|OV|系统音|内心独白|旁白)"
    wrapped_pattern = re.compile(label_pattern + r"\s*[：:]\s*[“\"][^”\"]+[”\"]")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or not any(label in line for label in POST_AUDIO_LABEL_TERMS):
            continue
        if "无台词" in line or re.fullmatch(r"无(?:OS|OV|系统音|内心独白|旁白).*", line):
            continue
        has_text_signal = any(mark in line for mark in ("“", "”", '"')) or any(
            term in line for term in ("响起", "念出", "吐槽", "旁白", "低语", "声音", "内心")
        )
        if has_text_signal and not wrapped_pattern.search(line):
            issues.append(line)
    return issues


def validate_child(group_id: str, number: int, header: str, block: str, issues: list[str]) -> None:
    sid = f"{group_id}-{number}"
    if not re.match(rf"^{number}\s*，\s*\d+(?:\.\d+)?s\s*，\s*(普通|复杂)。?$", header):
        issues.append(f"{sid}: 镜号应为“{number}，时长s，普通/复杂。” -> {header}")
    for field in CHILD_FIELDS[1:]:
        if field not in block:
            issues.append(f"{sid}: missing {field}")
    if "【出现人物】" in block:
        issues.append(f"{sid}: cast belongs only at group level")

    direct = direct_prompt(block)
    if not direct:
        issues.append(f"{sid}: missing direct prompt body")
        return
    performance = extract(block, "【表演与声音】", "【状态继承】")
    mouth_window = extract_optional_field(block, "【口型分窗】")
    keyframe_image = extract_optional_field(block, KEYFRAME_IMAGE_FIELD)
    keyframe_video = extract_optional_field(block, KEYFRAME_VIDEO_FIELD)
    if keyframe_image and not keyframe_video:
        issues.append(f"{sid}: {KEYFRAME_IMAGE_FIELD} should pair with {KEYFRAME_VIDEO_FIELD}")
    if keyframe_video and not keyframe_image:
        issues.append(f"{sid}: {KEYFRAME_VIDEO_FIELD} requires {KEYFRAME_IMAGE_FIELD}")
    if keyframe_image and not any(label in keyframe_image for label in ("首帧", "尾帧")):
        issues.append(f"{sid}: {KEYFRAME_IMAGE_FIELD} should include static frame labels such as 首帧/尾帧")
    if any(term in keyframe_image + keyframe_video for term in ("T2V", "I2V")):
        issues.append(f"{sid}: keyframe fields should not use T2V/I2V labels")
    if compact_len(direct) > 500:
        issues.append(f"{sid}: direct prompt over 500 chars -> {compact_len(direct)}")
    if (
        compact_len(direct) < 180
        and not any(term in direct for term in ("手部特写", "特写", "空镜", "只拍", "镜头不拍人物"))
    ):
        issues.append(f"{sid}: ordinary dialogue/drama direct prompt looks too thin -> {compact_len(direct)} chars")
    if not any(term in direct for term in SHOT_SIZE_TERMS):
        issues.append(f"{sid}: direct prompt missing shot size")
    if not any(term in direct for term in CAMERA_TERMS):
        issues.append(f"{sid}: direct prompt missing camera placement or angle")
    if not any(term in direct for term in CAMERA_STATE_TERMS):
        issues.append(f"{sid}: direct prompt missing static state or one camera path")
    if not any(term in direct for term in RELATION_TERMS):
        issues.append(f"{sid}: direct prompt missing body or prop relationship")
    if not any(term in direct for term in FACING_TERMS):
        issues.append(f"{sid}: direct prompt missing body-facing anchor")
    if re.search(r"(?:身体|上身)朝(?:左|右)(?!侧)", direct):
        issues.append(f"{sid}: body direction must name a person or fixed anchor, not only left/right")
    if ("只拍" in direct or "只保留" in direct) and re.search(r"中景|中近景|中远景|全景|远景", direct):
        issues.append(f"{sid}: hand/object-only frame conflicts with medium or wide shot size")
    if "肩后" in direct and "肩线" not in direct:
        issues.append(f"{sid}: shoulder shot should state foreground shoulder line and target")
    if "肩后" in direct and not re.search(r"身体面向[^，。；;]{1,12}，[^，。；;]{1,12}身体面向", direct):
        issues.append(f"{sid}: shoulder/reverse shot should restate face-to-face body orientation")
    if any(term in direct for term in PROP_TRANSFER_TERMS):
        if ("取出" in direct or "拿出" in direct) and not any(place in direct for place in ("包", "口袋", "桌面", "台面", "手中", "掌中", "外袋")):
            issues.append(f"{sid}: prop appearance needs starting holder/container/surface")
        if any(term in direct for term in ("递", "交给", "接过", "接住", "塞给")):
            if not any(term in direct for term in ("接触", "握住", "接住")) or "松手" not in direct:
                issues.append(f"{sid}: prop transfer needs contact and release chain to prevent flashing")
            if not any(term in direct for term in PROP_CONTINUITY_TERMS):
                issues.append(f"{sid}: prop transfer needs clear final holder/location")
    if any(term in direct for term in ("在身后", "侧后方", "身后半身")) and any(term in direct for term in ("递", "交给", "接过", "接住", "塞给")):
        if not any(term in direct for term in ("转身", "走到", "走近", "面向")):
            issues.append(f"{sid}: recipient behind/side-behind needs repositioning before prop transfer")
    if any(term in direct for term in POSTURE_RISK_TERMS):
        posture_hits = [term for term in POSTURE_STRUCTURE_TERMS if term in direct]
        if len(posture_hits) < 3:
            issues.append(
                f"{sid}: posture action needs physical structure: head/shoulder/waist-hip/legs/feet/support/contact/boundary"
            )
    if any(term in direct for term in GARMENT_RISK_TERMS):
        if not any(term in direct for term in GARMENT_STRUCTURE_TERMS):
            issues.append(f"{sid}: garment action needs clothing start point, hand contact, sleeve/shoulder/hem final state")
    if any(term in direct for term in DOOR_RISK_TERMS):
        if not any(term in direct for term in DOOR_STRUCTURE_TERMS):
            issues.append(f"{sid}: door/car-door action needs handle/contact, open-close direction, side crossing, final door state")
    if any(term in direct for term in UI_RISK_TERMS):
        if not any(term in direct for term in UI_STRUCTURE_TERMS):
            issues.append(f"{sid}: UI/text needs screen direction, blur or post-production text safety-zone handling")
    if any(term in direct for term in CROWD_RISK_TERMS):
        if not any(term in direct for term in CROWD_STRUCTURE_TERMS):
            issues.append(f"{sid}: crowd/background characters need region, depth/blur, approach and lip-sync control")
    if keyframe_image and any(term in direct for term in POSTURE_RISK_TERMS):
        keyframe_posture_hits = [term for term in POSTURE_STRUCTURE_TERMS if term in keyframe_image]
        if len(keyframe_posture_hits) < 4:
            issues.append(f"{sid}: posture keyframes should repeat body support/contact structure in each static frame")

    duration_match = re.search(r"，\s*(\d+(?:\.\d+)?)s\s*，", header)
    spoken_chars = sum(len(re.sub(r"\s+", "", line)) for line in re.findall(r"“([^”]+)”", direct))
    if duration_match and spoken_chars:
        duration = float(duration_match.group(1))
        min_duration = spoken_chars / 6.5 + 0.5
        if duration + 0.01 < min_duration:
            issues.append(
                f"{sid}: visible dialogue duration too short -> {duration:g}s for {spoken_chars} chars, need about {min_duration:.1f}s"
            )
    hits = [word for word in BANNED_DIRECT if word in direct]
    if hits:
        issues.append(f"{sid}: banned direct-prompt terms -> {','.join(hits)}")
    bland_hits = [word for word in BLAND_EXPRESSION_TERMS if word in direct]
    if bland_hits:
        issues.append(f"{sid}: bland expression terms need concrete facial/body evidence -> {','.join(bland_hits)}")
    if re.search(r"特写|(?<!中)近景", direct) and re.search(r"三人|四人|五人|众人|所有人|全部人", direct):
        issues.append(f"{sid}: close-up/insert shot overloaded with group cast; split relation shot and close-up")
    has_visible_emotion = any(word in direct for word in ("皱眉", "眼神", "委屈", "紧张", "焦虑", "愣", "僵", "怒", "冷", "慌", "压低", "哽", "红"))
    if has_visible_emotion and not any(word in direct for word in FACIAL_DETAIL_TERMS + BODY_PROP_EMOTION_TERMS):
        issues.append(f"{sid}: emotion needs readable facial/body/prop evidence matched to shot size")
    if has_visible_emotion and re.search(r"全景|远景|中远景", direct) and any(word in direct for word in ("眼睑", "眉尾", "嘴角", "下颌", "喉咙", "唇")):
        issues.append(f"{sid}: wide shot uses tiny facial details; use body/distance/prop evidence or cut closer")
    direct_quotes = set(quoted_lines(direct))
    for line in visible_dialogue_quotes(performance) + visible_dialogue_quotes(mouth_window):
        if line not in direct_quotes:
            issues.append(f"{sid}: visible dialogue must appear in direct prompt by default -> “{line}”")
    for line in post_audio_format_issues(performance) + post_audio_format_issues(mouth_window):
        issues.append(f"{sid}: OS/OV/系统音文本必须使用 标签：“...” 格式 -> {line}")
    if any(word in direct for word in CUTAWAY_NEEDLES):
        handoff = extract_optional_field(block, "【剪辑衔接】")
        in_place_focus = any(word in direct for word in ("焦点从", "焦点落到", "拉焦", "转焦"))
        if not handoff and not in_place_focus:
            issues.append(f"{sid}: standalone cutaway needs 【剪辑衔接】 with independent-generation sound bridge")

    state_change = extract_optional_field(block, "【镜内状态转换】")
    if state_change:
        for label in ("终态直投句", "尾帧直投句"):
            sentence = direct_sentence(state_change, label)
            if not sentence:
                issues.append(f"{sid}: 【镜内状态转换】 missing {label}")
            elif sentence not in direct:
                issues.append(f"{sid}: {label} must appear verbatim in direct prompt -> {sentence}")

    camera_execution = extract_optional_field(block, "【镜头执行】")
    if mouth_window:
        priority = "优先级：口型 > 听者反应 > 运镜"
        if priority not in mouth_window:
            issues.append(f"{sid}: 【口型分窗】 missing dialogue priority declaration")
        if camera_execution and re.search(r"推|拉|移|摇|跟拍|环绕|转焦|拉焦", camera_execution):
            if not any(term in mouth_window for term in ("听者保持", "听者不动", "听者静止", "仅呼吸", "仅视线")):
                issues.append(f"{sid}: lip-sync with camera move needs listener hold declaration in 【口型分窗】")
    high_risk_count = sum(
        bool(condition)
        for condition in (
            re.search(r"三人|四人|五人|众人|混混|人群", direct),
            any(term in direct for term in PROP_TRANSFER_TERMS + CONTACT_TERMS),
            bool(direct_quotes),
            any(term in direct for term in CAMERA_MOVE_TERMS),
            any(term in direct for term in MOVE_TERMS),
            any(term in direct for term in ("车", "人群", "闪回", "回忆", "梦境")),
        )
    )
    if high_risk_count >= 4:
        issues.append(f"{sid}: possible single-shot overload; split or simplify high-risk tasks")
    action_chain_hits = [term for term in ACTION_CHAIN_TERMS if term in direct]
    if len(action_chain_hits) >= 5:
        issues.append(
            f"{sid}: long action chain may be simplified by AI; split into prepare/contact/final-state shots -> {','.join(action_chain_hits[:8])}"
        )


def camera_signature(direct: str) -> str:
    size = next((term for term in SHOT_SIZE_TERMS if term in direct), "")
    moving = any(term in direct for term in ("推", "拉", "摇", "移", "跟", "转焦", "拉焦"))
    return f"{size}:{'move' if moving else 'static'}"


def shoulder_actor(direct: str) -> str:
    match = REVERSE_SHOT_RE.search(direct)
    return match.group(1).strip() if match else ""


def orientation_jump(prev_state: str, next_direct: str) -> bool:
    if not prev_state or not next_direct:
        return False
    if not any(term in prev_state for term in ORIENTATION_LOCK_TERMS):
        return False
    if any(term in next_direct for term in ORIENTATION_TURN_TERMS):
        return False
    next_demands_new_facing = (
        ("身体面向" in next_direct and not any(term in next_direct for term in ORIENTATION_LOCK_TERMS))
        or "面对面" in next_direct
        or "肩后" in next_direct
        or any(term in next_direct for term in ("开口", "接过", "接住", "递", "交给"))
    )
    return next_demands_new_facing


def prop_contexts(text: str) -> dict[str, str]:
    contexts: dict[str, str] = {}
    for prop in TRACKED_PROPS:
        if prop == "卡" and any(longer in text for longer in ("银行卡", "卡片")):
            continue
        if prop not in text:
            continue
        for match in re.finditer(re.escape(prop), text):
            start = max(0, match.start() - 18)
            end = min(len(text), match.end() + 22)
            context = text[start:end]
            if any(hint in context for hint in PROP_STATE_HINTS):
                contexts[prop] = re.sub(r"\s+", "", context)
                break
    return contexts


def prop_state_jump(prev_state: str, next_direct: str) -> list[str]:
    if not prev_state or not next_direct:
        return []
    prev_props = prop_contexts(prev_state)
    next_props = prop_contexts(next_direct)
    if not prev_props or not next_props:
        return []
    has_visible_transfer = any(term in next_direct for term in PROP_TRANSFER_CHAIN_TERMS)
    jumps: list[str] = []
    for prop, prev_context in prev_props.items():
        next_context = next_props.get(prop)
        if not next_context or prev_context == next_context:
            continue
        if set(hint for hint in STRONG_PROP_STATE_HINTS if hint in prev_context) & set(
            hint for hint in STRONG_PROP_STATE_HINTS if hint in next_context
        ):
            continue
        if has_visible_transfer:
            continue
        jumps.append(prop)
    return jumps


def validate(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    issues: list[str] = []
    for section in REQUIRED_TOP_SECTIONS:
        if section not in text:
            issues.append(f"missing top section {section}")
    hits = [heading for heading in DEPRECATED_HEADINGS if heading in text]
    if hits:
        issues.append("deprecated headings not allowed -> " + ",".join(hits))
    if NEGATIVE_NEEDLE not in text:
        issues.append("missing anti-stiffness negative prompt")

    group_count = child_count = 0
    for match in iter_groups(text):
        group_count += 1
        group_id, group_total, block = match.group(1), match.group(2), match.group(3)
        if group_total is None:
            issues.append(f"{group_id}: group heading must include summed duration -> #### {group_id}｜镜头组总时长：Xs")
        before_first_child = block.split("【镜号】", 1)[0]
        cast = extract_optional_field(before_first_child, "【出现人物】")
        if not cast:
            issues.append(f"{group_id}: missing group-level 【出现人物】")
        for line in [x.strip() for x in cast.splitlines() if x.strip()]:
            if any(sep in line for sep in "、，；;"):
                issues.append(f"{group_id}: cast line should contain one visible character/group only -> {line}")
        children = list(iter_children(block))
        if not children:
            issues.append(f"{group_id}: no child shots found")
        for expected_number, child in enumerate(children, start=1):
            child_count += 1
            validate_child(group_id, expected_number, child.group(1).strip(), child.group(0), issues)
        child_directs = [
            direct_prompt(child.group(0))
            for child in children
        ]
        child_states = [
            extract(child.group(0), "【状态继承】")
            for child in children
        ]
        for index in range(1, len(children)):
            if orientation_jump(child_states[index - 1], child_directs[index]):
                issues.append(
                    f"{group_id}-{index + 1}: 上一镜状态为背向/侧身/面向固定物，下一镜改变朝向前必须写转身/回身/肩线转正/双脚停稳"
                )
            jumped_props = prop_state_jump(child_states[index - 1], child_directs[index])
            if jumped_props:
                issues.append(
                    f"{group_id}-{index + 1}: 上一镜物品状态与下一镜开头不一致，{','.join(jumped_props)} 改变归属/位置前必须写取出/接触/移动/松手/稳定终态"
                )
        child_durations = []
        for child in children:
            duration_match = re.search(r"，\s*(\d+(?:\.\d+)?)s\s*，", child.group(1))
            if duration_match:
                child_durations.append(float(duration_match.group(1)))
        if group_total is not None and child_durations:
            summed = sum(child_durations)
            if abs(float(group_total) - summed) > 0.01:
                issues.append(f"{group_id}: group duration {float(group_total):g}s != child sum {summed:g}s")
        signatures = []
        for child in children:
            direct = direct_prompt(child.group(0))
            signatures.append(camera_signature(direct))
        for index in range(2, len(signatures)):
            if signatures[index] == signatures[index - 1] == signatures[index - 2] and signatures[index].endswith(":static"):
                issues.append(f"{group_id}: three consecutive identical static camera tasks -> {signatures[index]}")
        shoulder_actors = [
            shoulder_actor(direct_prompt(child.group(0)))
            for child in children
        ]
        for index in range(1, len(shoulder_actors)):
            if shoulder_actors[index - 1] and shoulder_actors[index] and shoulder_actors[index - 1] == shoulder_actors[index]:
                issues.append(f"{group_id}: consecutive shoulder shots use same shoulder actor; reverse shot should swap foreground shoulder")

    if group_count == 0:
        issues.append("no shot groups found; use #### S1-01 with group-level 【出现人物】")
    if child_count == 0:
        issues.append("no child shots found")
    return issues


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: validate_storyboard.py <file.md> [more.md ...]", file=sys.stderr)
        return 2
    failed = False
    for raw in argv[1:]:
        path = Path(raw)
        issues = validate(path)
        print(f"{path}: {'OK' if not issues else 'FAIL'}")
        for issue in issues:
            print(f"  - {issue}")
        failed = failed or bool(issues)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
