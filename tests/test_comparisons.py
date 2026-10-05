"""M12 local engineering qualification with independently reviewed synthetic captures."""

import copy
import importlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.db import close_old_connections
from django.db.migrations.exceptions import IrreversibleError
from rest_framework.test import APIClient

from analysis.comparison import diagnostics, schedule
from analysis.contracts import EvaluationSpec, digest
from backend.core.comparisons import availability, delete_session, record_session
from backend.core.evidence import as_opportunity
from backend.core.loops import create_assignment, create_plan, evaluate_plan, record_practice
from backend.core.models import AnalysisRun, ComparisonSession, Match, ReplaySource
from backend.core.storage import delete_account
from tests.test_backend import FakeStorage
from tests.test_complete_loop import approved_drill, make_capture

pytestmark = pytest.mark.django_db
START = datetime(2026, 8, 1, tzinfo=UTC)
SCHEDULE = {
    "version": "comparison-schedule/1",
    "expected_followup_sessions": 5,
    "retention": {
        "start": (START + timedelta(days=31)).isoformat(),
        "end": (START + timedelta(days=45)).isoformat(),
        "expected_sessions": 5,
    },
}


@pytest.fixture
def env(django_user_model):
    owner = django_user_model.objects.create_user("comparison-owner", is_staff=True)
    drill = approved_drill()
    baseline = [
        e for i in range(5) for e in make_capture(owner, START + timedelta(days=i), "ranked", 1)[1]
    ]
    assignment = create_assignment(owner, drill.pk)
    values = {
        "assignment_id": assignment.pk,
        "baseline_ids": [e.pk for e in baseline],
        "baseline_end": (START + timedelta(days=5)).isoformat(),
        "followup_start": (START + timedelta(days=10)).isoformat(),
        "followup_end": (START + timedelta(days=30)).isoformat(),
        "schedule": copy.deepcopy(SCHEDULE),
        "request_id": uuid4(),
    }
    plan = create_plan(owner, **values)
    practice = make_capture(owner, START + timedelta(days=6), "practice", 36, 40)[1]
    record_practice(owner, assignment.pk, [e.pk for e in practice])
    later = [
        e
        for i in range(5)
        for e in make_capture(owner, START + timedelta(days=11 + i), "ranked", 9)[1]
    ]
    client = APIClient()
    client.force_authenticate(owner)
    return owner, plan, baseline, later, client, values


def missing(code="missing-1", **changes):
    return {
        "request_id": uuid4(),
        "phase": "FOLLOWUP",
        "state": "MISSING",
        "code": code,
        "played_at": START + timedelta(days=11),
        "match_ids": [],
        **changes,
    }


def test_phases_positive_retention_and_immutable_reproducible_report(env):
    owner, plan, _, _, client, _ = env
    first = evaluate_plan(owner, plan.pk)
    assert first.result["status"] == "OBSERVED_IMPROVEMENT"
    assert evaluate_plan(owner, plan.pk).pk == first.pk
    for i in range(5):
        make_capture(owner, START + timedelta(days=32 + i), "ranked", 9)
    retained = evaluate_plan(owner, plan.pk, phase="RETENTION")
    assert retained.revision == 2 and retained.phase == "RETENTION"
    assert retained.result["retention"]["state"] == "OBSERVED_CHANGE_PERSISTS"
    first.refresh_from_db()
    assert first.result["phase"] == "FOLLOWUP"
    path = f"/api/plans/{plan.pk}/comparison"
    report = client.get(path)
    assert report.status_code == 200 and report["Cache-Control"] == "private, no-store"
    assert report.data == client.get(path).data == client.get(path + "?download=1").data
    body = dict(report.data)
    claimed = body.pop("report_hash")
    assert digest(body) == claimed and body["release_approved"] is False
    assert all(row["available"] for row in body["revisions"])
    assert "storage_key" not in str(body) and "reviews" not in str(body)
    with pytest.raises(ValidationError):
        plan.save()
    with pytest.raises(ValidationError):
        retained.save()


def test_plan_request_retry_keeps_recommendation_and_hash(env):
    owner, plan, _, _, _, values = env
    assert create_plan(owner, **values).pk == plan.pk
    assert plan.content_hash == digest(
        {"specification": plan.specification, "protocol": plan.protocol}
    )
    with pytest.raises(ValidationError, match="different"):
        create_plan(owner, **{**values, "schedule": {**SCHEDULE, "expected_followup_sessions": 6}})


def test_missing_session_blocks_positive_then_resolves_by_original_code(env):
    owner, plan, _, later, _, _ = env
    first = evaluate_plan(owner, plan.pk)
    match = later[0].match
    gap = record_session(owner, plan.pk, missing(match.session_id))
    blocked = evaluate_plan(owner, plan.pk)
    assert blocked.result["status"] == "INSUFFICIENT_EXPOSURE"
    assert blocked.result["verified_practice"] == 40
    assert not availability(owner, first)[0]
    resolved = record_session(
        owner, plan.pk, missing(match.session_id, state="RECORDED", match_ids=[match.pk])
    )
    assert resolved.revision == gap.revision + 1
    assert evaluate_plan(owner, plan.pk).result["status"] == "OBSERVED_IMPROVEMENT"
    assert not availability(owner, blocked)[0]


def test_deleted_report_erases_all_revisions_and_cannot_retry(env):
    owner, plan, _, later, client, _ = env
    values = missing(later[0].match.session_id)
    row = record_session(owner, plan.pk, values)
    assert record_session(owner, plan.pk, values).pk == row.pk
    record_session(
        owner, plan.pk, missing(values["code"], state="RECORDED", match_ids=[later[0].match_id])
    )
    result = evaluate_plan(owner, plan.pk)
    delete_session(owner, row.pk)
    assert all(
        r.state == "DELETED"
        and not r.code
        and not r.match_ids
        and not r.played_at
        and not r.input_hash
        for r in ComparisonSession.objects.all()
    )
    result.refresh_from_db()
    assert result.invalidated_at
    with pytest.raises(ValidationError):
        record_session(owner, plan.pk, values)
    with pytest.raises(ValidationError):
        record_session(owner, plan.pk, missing(values["code"]))
    assert client.get("/api/account/export").data["comparison_sessions"] == []


@pytest.mark.parametrize("change", ["pipeline", "decoder", "platform", "source", "publication"])
def test_source_measurement_changes_abstain_and_hide_active_result(env, change):
    owner, plan, _, later, client, _ = env
    first = evaluate_plan(owner, plan.pk)
    event = later[0]
    if change == "pipeline":
        AnalysisRun.objects.filter(pk=event.run_id).update(pipeline_version="changed/2")
    elif change == "decoder":
        AnalysisRun.objects.filter(pk=event.run_id).update(
            result={
                **event.run.result,
                "decoder_identity": {
                    "contract": "isolated-media/1",
                    "image_sha256": "sha256:" + "a" * 64,
                },
            }
        )
    elif change == "platform":
        from backend.core.models import ReplayAsset

        ReplayAsset.objects.filter(pk=event.run.asset_id).update(
            metadata={**event.run.asset.metadata, "platform": "different"}
        )
    elif change == "source":
        ReplaySource.objects.create(
            match=event.match,
            asset=event.run.asset,
            provider="synthetic-source",
            access_class="USER_UPLOAD",
            representation="VIDEO",
            parser_version="new/1",
        )
    else:
        from backend.core.models import AnalysisPublication

        AnalysisPublication.objects.filter(match=event.match).delete()
    assert not availability(owner, first)[0]
    current = evaluate_plan(owner, plan.pk)
    assert current.result["status"] in {"NOT_COMPARABLE", "INSUFFICIENT_EXPOSURE"}
    assert current.result["change_interval"] is None
    view = client.get(f"/api/plans/{plan.pk}/comparison").data
    assert not next(r for r in view["revisions"] if str(r["id"]) == str(first.pk))["available"]


def test_unfavorable_omission_and_expected_session_shortfall(env):
    owner, plan, _, later, _, _ = env
    with pytest.raises(ValidationError):
        evaluate_plan(owner, plan.pk, [e.pk for e in later[:-1]])
    # A whole recorded match with no publication is a gap, not zero opportunities.
    Match.objects.create(
        owner=owner,
        context="jin/jin",
        mode="ranked",
        dataset_kind="synthetic",
        session_id="extra",
        played_at=START + timedelta(days=12),
    )
    result = evaluate_plan(owner, plan.pk)
    assert result.result["status"] == "INSUFFICIENT_EXPOSURE"
    assert result.result["collection"]["matches_without_current_target_publication"] == 1


def test_expired_local_source_is_a_gap_even_with_published_events(env):
    owner, plan, _, later, _, _ = env
    first = evaluate_plan(owner, plan.pk)
    event = later[0]
    ReplaySource.objects.create(
        match=event.match,
        asset=event.run.asset,
        provider="owned-upload",
        access_class="USER_UPLOAD",
        representation="VIDEO",
        availability="AVAILABLE",
        local_retain_until=START,
    )
    assert availability(owner, first) == (False, ["SOURCE_EXPIRED_WITHDRAWN_OR_CHANGED"])
    result = evaluate_plan(owner, plan.pk)
    assert result.result["status"] == "NOT_COMPARABLE"
    assert result.result["collection"]["matches_with_unavailable_local_sources"] == 1


def test_retention_does_not_add_late_practice_or_survive_initial_gap(env):
    owner, plan, _, _, _, _ = env
    initial = evaluate_plan(owner, plan.pk)
    for i in range(5):
        make_capture(owner, START + timedelta(days=32 + i), "ranked", 9)
    retained = evaluate_plan(owner, plan.pk, phase="RETENTION")
    record_session(owner, plan.pk, missing())
    assert not availability(owner, retained)[0]
    next_result = evaluate_plan(owner, plan.pk, phase="RETENTION")
    assert next_result.result["retention"]["state"] == "INITIAL_COMPARISON_UNAVAILABLE"
    assert digest(initial.result) == retained.result["retention"]["reference_result_hash"]


@pytest.mark.parametrize(
    "values",
    [
        missing(played_at=START),
        missing(state="MISSING", match_ids=[uuid4()]),
        missing(code="bad space"),
        missing(state="RECORDED", match_ids=[uuid4()]),
        missing(phase="RETENTION", played_at=START),
    ],
)
def test_invalid_session_cannot_qualify_evidence(env, values):
    with pytest.raises((ValidationError, ValueError)):
        record_session(env[0], env[1].pk, values)


def test_api_ownership_csrf_export_and_account_erasure(env, django_user_model):
    owner, plan, _, _, client, _ = env
    row = record_session(owner, plan.pk, missing())
    result = evaluate_plan(owner, plan.pk)
    export = client.get("/api/account/export").data
    assert export["comparison_sessions"][0]["code"] == "missing-1"
    other = django_user_model.objects.create_user("other-comparison")
    client.force_authenticate(other)
    assert client.get(f"/api/plans/{plan.pk}/comparison").status_code == 404
    assert client.delete(f"/api/comparison-sessions/{row.pk}").status_code == 404
    csrf = APIClient(enforce_csrf_checks=True)
    csrf.force_login(owner)
    assert csrf.post(f"/api/plans/{plan.pk}/sessions", {}, format="json").status_code == 403
    delete_account(owner, FakeStorage())
    assert not ComparisonSession.objects.filter(owner=owner).exists()
    result.refresh_from_db()
    assert result.invalidated_at


def test_schedule_cannot_retrofit_overlap_weaken_counts_or_accept_unknown_fields(env):
    spec = EvaluationSpec.from_dict(env[1].specification)
    for bad in [
        {**SCHEDULE, "expected_followup_sessions": True},
        {**SCHEDULE, "expected_followup_sessions": 4},
        {**SCHEDULE, "other": True},
        {**SCHEDULE, "retention": {**SCHEDULE["retention"], "start": spec.followup_end}},
    ]:
        with pytest.raises(ValueError):
            schedule(bad, spec)
    module = importlib.import_module("backend.core.migrations.0020_longitudinal_comparison")
    from django.apps import apps

    with pytest.raises(IrreversibleError):
        module.guard_history(apps, None)


def test_planning_uses_baseline_sessions_and_has_no_power_or_causal_approval(env):
    spec = EvaluationSpec.from_dict(env[1].specification)
    baseline = [as_opportunity(e) for e in env[2]]
    sparse = diagnostics(baseline, spec)
    assert sparse["planning"]["sessions_per_period"] is None
    rich = [
        replace(
            o,
            id=f"{i}-{o.id}",
            played_key=f"{i}-{o.played_key}",
            session_id=f"session-{i}",
            outcome="SUCCESS" if i % 2 else "FAILURE",
        )
        for i in range(10)
        for o in baseline[:10]
    ]
    result = diagnostics(rich, spec)
    assert result["planning"]["sessions_per_period"] >= 5
    assert result["planning"]["actual_power_validated"] is False
    assert result["floor_is_power_guarantee"] is False and result["causal"] is False
    assert (
        diagnostics([replace(o, outcome="SUCCESS") for o in rich], spec)["planning"][
            "sessions_per_period"
        ]
        is None
    )


def test_decoder_identity_comes_from_host_and_raw_report_cannot_inject(
    monkeypatch, settings, tmp_path
):
    import json

    import backend.core.parser as parser

    raw = {
        "status": "REVIEW_REQUIRED",
        "opportunities": [],
        "automatic_gameplay_validated": False,
        "source": {"source_sha256": "a" * 64, "duration_seconds": 60},
        "decoder_identity": {"image_sha256": "attacker"},
    }
    assert "decoder_identity" not in parser.validate_report(raw)
    settings.PARSER_BACKEND = "docker"
    settings.PARSER_IMAGE = "sha256:" + "b" * 64
    monkeypatch.setattr(parser, "sandbox_command", lambda *a: ["docker"])
    monkeypatch.setattr(
        parser, "run_bounded", lambda *a, **k: SimpleNamespace(stdout=json.dumps(raw))
    )
    monkeypatch.setattr(
        parser.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stderr=b"")
    )
    report = parser.analyze_isolated(
        tmp_path / "source.mp4", tmp_path / "report", tmp_path / "metadata"
    )
    assert report["decoder_identity"]["image_sha256"] == settings.PARSER_IMAGE


@pytest.mark.django_db(transaction=True)
def test_concurrent_evaluation_and_session_retry_are_serialized(env):
    owner, plan, _, _, _, _ = env
    values = missing()

    def write(kind):
        close_old_connections()
        try:
            if kind == "session":
                return record_session(owner, plan.pk, values).pk
            return evaluate_plan(owner, plan.pk).pk
        finally:
            close_old_connections()

    for kind in ["session", "result"]:
        with ThreadPoolExecutor(max_workers=2) as pool:
            ids = list(pool.map(write, [kind, kind]))
        assert ids[0] == ids[1]
    assert ComparisonSession.objects.count() == 1 and plan.evaluations.count() == 1
