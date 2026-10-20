"""Independent Batch execution intent, including workers absent after SQL restore."""

import copy
from uuid import UUID, uuid5

from django.conf import settings
from django.db import transaction

from analysis.preview_bundle import MAX_BYTES
from backend.core.cloud import CloudFailure
from backend.core.cloud_journal import CloudLog
from backend.core.models import (
    AnalysisRun,
    ExecutionSlot,
    RecordingPreview,
    ReplayAsset,
    RunDispatch,
)
from backend.core.preview_ledger import LedgerFailure

STATES = {
    "PLANNED": {"PLANNED", "SUBMITTING", "STOPPED"},
    "SUBMITTING": {"SUBMITTING", "ACTIVE", "STOPPING", "STOPPED"},
    "ACTIVE": {"ACTIVE", "STOPPING"},
    "STOPPING": {"STOPPING", "STOPPED"},
    "STOPPED": {"STOPPED"},
}


def enabled():
    return settings.PREVIEW_CLOUD_BACKEND == "BATCH"


def identity(run_id, fence):
    return str(uuid5(UUID(str(run_id)), f"batch:{fence}"))


def reduce(records):
    rows = {}
    for row in records:
        if isinstance(row, dict) and set(row) == {"revoked_run"}:
            if str(UUID(row["revoked_run"])) != row["revoked_run"]:
                raise LedgerFailure("EXECUTION_REVOCATION_INVALID")
            continue
        if not isinstance(row, dict) or set(row) != {
            "id",
            "run",
            "fence",
            "owner",
            "asset",
            "source_bytes",
            "source_sha256",
            "source_generation",
            "dispatch",
            "generation",
            "seconds",
            "job",
            "spec",
            "state",
            "uid",
            "delete_operation",
            "revoked",
        }:
            raise LedgerFailure("EXECUTION_JOURNAL_INVALID")
        if row["id"] != identity(row["run"], row["fence"]) or row["state"] not in STATES:
            raise LedgerFailure("EXECUTION_JOURNAL_IDENTITY")
        old = rows.get(row["id"])
        if old:
            if any(
                row[k] != old[k] for k in set(row) - {"state", "uid", "delete_operation", "revoked"}
            ):
                raise LedgerFailure("EXECUTION_JOURNAL_PIN_CHANGED")
            if row["state"] not in STATES[old["state"]] or any(
                old[k] and row[k] != old[k] for k in ("uid", "delete_operation")
            ):
                raise LedgerFailure("EXECUTION_JOURNAL_TRANSITION")
            if old["revoked"] and not row["revoked"]:
                raise LedgerFailure("EXECUTION_JOURNAL_TRANSITION")
        elif row["state"] != "PLANNED" or row["uid"] or row["delete_operation"]:
            raise LedgerFailure("EXECUTION_JOURNAL_TRANSITION")
        rows[row["id"]] = row
    return rows


def history():
    configured = enabled() or bool(settings.GOOGLE_EXECUTION_JOURNAL_BUCKET)
    return CloudLog("execution").records()[0] if configured else []


def revocations(events):
    return {row["revoked_run"] for row in events if set(row) == {"revoked_run"}}


def records():
    return reduce(history())


def update(key, mutate):
    result = []

    def apply(history):
        old = reduce(history).get(key)
        row = mutate(copy.deepcopy(old))
        if (old is None or row["state"] == "SUBMITTING") and row["run"] in revocations(history):
            raise CloudFailure("BATCH_RUN_REVOKED", retryable=False)
        reduce([*history, row])  # Validate pins and irreversible transitions before signing.
        result[:] = [row]
        return None if row == old else row

    CloudLog("execution").update(apply)
    return result[0]


def change(key, state, **receipts):
    def mutate(old):
        if old is None:
            raise LedgerFailure("EXECUTION_JOURNAL_MISSING")
        old.update(state=state, **receipts)
        return old

    return update(key, mutate)


def plan(provider, run, fence, dispatch):
    if (
        run.asset.storage_provider != "GCS"
        or not run.asset.storage_generation
        or run.asset.storage_key != f"{run.owner_id}/{run.asset_id}/source.mp4"
    ):
        raise CloudFailure("BATCH_VERIFIED_SOURCE_REQUIRED", retryable=False)
    seconds = run.runbudget.attempt_seconds
    row = {
        "id": identity(run.pk, fence),
        "run": str(run.pk),
        "fence": fence,
        "owner": run.owner_id,
        "asset": str(run.asset_id),
        "source_bytes": run.asset.bytes,
        "source_sha256": run.asset.source_sha256,
        "source_generation": run.asset.storage_generation,
        "dispatch": str(dispatch.pk),
        "generation": dispatch.generation,
        "seconds": seconds,
        "job": provider.job_name(run.pk, fence),
        "spec": provider.spec(run.pk, fence, dispatch.pk, dispatch.generation, seconds),
        "state": "PLANNED",
        "uid": "",
        "delete_operation": "",
        "revoked": False,
    }

    def create(old):
        if old is not None and old != row:
            raise LedgerFailure("EXECUTION_ALREADY_PLANNED")
        return row

    return update(row["id"], create)


def launch(provider, run, fence, dispatch):
    row = plan(provider, run, fence, dispatch)
    row = change(row["id"], "SUBMITTING")  # Durable before any job creation RPC.
    try:
        uid = provider.create(row)
    except CloudFailure as error:
        if not error.ambiguous:
            change(row["id"], "STOPPED")  # Explicit remote rejection, not a timeout.
        raise

    def receipt(old):
        old["uid"] = uid  # A late receipt remains useful after durable stop was requested.
        if old["state"] == "SUBMITTING":
            old["state"] = "ACTIVE"
        return old

    try:
        update(row["id"], receipt)
    except (CloudFailure, ValueError, OSError):
        # The worker already exists. An archive outage here must not become an
        # "explicit rejection" that lets the dispatcher refund physical capacity.
        raise CloudFailure("BATCH_RECEIPT_PERSISTENCE_UNCONFIRMED", ambiguous=True) from None
    return row["job"]


def allowed(run_id, fence):
    events = history()
    row = reduce(events).get(identity(run_id, fence))
    return bool(
        row
        and str(run_id) not in revocations(events)
        and not row["revoked"]
        and row["state"] in {"SUBMITTING", "ACTIVE"}
    )


def run_revoked(run_id):
    events = history()
    rows = reduce(events)
    return str(run_id) in revocations(events) or any(
        row["run"] == str(run_id) and row["revoked"] for row in rows.values()
    )


def stop_runs(run_ids):
    ids = {str(value) for value in run_ids if value is not None}
    if not ids or not (enabled() or settings.GOOGLE_EXECUTION_JOURNAL_BUCKET):
        return
    # Revoke even a queued run with no execution/output intent. Otherwise SQL
    # rollback in the claim-to-plan interval can resurrect cancelled work.
    for run_id in sorted(ids):

        def revoke(events, run_id=run_id):
            reduce(events)
            return None if run_id in revocations(events) else {"revoked_run": run_id}

        CloudLog("execution").update(revoke)
    for key, row in records().items():
        if row["run"] not in ids:
            continue

        def stop(old):
            old["revoked"] = True
            if old["state"] == "PLANNED":
                old["state"] = "STOPPED"
            elif old["state"] != "STOPPED":
                old["state"] = "STOPPING"
            return old

        update(key, stop)


def extra_slots(owner_id=None):
    count = 0
    for row in records().values():
        if row["state"] == "STOPPED" or (owner_id is not None and row["owner"] != owner_id):
            continue
        if not ExecutionSlot.objects.filter(
            run_id=row["run"], fence=row["fence"], runtime="CLOUD_BATCH", released_at=None
        ).exists():
            count += 1
    return count


def extra_storage(owner_id=None):
    total, seen_sources = 0, set()
    for row in records().values():
        if owner_id is not None and row["owner"] != owner_id:
            continue
        # An untracked retained original is not erased merely because its VM stopped.
        key = (row["owner"], row["asset"])
        if (
            key not in seen_sources
            and not ReplayAsset.objects.filter(pk=row["asset"], owner_id=row["owner"]).exists()
        ):
            total += row["source_bytes"]
        seen_sources.add(key)
        if (
            row["state"] != "STOPPED"
            and not RecordingPreview.objects.filter(asset_id=row["asset"], run_id=row["run"])
            .exclude(state="PURGED")
            .exists()
        ):
            total += MAX_BYTES
    return total


def reconcile(provider, *, restore=False):
    from backend.core.jobs import acknowledge_stopped, locked_run

    events = history()
    rows, revoked = reduce(events), revocations(events)
    for key, row in rows.items():
        slot = ExecutionSlot.objects.filter(
            run_id=row["run"], fence=row["fence"], runtime="CLOUD_BATCH", released_at=None
        ).first()
        run = AnalysisRun.objects.filter(pk=row["run"]).first()
        stop = (
            restore
            or row["run"] in revoked
            or row["revoked"]
            or not slot
            or bool(slot.stop_requested_at)
            or not run
            or run.status != "PROCESSING"
        )
        try:
            if row["state"] == "PLANNED" and stop:
                # A compare-and-append rechecks the state if a launcher won the sequence.
                def no_rpc(old):
                    old["state"] = "STOPPED" if old["state"] == "PLANNED" else "STOPPING"
                    return old

                row = update(key, no_rpc)
            if row["state"] != "STOPPED":
                body = provider.inspect(row)
                if body is not None and not row["uid"]:
                    row = update(key, lambda old, uid=body["uid"]: {**old, "uid": uid})
                remote_terminal = body is not None and body.get("status", {}).get("state") in {
                    "SUCCEEDED",
                    "FAILED",
                    "DELETION_IN_PROGRESS",
                }
                if stop or remote_terminal or row["state"] == "STOPPING":
                    row = change(key, "STOPPING")
                    if row["uid"] and not row["delete_operation"] and body is not None:
                        operation = provider.delete(row)
                        row = change(key, "STOPPING", delete_operation=operation)
                    if provider.stopped(row):
                        row = change(key, "STOPPED")
            if row["state"] == "STOPPED" and slot:
                with transaction.atomic():
                    current_run = locked_run(slot.run_id)
                    if current_run.status == "PROCESSING" and current_run.fence == slot.fence:
                        current_run.lease_until = None
                        current_run.save(update_fields=["lease_until"])
                    acknowledge_stopped(slot.run_id, slot.fence)
                RunDispatch.objects.filter(pk=row["dispatch"]).update(lease_until=None)
        except (CloudFailure, ValueError, OSError):
            if restore:
                raise
            continue  # Uncertainty never refunds a physical worker slot.
    if restore and any(row["state"] != "STOPPED" for row in records().values()):
        raise LedgerFailure("RESTORE_CLOUD_EXECUTION_UNCONFIRMED")
