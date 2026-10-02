from django.core.management.base import BaseCommand

from backend.core.pilots import expire_enrollments


class Command(BaseCommand):
    help = "Erase expired study memberships, labels and captures; invalidate evidence reports."

    def handle(self, *args, **options):
        self.stdout.write(f"Expired memberships erased: {expire_enrollments()}")
