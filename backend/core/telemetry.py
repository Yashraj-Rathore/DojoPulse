"""Fixed labels and allowlisted measurements; never log paths, users or payloads."""

import logging
import math
import time
from datetime import datetime, timedelta
from datetime import time as daytime

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from backend.core.jobs import locked_run
from backend.core.models import AttemptMetric, RequestMetric


def finite(value, maximum=10**12):
    return type(value) in {int, float} and math.isfinite(value) and 0 <= value <= maximum


@transaction.atomic
def record_attempt(run_id, fence, *, elapsed, cpu_seconds, peak_rss, report):
    run = locked_run(run_id)
    if not run.owner.is_active or run.asset.deleted_at or run.fence != fence:
        return False
    metric = (
        AttemptMetric.objects.select_for_update().filter(slot__run=run, slot__fence=fence).first()
    )
    if not metric or metric.elapsed_seconds is not None:
        return False
    cost = report.get("cost", {})
    if not isinstance(cost, dict):
        cost = {}
    source = report.get("source", {})
    if not isinstance(source, dict):
        source = {}
    fields = {
        "elapsed_seconds": elapsed,
        "coordinator_cpu_seconds": cpu_seconds,
        "coordinator_peak_rss_bytes": peak_rss,
        "decoder_cpu_seconds": cost.get("decoder_cpu_seconds"),
        "decoder_peak_rss_bytes": cost.get("decoder_peak_rss_bytes"),
        "derived_bytes": cost.get("derived_bytes"),
        "media_seconds": source.get("duration_seconds"),
    }
    for name, value in fields.items():
        if finite(value, 600 if name == "media_seconds" else 10**12):
            if name.endswith("bytes") and type(value) is not int:
                continue
            setattr(metric, name, value)
    metric.save()
    return True


def route_label(path):
    if path.startswith("/api/operations"):
        return "OPERATIONS"
    if path.startswith("/api/account") or path == "/api/session":
        return "ACCOUNT"
    if path.startswith("/api/assets/") and path.endswith("/media"):
        return "MEDIA"
    if path.startswith("/api/"):
        return "WORKSPACE"
    return None


@transaction.atomic
def record_request(label, status, elapsed):
    now = timezone.now().replace(second=0, microsecond=0)
    RequestMetric.objects.get_or_create(minute=now, route=label)
    metric = RequestMetric.objects.select_for_update().get(minute=now, route=label)
    metric.count += 1
    metric.server_errors += int(status >= 500)
    metric.throttled += int(status == 429)
    metric.seconds += elapsed
    metric.max_seconds = max(metric.max_seconds, elapsed)
    metric.save()


class OperationsMetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        label = route_label(request.path)
        if label:
            try:
                record_request(label, response.status_code, time.monotonic() - start)
            except Exception:
                logging.getLogger("dojopulse.security").warning(
                    '{"event":"telemetry","reason":"METRICS_UNAVAILABLE"}'
                )
        return response


def request_summary(days):
    cutoff = timezone.make_aware(
        datetime.combine(timezone.localdate() - timedelta(days=days - 1), daytime.min)
    )
    data = (
        RequestMetric.objects.filter(minute__gte=cutoff)
        .exclude(route="OPERATIONS")
        .aggregate(
            count=Sum("count"),
            server_errors=Sum("server_errors"),
            throttled=Sum("throttled"),
            seconds=Sum("seconds"),
        )
    )
    count = data["count"] or 0
    return {
        "samples": count,
        "server_errors": data["server_errors"] or 0,
        "throttled": data["throttled"] or 0,
        "availability": 1 - (data["server_errors"] or 0) / count if count else None,
        "mean_seconds": data["seconds"] / count if count else None,
        "scope": "Observed API responses; client errors count as available. Probes/operator traffic excluded.",
    }
