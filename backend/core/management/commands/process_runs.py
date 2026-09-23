import json
import time

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from backend.core.jobs import claim_run, finish_run
from backend.core.models import AnalysisRun, ReplayAsset, ReplaySource
from backend.core.storage import private_path
from tools.analyze_capture import analyze


class Command(BaseCommand):
    help = "Poll local work outside HTTP; --once processes one bounded batch."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        while True:
            self.process_batch()
            if options["once"]:
                return
            time.sleep(2)

    def process_batch(self):
        runs = (
            AnalysisRun.objects.filter(
                Q(status="QUEUED") | Q(status="PROCESSING", lease_until__lt=timezone.now())
            )
            .select_related("asset")
            .order_by("created_at")[:100]
        )
        for run in runs:
            token = claim_run(run.pk)
            if token is None:
                continue
            try:
                source = private_path(run.asset.storage_key)
                directory = source.parent / str(run.pk)
                directory.mkdir(exist_ok=True)
                metadata = directory / "metadata.json"
                metadata.write_text(json.dumps(run.asset.metadata), encoding="utf-8")
                report = analyze(source, directory / "report.json", metadata)
            except (OSError, ValueError):
                report = {"status": "FAILED", "issues": ["LOCAL_IO_FAILURE"], "opportunities": []}
            if (
                run.asset.source_sha256
                and "source" in report
                and report["source"]["source_sha256"] != run.asset.source_sha256
            ):
                report = {
                    "status": "FAILED",
                    "issues": ["SOURCE_HASH_CHANGED"],
                    "opportunities": [],
                }
            if finish_run(run.pk, token, report):
                if "source" in report:
                    ReplayAsset.objects.filter(pk=run.asset_id, deleted_at__isnull=True).update(
                        source_sha256=report["source"]["source_sha256"]
                    )
                    ReplaySource.objects.filter(
                        asset_id=run.asset_id, asset__deleted_at=None
                    ).update(content_hash=report["source"]["source_sha256"])
                self.stdout.write(f"{run.pk}: {report['status']}")
            elif run.asset.__class__.objects.get(pk=run.asset_id).deleted_at:
                from backend.core.storage import delete_asset

                delete_asset(run.owner, run.asset_id)
