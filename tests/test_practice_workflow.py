"""M11 synthetic engineering contracts, never an expert/gameplay qualification."""

import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.db import close_old_connections
from django.utils import timezone
from rest_framework.test import APIClient

from analysis.contracts import digest
from analysis.practice import progression, workflow
from backend.core.evidence import as_opportunity, publish_annotations
from backend.core.loops import create_assignment, create_plan, evaluate_plan, record_practice
from backend.core.models import AnalysisRun, DrillAssignment, DrillAttempt, PracticeLog, Profile
from backend.core.practice import assignment_detail, delete_log, log_practice
from backend.core.storage import delete_account
from tests.test_backend import FakeStorage
from tests.test_complete_loop import approved_drill, make_capture

pytestmark = pytest.mark.django_db
START = datetime(2026, 8, 1, tzinfo=UTC)
WORKFLOW = {
    "version": "practice-workflow/1",
    "context": "jin/jin",
    "response": "Synthetic response only; not Tekken instructions.",
    "success_criteria": "Independent fixture reviewers agree on the visible response.",
    "setup_steps": ["Set up the reviewed synthetic open-space fixture."],
    "alternatives": ["Use the reviewed synthetic safe alternative."],
    "capture_steps": ["Capture the whole block including uncertain and excluded windows."],
    "progression": {
        "version": "practice-progression/1",
        "minimum_known": 40,
        "minimum_sessions": 2,
        "minimum_coverage": 0.9,
        "minimum_agreement": 0.8,
        "ready_lower_bound": 0.7,
    },
}


@pytest.fixture
def practice_env(django_user_model):
    owner = django_user_model.objects.create_user("practice-owner", is_staff=True)
    old = approved_drill()
    from backend.core.models import DefinitionVersion

    drill = DefinitionVersion.objects.create(
        key="practice-drill/2",
        kind="drill",
        status="APPROVED",
        payload={
            **old.payload,
            "practice_workflow": WORKFLOW,
            "metric_definition": "punish-success/v1",
            "knowledge_revision": "knowledge/1",
        },
    )
    baseline = [
        e for i in range(5) for e in make_capture(owner, START + timedelta(days=i), "ranked", 1)[1]
    ]
    assignment = create_assignment(owner, drill.pk)
    plan = create_plan(
        owner,
        assignment.pk,
        [e.pk for e in baseline],
        (START + timedelta(days=5)).isoformat(),
        (START + timedelta(days=10)).isoformat(),
        (START + timedelta(days=30)).isoformat(),
    )
    client = APIClient()
    client.force_authenticate(owner)
    return owner, assignment, plan, client


def log_values(**changes):
    return {
        "request_id": uuid4(),
        "state": "COMPLETED",
        "started_at": START,
        "ended_at": START + timedelta(minutes=10),
        "reported_attempts": 40,
        "obstacle": "NONE",
        **changes,
    }


def practice_rows(env, day=6, successes=20):
    return make_capture(env[0], START + timedelta(days=day), "practice", successes, 20)


@pytest.mark.parametrize(
    "field,value",
    [
        ("minimum_known", 39),
        ("minimum_known", True),
        ("minimum_sessions", 1),
        ("minimum_coverage", 0.89),
        ("minimum_agreement", float("nan")),
        ("ready_lower_bound", float("inf")),
    ],
)
def test_workflow_rejects_unbounded_or_weak_rules(field, value):
    rules = copy.deepcopy(WORKFLOW)
    rules["progression"][field] = value
    with pytest.raises(ValueError):
        workflow(rules)


def test_complete_two_session_progression_and_unknowns(practice_env):
    owner, assignment, _, client = practice_env
    for day in [6, 7]:
        _, events, _ = practice_rows(practice_env, day)
        request_id = str(uuid4())
        path = f"/api/assignments/{assignment.pk}/practice"
        first = client.post(
            path,
            {"event_ids": [str(e.pk) for e in events], "request_id": request_id},
            format="json",
        )
        assert first.status_code == 201, first.data
        retry = client.post(
            path,
            {"event_ids": [str(e.pk) for e in events], "request_id": request_id},
            format="json",
        )
        assert retry.status_code == 200 and retry.data["id"] == first.data["id"]
    data = client.get(f"/api/assignments/{assignment.pk}/training")
    assert data.status_code == 200 and data["Cache-Control"] == "private, no-store"
    assert data.data["progression"]["state"] == "READY_FOR_FOLLOWUP"
    assert data.data["progression"]["summary"]["denominator"] == 40
    assert data.data["progression"]["release_approved"] is False
    assert len(data.data["evidence"]) == 5
    opportunities = [as_opportunity(e) for e in events]
    real = [replace(e, dataset_kind="real") for e in opportunities]
    result = progression(
        real,
        WORKFLOW["progression"],
        reviewed=20,
        agreement=1,
        minimum_plan_practice=20,
        dataset_kind="real",
        baseline_available=True,
    )
    assert result["state"] == "MORE_REVIEWED_PRACTICE_NEEDED"
    all_real = real + [
        replace(e, id=e.id + "x", session_id="second", played_key=e.played_key + "x") for e in real
    ]
    result = progression(
        all_real,
        WORKFLOW["progression"],
        reviewed=40,
        agreement=1,
        minimum_plan_practice=40,
        dataset_kind="real",
        baseline_available=True,
    )
    assert result["state"] == "REAL_PRACTICE_VALIDATION_PENDING"


def test_partial_wrong_context_and_source_end_fail(practice_env):
    owner, assignment, _, _ = practice_env
    _, events, _ = practice_rows(practice_env)
    with pytest.raises(ValidationError, match="every reviewed"):
        record_practice(owner, assignment.pk, [e.pk for e in events[:-1]])
    from backend.core.models import Match

    Match.objects.filter(pk=events[0].match_id).update(context="jin/kazuya")
    with pytest.raises(ValidationError, match="exact baseline scope"):
        record_practice(owner, assignment.pk, [e.pk for e in events])
    Match.objects.filter(pk=events[0].match_id).update(
        context="jin/jin", played_at=START + timedelta(days=10, seconds=-30)
    )
    with pytest.raises(ValidationError, match="source end"):
        record_practice(owner, assignment.pk, [e.pk for e in events])
    assert not DrillAttempt.objects.exists()


def test_reanalysis_expiration_and_deletion_remove_exposure(practice_env):
    owner, assignment, _, _ = practice_env
    asset, events, annotation = practice_rows(practice_env)
    record_practice(owner, assignment.pk, [e.pk for e in events])
    newer = AnalysisRun.objects.create(
        owner=owner,
        asset=asset,
        request_key=uuid4().hex,
        result={"source": {"duration_seconds": 60}},
    )
    publish_annotations(owner, newer.pk, events[0].match_id, annotation)
    data = assignment_detail(owner, assignment)
    assert (
        data["unavailable_trials"] == 20
        and data["progression"]["state"] == "EVIDENCE_REVIEW_REQUIRED"
    )
    from backend.core.models import GameplayEvent

    overview = practice_env[3].get("/api/overview")
    assert overview.status_code == 200
    assert overview.data["practice"][0]["attempts"] == 20
    assert overview.data["practice"][0]["available_attempts"] == 0
    assert overview.data["practice"][0]["summary"]["denominator"] == 0
    fresh = list(GameplayEvent.objects.filter(run=newer))
    with pytest.raises(ValidationError, match="count twice"):
        record_practice(owner, assignment.pk, [e.pk for e in fresh])
    asset.retain_until = timezone.now() - timedelta(seconds=1)
    asset.save(update_fields=["retain_until"])
    assert assignment_detail(owner, assignment)["progression"]["summary"]["denominator"] == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"state": "SKIPPED", "reported_attempts": 1},
        {"reported_attempts": 0},
        {"ended_at": START - timedelta(seconds=1)},
        {"ended_at": START + timedelta(hours=9)},
        {"ended_at": datetime(9998, 1, 1, tzinfo=UTC)},
        {"obstacle": "PRIVATE_FREE_TEXT"},
    ],
)
def test_report_invalid_sessions_fail(practice_env, changes):
    owner, assignment, _, _ = practice_env
    with pytest.raises(ValidationError):
        log_practice(owner, assignment.pk, log_values(**changes))
    assert not PracticeLog.objects.exists()


def test_reports_never_expose_and_deleted_retry_cannot_resurrect(practice_env, django_user_model):
    owner, assignment, _, client = practice_env
    values = log_values()
    item = log_practice(owner, assignment.pk, values)
    assert log_practice(owner, assignment.pk, values).pk == item.pk
    assert not DrillAttempt.objects.exists()
    assert assignment_detail(owner, assignment)["progression"]["summary"]["denominator"] == 0
    other = django_user_model.objects.create_user("practice-other", is_staff=True)
    foreign = APIClient()
    foreign.force_authenticate(other)
    assert foreign.get(f"/api/assignments/{assignment.pk}/training").status_code == 404
    assert foreign.delete(f"/api/practice-reports/{item.pk}").status_code == 404
    assert client.delete(f"/api/practice-reports/{item.pk}").status_code == 200
    item.refresh_from_db()
    assert item.state == "DELETED" and item.pins == {} and item.started_at is None
    with pytest.raises(ValidationError, match="deleted"):
        log_practice(owner, assignment.pk, values)


def test_cancel_consent_and_account_erasure(practice_env):
    owner, assignment, _, client = practice_env
    log_practice(owner, assignment.pk, log_values())
    exported = client.get("/api/account/export")
    assert exported.status_code == 200 and len(exported.data["practice_reports"]) == 1
    assert (
        client.post(f"/api/assignments/{assignment.pk}/cancel", {}, format="json").status_code
        == 200
    )
    with pytest.raises(ValidationError, match="cancelled"):
        log_practice(owner, assignment.pk, log_values())
    Profile.objects.update_or_create(
        user=owner, defaults={"processing_withdrawn_at": timezone.now()}
    )
    assert client.get(f"/api/assignments/{assignment.pk}/training").status_code == 400
    delete_account(owner, FakeStorage())
    assert not PracticeLog.objects.exists()
    assignment.refresh_from_db()
    assert assignment.diagnosis == {} and assignment.status == "WITHDRAWN"


@pytest.mark.django_db(transaction=True)
def test_concurrent_report_retry_and_delete_are_serialized(practice_env):
    owner, assignment, _, _ = practice_env
    values = log_values()

    def write():
        close_old_connections()
        try:
            return log_practice(owner, assignment.pk, values).pk
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: write(), range(2)))
    assert results[0] == results[1] and PracticeLog.objects.count() == 1

    def erase():
        close_old_connections()
        try:
            delete_log(owner, results[0])
        finally:
            close_old_connections()

    def retry():
        try:
            return write()
        except ValidationError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        one, two = pool.submit(erase), pool.submit(retry)
        one.result()
        two.result()
    assert PracticeLog.objects.get().state == "DELETED" and not DrillAttempt.objects.exists()


def test_assignment_proof_is_current_complete_and_idempotent(practice_env):
    owner, assignment, _, client = practice_env
    filters = {"dataset_kind": "synthetic", "date_from": "2026-08-01", "date_to": "2026-08-05"}
    model = client.get("/api/player-model", filters).data
    card = model["cards"][0]
    proof = {
        "card_id": card["id"],
        "evidence_hash": card["evidence_hash"],
        "policy_hash": model["policy_hash"],
        "filters": filters,
    }
    values = {"drill_key": assignment.drill_id, "request_id": str(uuid4()), "diagnosis": proof}
    first = client.post("/api/assignments", values, format="json")
    assert first.status_code == 201, first.data
    retry = client.post("/api/assignments", values, format="json")
    assert retry.status_code == 200 and first.data["id"] == retry.data["id"]
    pinned = DrillAssignment.objects.get(pk=first.data["id"])
    assert len(pinned.diagnosis["membership"]) == 50
    values["request_id"] = str(uuid4())
    proof["evidence_hash"] = "0" * 64
    assert client.post("/api/assignments", values, format="json").status_code == 400
    pinned.diagnosis = {}
    with pytest.raises(ValidationError, match="immutable"):
        pinned.save()


def test_csrf_missing_plan_and_unknown_windows_never_qualify(practice_env):
    owner, assignment, _, _ = practice_env
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(owner)
    assert client.get(f"/api/assignments/{assignment.pk}/training").status_code == 200
    assert (
        client.post(f"/api/assignments/{assignment.pk}/cancel", {}, format="json").status_code
        == 403
    )
    another = create_assignment(owner, assignment.drill_id)
    _, events, _ = practice_rows(practice_env)
    with pytest.raises(ValidationError, match="Freeze a baseline"):
        record_practice(owner, another.pk, [e.pk for e in events])
    opportunities = [as_opportunity(e) for e in events]
    unknown = [
        replace(
            e,
            id=e.id + "u",
            played_key=e.played_key + "u",
            outcome="UNKNOWN",
            eligibility="ELIGIBLE",
        )
        for e in opportunities
    ]
    mixed = (
        opportunities
        + [
            replace(e, id=e.id + "b", played_key=e.played_key + "b", session_id="second")
            for e in opportunities
        ]
        + unknown
    )
    result = progression(
        mixed,
        WORKFLOW["progression"],
        reviewed=60,
        agreement=1,
        minimum_plan_practice=40,
        dataset_kind="synthetic",
        baseline_available=True,
    )
    assert result["state"] == "EVIDENCE_REVIEW_REQUIRED"
    assert result["summary"]["eligible_unknown"] == 20


def test_migration_pins_old_assignments_and_refuses_recorded_history(practice_env):
    from importlib import import_module

    from django.apps import apps
    from django.db.migrations.exceptions import IrreversibleError

    module = import_module("backend.core.migrations.0019_reviewed_practice_workflow")
    owner, assignment, _, _ = practice_env
    DrillAssignment.objects.filter(pk=assignment.pk).update(drill_hash="")
    module.pin_existing(apps, None)
    assignment.refresh_from_db()
    assert assignment.drill_hash == assignment.drill.content_hash
    log_practice(owner, assignment.pk, log_values())
    with pytest.raises(IrreversibleError):
        module.guard_history(apps, None)


def test_unavailable_practice_blocks_positive_reevaluation(practice_env):
    owner, assignment, plan, _ = practice_env
    assets = []
    for day in [6, 7]:
        asset, events, _ = practice_rows(practice_env, day)
        assets.append(asset)
        record_practice(owner, assignment.pk, [e.pk for e in events])
    followup = [
        e
        for day in range(11, 16)
        for e in make_capture(owner, START + timedelta(days=day), "ranked", 10)[1]
    ]
    first = evaluate_plan(owner, plan.pk, [e.pk for e in followup])
    assert first.result["verified_practice"] == 40
    assert first.result["status"] == "OBSERVED_IMPROVEMENT"
    original_membership = copy.deepcopy(first.result["practice_membership"])
    assets[0].retain_until = timezone.now() - timedelta(seconds=1)
    assets[0].save(update_fields=["retain_until"])
    second = evaluate_plan(owner, plan.pk, [e.pk for e in followup])
    assert second.result["verified_practice"] == 0
    assert second.result["unavailable_practice_trials"] == 20
    assert second.result["status"] == "INSUFFICIENT_EXPOSURE"
    first.refresh_from_db()
    assert digest(first.result["practice_membership"]) == digest(original_membership)
