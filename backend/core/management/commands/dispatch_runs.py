import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from backend.core.cloud_api import configured_control
from backend.core.dispatch import dispatch_pending, reconcile_cloud


class Command(BaseCommand):
    help = "Deliver the durable Google outbox and reconcile executions; never parse in HTTP."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        if settings.RESTORE_QUARANTINE or not settings.CLOUD_MEDIA_RUNTIME_QUALIFIED:
            raise CommandError("Cloud dispatch remains unqualified/quarantined")
        provider = configured_control()
        while True:
            dispatch_pending(provider)
            reconcile_cloud(provider)
            if options["once"]:
                return
            time.sleep(2)
