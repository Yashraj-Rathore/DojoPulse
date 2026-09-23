import json

from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from backend.core.api import handled
from backend.core.recordings import attach_recording, reprocess_recording


class AttributionInput(serializers.Serializer):
    metadata_revision = serializers.IntegerField(min_value=1)
    player_namespace = serializers.CharField(max_length=100, trim_whitespace=False)
    player_id = serializers.CharField(max_length=200, trim_whitespace=False)
    player_slot = serializers.ChoiceField(choices=[1, 2])
    opponent_namespace = serializers.CharField(max_length=100, trim_whitespace=False)
    opponent_id = serializers.CharField(max_length=200, trim_whitespace=False)
    game_build = serializers.CharField(max_length=80)
    session_id = serializers.CharField(max_length=100)
    played_at = serializers.DateTimeField()
    source_kind = serializers.ChoiceField(choices=["ranked", "practice", "takeover"])
    dataset_kind = serializers.ChoiceField(choices=["real", "synthetic"])
    characters = serializers.ListField(
        child=serializers.ChoiceField(choices=["jin"]), min_length=2, max_length=2
    )
    attribution_confirmed = serializers.BooleanField()


class RequestInput(serializers.Serializer):
    request_id = serializers.UUIDField()


@api_view(["POST"])
@handled
def upload_recording(request, match_id):
    if request.data.get("processing_consent") != "true":
        return Response({"error": "Explicit processing consent required"}, status=400)
    token = RequestInput(data=request.data)
    token.is_valid(raise_exception=True)
    data = AttributionInput(data=json.loads(request.data.get("metadata", "{}")))
    data.is_valid(raise_exception=True)
    claim = data.validated_data
    if not claim.pop("attribution_confirmed"):
        return Response({"error": "Confirm the recording attribution details"}, status=400)
    claim["played_at"] = claim["played_at"].isoformat()
    source, run = attach_recording(
        request.user, match_id, request.FILES.get("file"), claim, token.validated_data["request_id"]
    )
    response = Response(
        {
            "match_id": match_id,
            "source_id": source.pk,
            "asset_id": source.asset_id,
            "run_id": run.pk,
            "status": run.status,
            "attribution_state": source.attribution_state,
        },
        status=202,
    )
    response["Cache-Control"] = "private, no-store"
    return response


@api_view(["POST"])
@handled
def reprocess(request, match_id, source_id):
    data = RequestInput(data=request.data)
    data.is_valid(raise_exception=True)
    run = reprocess_recording(request.user, match_id, source_id, data.validated_data["request_id"])
    return Response({"run_id": run.pk, "status": run.status}, status=202)
