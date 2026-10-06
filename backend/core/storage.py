"""Private local storage and deletion lifecycle. Cloud adapters remain gated."""

import shutil
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from backend.core.control_journal import record_intent
from backend.core.loops import invalidate_for_events
from backend.core.models import (
    AnalysisRun,
    Feedback,
    GameplayEvent,
    Match,
    MatchContribution,
    MatchSourceRecord,
    MatchSync,
    NoticeReceipt,
    Participant,
    PlayerGameIdentity,
    Profile,
    ReplayAsset,
    ReplaySource,
    UploadAdmission,
)
from backend.core.ownership import lock_owner


def private_path(key: str) -> Path:
    root = settings.PRIVATE_DATA_ROOT.resolve()
    result = (root / key).resolve()
    if result == root or not result.is_relative_to(root):
        raise ValidationError("Invalid private object path")
    return result


class LocalStorage:
    def cancel_upload(self, session: str) -> None:
        if session:
            raise ValueError("Remote upload session requires configured cloud cancellation adapter")

    def delete_asset(self, storage_key: str) -> None:
        target = private_path(storage_key)
        directory = target.parent
        root = settings.PRIVATE_DATA_ROOT.resolve()
        if directory == root or not directory.is_relative_to(root):
            raise ValidationError("Refusing to delete storage root")
        if directory.exists():
            shutil.rmtree(directory)

    def delete_object(self, storage_key: str) -> None:
        private_path(storage_key).unlink(missing_ok=True)


def storage_for(asset):
    if asset.storage_provider == "LOCAL":
        return LocalStorage()
    if asset.storage_provider != "GCS" or not settings.GCS_PRIVATE_BUCKET:
        raise ValueError("STORAGE_PROVIDER_UNCONFIGURED")
    from backend.core.cloud import GooglePrivateStorage, authorized_session

    return GooglePrivateStorage(
        authorized_session(), settings.GCS_PRIVATE_BUCKET, asset.owner_id, asset.pk
    )


@contextmanager
def materialize(asset, storage=None):
    if asset.storage_provider == "LOCAL":
        yield private_path(asset.storage_key)
        return
    with tempfile.TemporaryDirectory(prefix="dojopulse-run-") as directory:
        target = Path(directory) / "source.mp4"
        (storage or storage_for(asset)).download(
            asset.storage_key, asset.storage_generation, target, asset.bytes
        )
        yield target


def delete_asset(owner, asset_id, storage=None):
    with transaction.atomic():
        lock_owner(owner.pk)
        asset = ReplayAsset.objects.select_for_update().get(pk=asset_id, owner=owner)
        record_intent(
            owner.pk,
            "ASSET_DELETE",
            asset=str(asset.pk),
            storage_key=asset.storage_key,
            storage_provider=asset.storage_provider,
            storage_generation=asset.storage_generation,
            upload_expires_at=asset.upload_expires_at.isoformat()
            if asset.upload_expires_at
            else None,
            bytes=asset.bytes,
        )
        if asset.deleted_at is None:
            asset.deleted_at = timezone.now()
            asset.save(update_fields=["deleted_at"])
        AnalysisRun.objects.filter(asset=asset).update(
            status="CANCELLED", fence=F("fence") + 1, lease_until=None, result={}
        )
        events = GameplayEvent.objects.filter(run__asset=asset)
        ids = list(events.values_list("pk", flat=True))
        events.update(deleted_at=timezone.now(), evidence=[], review={})
        # Imported match history survives loss of its optional recording.
        Match.objects.filter(asset=asset, metadata_revision__gt=0).update(asset=None)
        Match.objects.filter(asset=asset, metadata_revision=0).update(deleted_at=timezone.now())
        ReplaySource.objects.filter(asset=asset).update(
            availability="NOT_FOUND", content_hash="", attribution_state="WITHDRAWN", attribution={}
        )
        ReplayAsset.objects.filter(pk=asset.pk).update(metadata={})
        from backend.core.models import UploadSession

        UploadSession.objects.filter(asset=asset).update(
            state="PURGING",
            fence=F("fence") + 1,
            verification_lease=None,
        )
        from backend.core.pilots import invalidate_asset

        invalidate_asset(asset.pk)
        from backend.core.knowledge import invalidate_asset as invalidate_knowledge

        invalidate_knowledge(asset.pk)
        from backend.core.models import AttemptMetric

        AttemptMetric.objects.filter(slot__run__asset=asset).delete()
        MatchContribution.objects.filter(run__asset=asset).delete()
        invalidate_for_events(ids)
    # Remote calls outside transaction; failure leaves tombstone and unfinished purge for retry.
    storage = storage or storage_for(asset)
    storage.cancel_upload(asset.upload_session)
    storage.delete_asset(asset.storage_key)
    if (
        asset.storage_provider == "GCS"
        and not asset.upload_session
        and asset.upload_expires_at
        and asset.upload_expires_at > timezone.now()
    ):
        from backend.core.cloud import CloudFailure

        # A post-backup session capability may survive a restore without its URI.
        # Re-sweep its prefix until the documented upstream capability deadline.
        raise CloudFailure("UPLOAD_SESSION_EXPIRY_PENDING")
    ReplayAsset.objects.filter(pk=asset.pk).update(
        upload_cancelled=True,
        upload_session="",
        upload_expires_at=None,
        purge_completed_at=timezone.now(),
    )
    UploadSession.objects.filter(asset=asset).update(
        state="CANCELLED",
        expected_sha256="",
        expected_md5="",
        claim_digest="",
    )


def accept_finalized_upload(asset_id, storage_key, storage=None):
    asset = ReplayAsset.objects.select_related("owner").get(pk=asset_id)
    storage = storage or storage_for(asset)
    if storage_key != asset.storage_key:
        raise ValidationError("Finalized object key mismatch")
    if asset.deleted_at or not asset.owner.is_active:
        if asset.storage_provider == "GCS":
            storage.delete_object(storage_key, asset.storage_generation)
        else:
            storage.delete_object(storage_key)
        return False
    return True


def delete_account(owner, storage=None, *, password=None):
    with transaction.atomic():
        owner = lock_owner(owner.pk)
        if password is not None and (not owner.is_active or not owner.check_password(password)):
            raise ValidationError("Current password is incorrect")
        record_intent(
            owner.pk,
            "ACCOUNT_DELETE",
            assets=[
                {
                    "asset": str(asset.pk),
                    "storage_key": asset.storage_key,
                    "storage_provider": asset.storage_provider,
                    "storage_generation": asset.storage_generation,
                    "upload_expires_at": asset.upload_expires_at.isoformat()
                    if asset.upload_expires_at
                    else None,
                    "bytes": asset.bytes,
                }
                for asset in ReplayAsset.objects.filter(owner=owner)
            ],
        )
        from backend.core.pilots import erase_account

        erase_account(owner.pk)
        from backend.core.knowledge import erase_account as erase_knowledge

        erase_knowledge(owner.pk)
        profile, _ = Profile.objects.select_for_update().get_or_create(user=owner)
        from backend.core.companion import revoke_all

        revoke_all(owner)
        from backend.core.models import DevicePairing, RecordingDevice

        DevicePairing.objects.filter(owner=owner).update(label="")
        RecordingDevice.objects.filter(owner=owner).update(label="")
        profile.deleted_at = timezone.now()
        profile.processing_consent_at = None
        profile.training_consent_at = None
        profile.onboarding_completed_at = None
        profile.analysis_notices = profile.practice_notices = profile.followup_notices = False
        profile.save()
        owner.is_active = False
        owner.username = f"deleted-{owner.pk}-{uuid.uuid4().hex[:12]}"
        owner.email = owner.first_name = owner.last_name = ""
        owner.set_unusable_password()
        owner.save(
            update_fields=["is_active", "username", "email", "first_name", "last_name", "password"]
        )
        ReplayAsset.objects.filter(owner=owner).update(deleted_at=timezone.now(), metadata={})
        AnalysisRun.objects.filter(owner=owner).update(
            status="CANCELLED", fence=F("fence") + 1, lease_until=None, result={}
        )
        ReplaySource.objects.filter(match__owner=owner).update(
            availability="NOT_FOUND", content_hash="", attribution_state="WITHDRAWN", attribution={}
        )
        events = GameplayEvent.objects.filter(owner=owner)
        invalidate_for_events(list(events.values_list("pk", flat=True)))
        events.update(deleted_at=timezone.now(), evidence=[], review={})
        MatchContribution.objects.filter(match__owner=owner).delete()
        Match.objects.filter(owner=owner).update(deleted_at=timezone.now())
        MatchSync.objects.filter(owner=owner).delete()
        MatchSourceRecord.objects.filter(owner=owner).delete()
        Participant.objects.filter(match__owner=owner).update(snapshot={})
        Match.objects.filter(owner=owner).update(player_identity=None)
        PlayerGameIdentity.objects.filter(owner=owner).delete()
        Feedback.objects.filter(owner=owner).delete()
        from backend.core.models import (
            ComparisonSession,
            DrillAssignment,
            ImprovementEvaluation,
            PracticeLog,
        )

        PracticeLog.objects.filter(owner=owner).delete()
        ComparisonSession.objects.filter(owner=owner).delete()
        ImprovementEvaluation.objects.filter(owner=owner, invalidated_at=None).update(
            invalidated_at=timezone.now()
        )
        DrillAssignment.objects.filter(owner=owner).update(diagnosis={}, status="WITHDRAWN")

        NoticeReceipt.objects.filter(owner=owner).delete()
        UploadAdmission.objects.filter(owner=owner).delete()
        from backend.core.models import OperatorWork

        OperatorWork.objects.filter(owner=owner).delete()
        from backend.core.models import (
            AccountChallenge,
            AccountEmail,
            AccountSession,
            ConsentReceipt,
            MatchSuppression,
        )

        AccountChallenge.objects.filter(owner=owner).delete()
        AccountEmail.objects.filter(owner=owner).delete()
        AccountSession.objects.filter(owner=owner).delete()
        ConsentReceipt.objects.filter(owner=owner).delete()
        MatchSuppression.objects.filter(owner=owner).delete()
        profile.session_epoch += 1
        profile.save(update_fields=["session_epoch"])
    from backend.core.accounts import cleanup_account_mail

    cleanup_account_mail(owner.pk)
    for asset in ReplayAsset.objects.filter(owner=owner):
        delete_asset(owner, asset.pk, storage)


@transaction.atomic
def delete_metadata_match(owner, match_id):
    """Conservative local suppression: revoke this identity's sync consent on deletion.

    Known provider match IDs are retained only as owner-keyed HMACs. Explicit re-linking
    allows new imports while these matches stay suppressed. Account deletion removes
    both the revoked link and suppression receipts. Production policy remains gated.
    """
    lock_owner(owner.pk)
    match = Match.objects.get(pk=match_id, owner=owner)
    if (
        match.asset_id
        or match.replay_sources.filter(asset__isnull=False, asset__deleted_at=None).exists()
    ):
        raise ValidationError("Remove attached recordings before deleting match metadata")
    now = timezone.now()
    from backend.core.consents import suppression_digest
    from backend.core.models import MatchSuppression

    suppressions = [
        {
            "provider": source.provider,
            "key_digest": suppression_digest(
                owner.pk,
                match.game_id,
                source.provider,
                source.external_namespace,
                source.external_id,
            ),
        }
        for source in MatchSourceRecord.objects.filter(match=match, owner=owner)
    ]
    record_intent(owner.pk, "MATCH_DELETE", match=str(match.pk), suppressions=suppressions)
    from backend.core.models import UploadSession

    pending = UploadSession.objects.filter(match=match, owner=owner).exclude(
        state__in=["COMPLETE", "CANCELLED"]
    )
    for session in pending.select_related("asset"):
        asset = session.asset
        record_intent(
            owner.pk,
            "ASSET_DELETE",
            asset=str(asset.pk),
            storage_key=asset.storage_key,
            storage_provider=asset.storage_provider,
            storage_generation=asset.storage_generation,
            upload_expires_at=asset.upload_expires_at.isoformat()
            if asset.upload_expires_at
            else None,
            bytes=asset.bytes,
        )
    ReplayAsset.objects.filter(owner=owner, uploadsession__in=pending).update(
        deleted_at=now, metadata={}
    )
    pending.update(
        state="PURGING",
        fence=F("fence") + 1,
        verification_lease=None,
        next_attempt_at=None,
        error_code="MATCH_DELETED",
    )

    for source in MatchSourceRecord.objects.filter(match=match, owner=owner):
        MatchSuppression.objects.get_or_create(
            owner=owner,
            provider=source.provider,
            key_digest=suppression_digest(
                owner.pk,
                match.game_id,
                source.provider,
                source.external_namespace,
                source.external_id,
            ),
        )
    if match.player_identity_id:
        MatchSync.objects.filter(identity_id=match.player_identity_id, owner=owner).update(
            status="CANCELLED",
            fence=F("fence") + 1,
            lease_until=None,
            checkpoint=None,
            coverage=[],
            stop_reason="CONSENT_REVOKED",
        )
        PlayerGameIdentity.objects.filter(pk=match.player_identity_id, owner=owner).update(
            state="REVOKED",
            consent_scope="",
            display_label=None,
            provenance={},
            verification={},
            deleted_at=now,
        )
    events = GameplayEvent.objects.filter(match=match)
    invalidate_for_events(list(events.values_list("pk", flat=True)))
    events.update(deleted_at=now, evidence=[], review={})
    MatchContribution.objects.filter(match=match).delete()
    ReplaySource.objects.filter(match=match).delete()
    MatchSourceRecord.objects.filter(match=match).delete()
    Participant.objects.filter(match=match).delete()
    fields = {"deleted_at": now, "winner_slot": None, "metadata_state": "DELETED"}
    if not events.exists():
        fields.update(game_build=None, session_id=None, knowledge_revision=None, context=None)
    Match.objects.filter(pk=match.pk).update(**fields)
