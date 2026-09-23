"""Bounded local discovery worker; providers never run inside the HTTP request."""

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from backend.core.match_ingestion import (
    claim_local_sync,
    commit_local_page,
    fail_local_sync,
    locked_sync,
    valid_lease,
)
from backend.core.models import MatchSync
from ingestion.contracts import ExternalId
from ingestion.synthetic import SyntheticProvider


@transaction.atomic
def quarantine(owner, job_id, token):
    job = locked_sync(owner, job_id)
    if valid_lease(job, token):
        job.status, job.stop_reason, job.lease_until = (
            "ATTENTION_REQUIRED",
            "INVALID_PROVIDER_DATA",
            None,
        )
        job.save(update_fields=["status", "stop_reason", "lease_until"])


def process_sync_page(job):
    if not (settings.DEBUG and settings.LOCAL_MATCH_IMPORTS and job.owner.is_staff):
        return False
    token = None
    try:
        token = claim_local_sync(job.owner, job.pk)
        if token is None:
            return False
        job.refresh_from_db()
        adapter = SyntheticProvider(job.provider)
        page = adapter.discover_matches(
            ExternalId(job.identity.namespace, job.identity.value),
            job.checkpoint,
            job.query_start,
            job.query_end,
        )
        return commit_local_page(job.owner, job.pk, token, job.checkpoint, page)
    except (ValidationError, ValueError, ObjectDoesNotExist):
        if token is not None:
            try:
                quarantine(job.owner, job.pk, token)
            except (ValidationError, ObjectDoesNotExist):
                pass  # Revocation/deletion already fences the job.
        return False
    except OSError:
        if token is not None:
            try:
                fail_local_sync(job.owner, job.pk, token)
            except (ValidationError, ObjectDoesNotExist):
                pass
        return False


def process_batch():
    now = timezone.now()
    jobs = (
        MatchSync.objects.filter(
            Q(status="PENDING") | Q(status="PROCESSING", lease_until__lte=now),
            Q(next_attempt_at=None) | Q(next_attempt_at__lte=now),
            owner__is_active=True,
            owner__is_staff=True,
            identity__deleted_at=None,
        )
        .select_related("owner", "identity")
        .order_by("created_at")[:50]
    )
    committed = 0
    for job in jobs:
        # Fair, bounded local batch. The fixture currently has two pages.
        for _ in range(4):
            if not process_sync_page(job):
                break
            committed += 1
    return committed
