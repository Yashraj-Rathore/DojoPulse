"""Scoped local recording devices. No game credentials, identity resolver or provider RPC."""

import hashlib
import hmac
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed, Throttled

from backend.core.consents import record_consent, require_processing
from backend.core.models import (
    AnalysisRun,
    ConsentReceipt,
    DevicePairing,
    RecordingDevice,
    RecordingReceipt,
    ReplayAsset,
    UploadSession,
)
from backend.core.ownership import lock_owner
from backend.core.recordings import require_local_operator


def require_enabled(owner):
    require_local_operator(owner)
    require_processing(owner)
    if (
        not settings.LOCAL_RECORDING_COMPANION
        or settings.RESTORE_QUARANTINE
        or settings.RESUMABLE_STORAGE_PROVIDER != "LOCAL"
    ):
        raise PermissionDenied("Recording companion awaits local or hosted qualification")


def token_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def byte_key(owner, sha):
    return hmac.new(
        settings.DATA_SUPPRESSION_KEY.encode(),
        f"companion:{owner.pk}:{sha}".encode(),
        hashlib.sha256,
    ).hexdigest()


def sync_granted(owner):
    receipt = (
        ConsentReceipt.objects.filter(owner=owner, scope="RECORDING_SYNC")
        .order_by("-created_at", "-id")
        .first()
    )
    return receipt is not None and receipt.action == "GRANT"


def require_device(device):
    owner = lock_owner(device.owner_id)
    current = RecordingDevice.objects.get(pk=device.pk, owner=owner)
    if current.revoked_at or current.expires_at <= timezone.now() or not sync_granted(owner):
        raise AuthenticationFailed("Device access expired or was revoked; pair again")
    try:
        require_enabled(owner)
    except ValidationError:
        raise AuthenticationFailed("Device processing permission is unavailable") from None
    return owner, current


class RecordingDeviceAuthentication(BaseAuthentication):
    def authenticate(self, request):
        from backend.core.security import consume_budget

        delay = consume_budget(
            "device-auth", request.META.get("REMOTE_ADDR", "unknown"), settings.API_READ_RATE
        )
        if delay:
            raise Throttled(wait=delay, detail="Too many device requests; retry later")
        raw = get_authorization_header(request).split()
        if len(raw) != 2 or raw[0] != b"RecordingDevice" or len(raw[1]) != 43:
            raise AuthenticationFailed("Recording device credential required")
        try:
            token = raw[1].decode("ascii")
        except UnicodeDecodeError:
            raise AuthenticationFailed("Invalid recording device credential") from None
        device = (
            RecordingDevice.objects.select_related("owner")
            .filter(token_digest=token_hash(token))
            .first()
        )
        if device is None:
            raise AuthenticationFailed("Invalid recording device credential")
        with transaction.atomic():
            owner, device = require_device(device)
        return owner, device

    def authenticate_header(self, request):
        return "RecordingDevice"


@transaction.atomic
def create_pairing(owner, label, consent, version):
    owner = lock_owner(owner.pk)
    require_enabled(owner)
    if not consent:
        raise ValidationError("Explicit recording sync consent required")
    now = timezone.now()
    DevicePairing.objects.filter(owner=owner, expires_at__lte=now).delete()
    if (
        RecordingDevice.objects.filter(owner=owner, revoked_at=None, expires_at__gt=now).count()
        >= settings.COMPANION_MAX_DEVICES
    ):
        raise Throttled(wait=60, detail="Revoke an existing device before pairing another")
    # Issuing another challenge invalidates the previous unredeemed code.
    DevicePairing.objects.filter(owner=owner, consumed_at=None).update(consumed_at=now)
    record_consent(owner, "RECORDING_SYNC", "GRANT", version, uuid.uuid4(), "PAIRING")
    token = secrets.token_urlsafe(32)
    pairing = DevicePairing.objects.create(
        owner=owner,
        label=label,
        token_digest=token_hash(token),
        expires_at=now + timedelta(seconds=settings.COMPANION_PAIR_SECONDS),
    )
    return {"pairing_code": token, "expires_at": pairing.expires_at}


@transaction.atomic
def redeem_pairing(code):
    pairing = DevicePairing.objects.filter(token_digest=token_hash(code)).first()
    if pairing is None:
        raise ValidationError("Pairing code is invalid, expired or already used")
    owner = lock_owner(pairing.owner_id)
    require_enabled(owner)
    pairing.refresh_from_db()
    now = timezone.now()
    if pairing.consumed_at or pairing.expires_at <= now or not sync_granted(owner):
        raise ValidationError("Pairing code is invalid, expired or already used")
    if (
        RecordingDevice.objects.filter(owner=owner, revoked_at=None, expires_at__gt=now).count()
        >= settings.COMPANION_MAX_DEVICES
    ):
        raise Throttled(wait=60, detail="Device capacity reached")
    token = secrets.token_urlsafe(32)
    device = RecordingDevice.objects.create(
        owner=owner,
        label=pairing.label,
        token_digest=token_hash(token),
        expires_at=now + timedelta(seconds=settings.COMPANION_DEVICE_SECONDS),
    )
    pairing.consumed_at = now
    pairing.save(update_fields=["consumed_at"])
    return {
        "device_id": str(device.pk),
        "owner_id": str(owner.pk),
        "credential": token,
        "expires_at": device.expires_at,
        "scope": "recording-sync/1",
    }


def fence_devices(owner, devices):
    now = timezone.now()
    ids = list(devices.values_list("pk", flat=True))
    devices.update(revoked_at=now)
    pending = UploadSession.objects.filter(
        recordingreceipt__device_id__in=ids,
        owner=owner,
        state__in=["INITIALIZING", "UPLOADING", "VERIFYING", "PURGING"],
    )
    ReplayAsset.objects.filter(uploadsession__in=pending).update(deleted_at=now, metadata={})
    pending.update(
        state="PURGING", fence=F("fence") + 1, verification_lease=None, error_code="DEVICE_REVOKED"
    )


def revoke_all(owner):
    # Called under the owner lock by consent withdrawal/account deletion.
    DevicePairing.objects.filter(owner=owner, consumed_at=None).update(consumed_at=timezone.now())
    fence_devices(owner, RecordingDevice.objects.filter(owner=owner, revoked_at=None))


@transaction.atomic
def revoke_device(owner, device_id):
    lock_owner(owner.pk)
    device = RecordingDevice.objects.get(pk=device_id, owner=owner)
    fence_devices(owner, RecordingDevice.objects.filter(pk=device.pk, owner=owner))


def receipt_session(owner, device, session_id):
    return (
        RecordingReceipt.objects.select_related("session__asset")
        .get(owner=owner, device=device, session_id=session_id, session__owner=owner)
        .session
    )


def recording_view(session):
    asset = session.asset
    run = (
        AnalysisRun.objects.filter(owner=session.owner, asset=asset).order_by("-created_at").first()
    )
    source = asset.replaysource_set.filter(
        match__owner=session.owner, match__deleted_at=None
    ).first()
    if asset.deleted_at or session.state in {"CANCELLED", "PURGING"}:
        availability = "REMOVED"
    elif asset.retain_until and asset.retain_until <= timezone.now():
        availability = "EXPIRED"
    elif session.state != "COMPLETE" or not run or run.status in {"QUEUED", "PROCESSING"}:
        availability = "PENDING"
    elif (
        run.status not in {"REVIEW_REQUIRED", "PARTIAL", "COMPLETED"}
        or run.result.get("source", {}).get("source_sha256") != asset.source_sha256
    ):
        availability = "INCOMPATIBLE" if run.status == "FAILED" else "ERROR"
    else:
        availability = "AVAILABLE"
    return {
        "id": str(session.pk),
        "asset_id": str(asset.pk),
        "availability": availability,
        "uploaded_at": asset.created_at,
        "bytes": asset.bytes,
        "access_class": "USER_UPLOAD",
        "capture_tool": "dojopulse-companion/1",
        "match_id": str(source.match_id) if source else None,
        "attribution_state": source.attribution_state if source else "UNASSIGNED",
        "media_url": f"/api/assets/{asset.pk}/media" if availability == "AVAILABLE" else None,
    }


@transaction.atomic
def attach_synced(owner, session_id, match_id, claim):
    from backend.core.recordings import create_recording_source, target_match, validate_claim

    owner = lock_owner(owner.pk)
    require_local_operator(owner)
    require_processing(owner)
    receipt = RecordingReceipt.objects.select_related("session__asset").get(
        owner=owner, session_id=session_id
    )
    session = receipt.session
    if recording_view(session)["availability"] != "AVAILABLE":
        raise ValidationError("Successful media validation required before attribution")
    match = target_match(owner, match_id)
    validate_claim(match, claim)
    existing = session.asset.replaysource_set.first()
    if existing:
        if existing.match_id == match.pk and existing.attribution.get("claim") == claim:
            return existing
        raise ValidationError(
            "Recording is already assigned; remove it before changing attribution"
        )
    if (
        match.asset_id
        or match.replay_sources.filter(asset__isnull=False, asset__deleted_at=None).exists()
    ):
        raise ValidationError("Remove the existing recording before attaching another")
    session.asset.metadata = {**claim, "attachment": True, "capture_tool": "dojopulse-companion/1"}
    session.asset.save(update_fields=["metadata"])
    # This is a claim on the imported UUID; operator visual approval remains separate.
    return create_recording_source(match, session.asset, claim)
