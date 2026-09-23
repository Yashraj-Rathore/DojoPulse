import json
import shutil
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

import pytest
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from analysis.process import run_bounded
from backend.core.evidence import as_opportunity, publish_annotations
from backend.core.jobs import claim_run, finish_run
from backend.core.models import (
    AnalysisRun,
    DefinitionVersion,
    GameBuild,
    GameplayEvent,
    Match,
    MatchContribution,
    MatchSourceRecord,
    Recommendation,
    ReplayAsset,
    ReplaySource,
)
from backend.core.recordings import attach_recording, review_recording
from backend.core.storage import delete_account, delete_asset, delete_metadata_match
from tests.test_backend import FakeStorage, reviewed_annotation
from tests.test_match_import import import_one

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(django_user_model, settings, tmp_path):
    settings.LOCAL_OPERATOR_UPLOADS = True
    settings.PRIVATE_DATA_ROOT = tmp_path / "private"
    owner = django_user_model.objects.create_user("attach-operator", is_staff=True)
    match = import_one(owner)[-1]
    build = GameBuild.objects.create(key="fixture", game=match.game, platform="synthetic")
    DefinitionVersion.objects.create(
        key="knowledge/1", kind="knowledge", game_build=build, payload={"synthetic_only": True}
    )
    client = APIClient()
    client.force_authenticate(owner)
    return owner, client, match


def metadata(match):
    opponent = match.participants.get(is_player=False).snapshot["identities"][0]
    return {
        "metadata_revision": match.metadata_revision,
        "player_namespace": match.player_identity.namespace,
        "player_id": match.player_identity.value,
        "player_slot": 1,
        "opponent_namespace": opponent["namespace"],
        "opponent_id": opponent["value"],
        "played_at": match.played_at.isoformat(),
        "game_build": "fixture",
        "session_id": "review-session",
        "source_kind": "ranked",
        "dataset_kind": "synthetic",
        "characters": ["jin", "jin"],
        "attribution_confirmed": True,
    }


def upload(client, match, *, claim=None, request_id=None, contents=b"synthetic-video-fixture"):
    return client.post(
        f"/api/matches/{match.pk}/recordings",
        {
            "file": SimpleUploadedFile("fixture.mp4", contents, content_type="video/mp4"),
            "metadata": json.dumps(claim or metadata(match)),
            "request_id": str(request_id or uuid4()),
            "processing_consent": "true",
        },
        format="multipart",
    )


def validated(response):
    assert response.status_code == 202, response.data
    run = AnalysisRun.objects.get(pk=response.data["run_id"])
    run.status = "REVIEW_REQUIRED"
    run.result = {"source": {"source_sha256": run.asset.source_sha256, "duration_seconds": 1}}
    run.save()
    return ReplaySource.objects.get(pk=response.data["source_id"]), run


def approve(owner, source):
    return review_recording(
        owner,
        source.pk,
        source.asset.source_sha256,
        "knowledge/1",
        "Synthetic attribution test, both players and chronology reviewed",
        confirm_reviewed=True,
    )


def publish(owner, match, run):
    annotation = reviewed_annotation()
    annotation.update(
        source_sha256=run.asset.source_sha256,
        played_at=match.played_at.isoformat(),
        session_id="review-session",
    )
    return publish_annotations(owner, run.pk, match.pk, annotation)


def test_attachment_preserves_canonical_match_until_review_then_publishes(setup):
    owner, client, match = setup
    before = Match.objects.values().get(pk=match.pk)
    assertion = deepcopy(match.source_records.get().assertion)
    source, run = validated(upload(client, match))
    assert Match.objects.count() == 1 and Match.objects.values().get(pk=match.pk) == before
    assert source.attribution_state == "PENDING_REVIEW" and not GameplayEvent.objects.exists()
    with pytest.raises(ValidationError, match="mismatch"):
        publish(owner, match, run)
    approve(owner, source)
    match.refresh_from_db()
    assert match.asset_id == source.asset_id and match.game_build == "fixture"
    assert match.knowledge_revision == "knowledge/1" and match.chronology_verified
    assert match.source_records.get().assertion == assertion
    publish(owner, match, run)
    assert MatchContribution.objects.count() == GameplayEvent.objects.count() == 1
    history = client.get("/api/matches").data["matches"][0]
    assert history["evidence_status"] == "VIDEO_ATTACHED"
    assert history["recordings"][0]["attribution_state"] == "APPROVED"


@pytest.mark.parametrize(
    "change",
    [
        {"player_id": "wrong"},
        {"player_slot": 2},
        {"opponent_id": "wrong"},
        {"played_at": "2026-09-02T00:00:00Z"},
        {"dataset_kind": "real"},
        {"metadata_revision": 9},
        {"characters": ["kazuya", "jin"]},
        {"attribution_confirmed": False},
    ],
)
def test_mismatch_rejected_before_any_asset_or_job(setup, change):
    _, client, match = setup
    claim = metadata(match)
    claim.update(change)
    assert upload(client, match, claim=claim).status_code == 400
    assert ReplayAsset.objects.count() == AnalysisRun.objects.count() == 0


def test_known_build_mode_and_session_mismatch_rejected(setup):
    _, client, match = setup
    original = metadata(match)
    for field, value in [
        ("game_build", "other-build"),
        ("mode", "practice"),
        ("session_id", "different-session"),
    ]:
        setattr(match, field, value)
        match.save()
        assert upload(client, match, claim=original).status_code == 400
        setattr(match, field, "unknown" if field == "mode" else None)
    assert not ReplayAsset.objects.exists()


def test_duplicate_request_is_idempotent_and_changed_bytes_fail(setup, settings):
    _, client, match = setup
    key = uuid4()
    first = upload(client, match, request_id=key)
    second = upload(client, match, request_id=key)
    assert first.status_code == second.status_code == 202
    assert first.data["source_id"] == second.data["source_id"]
    assert upload(client, match, request_id=key, contents=b"different").status_code == 400
    assert upload(client, match).status_code == 400
    assert ReplayAsset.objects.count() == AnalysisRun.objects.count() == 1
    assert len(list(settings.PRIVATE_DATA_ROOT.rglob("*.mp4"))) == 1


def test_owner_consent_and_local_operator_gates(setup, django_user_model, settings):
    owner, client, match = setup
    other = django_user_model.objects.create_user("other-operator", is_staff=True)
    client.force_authenticate(other)
    assert upload(client, match).status_code == 404
    client.force_authenticate(owner)
    settings.LOCAL_OPERATOR_UPLOADS = False
    assert upload(client, match).status_code == 403
    settings.LOCAL_OPERATOR_UPLOADS = True
    assert (
        client.post(f"/api/matches/{match.pk}/recordings", {}, format="multipart").status_code
        == 400
    )
    assert not ReplayAsset.objects.exists()


def test_review_requires_validated_hash_and_current_metadata(setup):
    owner, client, match = setup
    response = upload(client, match)
    source = ReplaySource.objects.get(pk=response.data["source_id"])
    with pytest.raises(ValidationError, match="validation"):
        approve(owner, source)
    source, _ = validated(response)
    with pytest.raises(ValidationError, match="hash"):
        review_recording(owner, source.pk, "0" * 64, "knowledge/1", "review", confirm_reviewed=True)
    with pytest.raises(ValidationError, match="Explicit"):
        review_recording(
            owner, source.pk, source.content_hash, "knowledge/1", "review", confirm_reviewed=False
        )
    Match.objects.filter(pk=match.pk).update(metadata_revision=2)
    with pytest.raises(ValidationError, match="changed"):
        approve(owner, source)


def test_real_attribution_requires_approved_build_specific_knowledge(setup):
    owner, client, match = setup
    match.dataset_kind = "real"
    match.save()
    claim = metadata(match)
    claim["dataset_kind"] = "real"
    source, _ = validated(upload(client, match, claim=claim))
    with pytest.raises(ValidationError, match="approved knowledge"):
        approve(owner, source)
    match.refresh_from_db()
    assert match.asset_id is None


def test_delete_recording_keeps_metadata_and_invalidates_old_evidence(setup):
    owner, client, match = setup
    source, run = validated(upload(client, match))
    approve(owner, source)
    match.refresh_from_db()
    publish(owner, match, run)
    event = GameplayEvent.objects.get()
    original_hash = as_opportunity(event).source_sha256
    recommendation = Recommendation.objects.create(
        owner=owner, situation="s", metric="m", baseline_event_ids=[str(event.pk)], summary={}
    )
    delete_asset(owner, source.asset_id, FakeStorage())
    match.refresh_from_db()
    event.refresh_from_db()
    recommendation.refresh_from_db()
    assert match.deleted_at is None and match.asset_id is None
    assert match.source_records.count() == 1 and match.participants.count() == 2
    assert as_opportunity(event).deleted and as_opportunity(event).source_sha256 == original_hash
    assert recommendation.state == "INVALIDATED" and not MatchContribution.objects.exists()
    assert client.get("/api/overview").status_code == 200
    row = client.get("/api/matches").data["matches"][0]
    assert row["evidence_status"] == "EVIDENCE_REQUIRED" and row["can_attach_recording"]
    replacement, _ = validated(upload(client, match, contents=b"replacement-recording"))
    approve(owner, replacement)
    event.refresh_from_db()
    assert as_opportunity(event).source_sha256 == original_hash


def test_pending_video_prevents_match_purge_and_account_delete_stops_late_jobs(setup):
    owner, client, match = setup
    source, run = validated(upload(client, match))
    with pytest.raises(ValidationError, match="attached recordings"):
        delete_metadata_match(owner, match.pk)
    AnalysisRun.objects.filter(pk=run.pk).update(status="QUEUED")
    token = claim_run(run.pk)
    delete_account(owner, FakeStorage())
    assert not finish_run(run.pk, token, {"status": "COMPLETED"})
    source.asset.refresh_from_db()
    assert source.asset.deleted_at and not MatchSourceRecord.objects.exists()
    assert not Match.objects.filter(deleted_at=None).exists()


def test_reprocess_reuses_asset_and_does_not_duplicate_events(setup):
    owner, client, match = setup
    source, run = validated(upload(client, match))
    approve(owner, source)
    match.refresh_from_db()
    publish(owner, match, run)
    url = f"/api/matches/{match.pk}/recordings/{source.pk}/reprocess"
    key = str(uuid4())
    first = client.post(url, {"request_id": key}, format="json")
    second = client.post(url, {"request_id": key}, format="json")
    assert first.status_code == second.status_code == 202
    assert first.data == second.data
    assert ReplayAsset.objects.count() == 1 and GameplayEvent.objects.count() == 1
    newer = AnalysisRun.objects.get(pk=first.data["run_id"])
    newer.status, newer.result = "REVIEW_REQUIRED", run.result
    newer.save()
    publish(owner, match, newer)
    assert GameplayEvent.objects.count() == 2 and MatchContribution.objects.count() == 1


def test_match_deleted_while_streaming_cannot_leave_an_orphan(setup, settings):
    owner, _, match = setup
    claim = metadata(match)

    class InterruptedUpload:
        name = "fixture.mp4"
        size = 4

        def chunks(self):
            # Exercise the interval between initial authorization and DB publication.
            delete_metadata_match(owner, match.pk)
            yield b"data"

    with pytest.raises(ObjectDoesNotExist):
        attach_recording(owner, match.pk, InterruptedUpload(), claim, uuid4())
    assert not ReplayAsset.objects.exists() and not AnalysisRun.objects.exists()
    assert not list(settings.PRIVATE_DATA_ROOT.rglob("*.mp4"))


def test_replacement_cannot_rewrite_historical_knowledge(setup):
    owner, client, match = setup
    source, run = validated(upload(client, match))
    approve(owner, source)
    match.refresh_from_db()
    publish(owner, match, run)
    delete_asset(owner, source.asset_id, FakeStorage())
    match.refresh_from_db()
    replacement, _ = validated(upload(client, match, contents=b"replacement"))
    DefinitionVersion.objects.create(
        key="knowledge/2", kind="knowledge", game_build_id="fixture", payload={}
    )
    with pytest.raises(ValidationError, match="Historical gameplay facts"):
        review_recording(
            owner,
            replacement.pk,
            replacement.content_hash,
            "knowledge/2",
            "review",
            confirm_reviewed=True,
        )
    match.refresh_from_db()
    assert match.knowledge_revision == "knowledge/1" and match.asset_id is None


def test_worker_rejects_changed_source_bytes(setup, monkeypatch):
    _, client, match = setup
    response = upload(client, match)
    monkeypatch.setattr(
        "backend.core.management.commands.process_runs.analyze",
        lambda *args: {
            "status": "REVIEW_REQUIRED",
            "source": {"source_sha256": "0" * 64},
            "opportunities": [],
        },
    )
    call_command("process_runs", once=True)
    run = AnalysisRun.objects.get(pk=response.data["run_id"])
    assert run.status == "FAILED" and run.result["issues"] == ["SOURCE_HASH_CHANGED"]
    assert run.asset.source_sha256 != "0" * 64
    assert not GameplayEvent.objects.exists()


@pytest.mark.media
@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg absent")
def test_attached_media_worker_and_retention_preserve_match(setup, tmp_path):
    owner, client, match = setup
    source_file = tmp_path / "synthetic.mp4"
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
            str(source_file),
        ]
    )
    response = upload(client, match, contents=source_file.read_bytes())
    assert response.status_code == 202
    call_command("process_runs", once=True)
    source = ReplaySource.objects.get(pk=response.data["source_id"])
    approve(owner, source)
    ReplayAsset.objects.filter(pk=source.asset_id).update(
        retain_until=timezone.now() - timedelta(seconds=1)
    )
    call_command("purge_expired")
    match.refresh_from_db()
    assert match.asset_id is None and match.deleted_at is None and match.source_records.exists()
