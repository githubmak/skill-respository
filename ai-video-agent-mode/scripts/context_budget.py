"""Hard context budget for disk packets; never truncate dialogue to fit."""
import json
import os

MAX_PACKET_CHARS = 12000
# Reserve the remainder of MAX_PACKET_CHARS for dispatch provenance, paths,
# instructions, and phase metadata.
MAX_EDITOR_ITEMS_CHARS = 8000
# Master packets carry roughly 5.3k characters of fixed dispatch metadata and
# instructions inside MAX_PACKET_CHARS. Keep complete creative records, while
# leaving at least about 0.7k characters of headroom for serialization drift.
# This is a mechanical context budget only; it never evaluates or rewrites
# model-authored creative content.
MAX_COMPOSER_ITEMS_CHARS = 6000
# Worker context includes packet JSON plus the fixed files the packet instructs
# the Agent to read. Keep this separate from MAX_PACKET_CHARS so compact packet
# serialization remains stable while effective context is bounded too.
MAX_EFFECTIVE_CONTEXT_CHARS = 200000

def check(packet):
    size = len(json.dumps(packet, ensure_ascii=False))
    if size > MAX_PACKET_CHARS:
        raise ValueError("packet exceeds %d characters; split by main-shot or scene window" % MAX_PACKET_CHARS)
    external = 0
    default_fields = (
        "project_config_path", "source_snapshot_path", "source_ledger_path",
        "source_evidence_path", "constraints_path", "composer_scaffold_path", "scene_lock_cache_path",
        "pre_editor_gate_path", "review_packet_path", "editor_creative_context_path",
    )
    policy = packet.get("context_policy", {}) if isinstance(packet.get("context_policy"), dict) else {}
    declared = policy.get("fixed_global_context")
    fields = tuple(declared) if isinstance(declared, list) and declared else default_fields
    for key in fields:
        path = packet.get(key)
        if not path or not isinstance(path, str) or not os.path.isfile(path):
            continue
        try:
            external += os.path.getsize(path)
        except OSError:
            continue
    effective = size + external
    if effective > MAX_EFFECTIVE_CONTEXT_CHARS:
        raise ValueError(
            "effective worker context exceeds %d characters (%d); split by main-shot or scene window"
            % (MAX_EFFECTIVE_CONTEXT_CHARS, effective)
        )
    return effective


def size(value):
    """Return the serialized character count used by the packet gate."""
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def editor_items_fit(items):
    """Keep Editor capsules below the packet budget before dispatch metadata.

    Dialogue and prompt text are intentionally never truncated.  Callers must
    create another packet when a complete capsule does not fit.
    """
    return size(items) <= MAX_EDITOR_ITEMS_CHARS


def composer_items_fit(items):
    """Test compact Master Production items before a packet is written.

    Packet data is passed by path, but it still consumes worker context.  This
    preflight makes batching shrink automatically instead of failing late and
    forcing an operator to manually set batch_size=1.
    """
    return size(items) <= MAX_COMPOSER_ITEMS_CHARS
