import json
from datetime import timedelta
from io import StringIO
from unittest.mock import Mock
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone
from rest_framework.test import APIClient

from backend.core.cloud import CloudFailure, GoogleControl, GooglePrivateStorage
from backend.core.consents import POLICY_VERSION, record_consent
from backend.core.control_journal import verified_records
from backend.core.dispatch import dispatch_pending, launch_dispatch, reconcile_cloud
from backend.core.jobs import (
    acknowledge_stopped,
    begin_execution,
    cancel_run,
    claim_run,
    enqueue_run,
    finish_run,
    heartbeat,
    reconcile_runs,
)
from backend.core.models import AnalysisRun, ExecutionSlot, Profile, ReplayAsset, RunDispatch
from backend.core.recovery import apply_restore_controls
from backend.core.storage import delete_account, delete_asset, private_path

pytestmark = pytest.mark.django_db


@pytest.fixture
def run(django_user_model, settings, tmp_path):
    settings.PRIVATE_DATA_ROOT = tmp_path / "media"
    owner = django_user_model.objects.create_user("worker", password="synthetic-password")
    asset_id = uuid4()
    asset = ReplayAsset.objects.create(
        id=asset_id, owner=owner, storage_key=f"{owner.pk}/{asset_id}/source.mp4", bytes=7
    )
    path = private_path(asset.storage_key)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"fixture")
    return enqueue_run(owner=owner, asset=asset, request_key="synthetic")


def test_outbox_is_atomic_with_producer(run):
    assert RunDispatch.objects.filter(run=run).count() == 1
    with pytest.raises(RuntimeError), transaction.atomic():
        enqueue_run(owner=run.owner, asset=run.asset, request_key="rollback")
        raise RuntimeError("rollback")
    assert AnalysisRun.objects.count() == RunDispatch.objects.count() == 1


def test_heartbeat_deadline_duplicate_entry_and_fencing(run):
    fence = claim_run(run.pk)
    assert begin_execution(run.pk, fence)
    assert not begin_execution(run.pk, fence)
    assert heartbeat(run.pk, fence, phase="PUBLISHING", progress=90)
    assert heartbeat(run.pk, fence, progress=10)
    run.refresh_from_db()
    assert run.progress == 90 and run.lease_until <= run.deadline_at
    AnalysisRun.objects.filter(pk=run.pk).update(deadline_at=timezone.now() - timedelta(seconds=1))
    assert not heartbeat(run.pk, fence)
    assert not finish_run(run.pk, fence, {"status": "COMPLETED"})


def test_stale_or_cancelled_execution_holds_capacity(run, django_user_model, settings):
    settings.GLOBAL_ACTIVE_RUNS = 1
    fence = claim_run(run.pk)
    other = django_user_model.objects.create_user("second-worker")
    asset = ReplayAsset.objects.create(owner=other, storage_key="second/source.mp4")
    second = enqueue_run(owner=other, asset=asset, request_key="second")
    AnalysisRun.objects.filter(pk=run.pk).update(lease_until=timezone.now() - timedelta(seconds=1))
    reconcile_runs()
    assert ExecutionSlot.objects.get(run=run).stop_requested_at
    assert claim_run(second.pk) is None
    cancel_run(run.owner, run.pk)
    assert claim_run(second.pk) is None
    acknowledge_stopped(run.pk, fence)
    assert claim_run(second.pk) is not None


def test_dispatch_retry_is_bounded_and_does_not_parse_media(run):
    provider = Mock()
    provider.enqueue.side_effect = CloudFailure("CLOUD_RETRYABLE")
    for _ in range(8):
        RunDispatch.objects.filter(run=run).update(next_attempt_at=timezone.now())
        dispatch_pending(provider)
    item = RunDispatch.objects.get(run=run)
    assert item.status == "ATTENTION" and item.attempts == 8
    assert not ExecutionSlot.objects.exists()
    assert not provider.launch.called


def test_dispatch_duplicate_delivery_and_ambiguous_launch(run, settings):
    settings.CLOUD_MEDIA_RUNTIME_QUALIFIED = True  # Controlled client only, no qualification claim.
    provider = Mock()
    provider.enqueue.return_value = "deterministic-task"
    dispatch_pending(provider)
    item = RunDispatch.objects.get(run=run)
    provider.launch.side_effect = CloudFailure("CLOUD_TRANSPORT_FAILURE", ambiguous=True)
    assert launch_dispatch(provider, item.pk, item.generation) == "UNCERTAIN"
    assert launch_dispatch(provider, item.pk, item.generation) == "IGNORED"
    assert provider.launch.call_count == 1
    assert ExecutionSlot.objects.get(run=run).released_at is None
    provider.observe_operation.return_value = ""
    reconcile_cloud(provider)
    assert ExecutionSlot.objects.get(run=run).released_at is None


def test_remote_stop_requires_authoritative_terminal_observation(run, settings):
    settings.CLOUD_MEDIA_RUNTIME_QUALIFIED = True
    provider = Mock()
    provider.launch.return_value = "operation"
    item = RunDispatch.objects.get(run=run)
    assert launch_dispatch(provider, item.pk, item.generation) == "SUBMITTED"
    cancel_run(run.owner, run.pk)
    provider.observe_operation.return_value = "execution"
    provider.execution_stopped.return_value = False
    reconcile_cloud(provider)
    assert ExecutionSlot.objects.get(run=run).released_at is None
    provider.cancel.assert_called_once_with("execution")
    provider.execution_stopped.return_value = True
    reconcile_cloud(provider)
    assert ExecutionSlot.objects.get(run=run).released_at is not None


def test_cloud_launch_and_restore_are_gated(run, settings):
    provider = Mock()
    item = RunDispatch.objects.get(run=run)
    with pytest.raises(CloudFailure, match="UNQUALIFIED"):
        launch_dispatch(provider, item.pk, item.generation)
    assert not provider.launch.called
    settings.RESTORE_QUARANTINE = True
    assert claim_run(run.pk) is None
    dispatch_pending(provider)
    assert not provider.enqueue.called
    client = APIClient()
    client.force_authenticate(run.owner)
    for url in ["/api/overview", f"/api/assets/{run.asset_id}/media", "/health/ready"]:
        assert client.get(url).status_code == 503


def test_task_endpoint_requires_verified_identity_and_exact_payload(run, settings, monkeypatch):
    client = APIClient()
    assert client.post("/internal/dispatch", {}, format="json").status_code == 503
    settings.CLOUD_MEDIA_RUNTIME_QUALIFIED = True
    assert client.post("/internal/dispatch", {}, format="json").status_code == 401
    monkeypatch.setattr("backend.core.cloud_api.verify_task_identity", lambda token: None)
    provider = Mock()
    provider.launch.return_value = "operation"
    monkeypatch.setattr("backend.core.cloud_api.configured_control", lambda: provider)
    item = RunDispatch.objects.get(run=run)
    payload = {"dispatch_id": str(item.pk), "generation": item.generation}
    assert (
        client.post(
            "/internal/dispatch",
            {**payload, "owner": run.owner_id},
            format="json",
            HTTP_AUTHORIZATION="Bearer test",
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/internal/dispatch", payload, format="json", HTTP_AUTHORIZATION="Bearer test"
        ).status_code
        == 200
    )
    assert provider.launch.call_count == 1


def test_health_probe_has_no_private_configuration(run):
    result = APIClient().get("/health/ready")
    assert result.status_code == 200 and result.json() == {"status": "READY"}


def test_worker_success_releases_slot_and_exposes_progress(run, monkeypatch):
    monkeypatch.setattr(
        "backend.core.management.commands.process_runs.analyze",
        lambda *args: {"status": "REVIEW_REQUIRED", "opportunities": []},
    )
    call_command("process_runs", once=True, stdout=StringIO())
    run.refresh_from_db()
    assert run.status == "REVIEW_REQUIRED" and run.progress == 100
    assert ExecutionSlot.objects.get(run=run).released_at
    client = APIClient()
    client.force_authenticate(run.owner)
    assert client.get(f"/api/runs/{run.pk}").json()["progress"] == 100


def test_unconfirmed_parser_cleanup_retains_capacity(run, monkeypatch):
    def failed(*args):
        raise ValueError("PARSER_CLEANUP_UNCONFIRMED")

    monkeypatch.setattr("backend.core.management.commands.process_runs.analyze", failed)
    call_command("process_runs", once=True, stdout=StringIO())
    assert ExecutionSlot.objects.get(run=run).released_at is None
    run.refresh_from_db()
    assert run.error_code == "PARSER_CLEANUP_UNCONFIRMED"


def test_managed_worker_result_does_not_release_host_execution(run, monkeypatch):
    fence = claim_run(run.pk)
    ExecutionSlot.objects.filter(run=run, fence=fence).update(runtime="CLOUD_RUN")
    monkeypatch.setattr(
        "backend.core.management.commands.process_runs.analyze",
        lambda *args: {"status": "REVIEW_REQUIRED", "opportunities": []},
    )
    call_command("process_runs", run_id=str(run.pk), fence=fence, stdout=StringIO())
    assert ExecutionSlot.objects.get(run=run).released_at is None
    run.refresh_from_db()
    assert run.status == "REVIEW_REQUIRED"


def test_journal_failure_prevents_account_mutation(run, settings, tmp_path):
    blocked = tmp_path / "file"
    blocked.write_text("not a directory")
    settings.CONTROL_JOURNAL_ROOT = blocked
    with pytest.raises(OSError):
        delete_account(run.owner)
    run.owner.refresh_from_db()
    run.asset.refresh_from_db()
    assert run.owner.is_active and run.asset.deleted_at is None


def test_restore_reapplies_deletion_withdrawal_and_invalidates_work(run, settings):
    record_consent(run.owner, "PROCESSING", "WITHDRAW", POLICY_VERSION, uuid4())
    delete_asset(run.owner, run.asset_id)
    records = verified_records()
    assert {r["action"] for r in records} == {"CONSENT_WITHDRAW", "ASSET_DELETE"}
    # Simulate restored earlier DB and media; native pg_dump test covers real restore.
    ReplayAsset.objects.filter(pk=run.asset_id).update(deleted_at=None, purge_completed_at=None)
    AnalysisRun.objects.filter(pk=run.pk).update(status="QUEUED")
    Profile.objects.filter(user=run.owner).update(
        processing_consent_at=timezone.now(), processing_withdrawn_at=None
    )
    path = private_path(run.asset.storage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fixture")
    settings.RESTORE_QUARANTINE = True
    assert apply_restore_controls() == 2
    assert apply_restore_controls() == 2
    assert not path.exists()
    assert Profile.objects.get(user=run.owner).processing_withdrawn_at
    assert AnalysisRun.objects.get(pk=run.pk).status == "CANCELLED"
    assert len(verified_records()) == 2


def test_tampered_journal_rejects_restore_before_mutating_database(run, settings):
    delete_asset(run.owner, run.asset_id)
    path = next(
        p for p in settings.CONTROL_JOURNAL_ROOT.glob("*.json") if p.name != "checkpoint.json"
    )
    envelope = json.loads(path.read_text())
    envelope["record"]["owner"] += 1
    path.write_text(json.dumps(envelope))
    settings.RESTORE_QUARANTINE = True
    with pytest.raises(ValueError, match="INVALID_CONTROL_JOURNAL"):
        apply_restore_controls()
    assert AnalysisRun.objects.get(pk=run.pk).phase == "QUEUED"


def test_missing_control_intent_is_detected_by_signed_checkpoint(run, settings):
    delete_asset(run.owner, run.asset_id)
    path = next(
        p for p in settings.CONTROL_JOURNAL_ROOT.glob("*.json") if p.name != "checkpoint.json"
    )
    path.unlink()
    with pytest.raises(ValueError, match="INVALID_CONTROL_JOURNAL"):
        verified_records()


def response(status=200, body=None):
    result = Mock(status_code=status)
    result.json.return_value = body or {}
    return result


def control(session):
    return GoogleControl(
        session,
        "projects/fixture-project/locations/fixture-region/queues/analysis",
        "projects/fixture-project/locations/fixture-region/jobs/analysis",
        "https://fixture.example/internal/dispatch",
        "tasks@fixture-project.iam.gserviceaccount.com",
    )


def test_official_tasks_request_oidc_deterministic_name_and_timeout():
    session = Mock()
    session.request.return_value = response(409)
    provider = control(session)
    dispatch = uuid4()
    assert provider.enqueue(dispatch, 2).endswith(f"dispatch-{dispatch}-2")
    kwargs = session.request.call_args.kwargs
    assert kwargs["allow_redirects"] is False and kwargs["timeout"] == (5, 20)
    task = kwargs["json"]["task"]
    assert task["httpRequest"]["oidcToken"]["audience"] == provider.target
    assert task["dispatchDeadline"] == "60s"


def test_official_job_launch_timeout_is_ambiguous(settings):
    settings.CLOUD_MEDIA_RUNTIME_QUALIFIED = True
    session = Mock()
    session.request.side_effect = TimeoutError("secret transport text")
    with pytest.raises(CloudFailure) as failure:
        control(session).launch(uuid4(), 1, uuid4(), 1)
    assert failure.value.ambiguous and str(failure.value) == "CLOUD_TRANSPORT_FAILURE"


def test_cloud_operation_completion_is_not_execution_completion():
    session = Mock()
    provider = control(session)
    execution = provider.job + "/executions/analysis-123"
    session.request.return_value = response(body={"done": True, "metadata": {"name": execution}})
    assert (
        provider.observe_operation(
            "projects/fixture-project/locations/fixture-region/operations/op"
        )
        == execution
    )
    assert not provider.execution_stopped(execution)
    session.request.return_value = response(
        body={"completionTime": "2026-10-02T00:00:00Z", "runningCount": 0}
    )
    assert provider.execution_stopped(execution)


def test_private_storage_pins_generation_and_purges_versions():
    session = Mock()
    asset = uuid4()
    key = f"7/{asset}/source.mp4"
    store = GooglePrivateStorage(session, "fixture-private-bucket", 7, asset)
    session.request.side_effect = [
        response(
            body={"items": [{"name": key, "generation": "11"}, {"name": key, "generation": "12"}]}
        ),
        response(204),
        response(404),
    ]
    store.delete_asset(key)
    deletes = [call for call in session.request.call_args_list if call.args[0] == "DELETE"]
    assert [call.kwargs["params"] for call in deletes] == [
        {"generation": "11", "ifGenerationMatch": "11"},
        {"generation": "12", "ifGenerationMatch": "12"},
    ]
    with pytest.raises(ValueError, match="OWNERSHIP"):
        store.delete_asset("8/other/source.mp4")
    with pytest.raises(CloudFailure, match="NOT_QUALIFIED"):
        store.cancel_upload("https://untrusted.example/session")


@pytest.mark.parametrize(
    "blocks,size,valid",
    [([b"abc", b"def"], 6, True), ([b"too-long"], 2, False), ([b"short"], 6, False)],
)
def test_private_storage_download_is_generation_pinned_and_bounded(tmp_path, blocks, size, valid):
    session = Mock()
    session.request.return_value = response()
    session.request.return_value.iter_content.return_value = blocks
    asset = uuid4()
    store = GooglePrivateStorage(session, "fixture-private-bucket", 7, asset)
    if valid:
        store.download(f"7/{asset}/source.mp4", "11", tmp_path / "source.mp4", size)
    else:
        with pytest.raises(ValueError, match="SIZE_CHANGED"):
            store.download(f"7/{asset}/source.mp4", "11", tmp_path / "source.mp4", size)
    assert session.request.call_args.kwargs["params"]["ifGenerationMatch"] == "11"
    session.request.return_value.close.assert_called_once()
