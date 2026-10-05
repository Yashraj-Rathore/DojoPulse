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
from datetime import timedelta
from backend.core.models import PilotStudy, PilotEnrollment, PilotSession, PilotCapture, PilotTask, PilotReview, PilotGateReport
manager = get_user_model().objects.create_user('recovery-pilot-manager', is_staff=True)
study = PilotStudy.objects.create(owner=manager, title='Synthetic recovery', dataset_kind='synthetic', protocol={}, request_id=uuid.uuid4())
participant = PilotEnrollment.objects.create(owner=owner, study=study, role='PARTICIPANT', consent_digest='fixture', expires_at=timezone.now()+timedelta(days=1))
session = PilotSession.objects.create(enrollment=participant, code='fixture', phase='BASELINE', played_at=timezone.now(), state='CAPTURED', request_id=uuid.uuid4())
capture = PilotCapture.objects.create(session=session, asset=asset, source_sha256='f'*64, game_build='synthetic', duration_seconds=1)
reviewers = []
for role in ['REVIEWER', 'REVIEWER', 'ADJUDICATOR']:
    reviewer = get_user_model().objects.create_user('recovery-reviewer-'+uuid.uuid4().hex)
    reviewers.append(PilotEnrollment.objects.create(owner=reviewer, study=study, role=role, consent_digest='fixture', expires_at=timezone.now()+timedelta(days=1)))
task = PilotTask.objects.create(capture=capture, kind='TARGET', start_us=0, end_us=1, reviewer_one=reviewers[0], reviewer_two=reviewers[1], adjudicator=reviewers[2], request_id=uuid.uuid4())
PilotReview.objects.create(task=task, reviewer=reviewers[0], label={'private': 'must-erase'}, label_digest='fixture', seconds=1, request_id=uuid.uuid4())
PilotGateReport.objects.create(study=study, gate='G1', revision=1, data={'private': 'must-erase'}, content_hash='fixture')
from django.conf import settings
from backend.core.resumable import begin, write_chunk, request_completion
import base64, hashlib
settings.LOCAL_OPERATOR_UPLOADS = True
pending_owner = get_user_model().objects.create_user('recovery-pending-upload', is_staff=True)
content = b'pending-synthetic-upload'
pending = begin(pending_owner, uuid.uuid4(), len(content), hashlib.sha256(content).hexdigest(),
    base64.b64encode(hashlib.md5(content, usedforsecurity=False).digest()).decode(),
    {'game_build': 'fixture', 'session_id': 'recovery-pending', 'played_at': timezone.now().isoformat(),
     'source_kind': 'ranked', 'dataset_kind': 'synthetic', 'characters': ['jin', 'jin']})
write_chunk(pending_owner, pending.pk, 0, content)
request_completion(pending_owner, pending.pk)
from backend.core import knowledge
from backend.core.models import Game, GameBuild, KnowledgeProposal
settings.DEBUG = True
owner.is_staff = True
owner.save(update_fields=['is_staff'])
game, _ = Game.objects.get_or_create(key='tekken8')
build = GameBuild.objects.create(key='recovery-fixture', game=game, platform='synthetic')
asset.metadata = {'game_build': 'recovery-fixture', 'platform': 'synthetic', 'dataset_kind': 'synthetic'}
asset.source_sha256 = hashlib.sha256(b'fixture').hexdigest()
asset.retain_until = timezone.now()+timedelta(days=1)
asset.save(update_fields=['metadata', 'source_sha256', 'retain_until'])
asset.analysisrun_set.update(status='REVIEW_REQUIRED', result={'source': {'source_sha256': asset.source_sha256, 'duration_seconds': 1}})
operators = [get_user_model().objects.create_user('knowledge-review-'+str(i), is_staff=True) for i in range(2)]
proposal = knowledge.propose(owner, key='recovery/build/1', kind='build', build_key=build.pk, dataset_kind='synthetic',
    payload={'game_build': 'recovery-fixture', 'platform': 'synthetic', 'overlays': ['build', 'frames']},
    provenance={'reference': 'recovery/1', 'rights': 'OWNED_RECORDING', 'share_with_reviewers': True, 'publish_game_facts': True},
    asset_ids=[asset.pk], reviewer_one=operators[0].pk, reviewer_two=operators[1].pk, request_id=uuid.uuid4())
for operator in operators:
    knowledge.review(operator, proposal.pk, proposal_hash=proposal.content_hash, decision='APPROVE',
        note='Synthetic restore proof', confirm_reviewed=True, request_id=uuid.uuid4())
knowledge.publish(owner, proposal.pk)
# Minimal private-storage fixture, not a qualified dataset or measurement release.
from backend.core.models import DatasetCollection, DatasetStudy, DatasetSnapshot, DatasetPartition, DefinitionVersion
dataset = DatasetCollection.objects.create(owner=manager, title='Synthetic erasure fixture', dataset_kind='synthetic',
    knowledge=DefinitionVersion.objects.get(pk='recovery/build/1'), measurement={'restore-fixture': True},
    sampling={'private': 'must-erase'}, request_id=uuid.uuid4())
DatasetStudy.objects.create(dataset=dataset, study=study)
DatasetSnapshot.objects.create(dataset=dataset, sequence=1, request_id=uuid.uuid4(), data={'private': 'must-erase'})
DatasetPartition.objects.create(dataset=dataset, kind='PLAYER', token='a'*64, binding='', split='held-out')
from backend.core.models import DrillAssignment, PracticeLog
practice_drill = DefinitionVersion.objects.create(key='recovery/drill/1', kind='drill', status='APPROVED', payload={'synthetic_only': True})
assignment = DrillAssignment.objects.create(owner=manager, drill=practice_drill, drill_hash=practice_drill.content_hash, diagnosis={'private': 'must-erase'})
PracticeLog.objects.create(owner=manager, assignment=assignment, request_id=uuid.uuid4(), state='COMPLETED',
    started_at=timezone.now(), ended_at=timezone.now(), reported_attempts=40, pins={'private': 'must-erase'})

"""

DELETE = """
from django.contrib.auth import get_user_model
from backend.core.storage import delete_account, delete_metadata_match, delete_asset
from backend.core.consents import record_consent, POLICY_VERSION
from backend.core.models import Match, ReplayAsset
import uuid
delete_account(get_user_model().objects.get(username='recovery-deleted'))
owner = get_user_model().objects.get(username='recovery-withdrawn')
from backend.core.pilots import withdraw
from backend.core.models import PilotEnrollment
withdraw(owner, PilotEnrollment.objects.get(owner=owner).study_id)
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
from backend.core.models import PilotEnrollment, PilotReview, PilotGateReport
assert not PilotEnrollment.objects.filter(state='ACTIVE').exists()
assert not PilotReview.objects.exists()
assert not PilotGateReport.objects.filter(invalidated_at=None).exists()
assert not PilotGateReport.objects.exclude(data={}).exists()
assert Match.objects.filter(deleted_at=None).count() == 0
assert ReplayAsset.objects.filter(purge_completed_at=None).count() == 0
from backend.core.models import UploadSession
assert UploadSession.objects.count() == 1
assert not UploadSession.objects.exclude(state='CANCELLED').exists()
assert not UploadSession.objects.exclude(expected_sha256='', expected_md5='', claim_digest='').exists()
from backend.core.models import KnowledgeProposal, KnowledgeReview, KnowledgeEvidence, DefinitionVersion
assert KnowledgeProposal.objects.count() == 1
assert not KnowledgeProposal.objects.exclude(state='WITHDRAWN', payload={}, provenance={}).exists()
assert not KnowledgeEvidence.objects.exists()
assert not KnowledgeReview.objects.exclude(note='').exists()
assert DefinitionVersion.objects.get(pk='recovery/build/1').status == 'APPROVED'
from backend.core.models import DatasetCollection, DatasetSnapshot, DatasetPartition
assert DatasetCollection.objects.count() == 1
assert not DatasetCollection.objects.exclude(state='CLOSED', measurement={}, sampling={}).exists()
assert not DatasetCollection.objects.filter(deleted_at=None).exists()
assert not DatasetSnapshot.objects.filter(invalidated_at=None).exists()
assert not DatasetSnapshot.objects.exclude(data={}).exists()
assert not DatasetPartition.objects.exists()
from backend.core.models import PracticeLog, DrillAssignment
assert not PracticeLog.objects.exists()
assert not DrillAssignment.objects.exclude(diagnosis={}, status='CANCELLED').exists()

# Its immutable historical definition is retained; the restored grant is permanently revoked.
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
                            "pending_upload_erasure": "PASS",
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
