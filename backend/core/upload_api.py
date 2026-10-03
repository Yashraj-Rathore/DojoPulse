"""Small authenticated upload control requests and bounded local chunk transfer."""

import base64

from rest_framework import serializers
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import BaseParser
from rest_framework.response import Response

from backend.core.api import handled
from backend.core.cloud import CloudFailure
from backend.core.recording_api import AttributionInput
from backend.core.resumable import begin, cancel, request_completion, status, write_chunk


class CaptureInput(serializers.Serializer):
    game_build = serializers.CharField(max_length=80)
    session_id = serializers.CharField(max_length=100)
    played_at = serializers.DateTimeField()
    source_kind = serializers.ChoiceField(choices=["ranked", "practice", "takeover"])
    dataset_kind = serializers.ChoiceField(choices=["real", "synthetic"])
    characters = serializers.ListField(
        child=serializers.ChoiceField(choices=["jin"]), min_length=2, max_length=2
    )


class SessionInput(serializers.Serializer):
    request_id = serializers.UUIDField()
    filename = serializers.CharField(max_length=200)
    bytes = serializers.IntegerField(min_value=1, max_value=536870912)
    sha256 = serializers.RegexField(r"^[a-f0-9]{64}$")
    md5 = serializers.CharField(max_length=24)
    processing_consent = serializers.BooleanField()
    single_continuous = serializers.BooleanField()
    metadata = serializers.DictField()
    match_id = serializers.UUIDField(required=False)

    def validate(self, values):
        if (
            not values["filename"].lower().endswith(".mp4")
            or not values["processing_consent"]
            or not values["single_continuous"]
        ):
            raise serializers.ValidationError(
                "Confirm processing consent and one continuous MP4 capture"
            )
        try:
            if len(base64.b64decode(values["md5"], validate=True)) != 16:
                raise ValueError
        except ValueError:
            raise serializers.ValidationError("Invalid file integrity checksum") from None
        claim = (AttributionInput if values.get("match_id") else CaptureInput)(
            data=values["metadata"]
        )
        claim.is_valid(raise_exception=True)
        metadata = claim.validated_data
        if values.get("match_id") and not metadata.pop("attribution_confirmed"):
            raise serializers.ValidationError("Confirm the recording attribution details")
        metadata["played_at"] = metadata["played_at"].isoformat()
        values["metadata"] = metadata
        return values


def unavailable():
    return Response(
        {"error": "Upload storage is temporarily unavailable or awaits qualification"}, status=503
    )


@api_view(["POST"])
@handled
def sessions(request):
    data = SessionInput(data=request.data)
    data.is_valid(raise_exception=True)
    values = data.validated_data
    try:
        session = begin(
            request.user,
            values["request_id"],
            values["bytes"],
            values["sha256"],
            values["md5"],
            values["metadata"],
            values.get("match_id"),
        )
        return Response(status(request.user, session.pk), status=201)
    except CloudFailure:
        return unavailable()


@api_view(["GET", "DELETE"])
@handled
def session_detail(request, session_id):
    try:
        if request.method == "DELETE":
            cancel(request.user, session_id)
        return Response(status(request.user, session_id))
    except CloudFailure:
        return unavailable()


class ChunkParser(BaseParser):
    media_type = "application/octet-stream"

    def parse(self, stream, media_type=None, parser_context=None):
        from django.conf import settings
        from rest_framework.exceptions import ParseError

        request = parser_context["request"]
        try:
            length = int(request.headers.get("Content-Length", "0"))
        except ValueError:
            raise ParseError("Invalid chunk length") from None
        if not 0 < length <= settings.UPLOAD_CHUNK_BYTES:
            raise ParseError("Chunk exceeds transfer limit")
        data = stream.read(settings.UPLOAD_CHUNK_BYTES + 1)
        if len(data) != length:
            raise ParseError("Chunk length differs from declared size")
        return data


@api_view(["PUT"])
@parser_classes([ChunkParser])
@handled
def chunk(request, session_id):
    try:
        raw_offset = request.headers.get("Upload-Offset", "")
        if not raw_offset.isascii() or not raw_offset.isdigit() or len(raw_offset) > 12:
            raise ValueError("Invalid chunk offset")
        received = write_chunk(request.user, session_id, int(raw_offset), request.data)
        return Response({"received_bytes": received})
    except CloudFailure:
        return unavailable()


@api_view(["POST"])
@handled
def complete(request, session_id):
    try:
        request_completion(request.user, session_id)
        return Response(status(request.user, session_id), status=202)
    except CloudFailure:
        return unavailable()
