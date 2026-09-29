import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.db import close_old_connections, connection, transaction
from django.test import Client
from django.utils import timezone
from rest_framework.exceptions import Throttled
from rest_framework.test import APIClient

from analysis.process import execution_check, run_bounded
from backend.core.evidence import publish_annotations
from backend.core.jobs import cancel_run, claim_run, finish_run
from backend.core.models import AnalysisRun, ReplayAsset, RequestBudget, UploadAdmission
from backend.core.ownership import lock_owner
from backend.core.parser import analyze_isolated, validate_report
from backend.core.security import (
    MAX_UPLOAD,
    admission_id,
    admit_run,
    audit,
    check_capacity,
    consume_budget,
    reserve_upload,
    validate_admission,
)
from backend.core.storage import delete_account


@pytest.mark.django_db
def test_login_budget_ignores_forwarded_ip_and_hides_credentials(settings):
    settings.LOGIN_RATE = 2
    client = Client()
    for _ in range(2):
        assert client.post("/api/session", {}, content_type="application/json").status_code == 401
    response = client.post(
        "/api/session",
        {"username": "secret-name"},
        content_type="application/json",
        HTTP_X_FORWARDED_FOR="8.8.8.8",
    )
    assert response.status_code == 429 and int(response["Retry-After"]) > 0
    assert response["Cache-Control"] == "private, no-store"
    assert "secret" not in json.dumps(list(RequestBudget.objects.values()), default=str)


@pytest.mark.django_db
def test_account_throttle_and_private_errors(django_user_model, settings):
    owner = django_user_model.objects.create_user("rate")
    settings.API_READ_RATE = 1
    client = APIClient()
    client.force_authenticate(owner)
    assert client.get("/api/overview").status_code == 200
    result = client.get("/api/overview")
    assert result.status_code == 429 and result["Cache-Control"] == "private, no-store"
    assert result["X-Content-Type-Options"] == "nosniff"


@pytest.mark.django_db
def test_json_body_limit_before_feedback_creation(django_user_model, settings):
    owner = django_user_model.objects.create_user("body-limit")
    settings.DATA_UPLOAD_MAX_MEMORY_SIZE = 256
    client = APIClient()
    client.force_authenticate(owner)
    result = client.post(
        "/api/feedback",
        {"request_id": str(uuid4()), "category": "QUESTION", "message": "x" * 1000},
        format="json",
    )
    assert result.status_code == 400
    assert "configured limit" in str(result.data)


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_global_upload_reservation_race(django_user_model, settings):
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL locking")
    settings.LOCAL_OPERATOR_UPLOADS = True
    settings.GLOBAL_UPLOAD_SLOTS = 1
    owners = [
        django_user_model.objects.create_user(f"upload-race-{i}", is_staff=True) for i in range(2)
    ]

    def attempt(owner):
        close_old_connections()
        try:
            reserve_upload(owner)
            return True
        except Throttled:
            return False
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(attempt, owners)).count(True) == 1


def test_missing_docker_image_fails_closed(settings, tmp_path):
    settings.PARSER_BACKEND = "docker"
    settings.PARSER_IMAGE = ""
    with pytest.raises(ValueError, match="PARSER_IMAGE_NOT_PINNED"):
        analyze_isolated(tmp_path, tmp_path, tmp_path)


@pytest.mark.django_db
def test_upload_reservations_storage_pending_purge_and_expiry(django_user_model, settings):
    settings.LOCAL_OPERATOR_UPLOADS = True
    settings.OWNER_STORAGE_BYTES = MAX_UPLOAD
    owner = django_user_model.objects.create_user("admit", is_staff=True)
    first = reserve_upload(owner)
    with pytest.raises(Throttled):
        reserve_upload(owner)
    token = admission_id.set(first.pk)
    try:
        UploadAdmission.objects.filter(pk=first.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        with pytest.raises(Throttled):
            validate_admission(owner)
    finally:
        admission_id.reset(token)
    call_command("security_maintenance")
    assert not UploadAdmission.objects.exists()
    asset = ReplayAsset.objects.create(
        owner=owner, storage_key="fixture/source.mp4", bytes=MAX_UPLOAD, deleted_at=timezone.now()
    )
    with transaction.atomic(), pytest.raises(Throttled):
        lock_owner(owner.pk)
        check_capacity(owner, 1)
    asset.purge_completed_at = timezone.now()
    asset.save()
    with transaction.atomic():
        lock_owner(owner.pk)
        check_capacity(owner, MAX_UPLOAD)


@pytest.mark.django_db
def test_admission_rejects_before_upload_parser_and_releases_after_failure(
    django_user_model, settings
):
    settings.LOCAL_OPERATOR_UPLOADS = True
    owner = django_user_model.objects.create_user("early", is_staff=True)
    client = APIClient()
    client.force_authenticate(owner)
    settings.OWNER_STORAGE_BYTES = 0
    with patch(
        "rest_framework.parsers.MultiPartParser.parse", side_effect=AssertionError("body parsed")
    ):
        assert client.post("/api/uploads", {}, format="multipart").status_code == 429
    settings.OWNER_STORAGE_BYTES = MAX_UPLOAD
    assert client.post("/api/uploads", {}, format="multipart").status_code == 400
    assert not UploadAdmission.objects.exists()


@pytest.mark.django_db
def test_queue_quota_and_atomic_hash_publication(django_user_model, settings):
    owner = django_user_model.objects.create_user("queue")
    asset = ReplayAsset.objects.create(owner=owner, storage_key="fixture/source.mp4")
    run = AnalysisRun.objects.create(owner=owner, asset=asset, request_key="a")
    settings.OWNER_PENDING_RUNS = 1
    with transaction.atomic(), pytest.raises(Throttled):
        lock_owner(owner.pk)
        admit_run(owner)
    fence = claim_run(run.pk)
    cancel_run(owner, run.pk)
    assert not finish_run(
        run.pk, fence, {"status": "REVIEW_REQUIRED", "source": {"source_sha256": "a" * 64}}
    )
    asset.refresh_from_db()
    assert not asset.source_sha256


@pytest.mark.django_db
def test_nested_worker_and_operator_ownership(django_user_model):
    owner = django_user_model.objects.create_user("one", is_staff=True)
    other = django_user_model.objects.create_user("two", is_staff=True)
    asset = ReplayAsset.objects.create(owner=other, storage_key="other/source.mp4")
    run = AnalysisRun.objects.create(owner=owner, asset=asset, request_key="corrupt-nesting")
    assert claim_run(run.pk) is None
    with pytest.raises(PermissionDenied):
        publish_annotations(other, run.pk, "irrelevant", {})


@pytest.mark.django_db
def test_account_deletion_revokes_inflight_upload(django_user_model, settings):
    settings.LOCAL_OPERATOR_UPLOADS = True
    owner = django_user_model.objects.create_user("delete-admit", is_staff=True)
    admission = reserve_upload(owner)
    delete_account(owner)
    assert not UploadAdmission.objects.filter(pk=admission.pk).exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_global_claim_capacity_is_atomic_across_owners(django_user_model, settings):
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL locking")
    settings.GLOBAL_ACTIVE_RUNS = 1
    runs = []
    for i in range(2):
        owner = django_user_model.objects.create_user(f"capacity-{i}")
        asset = ReplayAsset.objects.create(owner=owner, storage_key=f"{i}/source.mp4")
        runs.append(AnalysisRun.objects.create(owner=owner, asset=asset, request_key="a"))

    def attempt(run):
        close_old_connections()
        try:
            return claim_run(run.pk)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, runs))
    assert sum(value is not None for value in results) == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_parallel_rate_consumption_cannot_overrun_budget():
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL locking")

    def attempt(_):
        close_old_connections()
        try:
            return consume_budget("test", "same-subject", 1, seconds=3600)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(attempt, range(4)))
    assert results.count(0) == 1


def test_process_revoke_stops_a_running_decoder():
    checks = 0

    def revoked():
        nonlocal checks
        checks += 1
        if checks >= 3:
            raise ValueError("RUN_REVOKED")

    token = execution_check.set(revoked)
    try:
        with pytest.raises(ValueError, match="RUN_REVOKED"):
            run_bounded([sys.executable, "-c", "import time; time.sleep(30)"], timeout=2)
    finally:
        execution_check.reset(token)


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {"status": "COMPLETED"},
        {"status": "REVIEW_REQUIRED", "opportunities": [1], "automatic_gameplay_validated": False},
    ],
)
def test_untrusted_parser_cannot_publish_gameplay(payload):
    with pytest.raises(ValueError, match="INVALID_PARSER_REPORT"):
        validate_report(payload)


def test_parser_failure_redacts_paths_and_fixed_audit_has_no_payload(caplog):
    report = validate_report(
        {
            "status": "FAILED",
            "opportunities": [],
            "automatic_gameplay_validated": False,
            "issues": ["/private/user/video.mp4", "DECODER_TIMEOUT"],
        }
    )
    assert report["issues"] == ["MEDIA_VALIDATION_FAILED", "DECODER_TIMEOUT"]
    with caplog.at_level("INFO", logger="dojopulse.security"):
        audit("parser_cleanup", "RUNTIME_UNAVAILABLE")
    assert json.loads(caplog.records[-1].message) == {
        "event": "parser_cleanup",
        "reason": "RUNTIME_UNAVAILABLE",
    }


def test_local_parser_cannot_be_enabled_outside_debug(settings, tmp_path):
    settings.PARSER_BACKEND = "local"
    settings.DEBUG = False
    settings.LOCAL_OPERATOR_UPLOADS = True
    with pytest.raises(ValueError, match="LOCAL_PARSER_DISABLED"):
        analyze_isolated(tmp_path, tmp_path, tmp_path)
