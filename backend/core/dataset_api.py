"""Owned local dataset workspace; reviewer access continues through /pilots."""

from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from backend.core import datasets, knowledge
from backend.core.api import handled
from backend.core.match_api import private
from backend.core.models import DatasetCollection, DatasetSnapshot, KnowledgeProposal, PilotCapture


class Create(serializers.Serializer):
    title = serializers.RegexField(r"^[A-Za-z0-9 _.-]{1,80}$")
    dataset_kind = serializers.ChoiceField(choices=["synthetic", "real"])
    knowledge_key = serializers.RegexField(r"^[A-Za-z0-9_.:/-]{1,160}$")
    request_id = serializers.UUIDField()


class Study(serializers.Serializer):
    title = serializers.RegexField(r"^[A-Za-z0-9 _.-]{1,80}$")
    request_id = serializers.UUIDField()


class Seal(serializers.Serializer):
    request_id = serializers.UUIDField()


def checked(serializer, value):
    data = serializer(data=value)
    data.is_valid(raise_exception=True)
    return data.validated_data


def brief(row):
    return {
        "id": str(row.pk),
        "title": row.title,
        "dataset_kind": row.dataset_kind,
        "state": row.state,
        "measurement": row.measurement,
        "sampling": row.sampling,
    }


@api_view(["GET", "POST"])
@private
@handled
@transaction.atomic
def collections(request):
    owner = knowledge.actor(request.user)
    if request.method == "POST":
        return Response(brief(datasets.create(owner, **checked(Create, request.data))), status=201)
    proposals = KnowledgeProposal.objects.filter(
        owner=owner, kind="knowledge", state="PUBLISHED", published__isnull=False
    ).select_related("published", "game_build")[:100]
    releases = [
        {
            "key": p.published_id,
            "game_build": p.payload["game_build"],
            "platform": p.game_build.platform,
            "dataset_kind": p.dataset_kind,
        }
        for p in proposals
        if knowledge.effective(p.published, p.dataset_kind, owner.pk)
    ]
    rows = DatasetCollection.objects.filter(owner=owner, deleted_at=None).order_by("-created_at")[
        :20
    ]
    return Response(
        {
            "datasets": [brief(row) for row in rows],
            "releases": releases,
            "real_intake_enabled": False,
            "automatic_publication": False,
        }
    )


@api_view(["GET", "DELETE"])
@private
@handled
@transaction.atomic
def detail(request, dataset_id):
    if request.method == "DELETE":
        datasets.close(request.user, dataset_id)
        return Response({"closed": True})
    owner, row = datasets.collection_for(request.user, dataset_id, require_live=False)
    data = brief(row)
    data["measurement_available"] = datasets.live_measurement(row, historical=row.state == "FROZEN")
    if not data["measurement_available"]:
        datasets.invalidate(row.pk, "MEASUREMENT_UNAVAILABLE")
    data["studies"] = [
        {
            "id": str(link.study_id),
            "title": link.study.title,
            "state": link.study.state,
            "revision": link.study.revision,
        }
        for link in row.studies.select_related("study").order_by("study_id")
    ]
    data["source_count"] = PilotCapture.objects.filter(
        session__enrollment__study__datasetstudy__dataset=row, withdrawn_at=None
    ).count()
    data["snapshots"] = []
    for snapshot in row.snapshots.order_by("-sequence")[:100]:
        valid = not snapshot.invalidated_at
        if valid:
            try:
                # A savepoint lets private-data erasure commit even when validation fails.
                with transaction.atomic():
                    datasets.current_snapshot(owner, row, snapshot)
            except (ValidationError, ValueError):
                datasets.invalidate(row.pk, "STALE_PERMISSION_OR_INPUT")
                valid = False
        data["snapshots"].append(
            {
                "id": str(snapshot.pk),
                "sequence": snapshot.sequence,
                "content_hash": snapshot.content_hash,
                "valid": valid,
                "reason": snapshot.reason
                if valid or snapshot.invalidated_at
                else "STALE_PERMISSION_OR_INPUT",
                "qa": snapshot.data.get("qa") if valid else None,
            }
        )
    return Response(data)


@api_view(["POST"])
@private
@handled
def command(request, dataset_id, operation):
    if operation == "study":
        row = datasets.new_study(request.user, dataset_id, **checked(Study, request.data))
        return Response({"study_id": str(row.pk)}, status=201)
    if operation == "freeze":
        datasets.freeze(request.user, dataset_id)
        return Response({"frozen": True})
    if operation == "seal":
        row = datasets.seal(request.user, dataset_id, **checked(Seal, request.data))
        return Response({"id": str(row.pk), "content_hash": row.content_hash}, status=201)
    return Response({"error": "Unknown dataset operation"}, status=404)


@api_view(["GET"])
@private
@handled
@transaction.atomic
def download(request, dataset_id, snapshot_id):
    owner, dataset = datasets.collection_for(request.user, dataset_id, require_live=False)
    if not datasets.live_measurement(dataset, historical=dataset.state == "FROZEN"):
        datasets.invalidate(dataset.pk, "MEASUREMENT_UNAVAILABLE")
        return Response({"error": "Pinned dataset measurement is unavailable"}, status=410)
    row = DatasetSnapshot.objects.get(pk=snapshot_id, dataset=dataset)
    try:
        with transaction.atomic():
            bundle = datasets.current_snapshot(owner, dataset, row)
    except (ValidationError, ValueError) as error:
        datasets.invalidate(dataset.pk, "STALE_PERMISSION_OR_INPUT")
        return Response({"error": str(error)}, status=410)
    return Response(bundle)
