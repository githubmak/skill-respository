"""Immutable-on-record local receipts for mandatory worker dispatch gates.

These receipts make the pipeline reject locally-written batches that have not
first passed through the register -> heartbeat -> record sequence.  They are
an on-disk gate, not an external attestation service: an executor that needs
adversarial protection must issue the receipt outside the model's filesystem.
"""

import hashlib
import json
import os
import secrets
import time


CONTRACT_VERSION = "jimeng-t2v-v1"


def issue(packet_path, packet, agent_id):
    """Create the only receipt accepted for one dispatched worker packet."""
    _validate_packet(packet)
    run_dir = packet["run_dir"]
    path = receipt_path(run_dir, packet["dispatch_id"])
    if os.path.exists(path):
        existing = _load(path)
        if (
            existing.get("packet_sha256") == sha256_file(packet_path)
            and existing.get("agent_id") == agent_id
        ):
            return existing, path
        raise ValueError("dispatch receipt already belongs to a different packet or agent")
    receipt = {
        "contract_version": CONTRACT_VERSION,
        "dispatch_id": packet["dispatch_id"],
        "phase": packet["phase"],
        "agent_id": agent_id,
        "packet_path": os.path.abspath(packet_path),
        "packet_sha256": sha256_file(packet_path),
        "batch_path": os.path.abspath(packet["_batch_output_path"]),
        "issued_at": time.time(),
        "nonce": secrets.token_urlsafe(24),
        "heartbeat_count": 0,
        "last_heartbeat_at": None,
        "completed_at": None,
    }
    _write(path, receipt)
    return receipt, path


def heartbeat(packet_path, packet, agent_id):
    """Record a worker liveness event tied to the immutable packet identity."""
    receipt, path = load_and_verify(packet_path, packet, agent_id, require_heartbeat=False)
    receipt["heartbeat_count"] = int(receipt.get("heartbeat_count", 0) or 0) + 1
    receipt["last_heartbeat_at"] = time.time()
    _write(path, receipt)
    return receipt, path


def complete(packet_path, packet, agent_id, batch_sha256):
    """Seal the completion receipt after phase validation accepted the worker output."""
    receipt, path = load_and_verify(packet_path, packet, agent_id, require_heartbeat=True)
    receipt["completed_at"] = time.time()
    receipt["completed_batch_sha256"] = batch_sha256
    _write(path, receipt)
    return receipt, path


def load_and_verify(packet_path, packet, agent_id=None, require_heartbeat=True):
    _validate_packet(packet)
    path = receipt_path(packet["run_dir"], packet["dispatch_id"])
    if not os.path.exists(path):
        raise ValueError("dispatch receipt missing: register a real worker before accepting output")
    receipt = _load(path)
    if receipt.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("dispatch receipt contract is invalid")
    if receipt.get("packet_path") != os.path.abspath(packet_path):
        raise ValueError("dispatch receipt packet path mismatch")
    if receipt.get("packet_sha256") != sha256_file(packet_path):
        raise ValueError("dispatch packet changed after receipt issuance")
    if receipt.get("batch_path") != os.path.abspath(packet["_batch_output_path"]):
        raise ValueError("dispatch receipt batch path mismatch")
    if agent_id and receipt.get("agent_id") != agent_id:
        raise ValueError("dispatch receipt agent mismatch")
    if require_heartbeat and int(receipt.get("heartbeat_count", 0) or 0) < 1:
        raise ValueError("dispatch receipt has no worker heartbeat")
    if require_heartbeat and not isinstance(receipt.get("last_heartbeat_at"), (int, float)):
        raise ValueError("dispatch receipt heartbeat timestamp is missing")
    return receipt, path


def receipt_path(run_dir, dispatch_id):
    return os.path.join(run_dir, ".cache", "dispatch_receipts", str(dispatch_id) + ".json")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_packet(packet):
    if not isinstance(packet, dict) or packet.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("invalid dispatch packet contract")
    for field in ("run_dir", "phase", "dispatch_id", "_batch_output_path"):
        if not str(packet.get(field, "") or "").strip():
            raise ValueError("dispatch packet missing %s" % field)


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, path)
