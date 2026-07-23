"""Hard context budget for disk packets; never truncate dialogue to fit."""
import json

MAX_PACKET_CHARS = 12000
# Reserve the remainder of MAX_PACKET_CHARS for dispatch provenance, paths,
# instructions, and phase metadata.
MAX_EDITOR_ITEMS_CHARS = 7000
MAX_COMPOSER_ITEMS_CHARS = 9000

def check(packet):
    size = len(json.dumps(packet, ensure_ascii=False))
    if size > MAX_PACKET_CHARS:
        raise ValueError("packet exceeds %d characters; split by main-shot or scene window" % MAX_PACKET_CHARS)
    return size


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
