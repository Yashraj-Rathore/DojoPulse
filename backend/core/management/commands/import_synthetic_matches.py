from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from backend.core.match_ingestion import (
    claim_local_sync,
    commit_local_page,
    link_local_identity,
    start_local_sync,
)
from ingestion.contracts import Operation
from ingestion.synthetic import END, PLAYER, START, SyntheticProvider


class Command(BaseCommand):
    help = "Import two fake matches for an existing local operator; no network or media."

    def add_arguments(self, parser):
        parser.add_argument("--operator", required=True)
        parser.add_argument(
            "--provider", choices=["synthetic-a", "synthetic-b"], default="synthetic-a"
        )
        parser.add_argument("--confirm-synthetic-consent", action="store_true", required=True)

    def handle(self, *args, **options):
        try:
            owner = get_user_model().objects.get(
                username=options["operator"], is_staff=True, is_active=True
            )
        except get_user_model().DoesNotExist as error:
            raise CommandError("An existing active local operator is required") from error
        provider = SyntheticProvider(options["provider"])
        identity = link_local_identity(
            owner,
            "tekken8",
            provider.resolve_player(PLAYER.value, Operation.RESOLVE_ID),
            PLAYER,
            processing_consent=options["confirm_synthetic_consent"],
        )
        job = start_local_sync(owner, identity.pk, provider.key, START, END)
        for _ in range(2):
            token = claim_local_sync(owner, job.pk)
            if token is None:
                break
            job.refresh_from_db()
            page = provider.discover_matches(PLAYER, job.checkpoint, START, END)
            if not commit_local_page(owner, job.pk, token, job.checkpoint, page):
                raise CommandError("Stale local sync; no checkpoint committed")
        job.refresh_from_db()
        self.stdout.write(f"Synthetic sync {job.pk}: {job.status}; no gameplay events generated.")
