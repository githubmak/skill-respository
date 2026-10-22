#!/usr/bin/env python3
"""Check storyboard structure, timing, basic composition, and language conflicts."""
import argparse
import math
import re
import sys
from pathlib import Path

UNIT = re.compile(
    r"^###\s+(生成单元|镜头)\s+([^｜|\n]+?)\s*[｜|]\s*时长[：:]\s*"
    r"(\d+(?:\.\d+)?)\s*(?:秒|[sS])([^\n]*)",
    re.M,
)
WINDOW = re.compile(r"^\s*(?:-\s*)?(\d+(?:\.\d+)?)\s*秒?\s*[—–-]\s*(\d+(?:\.\d+)?)\s*秒\s*[｜|]\s*(.+)$", re.M)
SIZES = re.compile(r"大特写|特写|近中景|中近景|近景|中全景|大全景|全景|中景|远景|半身")
MOVEMENTS = re.compile(r"固定|静止|推|拉|移|跟拍|跟随|环绕|短弧|升降|升机|降机|后退|前移|摇|俯仰|甩|穿越|变焦|手持|轨道|航拍|锁定|急停")
CONTRADICTIONS = re.compile(
    r"固定(?:机位|镜头)(?:缓慢|快速|持续|同时)?"
    r"(?:横移|侧移|推进|推近|拉远|后退|环绕|升降|跟拍)"
)
FIELDS = ["起幅与连续性", "摄影与构图", "光影、环境色彩与材质", "画面与表演时间线", "台词与声音层次", "落幅状态"]
GLOBAL_COMMON = ["项目直投参数", "项目共用视觉规则"]
GLOBAL_OLD_COMMON = ["项目直投参数", "全局摄影规则"]
SCENE_CURRENT = ["场景摄影规则", "场景光色与影调基线", "场景资产图提示词", "道具资产图提示词", "场景空间位置关系", "Seedance 独立直投生成单元"]
LIGHT_VALUE = re.compile(r"\d+(?:\.\d+)?\s*(?:[—–~～至到-]\s*\d+(?:\.\d+)?)?\s*[Kk]\b|\d+\s*开尔文|纯色(?:灯|光)|单色(?:灯|光)|无有效(?:光源|照明)")
GLOBAL_LEGACY_LIGHT = ["全局影调", "全局光影", "全局环境色彩"]
GLOBAL_CURRENT_LIGHT = ["全局光色与影调基线"]
GLOBAL_END = ["全局正向提示词", "全局负面提示词"]

def validate(raw, mode="refined", max_unit_seconds=35.0, require_focal_length=True, schema="auto"):
    errors = []
    if not math.isfinite(max_unit_seconds) or max_unit_seconds <= 0:
        return ["生成单元时长上限必须为有限正数"]
    raw = raw.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    comments = re.findall(r"<!--.*?-->", raw, re.S)
    body = re.sub(r"<!--.*?-->", "", raw, flags=re.S).lstrip()
    if comments:
        errors.append("精修正文仍包含HTML交接注释")
    is_project = bool(
        re.match(r"# 《.+》[^\n]*Seedance 独立直投版", body)
        or re.search(r"^## 项目直投参数\s*$", body, re.M)
    )
    current = schema != "legacy"
    if is_project and schema != "generic":
        if not re.match(r"# 《.+》[^\n]*Seedance 独立直投版", body):
            errors.append("正式标题不符合Seedance独立直投版格式")
        positions = []
        headings = set(re.findall(r"^## (.+?)\s*$", body, re.M))
        common = GLOBAL_COMMON if current else GLOBAL_OLD_COMMON
        light = [] if current else (GLOBAL_CURRENT_LIGHT if "全局光色与影调基线" in headings else GLOBAL_LEGACY_LIGHT)
        global_head = body.split("\n# 场景", 1)[0]
        expected = common + (["全局配音、配乐与声音规则"] if "全局配音、配乐与声音规则" in headings else []) + light + GLOBAL_END
        for key in expected:
            found = re.search(r"^## " + re.escape(key) + r"\s*$", global_head, re.M)
            if not found:
                errors.append("缺少全局栏目：" + key)
            else:
                positions.append(found.start())
                tail = global_head[found.end():]
                value = re.split(r"^#{1,2} ", tail, maxsplit=1, flags=re.M)[0].strip()
                if not value:
                    errors.append("全局栏目为空：" + key)
        if positions != sorted(positions):
            errors.append("全局栏目顺序不正确")
        if current and any(key in headings for key in ["全局摄影规则"] + GLOBAL_CURRENT_LIGHT + GLOBAL_LEGACY_LIGHT):
            errors.append("当前格式须将具体摄影与光色移入各场，不保留旧全局摄影/光色栏目")
    if schema != "generic" and (is_project or re.search(r"^# 场景", body, re.M)):
        scenes = list(re.finditer(r"^# 场景[^\n]+", body, re.M))
        if not scenes:
            errors.append("缺少场景标题")
        for i, scene in enumerate(scenes):
            section = body[scene.end():scenes[i+1].start() if i+1 < len(scenes) else len(body)]
            scene_positions = []
            for key in (SCENE_CURRENT if current else ["场景资产图提示词", "道具资产图提示词", "场景空间位置关系"]):
                found = re.search(r"^## " + re.escape(key) + r"[^\n]*$", section, re.M)
                if not found:
                    errors.append(scene.group(0) + "：缺少场景栏目 " + key)
                    continue
                scene_positions.append(found.start())
                value = re.split(r"^#{1,2} ", section[found.end():], maxsplit=1, flags=re.M)[0].strip()
                if not value:
                    errors.append(scene.group(0) + "：场景栏目为空 " + key)
                if current and key == "场景光色与影调基线" and not LIGHT_VALUE.search(value):
                    errors.append(scene.group(0) + "：光色基线缺少主光色温设计或纯色光/无有效照明例外")
            if scene_positions != sorted(scene_positions):
                errors.append(scene.group(0) + "：场景栏目顺序不正确")

    if is_project and schema != "generic" and current and re.search(r"配乐[：:]", body) and "全局配音、配乐与声音规则" not in headings:
        errors.append("配乐版缺少全局配音、配乐与声音规则")
    if re.search(r"^## (?:场景级导演设计源|场级导演设计源|来源原文)", body, re.M):
        errors.append("来源/导演设计源泄漏到正式正文")
    if re.search(r"脸部只写|按本技能|只在此栏|不得被省略|使用\s+\$", body):
        errors.append("正文包含写作指令，请转换为实际画面")
    matches = list(UNIT.finditer(body))
    if not matches:
        errors.append("未找到“### 生成单元”标题")
        return errors
    ids = set()
    total = 0.0
    shot_focal_tail = {}  # Same shot can span windows or generation units.
    for i, match in enumerate(matches):
        kind = match.group(1)
        sid = match.group(2).strip()
        duration = float(match.group(3))
        title_tail = match.group(4)
        if kind == "生成单元" and not re.search(r"[｜|]\s*承载[：:]", title_tail):
            errors.append(sid + "：生成单元标题缺少“承载”字段")
        if sid in ids:
            errors.append(sid + "：镜号重复")
        ids.add(sid)
        total += duration
        if duration <= 0 or (kind == "生成单元" and duration > max_unit_seconds):
            errors.append(sid + "：时长必须大于0，生成单元不得超过" + str(max_unit_seconds) + "秒")
        text = body[match.end():matches[i+1].start() if i+1 < len(matches) else len(body)]
        text = re.split(r"^# 场景[^\n]*", text, maxsplit=1, flags=re.M)[0]
        field_matches = list(re.finditer(r"^- ([^\n：:]+)[：:][ \t]*", text, re.M))
        fields = {}
        for fi, fm in enumerate(field_matches):
            fields[fm.group(1)] = text[fm.end():field_matches[fi+1].start() if fi+1 < len(field_matches) else len(text)].strip()
        for field in (FIELDS if schema != "generic" else ["画面与表演时间线"]):
            if field not in fields:
                errors.append(sid + "：缺少字段 " + field)
            elif not fields[field]:
                errors.append(sid + "：字段为空 " + field)
        if schema not in ("generic", "legacy"):
            lighting = fields.get("光影、环境色彩与材质", "")
            if lighting and not LIGHT_VALUE.search(lighting):
                errors.append(sid + "：光影栏缺少当前主光色温设计或纯色光/无有效照明例外")
        if re.search(r"(?m)^- 配乐/音效协同[：:]", text):
            errors.append(sid + "：配乐/音效协同须写入对应镜头时间窗的声音内容，不单设字段")
        timeline = re.search(r"^- 画面与表演时间线[：:]\s*\n(.*?)(?=^- \S|\Z)", text, re.S | re.M)
        if not timeline:
            errors.append(sid + "：时间线必须使用嵌套条目，不能写成同行概述")
            continue
        content = timeline.group(1)
        windows = list(WINDOW.finditer(content))
        if not windows:
            errors.append(sid + "：缺少嵌套时间段")
            continue
        previous = 0.0
        music_windows = 0
        unit_shots = []
        for j, window in enumerate(windows):
            start, end = float(window.group(1)), float(window.group(2))
            window_text = window.group(3)
            if abs(start - previous) > 0.05 or end <= start:
                errors.append(sid + "：时间段不连续或起止无效")
            previous = end
            if not SIZES.search(window_text):
                errors.append(sid + "：时间段须明确景别")
            focal_parts = re.split(r"[｜|]", window_text)
            focal_text = focal_parts[1] if len(focal_parts) > 1 else ""
            focal_values = re.findall(r"(-?\d+(?:\.\d+)?)\s*(?:mm|毫米)", focal_text, re.I)
            if not focal_values or any(float(value) <= 0 for value in focal_values):
                errors.append(sid + "：时间段须填写正数焦段，单位支持mm或毫米")
            segment = content[window.end():windows[j+1].start() if j+1 < len(windows) else len(content)]
            compiled = window_text + "\n" + segment
            shot_key = re.sub(r"^镜头\s*", "", focal_parts[0].strip()) if focal_parts else ""
            if shot_key and (not unit_shots or unit_shots[-1] != shot_key):
                unit_shots.append(shot_key)
            if shot_key and focal_values and all(float(value) > 0 for value in focal_values):
                focal_numbers = [float(value) for value in focal_values]
                zoom = "变焦" in compiled or "→" in focal_text
                prior = shot_focal_tail.get(shot_key)
                if len(focal_numbers) > 1:
                    if not zoom:
                        errors.append(sid + "：同一时间窗多个焦段须明确连续变焦")
                    if prior is not None and abs(prior - focal_numbers[0]) > 0.01:
                        errors.append(sid + "：同镜变焦起值与前窗/前单元焦段不接续")
                elif prior is not None and abs(prior - focal_numbers[0]) > 0.01 and not zoom:
                    errors.append(sid + "：同镜焦段无变焦说明却跨窗/跨单元跳变")
                shot_focal_tail[shot_key] = focal_numbers[-1]
            if "配乐：" in compiled:
                music_windows += 1
            sound = re.search(r"声音[：:][ \t]*([^\n]+)", compiled)
            if not sound or not sound.group(1).strip() or re.match(r"配乐[：:]", sound.group(1).strip()):
                errors.append(sid + "：时间段缺少实际声音/有因静默说明")
            # A camera label alone is not a picture. Inline pictures remain supported.
            picture_body = re.split(r"(?:声音|配乐)[：:]", segment, maxsplit=1)[0].strip()
            inline = re.split(r"(?:声音|配乐)[：:]", "｜".join(focal_parts[2:]), maxsplit=1)[0].strip()
            inline_picture = re.split(r"[，,。；;]", inline, maxsplit=1)
            if not picture_body and (len(inline_picture) < 2 or not inline_picture[1].strip()):
                errors.append(sid + "：时间段缺少实际画面/表演过程")
            if not shot_key:
                errors.append(sid + "：时间段缺少承载镜号")
            # Only inspect camera declarations, not an actor pushing/pulling an object.
            camera_text = inline.split("声音：", 1)[0]
            camera_lines = re.findall(r"(?:摄影机|摄像机|镜头)(?:[^。\n]*)(?:固定|静止|推进|推近|拉远|后退|横移|侧移|跟拍|环绕|摇摄|升降)[^。\n]*", picture_body)
            if not MOVEMENTS.search(camera_text + " ".join(camera_lines)):
                errors.append(sid + "：时间段缺少明确的运镜或固定方式（剪切不等于机位运动）")
            if CONTRADICTIONS.search(compiled):
                errors.append(sid + "：存在“固定机位/镜头”与位移运镜并存的术语矛盾")
        if kind == "生成单元":
            carried = re.search(r"[｜|]\s*承载[：:]\s*([^｜|]*)", title_tail)
            if carried:
                declared_shots = [re.sub(r"^镜头\s*", "", item.strip()) for item in re.split(r"[、,，/\s]+", carried.group(1).strip()) if item.strip() and item.strip() != "镜头"]
                if list(dict.fromkeys(declared_shots)) != list(dict.fromkeys(unit_shots)):
                    errors.append(sid + "：标题承载镜号与时间线镜号或顺序不一致")
        if is_project and schema not in ("generic", "legacy") and "全局配音、配乐与声音规则" in body and music_windows != len(windows):
            errors.append(sid + "：配乐版每个时间窗须写配乐状态，包括停奏")
        if abs(previous - duration) > 0.05:
            errors.append(sid + "：时间线镜尾与标题时长不一致")
        if music_windows and music_windows != len(windows):
            errors.append(sid + "：配乐开启时须在每个镜内时间窗写配乐子项；静默镜可写配乐：无")
    declared = re.search(r"(?:实际总时长|成片时长|总时长)[：:]?\s*(?:约\s*)?(\d+(?:\.\d+)?)\s*秒", body)
    if is_project and schema != "generic" and not declared:
        errors.append("项目参数须明确写出已有总时长字段及秒数（如成片总时长或实际总时长）")
    elif declared and abs(float(declared.group(1)) - total) > 0.5:
        errors.append("总时长与镜长之和不一致：镜头合计 " + str(round(total, 2)) + " 秒")
    return errors

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--mode", choices=["refined"], default="refined", help="兼容技能的精修入口")
    parser.add_argument("--max-unit-seconds", type=float, default=35.0, help="当前采用的生成单元上限")
    parser.add_argument("--require-focal-length", action="store_true", default=True, help="旧命令兼容；数值焦段始终强制校验，支持mm或毫米")
    parser.add_argument("--schema", choices=["auto", "current", "legacy", "generic"], default="auto", help="auto/current检查当前场景级格式；legacy仅供明确保留的旧版，generic保留用户锁定自定义栏目")
    args = parser.parse_args()
    if not math.isfinite(args.max_unit_seconds) or args.max_unit_seconds <= 0:
        parser.error("--max-unit-seconds 必须大于0")
    errors = validate(args.path.read_text(encoding="utf-8"), args.mode, args.max_unit_seconds, args.require_focal_length, args.schema)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("结构与时间校验通过；仍须复查来源、人物演绎、导演效果和连续状态。")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
