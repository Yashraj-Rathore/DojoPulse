"""Native PostgreSQL rehearsal in two newly created, disposable databases."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from psycopg import sql

SEED = """
from django.contrib.auth import get_user_model
from django.utils import timezone
from backend.core.models import Profile, ReplayAsset, Match
from backend.core.jobs import enqueue_run
from backend.core.storage import private_path
import uuid
for name in ['recovery-deleted', 'recovery-withdrawn']:
    owner = get_user_model().objects.create_user(name, password='synthetic-rehearsal-password')
    Profile.objects.create(user=owner, processing_consent_at=timezone.now())
    asset_id = uuid.uuid4()
    asset = ReplayAsset.objects.create(id=asset_id, owner=owner, storage_key=f'{owner.pk}/{asset_id}/source.mp4', bytes=7)
    path = private_path(asset.storage_key)
    path.parent.mkdir(parents=True)
    path.write_bytes(b'fixture')
    enqueue_run(owner=owner, asset=asset, request_key=name)
    Match.objects.create(owner=owner, played_at=timezone.now(), metadata_revision=1, dataset_kind='synthetic')
"""

DELETE = """
from django.contrib.auth import get_user_model
from backend.core.storage import delete_account, delete_metadata_match, delete_asset
from backend.core.consents import record_consent, POLICY_VERSION
from backend.core.models import Match, ReplayAsset
import uuid
delete_account(get_user_model().objects.get(username='recovery-deleted'))
owner = get_user_model().objects.get(username='recovery-withdrawn')
record_consent(owner, 'PROCESSING', 'WITHDRAW', POLICY_VERSION, uuid.uuid4())
delete_metadata_match(owner, Match.objects.get(owner=owner).pk)
delete_asset(owner, ReplayAsset.objects.get(owner=owner).pk)
"""

VERIFY = """
from django.contrib.auth import get_user_model
from django.test import Client
from backend.core.models import AnalysisRun, Profile, ReplayAsset, Match, RunDispatch
from backend.core.jobs import claim_run
from backend.core.storage import private_path
assert get_user_model().objects.filter(is_active=False).count() == 1
assert Profile.objects.filter(processing_consent_at__isnull=False).count() == 0
assert AnalysisRun.objects.exclude(status='CANCELLED').count() == 0
assert RunDispatch.objects.exclude(status='CANCELLED').count() == 0
assert Match.objects.filter(deleted_at=None).count() == 0
assert ReplayAsset.objects.filter(purge_completed_at=None).count() == 0
for asset in ReplayAsset.objects.all():
    assert not private_path(asset.storage_key).exists()
for run in AnalysisRun.objects.all():
    assert claim_run(run.pk) is None
assert Client().get('/api/overview').status_code == 503
assert Client().get('/health/ready').status_code == 503
"""


class Command(BaseCommand):
    help = "Rehearse dump/restore and migration rollback using synthetic data; never restore the source DB."

    def add_arguments(self, parser):
        parser.add_argument("--confirm-isolated-local", action="store_true")
        parser.add_argument("--postgres-bin", default="")
        parser.add_argument("--postgres-container-image", default="")

    def handle(self, *args, **options):
        config = settings.DATABASES["default"]
        if (
            not options["confirm_isolated_local"]
            or config["ENGINE"] != "django.db.backends.postgresql"
            or config["HOST"] not in {"127.0.0.1", "localhost", "::1"}
        ):
            raise CommandError("An explicitly confirmed loopback PostgreSQL instance is required")
        directory = options["postgres_bin"]
        image = options["postgres_container_image"]
        if image and (image != "postgres:17" or os.name != "posix"):
            raise CommandError("Container clients require Linux and the official postgres:17 image")
        binaries = {}
        for name in ("pg_dump", "pg_restore"):
            if image:
                binaries[name] = name
                continue
            candidate = (
                str(Path(directory) / (name + (".exe" if os.name == "nt" else "")))
                if directory
                else shutil.which(name)
            )
            if not candidate or not Path(candidate).is_file():
                raise CommandError("pg_dump/pg_restore unavailable; provide --postgres-bin")
            binaries[name] = candidate
        names = ["dojopulse_rehearsal_" + uuid.uuid4().hex for _ in range(2)]
        created = []
        with tempfile.TemporaryDirectory(prefix="dojopulse-recovery-") as temporary:
            root = Path(temporary)
            env = dict(os.environ)
            env.update(
                DJANGO_DEBUG="1",
                DEPLOYMENT_NAMESPACE="rehearsal-" + uuid.uuid4().hex,
                CONTROL_JOURNAL_ROOT=str(root / "journal"),
                CONTROL_JOURNAL_KEY=uuid.uuid4().hex,
                PRIVATE_DATA_ROOT=str(root / "media"),
                RESTORE_QUARANTINE="0",
            )
            if config.get("PASSWORD"):
                env["PGPASSWORD"] = config["PASSWORD"]

            def run(argv, environment=env):
                result = subprocess.run(
                    argv,
                    env=environment,
                    cwd=settings.BASE_DIR,
                    capture_output=True,
                    timeout=60,
                    check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if result.returncode:
                    # Child output may contain a DB URL on failures; keep it out of logs.
                    raise CommandError(
                        "Recovery rehearsal child failed; quarantine/cleanup preserved"
                    )

            def select_database(name):
                user = quote(config["USER"], safe="")
                password = (
                    ":" + quote(config.get("PASSWORD", ""), safe="")
                    if config.get("PASSWORD")
                    else ""
                )
                env["DATABASE_URL"] = (
                    f"postgresql://{user}{password}@{config['HOST']}:{config['PORT']}/{name}"
                )

            manage = [sys.executable, "manage.py"]
            common = ["-h", config["HOST"], "-p", str(config["PORT"]), "-U", config["USER"]]

            def postgres_command(name):
                if not image:
                    return [binaries[name]]
                return [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "host",
                    "--mount",
                    f"type=bind,source={root},target=/recovery",
                    "-e",
                    "PGPASSWORD",
                    image,
                    name,
                ]

            try:
                with connection.cursor() as cursor:
                    for name in names:
                        cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
                        created.append(name)
                select_database(names[0])
                run(manage + ["migrate", "--noinput"])
                run(manage + ["migrate", "core", "0008", "--noinput"])
                run(manage + ["migrate", "--noinput"])
                run(manage + ["shell", "-c", SEED])
                dump = "/recovery/backup.dump" if image else str(root / "backup.dump")
                run([*postgres_command("pg_dump"), *common, "-d", names[0], "-Fc", "-f", dump])
                shutil.copytree(root / "media", root / "media-backup")
                run(manage + ["shell", "-c", DELETE])
                run(
                    [
                        *postgres_command("pg_restore"),
                        *common,
                        "-d",
                        names[1],
                        "--no-owner",
                        "--no-privileges",
                        "--exit-on-error",
                        dump,
                    ]
                )
                shutil.copytree(root / "media-backup", root / "restored-media")
                select_database(names[1])
                env["PRIVATE_DATA_ROOT"], env["RESTORE_QUARANTINE"] = (
                    str(root / "restored-media"),
                    "1",
                )
                run(manage + ["apply_restore_controls"])
                run(manage + ["apply_restore_controls"])  # Idempotent replay/purge.
                run(manage + ["shell", "-c", VERIFY])
                self.stdout.write(
                    json.dumps(
                        {
                            "scope": "synthetic-loopback-postgresql",
                            "dump_restore": "PASS",
                            "migration_forward_reverse_forward": "PASS",
                            "controls_before_reads": "PASS",
                            "repeat_replay": "PASS",
                            "production_rpo_rto": "NOT_MEASURED",
                        }
                    )
                )
            finally:
                with connection.cursor() as cursor:
                    for name in created:
                        # Names are freshly created UUIDs, never user-specified targets.
                        cursor.execute(
                            sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
                        )
