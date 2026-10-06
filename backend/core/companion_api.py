"""Session/CSRF owner controls and a separate upload-only device API."""

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    parser_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle

from backend.core import companion, resumable
from backend.core.api import handled
from backend.core.cloud import CloudFailure
from backend.core.consents import POLICIES, POLICY_VERSION
from backend.core.models import RecordingDevice, RecordingReceipt, ReplayAsset, UploadSession
from backend.core.recording_api import AttributionInput
from backend.core.security import consume_budget
from backend.core.upload_api import ChunkParser, unavailable


class PairInput(serializers.Serializer):
    label = serializers.RegexField(r"^[\w .-]{1,60}$")
    sync_consent = serializers.BooleanField()
    policy_version = serializers.CharField(max_length=60)


class CodeInput(serializers.Serializer):
    pairing_code = serializers.RegexField(r"^[A-Za-z0-9_-]{43}$")


class PairThrottle(BaseThrottle):
    def allow_request(self, request, view):
        self.delay = consume_budget("device-pair", request.META.get("REMOTE_ADDR", "unknown"), 10)
        return not self.delay

    def wait(self):
        return self.delay


@api_view(["GET", "POST"])
@handled
def devices(request):
    if request.method == "POST":
        data = PairInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(
            companion.create_pairing(
                request.user,
                data.validated_data["label"],
                data.validated_data["sync_consent"],
                data.validated_data["policy_version"],
            ),
            status=201,
        )
    return Response(
        {
            "enabled": bool(
                settings.LOCAL_RECORDING_COMPANION
                and settings.LOCAL_OPERATOR_UPLOADS
                and request.user.is_staff
            ),
            "policy_version": POLICY_VERSION,
            "policy": POLICIES["RECORDING_SYNC"],
            "devices": [
                {
                    "id": d.pk,
                    "label": d.label,
                    "expires_at": d.expires_at,
                    "revoked_at": d.revoked_at,
                    "last_seen_at": d.last_seen_at,
                }
                for d in RecordingDevice.objects.filter(owner=request.user).order_by("-created_at")[
                    :50
                ]
            ],
        }
    )


@api_view(["DELETE"])
@handled
def revoke(request, device_id):
    companion.revoke_device(request.user, device_id)
    return Response({"revoked": True, "original_local_files_deleted": False})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([PairThrottle])
@handled
def redeem(request):
    data = CodeInput(data=request.data)
    data.is_valid(raise_exception=True)
    return Response(companion.redeem_pairing(data.validated_data["pairing_code"]), status=201)


class DeviceUploadInput(serializers.Serializer):
    bytes = serializers.IntegerField(min_value=1, max_value=536870912)
    sha256 = serializers.RegexField(r"^[a-f0-9]{64}$")
    md5 = serializers.CharField(max_length=24)


def safe_status(owner, session_id):
    info = resumable.status(owner, session_id)
    info.pop("upload_url", None)  # Device cannot accept arbitrary cloud capabilities.
    return info


@api_view(["POST"])
@authentication_classes([companion.RecordingDeviceAuthentication])
@handled
@transaction.atomic
def device_uploads(request):
    owner, device = companion.require_device(request.auth)
    data = DeviceUploadInput(data=request.data)
    data.is_valid(raise_exception=True)
    values = data.validated_data
    key = companion.byte_key(owner, values["sha256"])
    receipt = (
        RecordingReceipt.objects.filter(owner=owner, key_digest=key)
        .select_related("session__asset")
        .first()
    )
    if receipt and receipt.session_id:
        if receipt.session.asset.deleted_at or receipt.session.state in {"PURGING", "CANCELLED"}:
            return Response({"state": "REMOVED"})
        if receipt.device_id != device.pk:
            return Response({"state": "DUPLICATE"})
        if (receipt.session.asset.bytes, receipt.session.expected_md5) != (
            values["bytes"],
            values["md5"],
        ):
            return Response({"error": "Conflicting recording bytes"}, status=409)
        return Response(safe_status(owner, receipt.session_id))
    if receipt and receipt.suppressed:
        return Response({"state": "DUPLICATE"})
    if not receipt:
        if RecordingReceipt.objects.filter(owner=owner).count() >= settings.COMPANION_MAX_RECEIPTS:
            return Response(
                {"error": "Recording receipt capacity reached"},
                status=429,
                headers={"Retry-After": "3600"},
            )
        # Also suppress a previously removed/manual-uploaded copy of these exact bytes.
        if (
            UploadSession.objects.filter(owner=owner, expected_sha256=values["sha256"]).exists()
            or ReplayAsset.objects.filter(owner=owner, source_sha256=values["sha256"]).exists()
        ):
            RecordingReceipt.objects.create(
                owner=owner, device=device, key_digest=key, suppressed=True
            )
            return Response({"state": "DUPLICATE"})
        receipt = RecordingReceipt.objects.create(owner=owner, device=device, key_digest=key)
    elif receipt.device_id != device.pk:
        return Response({"state": "DUPLICATE"})
    try:
        session = resumable.begin(
            owner,
            receipt.request_id,
            values["bytes"],
            values["sha256"],
            values["md5"],
            {"unattributed_recording": True, "capture_tool": "dojopulse-companion/1"},
        )
    except CloudFailure:
        return unavailable()
    receipt.session = session
    receipt.save(update_fields=["session"])
    RecordingDevice.objects.filter(pk=device.pk).update(last_seen_at=timezone.now())
    return Response(safe_status(owner, session.pk), status=201)


@api_view(["GET", "DELETE"])
@authentication_classes([companion.RecordingDeviceAuthentication])
@handled
@transaction.atomic
def device_session(request, session_id):
    owner, device = companion.require_device(request.auth)
    companion.receipt_session(owner, device, session_id)
    try:
        if request.method == "DELETE":
            resumable.cancel(owner, session_id)
        return Response(safe_status(owner, session_id))
    except CloudFailure:
        return unavailable()


@api_view(["PUT"])
@authentication_classes([companion.RecordingDeviceAuthentication])
@parser_classes([ChunkParser])
@handled
@transaction.atomic
def device_chunk(request, session_id):
    owner, device = companion.require_device(request.auth)
    companion.receipt_session(owner, device, session_id)
    offset = request.headers.get("Upload-Offset", "")
    if not offset.isascii() or not offset.isdigit() or len(offset) > 12:
        return Response({"error": "Invalid chunk offset"}, status=400)
    return Response(
        {"received_bytes": resumable.write_chunk(owner, session_id, int(offset), request.data)}
    )


@api_view(["POST"])
@authentication_classes([companion.RecordingDeviceAuthentication])
@handled
@transaction.atomic
def device_complete(request, session_id):
    owner, device = companion.require_device(request.auth)
    companion.receipt_session(owner, device, session_id)
    resumable.request_completion(owner, session_id)
    return Response(safe_status(owner, session_id), status=202)


@api_view(["GET"])
@handled
def recordings(request):
    rows = (
        RecordingReceipt.objects.filter(owner=request.user, session__isnull=False)
        .select_related("session__asset")
        .order_by("-created_at")[:50]
    )
    return Response(
        {"recordings": [companion.recording_view(row.session) for row in rows], "limit": 50}
    )


class AttachInput(serializers.Serializer):
    match_id = serializers.UUIDField()
    metadata = AttributionInput()


@api_view(["POST"])
@handled
def attach(request, session_id):
    data = AttachInput(data=request.data)
    data.is_valid(raise_exception=True)
    claim = data.validated_data["metadata"]
    if not claim.pop("attribution_confirmed"):
        return Response({"error": "Confirm recording attribution"}, status=400)
    claim["played_at"] = claim["played_at"].isoformat()
    source = companion.attach_synced(
        request.user, session_id, data.validated_data["match_id"], claim
    )
    return Response(
        {
            "source_id": source.pk,
            "match_id": source.match_id,
            "attribution_state": source.attribution_state,
        },
        status=202,
    )
