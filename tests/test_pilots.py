"""Pilot role, consent, blinding, provenance and report safety regressions."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.db import close_old_connections
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from analysis.rules import REQUIRED
from backend.core import pilot_api, pilot_reports, pilots
from backend.core.consents import POLICY_VERSION, record_consent
from backend.core.control_journal import verified_records
from backend.core.models import (
    AnalysisRun,
    GameplayEvent,
    Match,
    PilotCapture,
    PilotEnrollment,
    PilotGateReport,
    PilotReview,
    PilotStudy,
    PilotTask,
    ReplayAsset,
)
from backend.core.storage import delete_account, delete_asset, private_path

pytestmark = pytest.mark.django_db


@pytest.fixture
def cohort(django_user_model, settings, tmp_path):
    settings.DEBUG = True
    settings.PRIVATE_DATA_ROOT = tmp_path / "media"
    users = {
        role: django_user_model.objects.create_user(f"pilot-{role}", is_staff=role == "manager")
        for role in ("manager", "participant", "one", "two", "third", "expert", "outsider")
    }
    study = pilots.create_study(users["manager"], "Synthetic pilot", "synthetic", uuid4())
    members = {}
    for key, role in [
        ("participant", "PARTICIPANT"),
        ("one", "REVIEWER"),
        ("two", "REVIEWER"),
        ("third", "ADJUDICATOR"),
        ("expert", "EXPERT"),
    ]:
        token = pilots.invite(users["manager"], study.pk, role)
        members[key] = pilots.enroll(
            users[key], token, study.protocol_digest, adult=True, accepted=True, rights=True
        )
    pilots.assign_split(users["manager"], study.pk, members["participant"].pk, "held-out")
    played = timezone.now()
    session = pilots.add_session(
        users["participant"],
        study.pk,
        code="baseline-1",
        phase="BASELINE",
        played_at=played,
        playable_seconds=None,
        state="CAPTURED",
        unaided=True,
        setup_seconds=None,
        useful=None,
        insight_seconds=None,
        request_id=uuid4(),
    )
    asset_id = uuid4()
    content = b"synthetic" * 18000
    asset = ReplayAsset.objects.create(
        id=asset_id,
        owner=users["participant"],
        storage_key=f"{users['participant'].pk}/{asset_id}/source.mp4",
        source_sha256=hashlib.sha256(content).hexdigest(),
        bytes=len(content),
        retain_until=played + timedelta(days=1),
    )
    path = private_path(asset.storage_key)
    path.parent.mkdir(parents=True)
    path.write_bytes(content)
    match = Match.objects.create(
        owner=users["participant"],
        asset=asset,
        played_at=played,
        game_build="synthetic-build/1",
        session_id="baseline-1",
        chronology_verified=True,
        mode="ranked",
        dataset_kind="synthetic",
    )
    AnalysisRun.objects.create(
        owner=users["participant"],
        asset=asset,
        request_key="pilot-safe",
        status="REVIEW_REQUIRED",
        result={"source": {"source_sha256": asset.source_sha256, "duration_seconds": 60}},
    )
    capture = pilots.add_capture(users["participant"], study.pk, session.pk, asset.pk)
    return users, study, members, session, asset, match, capture


def task(cohort, kind="TARGET", start=0, end=1000000, prediction=None):
    users, study, members, _, _, _, capture = cohort
    return pilots.add_task(
        users["manager"],
        study.pk,
        capture.pk,
        kind=kind,
        start_us=start,
        end_us=end,
        reviewer_one=members["one"].pk,
        reviewer_two=members["two"].pk,
        adjudicator=members["third"].pk,
        prediction=prediction,
        request_id=uuid4(),
    )


def label(success=True, visibility="RESOLVABLE"):
    return {
        "visibility": visibility,
        "conditions": {
            **dict.fromkeys(REQUIRED, True),
            "uncertainty_us": 0,
            "punish_confirmed": success,
            "failure_confirmed": not success,
        },
    }


def review(cohort, row, key, value=None, request_id=None):
    users, study, _, *_ = cohort
    return pilots.review_task(
        users[key], study.pk, row.pk, value or label(), 30, request_id or uuid4()
    )


def client(user):
    result = APIClient()
    result.force_authenticate(user)
    return result


def test_role_consent_no_manager_self_assignment_or_second_role(cohort):
    users, study, _, *_ = cohort
    token = pilots.invite(users["manager"], study.pk, "REVIEWER")
    with pytest.raises(ValidationError, match="manager"):
        pilots.enroll(
            users["manager"], token, study.protocol_digest, adult=True, accepted=True, rights=True
        )
    with pytest.raises(ValidationError, match="conflicts"):
        pilots.enroll(
            users["participant"],
            token,
            study.protocol_digest,
            adult=True,
            accepted=True,
            rights=True,
        )
    with pytest.raises(ValidationError, match="explicitly accept"):
        pilots.enroll(
            users["outsider"], token, study.protocol_digest, adult=False, accepted=True, rights=True
        )


def test_real_and_production_synthetic_intake_remain_gated(cohort, settings):
    users, _, _, *_ = cohort
    with pytest.raises(PermissionDenied):
        pilots.create_study(users["manager"], "Real", "real", uuid4())
    settings.DEBUG = False
    with pytest.raises(PermissionDenied):
        pilots.create_study(users["manager"], "Synthetic", "synthetic", uuid4())


def test_unrelated_staff_and_participants_cannot_review_or_manage(cohort):
    users, study, _, *_ = cohort
    row = task(cohort)
    users["outsider"].is_staff = True
    users["outsider"].save()
    assert client(users["outsider"]).get(f"/api/pilots/{study.pk}").status_code == 403
    assert (
        client(users["participant"])
        .post(f"/api/pilots/{study.pk}/freeze", {}, format="json")
        .status_code
        == 403
    )
    assert (
        client(users["participant"]).get(f"/api/pilots/{study.pk}/tasks/{row.pk}/media").status_code
        == 403
    )
    with pytest.raises(PermissionDenied):
        review(cohort, row, "participant")


def test_reviews_blinded_immutable_idempotent_and_heldout_hidden(cohort):
    users, study, _, *_ = cohort
    row = task(
        cohort,
        prediction={
            "detector_version": "offline/1",
            "start_us": 0,
            "eligibility": "ELIGIBLE",
            "outcome": "SUCCESS",
        },
    )
    request_id = uuid4()
    first = review(cohort, row, "one", request_id=request_id)
    assert review(cohort, row, "one", request_id=request_id).pk == first.pk
    with pytest.raises(ValidationError, match="immutable"):
        review(cohort, row, "one", label(False))
    data = client(users["two"]).get(f"/api/pilots/{study.pk}").json()
    assert data["tasks"][0]["reviews"] == [] and data["tasks"][0]["final_label"] is None
    assert "prediction" not in data["tasks"][0]
    review(cohort, row, "two")
    manager = client(users["manager"]).get(f"/api/pilots/{study.pk}").json()["tasks"][0]
    assert manager["state"] == "BLINDED" and manager["reviews"] == []
    pilots.freeze(users["manager"], study.pk)
    manager = client(users["manager"]).get(f"/api/pilots/{study.pk}").json()["tasks"][0]
    assert manager["state"] == "AGREED" and manager["final_label"]["outcome"] == "SUCCESS"
    assert not GameplayEvent.objects.exists()


def test_disagreement_requires_third_review_and_exports_valid_annotations(cohort):
    users, study, _, *_ = cohort
    row = task(cohort)
    with pytest.raises(ValidationError, match="two completed"):
        review(cohort, row, "third")
    review(cohort, row, "one")
    review(cohort, row, "two", label(False))
    assert pilots.final_label(row) == ("DISAGREEMENT", None)
    review(cohort, row, "third", label(False))
    assert pilots.final_label(row)[0] == "ADJUDICATED"
    pilots.freeze(users["manager"], study.pk)
    exported = pilot_reports.annotations(users["manager"], study.pk)
    assert exported["automatic_publication"] is False
    example = exported["batches"][0]["examples"][0]
    assert example["outcome"] == "FAILURE" and example["adjudication"]["seconds"] == 30
    assert not GameplayEvent.objects.exists()


def test_unknown_conditions_cannot_be_overridden_with_visibility(cohort):
    row = task(cohort)
    with pytest.raises(ValidationError, match="abstain"):
        review(cohort, row, "one", label(visibility="UNOBSERVABLE"))
    unknown = label(visibility="UNOBSERVABLE")
    unknown["conditions"]["block_verified"] = None
    review(cohort, row, "one", unknown)
    review(cohort, row, "two", unknown)
    assert pilots.final_label(row)[1]["outcome"] == "UNKNOWN"


def test_split_and_source_time_hash_and_overlap_guards(cohort):
    users, study, members, session, asset, match, capture = cohort
    with pytest.raises(ValidationError, match="before"):
        pilots.assign_split(users["manager"], study.pk, members["participant"].pk, "development")
    assert pilots.add_capture(users["participant"], study.pk, session.pk, asset.pk).pk == capture.pk
    task(cohort)
    with pytest.raises(ValidationError, match="overlap"):
        task(cohort, start=500, end=1500000)
    with pytest.raises(ValidationError, match="inside"):
        task(cohort, start=60000001, end=60000002)
    with pytest.raises(ValidationError, match="complete"):
        task(cohort, kind="QC")
    ReplayAsset.objects.filter(pk=asset.pk).update(source_sha256="b" * 64)
    with pytest.raises(ValidationError, match="retained"):
        task(cohort, start=2000000, end=3000000)
    assert not pilots.live_capture(
        PilotCapture.objects.select_related("asset", "session__enrollment__owner").get(
            pk=capture.pk
        )
    )


def test_reports_missing_values_denominators_and_no_synthetic_promotion(cohort):
    users, study, _, *_ = cohort
    row = task(cohort)
    review(cohort, row, "one")
    review(cohort, row, "two")
    with pytest.raises(ValidationError, match="Freeze"):
        pilot_reports.generate(users["manager"], study.pk)
    pilots.freeze(users["manager"], study.pk)
    reports = pilot_reports.generate(users["manager"], study.pk)
    assert len(reports) == 6
    assert {r.pk for r in pilot_reports.generate(users["manager"], study.pk)} == {
        r.pk for r in reports
    }
    assert all(
        r.data["scientific_gate"] == "NOT_RUN"
        and r.data["release_approval"] is False
        and r.data["scope"] == "SOFTWARE_REHEARSAL"
        for r in reports
    )
    g3 = next(r for r in reports if r.gate == "G3")
    assert g3.data["metrics"]["median_setup_seconds"] is None
    assert g3.data["metrics"]["participants"] == 1 and not g3.data["candidate_criteria_met"]
    g5 = next(r for r in reports if r.gate == "G5")
    assert g5.data["metrics"]["unmeasured_playable_sessions"] == 1
    with pytest.raises(ValidationError, match="sufficient"):
        pilot_reports.decide(users["expert"], study.pk, g3.pk, "CONTINUE", "CRITERIA_MET", "local")
    decision = pilot_reports.decide(
        users["expert"], study.pk, g3.pk, "WAIT", "INSUFFICIENT_SAMPLE", "local"
    )
    assert decision.actor_id != study.owner_id
    with pytest.raises(ValidationError, match="immutable"):
        pilot_reports.decide(users["expert"], study.pk, g3.pk, "STOP", "UTILITY", "local")


def test_reviews_after_freeze_invalidate_reports_without_editing_inputs(cohort):
    users, study, _, *_ = cohort
    row = task(cohort)
    pilots.freeze(users["manager"], study.pk)
    old = pilot_reports.generate(users["manager"], study.pk)
    review(cohort, row, "one")
    assert (
        PilotGateReport.objects.filter(
            pk__in=[r.pk for r in old], data={}, invalidated_at__isnull=False
        ).count()
        == 6
    )
    with pytest.raises(ValidationError, match="frozen"):
        task(cohort, start=2000000, end=3000000)
    new = pilot_reports.generate(users["manager"], study.pk)
    assert min(r.revision for r in new) > max(r.revision for r in old)


@pytest.mark.parametrize("operation", ["withdraw", "consent", "asset", "account", "expiry"])
def test_erasure_revokes_media_labels_exports_and_signed_controls(cohort, operation):
    users, study, members, _, asset, _, _ = cohort
    row = task(cohort)
    review(cohort, row, "one")
    review(cohort, row, "two")
    pilots.freeze(users["manager"], study.pk)
    pilot_reports.generate(users["manager"], study.pk)
    if operation == "withdraw":
        pilots.withdraw(users["participant"], study.pk)
        assert any(r["action"] == "PILOT_WITHDRAW" for r in verified_records())
        pilots.withdraw(users["participant"], study.pk)
    elif operation == "consent":
        record_consent(users["participant"], "PROCESSING", "WITHDRAW", POLICY_VERSION, uuid4())
    elif operation == "asset":
        delete_asset(users["participant"], asset.pk)
    elif operation == "account":
        delete_account(users["participant"])
    else:
        PilotEnrollment.objects.filter(pk=members["participant"].pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        assert pilots.expire_enrollments() == 1
    assert not PilotReview.objects.exists()
    assert not PilotGateReport.objects.filter(invalidated_at=None).exists()
    assert client(users["one"]).get(f"/api/pilots/{study.pk}/tasks/{row.pk}/media").status_code in {
        404,
        410,
    }
    asset.refresh_from_db()
    if operation in {"withdraw", "consent", "expiry"}:
        assert asset.deleted_at is None and private_path(asset.storage_key).exists()


def test_delegated_range_stream_stops_after_withdrawal(cohort):
    users, study, _, _, asset, *_ = cohort
    row = task(cohort)
    response = client(users["one"]).get(
        f"/api/pilots/{study.pk}/tasks/{row.pk}/media", HTTP_RANGE="bytes=0-"
    )
    assert response.status_code == 206 and response["Cache-Control"] == "private, no-store"
    stream = iter(response.streaming_content)
    assert len(next(stream)) == 65536
    pilots.withdraw(users["participant"], study.pk)
    assert list(stream) == []
    assert private_path(asset.storage_key).exists()


def test_reviewer_revocation_hides_reports_and_annotation_export(cohort):
    users, study, members, *_ = cohort
    row = task(cohort)
    review(cohort, row, "one")
    review(cohort, row, "two")
    pilots.freeze(users["manager"], study.pk)
    pilot_reports.generate(users["manager"], study.pk)
    users["two"].is_active = False
    users["two"].save()
    assert client(users["manager"]).get(f"/api/pilots/{study.pk}").json()["reports"] == []
    with pytest.raises(ValidationError, match="complete independent"):
        pilot_reports.annotations(users["manager"], study.pk)
    assert pilots.final_label(row) == ("PENDING", None)


def test_missing_and_zero_sessions_preserved_and_foreign_export_absent(cohort):
    users, study, _, *_ = cohort
    for code, state in [
        ("missing", "MISSING"),
        ("zero", "ZERO_OPPORTUNITIES"),
        ("invalid", "INVALID"),
    ]:
        pilots.add_session(
            users["participant"],
            study.pk,
            code=code,
            phase="BASELINE",
            played_at=timezone.now(),
            playable_seconds=None,
            state=state,
            unaided=False,
            setup_seconds=None,
            useful=None,
            insight_seconds=None,
            request_id=uuid4(),
        )
    metrics = pilot_reports.metrics(study)["G5"]["metrics"]
    assert metrics["session_states"] == {
        "CAPTURED": 1,
        "MISSING": 1,
        "ZERO_OPPORTUNITIES": 1,
        "INVALID": 1,
    }
    own = client(users["participant"]).get("/api/account/export").json()
    other = client(users["outsider"]).get("/api/account/export").json()
    assert "pilot_sessions" in str(own) and "baseline-1" in str(own)
    assert "baseline-1" not in str(other) and "storage_key" not in str(own)


def test_api_validates_structured_predictions_and_current_staff(cohort):
    users, study, _, *_ = cohort
    payload = {
        "start_us": 0,
        "eligibility": "UNKNOWN",
        "outcome": "SUCCESS",
        "detector_version": "test/1",
    }
    assert not pilot_api.Prediction(data=payload).is_valid()
    users["manager"].is_staff = False
    users["manager"].save()
    assert (
        client(users["manager"])
        .post(f"/api/pilots/{study.pk}/freeze", {}, format="json")
        .status_code
        == 403
    )


def test_closure_erases_study_and_restores_private_retention(cohort):
    users, study, _, _, asset, _, capture = cohort
    row = task(cohort)
    review(cohort, row, "one")
    pilots.close_study(users["manager"], study.pk)
    assert not PilotEnrollment.objects.filter(study=study, state="ACTIVE").exists()
    assert not PilotReview.objects.exists()
    assert PilotStudy.objects.get(pk=study.pk).protocol == {}
    assert any(r["action"] == "PILOT_CLOSE" for r in verified_records())
    asset.refresh_from_db()
    assert asset.deleted_at is None and asset.retain_until == capture.original_retain_until
    assert private_path(asset.storage_key).exists()


def test_provenance_change_cannot_preserve_evidence(cohort):
    users, study, _, _, _, match, _ = cohort
    row = task(cohort)
    review(cohort, row, "one")
    review(cohort, row, "two")
    pilots.freeze(users["manager"], study.pk)
    pilot_reports.generate(users["manager"], study.pk)
    Match.objects.filter(pk=match.pk).update(chronology_verified=False)
    data = client(users["manager"]).get(f"/api/pilots/{study.pk}").json()
    assert data["tasks"] == [] and data["reports"] == []
    assert pilot_reports.annotations(users["manager"], study.pk)["batches"] == []


def test_perfect_heldout_candidate_keeps_scientific_gate_not_run(cohort):
    from analysis.contracts import digest

    users, study, members, _, _, _, capture = cohort
    tasks = []
    labels = []
    for index in range(301):
        value = label(index < 150)
        if index == 300:
            value["conditions"]["standing"] = False
        checked = pilots.label_for("TARGET", value)
        labels.append(checked)
        tasks.append(
            PilotTask(
                capture=capture,
                kind="TARGET",
                start_us=index * 2000,
                end_us=index * 2000 + 1000,
                reviewer_one=members["one"],
                reviewer_two=members["two"],
                adjudicator=members["third"],
                request_id=uuid4(),
                prediction={
                    "detector_version": "offline/1",
                    "start_us": index * 2000,
                    "eligibility": checked["eligibility"],
                    "outcome": checked["outcome"],
                },
            )
        )
    PilotTask.objects.bulk_create(tasks)
    PilotReview.objects.bulk_create(
        [
            PilotReview(
                task=t,
                reviewer=members[key],
                label=value,
                label_digest=digest(value),
                seconds=1,
                request_id=uuid4(),
            )
            for t, value in zip(tasks, labels, strict=True)
            for key in ("one", "two")
        ]
    )
    pilots.freeze(users["manager"], study.pk)
    report = next(r for r in pilot_reports.generate(users["manager"], study.pk) if r.gate == "G2")
    assert report.data["candidate_criteria_met"]
    assert report.data["metrics"]["accepted_predictions"] == 300
    assert report.data["metrics"]["slices"]["FAILURE"]["one_sided_precision_lower_95"] >= 0.95
    pilot_reports.decide(
        users["expert"],
        study.pk,
        report.pk,
        "CONTINUE",
        "CRITERIA_MET",
        "synthetic-threshold-check",
    )
    assert report.data["scientific_gate"] == "NOT_RUN" and report.data["release_approval"] is False
    assert not GameplayEvent.objects.exists()


def test_canonical_link_pins_owned_evidence_and_counts_nonpositive_comparison(cohort):
    from backend.core.evidence import as_opportunity
    from backend.core.models import (
        DefinitionVersion,
        DrillAssignment,
        EvaluationPlan,
        ImprovementEvaluation,
    )

    users, study, _, _, asset, match, _ = cohort
    user = users["participant"]
    event = GameplayEvent.objects.create(
        owner=user,
        run=AnalysisRun.objects.get(asset=asset),
        match=match,
        played_key="pilot-source",
        situation=study.protocol["target"],
        metric="fixture",
        detector_version="offline/1",
        start_us=0,
        end_us=1,
        eligibility="ELIGIBLE",
        outcome="SUCCESS",
        verified=True,
        evidence=["synthetic-source-frame"],
    )
    Match.objects.filter(pk=match.pk).update(
        context="open-standing", knowledge_revision="synthetic/1"
    )
    match.refresh_from_db()
    event.match = match
    drill = DefinitionVersion.objects.create(
        key="pilot-synthetic-drill", kind="drill", payload={"synthetic_only": True}
    )
    assignment = DrillAssignment.objects.create(owner=user, drill=drill)
    spec = {
        "dataset_kind": "synthetic",
        "situation": study.protocol["target"],
        "baseline_end": study.protocol["baseline_end"],
        "followup_start": study.protocol["followup_start"],
        "followup_end": study.protocol["ends_at"],
        "baseline_membership": [[str(event.pk), as_opportunity(event).content_hash]],
    }
    plan = EvaluationPlan.objects.create(owner=user, assignment=assignment, specification=spec)
    result = ImprovementEvaluation.objects.create(
        owner=user,
        plan=plan,
        revision=1,
        result={"status": "OBSERVED_DETERIORATION", "dataset_kind": "synthetic"},
    )
    pilots.link_evaluation(user, study.pk, result.pk)
    metrics = pilot_reports.metrics(study)["G6"]["metrics"]
    assert metrics["linked_evaluations"] == 1 and metrics["comparable"] == 1
    assert not pilot_reports.metrics(study)["G6"]["candidate_criteria_met"]
    with pytest.raises(PermissionDenied):
        pilots.link_evaluation(users["outsider"], study.pk, result.pk)
    newer = ImprovementEvaluation.objects.create(
        owner=user, plan=plan, revision=2, result={"status": "NOT_COMPARABLE"}
    )
    with pytest.raises(ValidationError, match="latest"):
        pilots.link_evaluation(user, study.pk, result.pk)
    pilots.link_evaluation(user, study.pk, newer.pk)
    assert pilot_reports.metrics(study)["G6"]["metrics"]["comparable"] == 0
    delete_asset(user, asset.pk)
    assert pilot_reports.metrics(study)["G6"]["metrics"]["linked_evaluations"] == 0


def test_pilot_mutations_require_csrf_and_rollback_preserves_history(cohort):
    from importlib import import_module
    from types import SimpleNamespace

    from django.apps import apps
    from django.db import connection
    from django.test import Client

    users, study, _, *_ = cohort
    browser = Client(enforce_csrf_checks=True)
    browser.force_login(users["manager"])
    assert (
        browser.post(
            f"/api/pilots/{study.pk}/freeze", {}, content_type="application/json"
        ).status_code
        == 403
    )
    with pytest.raises(RuntimeError, match="pilot history"):
        import_module("backend.core.migrations.0013_pilot_workflow").guard_reverse(
            apps, SimpleNamespace(connection=connection)
        )
    with pytest.raises(RuntimeError, match="retention pins"):
        import_module("backend.core.migrations.0014_pilot_retention").guard_reverse(
            apps, SimpleNamespace(connection=connection)
        )
    with pytest.raises(RuntimeError, match="prospective allocation"):
        import_module("backend.core.migrations.0015_pilot_allocation").guard_reverse(
            apps, SimpleNamespace(connection=connection)
        )


@pytest.mark.django_db(transaction=True)
def test_concurrent_review_and_withdraw_leave_no_recreated_labels(cohort):
    users, study, members, *_ = cohort
    row = task(cohort)

    def submit():
        close_old_connections()
        try:
            review(cohort, row, "one")
        except (PermissionDenied, ValidationError, PilotTask.DoesNotExist):
            pass
        finally:
            close_old_connections()

    def remove():
        close_old_connections()
        try:
            pilots.withdraw(users["participant"], study.pk)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(submit), pool.submit(remove)]
        for future in futures:
            future.result(timeout=15)
    assert not PilotReview.objects.exists()
    assert PilotEnrollment.objects.get(pk=members["participant"].pk).state == "WITHDRAWN"
