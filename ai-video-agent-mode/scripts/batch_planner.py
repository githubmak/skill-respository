"""Deterministic batch planning shared by dispatch packet construction.

Batch boundaries depend only on declared item limits, continuity IDs, and the
actual serialized context budget. This module must not interpret scene text or
classify creative complexity.
"""

from context_budget import composer_items_fit, editor_items_fit


def analysis_chunks(items, max_items, phase):
    del phase
    item_cap = max(int(max_items), 1)
    chunks, current = [], []
    for item in items:
        if current and len(current) >= item_cap:
            chunks.append(current)
            current = []
        current.append(item)
    if current:
        chunks.append(current)
    return chunks or [items]


def batch_profile(items):
    """Return a mechanical batching receipt without classifying content."""
    return {
        "basis": "item_count_chain_ids_and_context_size",
        "item_count": len(items),
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


def dynamic_master_chunks(items, compact_item, max_items=6, force_single=False):
    """Batch by declared capacity, continuity IDs, and actual compact size."""
    if force_single:
        return [[item] for item in items]
    groups = []
    for item in items:
        group_id = composer_group_id(item)
        if groups and groups[-1][0] == group_id:
            groups[-1][1].append(item)
        else:
            groups.append([group_id, [item]])
    chunks, current = [], []
    item_cap = max(int(max_items), 1)
    for _, group in groups:
        if current and (
            len(current) + len(group) > item_cap
            or not composer_items_fit([compact_item(item) for item in current + group])
        ):
            chunks.append(current)
            current = []
        if not current and not composer_items_fit([compact_item(item) for item in group]):
            raise ValueError(
                "single Master Production task exceeds the packet context budget; "
                "split that main shot during Orchestrator instead of truncating its source facts"
            )
        current.extend(group)
        if len(current) >= item_cap:
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)
    return chunks or [items]


def editor_review_chunks(windows, batch_size=None):
    item_cap = max(int(batch_size), 1) if batch_size is not None else 10
    chunks, current = [], []
    for window in windows:
        if current and (len(current) >= item_cap or not editor_items_fit(current + [window])):
            chunks.append(current)
            current = []
        if not editor_items_fit([window]):
            raise ValueError("single Editor review capsule exceeds context budget; split the main shot")
        current.append(window)
    if current:
        chunks.append(current)
    return chunks or [windows]
