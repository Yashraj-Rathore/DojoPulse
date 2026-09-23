import json
import shutil
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.uploadhandler import StopUpload
from django.core.management import call_command
from django.test import Client
from django.utils import timezone
from rest_framework.test import APIClient

from analysis.process import run_bounded
from backend.core.models import AnalysisRun, ReplayAsset
from backend.core.uploads import BoundedUploadHandler

pytestmark = pytest.mark.django_db


def test_streaming_upload_limit_applies_across_chunks():
    handler = BoundedUploadHandler()
    handler.max_bytes = 5
    assert handler.receive_data_chunk(b"123", 0) == b"123"
    with pytest.raises(StopUpload):
        handler.receive_data_chunk(b"456", 3)


def test_session_login_requires_csrf(django_user_model):
    django_user_model.objects.create_user("login", password="synthetic-test-password")
    client = Client(enforce_csrf_checks=True)
    session = client.get("/api/session")
    body = {"username": "login", "password": "synthetic-test-password"}
    assert client.post("/api/session", body, content_type="application/json").status_code == 403
    response = client.post(
        "/api/session",
        body,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=session.json()["csrf"],
    )
    assert response.status_code == 200 and response.json()["authenticated"]
    assert client.get("/api/overview").status_code == 200


@pytest.mark.media
@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg absent")
def test_upload_queues_worker_analyzes_and_retention_purges(django_user_model, settings, tmp_path):
    settings.LOCAL_OPERATOR_UPLOADS = True
    settings.PRIVATE_DATA_ROOT = tmp_path / "private"
    owner = django_user_model.objects.create_user("operator", is_staff=True)
    source = tmp_path / "synthetic.mp4"
    run_bounded(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=1920x1080:r=60:d=0.1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ]
    )
    client = APIClient()
    client.force_authenticate(owner)
    metadata = {
        "game_build": "unverified-fixture",
        "session_id": "s",
        "played_at": timezone.now().isoformat(),
        "source_kind": "ranked",
    }
    response = client.post(
        "/api/uploads",
        {
            "file": SimpleUploadedFile(
                "capture.mp4", source.read_bytes(), content_type="video/mp4"
            ),
            "metadata": json.dumps(metadata),
            "processing_consent": "true",
        },
        format="multipart",
    )
    assert response.status_code == 202
    run = AnalysisRun.objects.get(pk=response.data["run_id"])
    assert run.status == "QUEUED" and not run.result
    call_command("process_runs", once=True)
    run.refresh_from_db()
    assert run.status == "REVIEW_REQUIRED" and run.result["opportunities"] == []
    asset = ReplayAsset.objects.get(pk=run.asset_id)
    assert len(asset.source_sha256) == 64
    path = settings.PRIVATE_DATA_ROOT / asset.storage_key
    assert path.is_file()
    ReplayAsset.objects.filter(pk=asset.pk).update(
        retain_until=timezone.now() - timedelta(seconds=1)
    )
    call_command("purge_expired")
    asset.refresh_from_db()
    assert asset.deleted_at and asset.purge_completed_at and not path.exists()
    assert client.get(f"/api/assets/{asset.pk}/media").status_code == 404
