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

    def handle(self, *args, **options):
        try:
            ledger = FileLedger()
            if options["initialize_local_ledger"]:
                if not settings.DEBUG:
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
                    },
                    sort_keys=True,
                )
            )
        except (ValueError, OSError, CloudFailure) as error:
            raise CommandError("PREVIEW_LEDGER_MAINTENANCE_FAILED") from error
