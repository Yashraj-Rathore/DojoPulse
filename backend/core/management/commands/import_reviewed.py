import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from backend.core.evidence import publish_annotations
from backend.core.models import AnalysisRun, Match


class Command(BaseCommand):
    help = "Operator imports independently reviewed evidence; logs operator provenance."

    def add_arguments(self, parser):
        parser.add_argument("--operator", required=True)
        parser.add_argument("--run", required=True)
        parser.add_argument("--annotations", type=Path, required=True)
        parser.add_argument("--confirm-chronology", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["confirm_chronology"]:
            raise CommandError("Explicit chronology review required")
        operator = get_user_model().objects.get(username=options["operator"])
        run = AnalysisRun.objects.get(pk=options["run"])
        match = Match.objects.get(asset=run.asset)
        annotations = json.loads(options["annotations"].read_text(encoding="utf-8"))
        result = publish_annotations(operator, run.pk, match.pk, annotations)
        match.chronology_verified = True
        match.save(update_fields=["chronology_verified"])
        self.stdout.write(f"Reviewed publication {result.pk}; automation still unvalidated.")
