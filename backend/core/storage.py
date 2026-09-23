"""Private local storage and deletion lifecycle. Cloud adapters remain gated."""

import shutil
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

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


def delete_asset(owner, asset_id, storage=None):
    storage = storage or LocalStorage()
    with transaction.atomic():
        lock_owner(owner.pk)
        asset = ReplayAsset.objects.select_for_update().get(pk=asset_id, owner=owner)
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
        MatchContribution.objects.filter(run__asset=asset).delete()
        invalidate_for_events(ids)
    # Remote calls outside transaction; failure leaves tombstone and unfinished purge for retry.
    storage.cancel_upload(asset.upload_session)
    storage.delete_asset(asset.storage_key)
    ReplayAsset.objects.filter(pk=asset.pk).update(
        upload_cancelled=True, upload_session="", purge_completed_at=timezone.now()
    )


def accept_finalized_upload(asset_id, storage_key, storage=None):
    storage = storage or LocalStorage()
    asset = ReplayAsset.objects.select_related("owner").get(pk=asset_id)
    if storage_key != asset.storage_key:
        raise ValidationError("Finalized object key mismatch")
    if asset.deleted_at or not asset.owner.is_active:
        storage.delete_object(storage_key)
        return False
    return True


def delete_account(owner, storage=None):
    with transaction.atomic():
        lock_owner(owner.pk)
        profile, _ = Profile.objects.select_for_update().get_or_create(user=owner)
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
        NoticeReceipt.objects.filter(owner=owner).delete()
    for asset in ReplayAsset.objects.filter(owner=owner):
        delete_asset(owner, asset.pk, storage)


@transaction.atomic
def delete_metadata_match(owner, match_id):
    """Conservative local suppression: revoke this identity's sync consent on deletion.

    Keep only the revoked link while the local account exists; account deletion removes it.
    Production per-match suppression/retention needs its own reviewed policy.
    """
    lock_owner(owner.pk)
    match = Match.objects.get(pk=match_id, owner=owner)
    if (
        match.asset_id
        or match.replay_sources.filter(asset__isnull=False, asset__deleted_at=None).exists()
    ):
        raise ValidationError("Remove attached recordings before deleting match metadata")
    now = timezone.now()
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
