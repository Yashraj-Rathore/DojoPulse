"""Owner-scoped offline imports. No network transports or production provider activation."""

import json
from dataclasses import asdict
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from analysis.contracts import digest
from backend.core.loops import invalidate_for_events
from backend.core.models import (
    Game,
    GameplayEvent,
    Match,
    MatchContribution,
    MatchSourceRecord,
    MatchSync,
    Participant,
    PlayerGameIdentity,
    Profile,
    ReplaySource,
)
from backend.core.ownership import lock_owner
from ingestion.contracts import ExternalId, ProviderClass, require_aware, select_candidate

LOCAL_PROVIDERS = frozenset({"synthetic-a", "synthetic-b"})
LOCAL_POLICY = "synthetic-local/1"


def json_value(value):
    return json.loads(json.dumps(value, default=lambda x: x.isoformat()))


def require_local(provider, provenance=None):
    if provider not in LOCAL_PROVIDERS:
        raise ValidationError("Only built-in synthetic providers are enabled")
    if provenance and (
        provenance.provider != provider
        or provenance.dataset_kind != "synthetic"
        or provenance.access_class != ProviderClass.USER_UPLOAD
    ):
        raise ValidationError("Local imports require synthetic USER_UPLOAD provenance")


def active_owner(owner):
    current = lock_owner(owner.pk)
    if (
        not current.is_active
        or Profile.objects.filter(user=current, deleted_at__isnull=False).exists()
    ):
        raise ValidationError("Deleted account cannot ingest matches")


@transaction.atomic
def link_local_identity(owner, game, candidates, selected, *, processing_consent):
    active_owner(owner)
    if processing_consent is not True:
        raise ValidationError("Explicit processing consent required")
    candidate = select_candidate(candidates, selected)
    require_local(candidate.source.provider, candidate.source)
    game_row, _ = Game.objects.get_or_create(key=game)
    identity, _ = PlayerGameIdentity.objects.get_or_create(
        owner=owner,
        game=game_row,
        namespace=selected.namespace,
        value=selected.value,
        defaults={
            "display_label": candidate.display_name,
            "consent_scope": LOCAL_POLICY,
            "provenance": json_value(asdict(candidate.source)),
        },
    )
    if identity.deleted_at or identity.state != "CLAIMED":
        raise ValidationError("Identity link is revoked or requires review")
    return identity


@transaction.atomic
def start_local_sync(owner, identity_id, provider, start, end):
    active_owner(owner)
    require_local(provider)
    require_aware(start)
    require_aware(end)
    if start >= end:
        raise ValidationError("Invalid discovery window")
    identity = PlayerGameIdentity.objects.get(pk=identity_id, owner=owner, deleted_at=None)
    if identity.state != "CLAIMED" or identity.consent_scope != LOCAL_POLICY:
        raise ValidationError("Identity consent unavailable")
    job, _ = MatchSync.objects.get_or_create(
        owner=owner,
        identity=identity,
        provider=provider,
        query_start=start,
        query_end=end,
        defaults={"policy_version": LOCAL_POLICY},
    )
    if job.status == "COMPLETE":
        job.status = "PENDING"
        job.checkpoint = None
        job.attempts = 0
        job.save(update_fields=["status", "checkpoint", "attempts"])
    return job


def locked_sync(owner, sync_id):
    active_owner(owner)
    job = (
        MatchSync.objects.select_for_update(of=("self",))
        .select_related("identity")
        .get(pk=sync_id, owner=owner)
    )
    require_local(job.provider)
    if job.identity.deleted_at or job.identity.state != "CLAIMED":
        raise ValidationError("Identity revoked")
    return job


@transaction.atomic
def claim_local_sync(owner, sync_id):
    job = locked_sync(owner, sync_id)
    now = timezone.now()
    if job.status in {"COMPLETE", "CANCELLED", "ATTENTION_REQUIRED"}:
        return None
    if (job.lease_until and job.lease_until > now) or (
        job.next_attempt_at and job.next_attempt_at > now
    ):
        return None
    if job.attempts >= 5:
        job.status = "ATTENTION_REQUIRED"
        job.stop_reason = "RETRIES_EXHAUSTED"
        job.save()
        return None
    job.fence += 1
    job.attempts += 1
    job.status = "PROCESSING"
    job.lease_until = now + timedelta(minutes=10)
    job.save()
    return job.fence


def valid_lease(job, token):
    return job.status == "PROCESSING" and job.fence == token and job.lease_until > timezone.now()


@transaction.atomic
def fail_local_sync(owner, sync_id, token):
    job = locked_sync(owner, sync_id)
    if not valid_lease(job, token):
        return False
    job.status = "ATTENTION_REQUIRED" if job.attempts >= 5 else "PENDING"
    job.next_attempt_at = timezone.now() + timedelta(seconds=min(300, 2**job.attempts))
    job.lease_until = None
    job.stop_reason = "LOCAL_ACQUISITION_FAILED"
    job.save()
    return True


def _import_metadata(job, item):
    require_local(job.provider, item.provenance)
    identity = job.identity
    selected = ExternalId(identity.namespace, identity.value)
    if (
        item.game != identity.game_id
        or sum(selected in p.identities for p in item.participants) != 1
    ):
        raise ValidationError("Match does not unambiguously contain the linked player")
    assertion = json_value(asdict(item))
    assertion.pop("provenance")
    normalized_digest = digest(
        {
            "assertion": assertion,
            "adapter": item.provenance.adapter_version,
            "schema": item.provenance.schema_version,
        }
    )
    prior = (
        MatchSourceRecord.objects.filter(
            owner=job.owner,
            provider=job.provider,
            external_namespace=item.external_id.namespace,
            external_id=item.external_id.value,
        )
        .order_by("-revision")
        .first()
    )
    if prior:
        match = prior.match
        if match.deleted_at:
            raise ValidationError("Deleted match cannot be reimported")
        if match.player_identity_id != identity.pk:
            raise ValidationError(
                "Existing match belongs to another selected identity; review required"
            )
        if (
            prior.normalized_digest == normalized_digest
            and prior.raw_digest == item.provenance.record_digest
        ):
            return match
        if item.provenance.retrieved_at <= prior.retrieved_at:
            raise ValidationError("Out-of-order correction requires review")
    else:
        match = Match.objects.create(
            owner=job.owner,
            game=identity.game,
            player_identity=identity,
            played_at=item.played_at,
            dataset_kind="synthetic",
            metadata_state="METADATA_IMPORTED",
        )
    revision = prior.revision + 1 if prior else 1
    # Keep reviewed evidence coordinates and frozen event hashes intact on corrections.
    protected = bool(match.asset_id or GameplayEvent.objects.filter(match=match).exists())
    MatchSourceRecord.objects.create(
        owner=job.owner,
        match=match,
        provider=job.provider,
        policy_version=LOCAL_POLICY,
        access_class=item.provenance.access_class,
        external_namespace=item.external_id.namespace,
        external_id=item.external_id.value,
        revision=revision,
        retrieved_at=item.provenance.retrieved_at,
        raw_digest=item.provenance.record_digest,
        normalized_digest=normalized_digest,
        adapter_version=item.provenance.adapter_version,
        schema_version=item.provenance.schema_version,
        assertion=assertion,
        correction_state="REVIEW_REQUIRED" if protected else "ACCEPTED",
    )
    if protected:
        match.metadata_state = "REVIEW_REQUIRED"
        MatchContribution.objects.filter(match=match).delete()
        invalidate_for_events(
            list(GameplayEvent.objects.filter(match=match).values_list("pk", flat=True))
        )
    else:
        match.played_at = item.played_at
        match.game_build = item.canonical_game_build
        match.mode = item.mode
        match.winner_slot = item.winner_slot
        match.metadata_state = "METADATA_IMPORTED"
        for player in item.participants:
            Participant.objects.update_or_create(
                match=match,
                slot=player.slot,
                defaults={
                    "character": None,
                    "is_player": selected in player.identities,
                    "snapshot": json_value(asdict(player)),
                },
            )
    match.metadata_revision = revision
    match.save()
    return match


@transaction.atomic
def commit_local_page(owner, sync_id, token, expected_cursor, page):
    job = locked_sync(owner, sync_id)
    if not valid_lease(job, token) or job.checkpoint != expected_cursor:
        return False
    if (
        page.requested_start != job.query_start
        or page.requested_end != job.query_end
        or page.coverage not in {"COMPLETE_FOR_QUERY", "PARTIAL", "UNKNOWN"}
        or len(page.matches) > 1000
    ):
        raise ValidationError("Invalid or oversized discovery page")
    if page.next_cursor is not None and page.next_cursor == expected_cursor:
        raise ValidationError("Cursor did not advance")
    for item in page.matches:
        if not job.query_start <= item.played_at <= job.query_end:
            raise ValidationError("Match outside requested interval")
        _import_metadata(job, item)
    job.coverage.append(
        {
            "start": page.requested_start.isoformat(),
            "end": page.requested_end.isoformat(),
            "coverage": page.coverage,
            "gaps": list(page.gaps),
            "truncated": page.truncated,
        }
    )
    job.checkpoint = page.next_cursor
    job.last_succeeded_at = timezone.now()
    job.status = "COMPLETE" if page.next_cursor is None else "PENDING"
    job.lease_until = None
    job.next_attempt_at = None
    job.attempts = 0
    job.save()
    return True


def register_upload_source(match):
    """Dual-write while Match.asset remains the legacy evidence pointer."""
    asset = match.asset
    source, _ = ReplaySource.objects.get_or_create(
        match=match,
        asset=asset,
        defaults={
            "provider": "user-video",
            "access_class": "USER_UPLOAD",
            "representation": "VIDEO",
            "availability": "AVAILABLE" if not asset.deleted_at else "NOT_FOUND",
            "checked_at": timezone.now(),
            "local_retain_until": asset.retain_until,
            "content_hash": asset.source_sha256,
            "canonical_build": match.game_build,
        },
    )
    return source


@transaction.atomic
def mark_replay_unavailable(owner, source_id, availability):
    active_owner(owner)
    if availability not in {"EXPIRED", "NOT_FOUND", "VERSION_UNSUPPORTED"}:
        raise ValidationError("Invalid unavailable state")
    source = ReplaySource.objects.get(pk=source_id, match__owner=owner, match__deleted_at=None)
    source.availability = availability
    source.checked_at = timezone.now()
    source.save(update_fields=["availability", "checked_at"])
    return source
