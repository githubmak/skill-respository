#!/usr/bin/env python3
"""Check storyboard structure, timing, basic composition, and language conflicts."""
import argparse
import re
import sys
from pathlib import Path

UNIT = re.compile(
    r"^###\s+(生成单元)\s+([^｜|\n]+?)\s*[｜|]\s*时长[：:]\s*"
    r"(\d+(?:\.\d+)?)\s*(?:秒|[sS])([^\n]*)",
    re.M,
)
WINDOW = re.compile(r"^\s{2,}-\s*(\d+(?:\.\d+)?)\s*[—–-]\s*(\d+(?:\.\d+)?)秒\s*[｜|]\s*(.+)$", re.M)
SIZES = re.compile(r"大特写|特写|近中景|中近景|近景|中全景|大全景|全景|中景|远景|半身")
MOVEMENTS = re.compile(r"固定|静止|推|拉|移|跟拍|环绕|升降|摇|俯仰|甩|穿越|变焦|手持|轨道|航拍|锁定|急停")
CONTRADICTIONS = re.compile(
    r"固定(?:机位|镜头)(?:缓慢|快速|持续|同时)?"
    r"(?:横移|侧移|推进|推近|拉远|后退|环绕|升降|跟拍)"
)
FIELDS = ["起幅与连续性", "摄影与构图", "光影、环境色彩与材质", "画面与表演时间线", "台词与声音层次", "落幅状态"]
GLOBAL = ["项目直投参数", "全局摄影规则", "全局影调", "全局光影", "全局环境色彩", "全局正向提示词", "全局负面提示词"]

def validate(raw, mode):
    errors = []
    comments = re.findall(r"<!--.*?-->", raw, re.S)
    body = re.sub(r"<!--.*?-->", "", raw, flags=re.S).lstrip()
    if comments:
        errors.append("精修正文仍包含HTML交接注释")
    is_project = bool(
        re.match(r"# 《.+》[^\n]*Seedance 独立直投版", body)
        or re.search(r"^## 项目直投参数\s*$", body, re.M)
        or re.search(r"^# 场景[^\n]+", body, re.M)
    )
    if is_project:
        if not re.match(r"# 《.+》[^\n]*Seedance 独立直投版", body):
            errors.append("正式标题不符合Seedance独立直投版格式")
        positions = []
        for key in GLOBAL:
            found = re.search(r"^## " + re.escape(key) + r"\s*$", body, re.M)
            if not found:
                errors.append("缺少全局栏目：" + key)
            else:
                positions.append(found.start())
        if positions != sorted(positions):
            errors.append("全局栏目顺序不正确")
        scenes = list(re.finditer(r"^# 场景[^\n]+", body, re.M))
        if not scenes:
            errors.append("缺少场景标题")
        for i, scene in enumerate(scenes):
            section = body[scene.end():scenes[i+1].start() if i+1 < len(scenes) else len(body)]
            for key in ["场景资产图提示词", "道具资产图提示词", "场景空间位置关系"]:
                if not re.search(r"^## " + re.escape(key), section, re.M):
                    errors.append(scene.group(0) + "：缺少场景栏目 " + key)
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
        if duration <= 0 or duration > 35:
            errors.append(sid + "：生成单元时长必须大于0且不超过35秒")
        text = body[match.end():matches[i+1].start() if i+1 < len(matches) else len(body)]
        for field in FIELDS:
            if not re.search(r"^- " + re.escape(field) + r"[：:]", text, re.M):
                errors.append(sid + "：缺少字段 " + field)
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
        for j, window in enumerate(windows):
            start, end = float(window.group(1)), float(window.group(2))
            window_text = window.group(3)
            if abs(start - previous) > 0.05 or end <= start:
                errors.append(sid + "：时间段不连续或起止无效")
            previous = end
            if not re.search(r"\d+(?:\.\d+)?\s*mm", window_text) or not SIZES.search(window_text):
                errors.append(sid + "：时间段须明确焦距、景别和运镜")
            segment = content[window.end():windows[j+1].start() if j+1 < len(windows) else len(content)]
            compiled = window_text + "\n" + segment
            if not re.search(r"声音[：:]", compiled):
                errors.append(sid + "：时间段缺少声音描述")
            visual = re.split(r"声音[：:]", compiled, maxsplit=1)[0].strip()
            visual_parts = [part.strip() for part in re.split(r"[｜|]", visual)]
            if len(visual_parts) < 3 or not "".join(visual_parts[2:]).strip():
                errors.append(sid + "：时间段缺少实际画面/表演过程")
            else:
                if not visual_parts[0]:
                    errors.append(sid + "：时间段缺少承载镜号")
                if not MOVEMENTS.search("".join(visual_parts[2:])):
                    errors.append(sid + "：时间段缺少明确的运镜或固定方式")
            if CONTRADICTIONS.search(compiled):
                errors.append(sid + "：存在“固定机位/镜头”与位移运镜并存的术语矛盾")
        if abs(previous - duration) > 0.05:
            errors.append(sid + "：时间线镜尾与标题时长不一致")
    declared = re.search(r"(?:实际总时长|成片时长|总时长)[：:]\s*(?:约\s*)?(\d+(?:\.\d+)?)\s*秒", body)
    if is_project and not declared:
        errors.append("项目参数须明确写出 实际总时长：X秒")
    elif declared and abs(float(declared.group(1)) - total) > 0.5:
        errors.append("总时长与镜长之和不一致：镜头合计 " + str(round(total, 2)) + " 秒")
    return errors

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    errors = validate(args.path.read_text(encoding="utf-8"), "refined")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("结构与时间校验通过；仍须复查来源、人物演绎、导演效果和连续状态。")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
