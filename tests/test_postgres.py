from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Event
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.db import close_old_connections, connection

from backend.core.jobs import claim_run
from backend.core.loops import create_assignment, create_plan, evaluate_plan
from backend.core.models import AnalysisRun, ReplayAsset
from backend.core.storage import delete_asset
from tests.test_backend import FakeStorage
from tests.test_complete_loop import approved_drill, make_capture

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def test_concurrent_claim_has_one_winner(django_user_model):
    if connection.vendor != "postgresql":
        pytest.skip("Real PostgreSQL locking test")
    owner = django_user_model.objects.create_user(username="concurrent")
    asset = ReplayAsset.objects.create(owner=owner, storage_key="private/source.mp4")
    run = AnalysisRun.objects.create(owner=owner, asset=asset, request_key=str(uuid4()))

    def attempt():
        close_old_connections()
        try:
            return claim_run(run.pk)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: attempt(), range(2)))
    assert sum(value is not None for value in results) == 1


def test_deletion_cannot_race_past_evaluation_publication(django_user_model):
    if connection.vendor != "postgresql":
        pytest.skip("Real PostgreSQL locking test")
    owner = django_user_model.objects.create_user("concurrent-delete", is_staff=True)
    asset, events, _ = make_capture(owner, datetime(2026, 8, 1, tzinfo=UTC), "ranked", 1)
    assignment = create_assignment(owner, approved_drill().pk)
    plan = create_plan(
        owner,
        assignment.pk,
        [e.pk for e in events],
        "2026-08-05T00:00:00Z",
        "2026-08-07T00:00:00Z",
        "2026-08-31T00:00:00Z",
    )
    entered, release, deleted, deleting = Event(), Event(), Event(), Event()
    from analysis.evaluation import evaluate

    def paused(*args, **kwargs):
        entered.set()
        assert release.wait(10)
        return evaluate(*args, **kwargs)

    def compare():
        close_old_connections()
        try:
            return evaluate_plan(owner, plan.pk, [])
        finally:
            close_old_connections()

    def remove():
        close_old_connections()
        try:
            deleting.set()
            delete_asset(owner, asset.pk, FakeStorage())
            deleted.set()
        finally:
            close_old_connections()

    with (
        patch("backend.core.loops.evaluate", paused),
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        first = executor.submit(compare)
        assert entered.wait(10)
        second = executor.submit(remove)
        assert deleting.wait(10)
        try:
            assert not deleted.wait(0.3)
        finally:
            release.set()
        result = first.result(timeout=10)
        second.result(timeout=10)
    result.refresh_from_db()
    assert result.invalidated_at is not None
