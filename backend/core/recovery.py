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
                    orphan = ReplayAsset(
                        id=payload["asset"],
                        owner_id=record["owner"],
                        storage_key=payload["storage_key"],
                        storage_provider=payload["storage_provider"],
                        storage_generation=payload["storage_generation"],
                    )
                    storage_for(orphan).delete_asset(orphan.storage_key)
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
        for record in records:
            if record["action"] == "ACCOUNT_DELETE":
                for item in record["payload"]["assets"]:
                    orphan = ReplayAsset(
                        id=item["asset"],
                        owner_id=record["owner"],
                        storage_key=item["storage_key"],
                        storage_provider=item["storage_provider"],
                        storage_generation=item["storage_generation"],
                    )
                    storage_for(orphan).delete_asset(orphan.storage_key)
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
