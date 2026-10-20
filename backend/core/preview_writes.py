"""Fenced cloud writes and quota/recovery projections of independent preview intents."""

import base64
import hashlib
import time
from uuid import UUID, uuid5

from django.conf import settings

from analysis.media import file_hash
from analysis.preview_bundle import FILES
from backend.core.cloud import CloudFailure, GooglePrivateStorage, authorized_session
from backend.core.models import PreviewWriteHold, RecordingPreview
from backend.core.preview_ledger import LedgerFailure, held_bytes, ledger, ledger_present, prefix


def intent_id(preview, fence):
    return str(uuid5(preview.pk, f"{preview.run_id}:{fence}"))


def sync_holds():
    required = (
        settings.PREVIEW_LEDGER_REQUIRED
        or settings.GCS_PREVIEW_WRITES_QUALIFIED
        or PreviewWriteHold.objects.exists()
    )
    if not ledger_present() and not required:
        return {}
    rows = ledger().records()
    if PreviewWriteHold.objects.exclude(pk__in=rows).exists():
        raise LedgerFailure("PREVIEW_LEDGER_MIRROR_MISSING")
    for identity, (row, sequence) in rows.items():
        previous = PreviewWriteHold.objects.filter(pk=identity).first()
        if previous and previous.sequence > sequence:
            raise LedgerFailure("PREVIEW_LEDGER_ROLLBACK")
        PreviewWriteHold.objects.update_or_create(
            pk=identity,
            defaults={
                "owner_key": row["owner"],
                "asset_key": row["asset"],
                "preview_key": row["preview"],
                "run_key": row["run"],
                "fence": row["fence"],
                "state": row["state"],
                "reserved_bytes": held_bytes(row),
                "sequence": sequence,
            },
        )
    return rows


def extra_capacity(owner_id=None):
    """Count each orphan/stale attempt, with one credit for its current child reservation."""
    holds = PreviewWriteHold.objects.exclude(state="ERASED")
    if owner_id is not None:
        holds = holds.filter(owner_key=owner_id)
    total = 0
    for hold in holds:
        covered = (
            RecordingPreview.objects.filter(
                pk=hold.preview_key,
                asset_id=hold.asset_key,
                asset__owner_id=hold.owner_key,
                run_id=hold.run_key,
                attempt_fence=hold.fence,
            )
            .exclude(state="PURGED")
            .values_list("reserved_bytes", flat=True)
            .first()
            or 0
        )
        total += max(0, hold.reserved_bytes - covered)
    return total


def plan(preview, fence, directory, bucket):
    files = {}
    for name in FILES:
        path = directory / name
        checksum = hashlib.md5(usedforsecurity=False)
        with path.open("rb") as stream:
            while block := stream.read(65536):
                checksum.update(block)
        files[name] = {
            "bytes": path.stat().st_size,
            "sha256": file_hash(path),
            "md5": base64.b64encode(checksum.digest()).decode(),
            "state": "PLANNED",
            "session": "",
            "generation": "",
        }
    row = {
        "id": intent_id(preview, fence),
        "owner": preview.asset.owner_id,
        "asset": str(preview.asset_id),
        "preview": str(preview.pk),
        "run": str(preview.run_id),
        "fence": fence,
        "bucket": bucket,
        "source_sha256": preview.source_sha256,
        "state": "OPEN",
        "files": files,
    }

    def create(old):
        if old is not None and old != row:
            raise LedgerFailure("PREVIEW_WRITE_ALREADY_PLANNED")
        return row

    result = ledger().update(row["id"], create)
    sync_holds()
    return result


def current(identity):
    return ledger().records()[str(identity)][0]


def file_state(identity, name, state, **receipts):
    def change(row):
        if row is None:
            raise LedgerFailure("PREVIEW_WRITE_MISSING")
        if state == "INITIALIZING" and row["state"] != "OPEN":
            raise LedgerFailure("PREVIEW_WRITE_REVOKED")
        row["files"][name].update(state=state, **receipts)
        return row

    return ledger().update(str(identity), change)


def check_open(identity, check):
    check()
    if current(identity)["state"] != "OPEN":
        raise LedgerFailure("PREVIEW_WRITE_REVOKED")


def upload_file(identity, name, path, storage, check):
    check_open(identity, check)
    row = file_state(identity, name, "INITIALIZING")  # Durable BEFORE initialization RPC.
    item, key = row["files"][name], prefix(row) + name
    session = storage.begin_preview(key, item["bytes"], item["md5"], identity)
    # Save late receipts even after revocation: cleanup needs the private capability.
    row = file_state(identity, name, "SESSION", session=session)
    check_open(identity, check)
    offset, generation = 0, ""
    failures = 0
    probing = False
    with path.open("rb") as source:
        for _ in range(256):  # Bounded total requests, including no-progress/probe retries.
            check_open(identity, check)
            source.seek(offset)
            block = None if probing else source.read(min(8388608, item["bytes"] - offset))
            try:
                received, generation = storage.preview_upload(session, key, item, offset, block)
            except CloudFailure as error:
                failures += 1
                if not error.retryable or failures > 3:
                    raise
                # No blind replay or initialization retry; probe the same persisted session.
                probing = True
                time.sleep(min(2**failures, 4))
                continue
            if (
                received < offset
                or received > item["bytes"]
                or (not probing and received > offset + len(block))
            ):
                raise CloudFailure("INVALID_PREVIEW_OFFSET", retryable=False)
            if generation:
                file_state(identity, name, "FINALIZED", generation=str(generation))
                check_open(identity, check)
                return generation
            if received == offset and not probing:
                failures += 1
                if failures > 3:
                    raise CloudFailure("PREVIEW_UPLOAD_NO_PROGRESS", retryable=False)
            offset, probing = received, False
    raise CloudFailure("PREVIEW_UPLOAD_REQUEST_LIMIT", retryable=False)


def published(preview, fence):
    def change(row):
        if row is None or row["state"] != "OPEN":
            raise LedgerFailure("PREVIEW_WRITE_REVOKED")
        row["state"] = "PUBLISHED"
        return row

    ledger().update(intent_id(preview, fence), change)
    sync_holds()


def revoke_ids(preview_ids=None):
    rows = sync_holds()
    selected = None if preview_ids is None else {str(x) for x in preview_ids}
    for identity, (row, _) in rows.items():
        if row["state"] == "ERASED" or (selected is not None and row["preview"] not in selected):
            continue

        def change(old):
            old["state"] = "CLEANUP"
            return old

        ledger().update(identity, change)
    sync_holds()


def storage_for_intent(row):
    if not settings.GCS_PREVIEW_WRITES_QUALIFIED:
        raise CloudFailure("GCS_PREVIEW_UNQUALIFIED", retryable=False)
    return GooglePrivateStorage(
        authorized_session(), row["bucket"], row["owner"], UUID(row["asset"])
    )


def cleanup(identity):
    row = current(identity)
    if row["state"] == "ERASED":
        return True
    if row["state"] != "CLEANUP":
        return False
    if any(x["state"] == "INITIALIZING" for x in row["files"].values()):
        return False  # Unknown capability, no invented expiry/refund.
    remote = any(x["session"] for x in row["files"].values())
    storage = storage_for_intent(row) if remote else None
    for name, item in row["files"].items():
        if item["state"] == "STOPPED":
            continue
        if item["session"]:
            storage.stop_preview_session(item["session"], prefix(row) + name)
        file_state(identity, name, "STOPPED")
    if storage:
        storage.erase_preview(prefix(row))  # Every generation, then a fresh empty inventory.

    def erased(old):
        old["state"] = "ERASED"
        return old

    ledger().update(str(identity), erased)
    sync_holds()
    return True


def recover_all():
    rows = sync_holds()
    if not rows:
        return
    revoke_ids()
    incomplete = False
    for identity in ledger().records():
        incomplete |= not cleanup(identity)
    if incomplete:
        raise LedgerFailure("RESTORE_PREVIEW_WRITE_UNCONFIRMED")


def is_published(preview):
    try:
        row = current(intent_id(preview, preview.attempt_fence))
        return (
            row["state"] == "PUBLISHED"
            and row["owner"] == preview.asset.owner_id
            and row["asset"] == str(preview.asset_id)
            and row["source_sha256"] == preview.source_sha256
            and set(preview.manifest) == set(FILES)
        ) and all(
            row["files"][name]["sha256"] == item["sha256"]
            and item["key"] == prefix(row) + name
            and row["files"][name]["generation"] == item["generation"]
            and row["files"][name]["bytes"] == item["bytes"]
            for name, item in preview.manifest.items()
        )
    except (KeyError, ValueError, CloudFailure):
        return False
