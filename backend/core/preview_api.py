"""Owned playback/quality only. No endpoint grants gameplay or source attribution."""

from django.db import transaction
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from backend.core.api import handled
from backend.core.cloud import CloudFailure
from backend.core.jobs import cancel_run, locked_run
from backend.core.models import RecordingPreview, ReplayAsset
from backend.core.ownership import lock_owner
from backend.core.previews import (
    enqueue_preview,
    preview_view,
    purge_preview,
    quality_windows,
    revoke,
)


class RequestInput(serializers.Serializer):
    request_id = serializers.UUIDField()


def owned(request, asset_id):
    return ReplayAsset.objects.select_related("owner").get(
        pk=asset_id, owner=request.user, deleted_at=None
    )


@api_view(["GET"])
@handled
def recordings(request):
    assets = (
        ReplayAsset.objects.filter(owner=request.user, deleted_at=None)
        .select_related("owner")
        .order_by("-created_at")[:50]
    )
    return Response(
        {
            "recordings": [
                {
                    "asset_id": str(asset.pk),
                    "uploaded_at": asset.created_at,
                    "bytes": asset.bytes,
                    "preview": preview_view(asset),
                }
                for asset in assets
            ],
            "limit": 50,
        }
    )


@api_view(["GET", "POST", "DELETE"])
@handled
def detail(request, asset_id):
    asset = owned(request, asset_id)
    if request.method == "POST":
        data = RequestInput(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            enqueue_preview(request.user, asset.pk, data.validated_data["request_id"])
        except CloudFailure:
            return Response(
                {"error": "Preview hosting awaits storage/runtime qualification"}, status=503
            )
    elif request.method == "DELETE":
        with transaction.atomic():
            lock_owner(request.user.pk)
            preview = RecordingPreview.objects.get(asset=asset)
            if preview.run_id:
                run = locked_run(preview.run_id)
                if run.status in {"QUEUED", "PROCESSING"}:
                    cancel_run(request.user, run.pk)
                else:
                    run.status, run.result, run.lease_until = "CANCELLED", {}, None
                    run.fence += 1
                    run.save()
            revoke(RecordingPreview.objects.filter(pk=preview.pk))
        try:
            purge_preview(preview.pk)
        except (OSError, CloudFailure):
            return Response({"error": "Playback revoked; storage cleanup pending"}, status=503)
    return Response(preview_view(asset), status=202 if request.method == "POST" else 200)


@api_view(["GET"])
@handled
def media(request, asset_id):
    asset = owned(request, asset_id)
    state = preview_view(asset)
    if not state.get("media_url"):
        return Response({"error": "Preview unavailable"}, status=404)
    preview = RecordingPreview.objects.get(asset=asset)
    item = preview.manifest["preview.mp4"]
    run_id, fence = preview.run_id, preview.attempt_fence

    def grant():
        return RecordingPreview.objects.filter(
            pk=preview.pk, state="READY", run_id=run_id, attempt_fence=fence
        ).exists() and bool(
            preview_view(ReplayAsset.objects.select_related("owner").get(pk=asset.pk)).get(
                "media_url"
            )
        )

    from backend.core.private_media import asset_response

    try:
        return asset_response(asset, request.headers.get("Range"), artifact=item, authorize=grant)
    except CloudFailure:
        return Response({"error": "Private preview storage unavailable"}, status=503)


@api_view(["GET"])
@handled
def windows(request, asset_id):
    asset = owned(request, asset_id)
    if not preview_view(asset).get("media_url"):
        return Response({"error": "Preview unavailable"}, status=404)
    query = serializers.IntegerField(min_value=0, max_value=36000)
    offset = query.run_validation(request.query_params.get("offset", 0))
    try:
        result = quality_windows(asset, offset)
    except CloudFailure:
        return Response({"error": "Private timing details unavailable"}, status=503)
    if not preview_view(asset).get("media_url"):
        return Response({"error": "Preview unavailable"}, status=404)
    return Response(result)
