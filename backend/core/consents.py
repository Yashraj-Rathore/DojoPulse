"""Versioned local policy receipts and a transactional stop for future processing."""

import hashlib
import hmac
import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from backend.core.models import (
    AnalysisRun,
    ConsentReceipt,
    MatchSync,
    PlayerGameIdentity,
    Profile,
    UploadAdmission,
)
from backend.core.ownership import lock_owner

POLICY_VERSION = "local-research-2026-09/1"
POLICIES = {
    "TERMS": "This local research prototype has no validated automatic coaching. An account does not prove ownership of a Tekken identity. Public service terms require separate release review.",
    "PROCESSING": "Process the matches and recordings you choose to provide for your private training workspace. Retained recordings expire under the stated capture policy. Withdrawal stops new processing and queued work; existing records remain available for export or deletion. Re-enabling does not restart cancelled jobs or restore deleted data.",
    "TRAINING": "Optional permission to use eligible retained evidence to improve DojoPulse recognition models. No model-training service is enabled. Withdrawal stops future use; any real training operation still requires reviewed data rights and a separate release decision. This choice is not required for workspace processing.",
}


def policy_digest(scope):
    return hashlib.sha256(POLICIES[scope].encode()).hexdigest()


def require_processing(owner):
    if Profile.objects.filter(user=owner, processing_withdrawn_at__isnull=False).exists():
        raise ValidationError(
            "Processing consent is withdrawn. Re-enable it in account privacy controls first."
        )


@transaction.atomic
def record_consent(owner, scope, action, version, request_id, source="ACCOUNT"):
    current = lock_owner(owner.pk)
    if not current.is_active or scope not in POLICIES or action not in {"GRANT", "WITHDRAW"}:
        raise ValidationError("Invalid consent operation")
    if version != POLICY_VERSION or (scope == "TERMS" and action != "GRANT"):
        raise ValidationError("Review the current policy before continuing")
    prior = ConsentReceipt.objects.filter(owner=owner, request_id=request_id).first()
    if prior:
        if (prior.scope, prior.action, prior.policy_version) != (scope, action, version):
            raise ValidationError("Consent request ID already used")
        return prior
    profile, _ = Profile.objects.get_or_create(user=owner)
    if profile.deleted_at:
        raise ValidationError("Account is deleted")
    receipt = ConsentReceipt.objects.create(
        owner=owner,
        scope=scope,
        action=action,
        policy_version=version,
        policy_digest=policy_digest(scope),
        source=source,
        request_id=request_id,
    )
    now = timezone.now()
    if scope == "PROCESSING":
        profile.processing_consent_at = now if action == "GRANT" else None
        profile.processing_withdrawn_at = now if action == "WITHDRAW" else None
        if action == "WITHDRAW":
            AnalysisRun.objects.filter(owner=owner, status__in=["QUEUED", "PROCESSING"]).update(
                status="CANCELLED", fence=F("fence") + 1, lease_until=None
            )
            MatchSync.objects.filter(owner=owner).update(
                status="CANCELLED",
                fence=F("fence") + 1,
                lease_until=None,
                checkpoint=None,
                stop_reason="CONSENT_WITHDRAWN",
            )
            PlayerGameIdentity.objects.filter(owner=owner, deleted_at=None).update(
                state="REVOKED", deleted_at=now, consent_scope=""
            )
            UploadAdmission.objects.filter(owner=owner).delete()
    elif scope == "TRAINING":
        profile.training_consent_at = now if action == "GRANT" else None
    profile.save()
    return receipt


def suppression_digest(owner_id, game, provider, namespace, value):
    material = json.dumps([str(owner_id), game, provider, namespace, value], separators=(",", ":"))
    return hmac.new(
        settings.DATA_SUPPRESSION_KEY.encode(), material.encode(), hashlib.sha256
    ).hexdigest()
