"""Validate prompt package completeness and consistency."""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(__file__))
from modec_v4 import attention_handoff_issues, camera_competition_issues, dialogue_event_issues, performance_causality_issues
from shot_semantics import quality_contract as derive_quality_contract


QUOTE_RE = re.compile(r"[「『“\"]([^」』”\"]{1,120})[」』”\"]")
LIP_KEYS = ["口型", "嘴型", "唇部", "嘴唇", "唇齿", "张嘴", "开口", "口唇"]
OVOS_KEYS = ["OV", "OS", "旁白", "画外音", "内心独白", "内心声"]


def _load_shot_plan_dialogues(path):
    if not path or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    return data.get("dialogue_map", {}) or {}


def _load_plan_items(path):
    if not path or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8-sig") as handle:
        plan = json.load(handle)
    return {
        subshot.get("subshot_id", ""): subshot
        for shot in plan.get("shots", [])
        for subshot in shot.get("subshots", [])
        if isinstance(subshot, dict) and subshot.get("subshot_id")
    }


def _normalize_dialogue_text(text):
    if not text:
        return ""
    text = re.sub(r"^\[[^\]]+\]\s*", "", str(text).strip())
    text = re.sub(r"^[^：:]{1,12}[：:]\s*", "", text)
    return re.sub(r"\s+", "", text)


def _extract_extra_quoted_text(text, expected_lines):
    expected = {_normalize_dialogue_text(x) for x in expected_lines if _normalize_dialogue_text(x)}
    extras = []
    for q in QUOTE_RE.findall(text or ""):
        qn = _normalize_dialogue_text(q)
        if qn and qn not in expected:
            extras.append(q)
    return extras


def _has_ovos_lip_sync(text):
    if not text:
        return False
    has_ovos = any(k in text for k in OVOS_KEYS)
    has_lip = any(k in text for k in LIP_KEYS)
    has_safe = any(k in text for k in ["无口型", "不驱动嘴唇", "不驱动口型", "无需口型", "不需要口型"])
    return has_ovos and has_lip and not has_safe


def validate(pkg_path, shot_plan_path=None):
    """Validate a prompt package JSON file.

    Checks:
      1. JSON structure valid
      2. All items have required fields
      3. merged_full_prompts covers all shot_ids
      4. Duration totals match

    Returns:
        list of issues [(subshot_id, field, value, expected)]
    """
    if not os.path.exists(pkg_path):
        return [("FILE", "not_found", 0, "")]

    try:
        with open(pkg_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [("JSON", "parse_error", 0, str(e))]

    issues = []
    dialogue_map = _load_shot_plan_dialogues(shot_plan_path)
    plan_items = _load_plan_items(shot_plan_path)
    if not dialogue_map:
        dialogue_map = data.get("dialogue_map", {}) or {}
    items = data.get("shots", data.get("items", []))
    shot_ids = set()
    package_subshot_ids = set()
    required_prompt_fields = [
        "full_prompt", "negative_prompt", "qa_metadata", "generation_control",
        "shot_id", "subshot_id", "duration",
    ]

    for item in items:
        sid = item.get("subshot_id", "?")
        if sid and sid != "?":
            package_subshot_ids.add(sid)
        shot_ids.add(item.get("shot_id", "?"))

        for field in required_prompt_fields:
            if field not in item or item.get(field) is None:
                issues.append((sid, field, "missing", "required"))

        fp = item.get("full_prompt", "")
        metadata = item.get("qa_metadata", {})
        metadata = metadata if isinstance(metadata, dict) else {}
        if metadata.get("editorial_mode") not in ("continuous_take", "motivated_sequence"):
            issues.append((sid, "qa_metadata.editorial_mode", metadata.get("editorial_mode"), "continuous_take|motivated_sequence"))
        if not isinstance(metadata.get("camera_beat_map"), list):
            issues.append((sid, "qa_metadata.camera_beat_map", type(metadata.get("camera_beat_map")).__name__, "list"))
        quality_contract = metadata.get("quality_contract")
        if not isinstance(quality_contract, dict) or not quality_contract.get("profile"):
            issues.append((sid, "qa_metadata.quality_contract", "missing", "typed quality contract"))
        elif sid in plan_items and quality_contract != derive_quality_contract(plan_items[sid]):
            issues.append((sid, "qa_metadata.quality_contract", "source_mismatch", "source-derived exact contract"))
        evidence = metadata.get("quality_evidence")
        if not isinstance(evidence, dict):
            issues.append((sid, "qa_metadata.quality_evidence", "missing", "map every required evidence to prompt sections"))
        elif isinstance(quality_contract, dict):
            for requirement in quality_contract.get("required_evidence", []):
                mapped = evidence.get(requirement)
                if not isinstance(mapped, dict):
                    issues.append((sid, "qa_metadata.quality_evidence", requirement, "section + grounded fragment"))
                    continue
                section = mapped.get("section")
                fragment = str(mapped.get("fragment", "") or "").strip()
                sections = {label: content for label, content in re.findall(r"(?:^|\n\n)([^：\n]+)[：:]([\s\S]*?)(?=\n\n[^\n]+[：:]|$)", fp)}
                if section not in sections or len(fragment) < 3 or fragment not in sections[section]:
                    issues.append((sid, "qa_metadata.quality_evidence", requirement, "grounded fragment in declared section"))
        if len(fp) < 120 or len(fp) > 1100:
            issues.append((sid, "full_prompt.len", len(fp), "120-1100"))
        if "负面提示词" in fp or "自包含验证" in fp:
            issues.append((sid, "full_prompt.pollution", "v3/negative section", "model-facing v4 only"))
        for problem in camera_competition_issues(fp, metadata.get("editorial_mode", item.get("editorial_mode", "continuous_take"))):
            issues.append((sid, "camera.competition", problem, "single executable camera strategy"))

        dur = item.get("duration", 0)
        if not isinstance(dur, (int, float)) or dur <= 0:
            issues.append((sid, "duration", dur, ">0"))

        for problem in performance_causality_issues(metadata):
            issues.append((sid, "performance_causality", problem, "complete causal performance audit"))
        for problem in attention_handoff_issues(metadata, fp):
            issues.append((sid, "attention_handoff", problem, "one causal handoff"))
        refs = metadata.get("dialogue_refs", item.get("dialogue_refs", []))
        if not refs and isinstance(item.get("dialogue_audio"), dict):
            refs = item.get("dialogue_audio", {}).get("dialogue_refs", [])
        refs = refs or []
        expected_lines = []
        for ref in refs:
            raw = dialogue_map.get(ref, "")
            if not raw:
                raw = item.get("dialogue_raw_text", "")
            if raw:
                expected_lines.append(raw)
        item_text = str(item.get("full_prompt", "") or "")
        control = item.get("generation_control", {})
        control = control if isinstance(control, dict) else {}
        audio_enabled = control.get("audio_enabled")
        for problem in dialogue_event_issues(
            metadata,
            full_prompt=fp,
            audio_enabled=audio_enabled,
            duration=dur,
        ):
            issues.append((sid, "dialogue_events", problem, "locked dialogue/OS identity and speaking performance"))

        if refs:
            for raw in expected_lines:
                raw_norm = _normalize_dialogue_text(raw)
                prompt_norm = _normalize_dialogue_text(item_text)
                if audio_enabled is True and raw_norm and raw_norm not in prompt_norm:
                    issues.append((sid, "dialogue.missing_or_rewritten", raw, "preserve_original_text"))
                if audio_enabled is False and raw_norm and raw_norm in prompt_norm:
                    issues.append((sid, "dialogue.audio_disabled_leak", raw, "keep_in_production_metadata"))
            extras = _extract_extra_quoted_text(item_text, expected_lines)
            for extra in extras[:5]:
                issues.append((sid, "dialogue.extra_quoted_text", extra, "no_added_dialogue"))
        else:
            extras = _extract_extra_quoted_text(item_text, [])
            if extras:
                issues.append((sid, "dialogue.extra_without_ref", extras[:3], "no_dialogue_refs"))

        has_ovos_ref = any(("OV" in str(r) or "OS" in str(r)) for r in refs)
        if has_ovos_ref and _has_ovos_lip_sync(item_text):
            issues.append((sid, "ov_os_lip_sync", "mouth_sync_detected", "OV/OS must be no-lip-sync"))

    # A public package must cover every planned subshot. This prevents a
    # partially validated Composer batch from looking structurally complete.
    if plan_items:
        missing_subshots = sorted(set(plan_items) - package_subshot_ids)
        extra_subshots = sorted(package_subshot_ids - set(plan_items))
        for sid in missing_subshots:
            issues.append((sid, "package_coverage", "missing", "planned subshot required"))
        for sid in extra_subshots:
            issues.append((sid, "package_coverage", "unexpected", "must exist in shot_plan"))

    # Check merged_full_prompts cover all shot_ids
    merged = data.get("merged_full_prompts", [])
    merged_ids = set(m.get("shot_id", "") for m in merged)
    missing_merged = shot_ids - merged_ids
    for sid in missing_merged:
        issues.append((sid, "merged_full_prompts", "missing", "merge_required"))

    if issues:
        print("[VALIDATE_PKG] %d issue(s) found" % len(issues))
    else:
        print("[VALIDATE_PKG] PASS")

    return issues


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: validate_prompt_package.py <pkg_path> [shot_plan.json]")
        sys.exit(1)
    issues = validate(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(json.dumps(issues, ensure_ascii=False, indent=2))
    sys.exit(0 if len(issues) == 0 else 1)
