import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from backend.core.match_worker import process_batch


class Command(BaseCommand):
    help = "Process enabled local match discovery jobs outside HTTP. No network providers."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        if not (settings.DEBUG and settings.LOCAL_MATCH_IMPORTS):
            raise CommandError("Enable LOCAL_MATCH_IMPORTS=1 in the local debug workspace first")
        while True:
            count = process_batch()
            if count:
                self.stdout.write(f"Committed {count} synthetic match pages.")
            if options["once"]:
                return
            time.sleep(2)
