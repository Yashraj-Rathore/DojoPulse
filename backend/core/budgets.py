"""Conservative daily resource reservations; physical work cannot refund itself early."""

import math

from django.conf import settings
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework.exceptions import Throttled

from backend.core.models import AnalysisRun, AttemptMetric, ExecutionSlot, RunBudget
from backend.core.security import capacity_lock


def totals(owner=None):
    query = RunBudget.objects.filter(Q(state="OPEN") | Q(day=timezone.localdate()))
    if owner is not None:
        query = query.filter(run__owner=owner)
    held = query.filter(state="OPEN").aggregate(
        media=Sum("reserved_media_seconds"), processing=Sum("reserved_processing_seconds")
    )
    used = query.filter(state="CLOSED").aggregate(
        media=Sum("charged_media_seconds"), processing=Sum("charged_processing_seconds")
    )
    return {
        "media_held": held["media"] or 0,
        "processing_held": held["processing"] or 0,
        "media_used": used["media"] or 0,
        "processing_used": used["processing"] or 0,
    }


def check_daily_capacity(owner):
    """Caller holds owner lock; preview before reading a body and recheck at enqueue."""
    capacity_lock()
    if settings.OPTIONAL_PROCESSING_PAUSED:
        raise Throttled(wait=60, detail="Analysis is temporarily paused by the operator.")
    media, processing = 600, settings.RUN_DEADLINE_SECONDS * settings.RUN_MAX_ATTEMPTS
    for scope_owner, media_limit, processing_limit in (
        (
            owner,
            settings.OWNER_MEDIA_SECONDS_PER_DAY,
            settings.OWNER_PROCESSING_SECONDS_PER_DAY,
        ),
        (None, settings.GLOBAL_MEDIA_SECONDS_PER_DAY, settings.GLOBAL_PROCESSING_SECONDS_PER_DAY),
    ):
        current = totals(scope_owner)
        if (
            current["media_used"] + current["media_held"] + media > media_limit
            or current["processing_used"] + current["processing_held"] + processing
            > processing_limit
        ):
            raise Throttled(
                wait=60,
                detail="Daily media or processing budget reached. Active reservations remain until work stops.",
            )
    return media, processing


def reserve_run(run):
    """Caller holds owner lock in a transaction; global mutex makes admission atomic."""
    prior = RunBudget.objects.filter(run=run).first()
    if prior:
        if prior.state != "OPEN":
            raise Throttled(detail="This analysis budget is already settled.")
        return prior
    media, processing = check_daily_capacity(run.owner)
    if (
        AnalysisRun.objects.filter(asset=run.asset, created_at__date=timezone.localdate())
        .exclude(pk=run.pk)
        .count()
        >= settings.ASSET_RUNS_PER_DAY
    ):
        raise Throttled(wait=60, detail="This recording reached its daily analysis limit.")
    return RunBudget.objects.create(
        run=run,
        reserved_media_seconds=media,
        reserved_processing_seconds=processing,
        attempt_seconds=settings.RUN_DEADLINE_SECONDS,
        max_attempts=settings.RUN_MAX_ATTEMPTS,
    )


def settle_run(run):
    """Caller holds owner lock. Cancellation is not proof of a stop."""
    budget = RunBudget.objects.filter(run=run, state="OPEN").first()
    if (
        not budget
        or run.status in {"QUEUED", "PROCESSING"}
        or ExecutionSlot.objects.filter(run=run, released_at=None).exists()
    ):
        return False
    capacity_lock()
    metrics = list(AttemptMetric.objects.filter(slot__run=run))
    attempts = ExecutionSlot.objects.filter(run=run).count()
    measured = [item.elapsed_seconds for item in metrics if item.elapsed_seconds is not None]
    missing = max(0, attempts - len(measured))
    budget.charged_processing_seconds = math.ceil(sum(measured) + missing * budget.attempt_seconds)
    durations = [item.media_seconds for item in metrics if item.media_seconds is not None]
    budget.charged_media_seconds = (
        math.ceil(max(durations)) if durations else (600 if attempts else 0)
    )
    budget.measurement_complete = missing == 0 and (bool(durations) or attempts == 0)
    budget.day, budget.state, budget.settled_at = timezone.localdate(), "CLOSED", timezone.now()
    budget.save()
    return True
