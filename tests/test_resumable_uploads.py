import base64
import hashlib
import json
from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient

from backend.core.cloud import CloudFailure, GooglePrivateStorage
from backend.core.consents import POLICY_VERSION, record_consent
from backend.core.models import (
    AnalysisRun,
    GameplayEvent,
    Match,
    ReplayAsset,
    ReplaySource,
    UploadSession,
)
from backend.core.resumable import (
    begin,
    cancel,
    reconcile_uploads,
    request_completion,
    verify,
    write_chunk,
)
from backend.core.storage import delete_account, delete_asset, private_path

pytestmark = pytest.mark.django_db
CONTENTS = b"synthetic bounded video fixture"
CLAIM = {
    "game_build": "fixture",
    "session_id": "session-a",
    "played_at": "2026-10-03T12:00:00Z",
    "source_kind": "ranked",
    "dataset_kind": "synthetic",
    "characters": ["jin", "jin"],
}


def checks(data=CONTENTS):
    return hashlib.sha256(data).hexdigest(), base64.b64encode(
        hashlib.md5(data, usedforsecurity=False).digest()
    ).decode()


@pytest.fixture
def workspace(django_user_model, settings, tmp_path):
    settings.LOCAL_OPERATOR_UPLOADS = True
    settings.PRIVATE_DATA_ROOT = tmp_path / "private"
    owner = django_user_model.objects.create_user("upload-operator", is_staff=True)
    client = APIClient()
    client.force_authenticate(owner)
    return owner, client


def start(owner, **kwargs):
    return begin(
        owner, kwargs.pop("request_id", uuid4()), len(CONTENTS), *checks(), dict(CLAIM), **kwargs
    )


def payload(**changes):
    sha, md5 = checks()
    return {
        "request_id": str(uuid4()),
        "filename": "capture.mp4",
        "bytes": len(CONTENTS),
        "sha256": sha,
        "md5": md5,
        "metadata": CLAIM,
        "processing_consent": True,
        "single_continuous": True,
        **changes,
    }


def uploaded(owner):
    session = start(owner)
    write_chunk(owner, session.pk, 0, CONTENTS)
    request_completion(owner, session.pk)
    return session


def test_api_resume_verified_completion_and_private_range(workspace):
    owner, client = workspace
    body = payload()
    response = client.post("/api/upload-sessions", body, format="json")
    assert response.status_code == 201
    session_id = response.json()["id"]
    path = f"/api/upload-sessions/{session_id}"
    assert client.post("/api/upload-sessions", body, format="json").json()["id"] == session_id
    assert client.get(f"/api/assets/{response.json()['asset_id']}/media").status_code == 404
    for offset, part in [(0, CONTENTS[:10]), (0, CONTENTS[:10]), (10, CONTENTS[10:])]:
        assert (
            client.put(
                path + "/chunk",
                part,
                content_type="application/octet-stream",
                HTTP_UPLOAD_OFFSET=str(offset),
            ).status_code
            == 200
        )
    assert client.get(path).json()["received_bytes"] == len(CONTENTS)
    assert client.post(path + "/complete", {}, format="json").json()["state"] == "VERIFYING"
    assert not AnalysisRun.objects.exists() and not GameplayEvent.objects.exists()
    assert verify(session_id)
    assert not verify(session_id)
    result = client.get(path).json()
    assert result["state"] == "COMPLETE" and result["run_id"]
    assert AnalysisRun.objects.count() == Match.objects.count() == ReplaySource.objects.count() == 1
    assert not GameplayEvent.objects.exists()
    asset = ReplayAsset.objects.get(pk=result["asset_id"])
    assert asset.source_sha256 == checks()[0]
    media = client.get(f"/api/assets/{asset.pk}/media", HTTP_RANGE="bytes=3-8")
    assert media.status_code == 206 and b"".join(media.streaming_content) == CONTENTS[3:9]
    assert media["Content-Range"] == f"bytes 3-8/{len(CONTENTS)}"
    assert client.delete(path).status_code == 400
    assert client.post(path + "/complete", {}, format="json").status_code == 202


@pytest.mark.parametrize(
    "changes",
    [
        {"processing_consent": False},
        {"single_continuous": False},
        {"bytes": 536870913},
        {"md5": "not-checksum"},
        {"filename": "capture.exe"},
        {"sha256": "X" * 64},
    ],
)
def test_invalid_admission_creates_no_storage_or_rows(workspace, changes):
    _, client = workspace
    assert client.post("/api/upload-sessions", payload(**changes), format="json").status_code == 400
    assert not ReplayAsset.objects.exists()


def test_conflicts_incomplete_chunks_and_storage_quota(workspace, settings):
    owner, client = workspace
    body = payload()
    first = client.post("/api/upload-sessions", body, format="json")
    assert (
        client.post("/api/upload-sessions", {**body, "sha256": "a" * 64}, format="json").status_code
        == 400
    )
    path = f"/api/upload-sessions/{first.json()['id']}"
    assert client.post(path + "/complete", {}, format="json").status_code == 400
    assert (
        client.put(
            path + "/chunk", b"bad", content_type="application/octet-stream", HTTP_UPLOAD_OFFSET="9"
        ).status_code
        == 400
    )
    assert (
        client.put(
            path + "/chunk",
            CONTENTS[:4],
            content_type="application/octet-stream",
            HTTP_UPLOAD_OFFSET="0",
        ).status_code
        == 200
    )
    assert (
        client.put(
            path + "/chunk",
            b"wrong",
            content_type="application/octet-stream",
            HTTP_UPLOAD_OFFSET="0",
        ).status_code
        == 400
    )
    assert client.post("/api/upload-sessions", payload(), format="json").status_code == 429
    assert client.delete(path).status_code == 200
    settings.OWNER_STORAGE_BYTES = len(CONTENTS) - 1
    assert client.post("/api/upload-sessions", payload(), format="json").status_code == 429
    assert not AnalysisRun.objects.exists()


def test_foreign_owner_and_csrf_cannot_transfer_or_inspect(workspace, django_user_model):
    owner, client = workspace
    session = start(owner)
    other = django_user_model.objects.create_user("other-operator", is_staff=True)
    client.force_authenticate(other)
    path = f"/api/upload-sessions/{session.pk}"
    assert client.get(path).status_code == client.delete(path).status_code == 404
    assert client.post(path + "/complete", {}, format="json").status_code == 404
    assert (
        client.put(
            path + "/chunk", b"x", content_type="application/octet-stream", HTTP_UPLOAD_OFFSET="0"
        ).status_code
        == 404
    )
    csrf = APIClient(enforce_csrf_checks=True)
    csrf.force_login(owner)
    assert csrf.post("/api/upload-sessions", payload(), format="json").status_code == 403


def test_checksum_failure_erases_bytes_and_does_not_publish(workspace):
    owner, _ = workspace
    session = start(owner)
    write_chunk(owner, session.pk, 0, b"X" * len(CONTENTS))
    request_completion(owner, session.pk)
    assert not verify(session.pk)
    session.refresh_from_db()
    session.asset.refresh_from_db()
    assert session.state == "CANCELLED" and session.asset.purge_completed_at
    assert not private_path(session.asset.storage_key).exists()
    assert session.asset.metadata == {} and not session.expected_sha256
    assert not AnalysisRun.objects.exists() and not Match.objects.exists()


def test_expiry_consent_withdrawal_and_account_deletion_purge_uploads(workspace):
    owner, _ = workspace
    session = start(owner)
    UploadSession.objects.filter(pk=session.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    reconcile_uploads()
    session.refresh_from_db()
    assert session.state == "CANCELLED"
    session = uploaded(owner)
    record_consent(owner, "PROCESSING", "WITHDRAW", POLICY_VERSION, uuid4())
    reconcile_uploads()
    session.refresh_from_db()
    assert session.state == "CANCELLED" and not AnalysisRun.objects.exists()
    record_consent(owner, "PROCESSING", "GRANT", POLICY_VERSION, uuid4())
    session = start(owner)
    delete_account(owner)
    session.refresh_from_db()
    assert session.state == "CANCELLED" and not session.asset.upload_session


def test_stale_verifier_cannot_erase_newly_completed_upload(workspace, monkeypatch):
    owner, _ = workspace
    session = uploaded(owner)
    import backend.core.resumable as service

    original = service.materialize
    nested = False

    @contextmanager
    def newer(asset, storage=None):
        nonlocal nested
        if not nested:
            nested = True
            UploadSession.objects.filter(pk=session.pk).update(
                verification_lease=timezone.now() - timedelta(seconds=1)
            )
            assert service.verify(session.pk)
        with original(asset, storage) as path:
            yield path

    monkeypatch.setattr(service, "materialize", newer)
    assert not verify(session.pk)
    session.refresh_from_db()
    session.asset.refresh_from_db()
    assert session.state == "COMPLETE" and not session.asset.deleted_at
    assert AnalysisRun.objects.count() == 1


def test_imported_recording_retains_review_and_rejects_stale_claim(workspace):
    owner, _ = workspace
    from tests.test_match_import import import_one
    from tests.test_recording_attachment import metadata

    match = import_one(owner)[-1]
    claim = metadata(match)
    claim.pop("attribution_confirmed")
    session = begin(owner, uuid4(), len(CONTENTS), *checks(), claim, match.pk)
    write_chunk(owner, session.pk, 0, CONTENTS)
    request_completion(owner, session.pk)
    Match.objects.filter(pk=match.pk).update(metadata_revision=match.metadata_revision + 1)
    assert not verify(session.pk)
    assert not AnalysisRun.objects.exists()
    match.refresh_from_db()
    claim = metadata(match)
    claim.pop("attribution_confirmed")
    session = begin(owner, uuid4(), len(CONTENTS), *checks(), claim, match.pk)
    write_chunk(owner, session.pk, 0, CONTENTS)
    request_completion(owner, session.pk)
    assert verify(session.pk)
    match.refresh_from_db()
    source = ReplaySource.objects.get(asset=session.asset)
    assert source.attribution_state == "PENDING_REVIEW" and match.asset_id is None
    assert not GameplayEvent.objects.exists()


class ControlledStorage:
    def __init__(self):
        self.info = {}
        self.cancelled = []
        self.fail_purge = False

    def begin_upload(self, key, size, md5_hash, session_id):
        self.info = {
            "name": key,
            "bucket": "fixture-private-bucket",
            "size": str(size),
            "generation": "17",
            "contentType": "video/mp4",
            "md5Hash": md5_hash,
            "metadata": {"upload_session_id": str(session_id)},
        }
        return f"https://storage.googleapis.com/upload/storage/v1/b/fixture-private-bucket/o?uploadType=resumable&name={key}&upload_id=fixture-token"

    def inspect_object(self, key):
        return self.info

    def upload_status(self, session, size):
        return size

    def download(self, key, generation, target, size):
        assert generation == "17" and size == len(CONTENTS)
        target.write_bytes(CONTENTS)

    def cancel_upload(self, session):
        self.cancelled.append(session)

    def delete_asset(self, key):
        if self.fail_purge:
            raise CloudFailure("STORAGE_UNAVAILABLE")


@pytest.fixture
def cloud(workspace, settings, monkeypatch):
    settings.RESUMABLE_STORAGE_PROVIDER = "GCS"
    settings.GCS_STORAGE_QUALIFIED = True
    settings.GCS_PRIVATE_BUCKET = "fixture-private-bucket"
    store = ControlledStorage()
    monkeypatch.setattr("backend.core.resumable.storage_for", lambda asset: store)
    monkeypatch.setattr("backend.core.storage.storage_for", lambda asset: store)
    return workspace[0], workspace[1], store


def test_cloud_byte_verification_pin_and_secret_exclusion(cloud):
    owner, client, store = cloud
    session = start(owner)
    assert session.asset.upload_session and session.asset.upload_expires_at
    exported = json.dumps(client.get("/api/account/export").json())
    assert "fixture-token" not in exported and "upload_url" not in exported
    assert "expected_sha256" not in exported and "expected_md5" not in exported
    assert client.get("/api/account/export").json()["upload_sessions"][0]["id"] == str(session.pk)
    request_completion(owner, session.pk)
    assert verify(session.pk, storage=store)
    session.asset.refresh_from_db()
    assert session.asset.storage_generation == "17" and not session.asset.upload_session
    assert session.asset.source_sha256 == checks()[0] and not session.asset.upload_expires_at


def test_failed_cloud_cancellation_holds_quota_until_retry(cloud):
    owner, _, store = cloud
    session = start(owner)
    store.fail_purge = True
    with pytest.raises(CloudFailure):
        cancel(owner, session.pk)
    session.refresh_from_db()
    session.asset.refresh_from_db()
    assert session.state == "PURGING" and not session.asset.purge_completed_at
    assert session.asset.bytes == len(CONTENTS)
    store.fail_purge = False
    reconcile_uploads()
    session.refresh_from_db()
    assert session.state == "CANCELLED"


def test_deletion_during_cloud_initialization_retains_and_cancels_returned_capability(cloud):
    owner, _, store = cloud
    original = store.begin_upload

    def deleted(*args):
        result = original(*args)
        with pytest.raises(CloudFailure, match="EXPIRY_PENDING"):
            delete_account(owner, storage=store)
        return result

    store.begin_upload = deleted
    with pytest.raises(CloudFailure, match="INITIALIZATION_FAILED"):
        start(owner)
    asset = ReplayAsset.objects.get(owner=owner)
    assert asset.deleted_at and asset.purge_completed_at and not asset.upload_session
    assert any("fixture-token" in value for value in store.cancelled)


def test_provider_outage_retries_are_bounded_and_leave_cleanup_receipt(cloud):
    owner, _, store = cloud
    session = start(owner)
    request_completion(owner, session.pk)
    store.inspect_object = Mock(side_effect=CloudFailure("STORAGE_UNAVAILABLE"))
    for _ in range(3):
        UploadSession.objects.filter(pk=session.pk).update(next_attempt_at=None)
        assert not verify(session.pk, storage=store)
    session.refresh_from_db()
    assert session.verification_attempts == 3 and session.state == "CANCELLED"
    assert not AnalysisRun.objects.exists()


def response(code=200, body=None, headers=None, blocks=None):
    value = Mock(status_code=code, headers=headers or {})
    value.json.return_value = body or {}
    value.iter_content.return_value = blocks or []
    return value


def test_google_create_only_fixed_length_and_validated_capability():
    transport = Mock()
    asset = uuid4()
    key = f"7/{asset}/source.mp4"
    store = GooglePrivateStorage(transport, "fixture-private-bucket", 7, asset)
    location = f"https://storage.googleapis.com/upload/storage/v1/b/fixture-private-bucket/o?uploadType=resumable&name={key}&upload_id=fixture"
    transport.request.return_value = response(headers={"Location": location})
    assert store.begin_upload(key, 123, checks()[1], uuid4()) == location
    call = transport.request.call_args.kwargs
    assert (
        call["params"]["ifGenerationMatch"] == "0"
        and call["headers"]["X-Upload-Content-Length"] == "123"
    )
    assert call["timeout"] == (5, 20) and call["allow_redirects"] is False
    transport.request.return_value = response(308, headers={"Range": "bytes=0-99"})
    assert store.upload_status(location, 123) == 100
    transport.request.return_value = response(499)
    store.cancel_upload(location)
    for evil in [
        "https://evil.example/session",
        location.replace("7/", "8/"),
        location + "&upload_id=duplicate",
        location.replace("https:", "http:"),
    ]:
        before = transport.request.call_count
        with pytest.raises((CloudFailure, ValueError)):
            store.cancel_upload(evil)
        assert transport.request.call_count == before


def test_google_range_is_generation_pinned_and_bounds_upstream_bytes():
    transport = Mock()
    asset = uuid4()
    key = f"7/{asset}/source.mp4"
    store = GooglePrivateStorage(transport, "fixture-private-bucket", 7, asset)
    upstream = response(206, headers={"Content-Range": "bytes 2-4/8"}, blocks=[b"abc"])
    transport.request.return_value = upstream
    assert b"".join(store.range_stream(key, "17", 2, 4, 8, lambda: None)) == b"abc"
    assert transport.request.call_args.kwargs["params"]["ifGenerationMatch"] == "17"
    upstream.close.assert_called_once()
    transport.request.return_value = response(
        206, headers={"Content-Range": "bytes 2-4/8"}, blocks=[b"too long"]
    )
    with pytest.raises(CloudFailure, match="LENGTH"):
        list(store.range_stream(key, "17", 2, 4, 8, lambda: None))


def test_unknown_post_restore_capability_never_reports_completed_erasure(cloud):
    owner, _, store = cloud
    session = start(owner)
    ReplayAsset.objects.filter(pk=session.asset_id).update(upload_session="")
    with pytest.raises(CloudFailure, match="EXPIRY_PENDING"):
        delete_asset(owner, session.asset_id, store)
    session.asset.refresh_from_db()
    assert session.asset.deleted_at and not session.asset.purge_completed_at
    ReplayAsset.objects.filter(pk=session.asset_id).update(
        upload_expires_at=timezone.now() - timedelta(seconds=1)
    )
    delete_asset(owner, session.asset_id, store)
    session.asset.refresh_from_db()
    assert session.asset.purge_completed_at


def test_gcs_and_public_activation_remain_gated(workspace, settings):
    _, client = workspace
    settings.RESUMABLE_STORAGE_PROVIDER = "GCS"
    assert client.post("/api/upload-sessions", payload(), format="json").status_code == 503
    settings.RESUMABLE_STORAGE_PROVIDER = "LOCAL"
    settings.LOCAL_OPERATOR_UPLOADS = False
    assert client.post("/api/upload-sessions", payload(), format="json").status_code == 403


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_concurrent_begin_and_repeated_chunk_have_one_reservation(workspace):
    from concurrent.futures import ThreadPoolExecutor

    from django.db import close_old_connections, connection

    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL locking required")
    owner, _ = workspace
    request_id = uuid4()

    def connected(fn, *args, **kwargs):
        close_old_connections()
        try:
            return fn(*args, **kwargs)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        sessions = [pool.submit(connected, start, owner, request_id=request_id) for _ in range(2)]
        ids = [future.result(timeout=10).pk for future in sessions]
        assert ids[0] == ids[1] and UploadSession.objects.count() == 1
        chunks = [pool.submit(connected, write_chunk, owner, ids[0], 0, CONTENTS) for _ in range(2)]
        assert [future.result(timeout=10) for future in chunks] == [len(CONTENTS)] * 2
    assert (
        private_path(UploadSession.objects.get(pk=ids[0]).asset.storage_key).read_bytes()
        == CONTENTS
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_cancellation_during_verification_cannot_publish(workspace, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from django.db import close_old_connections, connection

    import backend.core.resumable as service

    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL locking required")
    owner, _ = workspace
    session = uploaded(owner)
    entered, release = Event(), Event()
    original = service.materialize

    @contextmanager
    def paused(asset, storage=None):
        with original(asset, storage) as path:
            entered.set()
            assert release.wait(10)
            yield path

    def process():
        close_old_connections()
        try:
            return verify(session.pk)
        finally:
            close_old_connections()

    monkeypatch.setattr(service, "materialize", paused)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(process)
        assert entered.wait(10)
        try:
            cancel(owner, session.pk)
        finally:
            release.set()
        assert not future.result(timeout=10)
    assert not AnalysisRun.objects.exists() and not Match.objects.exists()
    assert UploadSession.objects.get(pk=session.pk).state == "CANCELLED"


def test_waiting_upload_does_not_starve_ready_verification(workspace, django_user_model):
    owner, _ = workspace
    start(owner)
    other = django_user_model.objects.create_user("ready-operator", is_staff=True)
    ready = uploaded(other)
    assert reconcile_uploads(limit=1) == 1
    ready.refresh_from_db()
    assert ready.state == "COMPLETE"


def test_expired_evidence_cannot_play_claim_heartbeat_or_publish(workspace):
    from backend.core.jobs import claim_run, finish_run, heartbeat

    owner, client = workspace
    session = uploaded(owner)
    assert verify(session.pk)
    run = AnalysisRun.objects.get(asset=session.asset)
    token = claim_run(run.pk)
    assert token is not None
    ReplayAsset.objects.filter(pk=session.asset_id).update(
        retain_until=timezone.now() - timedelta(seconds=1)
    )
    assert not heartbeat(run.pk, token)
    assert not finish_run(run.pk, token, {"status": "COMPLETED"})
    assert client.get(f"/api/assets/{session.asset_id}/media").status_code == 404


def test_restore_purges_pending_upload_without_reusing_authorization(workspace, settings):
    from backend.core.control_journal import record_intent
    from backend.core.recovery import apply_restore_controls

    owner, _ = workspace
    session = uploaded(owner)
    record_intent(owner.pk, "CONSENT_WITHDRAW", scope="PROCESSING")
    settings.RESTORE_QUARANTINE = True
    assert apply_restore_controls() == 1
    session.refresh_from_db()
    session.asset.refresh_from_db()
    assert session.state == "CANCELLED" and session.asset.purge_completed_at
    assert not AnalysisRun.objects.exists()


def test_restore_of_post_backup_session_preserves_unknown_capability_deadline(cloud):
    from backend.core.recovery import purge_orphan

    owner, _, store = cloud
    session = start(owner)
    item = {
        "asset": str(session.asset_id),
        "storage_key": session.asset.storage_key,
        "storage_provider": "GCS",
        "storage_generation": "",
        "bytes": len(CONTENTS),
        "upload_expires_at": session.asset.upload_expires_at.isoformat(),
    }
    UploadSession.objects.filter(pk=session.pk).delete()
    ReplayAsset.objects.filter(pk=session.asset_id).delete()
    with pytest.raises(CloudFailure, match="EXPIRY_PENDING"):
        purge_orphan(owner.pk, item)
    restored = ReplayAsset.objects.get(pk=session.asset_id)
    assert (
        restored.deleted_at and not restored.purge_completed_at and restored.bytes == len(CONTENTS)
    )
    ReplayAsset.objects.filter(pk=restored.pk).update(
        upload_expires_at=timezone.now() - timedelta(seconds=1)
    )
    purge_orphan(owner.pk, item)
    restored.refresh_from_db()
    assert restored.purge_completed_at


def test_invalid_upstream_range_closes_response_and_sends_no_body():
    transport = Mock()
    asset = uuid4()
    key = f"7/{asset}/source.mp4"
    store = GooglePrivateStorage(transport, "fixture-private-bucket", 7, asset)
    upstream = response(200, blocks=[b"full-object"])
    transport.request.return_value = upstream
    with pytest.raises(CloudFailure):
        list(store.range_stream(key, "17", 2, 4, 8, lambda: None))
    upstream.close.assert_called_once()
    upstream.iter_content.assert_not_called()


def test_migration_reverse_requires_completed_physical_erasure(workspace):
    from importlib import import_module

    from django.apps import apps
    from django.db import connection

    owner, _ = workspace
    session = start(owner)
    guard = import_module("backend.core.migrations.0016_resumable_uploads").guard_reverse
    with connection.schema_editor() as editor:
        with pytest.raises(ValueError):
            guard(apps, editor)
        cancel(owner, session.pk)
        guard(apps, editor)


def test_match_deletion_revokes_pending_attachment_and_schedules_private_purge(workspace):
    from backend.core.storage import delete_metadata_match
    from tests.test_match_import import import_one
    from tests.test_recording_attachment import metadata

    owner, _ = workspace
    match = import_one(owner)[-1]
    claim = metadata(match)
    claim.pop("attribution_confirmed")
    session = begin(owner, uuid4(), len(CONTENTS), *checks(), claim, match.pk)
    write_chunk(owner, session.pk, 0, CONTENTS)
    delete_metadata_match(owner, match.pk)
    session.refresh_from_db()
    session.asset.refresh_from_db()
    assert session.state == "PURGING" and session.asset.deleted_at and session.asset.metadata == {}
    with pytest.raises(ValidationError):
        request_completion(owner, session.pk)
    reconcile_uploads()
    session.refresh_from_db()
    assert session.state == "CANCELLED" and not AnalysisRun.objects.exists()


@pytest.mark.parametrize("metadata", [None, [], "unexpected"])
def test_provider_metadata_drift_fails_without_publication(cloud, metadata):
    owner, _, store = cloud
    session = start(owner)
    request_completion(owner, session.pk)
    store.info["metadata"] = metadata
    assert not verify(session.pk, storage=store)
    assert UploadSession.objects.get(pk=session.pk).state == "CANCELLED"
    assert not AnalysisRun.objects.exists()


def test_crashed_verifier_exhausts_durable_attempt_budget(workspace):
    owner, _ = workspace
    session = uploaded(owner)
    UploadSession.objects.filter(pk=session.pk).update(verification_attempts=3)
    assert not verify(session.pk)
    session.refresh_from_db()
    assert session.state == "PURGING" and session.verification_attempts == 3
    reconcile_uploads()
    assert UploadSession.objects.get(pk=session.pk).state == "CANCELLED"
    assert not AnalysisRun.objects.exists()


def test_cancellation_during_status_probe_does_not_return_stale_capability(cloud):
    from backend.core.resumable import status

    owner, _, store = cloud
    session = start(owner)

    def revoked(session_url, size):
        cancel(owner, session.pk)
        return size

    store.upload_status = revoked
    result = status(owner, session.pk)
    assert result["state"] == "CANCELLED" and result["upload_url"] is None
    assert not AnalysisRun.objects.exists()
