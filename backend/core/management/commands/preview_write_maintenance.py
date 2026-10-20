"""Redacted offline ledger maintenance; initialization never permits live GCS writes."""

import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from backend.core.cloud import CloudFailure
from backend.core.preview_ledger import FileLedger, held_bytes
from backend.core.preview_writes import cleanup, sync_holds


class Command(BaseCommand):
    help = "Inspect preview write reservations or reconcile already revoked sessions."

    def add_arguments(self, parser):
        parser.add_argument("--initialize-local-ledger", action="store_true")
        parser.add_argument("--cleanup", action="store_true")
        parser.add_argument("--initialize-cloud-journals", action="store_true")
        parser.add_argument("--confirm-empty-namespace", action="store_true")
        parser.add_argument("--reconcile-cloud-workers", action="store_true")

    def handle(self, *args, **options):
        try:
            ledger = FileLedger()
            if options["initialize_cloud_journals"]:
                if (
                    not options["confirm_empty_namespace"]
                    or settings.PREVIEW_LEDGER_BACKEND != "GCS"
                ):
                    raise CommandError("Explicit cloud namespace initialization required")
                from backend.core.cloud_journal import CloudLog

                for kind in ("preview", "control", "execution"):
                    CloudLog(kind).initialize()
            if options["reconcile_cloud_workers"]:
                from backend.core.batch_preview import GoogleBatchPreview
                from backend.core.cloud_execution import reconcile

                reconcile(GoogleBatchPreview(), restore=settings.RESTORE_QUARANTINE)
            if options["initialize_local_ledger"]:
                if not settings.DEBUG or settings.PREVIEW_LEDGER_BACKEND != "FILE":
                    raise CommandError("Local ledger initialization requires DEBUG")
                ledger.initialize()
            rows = sync_holds()
            if options["cleanup"]:
                for identity, (row, _) in rows.items():
                    if row["state"] == "CLEANUP":
                        cleanup(identity)
                rows = sync_holds()
            self.stdout.write(
                json.dumps(
                    {
                        "intents": len(rows),
                        "reserved_bytes": sum(held_bytes(row) for row, _ in rows.values()),
                        "unknown_sessions": sum(
                            x["state"] == "INITIALIZING"
                            for row, _ in rows.values()
                            for x in row["files"].values()
                        ),
                        "cleanup_pending": sum(
                            row["state"] == "CLEANUP" for row, _ in rows.values()
                        ),
                        "live_writes_qualified": settings.GCS_PREVIEW_WRITES_QUALIFIED,
                        "journal_backend": settings.PREVIEW_LEDGER_BACKEND,
                        "pending_cloud_workers": sum(
                            item["state"] != "STOPPED" for item in self.worker_records().values()
                        ),
                    },
                    sort_keys=True,
                )
            )
        except (ValueError, OSError, CloudFailure) as error:
            raise CommandError("PREVIEW_LEDGER_MAINTENANCE_FAILED") from error

    @staticmethod
    def worker_records():
        from backend.core.cloud_execution import records

        return records()
