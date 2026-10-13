"""Controlled failure injection; never credentials, live cloud or game approvals."""

import importlib
import io
import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.apps import apps
from django.core.management import call_command
from django.db import transaction
from rest_framework.exceptions import Throttled

from backend.core import preview_writes, previews
from backend.core.cloud import CloudFailure, GooglePrivateStorage
from backend.core.jobs import acknowledge_stopped, cancel_run, claim_run
from backend.core.models import GameplayEvent, Match, PreviewWriteHold, RecordingPreview
from backend.core.preview_ledger import FileLedger, LedgerFailure, held_bytes, prefix
from backend.core.security import check_capacity
from backend.core.storage import delete_asset
from tests import test_private_previews as preview_fixtures

owner = preview_fixtures.owner
asset, bundle = preview_fixtures.asset, preview_fixtures.bundle

pytestmark = pytest.mark.django_db(transaction=True)


class ControlledStorage:
    bucket = "preview-test-bucket"

    def __init__(self):
        self.sessions = {}
        self.objects = {}
        self.initializations = 0
        self.lost_put = False
        self.erase_unavailable = False
        self.stop_unavailable = False

    def begin_preview(self, key, size, md5_hash, identity):
        row = preview_writes.current(identity)
        name = key.rsplit("/", 1)[1]
        assert row["files"][name]["state"] == "INITIALIZING"
        self.initializations += 1
        session = f"https://storage.googleapis.com/upload/storage/v1/b/{self.bucket}/o?uploadType=resumable&upload_id=controlled_{self.initializations}"
        self.sessions[session] = {"key": key, "offset": 0, "stopped": False}
        return session

    def preview_upload(self, session, key, item, offset, block):
        upload = self.sessions[session]
        if upload["stopped"]:
            raise CloudFailure("UPLOAD_STOPPED", retryable=False)
        if block is not None:
            assert upload["offset"] == offset
            upload["offset"] += len(block)
            if upload["offset"] == item["bytes"]:
                self.objects[key] = "42"
            if self.lost_put:
                self.lost_put = False
                raise CloudFailure("LOST_RECEIPT", ambiguous=True)
        return upload["offset"], "42" if key in self.objects else ""

    def stop_preview_session(self, session, key):
        if self.stop_unavailable:
            raise CloudFailure("STOP_UNAVAILABLE")
        assert self.sessions[session]["key"] == key
        self.sessions[session]["stopped"] = True

    def erase_preview(self, scope):
        assert all(x["stopped"] for x in self.sessions.values() if x["key"].startswith(scope))
        if self.erase_unavailable:
            raise CloudFailure("ERASE_UNAVAILABLE")
        self.objects = {key: gen for key, gen in self.objects.items() if not key.startswith(scope)}


@pytest.fixture
def attempt(owner, tmp_path, settings, monkeypatch):
    source = asset(owner)
    source.storage_provider = "GCS"
    source.save()
    settings.GCS_PREVIEW_WRITES_QUALIFIED = True  # Fake transport only.
    preview = previews.enqueue_preview(owner, source.pk, uuid4())
    fence = claim_run(preview.run_id)
    previews.start_preview(preview.run_id, fence)
    preview.refresh_from_db()
    directory = tmp_path / "bundle"
    bundle(directory, source.source_sha256)
    storage = ControlledStorage()
    monkeypatch.setattr(previews, "storage_for", lambda asset: storage)
    monkeypatch.setattr(preview_writes, "storage_for_intent", lambda row: storage)
    return preview, fence, directory, storage


def test_lost_final_put_probes_same_session_then_publishes_and_erases(attempt):
    preview, fence, directory, storage = attempt
    storage.lost_put = True
    manifest = previews.publish_files(preview, fence, directory)
    assert storage.initializations == 3 and len(storage.objects) == 3
    RecordingPreview.objects.filter(pk=preview.pk).update(manifest=manifest)
    assert previews.complete_preview(preview.run_id, fence, directory, "controlled")
    preview.refresh_from_db()
    assert preview_writes.is_published(preview)
    assert not Match.objects.exists() and not GameplayEvent.objects.exists()
    previews.revoke(RecordingPreview.objects.filter(pk=preview.pk))
    acknowledge_stopped(preview.run_id, fence)
    assert previews.purge_preview(preview.pk)
    assert not storage.objects and PreviewWriteHold.objects.get().reserved_bytes == 0
    assert not preview_writes.is_published(preview)


def test_cloud_asset_delete_stops_sessions_and_retains_child_until_worker_stopped(
    attempt, monkeypatch
):
    preview, fence, directory, storage = attempt
    previews.publish_files(preview, fence, directory)
    parent_sweeps = []

    def sweep(key):
        assert not storage.objects and all(x["stopped"] for x in storage.sessions.values())
        parent_sweeps.append(key)

    monkeypatch.setattr(storage, "cancel_upload", lambda session: None, raising=False)
    monkeypatch.setattr(storage, "delete_asset", sweep, raising=False)
    delete_asset(preview.asset.owner, preview.asset_id, storage=storage)
    preview.refresh_from_db()
    preview.asset.refresh_from_db()
    assert preview.state == "PURGING" and preview.reserved_bytes > 0
    assert preview.asset.purge_completed_at is None and parent_sweeps == []
    acknowledge_stopped(preview.run_id, fence)
    delete_asset(preview.asset.owner, preview.asset_id, storage=storage)
    preview.refresh_from_db()
    assert preview.state == "PURGED" and len(parent_sweeps) == 1


@pytest.mark.parametrize("outage", ["stop_unavailable", "erase_unavailable"])
def test_cleanup_outage_keeps_quota_until_stop_and_empty_inventory(attempt, outage):
    preview, fence, directory, storage = attempt
    previews.publish_files(preview, fence, directory)
    identity = preview_writes.intent_id(preview, fence)
    preview_writes.revoke_ids([preview.pk])
    setattr(storage, outage, True)
    with pytest.raises(CloudFailure):
        preview_writes.cleanup(identity)
    assert PreviewWriteHold.objects.get().reserved_bytes > 0
    assert held_bytes(preview_writes.current(identity)) > 0
    setattr(storage, outage, False)
    assert preview_writes.cleanup(identity)
    assert preview_writes.cleanup(identity)  # Restart/repeated cleanup is idempotent.
    assert not storage.objects and PreviewWriteHold.objects.get().reserved_bytes == 0
    with pytest.raises(LedgerFailure):
        preview_writes.file_state(identity, "preview.mp4", "FINALIZED", generation="42")


def test_unknown_initialization_blocks_restore_and_late_handle_can_be_stopped(attempt, settings):
    preview, fence, directory, storage = attempt
    row = preview_writes.plan(preview, fence, directory, storage.bucket)
    preview_writes.file_state(row["id"], "preview.mp4", "INITIALIZING")
    session = storage.begin_preview(
        prefix(row) + "preview.mp4", row["files"]["preview.mp4"]["bytes"], "unused", row["id"]
    )
    acknowledge_stopped(preview.run_id, fence)
    settings.RESTORE_QUARANTINE = True
    with pytest.raises(LedgerFailure, match="WRITE_UNCONFIRMED"):
        previews.purge_restored_previews()
    assert settings.RESTORE_QUARANTINE and PreviewWriteHold.objects.get().reserved_bytes > 0
    preview_writes.file_state(row["id"], "preview.mp4", "SESSION", session=session)
    with pytest.raises(LedgerFailure, match="REVOKED"):
        preview_writes.check_open(row["id"], lambda: None)
    preview_writes.recover_all()
    assert (
        storage.sessions[session]["stopped"] and PreviewWriteHold.objects.get().reserved_bytes == 0
    )


def test_sql_rollback_and_absent_post_backup_asset_still_reserve_capacity(attempt, settings):
    preview, fence, directory, storage = attempt
    with pytest.raises(RuntimeError), transaction.atomic():
        row = preview_writes.plan(preview, fence, directory, storage.bucket)
        raise RuntimeError("database rollback")
    assert not PreviewWriteHold.objects.exists() and FileLedger().records()
    # A post-backup attempt need not have ANY owner/asset/run/preview SQL rows.
    orphan = SimpleNamespace(
        pk=uuid4(),
        run_id=uuid4(),
        asset_id=uuid4(),
        asset=SimpleNamespace(owner_id=999999),
        source_sha256="a" * 64,
    )
    orphan_row = preview_writes.plan(orphan, 1, directory, storage.bucket)
    settings.GLOBAL_STORAGE_BYTES = (
        preview.asset.bytes + preview.reserved_bytes + held_bytes(orphan_row) - 1
    )
    with pytest.raises(Throttled), transaction.atomic():
        check_capacity(preview.asset.owner)
    preview_writes.sync_holds()
    assert preview_writes.extra_capacity(preview.asset.owner_id) == 0
    assert preview_writes.extra_capacity(999999) == held_bytes(orphan_row)
    preview_writes.recover_all()  # No RPC was initialized, so safe erasure needs no transport.
    assert not PreviewWriteHold.objects.exclude(state="ERASED", reserved_bytes=0).exists()
    assert preview_writes.current(row["id"])["state"] == "ERASED"
    with transaction.atomic():
        check_capacity(preview.asset.owner)  # Erased orphan no longer pushes usage over the cap.


def test_durable_cancellation_survives_database_rollback(attempt):
    preview, fence, directory, storage = attempt
    row = preview_writes.plan(preview, fence, directory, storage.bucket)
    with pytest.raises(RuntimeError), transaction.atomic():
        previews.revoke(RecordingPreview.objects.filter(pk=preview.pk))
        raise RuntimeError("rollback revoke")
    preview.refresh_from_db()
    assert preview.state == "QUEUED"
    with pytest.raises(LedgerFailure, match="REVOKED"):
        preview_writes.upload_file(
            row["id"], "preview.mp4", directory / "preview.mp4", storage, lambda: None
        )
    assert storage.initializations == 0


def test_generic_job_cancel_also_records_irreversible_preview_intent(attempt):
    preview, fence, directory, storage = attempt
    row = preview_writes.plan(preview, fence, directory, storage.bucket)
    with pytest.raises(RuntimeError), transaction.atomic():
        cancel_run(preview.asset.owner, preview.run_id)
        raise RuntimeError("cancel rolled back")
    assert preview_writes.current(row["id"])["state"] == "CLEANUP"
    with pytest.raises(LedgerFailure, match="REVOKED"):
        preview_writes.upload_file(
            row["id"], "preview.mp4", directory / "preview.mp4", storage, lambda: None
        )


def test_retries_are_bounded_and_failed_known_session_keeps_reservation(attempt, monkeypatch):
    preview, fence, directory, storage = attempt
    row = preview_writes.plan(preview, fence, directory, storage.bucket)
    requests = []

    def unavailable(*args):
        requests.append(args)
        raise CloudFailure("STORAGE_RETRYABLE")

    monkeypatch.setattr(storage, "preview_upload", unavailable)
    monkeypatch.setattr(preview_writes.time, "sleep", lambda seconds: None)
    with pytest.raises(CloudFailure):
        preview_writes.upload_file(
            row["id"], "preview.mp4", directory / "preview.mp4", storage, lambda: None
        )
    assert storage.initializations == 1 and len(requests) == 4
    assert all(request[-1] is None for request in requests[1:])
    assert PreviewWriteHold.objects.get().reserved_bytes > 0
    preview_writes.revoke_ids([preview.pk])
    assert preview_writes.cleanup(row["id"])


def test_signed_old_checkpoint_cannot_roll_back_a_newer_sql_mirror(attempt, settings):
    preview, fence, directory, storage = attempt
    row = preview_writes.plan(preview, fence, directory, storage.bucket)
    checkpoint = settings.PREVIEW_LEDGER_ROOT / "checkpoint.json"
    old = checkpoint.read_bytes()
    preview_writes.revoke_ids([preview.pk])
    (settings.PREVIEW_LEDGER_ROOT / "00000002.json").unlink()
    checkpoint.write_bytes(old)
    with pytest.raises(LedgerFailure, match="ROLLBACK"):
        preview_writes.sync_holds()
    assert PreviewWriteHold.objects.get().reserved_bytes == held_bytes(row)


def test_unqualified_production_ledger_cannot_initialize_or_write(attempt, settings):
    preview, fence, directory, storage = attempt
    settings.DEBUG = False
    settings.PREVIEW_LEDGER_RUNTIME_QUALIFIED = False
    with pytest.raises(LedgerFailure, match="UNQUALIFIED"):
        FileLedger().initialize()
    with pytest.raises(LedgerFailure, match="UNQUALIFIED"):
        preview_writes.plan(preview, fence, directory, storage.bucket)
    assert not PreviewWriteHold.objects.exists()


def test_reverse_migration_protects_both_sql_and_independent_holds(attempt):
    preview, fence, directory, storage = attempt
    preview_writes.plan(preview, fence, directory, storage.bucket)
    guard = importlib.import_module(
        "backend.core.migrations.0025_preview_write_hold"
    ).refuse_pending_writes
    with pytest.raises(RuntimeError, match="RESERVATIONS_PENDING"):
        guard(apps, None)
    PreviewWriteHold.objects.all().delete()  # Mirror loss is not authority to drop the independent hold.
    with pytest.raises(RuntimeError, match="RESERVATIONS_PENDING"):
        guard(apps, None)
    preview_writes.recover_all()
    guard(apps, None)


def test_reverse_migration_refuses_missing_ledger_even_with_erased_sql_holds(
    attempt, settings, tmp_path
):
    preview, fence, directory, storage = attempt
    preview_writes.plan(preview, fence, directory, storage.bucket)
    preview_writes.recover_all()
    assert not PreviewWriteHold.objects.exclude(state="ERASED", reserved_bytes=0).exists()
    guard = importlib.import_module(
        "backend.core.migrations.0025_preview_write_hold"
    ).refuse_pending_writes
    settings.PREVIEW_LEDGER_ROOT = tmp_path / "missing-independent-store"
    with pytest.raises(LedgerFailure, match="UNAVAILABLE"):
        guard(apps, None)


@pytest.mark.parametrize("corruption", ["missing", "mutated", "tail", "namespace", "symlink"])
def test_missing_tampered_or_incomplete_ledger_fails_before_refund(attempt, settings, corruption):
    preview, fence, directory, storage = attempt
    row = preview_writes.plan(preview, fence, directory, storage.bucket)
    checkpoint = settings.PREVIEW_LEDGER_ROOT / "checkpoint.json"
    if corruption == "missing":
        checkpoint.unlink()
    elif corruption == "mutated":
        checkpoint.write_bytes(checkpoint.read_bytes().replace(b'"count":1', b'"count":0'))
    elif corruption == "tail":
        (settings.PREVIEW_LEDGER_ROOT / "00000002.json").write_text("{}")
    elif corruption == "namespace":
        settings.DEPLOYMENT_NAMESPACE = "foreign-deployment"
    else:
        checkpoint.unlink()
        try:
            checkpoint.symlink_to(directory / "report.json")
        except OSError:
            pytest.skip("OS does not permit test symlinks")
    with pytest.raises(LedgerFailure):
        preview_writes.recover_all()
    assert PreviewWriteHold.objects.get().reserved_bytes == held_bytes(row)


def test_independent_writers_are_serialized_and_status_redacts_capabilities(attempt):
    preview, fence, directory, storage = attempt
    row = preview_writes.plan(preview, fence, directory, storage.bucket)

    def revoke_one(_):
        def mutate(old):
            old["state"] = "CLEANUP"
            return old

        return FileLedger().update(row["id"], mutate)

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert all(x["state"] == "CLEANUP" for x in pool.map(revoke_one, range(8)))
    output = io.StringIO()
    call_command("preview_write_maintenance", stdout=output)
    status = json.loads(output.getvalue())
    assert status["reserved_bytes"] == held_bytes(row)
    assert "session" not in output.getvalue().replace("unknown_sessions", "")
    assert (
        str(preview.pk) not in output.getvalue()
        and "storage.googleapis.com" not in output.getvalue()
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://foreign.example/upload",
        "http://storage.googleapis.com/upload",
        "https://storage.googleapis.com/upload/storage/v1/b/preview-test-bucket/o?uploadType=resumable&upload_id=a&upload_id=b",
        "https://storage.googleapis.com/upload/storage/v1/b/preview-test-bucket/o?uploadType=resumable&upload_id=a&name=foreign",
    ],
)
def test_official_adapter_rejects_foreign_or_ambiguous_capabilities(url):
    storage = GooglePrivateStorage(None, "preview-test-bucket", 1, uuid4())
    with pytest.raises(CloudFailure):
        storage.preview_session_url(url, storage.prefix + "previews/test/preview.mp4")


def test_official_adapter_cancels_before_all_version_delete_and_confirms_empty():
    calls = []

    class Response:
        headers = {}

        def __init__(self, status, body):
            self.status_code, self.body = status, body

        def json(self):
            return self.body

        def close(self):
            pass

    class Session:
        def request(self, method, url, **kwargs):
            calls.append((method, url, kwargs))
            if "upload_id" in url:
                return Response(499, {})
            if method == "DELETE":
                return Response(204, {})
            if len(calls) == 2:
                return Response(
                    200,
                    {"items": [{"name": key, "generation": "1"}, {"name": key, "generation": "2"}]},
                )
            return Response(200, {})

    storage = GooglePrivateStorage(Session(), "preview-test-bucket", 1, uuid4())
    scope = storage.prefix + "previews/test/"
    key = scope + "preview.mp4"
    session = "https://storage.googleapis.com/upload/storage/v1/b/preview-test-bucket/o?uploadType=resumable&upload_id=test"
    storage.stop_preview_session(session, key)
    storage.erase_preview(scope)
    assert [x[0] for x in calls] == ["DELETE", "GET", "DELETE", "DELETE", "GET"]
    assert calls[-1][2]["params"] == {"prefix": scope, "versions": "true", "maxResults": 1}


@pytest.mark.parametrize("invalid", [False, True])
def test_official_resumable_metadata_is_checked_and_requests_are_create_only(invalid):
    calls = []

    class Response:
        status_code = 200
        headers = {}

        def close(self):
            pass

        def iter_content(self, chunk_size):
            yield json.dumps(
                {
                    "bucket": "preview-test-bucket",
                    "name": "foreign" if invalid else key,
                    "size": "3",
                    "md5Hash": "checksum",
                    "generation": "9",
                }
            ).encode()

    class Session:
        def request(self, method, url, **kwargs):
            calls.append((method, kwargs))
            response = Response()
            response.headers = {"Location": session}
            return response

    storage = GooglePrivateStorage(Session(), "preview-test-bucket", 1, uuid4())
    key = storage.prefix + "previews/test/preview.mp4"
    session = "https://storage.googleapis.com/upload/storage/v1/b/preview-test-bucket/o?uploadType=resumable&upload_id=test"
    assert storage.begin_preview(key, 3, "checksum", uuid4()) == session
    assert calls[0][1]["params"]["ifGenerationMatch"] == "0"
    if invalid:
        with pytest.raises(CloudFailure, match="INVALID_PREVIEW_OBJECT"):
            storage.preview_upload(session, key, {"bytes": 3, "md5": "checksum"}, 0, b"abc")
    else:
        assert storage.preview_upload(session, key, {"bytes": 3, "md5": "checksum"}, 0, b"abc") == (
            3,
            "9",
        )
    assert calls[-1][1]["headers"]["Content-Range"] == "bytes 0-2/3"
