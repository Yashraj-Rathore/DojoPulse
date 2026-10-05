"""M10 thresholds, provenance, current publications, privacy and separated history."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from analysis.player_model import diagnose, priority_assessment, rank_cards
from backend.core.evidence import as_opportunity, publish_annotations
from backend.core.models import (
    AnalysisRun,
    DefinitionVersion,
    GameplayEvent,
    Match,
    Participant,
    Profile,
)
from backend.core.storage import delete_asset
from tests.test_backend import FakeStorage
from tests.test_complete_loop import TARGET, make_capture

pytestmark = pytest.mark.django_db
START = datetime(2026, 8, 1, tzinfo=UTC)
ASSESSMENT = {
    "version": "priority-assessment/1",
    "value": 0.7,
    "trainability": 0.8,
    "rationale": "Synthetic relative assessment for software qualification only.",
}
FILTERS = "dataset_kind=synthetic&date_from=2026-08-01&date_to=2026-08-31"


@pytest.fixture
def model_env(django_user_model):
    owner = django_user_model.objects.create_user("diagnosis-owner", is_staff=True)
    rows = []
    for i in range(5):
        rows.append(make_capture(owner, START + timedelta(days=i), "ranked", 1))
    drill = DefinitionVersion.objects.create(
        key="diagnosis-drill/1",
        kind="drill",
        status="APPROVED",
        payload={
            "synthetic_only": True,
            "game_build": "fixture",
            "situation_definition": TARGET,
            "metric_definition": "punish-success/v1",
            "knowledge_revision": "knowledge/1",
            "title": "Synthetic response drill",
            "priority_assessment": ASSESSMENT,
        },
    )
    client = APIClient()
    client.force_authenticate(owner)
    return owner, rows, drill, client


def model(client, query=FILTERS):
    response = client.get("/api/player-model?" + query)
    assert response.status_code == 200, response.data
    assert response["Cache-Control"] == "private, no-store"
    return response.data


def observations(rows):
    return [as_opportunity(e) for _, events, _ in rows for e in events]


def assess(events, **overrides):
    return diagnose(
        events,
        **{
            "independent_reviews": len(events),
            "review_agreement": 1.0,
            "assessment": ASSESSMENT,
            "supported": True,
            **overrides,
        },
    )


def test_complete_projection_score_and_separate_result_history(model_env):
    _, rows, drill, client = model_env
    match = rows[0][1][0].match
    Participant.objects.create(match=match, slot=1, is_player=True, character="jin")
    Match.objects.filter(pk=match.pk).update(winner_slot=1)
    data = model(client)
    card = data["cards"][0]
    assert card["state"] == "OBSERVED_FAILURE_PATTERN" and card["priority_rank"] == 1
    assert card["summary"]["numerator"] == 5 and card["summary"]["denominator"] == 50
    assert card["summary"]["sessions"] == 5 and card["review"]["agreement"] == 1
    assert card["score"] == pytest.approx(card["factors"]["certainty"] * 0.7 * 0.8)
    assert card["assessment_drill"]["content_hash"] == drill.content_hash
    assert len(card["evidence"]) == 5 and card["evidence_total"] == 50
    assert all(e["outcome"] == "FAILURE" for e in card["evidence"])
    assert card["trends"][0]["summary"] == card["summary"]
    assert len(card["policy_hash"]) == len(card["evidence_hash"]) == 64
    assert data["history"]["summary"]["wins"] == 1
    assert data["history"]["summary"]["unknown"] == 4
    assert data["history"]["summary"]["win_rate"] == 1
    assert data["release_approved"] is False and card["release_approved"] is False


def test_thresholds_sessions_coverage_unknowns_and_exclusions(model_env):
    _, rows, _, _ = model_env
    events = observations(rows)
    assert assess(events[:39])["state"] == "INSUFFICIENT_EVIDENCE"
    assert (
        assess([replace(e, session_id="one") for e in events])["state"] == "INSUFFICIENT_EVIDENCE"
    )
    unknown = [replace(e, outcome="UNKNOWN") for e in events[:6]] + events[6:]
    result = assess(unknown)
    assert result["state"] == "INSUFFICIENT_EVIDENCE"
    assert result["summary"]["eligible_unknown"] == 6 and result["summary"]["denominator"] == 44
    uncertain = [replace(e, eligibility="UNKNOWN", outcome="UNKNOWN") for e in events[:6]] + events[
        6:
    ]
    assert "ELIGIBILITY_COVERAGE" in assess(uncertain)["reasons"]
    excluded = events + [
        replace(
            events[0],
            id="excluded",
            played_key="excluded",
            eligibility="INELIGIBLE",
            outcome="UNKNOWN",
        )
    ]
    assert assess(excluded)["factors"]["frequency"] == 50 / 51
    assert assess(excluded)["summary"]["excluded"] == 1


def test_low_agreement_missing_assessment_real_gate_and_success_pattern(model_env):
    events = observations(model_env[1])
    assert assess(events, review_agreement=0.79)["state"] == "REVIEW_REQUIRED"
    assert assess(events, independent_reviews=49)["state"] == "REVIEW_REQUIRED"
    assert assess(events, assessment=None)["score"] is None
    assert assess(events, supported=False)["state"] == "UNSUPPORTED_SCOPE"
    assert (
        assess([replace(e, dataset_kind="real") for e in events])["state"]
        == "REAL_VALIDATION_PENDING"
    )
    assert (
        assess([replace(e, outcome="SUCCESS") for e in events])["state"]
        == "NO_CLEAR_FAILURE_PATTERN"
    )


def test_mixed_duplicate_deleted_and_practice_evidence_rejected(model_env):
    events = observations(model_env[1])
    for changed in (
        replace(events[0], game_build="other"),
        replace(events[0], mode="practice"),
        replace(events[0], deleted=True),
    ):
        with pytest.raises(ValueError):
            assess([changed, *events[1:]])
    with pytest.raises(ValueError, match="Duplicate"):
        assess([*events, events[0]])


@pytest.mark.parametrize("value", [True, -1, 1.1, float("nan"), float("inf"), "0.5"])
def test_invalid_reviewed_assessment_fractions(value):
    with pytest.raises(ValueError):
        priority_assessment({**ASSESSMENT, "value": value})


def test_ranking_is_deterministic_bounded_and_missing_scores_stay_unranked():
    cards = [
        {"id": x, "score": score}
        for x, score in [("d", 0.4), ("b", 0.8), ("a", 0.8), ("c", 0.5), ("unknown", None)]
    ]
    ranked = rank_cards(cards)
    assert [c["id"] for c in ranked] == ["a", "b", "c", "d", "unknown"]
    assert [c["priority_rank"] for c in ranked] == [1, 2, 3, None, None]


def test_reanalysis_replaces_counts_and_changes_evidence_hash(model_env):
    owner, rows, _, client = model_env
    before = model(client)["cards"][0]
    asset, events, annotation = rows[0]
    run = AnalysisRun.objects.create(
        owner=owner,
        asset=asset,
        request_key=uuid4().hex,
        result={"source": {"duration_seconds": 60}},
    )
    publish_annotations(owner, run.pk, events[0].match_id, annotation)
    after = model(client)["cards"][0]
    assert after["summary"] == before["summary"]
    assert after["evidence_hash"] != before["evidence_hash"]
    assert after["evidence_total"] == 50


def test_source_deletion_expiry_and_drill_withdrawal_recompute(model_env):
    owner, rows, drill, client = model_env
    delete_asset(owner, rows[0][0].pk, FakeStorage())
    card = model(client)["cards"][0]
    assert card["summary"]["denominator"] == 40 and card["state"] == "INSUFFICIENT_EVIDENCE"
    rows[1][0].retain_until = timezone.now() - timedelta(seconds=1)
    rows[1][0].save(update_fields=["retain_until"])
    data = model(client)
    assert data["cards"][0]["summary"]["denominator"] == 30
    assert data["unavailable_events"]["WITHDRAWN_EXPIRED_OR_DISPUTED"] == 10
    DefinitionVersion.objects.filter(pk=drill.pk).update(status="WITHDRAWN")
    assert model(client)["cards"][0]["drills"] == []


def test_ownership_default_real_and_processing_withdrawal(model_env, django_user_model):
    owner, _, _, client = model_env
    other = django_user_model.objects.create_user("foreign-diagnosis", is_staff=True)
    make_capture(other, START, "ranked", 9)
    assert model(client)["cards"][0]["summary"]["denominator"] == 50
    assert model(client, "date_from=2026-08-01&date_to=2026-08-31")["cards"] == []
    anonymous = APIClient()
    assert anonymous.get("/api/player-model").status_code in (401, 403)
    Profile.objects.create(user=owner, processing_withdrawn_at=timezone.now())
    assert client.get("/api/player-model?" + FILTERS).status_code == 400


@pytest.mark.parametrize(
    "query",
    [
        "outcome=SUCCESS",
        "eligibility=ELIGIBLE",
        "mode=practice",
        "date_from=2027-01-01&date_to=2026-01-01",
        "date_from=2020-01-01&date_to=2026-01-01",
        "date_to=0001-01-01",
        "dataset_kind=synthetic&dataset_kind=real",
        "unknown=yes",
        "offset=-1",
    ],
)
def test_invalid_and_favorable_subselection_filters_rejected(model_env, query):
    assert model_env[3].get("/api/player-model?" + query).status_code == 400


def test_metadata_only_practice_and_disputed_result_never_become_gameplay(model_env):
    owner, rows, _, client = model_env
    make_capture(owner, START, "practice", 0, 40)
    metadata = Match.objects.create(
        owner=owner, played_at=START, mode="ranked", dataset_kind="synthetic", winner_slot=2
    )
    Participant.objects.create(match=metadata, slot=1, is_player=True)
    Match.objects.filter(pk=rows[0][1][0].match_id).update(
        metadata_state="REVIEW_REQUIRED", winner_slot=1
    )
    data = model(client)
    assert data["cards"][0]["summary"]["denominator"] == 40
    assert data["history"]["summary"]["matches"] == 6
    assert data["history"]["summary"]["losses"] == 1
    assert data["capture_inventory"]["without_publication"] == 1


def test_version_groups_and_filters_do_not_pool_or_rank_incompatible_scopes(model_env):
    owner, _, _, client = model_env
    _, events, _ = make_capture(owner, START, "ranked", 0)
    Match.objects.filter(pk=events[0].match_id).update(game_build="fixture-two")
    data = model(client)
    assert data["card_total"] == 2 and data["ranking_state"] == "MIXED_MEASUREMENT_SCOPES"
    assert all(c["priority_rank"] is None for c in data["cards"])
    assert sorted(c["summary"]["denominator"] for c in data["cards"]) == [10, 50]
    assert model(client, FILTERS + "&game_build=fixture")["cards"][0]["priority_rank"] == 1
    assert model(client, FILTERS + "&knowledge_revision=unknown")["cards"] == []


def test_missing_and_ambiguous_priority_assessments_never_get_default_weights(model_env):
    _, _, drill, client = model_env
    second = DefinitionVersion.objects.create(
        key="second-drill/1", kind="drill", status="APPROVED", payload=drill.payload
    )
    card = model(client)["cards"][0]
    assert card["score"] is None and "AMBIGUOUS_PRIORITY_ASSESSMENT" in card["reasons"]
    DefinitionVersion.objects.filter(pk__in=[drill.pk, second.pk]).update(status="WITHDRAWN")
    assert model(client)["cards"][0]["factors"]["value"] is None


def test_unreviewed_windows_block_diagnosis_and_bounded_scope_fails_closed(model_env, monkeypatch):
    _, rows, _, client = model_env
    GameplayEvent.objects.filter(pk=rows[0][1][0].pk).update(review={})
    assert model(client)["cards"][0]["state"] == "REVIEW_REQUIRED"
    monkeypatch.setattr("backend.core.player_model.MAX_MATCHES", 1)
    assert client.get("/api/player-model?" + FILTERS).status_code == 400


def test_event_group_and_drill_bounds_fail_without_silent_cutoffs(model_env, monkeypatch):
    owner, _, drill, client = model_env
    monkeypatch.setattr("backend.core.player_model.MAX_EVENTS", 1)
    assert client.get("/api/player-model?" + FILTERS).status_code == 400
    monkeypatch.setattr("backend.core.player_model.MAX_EVENTS", 20000)
    _, events, _ = make_capture(owner, START, "ranked", 0)
    Match.objects.filter(pk=events[0].match_id).update(game_build="fixture-two")
    monkeypatch.setattr("backend.core.player_model.MAX_GROUPS", 1)
    assert client.get("/api/player-model?" + FILTERS).status_code == 400
    monkeypatch.setattr("backend.core.player_model.MAX_GROUPS", 100)
    DefinitionVersion.objects.bulk_create(
        [
            DefinitionVersion(
                key=f"bounded-drill/{i}", kind="drill", status="APPROVED", payload=drill.payload
            )
            for i in range(100)
        ]
    )
    assert client.get("/api/player-model?" + FILTERS).status_code == 400
