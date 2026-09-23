"""Synthetic integration exercises software only; never promotes real definitions."""

import copy
import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from backend.core.evidence import publish_annotations
from backend.core.loops import create_assignment, create_plan, evaluate_plan
from backend.core.models import (
    AnalysisRun,
    DefinitionVersion,
    DrillAttempt,
    GameplayEvent,
    Match,
    ReplayAsset,
)
from backend.core.storage import delete_asset
from tests.test_backend import FakeStorage, reviewed_annotation

pytestmark = pytest.mark.django_db
TARGET = "tekken8.jin-vs-jin.blocked-uf4/v1"


def make_capture(owner, date, mode, successes, count=10):
    identity = uuid4().hex
    source_hash = hashlib.sha256(identity.encode()).hexdigest()
    asset = ReplayAsset.objects.create(
        owner=owner, storage_key=f"{owner.pk}/{identity}/source.mp4", source_sha256=source_hash
    )
    match = Match.objects.create(
        owner=owner,
        asset=asset,
        context="jin/jin",
        game_build="fixture",
        knowledge_revision="knowledge/1",
        session_id=identity,
        played_at=date,
        chronology_verified=True,
        mode=mode,
        dataset_kind="synthetic",
    )
    run = AnalysisRun.objects.create(
        owner=owner, asset=asset, request_key=identity, result={"source": {"duration_seconds": 60}}
    )
    annotation = reviewed_annotation(mode)
    annotation.update(source_sha256=source_hash, session_id=identity, played_at=date.isoformat())
    original = annotation["examples"][0]
    annotation["examples"] = []
    for i in range(count):
        item = copy.deepcopy(original)
        item.update(
            id=str(i),
            start_us=i * 1000000,
            end_us=i * 1000000 + 10000,
            outcome="SUCCESS" if i < successes else "FAILURE",
        )
        item["conditions"].update(punish_confirmed=i < successes, failure_confirmed=i >= successes)
        for review in item["reviews"]:
            review["outcome"] = item["outcome"]
        annotation["examples"].append(item)
    publish_annotations(owner, run.pk, match.pk, annotation)
    return asset, list(GameplayEvent.objects.filter(run=run)), annotation


def approved_drill():
    for key, kind in [
        (TARGET, "situation"),
        ("punish-success/v1", "metric"),
        ("knowledge/1", "knowledge"),
    ]:
        DefinitionVersion.objects.create(
            key=key, kind=kind, status="APPROVED", payload={"synthetic_only": True}
        )
    return DefinitionVersion.objects.create(
        key="synthetic-drill/1",
        kind="drill",
        status="APPROVED",
        payload={"situation_definition": TARGET, "game_build": "fixture", "synthetic_only": True},
    )


def test_full_synthetic_loop_through_api_and_practice_deletion(django_user_model):
    owner = django_user_model.objects.create_user("loop", is_staff=True)
    start = datetime(2026, 8, 1, tzinfo=UTC)
    baseline = []
    for i in range(5):
        _, events, _ = make_capture(owner, start + timedelta(days=i), "ranked", 1)
        baseline += events
    client = APIClient()
    client.force_authenticate(owner)
    drill = approved_drill()
    response = client.post("/api/assignments", {"drill_key": drill.pk}, format="json")
    assert response.status_code == 201
    assignment = response.data["id"]
    response = client.post(
        "/api/plans",
        {
            "assignment_id": assignment,
            "baseline_ids": [str(e.pk) for e in baseline],
            "baseline_end": (start + timedelta(days=5)).isoformat(),
            "followup_start": (start + timedelta(days=7)).isoformat(),
            "followup_end": (start + timedelta(days=30)).isoformat(),
        },
        format="json",
    )
    assert response.status_code == 201
    plan_id = response.data["id"]
    practice_asset, practice, _ = make_capture(owner, start + timedelta(days=6), "practice", 35, 40)
    response = client.post(
        f"/api/assignments/{assignment}/practice",
        {"assignment_id": assignment, "event_ids": [str(e.pk) for e in practice]},
        format="json",
    )
    assert response.status_code == 201
    assert DrillAttempt.objects.count() == 40
    duplicate = client.post(
        f"/api/assignments/{assignment}/practice",
        {"assignment_id": assignment, "event_ids": [str(e.pk) for e in practice]},
        format="json",
    )
    assert duplicate.status_code == 400
    followup = []
    for i in range(5):
        _, events, _ = make_capture(owner, start + timedelta(days=8 + i), "ranked", 9)
        followup += events
    body = {"event_ids": [str(e.pk) for e in followup]}
    response = client.post(f"/api/plans/{plan_id}/evaluate", body, format="json")
    assert response.status_code == 201
    result = response.data["result"]
    assert result["status"] == "OBSERVED_IMPROVEMENT"
    assert result["dataset_kind"] == "synthetic" and result["causal"] is False
    assert result["baseline"]["numerator"] == 5 and result["followup"]["numerator"] == 45
    assert len(result["practice_membership"]) == 40 and len(result["followup_membership"]) == 50
    repeated = client.post(f"/api/plans/{plan_id}/evaluate", body, format="json")
    assert repeated.data["id"] == response.data["id"]
    evaluation = evaluate_plan(owner, plan_id, [e.pk for e in followup])
    delete_asset(owner, practice_asset.pk, FakeStorage())
    evaluation.refresh_from_db()
    assert evaluation.invalidated_at is not None
    assert (
        evaluate_plan(owner, plan_id, [e.pk for e in followup]).result["status"]
        == "INSUFFICIENT_EXPOSURE"
    )


def test_conflicting_reimport_and_immutable_event(django_user_model):
    owner = django_user_model.objects.create_user("conflict", is_staff=True)
    _, events, annotation = make_capture(owner, datetime(2026, 8, 1, tzinfo=UTC), "ranked", 1)
    event = events[0]
    with pytest.raises(ValidationError, match="immutable"):
        event.save()
    annotation["examples"][0]["evidence"] = ["changed"]
    with pytest.raises(ValidationError, match="differs"):
        publish_annotations(owner, event.run_id, event.match_id, annotation)


def test_drill_baseline_mismatch(django_user_model):
    owner = django_user_model.objects.create_user("mismatch", is_staff=True)
    _, events, _ = make_capture(owner, datetime(2026, 8, 1, tzinfo=UTC), "ranked", 1)
    wrong = DefinitionVersion.objects.create(
        key="wrong",
        kind="drill",
        status="APPROVED",
        payload={"situation_definition": "other", "game_build": "fixture"},
    )
    assignment = create_assignment(owner, wrong.pk)
    with pytest.raises(ValidationError, match="does not match"):
        create_plan(
            owner,
            assignment.pk,
            [e.pk for e in events],
            "2026-08-05T00:00:00Z",
            "2026-08-07T00:00:00Z",
            "2026-08-31T00:00:00Z",
        )


def test_partial_capture_cannot_cherry_pick_success(django_user_model):
    owner = django_user_model.objects.create_user("partial", is_staff=True)
    _, events, _ = make_capture(owner, datetime(2026, 8, 1, tzinfo=UTC), "ranked", 1)
    assignment = create_assignment(owner, approved_drill().pk)
    with pytest.raises(ValidationError, match="every reviewed opportunity"):
        create_plan(
            owner,
            assignment.pk,
            [events[0].pk],
            "2026-08-05T00:00:00Z",
            "2026-08-07T00:00:00Z",
            "2026-08-31T00:00:00Z",
        )
