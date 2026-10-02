from django.core.management.base import BaseCommand, CommandError

from backend.core.jobs import acknowledge_stopped, reconcile_runs


class Command(BaseCommand):
    help = "Fence stale runs; release a slot only after an operator verifies the runtime stopped."

    def add_arguments(self, parser):
        parser.add_argument("--confirmed-stopped-run")
        parser.add_argument("--fence", type=int)

    def handle(self, *args, **options):
        reconcile_runs()
        if options["confirmed_stopped_run"]:
            if not options["fence"]:
                raise CommandError("Exact stopped execution fence required")
            acknowledge_stopped(options["confirmed_stopped_run"], options["fence"])
