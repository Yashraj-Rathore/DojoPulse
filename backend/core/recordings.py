"""Local, reviewed video attribution to an existing imported match. No provider access."""

import hashlib
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from analysis.contracts import aware_time, digest
from backend.core.match_ingestion import active_owner
from backend.core.models import (
    AnalysisRun,
    DefinitionVersion,
    GameplayEvent,
    Match,
    Participant,
    Profile,
    ReplayAsset,
    ReplaySource,
)
from backend.core.storage import private_path

MAX_BYTES = 536870912


def require_local_operator(owner):
    if not settings.LOCAL_OPERATOR_UPLOADS or not owner.is_staff or not owner.is_active:
        raise PermissionDenied("Local operator uploads must be enabled")


def target_match(owner, match_id):
    match = Match.objects.select_related("player_identity").get(
        pk=match_id, owner=owner, deleted_at=None
    )
    if not match.player_identity_id or not match.source_records.exists():
        raise ValidationError("An imported match with player/source provenance is required")
    if match.metadata_state == "REVIEW_REQUIRED":
        raise ValidationError("Resolve the source correction before attaching evidence")
    return match


def validate_claim(match, claim):
    if claim["metadata_revision"] != match.metadata_revision:
        raise ValidationError("Match metadata changed. Refresh and review the match again")
    identity = match.player_identity
    if claim["player_id"] != identity.value or claim["player_namespace"] != identity.namespace:
        raise ValidationError("Recorded player identity differs from this match")
    players = list(match.participants.order_by("slot"))
    own = next((player for player in players if player.is_player), None)
    opponent = next((player for player in players if not player.is_player), None)
    if len(players) != 2 or own is None or opponent is None or claim["player_slot"] != own.slot:
        raise ValidationError("Recorded player slot differs from this match")
    if {
        "namespace": claim["opponent_namespace"],
        "value": claim["opponent_id"],
    } not in opponent.snapshot.get("identities", []):
        raise ValidationError("Recorded opponent identity differs from this match")
    if aware_time(claim["played_at"]) != match.played_at:
        raise ValidationError("Original play time differs from this match")
    if claim["dataset_kind"] != match.dataset_kind:
        raise ValidationError("Real and synthetic evidence must not be mixed")
    for field, proposed in [
        ("game_build", claim["game_build"]),
        ("mode", claim["source_kind"]),
        ("session_id", claim["session_id"]),
        ("context", "/".join(claim["characters"])),
    ]:
        current = getattr(match, field)
        if current not in {None, "unknown", ""} and current != proposed:
            raise ValidationError(f"Recording {field} conflicts with canonical match facts")
    for player, character in zip(players, claim["characters"], strict=True):
        if player.character is not None and player.character != character:
            raise ValidationError("Recorded character conflicts with the match")


def attach_recording(owner, match_id, upload, claim, request_id):
    require_local_operator(owner)
    target = target_match(owner, match_id)  # Reject foreign/deleted targets before writing bytes.
    validate_claim(target, claim)
    if not upload or not upload.name.lower().endswith(".mp4") or not 0 < upload.size <= MAX_BYTES:
        raise ValidationError("An MP4 up to 512 MiB is required")
    asset_id = uuid.uuid4()
    key = f"{owner.pk}/{asset_id}/source.mp4"
    path = private_path(key)
    path.parent.mkdir(parents=True, exist_ok=False)
    retained = False
    try:
        content = hashlib.sha256()
        written = 0
        with path.open("xb") as stream:
            for chunk in upload.chunks():
                written += len(chunk)
                if written > MAX_BYTES:
                    raise ValidationError("File exceeded limit")
                stream.write(chunk)
                content.update(chunk)
        if written == 0:
            raise ValidationError("Empty recording")
        with transaction.atomic():
            active_owner(owner)
            match = target_match(owner, match_id)
            validate_claim(match, claim)
            request_key = f"attachment:{request_id}"
            prior = AnalysisRun.objects.filter(owner=owner, request_key=request_key).first()
            if prior:
                source = ReplaySource.objects.get(asset=prior.asset, match=match)
                if (
                    prior.asset.deleted_at
                    or prior.asset.source_sha256 != content.hexdigest()
                    or source.attribution.get("claim_digest") != digest(claim)
                ):
                    raise ValidationError(
                        "Request key was already used for different or deleted evidence"
                    )
                return source, prior
            if (
                match.asset_id
                or match.replay_sources.filter(asset__isnull=False, asset__deleted_at=None).exists()
            ):
                raise ValidationError("Remove the existing recording before attaching another")
            if ReplayAsset.objects.filter(
                owner=owner, source_sha256=content.hexdigest(), deleted_at=None
            ).exists():
                raise ValidationError("These exact recording bytes are already in this workspace")
            asset = ReplayAsset.objects.create(
                id=asset_id,
                owner=owner,
                storage_key=key,
                source_sha256=content.hexdigest(),
                bytes=written,
                metadata={**claim, "attachment": True},
                retain_until=timezone.now() + timedelta(days=60),
            )
            source = ReplaySource.objects.create(
                match=match,
                asset=asset,
                source_record=match.source_records.order_by("-revision").first(),
                provider="user-video",
                access_class="USER_UPLOAD",
                representation="VIDEO",
                availability="AVAILABLE",
                checked_at=timezone.now(),
                local_retain_until=asset.retain_until,
                content_hash=asset.source_sha256,
                canonical_build=claim["game_build"],
                attribution_state="PENDING_REVIEW",
                attribution={
                    "claim": claim,
                    "claim_digest": digest(claim),
                    "submitted_by": owner.pk,
                    "submitted_at": timezone.now().isoformat(),
                    "metadata_revision": match.metadata_revision,
                },
            )
            run = AnalysisRun.objects.create(owner=owner, asset=asset, request_key=request_key)
            profile, _ = Profile.objects.get_or_create(user=owner)
            profile.processing_consent_at = timezone.now()
            profile.save(update_fields=["processing_consent_at"])
        retained = True
        return source, run
    finally:
        if not retained:
            path.unlink(missing_ok=True)
            path.parent.rmdir()  # Only this newly-created, now-empty upload directory.


@transaction.atomic
def review_recording(
    operator, source_id, source_hash, knowledge_revision, note, *, confirm_reviewed
):
    require_local_operator(operator)
    active_owner(operator)
    source = ReplaySource.objects.select_related("asset", "match").get(
        pk=source_id, match__owner=operator
    )
    match = target_match(operator, source.match_id)
    if not confirm_reviewed or not note.strip():
        raise ValidationError("Explicit visual attribution review and a review note are required")
    if (
        not source.asset_id
        or source.asset.deleted_at
        or source.attribution_state != "PENDING_REVIEW"
    ):
        raise ValidationError("Recording is unavailable or attribution was already decided")
    if source_hash != source.asset.source_sha256 or source_hash != source.content_hash:
        raise ValidationError("Reviewed recording hash differs")
    latest = source.asset.analysisrun_set.order_by("-created_at").first()
    if (
        not latest
        or latest.status not in {"REVIEW_REQUIRED", "PARTIAL", "COMPLETED"}
        or latest.result.get("source", {}).get("source_sha256") != source_hash
    ):
        raise ValidationError("Successful media validation required before attribution review")
    claim = source.attribution["claim"]
    validate_claim(match, claim)
    if match.asset_id:
        raise ValidationError("Another recording is already selected")
    knowledge = DefinitionVersion.objects.get(pk=knowledge_revision, kind="knowledge")
    if knowledge.game_build_id != claim["game_build"]:
        raise ValidationError("Knowledge build must match the reviewed recording")
    if match.dataset_kind == "real" and (
        knowledge.status != "APPROVED" or not knowledge.game_build.verified
    ):
        raise ValidationError("Real evidence requires approved knowledge and a verified build")
    proposed = {
        "game_build": claim["game_build"],
        "mode": claim["source_kind"],
        "session_id": claim["session_id"],
        "context": "/".join(claim["characters"]),
        "knowledge_revision": knowledge.key,
    }
    if GameplayEvent.objects.filter(match=match).exists() and any(
        getattr(match, field) != value for field, value in proposed.items()
    ):
        raise ValidationError(
            "Historical gameplay facts are frozen; attachment cannot rewrite them"
        )
    for field, value in proposed.items():
        setattr(match, field, value)
    match.asset = source.asset
    match.chronology_verified = True
    match.save()
    for slot, character in enumerate(claim["characters"], start=1):
        Participant.objects.filter(match=match, slot=slot).update(character=character)
    source.attribution_state = "APPROVED"
    source.attribution.update(
        {
            "reviewed_by": operator.pk,
            "reviewed_at": timezone.now().isoformat(),
            "review_note": note.strip(),
            "source_sha256": source_hash,
            "knowledge_revision": knowledge.key,
            "knowledge_hash": knowledge.content_hash,
        }
    )
    source.save(update_fields=["attribution_state", "attribution"])
    return source


@transaction.atomic
def reprocess_recording(owner, match_id, source_id, request_id):
    require_local_operator(owner)
    active_owner(owner)
    source = ReplaySource.objects.select_related("asset").get(
        pk=source_id, match_id=match_id, match__owner=owner, match__deleted_at=None
    )
    if (
        not source.asset_id
        or source.asset.deleted_at
        or source.attribution_state not in {"PENDING_REVIEW", "APPROVED"}
    ):
        raise ValidationError("Recording unavailable")
    key = f"reprocess:{request_id}"
    prior = AnalysisRun.objects.filter(owner=owner, request_key=key).first()
    if prior:
        if prior.asset_id != source.asset_id:
            raise ValidationError("Request key already belongs to different evidence")
        return prior
    if AnalysisRun.objects.filter(asset=source.asset, status__in=["QUEUED", "PROCESSING"]).exists():
        raise ValidationError("Recording is already queued or processing")
    return AnalysisRun.objects.create(owner=owner, asset=source.asset, request_key=key)
