import base64
import hashlib
import importlib
from datetime import timedelta
from uuid import uuid4

import pytest
from django.db.migrations.exceptions import IrreversibleError
from django.utils import timezone
from rest_framework.test import APIClient

from backend.core.consents import POLICY_VERSION, record_consent
from backend.core.models import (
    AnalysisRun,
    DevicePairing,
    GameplayEvent,
    Match,
    RecordingDevice,
    RecordingReceipt,
    ReplayAsset,
    ReplaySource,
    UploadSession,
)
from backend.core.recovery import apply_restore_controls
from backend.core.resumable import verify
from backend.core.storage import delete_account, delete_asset
from tests.test_match_import import import_one
from tests.test_recording_attachment import metadata

pytestmark = pytest.mark.django_db
CONTENT = b"synthetic transfer bytes, not a playable Tekken capture"


@pytest.fixture
def workspace(django_user_model, settings, tmp_path):
    settings.LOCAL_OPERATOR_UPLOADS = settings.LOCAL_RECORDING_COMPANION = True
    settings.PRIVATE_DATA_ROOT = tmp_path / "private"
    owner = django_user_model.objects.create_user("companion-owner", is_staff=True)
    web = APIClient()
    web.force_authenticate(owner)
    return owner, web


def paired(web):
    response = web.post(
        "/api/recording-devices",
        {"label": "Fixture PC", "sync_consent": True, "policy_version": POLICY_VERSION},
        format="json",
    )
    assert response.status_code == 201, response.data
    client = APIClient()
    response = client.post(
        "/api/companion/pair", {"pairing_code": response.data["pairing_code"]}, format="json"
    )
    assert response.status_code == 201, response.data
    credential = response.data["credential"]
    client.credentials(HTTP_AUTHORIZATION="RecordingDevice " + credential)
    return client, response.data


def upload_body(content=CONTENT):
    return {
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "md5": base64.b64encode(hashlib.md5(content, usedforsecurity=False).digest()).decode(),
    }


def start(client, content=CONTENT):
    response = client.post("/api/companion/uploads", upload_body(content), format="json")
    assert response.status_code in {200, 201}, response.data
    return response.data


def uploaded(client):
    info = start(client)
    path = "/api/companion/uploads/" + info["id"]
    for offset, part in [(0, CONTENT[:9]), (0, CONTENT[:9]), (9, CONTENT[9:])]:
        result = client.put(
            path + "/chunk",
            part,
            content_type="application/octet-stream",
            HTTP_UPLOAD_OFFSET=str(offset),
        )
        assert result.status_code == 200, result.data
    assert client.post(path + "/complete", {}, format="json").status_code == 202
    assert verify(info["id"])
    return info


def validated(info):
    run = AnalysisRun.objects.get(asset_id=info["asset_id"])
    run.status = "REVIEW_REQUIRED"
    run.result = {"source": {"source_sha256": run.asset.source_sha256, "duration_seconds": 1}}
    run.save()
    return run


def test_pairing_one_use_expiry_new_challenge_and_private_hashes(workspace):
    owner, web = workspace
    client, data = paired(web)
    device = RecordingDevice.objects.get(pk=data["device_id"])
    assert data["credential"] != device.token_digest and device.owner == owner
    assert web.get("/api/recording-devices")["Cache-Control"] == "private, no-store"
    assert data["credential"] not in str(web.get("/api/recording-devices").data)
    code = web.post(
        "/api/recording-devices",
        {"label": "Second", "sync_consent": True, "policy_version": POLICY_VERSION},
        format="json",
    ).data["pairing_code"]
    DevicePairing.objects.filter(token_digest=hashlib.sha256(code.encode()).hexdigest()).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert (
        client.post("/api/companion/pair", {"pairing_code": code}, format="json").status_code == 400
    )
    first = web.post(
        "/api/recording-devices",
        {"label": "First", "sync_consent": True, "policy_version": POLICY_VERSION},
        format="json",
    ).data["pairing_code"]
    second = web.post(
        "/api/recording-devices",
        {"label": "Second", "sync_consent": True, "policy_version": POLICY_VERSION},
        format="json",
    ).data["pairing_code"]
    assert (
        client.post("/api/companion/pair", {"pairing_code": first}, format="json").status_code
        == 400
    )
    assert (
        client.post("/api/companion/pair", {"pairing_code": second}, format="json").status_code
        == 201
    )
    assert (
        client.post("/api/companion/pair", {"pairing_code": second}, format="json").status_code
        == 400
    )


@pytest.mark.parametrize(
    "change", [{"sync_consent": False}, {"policy_version": "old"}, {"label": "../private"}]
)
def test_pair_consent_policy_and_label_admission(workspace, change):
    _, web = workspace
    assert (
        web.post(
            "/api/recording-devices",
            {"label": "PC", "sync_consent": True, "policy_version": POLICY_VERSION, **change},
            format="json",
        ).status_code
        == 400
    )
    assert not RecordingDevice.objects.exists() and not DevicePairing.objects.exists()


def test_pair_rate_device_and_storage_limits(workspace, settings):
    _, web = workspace
    client, _ = paired(web)
    settings.COMPANION_MAX_DEVICES = 1
    assert (
        web.post(
            "/api/recording-devices",
            {"label": "PC", "sync_consent": True, "policy_version": POLICY_VERSION},
            format="json",
        ).status_code
        == 429
    )
    settings.OWNER_STORAGE_BYTES = 1
    assert client.post("/api/companion/uploads", upload_body(), format="json").status_code == 429
    anonymous = APIClient()
    for _ in range(10):
        response = anonymous.post("/api/companion/pair", {"pairing_code": "a" * 43}, format="json")
    assert response.status_code == 429 and int(response["Retry-After"]) > 0


def test_device_credential_cannot_access_account_or_other_uploads(workspace, django_user_model):
    owner, web = workspace
    client, _ = paired(web)
    assert client.get("/api/overview").status_code == 403
    assert client.get("/api/recording-devices").status_code == 403
    assert client.get("/api/synced-recordings").status_code == 403
    other = django_user_model.objects.create_user("other-companion", is_staff=True)
    otherweb = APIClient()
    otherweb.force_authenticate(other)
    otherclient, data = paired(otherweb)
    info = start(client)
    path = "/api/companion/uploads/" + info["id"]
    assert otherclient.get(path).status_code == 404
    assert (
        otherclient.put(
            path + "/chunk",
            CONTENT,
            content_type="application/octet-stream",
            HTTP_UPLOAD_OFFSET="0",
        ).status_code
        == 404
    )
    assert otherclient.post(path + "/complete", {}, format="json").status_code == 404
    assert otherweb.get("/api/synced-recordings").data["recordings"] == []
    assert web.delete("/api/recording-devices/" + data["device_id"]).status_code == 404
    assert RecordingReceipt.objects.get().owner == owner


def test_synced_bytes_remain_unassigned_and_playback_waits_for_media_validation(workspace):
    _, web = workspace
    client, _ = paired(web)
    info = uploaded(client)
    assert (
        Match.objects.count() == ReplaySource.objects.count() == GameplayEvent.objects.count() == 0
    )
    assert AnalysisRun.objects.count() == 1
    assert web.get("/api/assets/" + info["asset_id"] + "/media").status_code == 404
    assert web.get("/api/synced-recordings").data["recordings"][0]["availability"] == "PENDING"
    validated(info)
    recording = web.get("/api/synced-recordings").data["recordings"][0]
    assert (
        recording["availability"] == "AVAILABLE" and recording["attribution_state"] == "UNASSIGNED"
    )
    response = web.get(recording["media_url"], HTTP_RANGE="bytes=1-4")
    assert response.status_code == 206 and b"".join(response.streaming_content) == CONTENT[1:5]
    assert client.get(recording["media_url"]).status_code == 403


def test_deduplicate_across_restart_and_devices_and_suppress_deleted_copy(workspace):
    owner, web = workspace
    client, _ = paired(web)
    info = uploaded(client)
    assert start(client)["id"] == info["id"]
    second, _ = paired(web)
    assert second.post("/api/companion/uploads", upload_body(), format="json").data == {
        "state": "DUPLICATE"
    }
    delete_asset(owner, info["asset_id"])
    assert client.post("/api/companion/uploads", upload_body(), format="json").data == {
        "state": "REMOVED"
    }
    assert second.post("/api/companion/uploads", upload_body(), format="json").data == {
        "state": "REMOVED"
    }
    assert (
        UploadSession.objects.count()
        == ReplayAsset.objects.count()
        == RecordingReceipt.objects.count()
        == 1
    )


@pytest.mark.parametrize(
    "operation",
    [
        "revoke",
        "withdraw-sync",
        "withdraw-processing",
        "account-delete",
        "expire",
        "restore",
        "logout-all",
    ],
)
def test_lifecycle_stops_late_chunks_completions_and_retries(workspace, settings, operation):
    owner, web = workspace
    client, device = paired(web)
    info = start(client)
    if operation == "revoke":
        assert web.delete("/api/recording-devices/" + device["device_id"]).status_code == 200
    elif operation.startswith("withdraw"):
        record_consent(
            owner,
            "RECORDING_SYNC" if operation == "withdraw-sync" else "PROCESSING",
            "WITHDRAW",
            POLICY_VERSION,
            uuid4(),
        )
    elif operation == "account-delete":
        delete_account(owner)
    elif operation == "expire":
        RecordingDevice.objects.filter(pk=device["device_id"]).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
    elif operation == "logout-all":
        from backend.core.accounts import revoke_sessions

        revoke_sessions(owner)
    else:
        record_consent(owner, "PROCESSING", "WITHDRAW", POLICY_VERSION, uuid4())
        settings.RESTORE_QUARANTINE = True
        apply_restore_controls()
        settings.RESTORE_QUARANTINE = False
    path = "/api/companion/uploads/" + info["id"]
    for response in [
        client.put(
            path + "/chunk",
            CONTENT,
            content_type="application/octet-stream",
            HTTP_UPLOAD_OFFSET="0",
        ),
        client.post(path + "/complete", {}, format="json"),
        client.post("/api/companion/uploads", upload_body(), format="json"),
    ]:
        assert response.status_code in {401, 403}
    assert not GameplayEvent.objects.exists() and UploadSession.objects.count() == 1


def test_regrant_requires_new_pairing_and_old_upload_is_not_resurrected(workspace):
    owner, web = workspace
    client, _ = paired(web)
    start(client)
    record_consent(owner, "RECORDING_SYNC", "WITHDRAW", POLICY_VERSION, uuid4())
    newclient, _ = paired(web)
    assert client.post("/api/companion/uploads", upload_body(), format="json").status_code == 401
    assert newclient.post("/api/companion/uploads", upload_body(), format="json").data == {
        "state": "REMOVED"
    }


def test_attribution_preserves_imported_uuid_and_requires_matching_reviewed_claim(workspace):
    owner, web = workspace
    client, _ = paired(web)
    info = uploaded(client)
    validated(info)
    match = import_one(owner)[-1]
    before = Match.objects.values().get(pk=match.pk)
    url = "/api/synced-recordings/" + info["id"] + "/attach"
    claim = metadata(match)
    assert (
        web.post(
            url,
            {"match_id": str(match.pk), "metadata": {**claim, "player_id": "incorrect"}},
            format="json",
        ).status_code
        == 400
    )
    assert not ReplaySource.objects.exists()
    assert (
        web.post(url, {"match_id": str(match.pk), "metadata": claim}, format="json").status_code
        == 202
    )
    assert (
        web.post(url, {"match_id": str(match.pk), "metadata": claim}, format="json").status_code
        == 202
    )
    assert ReplaySource.objects.count() == 1 and Match.objects.values().get(pk=match.pk) == before
    source = ReplaySource.objects.get()
    assert source.match_id == match.pk and source.attribution_state == "PENDING_REVIEW"
    assert source.access_class == "USER_UPLOAD" and not GameplayEvent.objects.exists()


def test_gated_operation_and_migration_history(workspace, settings):
    _, web = workspace
    client, _ = paired(web)
    settings.LOCAL_RECORDING_COMPANION = False
    assert client.post("/api/companion/uploads", upload_body(), format="json").status_code == 403
    from django.apps import apps

    guard = importlib.import_module(
        "backend.core.migrations.0022_recording_companion"
    ).guard_history
    with pytest.raises(IrreversibleError):
        guard(apps, None)


def test_revocation_between_authentication_and_chunk_write_is_fenced(workspace, monkeypatch):
    from backend.core.companion import RecordingDeviceAuthentication, revoke_device

    owner, web = workspace
    client, device = paired(web)
    info = start(client)
    original = RecordingDeviceAuthentication.authenticate

    def revoked_authentication(authenticator, request):
        result = original(authenticator, request)
        revoke_device(owner, device["device_id"])
        return result

    monkeypatch.setattr(RecordingDeviceAuthentication, "authenticate", revoked_authentication)
    response = client.put(
        "/api/companion/uploads/" + info["id"] + "/chunk",
        CONTENT,
        content_type="application/octet-stream",
        HTTP_UPLOAD_OFFSET="0",
    )
    assert response.status_code == 401
    session = UploadSession.objects.get(pk=info["id"])
    assert session.received_bytes == 0 and session.state == "PURGING"


def test_pairing_controls_require_csrf_and_export_excludes_device_secrets(workspace):
    _, web = workspace
    client, data = paired(web)
    browser = APIClient(enforce_csrf_checks=True)
    browser.force_login(workspace[0])
    assert (
        browser.post(
            "/api/recording-devices",
            {"label": "PC", "sync_consent": True, "policy_version": POLICY_VERSION},
            format="json",
        ).status_code
        == 403
    )
    export = web.get("/api/account/export").data
    assert data["credential"] not in str(export)
    assert "token_digest" not in str(export) and "key_digest" not in str(export)
