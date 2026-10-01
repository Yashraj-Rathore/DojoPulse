import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from importlib import import_module
from threading import Barrier
from uuid import uuid4

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.management import call_command
from django.db import close_old_connections, connection, transaction
from django.test import Client
from django.utils import timezone

from backend.core import accounts
from backend.core.consents import POLICY_VERSION, record_consent, require_processing
from backend.core.jobs import claim_run, finish_run
from backend.core.match_ingestion import (
    claim_local_sync,
    commit_local_page,
    link_local_identity,
    start_local_sync,
)
from backend.core.models import (
    AccountChallenge,
    AccountEmail,
    AccountSession,
    AnalysisRun,
    ConsentReceipt,
    Match,
    MatchSuppression,
    Profile,
    ReplayAsset,
    UploadAdmission,
)
from backend.core.security import reserve_upload
from backend.core.storage import delete_account, delete_metadata_match
from ingestion.contracts import Operation
from ingestion.synthetic import END, PLAYER, START
from tests.test_match_import import import_one

pytestmark = pytest.mark.django_db
PASSWORD = "Orchard!railway-4826"
REPLACEMENT = "Mountain!harbor-7214"


@pytest.fixture(autouse=True)
def local_delivery(settings, tmp_path):
    settings.DEBUG = True
    settings.LOCAL_ACCOUNT_SIGNUP = True
    settings.PRIVATE_DATA_ROOT = tmp_path
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def owner(django_user_model):
    return django_user_model.objects.create_user("account-owner", password=PASSWORD, is_staff=True)


def latest_token(owner, purpose="VERIFY"):
    challenge = AccountChallenge.objects.filter(owner=owner, purpose=purpose).latest("created_at")
    envelope = json.loads(accounts.mail_path(challenge).read_text())
    return challenge, envelope["url"].rsplit(":", 1)[1]


def signup():
    accounts.register("New.Player", "Player@Example.com", PASSWORD, POLICY_VERSION)
    return get_user_model().objects.get(username="new.player")


def verified():
    owner = signup()
    _, token = latest_token(owner)
    accounts.consume_challenge(token, "VERIFY")
    owner.refresh_from_db()
    return owner


def post(client, path, data):
    csrf = client.get("/api/session").json()["csrf"]
    return client.post(
        path, json.dumps(data), content_type="application/json", HTTP_X_CSRFTOKEN=csrf
    )


def signed_in(owner):
    client = Client(enforce_csrf_checks=True)
    assert (
        post(client, "/api/session", {"username": owner.username, "password": PASSWORD}).status_code
        == 200
    )
    return client


def test_registration_verification_is_private_one_use_and_never_grants_operator_rights():
    owner = signup()
    assert not owner.is_active and not owner.is_staff
    assert not Client().login(username=owner.username, password=PASSWORD)
    challenge, token = latest_token(owner)
    assert challenge.token_digest != token and len(challenge.token_digest) == 64
    assert challenge.email == "player@example.com"
    assert ConsentReceipt.objects.get(owner=owner).scope == "TERMS"
    assert not owner.profile.training_consent_at
    accounts.consume_challenge(token, "VERIFY")
    assert Client().login(username=owner.username, password=PASSWORD)
    with pytest.raises(ValidationError, match="already used"):
        accounts.consume_challenge(token, "VERIFY")
    assert AccountEmail.objects.get(owner=owner).verified_at
    assert accounts.cleanup_account_mail() == 1


@pytest.mark.parametrize("failure", ["expired", "purpose", "malformed", "password_changed"])
def test_verification_rejects_invalid_links(failure):
    owner = signup()
    challenge, token = latest_token(owner)
    purpose = "VERIFY"
    if failure == "expired":
        challenge.expires_at = timezone.now() - timedelta(seconds=1)
        challenge.save()
    elif failure == "purpose":
        purpose = "RESET"
    elif failure == "malformed":
        token = "../../anything"
    else:
        owner.set_password(REPLACEMENT)
        owner.save()
    with pytest.raises(ValidationError):
        accounts.consume_challenge(token, purpose, REPLACEMENT)
    owner.refresh_from_db()
    assert not owner.is_active


def test_anonymous_mutations_require_csrf_and_do_not_enumerate():
    client = Client(enforce_csrf_checks=True)
    values = {
        "username": "new.player",
        "email": "player@example.com",
        "password": PASSWORD,
        "policy_version": POLICY_VERSION,
        "accepted_terms": True,
    }
    for path in ["register", "link", "confirm"]:
        assert (
            client.post(f"/api/account/{path}", "{}", content_type="application/json").status_code
            == 403
        )
    first = post(client, "/api/account/register", values)
    duplicate = post(client, "/api/account/register", values)
    assert first.status_code == duplicate.status_code == 202
    assert first.json() == duplicate.json()
    assert "token" not in first.content.decode()
    unknown = post(
        client, "/api/account/link", {"email": "unknown@example.com", "purpose": "RESET"}
    )
    known = post(client, "/api/account/link", {"email": values["email"], "purpose": "RESET"})
    assert unknown.json() == known.json()


def test_registration_gate_weak_password_and_stale_policy(settings):
    with pytest.raises(ValidationError):
        accounts.register("valid", "player@example.com", "1234", POLICY_VERSION)
    with pytest.raises(ValidationError):
        accounts.register("valid", "player@example.com", PASSWORD, "old")
    settings.DEBUG = False
    assert not accounts.local_accounts_enabled()
    with pytest.raises(ValidationError):
        signup()
    assert not AccountChallenge.objects.exists()


def test_reset_revokes_all_sessions_and_old_links():
    owner = verified()
    first, second = signed_in(owner), signed_in(owner)
    accounts.request_link(owner.email, "RESET")
    _, token = latest_token(owner, "RESET")
    accounts.consume_challenge(token, "RESET", REPLACEMENT)
    assert not first.get("/api/session").json()["authenticated"]
    assert not second.get("/api/session").json()["authenticated"]
    assert not Client().login(username=owner.username, password=PASSWORD)
    assert Client().login(username=owner.username, password=REPLACEMENT)
    with pytest.raises(ValidationError):
        accounts.consume_challenge(token, "RESET", PASSWORD)


def test_session_revoke_is_owned_and_logout_all_invalidates_other_session(owner, django_user_model):
    first, second = signed_in(owner), signed_in(owner)
    details = first.get("/api/account/details").json()
    assert len(details["sessions"]) == 2
    other_session = next(item for item in details["sessions"] if not item["current"])
    stranger = django_user_model.objects.create_user("stranger", password=PASSWORD)
    third = signed_in(stranger)
    csrf = third.get("/api/session").json()["csrf"]
    assert (
        third.delete(
            f"/api/account/sessions/{other_session['id']}", HTTP_X_CSRFTOKEN=csrf
        ).status_code
        == 404
    )
    csrf = first.get("/api/session").json()["csrf"]
    assert (
        first.delete(
            f"/api/account/sessions/{other_session['id']}", HTTP_X_CSRFTOKEN=csrf
        ).status_code
        == 200
    )
    assert not second.get("/api/session").json()["authenticated"]
    second = signed_in(owner)
    assert post(first, "/api/account/logout-all", {}).status_code == 200
    assert not second.get("/api/session").json()["authenticated"]
    assert third.get("/api/session").json()["authenticated"]


def test_password_change_needs_current_password_and_expires_links(owner):
    client = signed_in(owner)
    assert (
        post(
            client,
            "/api/account/password",
            {"current_password": "wrong", "new_password": REPLACEMENT},
        ).status_code
        == 400
    )
    accounts.change_email(owner, PASSWORD, "new@example.com")
    _, token = latest_token(owner)
    assert (
        post(
            client,
            "/api/account/password",
            {"current_password": PASSWORD, "new_password": REPLACEMENT},
        ).status_code
        == 200
    )
    assert not client.get("/api/session").json()["authenticated"]
    with pytest.raises(ValidationError):
        accounts.consume_challenge(token, "VERIFY")


def test_normal_logout_removes_session_from_active_inventory(owner):
    client = signed_in(owner)
    csrf = client.get("/api/session").json()["csrf"]
    assert AccountSession.objects.filter(owner=owner, revoked_at=None).count() == 1
    assert client.delete("/api/session", HTTP_X_CSRFTOKEN=csrf).status_code == 200
    assert not AccountSession.objects.filter(owner=owner, revoked_at=None).exists()


def test_account_deletion_rechecks_password_after_locking_stale_owner(owner):
    current = get_user_model().objects.get(pk=owner.pk)
    current.set_password(REPLACEMENT)
    current.save(update_fields=["password"])
    with pytest.raises(ValidationError, match="Current password"):
        delete_account(owner, password=PASSWORD)
    current.refresh_from_db()
    assert current.is_active and current.check_password(REPLACEMENT)


def test_email_change_waits_for_verification_and_invalidates_old_address_reset():
    owner = verified()
    accounts.request_link(owner.email, "RESET")
    _, reset_token = latest_token(owner, "RESET")
    accounts.change_email(owner, PASSWORD, "new@example.com")
    assert AccountEmail.objects.get(owner=owner).normalized == "player@example.com"
    _, token = latest_token(owner)
    accounts.consume_challenge(token, "VERIFY")
    assert AccountEmail.objects.get(owner=owner).normalized == "new@example.com"
    with pytest.raises(ValidationError):
        accounts.consume_challenge(reset_token, "RESET", REPLACEMENT)


def test_email_verification_cannot_reactivate_disabled_existing_account(owner):
    accounts.change_email(owner, PASSWORD, "new@example.com")
    _, token = latest_token(owner)
    owner.is_active = False
    owner.save()
    with pytest.raises(ValidationError):
        accounts.consume_challenge(token, "VERIFY")
    owner.refresh_from_db()
    assert not owner.is_active


def test_mail_requests_have_per_account_budget():
    owner = signup()
    for _ in range(6):
        accounts.request_link(owner.email, "VERIFY")
    assert AccountChallenge.objects.filter(owner=owner).count() == 3


def test_public_rate_limit_returns_retry_after():
    client = Client()
    for _ in range(10):
        assert (
            post(
                client, "/api/account/link", {"email": "unknown@example.com", "purpose": "RESET"}
            ).status_code
            == 202
        )
    response = post(
        client, "/api/account/link", {"email": "unknown@example.com", "purpose": "RESET"}
    )
    assert response.status_code == 429 and int(response["Retry-After"]) > 0


def test_withdrawal_fences_imports_and_requires_separate_regrant_and_relink(owner, settings):
    settings.LOCAL_OPERATOR_UPLOADS = True
    admission = reserve_upload(owner)
    adapter, identity, job, page, match = import_one(owner)
    start_local_sync(owner, identity.pk, job.provider, START, END)
    fence = claim_local_sync(owner, job.pk)
    asset = ReplayAsset.objects.create(
        owner=owner, storage_key="fixture.mp4", source_sha256="a" * 64
    )
    run = AnalysisRun.objects.create(
        owner=owner, asset=asset, request_key="consent", status="PROCESSING", fence=2
    )
    request_id = uuid4()
    receipt = record_consent(owner, "PROCESSING", "WITHDRAW", POLICY_VERSION, request_id)
    assert (
        record_consent(owner, "PROCESSING", "WITHDRAW", POLICY_VERSION, request_id).pk == receipt.pk
    )
    with pytest.raises(ValidationError):
        record_consent(owner, "PROCESSING", "GRANT", POLICY_VERSION, request_id)
    run.refresh_from_db()
    assert run.status == "CANCELLED" and run.fence == 3
    assert not UploadAdmission.objects.filter(pk=admission.pk).exists()
    assert claim_run(run.pk) is None
    assert not finish_run(run.pk, 2, {"status": "COMPLETED"})
    with pytest.raises(ValidationError, match="withdrawn"):
        reserve_upload(owner)
    with pytest.raises(ValidationError):
        commit_local_page(owner, job.pk, fence, None, page)
    with pytest.raises(ValidationError, match="withdrawn"):
        require_processing(owner)
    assert Match.objects.filter(pk=match.pk, deleted_at=None).exists()
    record_consent(owner, "PROCESSING", "GRANT", POLICY_VERSION, uuid4())
    require_processing(owner)
    with pytest.raises(ObjectDoesNotExist):
        start_local_sync(owner, identity.pk, job.provider, START, END)
    link_local_identity(
        owner,
        "tekken8",
        adapter.resolve_player(PLAYER.value, Operation.RESOLVE_ID),
        PLAYER,
        processing_consent=True,
        relink_confirmed=True,
    )
    job.refresh_from_db()
    assert job.status == "CANCELLED"


def test_deleted_match_is_suppressed_after_explicit_relink(owner):
    adapter, identity, job, page, match = import_one(owner)
    delete_metadata_match(owner, match.pk)
    suppression = MatchSuppression.objects.get(owner=owner)
    assert len(suppression.key_digest) == 64
    with pytest.raises(ValidationError, match="revoked"):
        link_local_identity(
            owner,
            "tekken8",
            adapter.resolve_player(PLAYER.value, Operation.RESOLVE_ID),
            PLAYER,
            processing_consent=True,
        )
    link_local_identity(
        owner,
        "tekken8",
        adapter.resolve_player(PLAYER.value, Operation.RESOLVE_ID),
        PLAYER,
        processing_consent=True,
        relink_confirmed=True,
    )
    start_local_sync(owner, identity.pk, job.provider, START, END)
    fence = claim_local_sync(owner, job.pk)
    assert commit_local_page(owner, job.pk, fence, None, page)
    assert not Match.objects.filter(owner=owner, deleted_at=None).exists()
    assert not match.source_records.exists()


def test_consent_export_contains_receipts_not_session_or_recovery_secrets(owner):
    accounts.change_email(owner, PASSWORD, "new@example.com")
    _, token = latest_token(owner)
    client = signed_in(owner)
    for scope in ["PROCESSING", "TRAINING"]:
        assert (
            post(
                client,
                "/api/account/consent",
                {
                    "scope": scope,
                    "action": "GRANT",
                    "policy_version": POLICY_VERSION,
                    "request_id": str(uuid4()),
                    "confirmed": True,
                },
            ).status_code
            == 200
        )
    response = client.get("/api/account/export")
    assert response.status_code == 200
    assert len(response.json()["consent_receipts"]) == 2
    assert token not in response.content.decode()
    assert "key_digest" not in response.content.decode()
    record_consent(owner, "TRAINING", "WITHDRAW", POLICY_VERSION, uuid4())
    assert not Profile.objects.get(user=owner).training_consent_at
    assert Profile.objects.get(user=owner).processing_consent_at


def test_account_delete_removes_credentials_receipts_and_retries_private_mail(owner, monkeypatch):
    accounts.change_email(owner, PASSWORD, "new@example.com")
    challenge, token = latest_token(owner)
    path = accounts.mail_path(challenge)
    real_cleanup = accounts.cleanup_account_mail
    monkeypatch.setattr(
        accounts, "cleanup_account_mail", lambda *args: (_ for _ in ()).throw(OSError("disk"))
    )
    with pytest.raises(OSError):
        delete_account(owner)
    owner.refresh_from_db()
    assert not owner.is_active and not owner.has_usable_password()
    assert not AccountChallenge.objects.filter(owner=owner).exists()
    assert not AccountEmail.objects.filter(owner=owner).exists()
    assert path.exists()
    monkeypatch.setattr(accounts, "cleanup_account_mail", real_cleanup)
    call_command("purge_expired")
    assert not path.exists()
    with pytest.raises(ValidationError):
        accounts.consume_challenge(token, "VERIFY")


@pytest.mark.django_db(transaction=True)
def test_concurrent_verification_has_only_one_winner():
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL locking test")
    owner = signup()
    _, token = latest_token(owner)
    barrier = Barrier(2)

    def confirm():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            accounts.consume_challenge(token, "VERIFY")
            return "confirmed"
        except ValidationError:
            return "rejected"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: confirm(), range(2)))
    assert sorted(results) == ["confirmed", "rejected"]


def test_legacy_consent_backfill_preserves_unknown_policy_and_original_time(owner):
    date = timezone.now() - timedelta(days=4)
    Profile.objects.create(user=owner, processing_consent_at=date)
    migration = import_module(
        "backend.core.migrations.0008_profile_processing_withdrawn_at_and_more"
    )
    with connection.schema_editor() as editor:
        migration.capture_legacy_receipts(apps, editor)
    receipt = ConsentReceipt.objects.get(owner=owner)
    assert receipt.policy_version == "legacy-unversioned"
    assert receipt.policy_digest == "" and receipt.source == "LEGACY_CAPTURED"
    assert receipt.created_at == date
    assert not AccountEmail.objects.filter(owner=owner).exists()


@pytest.mark.django_db(transaction=True)
def test_mail_cleanup_does_not_race_uncommitted_registration():
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL visibility test")

    def cleanup():
        close_old_connections()
        try:
            return accounts.cleanup_account_mail()
        finally:
            close_old_connections()

    with transaction.atomic():
        owner = signup()
        challenge, _ = latest_token(owner)
        with ThreadPoolExecutor(max_workers=1) as pool:
            assert pool.submit(cleanup).result(timeout=10) == 0
        assert accounts.mail_path(challenge).exists()
