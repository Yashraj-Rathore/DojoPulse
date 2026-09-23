"""Idempotent local retention worker; deletion also invalidates dependent evaluations."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from backend.core.models import ReplayAsset
from backend.core.storage import delete_asset


class Command(BaseCommand):
    help = __doc__

    def handle(self, *args, **options):
        from django.db.models import Q

        assets = ReplayAsset.objects.filter(
            Q(retain_until__lte=timezone.now()) | Q(deleted_at__isnull=False),
            purge_completed_at__isnull=True,
        ).select_related("owner")
        count = 0
        for asset in assets.iterator():
            delete_asset(asset.owner, asset.pk)
            count += 1
        self.stdout.write(f"Purged {count} expired/tombstoned assets")
