"""Session/CSRF protected, scoped knowledge review and explicit reanalysis commands."""

from django.db import transaction
from django.db.models import Q
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from backend.core import knowledge
from backend.core.api import handled
from backend.core.match_api import private
from backend.core.models import (
    DefinitionVersion,
    GameBuild,
    KnowledgeProposal,
    KnowledgeReanalysis,
    ReplayAsset,
)


class Proposal(serializers.Serializer):
    key = serializers.RegexField(knowledge.KEY)
    kind = serializers.ChoiceField(choices=knowledge.KINDS)
    build_key = serializers.CharField(max_length=80)
    dataset_kind = serializers.ChoiceField(choices=["synthetic", "real"])
    payload = serializers.JSONField()
    provenance = serializers.DictField()
    asset_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1, max_length=10)
    reviewer_one = serializers.IntegerField(min_value=1)
    reviewer_two = serializers.IntegerField(min_value=1)
    request_id = serializers.UUIDField()


class Review(serializers.Serializer):
    proposal_hash = serializers.RegexField(r"^[a-f0-9]{64}$")
    decision = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
    note = serializers.CharField(max_length=2000)
    confirm_reviewed = serializers.BooleanField()
    request_id = serializers.UUIDField()


class Reanalysis(serializers.Serializer):
    match_id = serializers.UUIDField()
    mapping_key = serializers.RegexField(knowledge.KEY)
    request_id = serializers.UUIDField()


class Build(serializers.Serializer):
    version = serializers.RegexField(r"^[A-Za-z0-9_.-]{1,30}$")
    platform = serializers.ChoiceField(choices=["steam", "ps5", "xbox_series", "synthetic"])


@api_view(["POST"])
@private
@handled
@transaction.atomic
def builds(request):
    knowledge.actor(request.user)
    data = Build(data=request.data)
    data.is_valid(raise_exception=True)
    version, platform = data.validated_data["version"], data.validated_data["platform"]
    key = f"tekken8/{platform}/{version}"
    build, _ = GameBuild.objects.get_or_create(
        key=key,
        defaults={
            "game_id": "tekken8",
            "platform": platform,
            "provenance": {"status": "UNVERIFIED_OPERATOR_REGISTRATION"},
        },
    )
    if build.game_id != "tekken8" or build.platform != platform:
        raise PermissionDenied("Build registration conflicts with the existing canonical key")
    return Response(
        {"key": build.pk, "platform": build.platform, "verified": build.verified}, status=201
    )


def render(proposal, user):
    author = proposal.owner_id == user.pk
    own_review = proposal.reviews.filter(owner=user).first()
    show_reviews = author or own_review is not None
    intact = knowledge.intact(proposal)
    return {
        "id": proposal.pk,
        "key": proposal.key,
        "kind": proposal.kind,
        "build_key": proposal.game_build_id,
        "dataset_kind": proposal.dataset_kind,
        "payload": proposal.payload,
        "provenance": {k: v for k, v in proposal.provenance.items() if k != "dependency_hashes"},
        "hash": proposal.content_hash,
        "state": proposal.state,
        "reason": proposal.reason,
        "author": author,
        "can_review": not author and own_review is None and proposal.state == "OPEN" and intact,
        "intact": intact,
        "effective": bool(
            proposal.published_id
            and knowledge.effective(proposal.published, proposal.dataset_kind, proposal.owner_id)
        ),
        "published_key": proposal.published_id,
        "reviews": [
            {"decision": r.decision, "note": r.note, "own": r.owner_id == user.pk}
            for r in proposal.reviews.all()
        ]
        if show_reviews
        else [],
        "review_visibility": "Sealed until you submit your independent decision"
        if not show_reviews
        else "Submitted review receipts",
        "sources": [
            {
                "asset_id": s.asset_id,
                **s.snapshot,
                "media_url": f"/api/knowledge/{proposal.pk}/media/{s.asset_id}",
            }
            for s in proposal.sources.all()
        ]
        if intact
        else [],
    }


@api_view(["GET", "POST"])
@private
@handled
@transaction.atomic
def proposals(request):
    current = knowledge.actor(request.user)
    if request.method == "POST":
        data = Proposal(data=request.data)
        data.is_valid(raise_exception=True)
        proposal = knowledge.propose(current, **data.validated_data)
        return Response(render(proposal, current), status=201)
    visible = (
        KnowledgeProposal.objects.filter(
            Q(owner=current) | Q(reviewer_one=current) | Q(reviewer_two=current)
        )
        .select_related("game_build", "published")
        .order_by("-created_at")[:100]
    )
    definitions = [
        d
        for d in DefinitionVersion.objects.all()
        if knowledge.effective(d, "synthetic", current.pk)
    ]
    return Response(
        {
            "real_publication_approved": knowledge.REAL_PUBLICATION_APPROVED,
            "proposals": [render(p, current) for p in visible],
            "builds": list(
                GameBuild.objects.filter(game_id="tekken8").values("key", "platform", "verified")
            ),
            "definitions": [
                {
                    "key": d.key,
                    "kind": d.kind,
                    "game_build": d.game_build_id,
                    "hash": d.content_hash,
                }
                for d in definitions
            ],
            "sources": list(
                ReplayAsset.objects.filter(owner=current, deleted_at=None).values(
                    "id", "source_sha256", "metadata", "retain_until"
                )[:100]
            ),
            "reanalyses": list(
                KnowledgeReanalysis.objects.filter(owner=current)
                .order_by("-created_at")
                .values("id", "match_id", "target_id", "run_id", "run__status")[:100]
            ),
            "limit": 100,
        }
    )


@api_view(["POST"])
@private
@handled
@transaction.atomic
def command(request, proposal_id, operation):
    if operation == "review":
        data = Review(data=request.data)
        data.is_valid(raise_exception=True)
        knowledge.review(request.user, proposal_id, **data.validated_data)
    elif operation == "publish":
        knowledge.publish(request.user, proposal_id)
    elif operation in {"retire", "withdraw"}:
        knowledge.lifecycle(request.user, proposal_id, operation.upper())
    else:
        raise PermissionDenied("Unknown knowledge operation")
    return Response(render(knowledge.accessible(request.user, proposal_id), request.user))


@api_view(["GET"])
@private
@handled
@transaction.atomic
def media(request, proposal_id, asset_id):
    proposal = knowledge.accessible(request.user, proposal_id)
    source = proposal.sources.select_related("asset").get(asset_id=asset_id)
    if not knowledge.intact(proposal):
        raise PermissionDenied("Review source is withdrawn or expired")
    from backend.core.private_media import asset_response

    def authorize():
        current = KnowledgeProposal.objects.get(pk=proposal_id)
        return (
            knowledge.live_user(request.user.pk)
            and knowledge.intact(current)
            and not current.state == "WITHDRAWN"
        )

    return asset_response(source.asset, request.headers.get("Range"), authorize=authorize)


@api_view(["GET", "POST"])
@private
@handled
def reanalysis(request):
    if request.method == "GET":
        return Response(
            knowledge.impact(
                request.user, knowledge.valid_key(request.query_params.get("mapping_key"))
            )
        )
    data = Reanalysis(data=request.data)
    data.is_valid(raise_exception=True)
    result = knowledge.reanalyse(request.user, **data.validated_data)
    return Response(
        {
            "id": result.pk,
            "run_id": result.run_id,
            "status": result.run.status,
            "review_required": True,
        },
        status=202,
    )
