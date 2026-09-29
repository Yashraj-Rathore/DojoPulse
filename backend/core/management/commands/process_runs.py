import json
import time

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from analysis.media import file_hash
from analysis.process import execution_check
from backend.core.jobs import claim_run, finish_run
from backend.core.models import AnalysisRun
from backend.core.parser import analyze_isolated as analyze
from backend.core.storage import private_path


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
            last_check = 0.0

            def check(run_id=run.pk, fence=token):
                nonlocal last_check
                if time.monotonic() - last_check < 0.5:
                    return
                last_check = time.monotonic()
                if not AnalysisRun.objects.filter(
                    pk=run_id,
                    fence=fence,
                    status="PROCESSING",
                    lease_until__gt=timezone.now(),
                    asset__deleted_at=None,
                    owner__is_active=True,
                ).exists():
                    raise ValueError("RUN_REVOKED")

            guard = execution_check.set(check)
            try:
                source = private_path(run.asset.storage_key)
                check()
                pinned_hash = file_hash(source)
                if run.asset.source_sha256 and run.asset.source_sha256 != pinned_hash:
                    raise ValueError("SOURCE_HASH_CHANGED")
                directory = source.parent / str(run.pk)
                directory.mkdir(exist_ok=True)
                metadata = directory / "metadata.json"
                # The unprivileged parser only needs capture declarations, not player identity.
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
                if "source" in report and report["source"]["source_sha256"] != pinned_hash:
                    raise ValueError("SOURCE_HASH_CHANGED")
            except (OSError, ValueError) as error:
                code = (
                    str(error)
                    if str(error)
                    in {
                        "SOURCE_HASH_CHANGED",
                        "RUN_REVOKED",
                        "PARSER_IMAGE_NOT_PINNED",
                        "LOCAL_PARSER_DISABLED",
                        "DECODER_TIMEOUT",
                        "DECODER_MEMORY_LIMIT",
                        "DECODER_OUTPUT_LIMIT",
                        "INVALID_PARSER_REPORT",
                    }
                    else "PARSER_EXECUTION_FAILED"
                )
                report = {"status": "FAILED", "issues": [code], "opportunities": []}
            finally:
                execution_check.reset(guard)
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
                self.stdout.write(f"{run.pk}: {report['status']}")
            elif run.asset.__class__.objects.get(pk=run.asset_id).deleted_at:
                from backend.core.storage import delete_asset

                delete_asset(run.owner, run.asset_id)
