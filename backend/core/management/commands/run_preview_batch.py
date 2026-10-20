"""Trusted Batch coordinator. This command does not decode media in its own process."""

import json
import os
import re

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from analysis.process import run_bounded
from backend.core.cloud_execution import allowed
from backend.core.models import AnalysisRun, ExecutionSlot


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--run-id", required=True)
        parser.add_argument("--fence", required=True, type=int)

    def handle(self, *args, **options):
        if (
            not settings.CLOUD_MEDIA_RUNTIME_QUALIFIED
            or not settings.CLOUD_PREVIEW_RUNTIME_QUALIFIED
            or not settings.PREVIEW_LEDGER_RUNTIME_QUALIFIED
            or not settings.GCS_PREVIEW_WRITES_QUALIFIED
            or settings.PREVIEW_CLOUD_BACKEND != "BATCH"
            or settings.PREVIEW_LEDGER_BACKEND != "GCS"
            or settings.CONTROL_JOURNAL_BACKEND != "GCS"
            or settings.PARSER_BACKEND != "docker"
            or settings.RESTORE_QUARANTINE
        ):
            raise CommandError("BATCH_PREVIEW_UNQUALIFIED")
        run_id, fence = options["run_id"], options["fence"]
        run = AnalysisRun.objects.get(pk=run_id, pipeline_version="recording-preview/1")
        if not ExecutionSlot.objects.filter(
            run=run, fence=fence, runtime="CLOUD_BATCH", released_at=None
        ).exists() or not allowed(run.pk, fence):
            raise CommandError("BATCH_PREVIEW_REVOKED")
        expected = settings.GOOGLE_PREVIEW_DECODER_IMAGE
        result = run_bounded(
            ["docker", "image", "inspect", "--format", "{{json .}}", expected],
            timeout=15,
            max_output=65536,
        )
        info = json.loads(result.stdout)
        image_id = info.get("Id", "")
        if expected not in info.get("RepoDigests", []) or not re.fullmatch(
            r"sha256:[a-f0-9]{64}", image_id
        ):
            raise CommandError("BATCH_DECODER_IDENTITY_UNCONFIRMED")
        # sandbox_command consumes a local immutable image ID and uses --pull never.
        previous = settings.PARSER_IMAGE
        settings.PARSER_IMAGE = image_id
        os.environ["DOJOPULSE_BATCH_WORKER"] = "1"
        try:
            call_command("process_runs", run_id=str(run.pk), fence=fence)
        finally:
            settings.PARSER_IMAGE = previous
            os.environ.pop("DOJOPULSE_BATCH_WORKER", None)
