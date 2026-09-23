from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

import pytest
from django.db import close_old_connections, connection

from backend.core import match_ingestion
from backend.core.match_ingestion import claim_local_sync, commit_local_page, start_local_sync
from backend.core.models import MatchSourceRecord, MatchSync
from backend.core.storage import delete_metadata_match
from ingestion.synthetic import END, START
from tests.test_match_import import corrected, import_one, setup_sync

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def connected(function, *args):
    close_old_connections()
    try:
        return function(*args)
    finally:
        close_old_connections()


def test_concurrent_match_claim_has_one_winner(django_user_model):
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL locking required")
    owner = django_user_model.objects.create_user("match-claim")
    _, _, job, _ = setup_sync(owner)
    MatchSync.objects.filter(pk=job.pk).update(status="PENDING", lease_until=None)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(connected, claim_local_sync, owner, job.pk) for _ in range(2)]
        assert sum(future.result(timeout=10) is not None for future in futures) == 1


def test_deletion_serializes_with_page_commit(django_user_model):
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL locking required")
    owner = django_user_model.objects.create_user("match-delete")
    _, identity, job, page, match = import_one(owner)
    start_local_sync(owner, identity.pk, job.provider, START, END)
    token = claim_local_sync(owner, job.pk)
    entered, release, deleting, deleted = Event(), Event(), Event(), Event()
    original = match_ingestion._import_metadata

    def paused(*args):
        entered.set()
        assert release.wait(10)
        return original(*args)

    def remove():
        deleting.set()
        delete_metadata_match(owner, match.pk)
        deleted.set()

    with (
        patch.object(match_ingestion, "_import_metadata", paused),
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        imported = executor.submit(
            connected,
            commit_local_page,
            owner,
            job.pk,
            token,
            None,
            corrected(page, winner_slot=2, raw_winner="2"),
        )
        assert entered.wait(10)
        removed = executor.submit(connected, remove)
        assert deleting.wait(10)
        try:
            assert not deleted.wait(0.3)
        finally:
            release.set()
        assert imported.result(timeout=10)
        removed.result(timeout=10)
    assert not MatchSourceRecord.objects.exists()
    job.refresh_from_db()
    assert job.status == "CANCELLED"
