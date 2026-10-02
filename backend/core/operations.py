"""Bounded operator aggregates. Cost coverage is explicit; no provider calls or prices."""

import math
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Count, Max, OuterRef, Subquery, Sum
from django.utils import timezone

from backend.core.budgets import totals
from backend.core.models import (
    AnalysisRun,
    AttemptMetric,
    CostObservation,
    ExecutionSlot,
    Feedback,
    ImprovementEvaluation,
    MatchSync,
    OperatorWork,
    ReplayAsset,
    RunBudget,
    RunDispatch,
)
from backend.core.telemetry import request_summary

COMPONENTS = ("INFRASTRUCTURE", "PROVIDER", "REVIEW", "SUPPORT")


def percentile(values):
    values = sorted(v for v in values if v is not None)
    return values[max(0, math.ceil(len(values) * 0.95) - 1)] if values else None


def objective(value, samples, target, *, at_least=False):
    return {
        "value": value,
        "samples": samples,
        "target": target,
        "state": "INSUFFICIENT_DATA"
        if value is None or samples < settings.OPS_MIN_SAMPLES
        else (
            "WITHIN_PROPOSAL" if (value >= target if at_least else value <= target) else "BREACH"
        ),
        "approval": "PROPOSED_NOT_RELEASE_APPROVED",
    }


def costs(start, end, scope):
    # Whole UTC days, exact matching window, one record for every component.
    records = {
        row.component: row
        for row in CostObservation.objects.filter(period_start=start, period_end=end, scope=scope)
    }
    amounts = {key: str(records[key].amount_usd) if key in records else None for key in COMPONENTS}
    total = (
        sum((records[key].amount_usd for key in COMPONENTS), Decimal(0))
        if all(key in records for key in COMPONENTS)
        else None
    )
    kind = "synthetic" if scope == "SYNTHETIC" else "real"
    captures = (
        ReplayAsset.objects.filter(
            created_at__date__range=(start, end), deleted_at=None, match__dataset_kind=kind
        )
        .distinct()
        .count()
    )
    runs = (
        AnalysisRun.objects.filter(
            created_at__date__range=(start, end),
            asset__deleted_at=None,
            asset__match__dataset_kind=kind,
        )
        .distinct()
        .count()
    )
    evaluations = ImprovementEvaluation.objects.filter(
        created_at__date__range=(start, end), invalidated_at=None, result__dataset_kind=kind
    )
    newest = (
        ImprovementEvaluation.objects.filter(plan_id=OuterRef("plan_id"))
        .order_by("-revision")
        .values("pk")[:1]
    )
    evaluations = evaluations.filter(pk=Subquery(newest))
    loops = (
        evaluations.filter(
            result__verified_practice__gt=0,
            result__baseline__denominator__gt=0,
            result__followup__denominator__gt=0,
            plan__assignment__trainingsession__completed_at__isnull=False,
        )
        .values("plan_id")
        .distinct()
        .count()
    )
    comparable = (
        evaluations.filter(
            result__status__in=[
                "INCONCLUSIVE",
                "NO_MEANINGFUL_CHANGE",
                "OBSERVED_IMPROVEMENT",
                "OBSERVED_DETERIORATION",
            ]
        )
        .values("plan_id")
        .distinct()
        .count()
    )
    denominators = {
        "capture": captures,
        "analysis": runs,
        "completed_loop": loops,
        "comparable_evaluation": comparable,
    }
    return {
        "scope": scope,
        "period_start": start,
        "period_end": end,
        "components_usd": amounts,
        "total_usd": str(total) if total is not None else None,
        "missing_components": [key for key in COMPONENTS if key not in records],
        "denominators": denominators,
        "per_unit_usd": {
            key: str(total / count) if total is not None and count else None
            for key, count in denominators.items()
        },
        "method": "Whole-window allocated cost, not marginal price. All analysis outcomes included; one loop/comparison per plan. A loop needs completed practice, verified trials and measured baseline/follow-up. Observed means operator-entered evidence, not production qualification.",
    }


def snapshot(days=1):
    now = timezone.now()
    end = timezone.localdate()
    start = end - timedelta(days=days - 1)
    runs = AnalysisRun.objects.filter(created_at__date__range=(start, end))
    outcomes = dict(runs.values("status").annotate(n=Count("pk")).values_list("status", "n"))
    attempts = AttemptMetric.objects.filter(slot__claimed_at__date__range=(start, end))
    # Fetch only scalars; bounded reporting window, never payloads or identities.
    attempt_count = attempts.count()
    times = list(
        attempts.order_by("-slot__claimed_at").values_list("queued_seconds", "elapsed_seconds")[
            : settings.OPS_MAX_ATTEMPT_SAMPLES
        ]
    )
    queue = [item[0] for item in times if item[0] is not None]
    processing = [item[1] for item in times if item[1] is not None]
    terminal = sum(
        value for key, value in outcomes.items() if key not in {"QUEUED", "PROCESSING", "CANCELLED"}
    )
    completed = sum(outcomes.get(key, 0) for key in {"COMPLETED", "PARTIAL", "REVIEW_REQUIRED"})
    requests = request_summary(days)
    slos = {
        "queue_p95_seconds": objective(
            percentile(queue), len(queue), settings.OPS_QUEUE_TARGET_SECONDS
        ),
        "processing_p95_seconds": objective(
            percentile(processing), len(processing), settings.OPS_PROCESSING_TARGET_SECONDS
        ),
        "technical_completion": objective(
            completed / terminal if terminal else None,
            terminal,
            settings.OPS_COMPLETION_TARGET,
            at_least=True,
        ),
        "api_availability": objective(
            requests["availability"],
            requests["samples"],
            settings.OPS_AVAILABILITY_TARGET,
            at_least=True,
        ),
    }
    truncated = attempt_count > len(times)
    if truncated:
        for key in ("queue_p95_seconds", "processing_p95_seconds"):
            slos[key]["state"] = "PARTIAL_WINDOW"
    queued = AnalysisRun.objects.filter(status="QUEUED")
    oldest = queued.order_by("created_at").values_list("created_at", flat=True).first()
    age = max(0, (now - oldest).total_seconds()) if oldest else 0
    held = totals()
    counts = {
        "queued": queued.count(),
        "active_slots": ExecutionSlot.objects.filter(released_at=None).count(),
        "stale_slots": ExecutionSlot.objects.filter(
            released_at=None, run__lease_until__lte=now
        ).count(),
        "stop_pending": ExecutionSlot.objects.filter(
            released_at=None, stop_requested_at__isnull=False
        ).count(),
        "dispatch_attention": RunDispatch.objects.filter(
            status__in=["ATTENTION", "UNCERTAIN"]
        ).count(),
        "source_attention": MatchSync.objects.filter(
            status__in=["FAILED", "REVIEW_REQUIRED"]
        ).count(),
        "purge_pending": ReplayAsset.objects.filter(
            deleted_at__isnull=False, purge_completed_at=None
        ).count(),
        "support_open": Feedback.objects.filter(status="OPEN").count(),
        "unmeasured_settlements": RunBudget.objects.filter(
            day=end, state="CLOSED", measurement_complete=False
        ).count(),
        "retry_attempts": attempts.filter(attempt_number__gt=1).count(),
        "historical_attempt_dates_unknown": ExecutionSlot.objects.filter(claimed_at=None).count(),
    }
    alerts = [
        key.upper()
        for key in (
            "stale_slots",
            "stop_pending",
            "dispatch_attention",
            "source_attention",
            "purge_pending",
        )
        if counts[key]
    ]
    if truncated:
        alerts.append("METRIC_WINDOW_TRUNCATED")
    if age > settings.OPS_QUEUE_TARGET_SECONDS:
        alerts.append("QUEUE_DELAY")
    if (
        held["processing_held"] + held["processing_used"]
        >= settings.GLOBAL_PROCESSING_SECONDS_PER_DAY
        or held["media_held"] + held["media_used"] >= settings.GLOBAL_MEDIA_SECONDS_PER_DAY
    ):
        alerts.append("RESOURCE_BUDGET")
    alerts.extend(key.upper() for key, value in slos.items() if value["state"] == "BREACH")
    return {
        "schema": "dojopulse-operations/1",
        "generated_at": now,
        "days": days,
        "scope": "Local engineering telemetry; synthetic and real costs kept separate. No gameplay or deployed SLO qualification.",
        "processing_paused": settings.OPTIONAL_PROCESSING_PAUSED,
        "counts": counts,
        "oldest_queue_seconds": age,
        "outcomes": outcomes,
        "budget": held,
        "alerts": alerts,
        "attempt_measurements": attempts.aggregate(
            elapsed_seconds=Sum("elapsed_seconds"),
            coordinator_cpu_seconds=Sum("coordinator_cpu_seconds"),
            decoder_cpu_seconds=Sum("decoder_cpu_seconds"),
            source_bytes=Sum("source_bytes"),
            derived_bytes=Sum("derived_bytes"),
            coordinator_peak_rss_bytes=Max("coordinator_peak_rss_bytes"),
            decoder_peak_rss_bytes=Max("decoder_peak_rss_bytes"),
        ),
        "missing_elapsed_attempts": attempts.filter(elapsed_seconds=None).count(),
        "attempt_window_truncated": truncated,
        "work": list(
            OperatorWork.objects.filter(created_at__date__range=(start, end))
            .values("scope", "kind")
            .annotate(seconds=Sum("seconds"))
        ),
        "requests": requests,
        "objectives": slos,
        "costs": [costs(start, end, scope) for scope in ("SYNTHETIC", "OBSERVED")],
        "coverage_note": "RAM is sampled coordinator peak / parser-reported decoder peak; unavailable values remain null. Failed and unmeasured work remain visible.",
    }
