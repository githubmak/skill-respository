"""Pure batch planning shared by dispatch packet construction.

This module deliberately knows nothing about run directories or packet files.
Keeping capacity policy here makes it testable without coupling it to scaffold
or retry serialization.
"""

from context_budget import composer_items_fit, editor_items_fit
from shot_semantics import dispatch_risk, workload_units


def analysis_chunks(items, max_items, phase):
    weight_budget = max_items * 2
    item_cap = max_items * 2
    chunks, current, current_weight = [], [], 0
    for item in items:
        weight = workload_units(item, phase)
        if current and (len(current) >= item_cap or current_weight + weight > weight_budget):
            chunks.append(current)
            current, current_weight = [], 0
        current.append(item)
        current_weight += weight
    if current:
        chunks.append(current)
    return chunks or [items]


def batch_risk(items):
    tiers = {"light": 0, "standard": 1, "high": 2}
    risks = [dispatch_risk(item) for item in items]
    selected = max(risks, key=lambda risk: tiers.get(risk.get("tier"), 1)) if risks else dispatch_risk({})
    reasons = []
    for risk in risks:
        for reason in risk.get("reasons", []):
            if reason not in reasons:
                reasons.append(reason)
    return {
        "tier": selected.get("tier", "standard"),
        "reasons": reasons or ["normal_contract"],
        "batch_capacity": int(selected.get("batch_capacity", 6)),
        "review_scope": selected.get("review_scope", "bounded_scene_window"),
    }


def composer_group_id(item):
    metadata = item.get("qa_metadata", {}) if isinstance(item.get("qa_metadata"), dict) else {}
    fight = item.get("fight_continuity", metadata.get("fight_continuity", {}))
    if isinstance(fight, dict) and fight.get("sequence_id"):
        return "fight:%s" % fight["sequence_id"]
    for key in ("continuous_interaction_id", "interaction_chain_id", "continuous_chain_id", "sequence_id", "performance_chain_id"):
        value = item.get(key, metadata.get(key))
        if value:
            return "chain:%s" % value
    return "shot:%s" % str(item.get("shot_id", "") or item.get("subshot_id", ""))


def dynamic_master_chunks(items, compact_item, force_single=False):
    """Batch master tasks by risk, continuity chain and actual compact size."""
    if force_single:
        return [[item] for item in items]
    groups = []
    for item in items:
        group_id = composer_group_id(item)
        if groups and groups[-1][0] == group_id:
            groups[-1][1].append(item)
        else:
            groups.append([group_id, [item]])
    chunks, current, capacity = [], [], 10
    for _, group in groups:
        group_capacity = batch_risk(group)["batch_capacity"]
        next_capacity = min(capacity, group_capacity) if current else group_capacity
        if current and (
            len(current) + len(group) > next_capacity
            or not composer_items_fit([compact_item(item) for item in current + group])
        ):
            chunks.append(current)
            current, capacity, next_capacity = [], 10, group_capacity
        if not current and not composer_items_fit([compact_item(item) for item in group]):
            raise ValueError(
                "single Master Production task exceeds the packet context budget; "
                "split that main shot during Phase 1 instead of truncating its source facts"
            )
        current.extend(group)
        capacity = next_capacity
        if len(current) >= capacity:
            chunks.append(current)
            current, capacity = [], 10
    if current:
        chunks.append(current)
    return chunks or [items]


def editor_review_chunks(windows, batch_size=None):
    tiers = {"light": 10, "standard": 6, "high": 4}
    requested = max(int(batch_size), 1) if batch_size is not None else None
    chunks, current, capacity = [], [], 10
    for window in windows:
        window_capacity = tiers.get(str(window.get("review_tier", "standard")), 6)
        if requested is not None:
            window_capacity = min(window_capacity, requested)
        next_capacity = min(capacity, window_capacity) if current else window_capacity
        if current and (len(current) >= next_capacity or not editor_items_fit(current + [window])):
            chunks.append(current)
            current, capacity, next_capacity = [], 10, window_capacity
        if not editor_items_fit([window]):
            raise ValueError("single Editor review capsule exceeds context budget; split the main shot")
        current.append(window)
        capacity = next_capacity
    if current:
        chunks.append(current)
    return chunks or [windows]
