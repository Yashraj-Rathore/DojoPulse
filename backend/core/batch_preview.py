"""Official Batch/Compute adapters for a dedicated trusted coordinator VM.

The decoder stays in the existing offline container, with no credentials/socket.
Task completion is NOT VM-stop proof. Delete completion AND empty VM inventory
AND absent job are required before physical capacity can be released.
"""

import hashlib
import shlex
from uuid import UUID, uuid5

from django.conf import settings

from backend.core.cloud import CloudFailure, authorized_session, resource
from backend.core.cloud_journal import decode, namespace_id
from backend.core.preview_ledger import canonical


class GoogleBatchPreview:
    runtime = "CLOUD_BATCH"

    def __init__(self, session=None):
        if not (
            settings.CLOUD_MEDIA_RUNTIME_QUALIFIED
            and settings.CLOUD_PREVIEW_RUNTIME_QUALIFIED
            and settings.PREVIEW_LEDGER_RUNTIME_QUALIFIED
        ):
            raise CloudFailure("CLOUD_PREVIEW_RUNTIME_UNQUALIFIED", retryable=False)
        self.parent = resource(
            settings.GOOGLE_BATCH_PARENT, r"projects/[a-z][a-z0-9-]+/locations/[a-z0-9-]+"
        )
        self.project = self.parent.split("/")[1]
        self.template = resource(
            settings.GOOGLE_BATCH_TEMPLATE,
            f"projects/{self.project}/global/instanceTemplates/[a-z][a-z0-9-]+",
        )
        pattern = (
            r"[a-z0-9-]+-docker\.pkg\.dev/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+@sha256:[a-f0-9]{64}"
        )
        self.image = resource(settings.GOOGLE_PREVIEW_COORDINATOR_IMAGE, pattern)
        self.decoder = resource(settings.GOOGLE_PREVIEW_DECODER_IMAGE, pattern)
        self.account = resource(
            settings.GOOGLE_PREVIEW_SERVICE_ACCOUNT,
            r"[a-z0-9-]+@[a-z0-9-]+\.iam\.gserviceaccount\.com",
        )
        self.session = session if session is not None else authorized_session()

    def job_name(self, run_id, fence):
        return f"{self.parent}/jobs/preview-{UUID(str(run_id)).hex}-{int(fence)}"

    def spec(self, run_id, fence, dispatch_id, generation, seconds):
        if not 1 <= fence < 2**31 or not 1 <= generation <= 1000 or not 60 <= seconds <= 2400:
            raise ValueError("INVALID_BATCH_ATTEMPT")
        required = {
            "DATABASE_URL",
            "DJANGO_SECRET_KEY",
            "DATA_SUPPRESSION_KEY",
            "CONTROL_JOURNAL_KEY",
            "PREVIEW_LEDGER_KEY",
        }
        secrets = dict(settings.GOOGLE_PREVIEW_SECRETS)
        if set(secrets) != required:
            raise ValueError("BATCH_SECRET_VERSION_REFERENCES_REQUIRED")
        for value in secrets.values():
            resource(value, r"projects/[a-z0-9-]+/secrets/[A-Za-z0-9_-]+/versions/[1-9][0-9]*")
        env = dict(settings.GOOGLE_PREVIEW_ENV)
        expected = {
            "DEPLOYMENT_NAMESPACE",
            "GCS_PRIVATE_BUCKET",
            "GOOGLE_PREVIEW_LEDGER_BUCKET",
            "GOOGLE_CONTROL_JOURNAL_BUCKET",
            "GOOGLE_EXECUTION_JOURNAL_BUCKET",
        }
        if set(env) != expected or any(
            not isinstance(v, str) or not 1 <= len(v) <= 128 for v in env.values()
        ):
            raise ValueError("BATCH_ENVIRONMENT_INVALID")
        if env["DEPLOYMENT_NAMESPACE"] != settings.DEPLOYMENT_NAMESPACE:
            raise ValueError("BATCH_NAMESPACE_MISMATCH")
        env.update(
            DJANGO_DEBUG="0",
            PREVIEW_LEDGER_BACKEND="GCS",
            CONTROL_JOURNAL_BACKEND="GCS",
            PREVIEW_CLOUD_BACKEND="BATCH",
            PARSER_BACKEND="docker",
            PARSER_IMAGE=self.decoder,
            GOOGLE_PREVIEW_DECODER_IMAGE=self.decoder,
            TMPDIR="/mnt/disks/preview/tmp",
            PRIVATE_DATA_ROOT="/mnt/disks/preview/private",
        )
        argv = [
            "docker",
            "run",
            "--rm",
            "--name",
            "dojopulse-coordinator",
            "--network",
            "host",
            "--memory",
            "4g",
            "--memory-swap",
            "4g",
            "--cpus",
            "2",
            "--pids-limit",
            "256",
            "--mount",
            "type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock",
            "--mount",
            "type=bind,source=/mnt/disks/preview,target=/mnt/disks/preview",
        ]
        for name in sorted(set(env) | set(secrets)):
            argv += ["--env", name]  # Values never appear in the shell command or task logs.
        argv += [
            "--entrypoint",
            "python",
            self.image,
            "manage.py",
            "run_preview_batch",
            "--run-id",
            str(run_id),
            "--fence",
            str(fence),
        ]
        login = (
            "import json,subprocess,urllib.request; "
            "r=urllib.request.Request('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token',headers={'Metadata-Flavor':'Google'}); "
            "t=json.load(urllib.request.urlopen(r,timeout=5))['access_token']; "
            f"subprocess.run(['docker','login','-u','oauth2accesstoken','--password-stdin','https://{self.image.split('/')[0]}'],input=t.encode(),capture_output=True,check=True)"
        )
        if self.image.split("/")[0] != self.decoder.split("/")[0]:
            raise ValueError("BATCH_REGISTRY_MISMATCH")
        script = "\n".join(
            [
                "set -eu",
                "umask 077",
                "mkdir -p /mnt/disks/preview/tmp /mnt/disks/preview/private",
                shlex.join(["python3", "-c", login]),
                shlex.join(["docker", "pull", self.decoder]),
                "exec " + shlex.join(argv),
            ]
        )
        spec = {
            "taskGroups": [
                {
                    "taskCount": 1,
                    "parallelism": 1,
                    "taskSpec": {
                        "runnables": [{"script": {"text": script}, "timeout": f"{seconds}s"}],
                        "computeResource": {"cpuMilli": 2000, "memoryMib": 6144},
                        "maxRetryCount": 0,
                        "maxRunDuration": f"{seconds}s",
                        "environment": {"variables": env, "secretVariables": secrets},
                    },
                }
            ],
            "allocationPolicy": {
                "instances": [{"instanceTemplate": self.template}],
                "serviceAccount": {"email": self.account},
            },
            "logsPolicy": {"destination": "CLOUD_LOGGING"},
        }
        digest = hashlib.sha256(canonical(spec)).hexdigest()
        spec["labels"] = {
            "dojopulse-namespace": namespace_id(),
            "run": UUID(str(run_id)).hex,
            "fence": str(fence),
            "dispatch": UUID(str(dispatch_id)).hex,
            "generation": str(generation),
            "spec-a": digest[:32],
            "spec-b": digest[32:],
        }
        return spec

    def call(self, method, name, *, compute=False, **kwargs):
        root = (
            "https://compute.googleapis.com/compute/v1/"
            if compute
            else "https://batch.googleapis.com/v1/"
        )
        try:
            response = self.session.request(
                method, root + name, timeout=(5, 20), allow_redirects=False, stream=True, **kwargs
            )
        except Exception:
            raise CloudFailure("BATCH_TRANSPORT_FAILURE", ambiguous=method != "GET") from None
        try:
            if response.status_code not in {200, 201, 404}:
                raise CloudFailure(
                    "BATCH_REQUEST_REJECTED",
                    ambiguous=method != "GET" and response.status_code not in {400, 401, 403},
                    retryable=response.status_code in {429, 500, 502, 503, 504},
                )
            raw = bytearray()
            for block in response.iter_content(chunk_size=16384):
                raw.extend(block)
                if len(raw) > 1048576:
                    raise CloudFailure(
                        "BATCH_RESPONSE_LIMIT", ambiguous=method != "GET", retryable=False
                    )
            if response.status_code == 404:
                return None
            return decode(raw)
        finally:
            response.close()

    def create(self, row):
        body = self.call(
            "POST",
            self.parent + "/jobs",
            json=row["spec"],
            params={
                "jobId": row["job"].rsplit("/", 1)[1],
                "requestId": str(uuid5(UUID(row["id"]), "launch")),
            },
        )
        return self.verify(row, body)

    def preflight(self, run, dispatch, fence):
        if (
            run.asset.storage_provider != "GCS"
            or not run.asset.storage_generation
            or run.asset.storage_key != f"{run.owner_id}/{run.asset_id}/source.mp4"
        ):
            raise CloudFailure("BATCH_VERIFIED_SOURCE_REQUIRED", retryable=False)
        self.spec(run.pk, fence, dispatch.pk, dispatch.generation, run.runbudget.attempt_seconds)

    def launch(self, run_id, fence, dispatch_id, generation, *, timeout_seconds=None):
        from backend.core.cloud_execution import launch
        from backend.core.models import AnalysisRun, RunDispatch

        run = AnalysisRun.objects.select_related("asset").get(pk=run_id)
        dispatch = RunDispatch.objects.get(pk=dispatch_id, run=run, generation=generation)
        return launch(self, run, fence, dispatch)

    def verify(self, row, body):
        if (
            not body
            or body.get("name") != row["job"]
            or any(body.get("labels", {}).get(k) != v for k, v in row["spec"]["labels"].items())
        ):
            raise CloudFailure("BATCH_IDENTITY_UNCONFIRMED", ambiguous=True, retryable=False)
        uid = resource(body.get("uid", ""), r"[A-Za-z0-9_-]{1,128}")
        if row["uid"] and row["uid"] != uid:
            raise CloudFailure("BATCH_UID_CHANGED", retryable=False)
        return uid

    def inspect(self, row):
        body = self.call("GET", row["job"])
        if body is not None:
            self.verify(row, body)
        return body

    def delete(self, row):
        body = self.call(
            "DELETE", row["job"], params={"requestId": str(uuid5(UUID(row["id"]), "delete"))}
        )
        if body is None:
            raise CloudFailure("BATCH_DELETE_RECEIPT_UNKNOWN")
        return resource(body.get("name", ""), self.parent + r"/operations/[A-Za-z0-9_-]+")

    def stopped(self, row):
        if not row["delete_operation"] or not row["uid"]:
            return False
        operation = self.call("GET", row["delete_operation"])
        if not operation or operation.get("done") is not True or operation.get("error"):
            return False
        token, seen = None, set()
        for _ in range(40):
            params = {
                "filter": f'labels.batch-job-uid = "{row["uid"]}"',
                "maxResults": 50,
                "returnPartialSuccess": "false",
            }
            if token:
                params["pageToken"] = token
            inventory = self.call(
                "GET", f"projects/{self.project}/aggregated/instances", compute=True, params=params
            )
            if not inventory or inventory.get("unreachables") or inventory.get("warning"):
                raise CloudFailure("BATCH_VM_INVENTORY_UNCONFIRMED")
            for scope in inventory.get("items", {}).values():
                if scope.get("instances"):
                    return False
                if (
                    scope.get("warning", {}).get("code", "NO_RESULTS_ON_PAGE")
                    != "NO_RESULTS_ON_PAGE"
                ):
                    raise CloudFailure("BATCH_VM_INVENTORY_UNCONFIRMED")
            token = inventory.get("nextPageToken")
            if not token:
                return self.call("GET", row["job"]) is None
            if not isinstance(token, str) or len(token) > 4096 or token in seen:
                raise CloudFailure("BATCH_VM_INVENTORY_UNCONFIRMED")
            seen.add(token)
        raise CloudFailure("BATCH_VM_INVENTORY_UNCONFIRMED")
