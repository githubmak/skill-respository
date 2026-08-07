"""Create a field-scoped retry packet for failed main-shot tasks."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from dispatch_cache import active_packet_paths, prepare_dispatch_packets, _write_active_manifest
from pipeline_runtime import atomic_json
from incremental_validation import ALL_MUTABLE_FIELDS, SCOPE_ORDER


def prepare(run_dir, review_path=None):
    review_path = review_path or os.path.join(run_dir, ".cache", "review", "llm_gate_result.json")
    with open(review_path, encoding="utf-8-sig") as handle:
        review = json.load(handle)
    fields, reasons, scopes, shots = {}, {}, {}, []
    creative_regeneration = False
    for window in review.get("windows", []):
        if (
            isinstance(window, dict)
            and not window.get("pass")
            and window.get("return_to_phase") == "master_production"
        ):
            creative_regeneration = True
            creative_reason = str(window.get("creative_cause", "") or "").strip()
            for shot_id in window.get("affected_shot_ids", []) if isinstance(window.get("affected_shot_ids"), list) else []:
                shot_id = str(shot_id or "").strip()
                if not shot_id:
                    continue
                shots.append(shot_id)
                fields.setdefault(shot_id, set()).add(ALL_MUTABLE_FIELDS)
                scopes[shot_id] = "shot"
                reasons.setdefault(shot_id, set()).update(
                    [creative_reason] + [str(value) for value in window.get("blocking", [])]
                )
            continue
        window_shots = _extract_window_shot_ids(window)
        window_reasons = _extract_window_reasons(window)
        window_scope = str(window.get("repair_scope", "") or "") if isinstance(window, dict) else ""
        for target in window.get("repair_targets", []):
            if isinstance(target, dict):
                shot_id = str(target.get("shot_id", "") or target.get("subshot_id", ""))
            else:
                shot_id = _extract_primary_shot_id(str(target or ""))
            if not shot_id:
                continue
            dependent = target.get("dependent_shot_ids", []) if isinstance(target, dict) else []
            target_shots = [shot_id] + [str(value) for value in dependent if str(value).strip()]
            target_scope = str(target.get("repair_scope", "") or window_scope or "field") if isinstance(target, dict) else (window_scope or "field")
            for target_shot in target_shots:
                shots.append(target_shot)
                scopes[target_shot] = _wider_scope(scopes.get(target_shot, "field"), target_scope)
            if isinstance(target, dict):
                target_fields = target.get("fields")
                if not target_fields:
                    target_fields = [target.get("field") or target.get("field_path") or "validator_reported_field"]
            else:
                target_fields = ["validator_reported_field"]
            for target_shot in target_shots:
                fields.setdefault(target_shot, set()).update(_normalize_retry_fields(target_fields))
                reasons.setdefault(target_shot, set()).update(window_reasons)
        if not window.get("repair_targets"):
            shots.extend(window_shots)
            for shot_id in window_shots:
                scopes[shot_id] = _wider_scope(scopes.get(shot_id, "field"), window_scope or "window")
                reasons.setdefault(shot_id, set()).update(window_reasons)
    shots = sorted(set(shots))
    if not shots:
        return []
    for shot_id in shots:
        scopes.setdefault(shot_id, "shot")
        if shot_id not in fields:
            fields[shot_id] = {"validator_reported_field"}
        else:
            fields[shot_id] = set(_expand_dependent_fields(fields[shot_id]))
    history = _prior_retry_attempts(run_dir, shots)
    effective_scopes = {}
    attempts = {}
    for shot_id in shots:
        prior = history.get(shot_id, 0)
        effective_scopes[shot_id] = _effective_scope(scopes.get(shot_id, "field"), prior)
        attempts[shot_id] = prior + 1
        if effective_scopes[shot_id] == "shot":
            fields[shot_id] = {ALL_MUTABLE_FIELDS}
    fields_by_shot = {key: sorted(value) for key, value in fields.items()}
    fields_by_shot = _inherit_prior_retry_fields(run_dir, fields_by_shot, shots)
    fields_by_shot = {key: _normalize_retry_fields(value) for key, value in fields_by_shot.items()}
    existing = _equivalent_active_retry_packets(run_dir, shots, fields_by_shot, effective_scopes)
    if existing:
        return existing
    retry_batch_size = 1 if _has_previous_retry(run_dir, shots) else None
    try:
        packets = prepare_dispatch_packets(run_dir, "master_production", batch_size=retry_batch_size, subshot_ids=shots)
    except ValueError as error:
        if "packet exceeds" not in str(error):
            raise
        packets = prepare_dispatch_packets(run_dir, "master_production", batch_size=1, subshot_ids=shots)
    for packet_path in packets:
        with open(packet_path, encoding="utf-8-sig") as handle:
            packet = json.load(handle)
        packet_shots = _packet_shot_ids(packet)
        packet_fields = {
            shot_id: fields_by_shot.get(shot_id, ["validator_reported_field"])
            for shot_id in packet_shots
            if shot_id in fields_by_shot
        }
        packet_reasons = {
            shot_id: sorted(reasons.get(shot_id, []))
            for shot_id in packet_shots
            if shot_id in reasons
        }
        packet["retry_context_path"] = atomic_json(packet_path + ".retry.json", {
            "mode": "creative_regeneration" if creative_regeneration else "field_patch",
            "fields_by_main_shot": packet_fields,
            "repair_scope_by_main_shot": {
                shot_id: effective_scopes.get(shot_id, "field") for shot_id in packet_shots
            },
            "attempt_by_main_shot": {
                shot_id: attempts.get(shot_id, 1) for shot_id in packet_shots
            },
            "failure_reasons_by_main_shot": packet_reasons,
            "rule": (
                "Re-author each listed main shot as one coherent delivery-ready director candidate; preserve locked facts and do not patch isolated phrases."
                if creative_regeneration else
                "Return only listed main shots and modify only the authorized mechanical scope; locked fields survive validation and merge."
            ),
        })
        packet["retry_field_scope"] = packet_fields
        if creative_regeneration:
            packet["creative_regeneration"] = True
            packet["instruction"] += (
                " Model Editor returned this shot to Master Production. Re-author the complete affected main shot from the episode intent and creative cause; "
                "do not perform a phrase-level patch and do not preserve failed mutable creative text merely to minimize the diff."
            )
        atomic_json(packet_path, packet)
    if packets:
        first_packet = json.load(open(packets[0], encoding="utf-8-sig"))
        _write_active_manifest(
            run_dir,
            "master_production",
            first_packet.get("source_path", ""),
            first_packet.get("dispatch_group_id", ""),
            packets,
            is_retry=True,
            target_ids=shots,
        )
    return packets


def _extract_primary_shot_id(text):
    matches = re.findall(r"S\d+(?:-\d+)?", text or "")
    return matches[0] if matches else ""


def _normalize_retry_fields(target_fields):
    normalized = []
    for field in target_fields or []:
        text = str(field or "").strip()
        if not text:
            continue
        if text.startswith("full_prompt."):
            text = "full_prompt"
        if text not in normalized:
            normalized.append(text)
    return _expand_dependent_fields(normalized)


def _expand_dependent_fields(fields):
    values = [str(field or "").strip() for field in fields or [] if str(field or "").strip()]
    if ALL_MUTABLE_FIELDS in values:
        return [ALL_MUTABLE_FIELDS]
    return values


def _extract_window_shot_ids(window):
    ids = []
    if not isinstance(window, dict) or window.get("pass"):
        return ids
    current = window.get("current", {}) if isinstance(window.get("current"), dict) else {}
    current_id = str(current.get("shot_id", "") or current.get("subshot_id", "") or "")
    if current_id:
        ids.append(current_id)
    for key in ("blocking", "repair_targets"):
        values = window.get(key, [])
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, dict):
                shot_id = str(value.get("shot_id", "") or value.get("subshot_id", ""))
                dependent = value.get("dependent_shot_ids", [])
                candidates = [shot_id] + [str(item) for item in dependent or []]
            else:
                candidates = [_extract_primary_shot_id(str(value or ""))]
            for shot_id in candidates:
                if shot_id and shot_id not in ids:
                    ids.append(shot_id)
    return ids


def _extract_window_reasons(window):
    if not isinstance(window, dict):
        return set()
    reasons = set()
    for key in ("blocking", "warnings", "issues"):
        values = window.get(key, [])
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, list):
            continue
        for value in values:
            text = str(value.get("message", "") if isinstance(value, dict) else value or "").strip()
            if text:
                reasons.add(text)
    return reasons


def _packet_shot_ids(packet):
    ids = []
    for item in packet.get("items", []) if isinstance(packet.get("items"), list) else []:
        if not isinstance(item, dict):
            continue
        shot_id = str(item.get("shot_id", "") or item.get("subshot_id", "") or "").strip()
        if shot_id and shot_id not in ids:
            ids.append(shot_id)
    return ids


def _wider_scope(left, right):
    left = left if left in SCOPE_ORDER else "field"
    right = right if right in SCOPE_ORDER else "field"
    return left if SCOPE_ORDER[left] >= SCOPE_ORDER[right] else right


def _effective_scope(requested, prior_attempts):
    """Escalate repeated field patches to one-shot repair, never silently to scene."""
    requested = requested if requested in SCOPE_ORDER else "field"
    if requested == "field" and prior_attempts >= 2:
        return "shot"
    return requested


def _prior_retry_attempts(run_dir, shot_ids):
    targets = set(str(value) for value in shot_ids or [])
    counts = {value: 0 for value in targets}
    dispatch_dir = os.path.join(run_dir, ".cache", "dispatch")
    if not os.path.isdir(dispatch_dir):
        return counts
    for name in os.listdir(dispatch_dir):
        if name.startswith("._") or not name.endswith("_packet.json"):
            continue
        try:
            with open(os.path.join(dispatch_dir, name), encoding="utf-8-sig") as handle:
                packet = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if packet.get("phase") != "master_production" or not packet.get("retry_context_path"):
            continue
        try:
            with open(packet["retry_context_path"], encoding="utf-8-sig") as handle:
                context = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        for shot_id in (context.get("attempt_by_main_shot", {}) or {}):
            shot_id = str(shot_id)
            if shot_id in counts:
                counts[shot_id] = max(counts[shot_id], int(
                    (context.get("attempt_by_main_shot", {}) or {}).get(shot_id, 1) or 1
                ))
        if not context.get("attempt_by_main_shot"):
            for shot_id in _packet_shot_ids(packet):
                if shot_id in counts:
                    counts[shot_id] += 1
    return counts


def _equivalent_active_retry_packets(run_dir, shot_ids, fields_by_shot, scopes_by_shot=None):
    wanted = sorted(set(str(shot_id) for shot_id in shot_ids or [] if str(shot_id).strip()))
    if not wanted:
        return []
    matching = []
    covered = set()
    for path in active_packet_paths(run_dir, "master_production"):
        try:
            with open(path, encoding="utf-8-sig") as handle:
                packet = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if not (packet.get("is_retry") or packet.get("retry_context_path")):
            continue
        packet_shots = _packet_shot_ids(packet)
        if not packet_shots or not set(packet_shots).issubset(set(wanted)):
            continue
        context_path = packet.get("retry_context_path", "")
        try:
            with open(context_path, encoding="utf-8-sig") as handle:
                context = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        context_fields = context.get("fields_by_main_shot", {})
        if not isinstance(context_fields, dict):
            continue
        provenance = _load_optional(packet.get("_batch_output_path", "") + ".provenance.json")
        if provenance and set(packet_shots) & set(provenance.get("failed_subshot_ids", []) or []):
            continue
        context_scopes = context.get("repair_scope_by_main_shot", {}) or {}
        if all(
            sorted(context_fields.get(shot_id, [])) == sorted(fields_by_shot.get(shot_id, []))
            and (not scopes_by_shot or context_scopes.get(shot_id, "field") == scopes_by_shot.get(shot_id, "field"))
            for shot_id in packet_shots
        ):
            matching.append(path)
            covered.update(packet_shots)
    return sorted(matching) if sorted(covered) == wanted else []


def _load_optional(path):
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}


def _inherit_prior_retry_fields(run_dir, fields_by_shot, shot_ids):
    """A newer retry for the same shot must not discard earlier field fixes."""
    targets = set(str(shot_id) for shot_id in shot_ids or [] if str(shot_id).strip())
    if not targets:
        return fields_by_shot
    inherited = {shot_id: set(fields_by_shot.get(shot_id, [])) for shot_id in targets}
    dispatch_dir = os.path.join(run_dir, ".cache", "dispatch")
    if not os.path.isdir(dispatch_dir):
        return {shot_id: sorted(fields) for shot_id, fields in inherited.items()}
    for name in os.listdir(dispatch_dir):
        if name.startswith("._") or not name.endswith("_packet.json"):
            continue
        path = os.path.join(dispatch_dir, name)
        try:
            with open(path, encoding="utf-8-sig") as handle:
                packet = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if packet.get("phase") != "master_production" or not (packet.get("is_retry") or packet.get("retry_context_path")):
            continue
        context_path = packet.get("retry_context_path", "")
        try:
            with open(context_path, encoding="utf-8-sig") as handle:
                context = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if context.get("mode") != "field_patch":
            continue
        for shot_id, fields in (context.get("fields_by_main_shot", {}) or {}).items():
            shot_id = str(shot_id)
            if shot_id not in inherited or not isinstance(fields, list):
                continue
            inherited[shot_id].update(str(field) for field in fields if str(field).strip())
    return {shot_id: sorted(fields) for shot_id, fields in inherited.items()}


def _has_previous_retry(run_dir, shot_ids):
    targets = set(str(shot_id) for shot_id in shot_ids or [])
    if not targets:
        return False
    dispatch_dir = os.path.join(run_dir, ".cache", "dispatch")
    if not os.path.isdir(dispatch_dir):
        return False
    for name in os.listdir(dispatch_dir):
        if name.startswith("._") or not name.endswith("_packet.json"):
            continue
        path = os.path.join(dispatch_dir, name)
        try:
            with open(path, encoding="utf-8-sig") as handle:
                packet = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if packet.get("phase") != "master_production":
            continue
        if not (packet.get("is_retry") or packet.get("retry_context_path")):
            continue
        packet_shots = {
            str(item.get("shot_id", "") or item.get("subshot_id", ""))
            for item in packet.get("items", []) if isinstance(item, dict)
        }
        if targets & packet_shots:
            return True
    return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: prepare_master_retry.py <run_dir>")
    print("\n".join(prepare(sys.argv[1])))
