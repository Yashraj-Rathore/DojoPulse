from django.core.management.base import BaseCommand, CommandError

from backend.core.recovery import apply_restore_controls


class Command(BaseCommand):
    help = "Apply the independently recovered journal; never turn off restore quarantine."

    def handle(self, *args, **options):
        try:
            count = apply_restore_controls()
        except (ValueError, OSError, KeyError) as error:
            raise CommandError("Restore controls failed; keep quarantine enabled") from error
        self.stdout.write(f"Verified {count} control intents; quarantine remains enabled.")
