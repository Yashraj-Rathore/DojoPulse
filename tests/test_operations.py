import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.db import close_old_connections, connection
from django.utils import timezone
from rest_framework.exceptions import Throttled
from rest_framework.test import APIClient

from backend.core.budgets import totals
from backend.core.jobs import acknowledge_stopped, cancel_run, claim_run, enqueue_run, finish_run
from backend.core.models import (
    AnalysisRun,
    AttemptMetric,
    CostObservation,
    ExecutionSlot,
    Match,
    OperatorWork,
    ReplayAsset,
    RunBudget,
)
from backend.core.operations import COMPONENTS, costs, objective, snapshot
from backend.core.storage import delete_account, delete_asset, private_path
from backend.core.telemetry import record_attempt, record_request, route_label

pytestmark = pytest.mark.django_db


@pytest.fixture
def run(django_user_model, settings, tmp_path):
    settings.PRIVATE_DATA_ROOT = tmp_path / "media"
    owner = django_user_model.objects.create_user("ops-owner", password="fixture-only")
    asset_id = uuid4()
    asset = ReplayAsset.objects.create(
        id=asset_id, owner=owner, storage_key=f"{owner.pk}/{asset_id}/source.mp4", bytes=7
    )
    path = private_path(asset.storage_key)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"fixture")
    Match.objects.create(
        owner=owner, asset=asset, played_at=timezone.now(), dataset_kind="synthetic"
    )
    return enqueue_run(owner=owner, asset=asset, request_key="first")


def measure(run, fence, elapsed=12.1):
    return record_attempt(
        run.pk,
        fence,
        elapsed=elapsed,
        cpu_seconds=1.5,
        peak_rss=12345,
        report={
            "source": {"duration_seconds": 60},
            "cost": {"decoder_cpu_seconds": 2, "decoder_peak_rss_bytes": 45678, "derived_bytes": 8},
            "private_path": "never-recorded",
        },
    )


def test_reservations_atomic_idempotent_and_policy_snapshot(run, settings):
    budget = RunBudget.objects.get(run=run)
    assert budget.reserved_processing_seconds == 1260
    assert enqueue_run(owner=run.owner, asset=run.asset, request_key="first").pk == run.pk
    assert RunBudget.objects.count() == 1
    settings.RUN_MAX_ATTEMPTS = 1
    settings.RUN_DEADLINE_SECONDS = 1
    fence = claim_run(run.pk)
    run.refresh_from_db()
    assert (run.deadline_at - run.heartbeat_at).total_seconds() == 420
    assert fence == 1


def test_queue_cancel_refunds_once(run):
    cancel_run(run.owner, run.pk)
    cancel_run(run.owner, run.pk)
    assert totals(run.owner) == {
        "media_held": 0,
        "processing_held": 0,
        "media_used": 0,
        "processing_used": 0,
    }
    assert RunBudget.objects.get(run=run).measurement_complete


def test_processing_cancel_holds_until_stop_and_charges_unknown(run):
    fence = claim_run(run.pk)
    cancel_run(run.owner, run.pk)
    assert totals(run.owner)["processing_held"] == 1260
    assert not measure(run, fence)
    acknowledge_stopped(run.pk, fence)
    acknowledge_stopped(run.pk, fence)
    assert totals(run.owner)["processing_used"] == 420
    budget = RunBudget.objects.get(run=run)
    assert budget.charged_media_seconds == 600 and not budget.measurement_complete


def test_measured_terminal_work_settles_only_after_stop(run):
    fence = claim_run(run.pk)
    assert measure(run, fence)
    assert not measure(run, fence, 999)
    assert finish_run(run.pk, fence, {"status": "FAILED", "issues": ["INVALID_PARSER_REPORT"]})
    assert totals(run.owner)["processing_held"] == 1260
    acknowledge_stopped(run.pk, fence)
    budget = RunBudget.objects.get(run=run)
    assert budget.charged_processing_seconds == 13 and budget.charged_media_seconds == 60
    assert budget.measurement_complete
    assert AttemptMetric.objects.get(slot__run=run).outcome == "FAILED"


def test_cross_midnight_open_holds_and_settlement_charge_today(run, settings):
    tomorrow = timezone.localdate() + timedelta(days=1)
    with patch("backend.core.budgets.timezone.localdate", return_value=tomorrow):
        assert totals(run.owner)["processing_held"] == 1260
        settings.OWNER_PROCESSING_SECONDS_PER_DAY = 1260
        with pytest.raises(Throttled):
            enqueue_run(owner=run.owner, asset=run.asset, request_key="tomorrow")
        cancel_run(run.owner, run.pk)
    assert RunBudget.objects.get(run=run).day == tomorrow


def test_retry_budget_stops_after_snapshot_maximum(run):
    for _ in range(3):
        fence = claim_run(run.pk)
        assert fence is not None
        acknowledge_stopped(run.pk, fence)  # Simulated authoritative crash/stop; no measurement.
    assert claim_run(run.pk) is None
    run.refresh_from_db()
    assert run.status == "FAILED" and run.error_code == "RETRY_BUDGET_EXHAUSTED"
    assert totals(run.owner)["processing_used"] == 1260
    assert snapshot()["counts"]["retry_attempts"] == 2


def test_reanalysis_limit_and_rollback(run):
    cancel_run(run.owner, run.pk)
    for key in ["second", "third"]:
        item = enqueue_run(owner=run.owner, asset=run.asset, request_key=key)
        cancel_run(run.owner, item.pk)
    with pytest.raises(Throttled):
        enqueue_run(owner=run.owner, asset=run.asset, request_key="fourth")
    assert AnalysisRun.objects.count() == RunBudget.objects.count() == 3


def test_operator_pause_rejects_new_and_preserves_pending(run, settings):
    settings.OPTIONAL_PROCESSING_PAUSED = True
    assert claim_run(run.pk) is None
    with pytest.raises(Throttled):
        enqueue_run(owner=run.owner, asset=run.asset, request_key="paused")
    assert AnalysisRun.objects.count() == 1 and totals()["processing_held"] == 1260


@pytest.mark.django_db(transaction=True)
def test_concurrent_global_budget_admission(django_user_model, settings):
    if connection.vendor != "postgresql":
        pytest.skip("Real row locks require PostgreSQL")
    settings.GLOBAL_PROCESSING_SECONDS_PER_DAY = 1260
    owners = [django_user_model.objects.create_user(f"parallel-ops-{i}") for i in range(4)]
    assets = [
        ReplayAsset.objects.create(owner=owner, storage_key=f"{owner.pk}/synthetic/source.mp4")
        for owner in owners
    ]

    def attempt(index):
        close_old_connections()
        try:
            enqueue_run(owner=owners[index], asset=assets[index], request_key="parallel")
            return True
        except Throttled:
            return False
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(attempt, range(4))) == 1
    assert AnalysisRun.objects.count() == RunBudget.objects.count() == 1


def test_metrics_allowlist_invalid_and_unknown(run):
    fence = claim_run(run.pk)
    record_attempt(
        run.pk,
        fence,
        elapsed=float("nan"),
        cpu_seconds=-1,
        peak_rss=True,
        report={"source": [], "cost": {"decoder_cpu_seconds": float("inf"), "derived_bytes": 1.1}},
    )
    metric = AttemptMetric.objects.get(slot__run=run)
    assert (
        metric.elapsed_seconds
        is metric.coordinator_cpu_seconds
        is metric.coordinator_peak_rss_bytes
        is metric.derived_bytes
        is None
    )
    assert not hasattr(metric, "private_path")


def test_staff_only_window_and_owner_usage(run, django_user_model):
    client = APIClient()
    assert client.get("/api/operations").status_code == 403
    client.force_authenticate(run.owner)
    assert client.get("/api/operations").status_code == 403
    assert client.get("/api/usage").json()["seconds"]["media_held"] == 600
    staff = django_user_model.objects.create_user("operator", is_staff=True)
    client.force_authenticate(staff)
    assert client.get("/api/operations?days=31").status_code == 400
    response = client.get("/api/operations?days=1")
    assert response.status_code == 200 and response["Cache-Control"] == "private, no-store"
    text = response.content.decode()
    assert "ops-owner" not in text and run.asset.storage_key not in text and str(run.pk) not in text
    assert response.json()["costs"][0]["total_usd"] is None


def test_staff_permission_rechecks_locked_current_account(run):
    run.owner.is_staff = True
    run.owner.save()
    client = APIClient()
    client.force_authenticate(run.owner)
    run.owner.__class__.objects.filter(pk=run.owner.pk).update(is_staff=False)
    assert client.get("/api/operations").status_code == 403


def test_work_idempotency_scope_and_conflict(run):
    run.owner.is_staff = True
    run.owner.save()
    client = APIClient()
    client.force_authenticate(run.owner)
    body = {"kind": "REVIEW", "seconds": 120, "scope": "SYNTHETIC", "request_id": str(uuid4())}
    assert client.post("/api/operations/work", body).status_code == 201
    assert client.post("/api/operations/work", body).status_code == 200
    assert client.post("/api/operations/work", {**body, "seconds": 200}).status_code == 400
    assert OperatorWork.objects.count() == 1
    exported = client.get("/api/account/export").json()
    assert exported["operator_work"][0]["seconds"] == 120
    assert exported["resource_budgets"][0]["run_id"] == str(run.pk)


def test_cost_exact_window_missing_zero_and_scope_separation(run):
    today = timezone.localdate()
    for component in COMPONENTS[:-1]:
        CostObservation.objects.create(
            component=component,
            scope="SYNTHETIC",
            period_start=today,
            period_end=today,
            amount_usd=0,
            reference="synthetic-zero",
        )
    assert costs(today, today, "SYNTHETIC")["total_usd"] is None
    CostObservation.objects.create(
        component="SUPPORT",
        scope="SYNTHETIC",
        period_start=today,
        period_end=today,
        amount_usd=2,
        reference="synthetic-2",
    )
    data = costs(today, today, "SYNTHETIC")
    assert data["total_usd"] == "2.000000" and data["per_unit_usd"]["capture"] == "2.000000"
    assert data["per_unit_usd"]["completed_loop"] is None
    assert costs(today, today, "OBSERVED")["total_usd"] is None
    assert costs(today - timedelta(days=1), today, "SYNTHETIC")["total_usd"] is None


def test_cost_write_validation_and_idempotency(run):
    run.owner.is_staff = True
    run.owner.save()
    client = APIClient()
    client.force_authenticate(run.owner)
    body = {
        "component": "INFRASTRUCTURE",
        "scope": "SYNTHETIC",
        "period_start": str(timezone.localdate()),
        "period_end": str(timezone.localdate()),
        "amount_usd": "2.50",
        "reference": "rehearsal-1",
    }
    assert client.post("/api/operations/cost", body).status_code == 201
    assert client.post("/api/operations/cost", body).status_code == 200
    assert client.post("/api/operations/cost", {**body, "amount_usd": "3"}).status_code == 400
    assert (
        client.post("/api/operations/cost", {**body, "reference": "secret@example.com"}).status_code
        == 400
    )
    assert client.post("/api/operations/cost", {**body, "amount_usd": "-1"}).status_code == 400


def test_request_fixed_labels_and_objective_sample_gates():
    assert route_label("/api/assets/private-player-id/media") == "MEDIA"
    assert route_label("/health/ready") is None
    assert objective(0.1, 1, 0.05)["state"] == "INSUFFICIENT_DATA"
    for status in [200, 429, 500]:
        record_request("WORKSPACE", status, 0.1)
    record_request("OPERATIONS", 500, 0.1)
    data = snapshot()
    assert data["requests"]["samples"] == 3 and data["requests"]["server_errors"] == 1
    assert data["objectives"]["api_availability"]["state"] == "INSUFFICIENT_DATA"
    assert objective(0.9, 20, 0.95, at_least=True)["state"] == "BREACH"


def test_alerts_and_cli_status(run):
    fence = claim_run(run.pk)
    AnalysisRun.objects.filter(pk=run.pk).update(lease_until=timezone.now() - timedelta(seconds=1))
    assert "STALE_SLOTS" in snapshot()["alerts"]
    from django.core.management.base import CommandError

    output = StringIO()
    with pytest.raises(CommandError, match="OPERATIONS_ALERTS_PRESENT"):
        call_command("operations_snapshot", fail_on_alert=True, stdout=output)
    assert json.loads(output.getvalue())["counts"]["active_slots"] == 1
    assert ExecutionSlot.objects.get(run=run, fence=fence).released_at is None


def test_asset_account_deletion_erases_measurements_but_keeps_safety_hold(run):
    fence = claim_run(run.pk)
    assert measure(run, fence)
    OperatorWork.objects.create(
        owner=run.owner, kind="REVIEW", seconds=2, scope="SYNTHETIC", request_id=uuid4()
    )
    delete_asset(run.owner, run.asset_id)
    assert not AttemptMetric.objects.exists()
    assert not measure(run, fence)
    assert totals()["processing_held"] == 1260
    delete_account(run.owner)
    assert not OperatorWork.objects.exists()
    acknowledge_stopped(run.pk, fence)
    assert totals()["processing_used"] == 420


def test_prune_never_releases_open_or_today_budget(run):
    old = timezone.now() - timedelta(days=40)
    fence = claim_run(run.pk)
    ExecutionSlot.objects.filter(run=run).update(claimed_at=old)
    RunBudget.objects.filter(run=run).update(day=old.date())
    call_command("operations_snapshot", prune=True, stdout=StringIO())
    assert RunBudget.objects.filter(run=run).exists() and AttemptMetric.objects.exists()
    assert ExecutionSlot.objects.get(run=run, fence=fence).released_at is None


def test_prune_removes_expired_never_started_cancelled_budget(run):
    old = timezone.localdate() - timedelta(days=40)
    cancel_run(run.owner, run.pk)
    RunBudget.objects.filter(run=run).update(day=old)
    call_command("operations_snapshot", prune=True, stdout=StringIO())
    assert not RunBudget.objects.filter(run=run).exists()


def test_framework_exception_logging_redacts_all_details():
    import logging

    from backend.core.logging import RedactedRequestLogFilter

    record = logging.LogRecord(
        "django.request",
        logging.ERROR,
        "private-media-path",
        1,
        "failed /api/assets/player-secret/media?token=secret %s",
        ("sensitive-body",),
        (ValueError, ValueError("secret"), None),
    )
    record.exc_text = "private traceback"
    record.stack_info = "private stack"
    assert RedactedRequestLogFilter().filter(record)
    assert record.getMessage() == '{"event":"http","reason":"SERVER_ERROR"}'
    assert record.exc_info is record.exc_text is record.stack_info is None


def test_upload_admission_rejects_before_body_when_time_budget_full(run, settings):
    from backend.core.security import reserve_upload

    run.owner.is_staff = True
    run.owner.save()
    settings.LOCAL_OPERATOR_UPLOADS = True
    settings.OWNER_PROCESSING_SECONDS_PER_DAY = 1260
    with pytest.raises(Throttled, match="budget reached"):
        reserve_upload(run.owner)


def test_rollback_refuses_outstanding_or_current_day_charges(run):
    from importlib import import_module

    from django.apps import apps

    guard = import_module(
        "backend.core.migrations.0010_operations_budgets"
    ).refuse_live_budget_rollback
    with pytest.raises(RuntimeError, match="drained holds"):
        guard(apps, None)
    fence = claim_run(run.pk)
    cancel_run(run.owner, run.pk)
    acknowledge_stopped(run.pk, fence)
    with pytest.raises(RuntimeError):
        guard(apps, None)
    RunBudget.objects.filter(run=run).update(day=timezone.localdate() - timedelta(days=1))
    guard(apps, None)


def test_partial_metric_window_is_visible_not_a_pass(run, settings):
    fence = claim_run(run.pk)
    assert measure(run, fence)
    settings.OPS_MAX_ATTEMPT_SAMPLES = 0
    data = snapshot()
    assert data["attempt_window_truncated"]
    assert "METRIC_WINDOW_TRUNCATED" in data["alerts"]
    assert data["objectives"]["processing_p95_seconds"]["state"] == "PARTIAL_WINDOW"


def test_cost_denominators_include_nonpositive_latest_results(run):
    from backend.core.models import (
        DefinitionVersion,
        DrillAssignment,
        EvaluationPlan,
        ImprovementEvaluation,
        TrainingSession,
    )

    drill = DefinitionVersion.objects.create(
        key="cost-synthetic", kind="drill", payload={"synthetic_only": True}
    )
    for index, status in enumerate(
        ["INCONCLUSIVE", "NO_MEANINGFUL_CHANGE", "OBSERVED_DETERIORATION", "NOT_COMPARABLE"]
    ):
        assignment = DrillAssignment.objects.create(owner=run.owner, drill=drill)
        plan = EvaluationPlan.objects.create(
            owner=run.owner, assignment=assignment, specification={"synthetic": index}
        )
        TrainingSession.objects.create(
            owner=run.owner, assignment=assignment, completed_at=timezone.now()
        )
        result = {
            "dataset_kind": "synthetic",
            "status": status,
            "verified_practice": 4,
            "baseline": {"denominator": 10},
            "followup": {"denominator": 10},
        }
        ImprovementEvaluation.objects.create(owner=run.owner, plan=plan, result=result, revision=1)
        if index == 0:
            ImprovementEvaluation.objects.create(
                owner=run.owner,
                plan=plan,
                result={**result, "status": "NOT_COMPARABLE"},
                revision=2,
            )
    data = costs(timezone.localdate(), timezone.localdate(), "SYNTHETIC")
    assert data["denominators"]["completed_loop"] == 4
    assert data["denominators"]["comparable_evaluation"] == 2
    assert data["total_usd"] is None


def test_upgrade_preserves_historical_unknowns_and_budget_rows(run):
    from importlib import import_module

    from django.apps import apps

    fence = claim_run(run.pk)
    legacy = ExecutionSlot.objects.create(run=run, fence=99, claimed_at=timezone.now())
    migration = import_module("backend.core.migrations.0012_preserve_unknown_attempt_dates")
    migration.clear_unmeasured_dates(apps, None)
    legacy.refresh_from_db()
    assert legacy.claimed_at is None
    assert ExecutionSlot.objects.get(run=run, fence=fence).claimed_at is not None
    assert totals(run.owner)["processing_held"] == 1260
    assert snapshot()["counts"]["historical_attempt_dates_unknown"] == 1
    with pytest.raises(RuntimeError, match="invented dates"):
        migration.refuse_unknown_date_rollback(apps, None)
