"""Hard context budget for disk packets; never truncate dialogue to fit."""
import json

MAX_PACKET_CHARS = 12000

def check(packet):
    size = len(json.dumps(packet, ensure_ascii=False))
    if size > MAX_PACKET_CHARS:
        raise ValueError("packet exceeds %d characters; split by main-shot or scene window" % MAX_PACKET_CHARS)
    return size
