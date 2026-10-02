import json
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone

from backend.core.models import AttemptMetric, OperatorWork, RequestMetric, RunBudget
from backend.core.operations import snapshot


class Command(BaseCommand):
    help = "Redacted local operations snapshot; exit nonzero on alerts; optional bounded retention."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=1)
        parser.add_argument("--fail-on-alert", action="store_true")
        parser.add_argument("--prune", action="store_true")

    def handle(self, *args, **options):
        if not 1 <= options["days"] <= 30:
            raise CommandError("Use a reporting window from 1 to 30 days")
        if options["prune"]:
            cutoff = timezone.now() - timedelta(days=settings.OPS_RETENTION_DAYS)
            RequestMetric.objects.filter(minute__lt=cutoff).delete()
            OperatorWork.objects.filter(created_at__lt=cutoff).delete()
            AttemptMetric.objects.filter(
                slot__released_at__lt=cutoff, slot__run__runbudget__state="CLOSED"
            ).delete()
            # Current-day charges and any uncertain physical work always survive pruning.
            RunBudget.objects.filter(state="CLOSED", day__lt=cutoff.date()).exclude(
                run__executionslot__released_at=None, run__executionslot__isnull=False
            ).delete()
        data = snapshot(options["days"])
        self.stdout.write(json.dumps(data, cls=DjangoJSONEncoder, sort_keys=True))
        if options["fail_on_alert"] and data["alerts"]:
            raise CommandError("OPERATIONS_ALERTS_PRESENT")
