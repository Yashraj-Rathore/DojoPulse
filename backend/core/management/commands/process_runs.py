import json
import os
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from analysis.media import file_hash
from analysis.process import execution_check
from backend.core.cloud import CloudFailure
from backend.core.jobs import (
    acknowledge_stopped,
    begin_execution,
    claim_run,
    finish_run,
    heartbeat,
    reconcile_runs,
)
from backend.core.models import AnalysisRun, ExecutionSlot
from backend.core.parser import analyze_isolated as analyze
from backend.core.storage import materialize


class Command(BaseCommand):
    help = "Bounded worker outside HTTP; supports polling or one fenced execution."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--run-id")
        parser.add_argument("--fence", type=int)

    def handle(self, *args, **options):
        if (
            os.getenv("K_SERVICE") or os.getenv("CLOUD_RUN_JOB")
        ) and not settings.CLOUD_MEDIA_RUNTIME_QUALIFIED:
            raise CommandError("CLOUD_MEDIA_RUNTIME_UNQUALIFIED")
        if settings.RESTORE_QUARANTINE:
            raise CommandError("RESTORE_QUARANTINE")
        if options["run_id"]:
            if not options["fence"]:
                raise CommandError("A dispatched run requires its exact fence")
            self.process_one(
                AnalysisRun.objects.select_related("asset").get(pk=options["run_id"]),
                options["fence"],
            )
            return
        while True:
            self.process_batch()
            if options["once"]:
                return
            time.sleep(2)

    def process_batch(self):
        reconcile_runs()
        runs = (
            AnalysisRun.objects.filter(status="QUEUED")
            .select_related("asset")
            .order_by("created_at")[:100]
        )
        for run in runs:
            token = claim_run(run.pk)
            if token is not None:
                self.process_one(run, token)

    def process_one(self, run, token):
        if not begin_execution(run.pk, token):
            return
        last_check = 0.0

        def check():
            nonlocal last_check
            if time.monotonic() - last_check < 0.5:
                return
            last_check = time.monotonic()
            if not heartbeat(run.pk, token):
                raise ValueError("RUN_REVOKED")

        guard = execution_check.set(check)
        stopped = False
        try:
            try:
                check()
                with materialize(run.asset) as source:
                    pinned_hash = file_hash(source)
                    if run.asset.source_sha256 and run.asset.source_sha256 != pinned_hash:
                        raise ValueError("SOURCE_HASH_CHANGED")
                    directory = source.parent / str(run.pk)
                    directory.mkdir(exist_ok=True)
                    metadata = directory / "metadata.json"
                    metadata.write_text(
                        json.dumps(
                            {
                                key: run.asset.metadata[key]
                                for key in ("game_build", "build_confirmed", "overlays_confirmed")
                                if key in run.asset.metadata
                            }
                        ),
                        encoding="utf-8",
                    )
                    report = analyze(source, directory / "report.json", metadata)
                    stopped = True
                    if "source" in report and report["source"]["source_sha256"] != pinned_hash:
                        raise ValueError("SOURCE_HASH_CHANGED")
            except (OSError, ValueError, CloudFailure) as error:
                stopped = str(error) != "PARSER_CLEANUP_UNCONFIRMED"
                codes = {
                    "SOURCE_HASH_CHANGED",
                    "RUN_REVOKED",
                    "PARSER_IMAGE_NOT_PINNED",
                    "LOCAL_PARSER_DISABLED",
                    "DECODER_TIMEOUT",
                    "DECODER_MEMORY_LIMIT",
                    "DECODER_OUTPUT_LIMIT",
                    "INVALID_PARSER_REPORT",
                    "PARSER_CLEANUP_UNCONFIRMED",
                }
                report = {
                    "status": "FAILED",
                    "issues": [str(error) if str(error) in codes else "PARSER_EXECUTION_FAILED"],
                    "opportunities": [],
                }
            if finish_run(run.pk, token, report):
                self.stdout.write(f"{run.pk}: {report['status']}")
            elif run.asset.__class__.objects.get(pk=run.asset_id).deleted_at:
                from backend.core.storage import delete_asset

                delete_asset(run.owner, run.asset_id)
        finally:
            execution_check.reset(guard)
            # A managed worker's report is not proof its hosting execution ended.
            # Its slot is released by authoritative remote reconciliation.
            if (
                stopped
                and ExecutionSlot.objects.filter(run=run, fence=token, runtime="LOCAL").exists()
            ):
                acknowledge_stopped(run.pk, token)
