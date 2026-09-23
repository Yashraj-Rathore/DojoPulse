"""Durable local job state; hosted delivery may call the same commands."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from backend.core.models import AnalysisRun, Profile
from backend.core.ownership import lock_owner


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
    run = locked_run(run_id)
    now = timezone.now()
    if (
        not run.owner.is_active
        or Profile.objects.filter(user=run.owner, deleted_at__isnull=False).exists()
    ):
        return None
    if run.asset.deleted_at or run.status in {
        "CANCELLED",
        "COMPLETED",
        "REVIEW_REQUIRED",
        "PARTIAL",
        "FAILED",
    }:
        return None
    if run.status == "PROCESSING" and run.lease_until and run.lease_until > now:
        return None
    if run.attempts >= 3:
        run.status, run.error_code = "FAILED", "RETRY_BUDGET_EXHAUSTED"
        run.save()
        return None
    run.status = "PROCESSING"
    run.fence += 1
    run.attempts += 1
    run.lease_until = now + timedelta(minutes=10)
    run.save()
    return run.fence


@transaction.atomic
def finish_run(run_id, fence, report):
    run = locked_run(run_id)
    if (
        run.fence != fence
        or run.status != "PROCESSING"
        or run.asset.deleted_at
        or not run.owner.is_active
        or not run.lease_until
        or run.lease_until <= timezone.now()
    ):
        return False
    status = report["status"]
    if status not in {"FAILED", "REVIEW_REQUIRED", "PARTIAL", "COMPLETED"}:
        raise ValueError("Invalid terminal report status")
    run.result, run.status = report, status
    run.error_code = report.get("issues", [""])[0] if report.get("issues") else ""
    run.lease_until = None
    run.save()
    return True


@transaction.atomic
def cancel_run(owner, run_id):
    lock_owner(owner.pk)
    run = AnalysisRun.objects.select_for_update().get(pk=run_id, owner=owner)
    run.status, run.lease_until = "CANCELLED", None
    run.fence += 1
    run.save()
    return run
