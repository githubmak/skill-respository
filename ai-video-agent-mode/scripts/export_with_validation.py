#!/usr/bin/env python3
"""Export a normalized Mode C v4 package, then run the 30-point gate.

Usage:
    python3 export_with_validation.py <user_confirmed_export_md_path> <run_dir>
    python3 export_with_validation.py --regenerate <user_confirmed_export_md_path> <run_dir>

The output path is mandatory and must come from the current user's explicit
confirmation. This script never invents an export location.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from normalize_prompt_package import normalize_package


CHECK_EXPORT = os.path.join(os.path.dirname(__file__), "check_export.py")


def export_with_validation(md_path, run_dir):
    package_path = _find_package(run_dir)
    if not package_path:
        raise SystemExit("Missing prompt package in run directory")
    normalize_package(package_path, package_path)
    package = _load(package_path)
    plan = _load(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"))
    director = _load_optional(os.path.join(run_dir, ".cache", "director", "director_pass.json"))
    config = _load_optional(os.path.join(run_dir, "project_config.json"))
    grid_enabled = _grid_enabled(config)
    grid_packages = _load_optional(os.path.join(run_dir, ".cache", "grid_storyboard", "packages.json")) if grid_enabled else {}
    _write_markdown(md_path, package, plan, director, grid_packages)
    _write_workbook(os.path.splitext(md_path)[0] + ".xlsx", package, plan, director, grid_packages, grid_enabled)

    result = subprocess.run(
        [sys.executable, CHECK_EXPORT, md_path, run_dir],
        text=True,
        capture_output=True,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    if result.returncode:
        print("[EXPORT V4] DELIVERY BLOCKED - fix the reported phase and export again")
        return result.returncode
    print("[EXPORT V4] DELIVERY APPROVED")
    print("[EXPORT V4] Markdown: " + md_path)
    print("[EXPORT V4] XLSX: " + os.path.splitext(md_path)[0] + ".xlsx")
    return 0


def _write_markdown(path, package, plan, director, grid_packages=None):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    shots = package.get("shots", [])
    by_id = {shot.get("subshot_id", ""): shot for shot in shots}
    director_map = {
        item.get("subshot_id", ""): item
        for item in director.get("items", []) if isinstance(item, dict) and item.get("subshot_id")
    }
    ordered_ids = [
        subshot.get("subshot_id", "")
        for plan_shot in plan.get("shots", [])
        for subshot in plan_shot.get("subshots", [])
        if subshot.get("subshot_id", "") in by_id
    ]
    lines = [
        f"# {plan.get('project_name', '')} AI视频提示词包 — Mode C v4",
        "",
        f"画幅：{plan.get('canvas', '')} | 风格：{plan.get('visual_style', '')}",
        "",
        "> Markdown仅导出模型可投喂内容、负面提示词、下一镜转场提示词与台词/OS/OV表演；内部质检与生成配置数据保留在缓存与XLSX质检表中。",
        "",
        "---",
        "",
    ]
    current_scene = None
    ordered_index = {sid: idx for idx, sid in enumerate(ordered_ids)}
    for plan_shot in plan.get("shots", []):
        scene = plan_shot.get("scene", "场景")
        if scene != current_scene:
            lines.extend([f"## {scene}", ""])
            current_scene = scene
        children = [by_id.get(subshot.get("subshot_id", "")) for subshot in plan_shot.get("subshots", [])]
        children = [child for child in children if child]
        total = sum(float(child.get("duration", 0) or 0) for child in children)
        lines.extend([f"### {plan_shot.get('shot_id', '')}（{total:g}秒）", ""])
        for shot in children:
            metadata = shot.get("qa_metadata", {}) if isinstance(shot.get("qa_metadata"), dict) else {}
            dialogue_events = metadata.get("dialogue_events", []) if isinstance(metadata.get("dialogue_events"), list) else []
            next_shot = None
            idx = ordered_index.get(shot.get("subshot_id", ""), -1)
            if idx >= 0 and idx + 1 < len(ordered_ids):
                next_shot = by_id.get(ordered_ids[idx + 1])
            lines.extend([
                f"#### 子镜头 {shot.get('subshot_id', '')}｜{float(shot.get('duration', 0) or 0):g}秒",
                "",
                "**模型提示词**",
                "",
                "```text",
                str(shot.get("full_prompt", "") or ""),
                "```",
                "",
                "**负面提示词**",
                "",
                "```text",
                str(shot.get("negative_prompt", "") or ""),
                "```",
                "",
                "**下一镜转场提示词**",
                "",
                "```text",
                _build_transition_prompt(shot, next_shot),
                "```",
                "",
                "**镜头执行节拍**",
                "",
            ])
            _append_execution_beats(lines, director_map.get(shot.get("subshot_id", ""), {}))
            lines.extend([
                "**台词/OS/OV表演**",
                "",
            ])
            if dialogue_events:
                lines.extend([
                    "| 引用 | 类型 | 人物 | 逐字原文 | 时间窗 | 神态 | 身体状态 | 语气 | 口型同步 |",
                    "|---|---|---|---|---|---|---|---|---|",
                ])
                for event in dialogue_events:
                    lines.append("| " + " | ".join(_md_cell(event.get(field, "")) for field in (
                        "ref", "kind", "speaker", "text", "time_range", "facial_state", "body_state", "delivery", "lip_sync",
                    )) + " |")
                lines.append("")
            else:
                lines.extend(["无。", ""])
        lines.extend(["---", ""])
    _append_grid_packages(lines, grid_packages)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def _append_execution_beats(lines, director_item):
    beats = director_item.get("camera_beat_map", []) if isinstance(director_item, dict) else []
    if not isinstance(beats, list) or not beats:
        lines.extend(["连续镜头，无额外切换。", ""])
        return
    lines.extend(["| 时间窗 | 表演触发 | 视觉主体与落幅 | 镜头响应 | 状态承接 |", "|---|---|---|---|---|"])
    for beat in beats[:3]:
        if not isinstance(beat, dict):
            continue
        lines.append("| %s | %s | %s | %s | %s |" % (
            _md_cell(beat.get("time_range", "")),
            _md_cell(beat.get("trigger", "")),
            _md_cell("%s；%s" % (beat.get("focus_subject", ""), beat.get("framing", ""))),
            _md_cell(beat.get("camera_response", "")),
            _md_cell(beat.get("carryover", "")),
        ))
    lines.append("")


def _append_grid_packages(lines, grid_packages):
    packages = grid_packages.get("packages", []) if isinstance(grid_packages, dict) else []
    if not packages:
        return
    lines.extend(["## 自动九宫格剧情包", ""])
    for package in packages:
        lines.extend([
            f"### {package.get('chain_id', '')}｜{package.get('scene', '')}",
            "",
            "**九宫格总图生图提示词**",
            "",
            "```text",
            str(package.get("grid_prompt", "") or ""),
            "```",
            "",
            "**九宫格负面提示词**",
            "",
            "```text",
            str(package.get("negative_prompt", "") or ""),
            "```",
            "",
            "**九格剧情节拍**",
            "",
            "| 格 | 对应子镜头 | 剧情节拍 |",
            "|---|---|---|",
        ])
        for beat in package.get("beats", []) if isinstance(package.get("beats"), list) else []:
            lines.append("| %s | %s | %s |" % (
                _md_cell(beat.get("panel_id", "")),
                _md_cell(beat.get("source_subshot_id", "")),
                _md_cell(beat.get("description", "")),
            ))
        lines.extend(["", "---", ""])


def _build_transition_prompt(current_shot, next_shot):
    if not next_shot:
        return "无，段落结束。"
    current_meta = current_shot.get("qa_metadata", {}) if isinstance(current_shot.get("qa_metadata"), dict) else {}
    next_meta = next_shot.get("qa_metadata", {}) if isinstance(next_shot.get("qa_metadata"), dict) else {}
    current_contract = current_meta.get("continuity_contract", {}) if isinstance(current_meta.get("continuity_contract"), dict) else {}
    next_contract = next_meta.get("continuity_contract", {}) if isinstance(next_meta.get("continuity_contract"), dict) else {}
    current_end = _shorten(
        current_contract.get("next_carryover") or current_contract.get("end_anchor") or current_meta.get("end_state", "")
    )
    next_start = _shorten(next_contract.get("start_anchor") or next_meta.get("start_state", ""))
    transition_type = _detect_transition_type(current_contract, next_contract, current_shot, next_shot)
    body = [
        f"转场类型：{transition_type}。",
        f"上一镜落幅：{current_end}" if current_end else "上一镜落幅：保持上一镜可见残留。",
        f"下一镜开头：{next_start}" if next_start else "下一镜开头：继承上一镜残留，不复位。",
    ]
    return _shorten(" ".join(body), 180)


def _detect_transition_type(current_contract, next_contract, current_shot, next_shot):
    text = " ".join(str(v or "") for v in (
        current_contract.get("prop_state", ""),
        current_contract.get("next_carryover", ""),
        next_contract.get("start_anchor", ""),
        next_contract.get("eyeline_continuity", ""),
        next_contract.get("lighting_continuity", ""),
        current_shot.get("full_prompt", ""),
        next_shot.get("full_prompt", ""),
    ))
    if any(token in text for token in ("门", "把手", "手机", "外套", "道具", "纸", "刀", "枪", "杯", "领口", "衣角")):
        return "道具接"
    if any(token in text for token in ("视线", "目光", "看向", "回望", "对视")):
        return "视线接"
    if any(token in text for token in ("光", "亮", "暗", "色温", "阴影", "背光", "逆光", "侧光")):
        return "光线接"
    if any(token in text for token in ("说", "台词", "OS", "OV", "声音", "脚步", "关门", "呼吸")):
        return "声桥"
    if any(token in text for token in ("走", "转身", "抬手", "停住", "落步", "前倾", "后仰", "推进", "拉回")):
        return "动作接"
    if any(token in text for token in ("同框", "构图", "站位", "位置", "距离", "屏幕方向")):
        return "同构图接"
    return "硬切"


def _shorten(text, limit=120):
    text = str(text or "").replace("\r", " ").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip("，。；; ") + "…"


def _write_workbook(path, package, plan, director, grid_packages=None, grid_enabled=False):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    shots = package.get("shots", [])
    director_map = {
        item.get("subshot_id", ""): item for item in director.get("items", []) if item.get("subshot_id")
    }
    workbook = Workbook()
    prompts = workbook.active
    prompts.title = "Mode C v4模型提示词"
    prompts.append([
        "主镜头", "子镜头", "时长(s)", "模型提示词", "负面提示词",
        "生成模式", "原生音频", "参考资产",
    ])
    for shot in shots:
        control = shot.get("generation_control", {}) if isinstance(shot.get("generation_control"), dict) else {}
        prompts.append([
            shot.get("shot_id", ""),
            shot.get("subshot_id", ""),
            shot.get("duration", 0),
            shot.get("full_prompt", ""),
            shot.get("negative_prompt", ""),
            control.get("mode", ""),
            control.get("audio_enabled", False),
            json.dumps(control.get("reference_assets", []), ensure_ascii=False),
        ])

    qa = workbook.create_sheet("QA与表演预算")
    qa.append([
        "主镜头", "子镜头", "戏剧目标", "主表演者", "对手", "背景",
        "主动作数", "情绪转折数", "对手反应数", "实体运镜数", "镜头响应数", "起始状态", "终态",
        "表演因果", "表演张力合同", "连续性合同", "抽卡控制", "台词引用", "注意力交接", "打斗连续性",
    ])
    for shot in shots:
        metadata = shot.get("qa_metadata", {}) if isinstance(shot.get("qa_metadata"), dict) else {}
        roles = metadata.get("performance_priority", {}) if isinstance(metadata.get("performance_priority"), dict) else {}
        budget = metadata.get("action_budget", {}) if isinstance(metadata.get("action_budget"), dict) else {}
        qa.append([
            shot.get("shot_id", ""), shot.get("subshot_id", ""), metadata.get("dramatic_goal", ""),
            roles.get("primary", ""), "；".join(roles.get("supporting", [])), "；".join(roles.get("background", [])),
            budget.get("primary_action_count", 0), budget.get("emotion_turn_count", 0),
            budget.get("supporting_reaction_count", 0), budget.get("physical_camera_move_count", 0), budget.get("editorial_response_count", 0),
            metadata.get("start_state", ""), metadata.get("end_state", ""),
            json.dumps(metadata.get("performance_causality", {}), ensure_ascii=False),
            json.dumps(metadata.get("performance_contract", {}), ensure_ascii=False),
            json.dumps(metadata.get("continuity_contract", {}), ensure_ascii=False),
            json.dumps(metadata.get("reroll_control", {}), ensure_ascii=False),
            "；".join(metadata.get("dialogue_refs", [])),
            json.dumps(metadata.get("attention_handoff", {}), ensure_ascii=False),
            json.dumps(metadata.get("fight_continuity", {}), ensure_ascii=False),
        ])

    dialogue_sheet = workbook.create_sheet("台词与OS表演")
    dialogue_sheet.append([
        "主镜头", "子镜头", "引用", "类型", "人物", "逐字原文", "时间窗",
        "人物可见性", "发声时神态", "发声时身体状态", "语气与停顿", "口型同步", "原生音频",
    ])
    for shot in shots:
        metadata = shot.get("qa_metadata", {}) if isinstance(shot.get("qa_metadata"), dict) else {}
        control = shot.get("generation_control", {}) if isinstance(shot.get("generation_control"), dict) else {}
        for event in metadata.get("dialogue_events", []) if isinstance(metadata.get("dialogue_events"), list) else []:
            dialogue_sheet.append([
                shot.get("shot_id", ""), shot.get("subshot_id", ""), event.get("ref", ""),
                event.get("kind", ""), event.get("speaker", ""), event.get("text", ""),
                event.get("time_range", ""), event.get("speaker_visibility", ""),
                event.get("facial_state", ""), event.get("body_state", ""), event.get("delivery", ""),
                event.get("lip_sync", False), control.get("audio_enabled", False),
            ])

    director_sheet = workbook.create_sheet("导演连续性")
    director_sheet.append(["主镜头", "子镜头", "景别", "机位", "运镜", "镜头模式", "表演链", "镜头执行节拍", "序列承接", "轴线", "灯光", "落幅"])
    for shot in shots:
        item = director_map.get(shot.get("subshot_id", ""), {})
        director_sheet.append([
            shot.get("shot_id", ""), shot.get("subshot_id", ""), item.get("shot_size", ""),
            item.get("camera_position", item.get("camera_relative_pos", "")),
            item.get("movement_detail", item.get("camera", "")), item.get("editorial_mode", ""),
            json.dumps(item.get("performance_chain", {}), ensure_ascii=False),
            json.dumps(item.get("camera_beat_map", []), ensure_ascii=False),
            json.dumps(item.get("sequence_context", {}), ensure_ascii=False), item.get("axis_space", ""),
            item.get("lighting", ""), item.get("end_state", ""),
        ])

    if grid_enabled:
        grid_sheet = workbook.create_sheet("九宫格剧情分镜图")
        grid_sheet.append(["分镜编号", "场景", "关联子镜头", "九宫格总图生图提示词", "九宫格负面提示词", "格", "对应子镜头", "剧情节拍"])
        packages = grid_packages.get("packages", []) if isinstance(grid_packages, dict) else []
        for package in packages:
            beats = package.get("beats", []) if isinstance(package.get("beats"), list) else []
            for index, beat in enumerate(beats):
                grid_sheet.append([
                    package.get("chain_id", "") if index == 0 else "",
                    package.get("scene", "") if index == 0 else "",
                    "；".join(package.get("subshot_ids", [])) if index == 0 else "",
                    package.get("grid_prompt", "") if index == 0 else "",
                    package.get("negative_prompt", "") if index == 0 else "",
                    beat.get("panel_id", ""), beat.get("source_subshot_id", ""), beat.get("description", ""),
                ])

    header_fill = PatternFill("solid", fgColor="1F4E79")
    for sheet in workbook.worksheets:
        sheet.freeze_panes = "A2"
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = header_fill
        for row in sheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
        for column in sheet.columns:
            letter = column[0].column_letter
            max_len = max(len(str(cell.value or "")) for cell in column)
            sheet.column_dimensions[letter].width = min(max(max_len + 2, 10), 80)
    workbook.save(path)


def _md_cell(value):
    text = str(value).replace("\r", " ").replace("\n", " ")
    return text.replace("|", "\\|")


def _find_package(run_dir):
    for relative in (
        ".cache/composer/merged.prompt_package.json",
        ".cache/composer/prompt_package.json",
        ".cache/prompt_package.json",
    ):
        path = os.path.join(run_dir, relative)
        if os.path.exists(path):
            return path
    return ""


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _load_optional(path):
    return _load(path) if os.path.exists(path) else {"items": []}


def _grid_enabled(config):
    grid = config.get("storyboard_grid", {}) if isinstance(config, dict) else {}
    return isinstance(grid, dict) and grid.get("enabled") is True


if __name__ == "__main__":
    args = [argument for argument in sys.argv[1:] if argument != "--regenerate"]
    if len(args) != 2:
        print("Usage: python3 export_with_validation.py <user_confirmed_export_md> <run_dir>")
        print("ERROR: output path is mandatory. Ask the user for the export file location before running.")
        sys.exit(2)
    sys.exit(export_with_validation(args[0], args[1]))
