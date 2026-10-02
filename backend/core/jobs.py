"""Durable local job state; hosted delivery may call the same commands."""

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from backend.core.models import (
    AnalysisRun,
    ExecutionSlot,
    Profile,
    ReplayAsset,
    ReplaySource,
    RunDispatch,
)
from backend.core.ownership import lock_owner
from backend.core.security import capacity_lock


def locked_run(run_id):
    owner_id = AnalysisRun.objects.values_list("owner_id", flat=True).get(pk=run_id)
    lock_owner(owner_id)
    return (
        AnalysisRun.objects.select_for_update(of=("self",))
        .select_related("asset", "owner")
        .get(pk=run_id)
    )


@transaction.atomic
def claim_run(run_id):
    if settings.RESTORE_QUARANTINE:
        return None
    run = locked_run(run_id)
    now = timezone.now()
    if (
        not run.owner.is_active
        or Profile.objects.filter(user=run.owner, deleted_at__isnull=False).exists()
        or Profile.objects.filter(user=run.owner, processing_withdrawn_at__isnull=False).exists()
    ):
        return None
    if (
        run.asset.owner_id != run.owner_id
        or run.asset.deleted_at
        or run.status
        in {
            "CANCELLED",
            "COMPLETED",
            "REVIEW_REQUIRED",
            "PARTIAL",
            "FAILED",
        }
    ):
        return None
    # Expiry revokes publication; it is not proof that the old process is dead.
    if ExecutionSlot.objects.filter(run=run, released_at=None).exists():
        return None
    if run.status == "PROCESSING" and run.lease_until and run.lease_until > now:
        return None
    if run.attempts >= 3:
        run.status, run.error_code = "FAILED", "RETRY_BUDGET_EXHAUSTED"
        run.save()
        return None
    capacity_lock()
    active = ExecutionSlot.objects.filter(released_at=None)
    if (
        active.count() >= settings.GLOBAL_ACTIVE_RUNS
        or active.filter(run__owner=run.owner).exists()
    ):
        return None
    run.status = "PROCESSING"
    run.fence += 1
    run.attempts += 1
    run.deadline_at = now + timedelta(seconds=settings.RUN_DEADLINE_SECONDS)
    run.lease_until = min(now + timedelta(seconds=settings.RUN_LEASE_SECONDS), run.deadline_at)
    run.heartbeat_at, run.phase, run.progress = now, "STARTING", 1
    run.save()
    ExecutionSlot.objects.create(run=run, fence=run.fence)
    RunDispatch.objects.get_or_create(run=run)
    return run.fence


@transaction.atomic
def finish_run(run_id, fence, report):
    run = locked_run(run_id)
    if (
        run.fence != fence
        or run.status != "PROCESSING"
        or run.asset.deleted_at
        or run.asset.owner_id != run.owner_id
        or not run.owner.is_active
        or not run.lease_until
        or run.lease_until <= timezone.now()
        or not run.deadline_at
        or run.deadline_at <= timezone.now()
        or Profile.objects.filter(user=run.owner, processing_withdrawn_at__isnull=False).exists()
    ):
        return False
    status = report["status"]
    if status not in {"FAILED", "REVIEW_REQUIRED", "PARTIAL", "COMPLETED"}:
        raise ValueError("Invalid terminal report status")
    run.result, run.status = report, status
    run.error_code = report.get("issues", [""])[0] if report.get("issues") else ""
    run.lease_until = None
    run.phase, run.progress = status, 100
    run.save()
    if "source" in report:
        sha = report["source"]["source_sha256"]
        if run.asset.source_sha256 and run.asset.source_sha256 != sha:
            raise ValueError("SOURCE_HASH_CHANGED")
        ReplayAsset.objects.filter(pk=run.asset_id).update(source_sha256=sha)
        ReplaySource.objects.filter(asset_id=run.asset_id, match__owner_id=run.owner_id).update(
            content_hash=sha
        )
    return True


@transaction.atomic
def cancel_run(owner, run_id):
    lock_owner(owner.pk)
    run = AnalysisRun.objects.select_for_update().get(pk=run_id, owner=owner)
    if run.status == "CANCELLED":
        return run
    if run.status not in {"QUEUED", "PROCESSING"}:
        raise ValidationError("Only queued or processing runs can be cancelled")
    run.status, run.lease_until = "CANCELLED", None
    run.fence += 1
    run.save()
    RunDispatch.objects.filter(run=run).update(status="CANCELLED", lease_until=None)
    ExecutionSlot.objects.filter(run=run, released_at=None).update(stop_requested_at=timezone.now())
    return run


@transaction.atomic
def enqueue_run(**fields):
    """Call inside the producer's owner/admission transaction."""
    run = AnalysisRun.objects.create(**fields)
    RunDispatch.objects.create(run=run)
    return run


@transaction.atomic
def heartbeat(run_id, fence, *, phase="ANALYZING", progress=10):
    if settings.RESTORE_QUARANTINE:
        return False
    run = locked_run(run_id)
    now = timezone.now()
    if (
        run.fence != fence
        or run.status != "PROCESSING"
        or run.asset.deleted_at
        or not run.owner.is_active
        or not run.lease_until
        or run.lease_until <= now
        or not run.deadline_at
        or run.deadline_at <= now
        or Profile.objects.filter(user=run.owner, processing_withdrawn_at__isnull=False).exists()
    ):
        return False
    if phase not in {"STARTING", "FETCHING", "ANALYZING", "PUBLISHING"} or not 0 <= progress <= 99:
        raise ValueError("INVALID_PROGRESS")
    run.heartbeat_at = now
    run.lease_until = min(now + timedelta(seconds=settings.RUN_LEASE_SECONDS), run.deadline_at)
    run.phase, run.progress = phase, max(run.progress, progress)
    run.save(update_fields=["heartbeat_at", "lease_until", "phase", "progress"])
    return True


@transaction.atomic
def acknowledge_stopped(run_id, fence):
    """Only after local cleanup or authoritative remote terminal observation."""
    run = locked_run(run_id)
    released = ExecutionSlot.objects.filter(run=run, fence=fence, released_at=None).update(
        released_at=timezone.now()
    )
    if not released:
        return
    if run.fence == fence and run.status == "PROCESSING":
        run.fence += 1
        run.status, run.lease_until, run.phase = "QUEUED", None, "QUEUED"
        run.save()
        dispatch, _ = RunDispatch.objects.get_or_create(run=run)
        dispatch.generation += 1
        dispatch.status, dispatch.attempts = "PENDING", 0
        dispatch.lease_until, dispatch.next_attempt_at = None, timezone.now()
        dispatch.task_name = dispatch.operation_name = dispatch.error_code = ""
        dispatch.save()
    elif run.status != "QUEUED":
        RunDispatch.objects.filter(run=run).update(status="DONE", lease_until=None)


@transaction.atomic
def begin_execution(run_id, fence):
    """One worker entry per attempt, even if a transport delivers duplicates."""
    run = locked_run(run_id)
    if not heartbeat(run_id, fence, phase="STARTING", progress=1):
        return False
    slot = ExecutionSlot.objects.select_for_update().get(run=run, fence=fence)
    if slot.started_at or slot.released_at or slot.stop_requested_at:
        return False
    slot.started_at = timezone.now()
    slot.save(update_fields=["started_at"])
    RunDispatch.objects.filter(run=run).update(status="STARTED", lease_until=None)
    return True


def reconcile_runs():
    """Fence stale work and request stop. Never free capacity based on wall time alone."""
    now = timezone.now()
    for run_id in AnalysisRun.objects.filter(status="PROCESSING", lease_until__lte=now).values_list(
        "pk", flat=True
    ):
        with transaction.atomic():
            run = locked_run(run_id)
            if run.status != "PROCESSING" or (run.lease_until and run.lease_until > now):
                continue
            ExecutionSlot.objects.filter(run=run, released_at=None).update(stop_requested_at=now)
            run.phase, run.error_code = "STOPPING", "STALE_EXECUTION"
            run.save(update_fields=["phase", "error_code"])
    # Deletion/withdrawal can revoke runs without going through cancel_run.
    ExecutionSlot.objects.filter(released_at=None).exclude(run__status="PROCESSING").update(
        stop_requested_at=now
    )
    RunDispatch.objects.filter(run__status="CANCELLED").update(status="CANCELLED", lease_until=None)
    for run in AnalysisRun.objects.filter(status="QUEUED"):
        RunDispatch.objects.get_or_create(run=run)
