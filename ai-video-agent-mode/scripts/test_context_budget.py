#!/usr/bin/env python3
"""Regression checks for mechanical Master packet sizing.

The test deliberately uses opaque payload text.  No scene words are inspected;
the only batching input is serialized character count and declared item cap.
"""

from batch_planner import dynamic_master_chunks
from context_budget import MAX_COMPOSER_ITEMS_CHARS, MAX_PACKET_CHARS, composer_items_fit, size

FIXED_PACKET_FIXTURE_CHARS = 5292


def _item(index, payload_chars=1300):
    return {
        "shot_id": "S%03d" % index,
        "subshot_id": "S%03d" % index,
        "opaque_model_authored_payload": "x" * payload_chars,
    }


def run():
    four = [_item(index) for index in range(1, 5)]
    four_size = size(four)
    assert four_size > 4500, four_size
    assert four_size <= MAX_COMPOSER_ITEMS_CHARS, four_size
    assert composer_items_fit(four)
    assert len(dynamic_master_chunks(four, lambda item: item, max_items=6)) == 1

    five = four + [_item(5)]
    chunks = dynamic_master_chunks(five, lambda item: item, max_items=6)
    assert [len(chunk) for chunk in chunks] == [4, 1], [len(chunk) for chunk in chunks]
    assert size(chunks[0]) <= MAX_COMPOSER_ITEMS_CHARS
    assert size(chunks[0]) + FIXED_PACKET_FIXTURE_CHARS < MAX_PACKET_CHARS

    oversized = [_item(1, payload_chars=MAX_COMPOSER_ITEMS_CHARS)]
    try:
        dynamic_master_chunks(oversized, lambda item: item, max_items=6)
    except ValueError as exc:
        assert "exceeds the packet context budget" in str(exc)
    else:
        raise AssertionError("an oversized complete item must be rejected, never truncated")

    print("context budget regression passed")


if __name__ == "__main__":
    run()
