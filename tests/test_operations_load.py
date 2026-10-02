"""Reproducible synthetic load shapes, not real-user or hosted throughput qualification."""

import json
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.exceptions import Throttled
from rest_framework.test import APIClient

from backend.core.cloud import CloudFailure
from backend.core.dispatch import dispatch_pending
from backend.core.jobs import (
    acknowledge_stopped,
    cancel_run,
    claim_run,
    enqueue_run,
    reconcile_runs,
)
from backend.core.models import (
    AnalysisRun,
    ExecutionSlot,
    Match,
    Participant,
    ReplayAsset,
    RunDispatch,
)
from backend.core.operations import snapshot
from backend.core.ownership import lock_owner
from backend.core.security import admit_run

pytestmark = pytest.mark.django_db


def test_synthetic_history_queue_saturation_and_outage(django_user_model, settings):
    settings.OWNER_PROCESSING_SECONDS_PER_DAY = 7200
    owners = [django_user_model.objects.create_user(f"load-owner-{i}") for i in range(9)]
    now = timezone.now()
    matches = [
        Match(
            owner=owner,
            played_at=now - timedelta(minutes=j),
            mode="ranked",
            context="jin/jin",
            dataset_kind="synthetic",
            metadata_revision=1,
        )
        for owner in owners
        for j in range(250)
    ]
    Match.objects.bulk_create(matches)
    Participant.objects.bulk_create(
        [Participant(match=match, slot=1, character="jin", is_player=True) for match in matches]
    )
    client = APIClient()
    client.force_authenticate(owners[0])
    latencies, queries = [], []
    for offset in (0, 100, 200):
        start = time.monotonic()
        with CaptureQueriesContext(connection) as captured:
            response = client.get(f"/api/matches?limit=100&offset={offset}")
        latencies.append(time.monotonic() - start)
        queries.append(len(captured))
        assert response.status_code == 200 and response.json()["total"] == 250
        assert len(response.json()["matches"]) == (50 if offset == 200 else 100)
        assert all(
            row["id"] in {str(match.pk) for match in matches[:250]}
            for row in response.json()["matches"]
        )
    # Query count remains bounded as page size grows; no per-match request/query loop.
    assert max(queries) <= 25
    plan = (
        Match.objects.filter(owner=owners[0], deleted_at=None)
        .order_by("-played_at", "-id")[:100]
        .explain()
    )
    runs = []
    for owner in owners[:8]:
        for index in range(4):
            asset = ReplayAsset.objects.create(
                owner=owner, storage_key=f"{owner.pk}/synthetic-{index}/source.mp4", bytes=536870912
            )
            with transaction.atomic():
                lock_owner(owner.pk)
                admit_run(owner)
                runs.append(enqueue_run(owner=owner, asset=asset, request_key=f"load-{index}"))
    with transaction.atomic(), pytest.raises(Throttled):
        lock_owner(owners[8].pk)
        admit_run(owners[8])
    assert AnalysisRun.objects.count() == 32
    fences = [(run, claim_run(run.pk)) for run in runs]
    active = [(run, fence) for run, fence in fences if fence is not None]
    assert len(active) == ExecutionSlot.objects.filter(released_at=None).count() == 2
    assert active[0][0].owner_id != active[1][0].owner_id
    source = Mock()
    source.enqueue.side_effect = CloudFailure("CLOUD_RETRYABLE")
    for _ in range(8):
        RunDispatch.objects.all().update(next_attempt_at=timezone.now())
        dispatch_pending(source)
    assert RunDispatch.objects.filter(status="ATTENTION").count() > 0
    assert not source.launch.called
    AnalysisRun.objects.filter(pk__in=[run.pk for run, _ in active]).update(
        lease_until=now - timedelta(seconds=1)
    )
    reconcile_runs()
    data = snapshot()
    assert {"STALE_SLOTS", "DISPATCH_ATTENTION"} <= set(data["alerts"])
    for run, fence in active:
        cancel_run(run.owner, run.pk)
        assert ExecutionSlot.objects.get(run=run, fence=fence).released_at is None
        acknowledge_stopped(run.pk, fence)
    assert ExecutionSlot.objects.filter(released_at=None).count() == 0
    report = {
        "scope": "Synthetic metadata / quota / dispatch-outage rehearsal; media files not decoded by this test",
        "history_rows": len(matches),
        "owners": len(owners),
        "page_rows": [100, 100, 50],
        "history_seconds": latencies,
        "history_query_counts": queries,
        "pending_cap": len(runs),
        "physical_cap": len(active),
        "source_outage": "controlled mock",
        "reservation_file_bytes": 536870912,
        "query_plan": plan,
    }
    output = Path("reports/m17-load.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
