"""Hybrid deterministic + LLM review gate.

Deterministic scripts catch mechanical violations. The generated LLM review
packet asks an editor agent to judge semantic continuity and story fit.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from continuity_check import run as continuity_run
from enhance_performance import audit as performance_audit
from validate_prompt_package import validate as validate_prompt_package


LLM_REVIEW_PHASES = {"qa_integration", "prompt_composer", "editor_pass2", "validate"}


def run(run_dir, phase=None, require_llm=False):
    """Run hybrid gate and return a normalized gate result."""
    result = {
        "pass": True,
        "deterministic_issues": [],
        "llm_review_packet": None,
        "llm_review_result": None,
        "llm_required": bool(require_llm),
        "issues": [],
    }

    prompt_path = _find_file(run_dir, [
        "prompt_package.json",
        os.path.join(".cache", "prompt_package.json"),
        os.path.join(".cache", "prompt", "prompt_package.json"),
    ])
    shot_plan_path = _find_file(run_dir, [
        "shot_plan.json",
        os.path.join(".cache", "orchestrator", "shot_plan.json"),
    ])
    director_path = _find_file(run_dir, [
        os.path.join(".cache", "director", "director_pass.json"),
        "director_pass.json",
    ])

    if prompt_path:
        for iss in validate_prompt_package(prompt_path, shot_plan_path):
            _add_issue(result, "prompt_package", iss, "blocking")
        try:
            audit_result = performance_audit(prompt_path)
            for item in audit_result.get("shot_size_blocking", []):
                _add_issue(result, "performance", item, "blocking")
            for item in audit_result.get("items_flagged", []):
                text = str(item)
                if "OV/OS" in text or "blocking" in text:
                    _add_issue(result, "performance", item, "blocking")
        except Exception as exc:
            _add_issue(result, "performance", str(exc), "warning")

    if director_path:
        try:
            warnings, errors, issues = continuity_run(run_dir, dry=False)
            for iss in issues:
                severity = "blocking" if "AXIS_CROSSING" in str(iss) or errors else "warning"
                _add_issue(result, "continuity", iss, severity)
        except Exception as exc:
            _add_issue(result, "continuity", str(exc), "warning")

    deterministic_blocking = any(i["severity"] == "blocking" for i in result["deterministic_issues"])
    if phase in LLM_REVIEW_PHASES or prompt_path or director_path:
        result["llm_review_packet"] = _write_llm_review_packet(
            run_dir, phase, prompt_path, shot_plan_path, director_path, result["deterministic_issues"], skip_semantic=deterministic_blocking
        )
        llm_result_path = os.path.join(run_dir, ".cache", "review", "llm_gate_result.json")
        if deterministic_blocking:
            result["llm_required"] = False
        elif os.path.exists(llm_result_path):
            with open(llm_result_path, "r", encoding="utf-8-sig") as f:
                llm_result = json.load(f)
            result["llm_review_result"] = llm_result
            for item in llm_result.get("blocking", []):
                _add_issue(result, "llm_review", item, "blocking")
            for item in llm_result.get("warnings", []):
                _add_issue(result, "llm_review", item, "warning")
            if llm_result.get("pass") is False:
                _add_issue(result, "llm_review", "LLM review marked pass=false", "blocking")
        elif require_llm:
            _add_issue(result, "llm_review", "Missing .cache/review/llm_gate_result.json", "blocking")

    result["pass"] = not any(i["severity"] == "blocking" for i in result["issues"])
    return result


def _find_file(run_dir, candidates):
    for rel in candidates:
        path = os.path.join(run_dir, rel)
        if os.path.exists(path):
            return path
    return None


def _add_issue(result, check, detail, severity):
    issue = {"check": check, "severity": severity, "msg": str(detail)}
    result["issues"].append(issue)
    if check != "llm_review":
        result["deterministic_issues"].append(issue)


def _write_llm_review_packet(run_dir, phase, prompt_path, shot_plan_path, director_path, deterministic_issues, skip_semantic=False):
    review_dir = os.path.join(run_dir, ".cache", "review")
    os.makedirs(review_dir, exist_ok=True)
    packet_path = os.path.join(review_dir, "llm_gate_review.md")
    result_path = os.path.join(review_dir, "llm_gate_result.json")
    lines = [
        "# LLM Gate Review",
        "",
        "你是 AI 视频分镜最终门禁审查 Agent。脚本已经完成确定性检查；你只审查需要语义判断的问题。",
        "",
        "## 输入文件",
        "- phase: `%s`" % (phase or "unknown"),
        "- shot_plan: `%s`" % (shot_plan_path or "missing"),
        "- director_pass: `%s`" % (director_path or "missing"),
        "- prompt_package: `%s`" % (prompt_path or "missing"),
        "",
        "## 已由脚本检查的问题",
    ]
    if deterministic_issues:
        for issue in deterministic_issues[:40]:
            lines.append("- [%s] %s: %s" % (issue["severity"], issue["check"], issue["msg"]))
    else:
        lines.append("- 无脚本阻断项。")
    if skip_semantic:
        lines.extend([
            "",
            "## 当前动作",
            "脚本门禁已有 blocking。先修复上方确定性问题；本轮不要进行语义复审，避免重复消耗和结论冲突。",
            "",
            "修复后重新运行 `hybrid_gate.py`，脚本 blocking 清零后再进入 LLM 语义复审。",
        ])
    else:
        lines.extend([
            "",
            "## 你必须审查",
            "只审查脚本无法可靠判断的语义问题，不重复判定字段长度、台词逐字匹配、OV/OS口型、景别关键词等脚本项。",
            "1. 相邻镜头人物位置、视线、出入画方向是否存在观感空间跳变。",
            "2. 人物表情、动作、语气、灯光是否符合当前场景事件和角色状态。",
            "3. 无声动作是否改变了剧情结果、角色动机或台词含义。",
            "4. 多镜头连续情绪是否有触发、变化、残留，而不是模板重复。",
            "",
            "## 输出格式",
            "将结果写入：`%s`" % result_path,
            "",
            "```json",
            "{",
            "  \"pass\": true,",
            "  \"blocking\": [],",
            "  \"warnings\": [],",
            "  \"repair_targets\": [",
            "    {\"subshot_id\": \"S1-01-01\", \"send_back_to\": \"camera_movement|emotion_analysis|scene_analysis|prompt_composer|editor_pass2\", \"reason\": \"...\"}",
            "  ]",
            "}",
            "```",
        ])
    with open(packet_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return packet_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: hybrid_gate.py <run_dir> [phase] [--require-llm]")
        sys.exit(1)
    gate = run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None, "--require-llm" in sys.argv)
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    sys.exit(0 if gate["pass"] else 1)
