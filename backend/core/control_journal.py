"""Deletion/withdrawal intents survive database restore. No media or identity labels."""

import hashlib
import hmac
import json
import os
import uuid
from contextvars import ContextVar
from pathlib import Path

from django.conf import settings

replaying = ContextVar("journal_replay", default=False)


def signature(record):
    raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(settings.CONTROL_JOURNAL_KEY.encode(), raw, hashlib.sha256).hexdigest()


def record_intent(owner_id, action, **payload):
    """Owner row lock serializes intents. Persist before the database mutation.

    A rollback may retain an intent: recovery deliberately favors revocation. This
    directory needs an independent, continuously replicated backup in production.
    """
    if replaying.get():
        return
    if action not in {
        "ACCOUNT_DELETE",
        "ASSET_DELETE",
        "MATCH_DELETE",
        "CONSENT_WITHDRAW",
        "PILOT_WITHDRAW",
        "PILOT_CLOSE",
    }:
        raise ValueError("INVALID_CONTROL_ACTION")
    # Owner -> global mutex is the repository lock order. Serialize the signed
    # completeness checkpoint across owners without relying on filesystem locks.
    from backend.core.security import capacity_lock

    capacity_lock()
    record = {
        "version": 1,
        "namespace": settings.DEPLOYMENT_NAMESPACE,
        "owner": owner_id,
        "action": action,
        "payload": payload,
        "id": str(uuid.uuid4()),
    }
    root = Path(settings.CONTROL_JOURNAL_ROOT)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = root / (record["id"] + ".json")
    temporary = root / (record["id"] + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump({"record": record, "signature": signature(record)}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        write_checkpoint(root)
        if os.name != "nt":
            descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def journal_digest(root):
    index = [
        [path.name, hashlib.sha256(path.read_bytes()).hexdigest()]
        for path in sorted(root.glob("*.json"))
        if path.name != "checkpoint.json"
    ]
    return len(index), hashlib.sha256(json.dumps(index, separators=(",", ":")).encode()).hexdigest()


def write_checkpoint(root):
    count, digest = journal_digest(root)
    checkpoint = {
        "version": 1,
        "namespace": settings.DEPLOYMENT_NAMESPACE,
        "count": count,
        "digest": digest,
    }
    temporary = root / "checkpoint.tmp"
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump({"checkpoint": checkpoint, "signature": signature(checkpoint)}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, root / "checkpoint.json")


def verified_records():
    """Validate the complete supplied journal before applying any record."""
    records = []
    root = Path(settings.CONTROL_JOURNAL_ROOT)
    if not root.is_dir() or list(root.glob("*.tmp")):
        raise ValueError("JOURNAL_UNAVAILABLE_OR_INCOMPLETE")
    envelope = json.loads((root / "checkpoint.json").read_text(encoding="utf-8"))
    checkpoint = envelope["checkpoint"]
    count, digest = journal_digest(root)
    if not hmac.compare_digest(envelope["signature"], signature(checkpoint)) or checkpoint != {
        "version": 1,
        "namespace": settings.DEPLOYMENT_NAMESPACE,
        "count": count,
        "digest": digest,
    }:
        raise ValueError("INVALID_CONTROL_JOURNAL")
    for path in sorted(root.glob("*.json")):
        if path.name == "checkpoint.json":
            continue
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("INVALID_CONTROL_JOURNAL")
        envelope = json.loads(path.read_text(encoding="utf-8"))
        record = envelope["record"]
        if (
            not hmac.compare_digest(envelope["signature"], signature(record))
            or record["version"] != 1
            or record["namespace"] != settings.DEPLOYMENT_NAMESPACE
            or record["action"]
            not in {
                "ACCOUNT_DELETE",
                "ASSET_DELETE",
                "MATCH_DELETE",
                "CONSENT_WITHDRAW",
                "PILOT_WITHDRAW",
                "PILOT_CLOSE",
            }
        ):
            raise ValueError("INVALID_CONTROL_JOURNAL")
        records.append(record)
    return records
