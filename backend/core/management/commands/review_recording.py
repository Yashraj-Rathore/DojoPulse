from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.management.base import BaseCommand, CommandError

from backend.core.recordings import review_recording


class Command(BaseCommand):
    help = "Confirm visually reviewed recording attribution; does not approve gameplay labels."

    def add_arguments(self, parser):
        parser.add_argument("--operator", required=True)
        parser.add_argument("--source", required=True)
        parser.add_argument("--source-hash", required=True)
        parser.add_argument("--knowledge", required=True)
        parser.add_argument("--note", required=True)
        parser.add_argument("--confirm-reviewed", action="store_true")

    def handle(self, *args, **options):
        try:
            operator = get_user_model().objects.get(username=options["operator"])
            source = review_recording(
                operator,
                options["source"],
                options["source_hash"],
                options["knowledge"],
                options["note"],
                confirm_reviewed=options["confirm_reviewed"],
            )
        except (ObjectDoesNotExist, PermissionDenied, ValidationError) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            f"Recording {source.pk} attributed. Gameplay annotation review is still required."
        )
