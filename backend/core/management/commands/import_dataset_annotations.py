"""Explicitly import one owned reviewed dataset source through the canonical publisher."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from backend.core.datasets import canonical_measurement
from backend.core.evidence import publish_annotations
from backend.core.models import AnalysisRun, DatasetSnapshot, Match
from backend.core.ownership import lock_owner
from backend.core.security import capacity_lock


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--owner", required=True, type=int)
        parser.add_argument("--run", required=True)
        parser.add_argument("--match", required=True)
        parser.add_argument("--snapshot", required=True)
        parser.add_argument("--confirm-owned-reviewed-source", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["confirm_owned_reviewed_source"]:
            raise CommandError("Explicit owned-source import confirmation required")
        owner = get_user_model().objects.get(pk=options["owner"], is_staff=True, is_active=True)
        lock_owner(owner.pk)
        capacity_lock()
        run = AnalysisRun.objects.get(pk=options["run"], owner=owner)
        match = Match.objects.get(pk=options["match"], owner=owner, asset=run.asset)
        row = DatasetSnapshot.objects.get(pk=options["snapshot"], invalidated_at=None)
        source = next((s for s in row.data["sources"] if s["source_id"] == str(run.asset_id)), None)
        if not source:
            raise CommandError("Owned source is not in this snapshot")
        canonical_measurement(run, match, row.pk, source["annotations"])
        result = publish_annotations(
            owner, run.pk, match.pk, source["annotations"], dataset_snapshot_id=row.pk
        )
        self.stdout.write(f"Canonical reviewed publication {result.pk}; real release remains gated")
