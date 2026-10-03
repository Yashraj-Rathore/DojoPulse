"""Database-backed admission. Lock order: owner, then capacity; never the reverse."""

import hashlib
import hmac
import json
import logging
from contextvars import ContextVar
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.exceptions import APIException, Throttled
from rest_framework.throttling import BaseThrottle

from backend.core.models import (
    AnalysisRun,
    MatchSync,
    ReplayAsset,
    RequestBudget,
    SecurityMutex,
    UploadAdmission,
    UploadSession,
)
from backend.core.ownership import lock_owner

MAX_UPLOAD = 536870912
admission_id = ContextVar("upload_admission", default=None)
logger = logging.getLogger("dojopulse.security")


class IngestionUnavailable(APIException):
    status_code = 503
    default_detail = "External uploads gated. Local operator ingestion must be enabled."


def audit(event, reason):
    # Callers supply fixed codes only: no body, URLs, cookies, file paths or player IDs.
    logger.info(json.dumps({"event": event, "reason": reason}, sort_keys=True))


def capacity_lock():
    SecurityMutex.objects.get_or_create(key="capacity")
    SecurityMutex.objects.select_for_update().get(key="capacity")


@transaction.atomic
def consume_budget(scope, subject, limit, seconds=60):
    now = timezone.now()
    window = int(now.timestamp()) // seconds
    key = hmac.new(
        settings.SECRET_KEY.encode(), f"{scope}:{subject}:{window}".encode(), hashlib.sha256
    ).hexdigest()
    RequestBudget.objects.get_or_create(
        key=key, defaults={"expires_at": now + timedelta(seconds=seconds * 2)}
    )
    budget = RequestBudget.objects.select_for_update().get(key=key)
    if budget.count >= limit:
        return max(1, seconds - int(now.timestamp()) % seconds)
    budget.count += 1
    budget.save(update_fields=["count"])
    return 0


class AccountThrottle(BaseThrottle):
    def allow_request(self, request, view):
        if not request.user.is_authenticated:
            return True  # Authentication rejects the request before parsing any media.
        write = request.method not in {"GET", "HEAD", "OPTIONS"}
        limit = settings.API_WRITE_RATE if write else settings.API_READ_RATE
        self.delay = consume_budget("write" if write else "read", request.user.pk, limit)
        if self.delay:
            audit("request_rejected", "ACCOUNT_RATE_LIMIT")
        return not self.delay

    def wait(self):
        return self.delay


class PrivateResponseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/api/session" and request.method == "POST":
            delay = consume_budget(
                "login", request.META.get("REMOTE_ADDR", "unknown"), settings.LOGIN_RATE
            )
            if delay:
                audit("request_rejected", "LOGIN_RATE_LIMIT")
                response = JsonResponse(
                    {"error": "Too many attempts. Try again later."}, status=429
                )
                response["Retry-After"] = str(delay)
            else:
                response = self.get_response(request)
        else:
            response = self.get_response(request)
        if request.path.startswith("/api/"):
            response["Cache-Control"] = "private, no-store"
            response["X-Content-Type-Options"] = "nosniff"
            response["Referrer-Policy"] = "no-referrer"
        return response


def check_capacity(owner, incoming_bytes=0):
    """Called inside an owner transaction; counts pending physical deletion, too."""
    capacity_lock()
    now = timezone.now()
    reservations = UploadAdmission.objects.filter(expires_at__gt=now).exclude(pk=admission_id.get())
    assets = ReplayAsset.objects.filter(purge_completed_at=None)
    for records, pending, limit in (
        (
            assets.filter(owner=owner),
            reservations.filter(owner=owner),
            settings.OWNER_STORAGE_BYTES,
        ),
        (assets, reservations, settings.GLOBAL_STORAGE_BYTES),
    ):
        used = records.aggregate(total=Sum("bytes"))["total"] or 0
        held = pending.aggregate(total=Sum("reserved_bytes"))["total"] or 0
        if used + held + incoming_bytes > limit:
            audit("admission_rejected", "STORAGE_QUOTA")
            raise Throttled(
                wait=60, detail="Storage capacity reached; remove media or wait for purge."
            )


def admit_run(owner):
    capacity_lock()
    outstanding = AnalysisRun.objects.filter(status__in=["QUEUED", "PROCESSING"])
    recent = AnalysisRun.objects.filter(
        owner=owner, created_at__gte=timezone.now() - timedelta(days=1)
    )
    if (
        outstanding.filter(owner=owner).count() >= settings.OWNER_PENDING_RUNS
        or outstanding.count() >= settings.GLOBAL_PENDING_RUNS
        or recent.count() >= settings.OWNER_DAILY_RUNS
    ):
        audit("admission_rejected", "ANALYSIS_QUOTA")
        raise Throttled(wait=60, detail="Analysis capacity reached. Try again later.")


def admit_sync(owner):
    capacity_lock()
    active = MatchSync.objects.filter(status__in=["PENDING", "PROCESSING"])
    if (
        active.filter(owner=owner).count() >= settings.OWNER_PENDING_RUNS
        or active.count() >= settings.GLOBAL_PENDING_RUNS
    ):
        audit("admission_rejected", "SYNC_QUOTA")
        raise Throttled(wait=60, detail="Match discovery capacity reached. Try again later.")


@transaction.atomic
def reserve_upload(owner):
    current = lock_owner(owner.pk)
    if not current.is_active or not current.is_staff or not settings.LOCAL_OPERATOR_UPLOADS:
        raise IngestionUnavailable()
    from backend.core.consents import require_processing

    require_processing(current)
    from backend.core.budgets import check_daily_capacity

    check_daily_capacity(current)
    check_capacity(owner, MAX_UPLOAD)
    slots = UploadAdmission.objects.filter(expires_at__gt=timezone.now())
    sessions = UploadSession.objects.filter(
        state__in=["INITIALIZING", "UPLOADING", "VERIFYING", "PURGING"]
    )
    if (
        slots.filter(owner=owner).exists()
        or sessions.filter(owner=owner).exists()
        or slots.count() + sessions.count() >= settings.GLOBAL_UPLOAD_SLOTS
    ):
        raise Throttled(wait=60, detail="Upload already in progress or capacity reached.")
    admit_run(owner)
    return UploadAdmission.objects.create(
        owner=owner, reserved_bytes=MAX_UPLOAD, expires_at=timezone.now() + timedelta(minutes=15)
    )


def validate_admission(owner):
    if (
        admission_id.get()
        and not UploadAdmission.objects.filter(
            pk=admission_id.get(), owner=owner, expires_at__gt=timezone.now()
        ).exists()
    ):
        raise Throttled(wait=60, detail="Upload admission expired. Try again.")


def bounded_upload(function):
    @wraps(function)
    def wrapped(request, *args, **kwargs):
        admission = reserve_upload(request.user)
        token = admission_id.set(admission.pk)
        try:
            return function(request, *args, **kwargs)
        finally:
            admission_id.reset(token)
            UploadAdmission.objects.filter(pk=admission.pk).delete()

    return wrapped
