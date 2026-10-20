"""One bounded scheduled pass; media parsing remains exclusively on Batch workers."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    def handle(self, *args, **options):
        if (
            settings.RESTORE_QUARANTINE
            or not settings.CLOUD_PREVIEW_RUNTIME_QUALIFIED
            or not settings.CLOUD_MEDIA_RUNTIME_QUALIFIED
            or not settings.PREVIEW_LEDGER_RUNTIME_QUALIFIED
            or not settings.GCS_PREVIEW_WRITES_QUALIFIED
            or not settings.GCS_STORAGE_QUALIFIED
            or settings.PREVIEW_CLOUD_BACKEND != "BATCH"
            or settings.PREVIEW_LEDGER_BACKEND != "GCS"
            or settings.CONTROL_JOURNAL_BACKEND != "GCS"
        ):
            raise CommandError("HOSTED_PREVIEW_MAINTENANCE_UNQUALIFIED")
        from backend.core.batch_preview import GoogleBatchPreview
        from backend.core.cloud_api import configured_control
        from backend.core.cloud_execution import reconcile
        from backend.core.dispatch import dispatch_pending
        from backend.core.jobs import reconcile_runs
        from backend.core.previews import reconcile_previews
        from backend.core.resumable import reconcile_uploads

        if connection.vendor != "postgresql":
            raise CommandError("HOSTED_MAINTENANCE_REQUIRES_POSTGRESQL")
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s)", [1146047056])
            acquired = cursor.fetchone()[0]
        if not acquired:
            self.stdout.write("Hosted preview maintenance already active")
            return
        try:
            reconcile_uploads(limit=1)
            reconcile_runs()
            reconcile(GoogleBatchPreview())
            reconcile_previews()
            dispatch_pending(configured_control(), limit=20)
            self.stdout.write("Hosted preview maintenance pass completed")
        finally:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [1146047056])
