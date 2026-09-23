import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from backend.core.models import (
    AnalysisRun,
    DefinitionVersion,
    DrillAssignment,
    EvaluationPlan,
    Feedback,
    Match,
    NoticeReceipt,
    Profile,
    ReplayAsset,
)
from backend.core.storage import private_path
from tests.test_complete_loop import make_capture
from tests.test_match_import import import_one

pytestmark = pytest.mark.django_db


@pytest.fixture
def workspace(django_user_model, settings, tmp_path):
    settings.PRIVATE_DATA_ROOT = tmp_path / "private"
    owner = django_user_model.objects.create_user(
        "experience", password="test-password", is_staff=True, email="private@example.test"
    )
    other = django_user_model.objects.create_user("other-experience", is_staff=True)
    asset, events, _ = make_capture(owner, datetime(2026, 9, 1, 23, 59, tzinfo=UTC), "ranked", 1, 3)
    foreign, foreign_events, _ = make_capture(
        other, datetime(2026, 9, 2, tzinfo=UTC), "practice", 1, 2
    )
    path = private_path(asset.storage_key)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"0123456789")
    client = APIClient()
    client.force_authenticate(owner)
    return owner, client, asset, events, other, foreign_events


def test_preferences_persist_and_do_not_grant_training_consent(workspace):
    owner, client, *_ = workspace
    first = client.get("/api/preferences")
    assert first.status_code == 200 and first.data["display_timezone"] == "UTC"
    result = client.patch(
        "/api/preferences",
        {
            "complete_onboarding": True,
            "display_timezone": "browser",
            "analysis_notices": False,
            "training_consent_at": "invented",
        },
        format="json",
    )
    assert result.status_code == 200 and result.data["onboarding_completed_at"]
    profile = Profile.objects.get(user=owner)
    assert not profile.analysis_notices and profile.training_consent_at is None
    assert client.get("/api/preferences").data["display_timezone"] == "browser"
    assert (
        client.patch("/api/preferences", {"display_timezone": "invalid"}, format="json").status_code
        == 400
    )
    assert first["Cache-Control"] == "private, no-store"


def test_evidence_filters_pagination_and_no_cross_owner_or_private_review_data(workspace):
    _, client, _, events, _, foreign = workspace
    first = client.get(
        "/api/evidence?limit=2&date_from=2026-09-01&date_to=2026-09-01&character=jin"
    )
    assert first.status_code == 200 and first.data["total"] == 3 and first.data["next_offset"] == 2
    assert len(client.get("/api/evidence?offset=2&limit=2").data["events"]) == 1
    success = client.get("/api/evidence?outcome=SUCCESS&mode=ranked")
    assert success.data["total"] == 1 and success.data["events"][0]["id"] == events[0].pk
    assert client.get("/api/evidence?date_from=2026-09-02").data["total"] == 0
    assert client.get(f"/api/evidence?match={foreign[0].match_id}").status_code == 404
    assert all("reviews" not in row and "storage_key" not in row for row in first.data["events"])
    assert client.get("/api/evidence?date_from=2026-09-02&date_to=2026-09-01").status_code == 400
    assert client.get("/api/evidence?date_to=9999-12-31").status_code == 400


def test_disputed_events_visible_but_not_selectable_or_searchable_as_success(workspace):
    _, client, _, events, *_ = workspace
    Match.objects.filter(pk=events[0].match_id).update(metadata_state="REVIEW_REQUIRED")
    result = client.get("/api/evidence")
    assert result.data["total"] == 3
    assert not any(row["selectable"] for row in result.data["events"])
    assert client.get("/api/matches?outcome=SUCCESS").data["total"] == 0


def test_match_filters_keep_metadata_separate_from_gameplay(workspace):
    owner, client, _, _, *_ = workspace
    import_one(owner)
    assert client.get("/api/matches?evidence=METADATA").data["total"] == 1
    assert (
        client.get("/api/matches?evidence=VIDEO&character=jin&outcome=FAILURE").data["total"] == 1
    )
    assert client.get("/api/matches?evidence=METADATA&outcome=FAILURE").data["total"] == 0
    assert client.get("/api/matches?date_from=2026-09-02&mode=ranked").data["total"] == 0


def test_feedback_is_local_idempotent_owner_scoped_and_does_not_relabel(workspace):
    owner, client, _, events, _, foreign = workspace
    body = {
        "request_id": str(uuid4()),
        "category": "CORRECTION",
        "message": "Please review this event",
        "event_id": str(events[0].pk),
    }
    first = client.post("/api/feedback", body, format="json")
    second = client.post("/api/feedback", body, format="json")
    assert (
        first.status_code == 201
        and second.status_code == 200
        and first.data["id"] == second.data["id"]
    )
    assert Feedback.objects.filter(owner=owner).count() == 1
    assert (
        client.post(
            "/api/feedback", {**body, "message": "A different request"}, format="json"
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/feedback",
            {**body, "request_id": str(uuid4()), "event_id": str(foreign[0].pk)},
            format="json",
        ).status_code
        == 404
    )
    events[0].refresh_from_db()
    assert events[0].outcome == "SUCCESS" and events[0].verified
    assert client.get("/api/feedback").data["feedback"][0]["message"] == body["message"]


def test_notices_survive_refresh_dismissal_and_preferences(workspace):
    owner, client, asset, *_ = workspace
    AnalysisRun.objects.filter(asset=asset).update(status="REVIEW_REQUIRED")
    first = client.get("/api/notices").data["notices"]
    assert len(first) == 1
    assert client.get("/api/notices").data["notices"] == first
    assert (
        client.post("/api/notices", {"key": "run:someone-else"}, format="json").status_code == 400
    )
    client.patch("/api/preferences", {"analysis_notices": False}, format="json")
    assert client.get("/api/notices").data["notices"] == []
    client.patch("/api/preferences", {"analysis_notices": True}, format="json")
    for _ in range(2):
        assert (
            client.post("/api/notices", {"key": first[0]["key"]}, format="json").status_code == 200
        )
    assert NoticeReceipt.objects.filter(owner=owner).count() == 1
    assert client.get("/api/notices").data["notices"] == []
    AnalysisRun.objects.filter(asset=asset).update(status="FAILED")
    assert len(client.get("/api/notices").data["notices"]) == 1


def test_practice_and_followup_notices_follow_persistent_plan_state(workspace, monkeypatch):
    owner, client, *_ = workspace
    drill = DefinitionVersion.objects.create(
        key="notice-drill", kind="drill", status="APPROVED", payload={"synthetic_only": True}
    )
    assignment = DrillAssignment.objects.create(owner=owner, drill=drill)
    EvaluationPlan.objects.create(
        owner=owner,
        assignment=assignment,
        specification={
            "followup_start": "2026-10-01T00:00:00Z",
            "followup_end": "2026-10-10T00:00:00Z",
        },
    )
    monkeypatch.setattr(
        "backend.core.experience_api.timezone.now", lambda: datetime(2026, 9, 30, tzinfo=UTC)
    )
    initial = client.get("/api/notices").data["notices"]
    assert [n["category"] for n in initial].count("practice") == 1
    assert not any(n["category"] == "followup" for n in initial)
    monkeypatch.setattr(
        "backend.core.experience_api.timezone.now", lambda: datetime(2026, 10, 1, tzinfo=UTC)
    )
    opened = next(
        n for n in client.get("/api/notices").data["notices"] if n["category"] == "followup"
    )
    client.post("/api/notices", {"key": opened["key"]}, format="json")
    assert not any(n["category"] == "followup" for n in client.get("/api/notices").data["notices"])
    assignment.status = "PRACTICED"
    assignment.save()
    monkeypatch.setattr(
        "backend.core.experience_api.timezone.now", lambda: datetime(2026, 10, 10, tzinfo=UTC)
    )
    ended = client.get("/api/notices").data["notices"]
    assert not any(n["category"] == "practice" for n in ended)
    assert any(n["key"].endswith(":ended") for n in ended)


def test_export_allowlist_excludes_secrets_paths_other_people_and_deleted_media(workspace):
    owner, client, asset, events, other, foreign = workspace
    asset.upload_session = "secret-upload-token"
    asset.metadata = {"private": "raw-provider-secret"}
    asset.save()
    result = client.get("/api/account/export")
    assert result.status_code == 200 and result["Cache-Control"] == "private, no-store"
    data = json.loads(result.content)
    assert data["schema"] == "dojopulse-export/1" and len(data["events"]) == 3
    encoded = result.content.decode()
    for forbidden in (
        other.username,
        str(foreign[0].pk),
        asset.storage_key,
        asset.upload_session,
        "raw-provider-secret",
        owner.password,
    ):
        assert forbidden not in encoded
    assert not data["media_included"] and data["username"] == owner.username


def test_delete_requires_password_and_confirmation_then_logs_out_and_purges(workspace):
    owner, client, asset, *_ = workspace
    client.force_authenticate(user=None)
    assert client.login(username=owner.username, password="test-password")
    assert (
        client.delete(
            "/api/account",
            {"password": "wrong", "confirmation": "DELETE MY WORKSPACE"},
            format="json",
        ).status_code
        == 400
    )
    assert (
        client.delete("/api/account", {"password": "test-password"}, format="json").status_code
        == 400
    )
    result = client.delete(
        "/api/account",
        {"password": "test-password", "confirmation": "DELETE MY WORKSPACE"},
        format="json",
    )
    assert result.status_code == 202 and not result.data["purge_pending"]
    owner.refresh_from_db()
    asset.refresh_from_db()
    assert not owner.is_active and not owner.has_usable_password() and not owner.email
    assert asset.purge_completed_at and not private_path(asset.storage_key).exists()
    assert client.get("/api/account/export").status_code == 403


def test_account_file_failure_tombstones_all_assets_for_retry(workspace, monkeypatch):
    owner, client, asset, *_ = workspace
    second = ReplayAsset.objects.create(owner=owner, storage_key=f"{owner.pk}/{uuid4()}/source.mp4")
    from backend.core.storage import LocalStorage

    original = LocalStorage.delete_asset

    def fail(*args):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(LocalStorage, "delete_asset", fail)
    response = client.delete(
        "/api/account",
        {"password": "test-password", "confirmation": "DELETE MY WORKSPACE"},
        format="json",
    )
    assert response.status_code == 202 and response.data["purge_pending"]
    assert ReplayAsset.objects.filter(owner=owner, deleted_at=None).count() == 0
    monkeypatch.setattr(LocalStorage, "delete_asset", original)
    call_command("purge_expired")
    second.refresh_from_db()
    asset.refresh_from_db()
    assert second.purge_completed_at and asset.purge_completed_at


@pytest.mark.parametrize(
    "header, status, content",
    [
        ("bytes=2-5", 206, b"2345"),
        ("bytes=-3", 206, b"789"),
        ("bytes=8-", 206, b"89"),
        ("bytes=0-999", 206, b"0123456789"),
        ("bytes=100-200", 416, b""),
        ("bytes=2-1", 416, b""),
        ("bytes=0-1,3-4", 416, b""),
    ],
)
def test_private_timeline_range_playback(workspace, header, status, content):
    _, client, asset, *_ = workspace
    response = client.get(f"/api/assets/{asset.pk}/media", HTTP_RANGE=header)
    assert response.status_code == status and response["Accept-Ranges"] == "bytes"
    actual = b"".join(response.streaming_content) if response.streaming else response.content
    assert actual == content
    assert response["Cache-Control"] == "private, no-store"


def test_all_new_mutations_require_csrf_and_anonymous_access_is_denied(workspace):
    owner, _, _, *_ = workspace
    client = APIClient(enforce_csrf_checks=True)
    for endpoint in ("preferences", "evidence", "feedback", "notices", "account/export"):
        assert client.get("/api/" + endpoint).status_code == 403
    assert client.login(username=owner.username, password="test-password")
    assert (
        client.patch("/api/preferences", {"analysis_notices": False}, format="json").status_code
        == 403
    )
    assert client.post("/api/feedback", {}, format="json").status_code == 403
    assert client.post("/api/notices", {}, format="json").status_code == 403
    assert client.delete("/api/account", {}, format="json").status_code == 403
