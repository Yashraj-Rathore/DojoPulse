from dataclasses import replace
from unittest.mock import patch

import pytest
from django.core import signing
from django.utils import timezone
from rest_framework.test import APIClient

from backend.core.match_api import SELECTION_SALT
from backend.core.match_worker import process_batch
from backend.core.models import (
    GameplayEvent,
    Match,
    MatchSourceRecord,
    MatchSync,
    PlayerGameIdentity,
)
from ingestion.synthetic import PLAYER

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(django_user_model, settings):
    settings.DEBUG = True
    settings.LOCAL_MATCH_IMPORTS = True
    return django_user_model.objects.create_user("history-operator", is_staff=True)


@pytest.fixture
def client(user):
    api = APIClient()
    api.force_authenticate(user)
    return api


def candidate(client, provider="synthetic-a"):
    response = client.post(
        "/api/player-candidates", {"provider": provider, "query": PLAYER.value}, format="json"
    )
    assert response.status_code == 200
    return response.data["candidates"][0]


def linked(client):
    response = client.post(
        "/api/player-identities",
        {
            "selection_token": candidate(client)["selection_token"],
            "processing_consent": True,
        },
        format="json",
    )
    assert response.status_code == 201
    return response.data["id"]


def queued(client):
    identity = linked(client)
    response = client.post(f"/api/player-identities/{identity}/sync", {}, format="json")
    assert response.status_code == 202
    return identity, response.data["id"]


def test_link_queue_worker_history_complete_flow(client):
    identity, job = queued(client)
    assert not Match.objects.exists()  # Requests queue work; they don't call adapters.
    assert process_batch() == 2
    response = client.get("/api/matches")
    assert response.status_code == 200 and response["Cache-Control"] == "private, no-store"
    assert response.data["total"] == 2
    row = response.data["matches"][0]
    assert row["identity_id"] == identity and row["result"] == "WIN"
    assert row["game_build"] is row["character"] is None
    assert row["dataset_kind"] == "synthetic" and row["evidence_status"] == "EVIDENCE_REQUIRED"
    assert row["source"]["provider"] == "synthetic-a"
    assert "assertion" not in row["source"] and "storage_key" not in str(response.data)
    assert client.get(f"/api/match-syncs/{job}").data["status"] == "COMPLETE"
    assert not GameplayEvent.objects.exists()
    assert (
        client.post(f"/api/player-identities/{identity}/sync", {}, format="json").status_code == 202
    )
    assert process_batch() == 2 and Match.objects.count() == MatchSourceRecord.objects.count() == 2


def test_selection_requires_consent_and_rejects_tampering_expiry(client):
    token = candidate(client)["selection_token"]
    assert (
        client.post(
            "/api/player-identities",
            {"selection_token": token, "processing_consent": False},
            format="json",
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/player-identities",
            {"selection_token": token + "changed", "processing_consent": True},
            format="json",
        ).status_code
        == 400
    )
    with patch("django.core.signing.time.time", return_value=timezone.now().timestamp() - 600):
        expired = signing.dumps({"owner": "unused"}, salt=SELECTION_SALT)
    assert (
        client.post(
            "/api/player-identities",
            {"selection_token": expired, "processing_consent": True},
            format="json",
        ).status_code
        == 400
    )
    assert not PlayerGameIdentity.objects.exists()


def test_name_search_and_unknown_id_are_explicit(client):
    response = client.post(
        "/api/player-candidates",
        {"provider": "synthetic-a", "query": "someone", "kind": "RESOLVE_NAME"},
        format="json",
    )
    assert response.status_code == 400 and response.data["code"] == "OPERATION_UNSUPPORTED"
    response = client.post(
        "/api/player-candidates", {"provider": "synthetic-a", "query": "unknown"}, format="json"
    )
    assert response.data == {"candidates": []}


def test_provider_gates_cannot_be_bypassed(client, user, settings):
    for provider in ["ewgf-public", "wavu", "tekken-undocumented-candidate", "https://example.com"]:
        assert (
            client.post(
                "/api/player-candidates",
                {"provider": provider, "query": PLAYER.value},
                format="json",
            ).status_code
            == 400
        )
    token = candidate(client)["selection_token"]
    settings.LOCAL_MATCH_IMPORTS = False
    assert not any(item["enabled"] for item in client.get("/api/match-providers").data["providers"])
    assert (
        client.post(
            "/api/player-identities",
            {"selection_token": token, "processing_consent": True},
            format="json",
        ).status_code
        == 400
    )
    settings.LOCAL_MATCH_IMPORTS = True
    settings.DEBUG = False
    assert not any(item["enabled"] for item in client.get("/api/match-providers").data["providers"])
    settings.DEBUG = True
    user.is_staff = False
    user.save()
    assert (
        client.post(
            "/api/player-candidates",
            {"provider": "synthetic-a", "query": PLAYER.value},
            format="json",
        ).status_code
        == 400
    )


def test_cross_owner_selection_identity_history_and_jobs(client, django_user_model):
    selection = candidate(client)
    identity, job = queued(client)
    process_batch()
    match = Match.objects.first()
    other = django_user_model.objects.create_user("another-history-operator", is_staff=True)
    client.force_authenticate(other)
    assert (
        client.post(
            "/api/player-identities",
            {"selection_token": selection["selection_token"], "processing_consent": True},
            format="json",
        ).status_code
        == 400
    )
    assert client.get("/api/matches").data["total"] == 0
    assert client.get("/api/player-identities").data["identities"] == []
    for path, method in [
        (f"player-identities/{identity}/sync", "post"),
        (f"player-identities/{identity}", "delete"),
        (f"match-syncs/{job}", "get"),
        (f"matches/{match.pk}", "delete"),
        (f"matches?identity={identity}", "get"),
    ]:
        assert getattr(client, method)(f"/api/{path}").status_code == 404


def test_pagination_filter_and_provider_choice(client):
    identity, _ = queued(client)
    process_batch()
    assert (
        client.post(
            f"/api/player-identities/{identity}/sync", {"provider": "synthetic-b"}, format="json"
        ).status_code
        == 202
    )
    process_batch()
    first = client.get(f"/api/matches?identity={identity}&limit=2").data
    second = client.get(f"/api/matches?identity={identity}&limit=2&offset=2").data
    assert first["total"] == 4 and first["next_offset"] == 2 and second["next_offset"] is None
    assert not {r["id"] for r in first["matches"]} & {r["id"] for r in second["matches"]}
    assert client.get("/api/matches?limit=1000").status_code == 400
    assert client.get("/api/matches?offset=-1").status_code == 400


def test_stop_sync_retains_history_and_prevents_new_imports(client):
    identity, job = queued(client)
    process_batch()
    assert client.delete(f"/api/player-identities/{identity}").status_code == 200
    assert client.get("/api/matches").data["total"] == 2
    assert (
        client.post(f"/api/player-identities/{identity}/sync", {}, format="json").status_code == 404
    )
    assert client.get(f"/api/match-syncs/{job}").data["status"] == "CANCELLED"
    assert process_batch() == 0


def test_remove_match_exposes_revocation_and_filters_deleted_history(client):
    identity, _ = queued(client)
    process_batch()
    match = Match.objects.first()
    assert client.delete(f"/api/matches/{match.pk}").data["identity_sync_revoked"]
    assert client.get("/api/matches").data["total"] == 1
    assert not MatchSourceRecord.objects.filter(match=match).exists()
    assert not client.get("/api/player-identities").data["identities"][0]["can_sync"]


def test_worker_schema_failure_quarantines_without_checkpoint(client):
    _, job_id = queued(client)
    from ingestion.synthetic import SyntheticProvider

    discover = SyntheticProvider.discover_matches

    def invalid(self, *args):
        page = discover(self, *args)
        return replace(page, matches=(replace(page.matches[0], game="wrong"),))

    with patch.object(SyntheticProvider, "discover_matches", invalid):
        assert process_batch() == 0
    job = MatchSync.objects.get(pk=job_id)
    assert job.status == "ATTENTION_REQUIRED" and job.checkpoint is None and job.coverage == []
    assert not Match.objects.exists()


def test_worker_failure_waits_and_disabled_worker_makes_no_calls(client, settings):
    queued(client)
    settings.LOCAL_MATCH_IMPORTS = False
    with patch("backend.core.match_worker.SyntheticProvider") as adapter:
        assert process_batch() == 0
        adapter.assert_not_called()
    settings.LOCAL_MATCH_IMPORTS = True
    with patch("ingestion.synthetic.SyntheticProvider.discover_matches", side_effect=OSError):
        assert process_batch() == 0
    job = MatchSync.objects.get()
    assert job.status == "PENDING" and job.next_attempt_at > timezone.now()
    assert job.coverage == [] and process_batch() == 0


def test_authentication_and_csrf_required(user):
    client = APIClient(enforce_csrf_checks=True)
    assert client.get("/api/matches").status_code == 403
    client.force_login(user)
    assert client.get("/api/matches").status_code == 200
    assert (
        client.post(
            "/api/player-candidates",
            {"provider": "synthetic-a", "query": PLAYER.value},
            format="json",
        ).status_code
        == 403
    )


def test_history_preserves_earlier_page_gaps_and_hides_unreviewed_result(client):
    _, job_id = queued(client)
    process_batch()
    job = MatchSync.objects.get(pk=job_id)
    job.coverage[0].update(coverage="PARTIAL", gaps=["earlier page incomplete"], truncated=True)
    job.save(update_fields=["coverage"])
    Match.objects.update(metadata_state="REVIEW_REQUIRED")
    response = client.get("/api/matches")
    coverage = response.data["syncs"][0]["coverage"]
    assert coverage["coverage"] == "PARTIAL" and coverage["truncated"]
    assert coverage["gaps"] == ["earlier page incomplete"]
    assert all(row["result"] == "UNKNOWN" for row in response.data["matches"])
