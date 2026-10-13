"""Fenced private artifacts and actual codecs. Synthetic facts cannot approve gameplay."""

import base64
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import Throttled
from rest_framework.test import APIClient

from analysis.contracts import digest
from analysis.media import file_hash
from analysis.normalization import policy
from analysis.preview_bundle import MAX_BYTES, PIPELINE, validate_bundle
from analysis.process import run_bounded
from analysis.timing import timing_quality
from backend.core import previews
from backend.core.consents import POLICY_VERSION, record_consent
from backend.core.jobs import acknowledge_stopped, begin_execution, claim_run, finish_run
from backend.core.models import (
    AnalysisRun,
    GameplayEvent,
    Match,
    RecordingPreview,
    ReplayAsset,
)
from backend.core.preview_sandbox import COPY_FILE, command
from backend.core.resumable import begin, request_completion, verify, write_chunk
from backend.core.security import check_capacity
from backend.core.storage import delete_asset, private_path

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def owner(settings, tmp_path, django_user_model):
    settings.PRIVATE_DATA_ROOT = tmp_path
    settings.LOCAL_OPERATOR_UPLOADS = True
    settings.DEBUG = True
    settings.PARSER_BACKEND = "local"
    settings.RESUMABLE_STORAGE_PROVIDER = "LOCAL"
    return django_user_model.objects.create_user(username="preview-owner", is_staff=True)


def asset(owner, data=b"owner-source", **kwargs):
    result = ReplayAsset.objects.create(
        owner=owner,
        source_sha256=hashlib.sha256(data).hexdigest(),
        bytes=len(data),
        retain_until=timezone.now() + timedelta(days=1),
        **kwargs,
    )
    result.storage_key = f"{owner.pk}/{result.pk}/source.mp4"
    result.save()
    path = private_path(result.storage_key)
    path.parent.mkdir(parents=True)
    path.write_bytes(data)
    return result


def bundle(directory, source_hash):
    """Self-declared decoder output exercises boundary shape, not a playable/game fixture."""
    directory.mkdir()
    video = directory / "preview.mp4"
    video.write_bytes(b"synthetic-preview-bytes" + b"x" * 131072)
    times = [0, 16667, 50000, 66667]
    timeline = {"source_sha256": source_hash, "source_pts_us": times, "derived_pts_us": times}
    (directory / "timeline.json").write_text(json.dumps(timeline))
    report = {
        "status": "PREVIEW_READY",
        "policy_id": policy()["id"],
        "policy_sha256": digest(policy()),
        "source": {"sha256": source_hash},
        "timeline": {"content_hash": digest(timeline)},
        "quality": timing_quality(times, policy()),
        "canonical_publication": False,
        "precise_gameplay_analysis_approved": False,
        "scientific_gate_approval": False,
        "preservation": {
            "frame_count_preserved": True,
            "audio_packet_count_preserved": True,
            "audio_payloads_preserved": True,
            "unknown_intervals_preserved": True,
            "maximum_video_pts_error_us": 0,
            "maximum_audio_timestamp_error_us": 0,
        },
        "derivative": {
            "codec": "h264",
            "bytes": video.stat().st_size,
            "sha256": file_hash(video),
            "duration_seconds": 1,
        },
    }
    (directory / "report.json").write_text(json.dumps(report))
    return report


def ready(owner, tmp_path, monkeypatch):
    source = asset(owner)
    preview = previews.enqueue_preview(owner, source.pk, uuid4())

    def fake_normalize(src, directory, name):
        bundle(directory, source.source_sha256)
        return {"contract": "synthetic-fixture"}

    monkeypatch.setattr("backend.core.preview_sandbox.normalize_isolated", fake_normalize)
    call_command("process_runs", once=True)
    preview.refresh_from_db()
    assert preview.state == "READY"
    return source, preview


def test_fenced_publication_private_ranges_no_matches_or_gameplay(
    owner, tmp_path, monkeypatch, django_user_model
):
    source, preview = ready(owner, tmp_path, monkeypatch)
    assert private_path(source.storage_key).read_bytes() == b"owner-source"
    assert (
        preview.run.status == "PREVIEW_READY"
        and preview.run.result["automatic_gameplay_validated"] is False
    )
    assert not Match.objects.exists() and not GameplayEvent.objects.exists()
    assert preview.reserved_bytes == sum(value["bytes"] for value in preview.manifest.values())
    client = APIClient()
    client.force_authenticate(owner)
    response = client.get(f"/api/assets/{source.pk}/preview/media", HTTP_RANGE="bytes=2-6")
    assert response.status_code == 206 and response["Cache-Control"] == "private, no-store"
    assert b"".join(response.streaming_content) == b"nthet"
    response.close()
    data = client.get(f"/api/assets/{source.pk}/preview/quality").json()
    assert data["total"] == 1 and data["intervals"][0]["gap_us"] == 33333
    foreign = django_user_model.objects.create_user(username="foreign-preview", is_staff=True)
    client.force_authenticate(foreign)
    assert client.get(f"/api/assets/{source.pk}/preview/media").status_code == 404
    assert (
        client.post(
            f"/api/assets/{source.pk}/preview", {"request_id": str(uuid4())}, format="json"
        ).status_code
        == 404
    )
    client.force_authenticate(None)
    assert client.get(f"/api/assets/{source.pk}/preview/media").status_code == 403


def test_source_and_derivative_capacity_and_idempotence(owner, settings):
    source = asset(owner)
    request_id = uuid4()
    preview = previews.enqueue_preview(owner, source.pk, request_id)
    assert previews.enqueue_preview(owner, source.pk, request_id).pk == preview.pk
    assert AnalysisRun.objects.count() == 1 and preview.run.runbudget.attempt_seconds == 1920
    settings.OWNER_STORAGE_BYTES = source.bytes + MAX_BYTES
    with transaction.atomic(), pytest.raises(Throttled):
        check_capacity(owner, 1)
    source2 = asset(owner, b"other")
    with pytest.raises(ValidationError):
        previews.enqueue_preview(owner, source2.pk, request_id)


def test_stale_or_cross_pipeline_results_cannot_publish(owner):
    source = asset(owner)
    preview = previews.enqueue_preview(owner, source.pk, uuid4())
    fence = claim_run(preview.run_id)
    assert begin_execution(preview.run_id, fence)
    with pytest.raises(ValueError, match="cannot establish gameplay"):
        finish_run(preview.run_id, fence, {"status": "COMPLETED"})
    with pytest.raises(ValueError, match="Invalid preview"):
        finish_run(
            preview.run_id, fence, {"status": "PREVIEW_READY", "automatic_gameplay_validated": True}
        )
    assert not finish_run(preview.run_id, fence + 1, {"status": "PREVIEW_READY"})
    ordinary = AnalysisRun.objects.create(owner=owner, asset=source, request_key="ordinary")
    fence = claim_run(ordinary.pk)
    acknowledge_stopped(preview.run_id, 1)
    fence = claim_run(ordinary.pk)
    with pytest.raises(ValueError):
        finish_run(ordinary.pk, fence, {"status": "PREVIEW_READY"})


def test_stale_attempt_is_cleaned_before_retry_and_old_publication_fails(
    owner, monkeypatch, settings
):
    from backend.core.jobs import reconcile_runs
    from backend.core.models import ExecutionSlot

    source = asset(owner)
    preview = previews.enqueue_preview(owner, source.pk, uuid4())
    token = claim_run(preview.run_id)
    previews.start_preview(preview.run_id, token)
    preview.refresh_from_db()
    path = private_path(previews.attempt_prefix(preview, token) + "preview.mp4")
    path.parent.mkdir(parents=True)
    path.write_bytes(b"partial old attempt")
    AnalysisRun.objects.filter(pk=preview.run_id).update(
        lease_until=timezone.now() - timedelta(seconds=1)
    )
    reconcile_runs()
    settings.PARSER_BACKEND = "docker"
    monkeypatch.setattr("backend.core.preview_sandbox.remove_container", lambda name: None)
    previews.reconcile_previews()
    preview.run.refresh_from_db()
    assert preview.run.status == "QUEUED" and not path.exists()
    assert ExecutionSlot.objects.get(run=preview.run).released_at is not None
    new_token = claim_run(preview.run_id)
    assert new_token > token
    with pytest.raises(ValueError, match="RUN_REVOKED"):
        previews.publish_files(preview, token, path.parent)
    assert not path.exists()


def test_ambiguous_cloud_write_retains_quota_and_blocks_restore(
    owner, tmp_path, settings, monkeypatch
):
    from backend.core.cloud import CloudFailure

    source = asset(owner)
    source.storage_provider = "GCS"
    source.save()
    with pytest.raises(CloudFailure, match="UNQUALIFIED"):
        previews.enqueue_preview(owner, source.pk, uuid4())
    settings.GCS_PREVIEW_WRITES_QUALIFIED = True
    preview = previews.enqueue_preview(owner, source.pk, uuid4())
    token = claim_run(preview.run_id)
    previews.start_preview(preview.run_id, token)
    preview.refresh_from_db()
    directory = tmp_path / "bundle"
    bundle(directory, source.source_sha256)

    class FailedStorage:
        def create_preview_object(self, key, path):
            assert RecordingPreview.objects.get(pk=preview.pk).write_pending
            raise CloudFailure("TRANSPORT_AMBIGUOUS", ambiguous=True)

    monkeypatch.setattr(previews, "storage_for", lambda source: FailedStorage())
    with pytest.raises(CloudFailure):
        previews.publish_files(preview, token, directory)
    acknowledge_stopped(preview.run_id, token)
    previews.revoke(RecordingPreview.objects.filter(pk=preview.pk))
    assert not previews.purge_preview(preview.pk)
    preview.refresh_from_db()
    assert preview.reserved_bytes == MAX_BYTES and preview.write_pending
    with pytest.raises(ValueError, match="RESTORE_PREVIEW_WRITE_UNCONFIRMED"):
        previews.purge_restored_previews()


def test_preview_rollback_requires_confirmed_byte_erasure(owner):
    from importlib import import_module

    from django.apps import apps
    from django.db.migrations.exceptions import IrreversibleError

    guard = import_module("backend.core.migrations.0024_recording_previews").guard_preview_erasure
    preview = RecordingPreview.objects.create(asset=asset(owner))
    with pytest.raises(IrreversibleError):
        guard(apps, None)
    RecordingPreview.objects.filter(pk=preview.pk).update(state="PURGED", reserved_bytes=0)
    guard(apps, None)
    RecordingPreview.objects.filter(pk=preview.pk).update(write_pending=True)
    with pytest.raises(IrreversibleError):
        guard(apps, None)


def test_controlled_gcs_preview_stream_is_bounded_create_only_and_generation_pinned(
    owner, tmp_path
):
    from backend.core.cloud import GooglePrivateStorage

    data = b"preview" * 20000
    path = tmp_path / "preview.mp4"
    path.write_bytes(data)
    source = asset(owner)
    key = f"{owner.pk}/{source.pk}/previews/{uuid4()}/preview.mp4"
    payload = {
        "bucket": "fixture-bucket",
        "name": key,
        "size": str(len(data)),
        "generation": "17",
        "md5Hash": base64.b64encode(hashlib.md5(data).digest()).decode(),
    }
    closed = []

    class Response:
        status_code = 200

        def iter_content(self, chunk_size):
            yield json.dumps(payload).encode()

        def close(self):
            closed.append(True)

    class Session:
        def request(self, method, url, **kwargs):
            assert (
                method == "POST"
                and url == "https://storage.googleapis.com/upload/storage/v1/b/fixture-bucket/o"
            )
            assert kwargs["params"] == {
                "uploadType": "media",
                "name": key,
                "ifGenerationMatch": "0",
            }
            assert kwargs["allow_redirects"] is False and kwargs["stream"] is True
            body = kwargs["data"]
            assert len(body) == len(data) and body.read(0) == b""
            chunks = []
            while chunk := body.read(1000000):
                assert len(chunk) <= 65536
                chunks.append(chunk)
            assert b"".join(chunks) == data
            return Response()

    storage = GooglePrivateStorage(Session(), "fixture-bucket", owner.pk, source.pk)
    assert storage.create_preview_object(key, path) == "17" and closed == [True]
    from backend.core.cloud import CloudFailure

    payload["md5Hash"] = "invalid"
    with pytest.raises(CloudFailure):
        storage.create_preview_object(key, path)
    with pytest.raises(ValueError):
        storage.create_preview_object(f"{owner.pk}/{source.pk}/source.mp4", path)
    with pytest.raises(ValueError):
        storage.delete_preview(f"{owner.pk}/{source.pk}/")


@pytest.mark.parametrize("reason", ["delete", "withdraw", "expire", "cancel"])
def test_revoke_playback_and_cleanup_retains_original_when_applicable(
    owner, tmp_path, monkeypatch, reason
):
    source, preview = ready(owner, tmp_path, monkeypatch)
    client = APIClient()
    client.force_authenticate(owner)
    response = client.get(f"/api/assets/{source.pk}/preview/media")
    chunks = iter(response.streaming_content)
    next(chunks)  # Bytes already prefetched/authorized cannot be revoked retroactively.
    if reason == "delete":
        try:
            delete_asset(owner, source.pk)
        except PermissionError:
            source.refresh_from_db()
            assert source.deleted_at and not source.purge_completed_at
    elif reason == "withdraw":
        record_consent(owner, "PROCESSING", "WITHDRAW", POLICY_VERSION, uuid4())
    elif reason == "expire":
        ReplayAsset.objects.filter(pk=source.pk).update(
            retain_until=timezone.now() - timedelta(seconds=1)
        )
    else:
        assert client.delete(f"/api/assets/{source.pk}/preview").status_code in {200, 503}
    time.sleep(0.55)
    with pytest.raises(ValueError):
        next(chunks)
    response.close()
    assert client.get(f"/api/assets/{source.pk}/preview/media").status_code == 404
    previews.reconcile_previews()
    preview.refresh_from_db()
    assert preview.state == "PURGED" and preview.reserved_bytes == 0
    if reason != "delete":
        assert private_path(source.storage_key).read_bytes() == b"owner-source"


def test_unconfirmed_write_or_execution_never_releases_storage(owner):
    source = asset(owner)
    preview = previews.enqueue_preview(owner, source.pk, uuid4())
    token = claim_run(preview.run_id)
    previews.revoke(RecordingPreview.objects.filter(pk=preview.pk))
    assert not previews.purge_preview(preview.pk)
    acknowledge_stopped(preview.run_id, token)
    RecordingPreview.objects.filter(pk=preview.pk).update(write_pending=True)
    assert not previews.purge_preview(preview.pk)
    preview.refresh_from_db()
    assert preview.reserved_bytes == MAX_BYTES


def test_restore_sweeps_known_and_post_backup_artifacts_without_original_loss(
    owner, tmp_path, monkeypatch, settings
):
    source, preview = ready(owner, tmp_path, monkeypatch)
    orphan = private_path(
        str(Path(source.storage_key).parent) + "/previews/post-backup/unknown.mp4"
    )
    orphan.parent.mkdir()
    orphan.write_bytes(b"post-backup bytes")
    settings.RESTORE_QUARANTINE = True
    from backend.core.recovery import apply_restore_controls

    monkeypatch.setattr("backend.core.recovery.verified_records", lambda: [])
    apply_restore_controls()
    preview.refresh_from_db()
    assert preview.state == "PURGED" and not orphan.exists()
    assert private_path(source.storage_key).read_bytes() == b"owner-source"
    assert not previews.preview_view(source)["media_url"]


def test_preview_upload_reserves_before_transfer_and_does_not_create_match(owner):
    data = b"untrusted-invalid-media"
    sha = hashlib.sha256(data).hexdigest()
    session = begin(
        owner,
        uuid4(),
        len(data),
        sha,
        base64.b64encode(hashlib.md5(data).digest()).decode(),
        {"preview_only": True, "unattributed_recording": True},
    )
    assert RecordingPreview.objects.get(asset=session.asset).reserved_bytes == MAX_BYTES
    write_chunk(owner, session.pk, 0, data)
    request_completion(owner, session.pk)
    verify(session.pk)
    session.refresh_from_db()
    assert session.state == "COMPLETE"
    assert RecordingPreview.objects.get(asset=session.asset).run.pipeline_version == PIPELINE
    assert not Match.objects.exists()


def test_restore_removes_unknown_local_asset_preview_but_preserves_its_original(owner):
    unknown = f"{owner.pk}/{uuid4()}/"
    original = private_path(unknown + "source.mp4")
    original.parent.mkdir(parents=True)
    original.write_bytes(b"untracked original")
    converted = private_path(unknown + f"previews/{uuid4()}/preview.mp4")
    converted.parent.mkdir(parents=True)
    converted.write_bytes(b"untracked derivative")
    assert not ReplayAsset.objects.exists()
    previews.purge_restored_previews()
    assert not converted.exists() and original.read_bytes() == b"untracked original"


@pytest.mark.parametrize(
    "mutation", ["source", "video", "timeline", "approval", "link", "quality", "shape"]
)
def test_forged_or_corrupt_bundle_is_rejected(tmp_path, mutation):
    root = tmp_path / "bundle"
    report = bundle(root, "a" * 64)
    if mutation == "source":
        report["source"]["sha256"] = "b" * 64
    elif mutation == "video":
        (root / "preview.mp4").write_bytes(b"changed")
    elif mutation == "timeline":
        (root / "timeline.json").write_text("{}")
    elif mutation == "approval":
        report["canonical_publication"] = True
    elif mutation == "quality":
        report["quality"]["gaps_over_limit"] = 0
    elif mutation == "shape":
        report["preservation"] = []
    else:
        (root / "extra").write_bytes(b"unexpected artifact")
    (root / "report.json").write_text(json.dumps(report))
    with pytest.raises(ValueError):
        validate_bundle(root, "a" * 64)


def test_output_stream_is_bounded_create_only_and_not_loaded_in_memory(tmp_path):
    output = tmp_path / "raw"
    result = run_bounded(
        [sys.executable, "-c", "import sys;sys.stdout.buffer.write(b'x'*65536)"],
        stdout_path=output,
        max_output=65536,
    )
    assert result.stdout == b"" and output.stat().st_size == 65536
    with pytest.raises(FileExistsError):
        run_bounded([sys.executable, "-c", "pass"], stdout_path=output)
    with pytest.raises(ValueError, match="OUTPUT_LIMIT"):
        run_bounded(
            [sys.executable, "-c", "print('x'*20000)"],
            stdout_path=tmp_path / "bounded",
            max_output=1000,
        )


def test_regular_descriptor_copy_refuses_directory(tmp_path):
    result = subprocess.run(
        [sys.executable, "-c", COPY_FILE, str(tmp_path), "100"], capture_output=True
    )
    assert result.returncode != 0 and result.stdout == b""


def test_sandbox_profile_has_no_host_output_mount():
    source = Path(__file__).resolve()
    argv = command("sha256:" + "a" * 64, "preview-fixture", source, source)
    assert "--detach" in argv and "--rm" not in argv and "3g" in argv and "--network" in argv
    assert argv[argv.index("--cpus") + 1] == "2"
    assert sum("type=bind" in item for item in argv) == 2
    assert "tools.sandbox_recording_preview" in argv


@pytest.mark.media
@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg absent")
def test_actual_hevc_vfr_upload_worker_private_playback_abstains(owner, tmp_path):
    from tests.test_recording_normalization import generate

    video = tmp_path / "actual.mp4"
    generate(video, codec="hevc", gaps=True, full_range=True)
    data = video.read_bytes()
    source = asset(owner, data, metadata={"unattributed_recording": True})
    preview = previews.enqueue_preview(owner, source.pk, uuid4())
    call_command("process_runs", once=True)
    preview.refresh_from_db()
    assert preview.state == "READY"
    assert preview.quality["gaps_over_limit"] == 1 and preview.quality["frame_count"] == 29
    assert preview.quality["precise_gameplay_analysis_approved"] is False
    client = APIClient()
    client.force_authenticate(owner)
    response = client.get(f"/api/assets/{source.pk}/preview/media", HTTP_RANGE="bytes=0-31")
    assert response.status_code == 206 and len(b"".join(response.streaming_content)) == 32
    response.close()
    assert file_hash(private_path(source.storage_key)) == source.source_sha256
    assert not Match.objects.exists() and not GameplayEvent.objects.exists()
