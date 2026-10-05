"""Quarantine restores, revoke stale authorization, replay controls, then purge."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from backend.core.control_journal import replaying, verified_records
from backend.core.models import (
    AccountChallenge,
    AccountSession,
    AnalysisRun,
    Match,
    MatchSuppression,
    MatchSync,
    PlayerGameIdentity,
    Profile,
    ReplayAsset,
    RunDispatch,
    UploadAdmission,
    UploadSession,
)
from backend.core.storage import delete_account, delete_asset, delete_metadata_match, storage_for


def apply_restore_controls():
    if not settings.RESTORE_QUARANTINE:
        raise ValueError("RESTORE_QUARANTINE_REQUIRED")
    records = verified_records()
    now = timezone.now()
    with transaction.atomic():
        Session.objects.all().delete()
        AccountSession.objects.all().delete()
        AccountChallenge.objects.all().delete()
        UploadAdmission.objects.all().delete()
        pending = UploadSession.objects.exclude(state__in=["COMPLETE", "CANCELLED"])
        ReplayAsset.objects.filter(uploadsession__in=pending).update(deleted_at=now, metadata={})
        pending.update(state="PURGING", fence=F("fence") + 1, verification_lease=None)
        Profile.objects.all().update(
            processing_consent_at=None,
            training_consent_at=None,
            processing_withdrawn_at=now,
            session_epoch=F("session_epoch") + 1,
        )
        for user_id in (
            get_user_model().objects.filter(profile__isnull=True).values_list("pk", flat=True)
        ):
            Profile.objects.create(user_id=user_id, processing_withdrawn_at=now)
        AnalysisRun.objects.all().update(
            status="CANCELLED", fence=F("fence") + 1, lease_until=None, result={}, phase="CANCELLED"
        )
        RunDispatch.objects.all().update(status="CANCELLED", lease_until=None)
        MatchSync.objects.all().update(
            status="CANCELLED",
            fence=F("fence") + 1,
            lease_until=None,
            checkpoint=None,
            stop_reason="RESTORE_QUARANTINE",
        )
        PlayerGameIdentity.objects.all().update(state="REVOKED", consent_scope="", deleted_at=now)
        from backend.core.models import PilotEnrollment
        from backend.core.pilots import erase_enrollment
        from backend.core.security import capacity_lock

        capacity_lock()
        # Restored study consent and blind labels cannot be trusted as current authorization.
        for member in PilotEnrollment.objects.filter(state="ACTIVE"):
            erase_enrollment(member)
        from backend.core.knowledge import restore_revoke

        restore_revoke()
        from backend.core.datasets import restore_revoke as revoke_datasets

        revoke_datasets()
        from backend.core.recognition import restore_revoke as revoke_recognition

        revoke_recognition()
        from backend.core.models import (
            ComparisonSession,
            DrillAssignment,
            ImprovementEvaluation,
            PracticeLog,
        )

        # Restore cannot resurrect a removed report or trust an old diagnosis authorization.
        PracticeLog.objects.all().delete()
        ComparisonSession.objects.all().delete()
        ImprovementEvaluation.objects.filter(invalidated_at=None).update(invalidated_at=now)
        DrillAssignment.objects.all().update(diagnosis={}, status="CANCELLED")

    token = replaying.set(True)
    try:
        for record in records:
            owner = get_user_model().objects.filter(pk=record["owner"]).first()
            payload, action = record["payload"], record["action"]
            if action == "ASSET_DELETE":
                asset = ReplayAsset.objects.filter(
                    pk=payload["asset"], owner_id=record["owner"]
                ).first()
                if asset:
                    delete_asset(owner, asset.pk)
                else:
                    purge_orphan(record["owner"], payload)
            elif owner and action == "MATCH_DELETE":
                match = Match.objects.filter(pk=payload["match"], owner=owner).first()
                if match:
                    asset_ids = set(
                        match.replay_sources.filter(asset__isnull=False).values_list(
                            "asset_id", flat=True
                        )
                    )
                    if match.asset_id:
                        asset_ids.add(match.asset_id)
                    for asset_id in asset_ids:
                        delete_asset(owner, asset_id)
                    Match.objects.filter(pk=match.pk).update(asset=None)
                    delete_metadata_match(owner, match.pk)
                for suppression in payload["suppressions"]:
                    MatchSuppression.objects.get_or_create(owner=owner, **suppression)
            elif owner and action == "CONSENT_WITHDRAW":
                field = (
                    "training_consent_at"
                    if payload["scope"] == "TRAINING"
                    else "processing_consent_at"
                )
                Profile.objects.filter(user=owner).update(**{field: None})
            elif owner and action == "PILOT_WITHDRAW":
                member = PilotEnrollment.objects.filter(
                    owner=owner, study_id=payload["study"], state="ACTIVE"
                ).first()
                if member:
                    with transaction.atomic():
                        capacity_lock()
                        erase_enrollment(member)
            elif owner and action == "PILOT_CLOSE":
                from backend.core.models import PilotStudy

                PilotStudy.objects.filter(owner=owner, pk=payload["study"]).update(
                    deleted_at=now,
                    state="CLOSED",
                    title="Closed study",
                    protocol={},
                    protocol_digest="",
                )
        for record in records:
            if record["action"] == "ACCOUNT_DELETE":
                for item in record["payload"]["assets"]:
                    purge_orphan(record["owner"], item)
                owner = get_user_model().objects.filter(pk=record["owner"]).first()
                if owner:
                    delete_account(owner)
        for asset in ReplayAsset.objects.filter(
            deleted_at__isnull=False, purge_completed_at=None
        ).select_related("owner"):
            delete_asset(asset.owner, asset.pk)
    finally:
        replaying.reset(token)
    if ReplayAsset.objects.filter(deleted_at__isnull=False, purge_completed_at=None).exists():
        raise ValueError("RESTORE_PURGE_INCOMPLETE")
    return len(records)


def purge_orphan(owner_id, item):
    """Retain post-backup upload deadlines without putting capability URLs in controls."""
    from django.utils.dateparse import parse_datetime

    from backend.core.cloud import CloudFailure

    owner = get_user_model().objects.filter(pk=owner_id).first()
    defaults = {
        "storage_key": item["storage_key"],
        "storage_provider": item["storage_provider"],
        "storage_generation": item["storage_generation"],
        "deleted_at": timezone.now(),
        "bytes": item.get("bytes", 536870912 if item["storage_provider"] == "GCS" else 0),
        "upload_expires_at": parse_datetime(item["upload_expires_at"])
        if item.get("upload_expires_at")
        else None,
    }
    if owner:
        asset, _ = ReplayAsset.objects.get_or_create(
            pk=item["asset"], owner=owner, defaults=defaults
        )
        delete_asset(owner, asset.pk)
    else:
        orphan = ReplayAsset(id=item["asset"], owner_id=owner_id, **defaults)
        storage_for(orphan).delete_asset(orphan.storage_key)
        if orphan.upload_expires_at and orphan.upload_expires_at > timezone.now():
            raise CloudFailure("UPLOAD_SESSION_EXPIRY_PENDING")
