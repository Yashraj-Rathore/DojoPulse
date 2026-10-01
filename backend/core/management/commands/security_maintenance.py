"""Expire transient security budgets without touching player evidence."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from backend.core.models import RequestBudget, UploadAdmission


class Command(BaseCommand):
    help = "Remove expired rate windows and upload reservations; run at least hourly."

    def handle(self, *args, **options):
        now = timezone.now()
        budgets, _ = RequestBudget.objects.filter(expires_at__lte=now).delete()
        slots, _ = UploadAdmission.objects.filter(expires_at__lte=now).delete()
        from backend.core.accounts import cleanup_account_mail
        from backend.core.models import AccountChallenge, AccountSession

        cleanup_account_mail()
        AccountChallenge.objects.filter(expires_at__lte=now).delete()
        AccountSession.objects.filter(expires_at__lte=now).delete()
        self.stdout.write(f"Expired budgets: {budgets}; upload reservations: {slots}")
