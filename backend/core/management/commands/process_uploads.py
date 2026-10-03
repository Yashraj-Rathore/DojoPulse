from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from backend.core.resumable import reconcile_uploads


class Command(BaseCommand):
    help = "Verify completed uploads and retry expired/cancelled upload cleanup outside HTTP."

    def handle(self, *args, **options):
        if settings.RESTORE_QUARANTINE:
            raise CommandError("RESTORE_QUARANTINE")
        self.stdout.write(f"Reconciled {reconcile_uploads()} upload sessions")
