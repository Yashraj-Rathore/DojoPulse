from datetime import timedelta
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from backend.core.evidence import as_opportunity, publish_annotations
from backend.core.jobs import claim_run, finish_run
from backend.core.loops import create_assignment, create_plan, evaluate_plan, record_practice
from backend.core.models import (
    AnalysisRun,
    DefinitionVersion,
    DrillAssignment,
    EvaluationPlan,
    GameplayEvent,
    Match,
    MatchContribution,
    Profile,
    ReplayAsset,
)
from backend.core.storage import accept_finalized_upload, delete_account, delete_asset
from tests.test_dataset_vision import annotation

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner(django_user_model):
    return django_user_model.objects.create_user(
        username="owner", password="test-password", is_staff=True
    )


@pytest.fixture
def other(django_user_model):
    return django_user_model.objects.create_user(username="other", password="test-password")


@pytest.fixture
def capture(owner):
    asset = ReplayAsset.objects.create(
        owner=owner, storage_key=f"1/{uuid4()}/source.mp4", source_sha256="a" * 64
    )
    match = Match.objects.create(
        owner=owner,
        asset=asset,
        context="jin/jin",
        game_build="fixture",
        knowledge_revision="knowledge/1",
        session_id="s",
        played_at="2026-09-18T00:00:00Z",
        chronology_verified=True,
        mode="ranked",
        dataset_kind="synthetic",
    )
    run = AnalysisRun.objects.create(
        owner=owner, asset=asset, request_key="a", result={"source": {"duration_seconds": 1}}
    )
    return asset, match, run


def reviewed_annotation(mode="ranked"):
    value = annotation()
    value["source_kind"] = mode
    return value


def test_publish_idempotent_and_reanalysis_replaces(owner, capture):
    asset, match, run = capture
    publish_annotations(owner, run.pk, match.pk, reviewed_annotation())
    publish_annotations(owner, run.pk, match.pk, reviewed_annotation())
    assert GameplayEvent.objects.count() == 1
    assert MatchContribution.objects.get(match=match).summary["numerator"] == 1
    newer = AnalysisRun.objects.create(
        owner=owner, asset=asset, request_key="b", result={"source": {"duration_seconds": 1}}
    )
    value = reviewed_annotation()
    item = value["examples"][0]
    item["outcome"] = "FAILURE"
    item["conditions"].update(punish_confirmed=False, failure_confirmed=True)
    for review in item["reviews"]:
        review["outcome"] = "FAILURE"
    publish_annotations(owner, newer.pk, match.pk, value)
    assert GameplayEvent.objects.count() == 2
    assert MatchContribution.objects.count() == 1
    assert MatchContribution.objects.get(match=match).summary["numerator"] == 0


def test_cross_owner_and_unreviewed_api_attempts(owner, other, capture):
    asset, _, run = capture
    client = APIClient()
    client.force_authenticate(other)
    assert client.get(f"/api/runs/{run.pk}").status_code == 404
    assert client.get(f"/api/assets/{asset.pk}/media").status_code == 404
    assert client.delete(f"/api/assets/{asset.pk}").status_code == 404
    assert client.post("/api/uploads", {}, format="json").status_code == 503
    assert (
        client.post("/api/assignments", {"drill_key": "missing"}, format="json").status_code == 404
    )
    client.force_authenticate(owner)
    draft = DefinitionVersion.objects.create(key="draft", kind="drill", payload={})
    assert (
        client.post("/api/assignments", {"drill_key": draft.pk}, format="json").status_code == 400
    )


def test_job_claim_and_stale_fence(owner, capture):
    asset, _, run = capture
    token = claim_run(run.pk)
    assert token == 1
    assert claim_run(run.pk) is None
    assert finish_run(run.pk, token + 1, {"status": "COMPLETED"}) is False
    AnalysisRun.objects.filter(pk=run.pk).update(lease_until=timezone.now() - timedelta(seconds=1))
    new_token = claim_run(run.pk)
    assert new_token == 2
    assert finish_run(run.pk, token, {"status": "COMPLETED"}) is False
    assert finish_run(run.pk, new_token, {"status": "REVIEW_REQUIRED"}) is True


class FakeStorage:
    def __init__(self):
        self.cancelled = []
        self.deleted = []

    def cancel_upload(self, session):
        self.cancelled.append(session)

    def delete_asset(self, key):
        self.deleted.append(key)

    def delete_object(self, key):
        self.deleted.append(key)


def test_deletion_cancels_upload_and_late_object(owner, capture):
    asset, match, run = capture
    asset.upload_session = "secret-session"
    asset.save()
    token = claim_run(run.pk)
    store = FakeStorage()
    delete_asset(owner, asset.pk, store)
    assert store.cancelled == ["secret-session"]
    assert not finish_run(run.pk, token, {"status": "COMPLETED"})
    assert not accept_finalized_upload(asset.pk, asset.storage_key, store)
    assert len(store.deleted) == 2
    run.refresh_from_db()
    assert run.status == "CANCELLED"


def test_deleted_account_never_claims(owner, capture):
    _, _, run = capture
    delete_account(owner, FakeStorage())
    assert claim_run(run.pk) is None
    assert Profile.objects.get(user=owner).deleted_at is not None


def test_db_constraint_known_outcome_requires_eligible(owner, capture):
    _, match, run = capture
    with pytest.raises(IntegrityError), transaction.atomic():
        GameplayEvent.objects.create(
            owner=owner,
            run=run,
            match=match,
            played_key="bad",
            situation="s",
            metric="m",
            detector_version="d",
            start_us=0,
            end_us=1,
            eligibility="UNKNOWN",
            outcome="SUCCESS",
            verified=True,
        )


def setup_plan(owner, capture):
    _, match, run = capture
    publish_annotations(owner, run.pk, match.pk, reviewed_annotation())
    for key, kind in [
        ("tekken8.jin-vs-jin.blocked-uf4/v1", "situation"),
        ("punish-success/v1", "metric"),
        ("knowledge/1", "knowledge"),
    ]:
        DefinitionVersion.objects.create(key=key, kind=kind, payload={}, status="APPROVED")
    drill = DefinitionVersion.objects.create(
        key="synthetic-drill/1",
        kind="drill",
        status="APPROVED",
        payload={
            "situation_definition": "tekken8.jin-vs-jin.blocked-uf4/v1",
            "game_build": "fixture",
        },
    )
    assignment = create_assignment(owner, drill.pk)
    event = GameplayEvent.objects.get(run=run)
    plan = create_plan(
        owner,
        assignment.pk,
        [event.pk],
        "2026-09-19T00:00:00Z",
        "2026-09-21T00:00:00Z",
        "2026-10-21T00:00:00Z",
    )
    return plan, event


def test_plan_immutable_evaluation_revision_and_deletion(owner, capture):
    asset, _, _ = capture
    plan, event = setup_plan(owner, capture)
    with pytest.raises(ValidationError):
        plan.save()
    first = evaluate_plan(owner, plan.pk, [])
    assert first.result["status"] == "INSUFFICIENT_EXPOSURE"
    assert evaluate_plan(owner, plan.pk, []).pk == first.pk
    delete_asset(owner, asset.pk, FakeStorage())
    first.refresh_from_db()
    assert first.invalidated_at is not None
    second = evaluate_plan(owner, plan.pk, [])
    assert second.result["status"] == "NOT_COMPARABLE"
    assert second.revision == 2
    assert as_opportunity(GameplayEvent.objects.get(pk=event.pk)).deleted


def test_foreign_evidence_cannot_enter_plan(owner, other, capture):
    plan, event = setup_plan(owner, capture)
    client = APIClient()
    client.force_authenticate(other)
    assert (
        client.post(
            f"/api/plans/{plan.pk}/evaluate", {"event_ids": [str(event.pk)]}, format="json"
        ).status_code
        == 404
    )
    assert EvaluationPlan.objects.count() == 1


def test_practice_requires_actual_reviewed_practice(owner, capture):
    plan, event = setup_plan(owner, capture)
    with pytest.raises(ValidationError, match="practice"):
        record_practice(owner, plan.assignment_id, [event.pk])
    assert DrillAssignment.objects.get(pk=plan.assignment_id).status == "ASSIGNED"


def test_definition_cannot_be_overwritten():
    definition = DefinitionVersion.objects.create(
        key="immutable/1", kind="metric", payload={"a": 1}
    )
    definition.payload = {"a": 2}
    with pytest.raises(ValidationError):
        definition.save()
    with pytest.raises(IntegrityError), transaction.atomic():
        DefinitionVersion(key=definition.pk, kind="metric", payload={"a": 999}).save()
