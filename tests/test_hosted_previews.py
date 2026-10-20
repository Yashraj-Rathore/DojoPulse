"""Real API/coordinator boundaries with controlled official HTTP clients, never live GCP."""

import base64
import copy
import hashlib
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from types import SimpleNamespace
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from backend.core import cloud_execution, cloud_journal, previews
from backend.core.batch_preview import GoogleBatchPreview
from backend.core.cloud import CloudFailure
from backend.core.cloud_journal import CloudLog
from backend.core.control_journal import record_intent, verified_records
from backend.core.dispatch import launch_dispatch
from backend.core.jobs import cancel_run, claim_run, heartbeat
from backend.core.models import (
    AnalysisRun,
    ExecutionSlot,
    GameplayEvent,
    Match,
    RecordingPreview,
    RunDispatch,
    UploadSession,
)
from backend.core.preview_ledger import LedgerFailure, ledger
from backend.core.recordings import require_local_operator, require_preview_operator
from backend.core.resumable import verify
from tests import test_private_previews as fixtures

owner = fixtures.owner
pytestmark = pytest.mark.django_db(transaction=True)


class Response:
    def __init__(self, status=200, body=None, *, raw=None, headers=None):
        self.status_code, self.headers = status, headers or {}
        self.raw = json.dumps(body or {}).encode() if raw is None else raw

    def iter_content(self, chunk_size):
        for offset in range(0, len(self.raw), chunk_size):
            yield self.raw[offset : offset + chunk_size]

    def json(self):
        return json.loads(self.raw)

    def close(self):
        pass


class FakeGoogle:
    def __init__(self):
        self.objects, self.sessions, self.jobs, self.operations, self.nodes = {}, {}, {}, {}, {}
        self.calls, self.counter = [], 0
        self.lock = threading.RLock()
        self.fail_list, self.fail_delete, self.lose_create, self.lose_chunk = (
            False,
            False,
            False,
            False,
        )
        self.unreachable = False

    def metadata(self, bucket, key):
        item = self.objects[bucket, key]
        return {
            "bucket": bucket,
            "name": key,
            "generation": str(item["generation"]),
            "size": str(len(item["raw"])),
            "md5Hash": base64.b64encode(
                hashlib.md5(item["raw"], usedforsecurity=False).digest()
            ).decode(),
            "contentType": "video/mp4" if key.endswith(".mp4") else "application/json",
            "metadata": item.get("metadata", {}),
        }

    def put(self, bucket, key, raw):
        self.counter += 1
        self.objects[bucket, key] = {"generation": self.counter, "raw": raw}
        return self.metadata(bucket, key)

    def request(self, method, url, **kwargs):
        with self.lock:
            assert kwargs["allow_redirects"] is False and kwargs["timeout"] == (5, 20)
            self.calls.append((method, url, copy.deepcopy(kwargs.get("params", {}))))
            path = urlparse(url)
            params = {k: v[0] for k, v in parse_qs(path.query).items()} | kwargs.get("params", {})
            if path.hostname == "batch.googleapis.com":
                name = path.path.removeprefix("/v1/")
                if method == "POST":
                    job = name + "/" + params["jobId"]
                    if job in self.jobs:
                        return Response(409)
                    uid = "batch-" + uuid4().hex
                    body = {
                        **copy.deepcopy(kwargs["json"]),
                        "name": job,
                        "uid": uid,
                        "status": {"state": "RUNNING"},
                    }
                    body["labels"]["batch-job-id"] = params["jobId"]
                    self.jobs[job], self.nodes[uid] = body, True
                    if self.lose_create:
                        self.lose_create = False
                        raise TimeoutError("controlled response loss")
                    return Response(200, body)
                if "/operations/" in name:
                    return (
                        Response(200, self.operations[name])
                        if name in self.operations
                        else Response(404)
                    )
                if method == "GET":
                    return Response(200, self.jobs[name]) if name in self.jobs else Response(404)
                if method == "DELETE":
                    if self.fail_delete:
                        return Response(503)
                    if name not in self.jobs:
                        return Response(404)
                    self.jobs.pop(name)
                    operation = name.split("/jobs/")[0] + "/operations/delete-" + uuid4().hex
                    self.operations[operation] = {"name": operation, "done": False}
                    return Response(200, self.operations[operation])
            if path.hostname == "compute.googleapis.com":
                if self.unreachable:
                    return Response(200, {"unreachables": ["zone-a"]})
                uid = re.search(r'"([A-Za-z0-9_-]+)"', params["filter"])[1]
                return Response(
                    200,
                    {
                        "items": {"zones/test": {"instances": [{"id": "1"}]}}
                        if self.nodes.get(uid)
                        else {}
                    },
                )
            assert path.hostname == "storage.googleapis.com", "Unexpected endpoint"
            match = re.fullmatch(r"/(upload/)?storage/v1/b/([^/]+)/o(?:/(.*))?", path.path)
            assert match
            upload, bucket, encoded = match.groups()
            key = unquote(encoded) if encoded else params.get("name")
            if upload and method == "POST" and params.get("uploadType") == "resumable":
                assert params["ifGenerationMatch"] == "0"
                token = uuid4().hex
                self.sessions[token] = {
                    "bucket": bucket,
                    "key": key,
                    "raw": b"",
                    "stopped": False,
                    "metadata": kwargs.get("json", {}).get("metadata", {}),
                }
                location = (
                    f"https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o?"
                    + urlencode(
                        {
                            "uploadType": "resumable",
                            "name": key,
                            "upload_id": token,
                            "ifGenerationMatch": "0",
                        }
                    )
                )
                return Response(200, headers={"Location": location})
            if upload and params.get("upload_id"):
                session = self.sessions[params["upload_id"]]
                if method == "DELETE":
                    if self.fail_delete:
                        return Response(503)
                    session["stopped"] = True
                    return Response(499)
                if session["stopped"]:
                    return Response(410)
                block = kwargs.get("data", b"")
                if not block and (bucket, session["key"]) not in self.objects:
                    return Response(308)
                if block:
                    session["raw"] += block
                    self.put(bucket, session["key"], session["raw"])
                    self.objects[bucket, session["key"]]["metadata"] = session["metadata"]
                    if self.lose_chunk:
                        self.lose_chunk = False
                        raise TimeoutError("controlled upload response loss")
                return Response(200, self.metadata(bucket, session["key"]))
            if upload and method == "POST":
                assert params["ifGenerationMatch"] == "0"
                if (bucket, key) in self.objects:
                    return Response(412)
                return Response(200, self.put(bucket, key, kwargs["data"]))
            if key is None:
                if self.fail_list:
                    return Response(503)
                items = [
                    self.metadata(b, k)
                    for b, k in sorted(self.objects)
                    if b == bucket and k.startswith(params.get("prefix", ""))
                ]
                offset, size = int(params.get("pageToken", 0)), int(params.get("maxResults", 128))
                body = {"items": items[offset : offset + size]}
                if len(items) > offset + size:
                    body["nextPageToken"] = str(offset + size)
                return Response(200, body)
            if (bucket, key) not in self.objects:
                return Response(404)
            if "generation" in params and str(self.objects[bucket, key]["generation"]) != str(
                params["generation"]
            ):
                return Response(412)
            if method == "DELETE":
                if self.fail_delete:
                    return Response(503)
                self.objects.pop((bucket, key))
                return Response(204)
            if params.get("alt") == "media":
                raw = self.objects[bucket, key]["raw"]
                if "Range" in kwargs.get("headers", {}):
                    start, end = map(int, kwargs["headers"]["Range"][6:].split("-"))
                    return Response(
                        206,
                        raw=raw[start : end + 1],
                        headers={"Content-Range": f"bytes {start}-{end}/{len(raw)}"},
                    )
                return Response(200, raw=raw)
            return Response(200, self.metadata(bucket, key))

    def finish_deletion(self):
        self.nodes = {uid: False for uid in self.nodes}
        for operation in self.operations.values():
            operation["done"] = True


@pytest.fixture
def cloud(owner, settings, monkeypatch):
    settings.PREVIEW_LEDGER_RUNTIME_QUALIFIED = True
    settings.CLOUD_MEDIA_RUNTIME_QUALIFIED = True
    settings.CLOUD_PREVIEW_RUNTIME_QUALIFIED = True
    settings.GCS_PREVIEW_WRITES_QUALIFIED = True
    settings.GCS_STORAGE_QUALIFIED = True
    settings.PREVIEW_LEDGER_BACKEND = settings.CONTROL_JOURNAL_BACKEND = "GCS"
    settings.PREVIEW_CLOUD_BACKEND = "BATCH"
    settings.GCS_PRIVATE_BUCKET = "private-media"
    settings.GOOGLE_PREVIEW_LEDGER_BUCKET = "preview-journal"
    settings.GOOGLE_CONTROL_JOURNAL_BUCKET = "control-journal"
    settings.GOOGLE_EXECUTION_JOURNAL_BUCKET = "execution-journal"
    settings.GOOGLE_BATCH_PARENT = "projects/dojo-test/locations/us-central1"
    settings.GOOGLE_BATCH_TEMPLATE = "projects/dojo-test/global/instanceTemplates/preview-v001"
    settings.GOOGLE_PREVIEW_COORDINATOR_IMAGE = (
        "us-central1-docker.pkg.dev/dojo-test/images/coordinator@sha256:" + "a" * 64
    )
    settings.GOOGLE_PREVIEW_DECODER_IMAGE = (
        "us-central1-docker.pkg.dev/dojo-test/images/decoder@sha256:" + "b" * 64
    )
    settings.GOOGLE_PREVIEW_SERVICE_ACCOUNT = "preview@dojo-test.iam.gserviceaccount.com"
    settings.GOOGLE_PREVIEW_ENV = {
        "DEPLOYMENT_NAMESPACE": settings.DEPLOYMENT_NAMESPACE,
        "GCS_PRIVATE_BUCKET": settings.GCS_PRIVATE_BUCKET,
        "GOOGLE_PREVIEW_LEDGER_BUCKET": settings.GOOGLE_PREVIEW_LEDGER_BUCKET,
        "GOOGLE_CONTROL_JOURNAL_BUCKET": settings.GOOGLE_CONTROL_JOURNAL_BUCKET,
        "GOOGLE_EXECUTION_JOURNAL_BUCKET": settings.GOOGLE_EXECUTION_JOURNAL_BUCKET,
    }
    settings.GOOGLE_PREVIEW_SECRETS = {
        key: f"projects/dojo-test/secrets/{key}/versions/1"
        for key in [
            "DATABASE_URL",
            "DJANGO_SECRET_KEY",
            "DATA_SUPPRESSION_KEY",
            "CONTROL_JOURNAL_KEY",
            "PREVIEW_LEDGER_KEY",
        ]
    }
    fake = FakeGoogle()
    with cloud_journal._cache_lock:
        cloud_journal._cache.clear()
        cloud_journal._cache_bytes = 0
    monkeypatch.setattr(cloud_journal, "authorized_session", lambda: fake)
    monkeypatch.setattr("backend.core.batch_preview.authorized_session", lambda: fake)
    monkeypatch.setattr("backend.core.cloud.authorized_session", lambda: fake)
    monkeypatch.setattr("backend.core.preview_writes.authorized_session", lambda: fake)
    for kind in ("preview", "control", "execution"):
        CloudLog(kind).initialize()
    return fake


def queued(owner, cloud):
    source = fixtures.asset(owner)
    source.storage_provider, source.storage_generation = "GCS", "1"
    source.save()
    metadata = cloud.put("private-media", source.storage_key, b"owner-source")
    source.storage_generation = metadata["generation"]
    source.save()
    preview = previews.enqueue_preview(owner, source.pk, uuid4())
    return source, preview, RunDispatch.objects.get(run=preview.run)


def test_independent_writers_arbitrate_sequences_and_reader_detects_missing_middle(cloud):
    def append(index):
        CloudLog("control").update(lambda records: {"index": index})

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(append, range(4)))
    history, _ = CloudLog("control").records()
    assert sorted(row["index"] for row in history) == list(range(4))
    cloud.objects.pop(("control-journal", CloudLog("control").prefix + "00000002.json"))
    with pytest.raises(LedgerFailure, match="GAP"):
        CloudLog("control").records()


def test_cloud_journals_require_explicit_bootstrap_and_gates(owner, cloud, settings):
    cloud.objects = {
        key: value for key, value in cloud.objects.items() if key[0] != "preview-journal"
    }
    with pytest.raises(LedgerFailure, match="UNINITIALIZED"):
        ledger().records()
    settings.PREVIEW_LEDGER_RUNTIME_QUALIFIED = False
    before = len(cloud.calls)
    with pytest.raises(LedgerFailure, match="UNQUALIFIED"):
        CloudLog("preview")
    assert len(cloud.calls) == before


def test_fresh_inventory_detects_replaced_tail_despite_generation_cache(cloud):
    log = CloudLog("control")
    log.update(lambda records: {"action": "original"})
    assert log.records()[0] == [{"action": "original"}]
    key = log.prefix + "00000001.json"
    raw = cloud.objects["control-journal", key]["raw"]
    cloud.put("control-journal", key, raw.replace(b"original", b"tampered"))
    with pytest.raises(LedgerFailure, match="SIGNATURE"):
        log.records()


def test_lost_append_response_is_resolved_only_by_identical_read_receipt(cloud, monkeypatch):
    original = cloud.request

    def lose_response(method, url, **kwargs):
        result = original(method, url, **kwargs)
        if method == "POST" and "/upload/storage/" in url:
            raise TimeoutError("controlled response loss after commit")
        return result

    monkeypatch.setattr(cloud, "request", lose_response)
    log = CloudLog("control")
    log.update(lambda records: {"once": True})
    assert log.records()[0] == [{"once": True}]


def test_maintenance_overlap_exits_before_any_cloud_rpc(owner, cloud):
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL advisory-lock contract")
    holder = connection.copy()
    try:
        with holder.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_lock(%s)", [1146047056])
        before = len(cloud.calls)
        output = StringIO()
        call_command("hosted_preview_maintenance", stdout=output)
        assert "already active" in output.getvalue() and len(cloud.calls) == before
    finally:
        holder.close()  # Session-scoped lock cannot survive this connection.


def test_control_intent_survives_sql_rollback_without_local_journal(owner, cloud, settings):
    with pytest.raises(RuntimeError), transaction.atomic():
        record_intent(owner.pk, "CONSENT_WITHDRAW", scope="PROCESSING")
        raise RuntimeError("SQL rollback")
    assert verified_records()[0]["payload"] == {"scope": "PROCESSING"}
    assert not settings.CONTROL_JOURNAL_ROOT.exists()


def test_batch_preview_conversion_owned_range_and_stop_before_slot_refund(
    owner, cloud, monkeypatch, settings
):
    settings.PARSER_BACKEND = "docker"
    source, preview, dispatch = queued(owner, cloud)
    provider = GoogleBatchPreview()
    assert launch_dispatch(provider, dispatch.pk, dispatch.generation) == "SUBMITTED"
    slot = ExecutionSlot.objects.get(run=preview.run)
    assert slot.runtime == "CLOUD_BATCH"
    row = next(iter(cloud_execution.records().values()))
    spec = row["spec"]["taskGroups"][0]["taskSpec"]
    assert spec["maxRetryCount"] == 0 and spec["maxRunDuration"] == "1920s"
    assert "@sha256:" in spec["runnables"][0]["script"]["text"]

    def normalize(path, root, name):
        fixtures.bundle(root, source.source_sha256)
        return {"contract": "controlled-offline"}

    monkeypatch.setattr("backend.core.preview_sandbox.normalize_isolated", normalize)
    monkeypatch.setattr(
        "backend.core.management.commands.run_preview_batch.run_bounded",
        lambda *args, **kwargs: SimpleNamespace(
            stdout=json.dumps(
                {
                    "Id": "sha256:" + "c" * 64,
                    "RepoDigests": [provider.decoder],
                }
            ).encode()
        ),
    )
    call_command("run_preview_batch", run_id=str(preview.run_id), fence=slot.fence)
    preview.refresh_from_db()
    assert (
        preview.state == "READY"
        and not Match.objects.exists()
        and not GameplayEvent.objects.exists()
    )
    assert not preview.quality["precise_gameplay_analysis_approved"]
    client = APIClient()
    client.force_authenticate(owner)
    response = client.get(f"/api/assets/{source.pk}/preview/media", HTTP_RANGE="bytes=0-9")
    assert response.status_code == 206 and len(b"".join(response.streaming_content)) == 10
    response.close()
    cloud_execution.reconcile(provider)
    assert ExecutionSlot.objects.get(pk=slot.pk).released_at is None
    cloud.finish_deletion()
    cloud_execution.reconcile(provider)
    assert ExecutionSlot.objects.get(pk=slot.pk).released_at is not None
    assert next(iter(cloud_execution.records().values()))["state"] == "STOPPED"


def test_ambiguous_create_is_not_retried_and_reconciler_keeps_capacity_until_vm_stop(owner, cloud):
    _, preview, dispatch = queued(owner, cloud)
    cloud.lose_create = True
    provider = GoogleBatchPreview()
    assert launch_dispatch(provider, dispatch.pk, dispatch.generation) == "UNCERTAIN"
    assert launch_dispatch(provider, dispatch.pk, dispatch.generation) == "IGNORED"
    assert (
        sum(method == "POST" and "batch.googleapis.com" in url for method, url, _ in cloud.calls)
        == 1
    )
    slot = ExecutionSlot.objects.get(run=preview.run)
    slot.stop_requested_at = timezone.now()
    slot.save()
    cloud_execution.reconcile(provider)
    assert ExecutionSlot.objects.get(pk=slot.pk).released_at is None
    cloud.finish_deletion()
    cloud_execution.reconcile(provider)
    assert ExecutionSlot.objects.get(pk=slot.pk).released_at is not None


def test_missing_create_receipt_and_absent_job_fail_restore_closed(owner, cloud):
    _, preview, dispatch = queued(owner, cloud)
    provider = GoogleBatchPreview()
    assert launch_dispatch(provider, dispatch.pk, dispatch.generation) == "SUBMITTED"
    cloud.jobs.clear()
    with pytest.raises(LedgerFailure, match="UNCONFIRMED"):
        cloud_execution.reconcile(provider, restore=True)
    assert ExecutionSlot.objects.get(run=preview.run).released_at is None


def test_archive_outage_after_successful_create_never_refunds_running_worker(
    owner, cloud, monkeypatch
):
    _, preview, dispatch = queued(owner, cloud)
    request = cloud.request

    def lose_archive_after_creation(method, url, **kwargs):
        response = request(method, url, **kwargs)
        if method == "POST" and "batch.googleapis.com" in url:
            cloud.fail_list = True
        return response

    monkeypatch.setattr(cloud, "request", lose_archive_after_creation)
    provider = GoogleBatchPreview()
    assert launch_dispatch(provider, dispatch.pk, dispatch.generation) == "UNCERTAIN"
    assert cloud.jobs and ExecutionSlot.objects.get(run=preview.run).released_at is None
    cloud.fail_list = False
    with pytest.raises(LedgerFailure, match="UNCONFIRMED"):
        cloud_execution.reconcile(provider, restore=True)
    cloud.finish_deletion()
    cloud_execution.reconcile(provider, restore=True)
    assert ExecutionSlot.objects.get(run=preview.run).released_at


def test_restore_stops_post_backup_worker_with_no_sql_slot_and_keeps_orphan_source_quota(
    owner, cloud
):
    source, preview, dispatch = queued(owner, cloud)
    provider = GoogleBatchPreview()
    launch_dispatch(provider, dispatch.pk, dispatch.generation)
    ExecutionSlot.objects.all().delete()
    assert cloud_execution.extra_slots() == 1
    with pytest.raises(LedgerFailure, match="UNCONFIRMED"):
        cloud_execution.reconcile(provider, restore=True)
    cloud.finish_deletion()
    cloud_execution.reconcile(provider, restore=True)
    assert cloud_execution.extra_slots() == 0
    # SQL snapshot missing the source cannot implicitly refund its retained object.
    assert source.bytes > 0 and ("private-media", source.storage_key) in cloud.objects
    size = source.bytes
    RecordingPreview.objects.filter(pk=preview.pk).delete()
    AnalysisRun.objects.filter(pk=preview.run_id).delete()
    source.delete()
    assert cloud_execution.extra_storage(owner.pk) == size


def test_http_upload_verification_queues_batch_preview_without_canonical_claims(
    owner, cloud, settings
):
    settings.RESUMABLE_STORAGE_PROVIDER = "GCS"
    client = APIClient()
    client.force_authenticate(owner)
    data = b"controlled playback-only source"
    response = client.post(
        "/api/upload-sessions",
        {
            "request_id": str(uuid4()),
            "filename": "capture.mp4",
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "md5": base64.b64encode(hashlib.md5(data, usedforsecurity=False).digest()).decode(),
            "processing_consent": True,
            "single_continuous": False,
            "preview_only": True,
            "metadata": {},
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    info = response.json()
    cloud.request(
        "PUT",
        info["upload_url"],
        data=data,
        timeout=(5, 20),
        allow_redirects=False,
        headers={"Content-Range": f"bytes 0-{len(data) - 1}/{len(data)}"},
    )
    response = client.post(f"/api/upload-sessions/{info['id']}/complete", {}, format="json")
    assert response.status_code == 202
    verify(UploadSession.objects.get().pk)
    preview = RecordingPreview.objects.get()
    dispatch = RunDispatch.objects.get(run=preview.run)
    assert launch_dispatch(GoogleBatchPreview(), dispatch.pk, dispatch.generation) == "SUBMITTED"
    assert not Match.objects.exists() and not GameplayEvent.objects.exists()


def test_vm_inventory_outage_does_not_release_completed_deletion(owner, cloud):
    _, preview, dispatch = queued(owner, cloud)
    provider = GoogleBatchPreview()
    launch_dispatch(provider, dispatch.pk, dispatch.generation)
    with pytest.raises(LedgerFailure):
        cloud_execution.reconcile(provider, restore=True)
    cloud.finish_deletion()
    cloud.unreachable = True
    with pytest.raises(CloudFailure, match="INVENTORY"):
        cloud_execution.reconcile(provider, restore=True)
    assert ExecutionSlot.objects.get(run=preview.run).released_at is None


def test_batch_unknown_uid_or_foreign_contract_never_authorizes_delete(owner, cloud):
    _, preview, dispatch = queued(owner, cloud)
    provider = GoogleBatchPreview()
    launch_dispatch(provider, dispatch.pk, dispatch.generation)
    job = next(iter(cloud.jobs.values()))
    job["labels"]["spec-a"] = "f" * 32
    with pytest.raises(CloudFailure, match="IDENTITY"):
        cloud_execution.reconcile(provider, restore=True)
    assert not cloud.operations and ExecutionSlot.objects.get(run=preview.run).released_at is None


def test_runtime_and_secret_versions_are_not_implicitly_qualified(owner, cloud, settings):
    settings.CLOUD_PREVIEW_RUNTIME_QUALIFIED = False
    with pytest.raises(CloudFailure, match="UNQUALIFIED"):
        GoogleBatchPreview()
    settings.CLOUD_PREVIEW_RUNTIME_QUALIFIED = True
    settings.GOOGLE_PREVIEW_SECRETS = {
        "DATABASE_URL": "projects/dojo-test/secrets/db/versions/latest"
    }
    provider = GoogleBatchPreview()
    with pytest.raises(ValueError, match="REFERENCES"):
        provider.spec(uuid4(), 1, uuid4(), 1, 1920)


def test_invalid_batch_configuration_never_claims_a_physical_slot(owner, cloud, settings):
    _, preview, dispatch = queued(owner, cloud)
    settings.GOOGLE_PREVIEW_SECRETS = {}
    assert launch_dispatch(GoogleBatchPreview(), dispatch.pk, dispatch.generation) == "ATTENTION"
    assert not ExecutionSlot.objects.exists() and not cloud.jobs
    assert not cloud_execution.records()
    assert AnalysisRun.objects.get(pk=preview.run_id).status == "QUEUED"


def test_full_restore_keeps_quarantine_until_vm_stop_then_preserves_original(
    owner, cloud, settings, monkeypatch
):
    from backend.core.recovery import apply_restore_controls

    source, preview, dispatch = queued(owner, cloud)
    launch_dispatch(GoogleBatchPreview(), dispatch.pk, dispatch.generation)
    settings.RESTORE_QUARANTINE = True
    # Controlled inventory for the local orphan-container sweep; no Docker is run.
    monkeypatch.setattr(
        "backend.core.previews.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=b"", stderr=b""),
    )
    with pytest.raises(LedgerFailure, match="UNCONFIRMED"):
        apply_restore_controls()
    assert settings.RESTORE_QUARANTINE and not heartbeat(preview.run_id, 1)
    cloud.finish_deletion()
    apply_restore_controls()
    apply_restore_controls()
    assert not ExecutionSlot.objects.filter(released_at=None).exists()
    assert ("private-media", source.storage_key) in cloud.objects
    assert not Match.objects.exists() and not GameplayEvent.objects.exists()


def test_cancel_before_any_output_plan_survives_sql_rollback(owner, cloud):
    _, preview, dispatch = queued(owner, cloud)
    provider = GoogleBatchPreview()
    launch_dispatch(provider, dispatch.pk, dispatch.generation)
    slot = ExecutionSlot.objects.get(run=preview.run)
    assert not ledger().records()  # The decoder has not produced/published artifacts yet.
    with pytest.raises(RuntimeError), transaction.atomic():
        cancel_run(owner, preview.run_id)
        raise RuntimeError("cancel SQL rolled back")
    assert AnalysisRun.objects.get(pk=preview.run_id).status == "PROCESSING"
    assert not heartbeat(preview.run_id, slot.fence)
    assert claim_run(preview.run_id) is None
    cloud_execution.reconcile(provider)
    cloud.finish_deletion()
    cloud_execution.reconcile(provider)
    assert ExecutionSlot.objects.get(pk=slot.pk).released_at is not None
    assert cloud_execution.run_revoked(preview.run_id)


def test_queued_cancel_without_any_attempt_survives_sql_rollback(owner, cloud):
    _, preview, _ = queued(owner, cloud)
    with pytest.raises(RuntimeError), transaction.atomic():
        cancel_run(owner, preview.run_id)
        raise RuntimeError("queued cancellation SQL rolled back")
    assert AnalysisRun.objects.get(pk=preview.run_id).status == "QUEUED"
    assert not cloud_execution.records() and cloud_execution.run_revoked(preview.run_id)
    assert claim_run(preview.run_id) is None
    assert not ExecutionSlot.objects.exists() and not cloud.jobs


def test_cancel_between_claim_and_plan_never_creates_worker(owner, cloud, monkeypatch):
    _, preview, dispatch = queued(owner, cloud)
    provider = GoogleBatchPreview()
    launch = provider.launch

    def cancel_before_plan(*args, **kwargs):
        with pytest.raises(RuntimeError), transaction.atomic():
            cancel_run(owner, preview.run_id)
            raise RuntimeError("cancellation SQL rolled back")
        return launch(*args, **kwargs)

    monkeypatch.setattr(provider, "launch", cancel_before_plan)
    assert launch_dispatch(provider, dispatch.pk, dispatch.generation) == "ATTENTION"
    assert not cloud.jobs and not ExecutionSlot.objects.filter(released_at=None).exists()


def test_already_stopped_independent_attempt_releases_restored_sql_slot(owner, cloud):
    _, preview, dispatch = queued(owner, cloud)
    provider = GoogleBatchPreview()
    launch_dispatch(provider, dispatch.pk, dispatch.generation)
    cloud_execution.reconcile(provider, restore=False)
    cloud_execution.stop_runs([preview.run_id])
    cloud_execution.reconcile(provider)
    cloud.finish_deletion()
    cloud_execution.reconcile(provider)
    slot = ExecutionSlot.objects.get(run=preview.run)
    assert slot.released_at
    ExecutionSlot.objects.filter(pk=slot.pk).update(released_at=None)
    cloud_execution.reconcile(provider, restore=True)
    assert ExecutionSlot.objects.get(pk=slot.pk).released_at is not None


def test_shared_store_outage_blocks_admission_and_control_changes(owner, cloud):
    cloud.fail_list = True
    with pytest.raises(CloudFailure), transaction.atomic():
        record_intent(owner.pk, "ACCOUNT_DELETE")
    with pytest.raises(CloudFailure):
        queued(owner, cloud)
    assert not AnalysisRun.objects.exists()


def test_cloud_task_handler_uses_batch_and_duplicate_delivery_does_not_create_again(
    owner, cloud, monkeypatch
):
    _, preview, dispatch = queued(owner, cloud)
    monkeypatch.setattr("backend.core.cloud_api.verify_task_identity", lambda token: None)
    client = APIClient()
    payload = {"dispatch_id": str(dispatch.pk), "generation": dispatch.generation}
    response = client.post(
        "/internal/dispatch", payload, format="json", HTTP_AUTHORIZATION="Bearer controlled"
    )
    assert response.status_code == 200 and response.json()["status"] == "SUBMITTED"
    response = client.post(
        "/internal/dispatch", payload, format="json", HTTP_AUTHORIZATION="Bearer controlled"
    )
    assert response.status_code == 200 and response.json()["status"] == "IGNORED"
    assert (
        len(cloud.jobs) == 1 and ExecutionSlot.objects.get(run=preview.run).runtime == "CLOUD_BATCH"
    )


def test_late_create_receipt_cannot_revive_a_revoked_attempt(owner, cloud, monkeypatch):
    _, preview, dispatch = queued(owner, cloud)
    provider = GoogleBatchPreview()
    create = provider.create

    def delayed(row):
        uid = create(row)
        cloud_execution.stop_runs([preview.run_id])
        return uid

    monkeypatch.setattr(provider, "create", delayed)
    launch_dispatch(provider, dispatch.pk, dispatch.generation)
    row = next(iter(cloud_execution.records().values()))
    assert row["uid"] and row["revoked"] and row["state"] == "STOPPING"
    assert not cloud_execution.allowed(preview.run_id, row["fence"])


def test_disabling_dispatch_backend_does_not_hide_existing_execution_holds(owner, cloud, settings):
    _, preview, dispatch = queued(owner, cloud)
    launch_dispatch(GoogleBatchPreview(), dispatch.pk, dispatch.generation)
    ExecutionSlot.objects.all().delete()
    settings.PREVIEW_CLOUD_BACKEND = "DISABLED"
    assert cloud_execution.extra_slots() == 1


def test_hosted_preview_admission_does_not_enable_legacy_analysis(owner, cloud, settings):
    settings.DEBUG = False
    settings.LOCAL_OPERATOR_UPLOADS = False
    settings.RESUMABLE_STORAGE_PROVIDER = "GCS"
    with pytest.raises(PermissionDenied):
        require_preview_operator(owner)
    settings.HOSTED_PREVIEW_UPLOADS_QUALIFIED = True
    require_preview_operator(owner)
    with pytest.raises(PermissionDenied):
        require_local_operator(owner)
    owner.is_staff = False
    with pytest.raises(PermissionDenied):
        require_preview_operator(owner)


def test_worker_and_scheduled_maintenance_fail_before_network_when_unqualified(owner, settings):
    settings.CLOUD_PREVIEW_RUNTIME_QUALIFIED = False
    with pytest.raises(CommandError, match="UNQUALIFIED"):
        call_command("run_preview_batch", run_id=str(uuid4()), fence=1)
    with pytest.raises(CommandError, match="UNQUALIFIED"):
        call_command("hosted_preview_maintenance")


def test_task_identity_audience_is_service_origin_not_dispatch_path(owner, cloud, settings):
    from unittest.mock import Mock

    from backend.core.cloud import GoogleControl

    settings.GOOGLE_TASK_GATEWAY_HOST = "api.example"
    session = Mock()
    session.request.return_value.status_code = 200
    provider = GoogleControl(
        session,
        "projects/dojo-test/locations/us-central1/queues/preview",
        "projects/dojo-test/locations/us-central1/jobs/disabled-analysis",
        "https://dojo-api-abc.a.run.app/internal/dispatch",
        "api@dojo-test.iam.gserviceaccount.com",
        audience="https://dojo-api-abc.a.run.app",
    )
    provider.enqueue(uuid4(), 1)
    request = session.request.call_args.kwargs["json"]["task"]["httpRequest"]
    assert request["oidcToken"]["audience"] == "https://dojo-api-abc.a.run.app"
    assert request["url"].endswith("/internal/dispatch")
    assert request["headers"]["X-Forwarded-Host"] == "api.example"
    with pytest.raises(CloudFailure, match="ANALYSIS_RUNTIME_UNQUALIFIED"):
        provider.launch(uuid4(), 1, uuid4(), 1)
