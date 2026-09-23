"""Rehearse the schema cutover with pre-existing upload and frozen evaluation rows."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from ingestion.synthetic import START


@pytest.mark.django_db(transaction=True)
def test_upgrade_preserves_upload_event_and_frozen_plan():
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    # Use the actual discovered migration name, avoiding any reconstructed schema.
    old_target = [
        (
            "core",
            next(
                name
                for app, name in executor.loader.disk_migrations
                if app == "core" and name.startswith("0002_")
            ),
        )
    ]
    try:
        executor.migrate(old_target)
        old = executor.loader.project_state(old_target).apps
        owner = old.get_model("auth", "User").objects.create(username="migration-owner")
        asset = old.get_model("core", "ReplayAsset").objects.create(
            owner_id=owner.pk, storage_key="historical/source.mp4", source_sha256="a" * 64
        )
        match = old.get_model("core", "Match").objects.create(
            owner_id=owner.pk,
            asset_id=asset.pk,
            game_build="historical-build",
            knowledge_revision="knowledge/old",
            session_id="historical-session",
            played_at=START,
            mode="ranked",
            context="jin/jin",
        )
        run = old.get_model("core", "AnalysisRun").objects.create(
            owner_id=owner.pk, asset_id=asset.pk, request_key="historical"
        )
        event = old.get_model("core", "GameplayEvent").objects.create(
            owner_id=owner.pk,
            match_id=match.pk,
            run_id=run.pk,
            played_key="1",
            situation="s",
            metric="m",
            detector_version="review/1",
            start_us=0,
            end_us=100,
            eligibility="ELIGIBLE",
            outcome="SUCCESS",
            verified=True,
            evidence=["span/1"],
        )
        drill = old.get_model("core", "DefinitionVersion").objects.create(
            key="historical-drill", kind="drill", payload={}, content_hash="b" * 64
        )
        assignment = old.get_model("core", "DrillAssignment").objects.create(
            owner_id=owner.pk, drill_id=drill.pk
        )
        plan = old.get_model("core", "EvaluationPlan").objects.create(
            owner_id=owner.pk,
            assignment_id=assignment.pk,
            specification={"baseline_membership": [[str(event.pk), "c" * 64]]},
            content_hash="d" * 64,
        )
        snapshots = {
            name: old.get_model("core", name).objects.values().get(pk=obj.pk)
            for name, obj in [("Match", match), ("GameplayEvent", event), ("EvaluationPlan", plan)]
        }
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        current = executor.loader.project_state(latest).apps
        for name, snapshot in snapshots.items():
            assert (
                current.get_model("core", name).objects.values(*snapshot).get(pk=snapshot["id"])
                == snapshot
            )
        source = current.get_model("core", "ReplaySource").objects.get(match_id=match.pk)
        assert source.asset_id == asset.pk and source.content_hash == "a" * 64
        assert source.access_class == "USER_UPLOAD"
    finally:
        MigrationExecutor(connection).migrate(latest)
