"""Session-authenticated identity selection and history. Live providers stay disabled."""

from functools import wraps

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Prefetch
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from backend.core.api import handled
from backend.core.match_ingestion import active_owner, link_local_identity, start_local_sync
from backend.core.models import (
    Match,
    MatchSourceRecord,
    MatchSync,
    PlayerGameIdentity,
    ReplaySource,
)
from backend.core.search import SearchInput, current_events, filter_events, filter_matches
from backend.core.storage import delete_metadata_match
from ingestion.contracts import ExternalId, Operation
from ingestion.synthetic import END, START, SyntheticProvider

SELECTION_SALT = "match-identity-selection/1"


def private(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        response = function(*args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response

    return wrapped


def demo_enabled(user):
    return settings.DEBUG and settings.LOCAL_MATCH_IMPORTS and user.is_staff and user.is_active


def require_adapter(user, key):
    if not demo_enabled(user) or key not in {"synthetic-a", "synthetic-b"}:
        raise ValidationError(
            "Provider unavailable. Live match services are awaiting access review."
        )
    return SyntheticProvider(key)


@api_view(["GET"])
@private
def providers(request):
    enabled = demo_enabled(request.user)
    return Response(
        {
            "providers": [
                {
                    "key": "ewgf-public",
                    "label": "EWGF.GG",
                    "enabled": False,
                    "access_class": "COMMUNITY_PUBLIC_API",
                    "supports_name": False,
                    "reason": "Live access awaits usage review, a server API key and verified response data.",
                },
                {
                    "key": "wavu",
                    "label": "Wavu Wank",
                    "enabled": False,
                    "access_class": "COMMUNITY_PUBLIC_API",
                    "supports_name": False,
                    "reason": "The documented feed is global; player discovery and usage review are pending.",
                },
                *[
                    {
                        "key": key,
                        "label": label,
                        "enabled": enabled,
                        "access_class": "USER_UPLOAD",
                        "supports_name": False,
                        "example_id": "ExamplePlayer-A",
                        "reason": "Local demo with fictional matches."
                        if enabled
                        else "Local operator demo is disabled.",
                    }
                    for key, label in [
                        ("synthetic-a", "Demo source A"),
                        ("synthetic-b", "Demo source B"),
                    ]
                ],
            ]
        }
    )


class CandidateInput(serializers.Serializer):
    provider = serializers.CharField(max_length=100)
    query = serializers.CharField(max_length=200, trim_whitespace=False)
    kind = serializers.ChoiceField(choices=["RESOLVE_ID", "RESOLVE_NAME"], default="RESOLVE_ID")


@api_view(["POST"])
@private
@handled
def candidates(request):
    data = CandidateInput(data=request.data)
    data.is_valid(raise_exception=True)
    values = data.validated_data
    adapter = require_adapter(request.user, values["provider"])
    if values["kind"] != "RESOLVE_ID":
        return Response(
            {
                "error": "Name search is unavailable. Use an exact player ID.",
                "code": "OPERATION_UNSUPPORTED",
            },
            status=400,
        )
    found = adapter.resolve_player(values["query"], Operation.RESOLVE_ID)
    return Response(
        {
            "candidates": [
                {
                    "display_name": item.display_name,
                    "namespace": item.canonical_id.namespace,
                    "value": item.canonical_id.value,
                    "provider": adapter.key,
                    "ownership_verified": False,
                    "dataset_kind": item.source.dataset_kind,
                    "selection_token": signing.dumps(
                        {
                            "owner": str(request.user.pk),
                            "provider": adapter.key,
                            "namespace": item.canonical_id.namespace,
                            "value": item.canonical_id.value,
                        },
                        salt=SELECTION_SALT,
                    ),
                }
                for item in found
            ]
        }
    )


class LinkInput(serializers.Serializer):
    selection_token = serializers.CharField(max_length=2000)
    processing_consent = serializers.BooleanField()


def identity_data(item):
    return {
        "id": item.pk,
        "game": item.game_id,
        "namespace": item.namespace,
        "value": item.value,
        "display_label": item.display_label,
        "state": item.state,
        "provider": item.provenance.get("provider"),
        "linked_at": item.created_at,
        "can_sync": item.state == "CLAIMED" and not item.deleted_at,
    }


@api_view(["GET", "POST"])
@private
@handled
def identities(request):
    if request.method == "GET":
        return Response(
            {
                "identities": [
                    identity_data(item)
                    for item in PlayerGameIdentity.objects.filter(owner=request.user).order_by(
                        "created_at"
                    )
                ]
            }
        )
    data = LinkInput(data=request.data)
    data.is_valid(raise_exception=True)
    try:
        selection = signing.loads(
            data.validated_data["selection_token"], salt=SELECTION_SALT, max_age=300
        )
    except signing.BadSignature as error:
        raise ValidationError(
            "Player selection expired or was changed. Look up the player again."
        ) from error
    if selection["owner"] != str(request.user.pk):
        raise ValidationError("Player selection belongs to another workspace")
    adapter = require_adapter(request.user, selection["provider"])
    item = link_local_identity(
        request.user,
        "tekken8",
        adapter.resolve_player(selection["value"], Operation.RESOLVE_ID),
        ExternalId(selection["namespace"], selection["value"]),
        processing_consent=data.validated_data["processing_consent"],
    )
    return Response(identity_data(item), status=201)


def sync_data(job):
    coverage = None
    if job.coverage:
        gaps = list(dict.fromkeys(gap for page in job.coverage for gap in page.get("gaps", [])))
        truncated = any(page.get("truncated", False) for page in job.coverage)
        complete = (
            job.status == "COMPLETE"
            and not gaps
            and not truncated
            and all(page.get("coverage") == "COMPLETE_FOR_QUERY" for page in job.coverage)
        )
        coverage = {
            "coverage": "COMPLETE_FOR_QUERY" if complete else "PARTIAL",
            "gaps": gaps,
            "truncated": truncated,
        }
    return {
        "id": job.pk,
        "identity_id": job.identity_id,
        "provider": job.provider,
        "status": job.status,
        "coverage": coverage,
        "last_succeeded_at": job.last_succeeded_at,
        "next_attempt_at": job.next_attempt_at,
        "stop_reason": job.stop_reason,
        "requested_start": job.query_start,
        "requested_end": job.query_end,
    }


class SyncInput(serializers.Serializer):
    provider = serializers.CharField(max_length=100, required=False)


@api_view(["POST"])
@private
@handled
def sync_identity(request, identity_id):
    identity = PlayerGameIdentity.objects.get(pk=identity_id, owner=request.user)
    data = SyncInput(data=request.data)
    data.is_valid(raise_exception=True)
    adapter = require_adapter(
        request.user, data.validated_data.get("provider", identity.provenance.get("provider"))
    )
    job = start_local_sync(request.user, identity.pk, adapter.key, START, END)
    return Response(sync_data(job), status=202)


@api_view(["GET"])
@private
@handled
def sync_detail(request, sync_id):
    return Response(sync_data(MatchSync.objects.get(pk=sync_id, owner=request.user)))


@api_view(["DELETE"])
@private
@handled
@transaction.atomic
def unlink_identity(request, identity_id):
    active_owner(request.user)
    item = PlayerGameIdentity.objects.get(pk=identity_id, owner=request.user)
    item.state, item.deleted_at, item.consent_scope = "REVOKED", timezone.now(), ""
    item.save(update_fields=["state", "deleted_at", "consent_scope"])
    MatchSync.objects.filter(owner=request.user, identity=item).update(
        status="CANCELLED",
        fence=F("fence") + 1,
        lease_until=None,
        checkpoint=None,
        coverage=[],
        stop_reason="CONSENT_REVOKED",
    )
    return Response({"state": "REVOKED", "history_retained": True})


class HistoryInput(SearchInput):
    identity = serializers.UUIDField(required=False)
    evidence = serializers.ChoiceField(choices=["VIDEO", "PENDING", "METADATA"], required=False)
    offset = serializers.IntegerField(default=0, min_value=0, max_value=100000)
    limit = serializers.IntegerField(default=20, min_value=1, max_value=100)


def match_data(match, allow_uploads=False):
    players = list(match.participants.all())
    own = next((player for player in players if player.is_player), None)
    opponent = next((player for player in players if not player.is_player), None)
    source = next(iter(match.source_records.all()), None)
    representations = list(match.replay_sources.all())
    recordings = [row for row in representations if row.asset_id and not row.asset.deleted_at]
    identity = match.player_identity
    return {
        "id": match.pk,
        "identity_id": match.player_identity_id,
        "played_at": match.played_at,
        "game_build": match.game_build,
        "mode": match.mode,
        "dataset_kind": match.dataset_kind,
        "metadata_state": match.metadata_state,
        "result": ("WIN" if match.winner_slot == own.slot else "LOSS")
        if own and match.winner_slot in {1, 2} and match.metadata_state != "REVIEW_REQUIRED"
        else "UNKNOWN",
        "opponent": opponent.snapshot.get("display_name") if opponent else None,
        "character": own.character if own else None,
        "opponent_character": opponent.character if opponent else None,
        "evidence_status": "VIDEO_ATTACHED"
        if match.asset_id
        else "ATTRIBUTION_PENDING"
        if recordings
        else "EVIDENCE_REQUIRED",
        "can_delete_metadata": match.asset_id is None and not recordings,
        "can_attach_recording": bool(
            allow_uploads
            and identity
            and source
            and not match.asset_id
            and not recordings
            and match.metadata_state != "REVIEW_REQUIRED"
        ),
        "recording_target": {
            "metadata_revision": match.metadata_revision,
            "player_namespace": identity.namespace,
            "player_id": identity.value,
            "player_slot": own.slot if own else None,
            "opponent_ids": opponent.snapshot.get("identities", []) if opponent else [],
        }
        if identity
        else None,
        "recordings": [
            {
                "source_id": row.pk,
                "asset_id": row.asset_id,
                "attribution_state": row.attribution_state,
                "source_hash": row.content_hash,
                "run_id": row.asset.analysisrun_set.all()[0].pk
                if row.asset.analysisrun_set.all()
                else None,
                "status": row.asset.analysisrun_set.all()[0].status
                if row.asset.analysisrun_set.all()
                else "UNKNOWN",
                "can_manage": allow_uploads
                and row.attribution_state in {"PENDING_REVIEW", "APPROVED"},
            }
            for row in recordings
        ],
        "source": {
            "provider": source.provider,
            "access_class": source.access_class,
            "retrieved_at": source.retrieved_at,
            "revision": source.revision,
            "raw_game_version": source.assertion.get("raw_game_version"),
        }
        if source
        else None,
        "replays": [
            {
                "representation": row.representation,
                "availability": row.availability,
                "upstream_expires_at": row.upstream_expires_at,
            }
            for row in representations
        ],
    }


@api_view(["GET"])
@private
@handled
def history(request):
    data = HistoryInput(data=request.query_params)
    data.is_valid(raise_exception=True)
    values = data.validated_data
    matches = filter_matches(Match.objects.filter(owner=request.user, deleted_at=None), values)
    if "situation" in values or "outcome" in values:
        events = filter_events(
            current_events(request.user).exclude(match__metadata_state="REVIEW_REQUIRED"), values
        )
        matches = matches.filter(pk__in=events.values("match_id"))
    if "evidence" in values:
        pending = ReplaySource.objects.filter(asset__isnull=False, asset__deleted_at=None).values(
            "match_id"
        )
        if values["evidence"] == "VIDEO":
            matches = matches.filter(asset__isnull=False, asset__deleted_at=None)
        elif values["evidence"] == "PENDING":
            matches = matches.filter(asset__isnull=True, pk__in=pending)
        else:
            matches = matches.filter(asset__isnull=True).exclude(pk__in=pending)
    if "identity" in values:
        identity = PlayerGameIdentity.objects.get(pk=values["identity"], owner=request.user)
        matches = matches.filter(player_identity=identity)
    total = matches.count()
    start, limit = values["offset"], values["limit"]
    from backend.core.models import AnalysisRun

    rows = (
        matches.select_related("player_identity")
        .order_by("-played_at", "-id")
        .prefetch_related(
            "participants",
            "replay_sources__asset",
            Prefetch(
                "replay_sources__asset__analysisrun_set",
                queryset=AnalysisRun.objects.order_by("-created_at"),
            ),
            Prefetch("source_records", queryset=MatchSourceRecord.objects.order_by("-revision")),
        )[start : start + limit]
    )
    jobs = MatchSync.objects.filter(owner=request.user)
    if "identity" in values:
        jobs = jobs.filter(identity_id=values["identity"])
    return Response(
        {
            "matches": [
                match_data(row, settings.LOCAL_OPERATOR_UPLOADS and request.user.is_staff)
                for row in rows
            ],
            "total": total,
            "next_offset": start + limit if start + limit < total else None,
            "syncs": [sync_data(job) for job in jobs.order_by("-created_at")[:20]],
        }
    )


@api_view(["DELETE"])
@private
@handled
def remove_match(request, match_id):
    delete_metadata_match(request.user, match_id)
    return Response({"status": "DELETED", "identity_sync_revoked": True})
