#!/usr/bin/env python3
"""Atomically export model-authored Seedance text without semantic transforms."""

import hashlib
import json
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(__file__))
from contract_registry import PROMPT_CONTRACT_VERSION
from materialize_master_tasks import materialize as materialize_master_tasks
from normalize_prompt_package import normalize_package
from pipeline_runtime import atomic_json
from pipeline_state import AGENT_PHASES, load_state
from record_batch_provenance import verify as verify_provenance
from seedance_target import TARGET_LABELS, normalize_target, variant_paths
from validate_deterministic_package import selected_seedance_prompt, validate_package
from validate_master_tasks import validate as validate_master_tasks


def export_with_validation(md_path, run_dir):
    package_path = _find_package(run_dir)
    if not package_path:
        raise SystemExit("Missing prompt package in run directory")
    _require_agent_dispatch_gates(run_dir, package_path)
    source_sha256 = _sha256(package_path)
    normalize_package(package_path, package_path)
    _record_normalization_provenance(package_path, source_sha256)
    master_path, master_package = materialize_master_tasks(run_dir, source_path=package_path)
    master_issues = validate_master_tasks(run_dir)
    if master_issues:
        raise SystemExit("Invalid model-authored main-shot package: " + "; ".join(master_issues[:8]))
    deterministic = validate_package(
        package_path,
        run_dir=run_dir,
        report_path=os.path.join(run_dir, ".cache", "export", "deterministic_pre_export.json"),
        require_editor=True,
    )
    if not deterministic["pass"]:
        for issue in deterministic["issues"][:30]:
            print("  - " + issue)
        return 1

    plan = _load(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"))
    config = _load(os.path.join(run_dir, "project_config.json"))
    target = normalize_target(config.get("seedance_target", "auto"))
    feed_paths, index_path = variant_paths(md_path, target)
    destination_dir = os.path.dirname(os.path.abspath(md_path))
    os.makedirs(destination_dir, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix=".jimeng-export-", dir=destination_dir)
    temporary_feeds = {
        version: os.path.join(temp_dir, os.path.basename(path))
        for version, path in feed_paths.items()
    }
    reports = []
    try:
        for version, path in temporary_feeds.items():
            _write_master_markdown(path, master_package, plan, reports, version)
            _verify_passthrough_markdown(path, master_package, version)
        temporary_xlsx = os.path.join(temp_dir, os.path.splitext(os.path.basename(md_path))[0] + ".xlsx")
        xlsx_written = _write_workbook(temporary_xlsx, master_package, plan, {}, target)
        temporary_concise = os.path.join(temp_dir, os.path.splitext(os.path.basename(md_path))[0] + ".concise.md")
        temporary_engineering = os.path.join(temp_dir, os.path.splitext(os.path.basename(md_path))[0] + ".engineering.md")
        if target != "both":
            only_target = next(iter(feed_paths))
            _write_concise_markdown(temporary_concise, master_package, plan, only_target)
            _write_engineering_review(temporary_engineering, master_package, reports)
        temporary_index = ""
        if target == "both":
            temporary_index = os.path.join(temp_dir, os.path.basename(index_path))
            _write_target_index(temporary_index, plan, feed_paths)

        for version, destination in feed_paths.items():
            os.replace(temporary_feeds[version], destination)
        if target == "both":
            os.replace(temporary_index, index_path)
        else:
            os.replace(temporary_concise, os.path.splitext(md_path)[0] + ".concise.md")
            os.replace(temporary_engineering, os.path.splitext(md_path)[0] + ".engineering.md")
        if xlsx_written:
            xlsx_destination = os.path.splitext(md_path)[0] + ".xlsx"
            os.replace(temporary_xlsx, xlsx_destination)
            if target == "both":
                for destination in feed_paths.values():
                    variant_xlsx = os.path.splitext(destination)[0] + ".xlsx"
                    if os.path.abspath(variant_xlsx) != os.path.abspath(xlsx_destination):
                        shutil.copyfile(xlsx_destination, variant_xlsx)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    report_path = os.path.join(run_dir, ".cache", "export", "prompt_passthrough_report.json")
    atomic_json(report_path, {
        "contract_version": PROMPT_CONTRACT_VERSION,
        "pass": True,
        "semantic_transform": False,
        "shots": reports,
    })
    _record_export_result(run_dir, md_path, report_path, target, feed_paths, index_path)
    print("[EXPORT] DELIVERY APPROVED - model-authored text preserved")
    for version, path in feed_paths.items():
        print("[EXPORT] Markdown %s: %s" % (TARGET_LABELS[version], path))
    print("[EXPORT] Master tasks: " + master_path)
    return 0


def _build_direct_copy_prompt(task, plan=None, compile_reports=None, seedance_target="auto"):
    text = selected_seedance_prompt(task, seedance_target)
    if not text.strip():
        raise ValueError("CREATIVE_REWRITE_REQUIRED: model-authored Seedance prompt is missing")
    if len(text) > 700:
        raise ValueError("CREATIVE_REWRITE_REQUIRED: seedance_prompt %d>700 chars" % len(text))
    if isinstance(compile_reports, list):
        source_field = "seedance_prompt"
        variants = task.get("seedance_prompt_variants", {})
        if seedance_target in {"2.0", "2.5"} and isinstance(variants, dict) and variants.get(seedance_target):
            source_field = "seedance_prompt_variants.%s" % seedance_target
        compile_reports.append({
            "shot_id": str(task.get("shot_id", "")),
            "subshot_id": str(task.get("subshot_id", "")),
            "target": seedance_target,
            "source_field": source_field,
            "char_count": len(text),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "semantic_transform": False,
        })
    return text


def _build_director_card(task, plan=None, compile_reports=None, seedance_target="auto"):
    card = task.get("director_card", "")
    if not isinstance(card, str) or not card.strip():
        raise ValueError("CREATIVE_REWRITE_REQUIRED: director_card is missing")
    if len(card) > 500:
        raise ValueError("CREATIVE_REWRITE_REQUIRED: director_card %d>500 chars" % len(card))
    return card


def _write_master_markdown(path, master_package, plan, compile_reports=None, seedance_target="auto"):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tasks = {str(item.get("shot_id", "")): item for item in master_package.get("shots", []) if isinstance(item, dict)}
    planned = plan.get("shots", []) if isinstance(plan.get("shots"), list) else []
    order = [str(item.get("shot_id", "")) for item in planned if str(item.get("shot_id", "")) in tasks]
    order.extend(shot_id for shot_id in tasks if shot_id not in order)
    lines = [
        "# %s 即梦投喂分镜｜%s" % (plan.get("project_name", ""), TARGET_LABELS[seedance_target]), "",
        "## 项目参数", "",
        "- 画幅：%s" % plan.get("canvas", ""),
        "- 风格：%s" % plan.get("visual_style", ""),
        "- 提示词来源：模型创作原文；导出未做语义变换。", "",
        "## 分镜投喂卡", "",
    ]
    for shot_id in order:
        task = tasks[shot_id]
        prompt = _build_direct_copy_prompt(task, plan, compile_reports, seedance_target)
        card = _build_director_card(task, plan, compile_reports, seedance_target)
        lines.extend([
            "### %s｜%gs" % (shot_id, float(task.get("duration", 0) or 0)), "",
            "【画面描述｜直接复制】", "", prompt, "",
            "【导演卡｜直接复制｜≤500字】", "", card, "",
            "【负面提示词｜直接复制】", "", str(task.get("negative_prompt", "")), "",
            "【逐字台词／OS／OV／系统音】", "",
        ])
        events = (task.get("qa_metadata", {}) or {}).get("dialogue_events", [])
        if isinstance(events, list) and events:
            lines.extend(["| 引用 | 类型 | 人物 | 逐字原文 |", "|---|---|---|---|"])
            for event in events:
                if isinstance(event, dict):
                    lines.append("| %s | %s | %s | %s |" % tuple(
                        _md_cell(event.get(field, "")) for field in ("ref", "kind", "speaker", "text")
                    ))
        else:
            lines.append("无。")
        lines.extend(["", "【模型完整导演表达】", "", str(task.get("full_prompt", "")), "", "---", ""])
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def _write_concise_markdown(path, master_package, plan, seedance_target="auto"):
    lines = ["# %s 导演卡" % plan.get("project_name", ""), ""]
    for task in master_package.get("shots", []):
        if not isinstance(task, dict):
            continue
        lines.extend([
            "## %s｜%gs" % (task.get("shot_id", ""), float(task.get("duration", 0) or 0)), "",
            _build_director_card(task), "",
            "【负面提示词】", "", str(task.get("negative_prompt", "")), "",
        ])
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def _write_engineering_review(path, master_package, reports):
    lines = ["# 工程交付报告", "", "> 只含字符数、字段来源和哈希，不评价创作质量。", ""]
    for report in reports:
        lines.extend([
            "## %s｜%s" % (report.get("shot_id", ""), report.get("target", "")), "",
            "- 来源字段：`%s`" % report.get("source_field", ""),
            "- 字符数：%s" % report.get("char_count", 0),
            "- SHA-256：`%s`" % report.get("sha256", ""),
            "- 语义变换：否", "",
        ])
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def _write_target_index(path, plan, feed_paths):
    lines = [
        "# %s 双版本文件索引" % plan.get("project_name", ""), "",
        "| 目标 | 文件 | 模型字段 |", "|---|---|---|",
        "| Seedance 2.0 | `%s` | `seedance_prompt_variants[\"2.0\"]` |" % os.path.basename(feed_paths["2.0"]),
        "| Seedance 2.5 | `%s` | `seedance_prompt_variants[\"2.5\"]` |" % os.path.basename(feed_paths["2.5"]),
        "", "工程只选择字段并原样排版，不解释或改写版本差异。", "",
    ]
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def _write_workbook(path, package, plan, director=None, seedance_target="auto"):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font
    except ImportError:
        return False
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    workbook = Workbook()
    prompts = workbook.active
    prompts.title = "AI视频模型提示词"
    prompts.append([
        "主镜头", "子镜头", "时长(s)", "目标提示词｜模型原文",
        "Seedance 2.0｜模型原文", "Seedance 2.5｜模型原文", "导演卡｜模型原文", "负面提示词｜模型原文",
    ])
    dialogue = workbook.create_sheet("逐字台词")
    dialogue.append(["主镜头", "引用", "类型", "人物", "逐字原文"])
    for task in package.get("shots", []):
        if not isinstance(task, dict):
            continue
        variants = task.get("seedance_prompt_variants", {}) if isinstance(task.get("seedance_prompt_variants"), dict) else {}
        selected = ""
        if seedance_target != "both":
            selected = selected_seedance_prompt(task, seedance_target)
        prompts.append([
            task.get("shot_id", ""), task.get("subshot_id", ""), task.get("duration", 0), selected,
            variants.get("2.0", ""), variants.get("2.5", ""), task.get("director_card", ""), task.get("negative_prompt", ""),
        ])
        for event in (task.get("qa_metadata", {}) or {}).get("dialogue_events", []):
            if isinstance(event, dict):
                dialogue.append([task.get("shot_id", ""), event.get("ref", ""), event.get("kind", ""), event.get("speaker", ""), event.get("text", "")])
    for sheet in workbook.worksheets:
        sheet.freeze_panes = "A2"
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for row in sheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
        for column in sheet.columns:
            letter = column[0].column_letter
            sheet.column_dimensions[letter].width = min(max(max(len(str(cell.value or "")) for cell in column) + 2, 12), 60)
    workbook.save(path)
    return True


def _verify_passthrough_markdown(path, package, target):
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    for task in package.get("shots", []):
        if not isinstance(task, dict):
            continue
        for field_text, label in (
            (selected_seedance_prompt(task, target), "seedance_prompt"),
            (task.get("director_card", ""), "director_card"),
        ):
            if not isinstance(field_text, str) or field_text not in text:
                raise ValueError("%s: %s changed or missing during layout" % (task.get("shot_id", ""), label))


def _record_export_result(run_dir, md_path, report_path="", seedance_target="auto", feed_paths=None, index_path=""):
    package_path = _find_package(run_dir)
    feed_paths = {key: os.path.abspath(value) for key, value in (feed_paths or {seedance_target: md_path}).items()}
    primary = next(iter(feed_paths.values())) if len(feed_paths) == 1 else os.path.abspath(index_path)
    atomic_json(os.path.join(run_dir, ".cache", "export", "result.json"), {
        "pass": True,
        "exported_at": time.time(),
        "seedance_target": seedance_target,
        "markdown_path": primary,
        "markdown_sha256": _sha256(primary),
        "markdown_paths": feed_paths,
        "markdown_sha256_by_target": {key: _sha256(value) for key, value in feed_paths.items()},
        "index_markdown_path": os.path.abspath(index_path) if index_path else "",
        "package_sha256": _sha256(package_path),
        "xlsx_path": os.path.splitext(os.path.abspath(md_path))[0] + ".xlsx",
        "passthrough_report": os.path.abspath(report_path) if report_path else "",
    })


def _require_agent_dispatch_gates(run_dir, package_path):
    state = load_state(run_dir)
    incomplete = [phase for phase in AGENT_PHASES if state.get("phases", {}).get(phase, {}).get("status") != "done"]
    if incomplete:
        raise SystemExit("DISPATCH_GATE: Agent phases are incomplete: " + ", ".join(sorted(incomplete)))
    manifest_path = package_path + ".merge_provenance.json"
    manifest = _load_optional(manifest_path)
    if not manifest or manifest.get("output_path") != os.path.abspath(package_path):
        raise SystemExit("DISPATCH_GATE: verified merge provenance is required before export")
    if manifest.get("output_sha256") != _sha256(package_path):
        raise SystemExit("DISPATCH_GATE: prompt package changed after verified merge")
    sources = manifest.get("source_batches")
    if not isinstance(sources, list) or not sources:
        raise SystemExit("DISPATCH_GATE: merge provenance has no verified worker batches")
    for source in sources:
        batch_path = source.get("batch_path") if isinstance(source, dict) else ""
        valid, reason, _record = verify_provenance(batch_path) if batch_path and os.path.exists(batch_path) else (False, "batch missing", None)
        if not valid:
            raise SystemExit("DISPATCH_GATE: source worker batch is invalid: " + reason)


def _record_normalization_provenance(package_path, source_sha256):
    manifest_path = package_path + ".merge_provenance.json"
    manifest = _load_optional(manifest_path)
    if not manifest or manifest.get("output_sha256") != source_sha256:
        raise SystemExit("DISPATCH_GATE: package changed before deterministic serialization")
    current_hash = _sha256(package_path)
    manifest["output_sha256"] = current_hash
    manifest["serialization"] = {
        "name": "normalize_prompt_package",
        "semantic_transform": False,
        "input_sha256": source_sha256,
        "output_sha256": current_hash,
        "recorded_at": time.time(),
    }
    atomic_json(manifest_path, manifest)


def _find_package(run_dir):
    for relative in (
        ".cache/composer/merged.prompt_package.json",
        ".cache/composer/prompt_package.json",
        ".cache/prompt_package.json",
    ):
        path = os.path.join(run_dir, relative)
        if os.path.isfile(path):
            return path
    return ""


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _load_optional(path):
    try:
        return _load(path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _md_cell(value):
    return str(value or "").replace("|", "\\|").replace("\r", " ").replace("\n", "<br>")


if __name__ == "__main__":
    args = [value for value in sys.argv[1:] if value != "--regenerate"]
    if len(args) != 2:
        raise SystemExit("usage: export_with_validation.py [--regenerate] <confirmed.md> <run_dir>")
    raise SystemExit(export_with_validation(args[0], args[1]))
