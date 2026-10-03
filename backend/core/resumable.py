"""Owner-scoped upload lifecycle. Full integrity work runs outside HTTP."""

import base64
import hashlib
import os
import re
import time
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import Throttled

from analysis.contracts import digest
from analysis.process import execution_check
from backend.core.cloud import CloudFailure
from backend.core.consents import POLICY_VERSION, record_consent, require_processing
from backend.core.jobs import enqueue_run
from backend.core.match_ingestion import active_owner, register_upload_source
from backend.core.models import AnalysisRun, Match, ReplayAsset, UploadAdmission, UploadSession
from backend.core.ownership import lock_owner
from backend.core.recordings import (
    create_recording_source,
    require_local_operator,
    target_match,
    validate_claim,
)
from backend.core.security import admit_run, capacity_lock, check_capacity
from backend.core.storage import delete_asset, materialize, private_path, storage_for

PENDING = ("INITIALIZING", "UPLOADING", "VERIFYING", "PURGING")


def require_access(owner):
    require_local_operator(owner)
    if settings.RESTORE_QUARANTINE:
        raise CloudFailure("RESTORE_QUARANTINE", retryable=False)
    if settings.RESUMABLE_STORAGE_PROVIDER == "GCS" and not settings.GCS_STORAGE_QUALIFIED:
        raise CloudFailure("GCS_STORAGE_UNQUALIFIED", retryable=False)
    if settings.RESUMABLE_STORAGE_PROVIDER not in {"LOCAL", "GCS"}:
        raise CloudFailure("STORAGE_PROVIDER_UNCONFIGURED", retryable=False)
    require_processing(owner)


def owned_session(owner, session_id):
    return UploadSession.objects.select_related("asset", "match").get(
        pk=session_id, owner=owner, asset__owner=owner
    )


def usable(session, owner):
    require_access(owner)
    if (
        session.asset.owner_id != owner.pk
        or session.asset.deleted_at
        or session.state not in {"UPLOADING", "VERIFYING"}
        or session.expires_at <= timezone.now()
    ):
        raise ValidationError("Upload is cancelled, expired or unavailable")


def begin(owner, request_id, size, sha256, md5_hash, metadata, match_id=None, *, storage=None):
    require_access(owner)
    if (
        type(size) is not int
        or not 0 < size <= 536870912
        or not re.fullmatch(r"[a-f0-9]{64}", sha256)
        or len(base64.b64decode(md5_hash, validate=True)) != 16
    ):
        raise ValidationError("Invalid upload reservation or checksum")
    claim_hash = digest(
        {
            "size": size,
            "sha256": sha256,
            "md5": md5_hash,
            "metadata": metadata,
            "match_id": str(match_id) if match_id else None,
        }
    )
    with transaction.atomic():
        active_owner(owner)
        require_access(owner)
        prior = UploadSession.objects.filter(owner=owner, request_id=request_id).first()
        if prior:
            if prior.claim_digest != claim_hash:
                raise ValidationError("Upload request already belongs to different file or details")
            return prior
        match = target_match(owner, match_id) if match_id else None
        if match:
            validate_claim(match, metadata)
            if (
                match.asset_id
                or match.replay_sources.filter(asset__deleted_at=None, asset__isnull=False).exists()
            ):
                raise ValidationError("Remove the existing recording before attaching another")
        from backend.core.budgets import check_daily_capacity

        check_daily_capacity(owner)
        check_capacity(owner, size)
        admit_run(owner)
        capacity_lock()
        pending = UploadSession.objects.filter(state__in=PENDING)
        legacy = UploadAdmission.objects.filter(expires_at__gt=timezone.now())
        if (
            pending.filter(owner=owner).exists()
            or legacy.filter(owner=owner).exists()
            or pending.count() + legacy.count() >= settings.GLOBAL_UPLOAD_SLOTS
        ):
            raise Throttled(wait=60, detail="An upload or its cleanup is already in progress.")
        asset_id = uuid.uuid4()
        asset = ReplayAsset.objects.create(
            id=asset_id,
            owner=owner,
            storage_key=f"{owner.pk}/{asset_id}/source.mp4",
            storage_provider=settings.RESUMABLE_STORAGE_PROVIDER,
            bytes=size,
            metadata={**metadata, "attachment": bool(match)},
            retain_until=timezone.now() + timedelta(days=60),
            upload_expires_at=(timezone.now() + timedelta(days=7, minutes=10))
            if settings.RESUMABLE_STORAGE_PROVIDER == "GCS"
            else None,
        )
        session = UploadSession.objects.create(
            owner=owner,
            asset=asset,
            match=match,
            request_id=request_id,
            claim_digest=claim_hash,
            expected_sha256=sha256,
            expected_md5=md5_hash,
            expires_at=timezone.now() + timedelta(seconds=settings.UPLOAD_SESSION_SECONDS),
        )
        record_consent(owner, "PROCESSING", "GRANT", POLICY_VERSION, asset_id, "UPLOAD")
    # Persist the reservation BEFORE the remote RPC. An ambiguous begin is never reissued.
    try:
        if asset.storage_provider == "LOCAL":
            path = private_path(asset.storage_key)
            path.parent.mkdir(parents=True, exist_ok=False)
            with path.open("xb"):
                pass
            location = ""
        else:
            location = (storage or storage_for(asset)).begin_upload(
                asset.storage_key, size, md5_hash, session.pk
            )
        with transaction.atomic():
            lock_owner(owner.pk)
            current = UploadSession.objects.select_for_update().get(pk=session.pk)
            # Always retain a returned capability for cancellation, including a deletion race.
            ReplayAsset.objects.filter(pk=asset.pk).update(upload_session=location)
            current.asset.refresh_from_db()
            revoked = (
                current.state != "INITIALIZING"
                or current.asset.deleted_at
                or not owner_is_active(owner.pk)
            )
            if not revoked:
                current.state = "UPLOADING"
                current.save(update_fields=["state"])
        if revoked:
            raise ValidationError("Upload revoked during initialization")
        return current
    except Exception:
        mark_purging(owner, session.pk, "UPLOAD_INITIALIZATION_FAILED")
        try:
            delete_asset(owner, asset.pk, storage)
        except (OSError, ValueError, CloudFailure):
            pass  # Tombstone, bytes and slot remain for the cleanup worker.
        raise CloudFailure("UPLOAD_INITIALIZATION_FAILED") from None


def owner_is_active(owner_id):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.filter(pk=owner_id, is_active=True).exists()


@transaction.atomic
def mark_purging(owner, session_id, code="UPLOAD_CANCELLED", *, allow_complete=True):
    lock_owner(owner.pk)
    session = UploadSession.objects.select_for_update().get(pk=session_id, owner=owner)
    if session.state == "COMPLETE" and not allow_complete:
        raise ValidationError("Upload completed; use capture deletion to remove its evidence")
    session.state = "PURGING"
    session.fence += 1
    session.verification_lease = None
    session.next_attempt_at = None
    session.error_code = code
    session.save(
        update_fields=["state", "fence", "verification_lease", "next_attempt_at", "error_code"]
    )
    return session


def cancel(owner, session_id):
    session = owned_session(owner, session_id)
    if session.state == "COMPLETE":
        raise ValidationError("Upload completed; use capture deletion to remove its evidence")
    if session.state != "CANCELLED":
        mark_purging(owner, session_id, allow_complete=False)
        delete_asset(owner, session.asset_id)
    return owned_session(owner, session_id)


def status(owner, session_id):
    if not owner_is_active(owner.pk):
        raise ValidationError("Account is unavailable")
    session = owned_session(owner, session_id)
    if session.state == "UPLOADING":
        usable(session, owner)
        if session.asset.storage_provider == "LOCAL":
            received = private_path(session.asset.storage_key).stat().st_size
        else:
            received = storage_for(session.asset).upload_status(
                session.asset.upload_session, session.asset.bytes
            )
        if not 0 <= received <= session.asset.bytes:
            raise ValidationError("Upload size differs from reservation")
        with transaction.atomic():
            lock_owner(owner.pk)
            session = owned_session(owner, session_id)
            if not owner_is_active(owner.pk):
                raise ValidationError("Account is unavailable")
            if session.state == "UPLOADING":
                usable(session, owner)
                session.received_bytes = received
                session.save(update_fields=["received_bytes"])
            # A slow upstream probe cannot return a capability from before revocation.
    run = (
        AnalysisRun.objects.filter(asset=session.asset, owner=owner).first()
        if session.state == "COMPLETE"
        else None
    )
    return {
        "id": str(session.pk),
        "state": session.state,
        "received_bytes": session.received_bytes,
        "bytes": session.asset.bytes,
        "expires_at": session.expires_at,
        "storage_provider": session.asset.storage_provider,
        "error_code": session.error_code,
        "run_id": str(run.pk) if run else None,
        "asset_id": str(session.asset_id),
        "upload_url": session.asset.upload_session
        if session.state == "UPLOADING" and session.asset.storage_provider == "GCS"
        else None,
        "chunk_bytes": settings.UPLOAD_CHUNK_BYTES,
    }


@transaction.atomic
def write_chunk(owner, session_id, offset, data):
    lock_owner(owner.pk)
    session = (
        UploadSession.objects.select_for_update()
        .select_related("asset")
        .get(pk=session_id, owner=owner)
    )
    usable(session, owner)
    if session.state != "UPLOADING" or session.asset.storage_provider != "LOCAL":
        raise ValidationError("This upload does not accept local chunks")
    if not 0 < len(data) <= settings.UPLOAD_CHUNK_BYTES or offset + len(data) > session.asset.bytes:
        raise ValidationError("Chunk exceeds upload reservation")
    path = private_path(session.asset.storage_key)
    with path.open("r+b") as stream:
        stream.seek(0, os.SEEK_END)
        received = stream.tell()
        if offset < received:
            stream.seek(offset)
            if offset + len(data) > received or stream.read(len(data)) != data:
                raise ValidationError("Chunk conflicts with bytes already received")
        elif offset != received:
            raise ValidationError("Chunk offset differs; refresh upload progress")
        else:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            received += len(data)
    session.received_bytes = received
    session.save(update_fields=["received_bytes"])
    return received


def request_completion(owner, session_id):
    session = owned_session(owner, session_id)
    if session.state == "COMPLETE":
        return session
    usable(session, owner)
    if session.state == "VERIFYING":
        return session
    info = status(owner, session_id)
    if info["received_bytes"] != session.asset.bytes:
        raise ValidationError("Upload is incomplete; resume the remaining bytes")
    with transaction.atomic():
        lock_owner(owner.pk)
        session = (
            UploadSession.objects.select_for_update()
            .select_related("asset")
            .get(pk=session_id, owner=owner)
        )
        usable(session, owner)
        session.state = "VERIFYING"
        session.save(update_fields=["state"])
    return session


def verify(session_id, *, storage=None):
    """Claim a bounded verification lease, verify real bytes, then publish atomically."""
    snapshot = UploadSession.objects.select_related("asset", "owner").get(pk=session_id)
    with transaction.atomic():
        lock_owner(snapshot.owner_id)
        session = (
            UploadSession.objects.select_for_update()
            .select_related("asset", "owner")
            .get(pk=session_id)
        )
        if (
            session.state != "VERIFYING"
            or (session.verification_lease and session.verification_lease > timezone.now())
            or (session.next_attempt_at and session.next_attempt_at > timezone.now())
        ):
            return False
        usable(session, session.owner)
        if session.verification_attempts >= 3:
            mark_purging(session.owner, session.pk, "UPLOAD_RETRY_BUDGET_EXHAUSTED")
            return False
        session.fence += 1
        session.verification_attempts += 1
        session.verification_lease = timezone.now() + timedelta(
            seconds=settings.UPLOAD_VERIFICATION_SECONDS
        )
        session.save(update_fields=["fence", "verification_lease", "verification_attempts"])
        token = session.fence
    deadline = time.monotonic() + settings.UPLOAD_VERIFICATION_SECONDS
    last_check = 0.0

    def check():
        nonlocal last_check
        if time.monotonic() >= deadline:
            raise ValueError("UPLOAD_VERIFICATION_TIMEOUT")
        if time.monotonic() - last_check < 0.5:
            return
        last_check = time.monotonic()
        if (
            settings.RESTORE_QUARANTINE
            or not UploadSession.objects.filter(
                pk=session.pk,
                state="VERIFYING",
                fence=token,
                expires_at__gt=timezone.now(),
                asset__deleted_at=None,
                owner__is_active=True,
            ).exists()
        ):
            raise ValueError("UPLOAD_REVOKED")
        require_processing(session.owner)

    generation = ""
    guard = execution_check.set(check)
    try:
        check()
        if session.asset.storage_provider == "GCS":
            adapter = storage or storage_for(session.asset)
            info = adapter.inspect_object(session.asset.storage_key)
            if not isinstance(info, dict) or not isinstance(info.get("metadata"), dict):
                raise ValueError("UPLOAD_OBJECT_MISMATCH")
            if (
                info.get("name") != session.asset.storage_key
                or info.get("bucket") != settings.GCS_PRIVATE_BUCKET
                or str(info.get("size")) != str(session.asset.bytes)
                or info.get("contentType") != "video/mp4"
                or info.get("contentEncoding") not in {None, "identity"}
                or info.get("md5Hash") != session.expected_md5
                or info.get("metadata", {}).get("upload_session_id") != str(session.pk)
            ):
                raise ValueError("UPLOAD_OBJECT_MISMATCH")
            generation = str(info["generation"])
            session.asset.storage_generation = generation
        sha, md5, total = hashlib.sha256(), hashlib.md5(usedforsecurity=False), 0
        # materialize is generation-pinned and bounded. Hashing/remote reads never run in HTTP.
        with materialize(session.asset, storage=storage) as path, path.open("rb") as stream:
            while block := stream.read(65536):
                check()
                total += len(block)
                if total > session.asset.bytes:
                    raise ValueError("UPLOAD_SIZE_MISMATCH")
                sha.update(block)
                md5.update(block)
        if (
            total != session.asset.bytes
            or sha.hexdigest() != session.expected_sha256
            or base64.b64encode(md5.digest()).decode() != session.expected_md5
        ):
            raise ValueError("UPLOAD_CHECKSUM_MISMATCH")
        with transaction.atomic():
            active_owner(session.owner)
            current = (
                UploadSession.objects.select_for_update()
                .select_related("asset", "owner")
                .get(pk=session.pk)
            )
            usable(current, current.owner)
            if current.fence != token or current.verification_lease <= timezone.now():
                raise ValueError("UPLOAD_REVOKED")
            claim = dict(current.asset.metadata)
            claim.pop("attachment", None)
            match = target_match(current.owner, current.match_id) if current.match_id else None
            if match:
                validate_claim(match, claim)
                if (
                    match.asset_id
                    or match.replay_sources.filter(
                        asset__isnull=False, asset__deleted_at=None
                    ).exists()
                ):
                    raise ValidationError("Recording already attached")
            if (
                ReplayAsset.objects.filter(
                    owner=current.owner, source_sha256=sha.hexdigest(), deleted_at=None
                )
                .exclude(pk=current.asset_id)
                .exists()
            ):
                raise ValidationError("These recording bytes already exist in this workspace")
            admit_run(current.owner)
            current.asset.source_sha256 = sha.hexdigest()
            current.asset.storage_generation = generation
            current.asset.upload_session = ""
            current.asset.upload_expires_at = None
            current.asset.save(
                update_fields=[
                    "source_sha256",
                    "storage_generation",
                    "upload_session",
                    "upload_expires_at",
                ]
            )
            if match:
                create_recording_source(match, current.asset, claim)
            else:
                match = Match.objects.create(
                    owner=current.owner,
                    asset=current.asset,
                    game_build=claim["game_build"],
                    knowledge_revision="tekken8-3.02.01-pilot-draft/1",
                    session_id=claim["session_id"],
                    played_at=claim["played_at"],
                    mode=claim["source_kind"],
                    dataset_kind=claim["dataset_kind"],
                    context="jin/jin",
                )
                register_upload_source(match)
            enqueue_run(
                owner=current.owner, asset=current.asset, request_key=f"resumable:{current.pk}"
            )
            current.state = "COMPLETE"
            current.error_code = ""
            current.verification_lease = None
            current.save(update_fields=["state", "verification_lease", "error_code"])
        return True
    except (OSError, ValueError, ValidationError, CloudFailure, Throttled) as error:
        # Never expose transport text, paths or capability URLs.
        code = (
            "UPLOAD_VERIFY_UNAVAILABLE"
            if isinstance(error, (CloudFailure, OSError, Throttled))
            else "UPLOAD_VERIFY_REJECTED"
        )
        with transaction.atomic():
            lock_owner(session.owner_id)
            current = UploadSession.objects.select_for_update().get(pk=session.pk)
            if current.state != "VERIFYING" or current.fence != token:
                return False  # A stale verifier cannot erase or overwrite newer evidence.
            retry = (
                current.verification_attempts < 3
                and isinstance(error, (CloudFailure, OSError, Throttled))
                and (not isinstance(error, CloudFailure) or error.retryable)
            )
            if retry:
                current.verification_lease = None
                current.error_code = code
                current.next_attempt_at = timezone.now() + timedelta(
                    seconds=2**current.verification_attempts
                )
                current.save(update_fields=["verification_lease", "error_code", "next_attempt_at"])
            else:
                mark_purging(session.owner, session.pk, code)
        if not retry:
            try:
                delete_asset(session.owner, session.asset_id, storage)
            except (OSError, ValueError, CloudFailure):
                pass
        return False
    finally:
        execution_check.reset(guard)


def reconcile_uploads(limit=20):
    if settings.RESTORE_QUARANTINE:
        return 0
    count = 0
    sessions = (
        UploadSession.objects.select_related("owner", "asset")
        .filter(state__in=PENDING)
        .filter(Q(next_attempt_at=None) | Q(next_attempt_at__lte=timezone.now()))
        .filter(
            Q(state__in=["VERIFYING", "PURGING"])
            | Q(asset__deleted_at__isnull=False)
            | Q(expires_at__lte=timezone.now())
            | Q(owner__is_active=False)
        )
        .order_by("created_at")[:limit]
    )
    for session in sessions:
        try:
            if (
                session.asset.deleted_at
                or session.expires_at <= timezone.now()
                or not session.owner.is_active
            ):
                mark_purging(session.owner, session.pk, "UPLOAD_EXPIRED_OR_REVOKED")
                delete_asset(session.owner, session.asset_id)
            elif session.state == "PURGING":
                delete_asset(session.owner, session.asset_id)
            elif session.state == "VERIFYING":
                verify(session.pk)
            count += 1
        except (OSError, ValueError, ValidationError, CloudFailure):
            UploadSession.objects.filter(pk=session.pk, state__in=PENDING).update(
                next_attempt_at=timezone.now() + timedelta(seconds=60)
            )  # A failed purge cannot starve unrelated verification on every sweep.
    return count
