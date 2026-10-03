"""Official Google REST adapters. Inject an authorized session; tests never use live GCP.

No user-supplied URLs, credentials or object names are accepted. The cloud media
runtime is deliberately gated until its isolation profile is qualified.
"""

import base64
import json
import re
from urllib.parse import parse_qs, quote, urlparse

from django.conf import settings


class CloudFailure(Exception):
    def __init__(self, code, *, ambiguous=False, retryable=True):
        super().__init__(code)
        self.code, self.ambiguous, self.retryable = code, ambiguous, retryable


def resource(value, pattern):
    if not re.fullmatch(pattern, value):
        raise ValueError("INVALID_CLOUD_RESOURCE")
    return value


def authorized_session():
    # Optional cloud dependency set, ADC/workload identity only; no key files in repo.
    import google.auth
    from google.auth.transport.requests import AuthorizedSession

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    return AuthorizedSession(credentials)


class GoogleControl:
    def __init__(self, session, queue, job, target, service_account):
        self.session = session
        self.queue = resource(
            queue, r"projects/[a-z][a-z0-9-]+/locations/[a-z0-9-]+/queues/[a-z0-9-]+"
        )
        self.job = resource(job, r"projects/[a-z][a-z0-9-]+/locations/[a-z0-9-]+/jobs/[a-z0-9-]+")
        parsed = urlparse(target)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("INVALID_TASK_TARGET")
        self.target = target
        self.service_account = resource(
            service_account, r"[a-z0-9-]+@[a-z0-9-]+\.iam\.gserviceaccount\.com"
        )

    def request(self, method, url, *, ambiguous=False, **kwargs):
        try:
            response = self.session.request(
                method, url, timeout=(5, 20), allow_redirects=False, **kwargs
            )
        except Exception as error:
            # Transport implementations may differ. Never log credentials/raw exception text.
            raise CloudFailure("CLOUD_TRANSPORT_FAILURE", ambiguous=ambiguous) from error
        if response.status_code in {429, 500, 502, 503, 504}:
            raise CloudFailure("CLOUD_RETRYABLE", ambiguous=ambiguous)
        if response.status_code not in {200, 201, 204, 404, 409}:
            raise CloudFailure(
                "CLOUD_REQUEST_REJECTED",
                retryable=False,
                ambiguous=ambiguous and response.status_code not in {400, 401, 403, 404},
            )
        return response

    def enqueue(self, dispatch_id, generation):
        name = f"{self.queue}/tasks/dispatch-{dispatch_id}-{generation}"
        payload = json.dumps({"dispatch_id": str(dispatch_id), "generation": generation}).encode()
        response = self.request(
            "POST",
            f"https://cloudtasks.googleapis.com/v2/{self.queue}/tasks",
            json={
                "task": {
                    "name": name,
                    "dispatchDeadline": "60s",
                    "httpRequest": {
                        "httpMethod": "POST",
                        "url": self.target,
                        "headers": {"Content-Type": "application/json"},
                        "body": base64.b64encode(payload).decode(),
                        "oidcToken": {
                            "serviceAccountEmail": self.service_account,
                            "audience": self.target,
                        },
                    },
                }
            },
        )
        if response.status_code == 404:
            raise CloudFailure("QUEUE_NOT_FOUND", retryable=False)
        # ALREADY_EXISTS means our deterministic task was already created.
        return name

    def launch(self, run_id, fence, dispatch_id, generation):
        if not settings.CLOUD_MEDIA_RUNTIME_QUALIFIED:
            raise CloudFailure("CLOUD_MEDIA_RUNTIME_UNQUALIFIED", retryable=False)
        response = self.request(
            "POST",
            f"https://run.googleapis.com/v2/{self.job}:run",
            ambiguous=True,
            json={
                "overrides": {
                    "taskCount": 1,
                    "timeout": f"{settings.RUN_DEADLINE_SECONDS}s",
                    "containerOverrides": [
                        {
                            "args": [
                                "python",
                                "manage.py",
                                "process_runs",
                                "--run-id",
                                str(run_id),
                                "--fence",
                                str(fence),
                            ],
                            "env": [
                                {
                                    "name": "DOJOPULSE_DISPATCH",
                                    "value": f"{dispatch_id}:{generation}",
                                }
                            ],
                        }
                    ],
                }
            },
        )
        if response.status_code not in {200, 201}:
            raise CloudFailure(
                "JOB_LAUNCH_REJECTED", retryable=False, ambiguous=response.status_code == 409
            )
        name = response.json().get("name", "")
        try:
            return resource(
                name, r"projects/[a-z][a-z0-9-]+/locations/[a-z0-9-]+/operations/[a-zA-Z0-9_-]+"
            )
        except ValueError as error:
            raise CloudFailure("JOB_LAUNCH_UNKNOWN", ambiguous=True) from error

    def observe_operation(self, name):
        resource(name, re.escape(self.job.split("/jobs/")[0]) + r"/operations/[a-zA-Z0-9_-]+")
        response = self.request("GET", f"https://run.googleapis.com/v2/{name}")
        if response.status_code != 200:
            raise CloudFailure("OPERATION_UNAVAILABLE")
        operation = response.json()
        execution = operation.get("metadata", {}).get("name", "")
        if execution:
            resource(execution, re.escape(self.job) + r"/executions/[a-zA-Z0-9_-]+")
        # Long-running-operation completion alone does not imply execution completion.
        return execution

    def execution_stopped(self, name):
        resource(name, re.escape(self.job) + r"/executions/[a-zA-Z0-9_-]+")
        response = self.request("GET", f"https://run.googleapis.com/v2/{name}")
        if response.status_code != 200:
            raise CloudFailure("EXECUTION_UNAVAILABLE")
        body = response.json()
        return bool(body.get("completionTime")) and body.get("runningCount", 0) == 0

    def cancel(self, name):
        resource(name, re.escape(self.job) + r"/executions/[a-zA-Z0-9_-]+")
        self.request("POST", f"https://run.googleapis.com/v2/{name}:cancel", json={})


class GooglePrivateStorage:
    def __init__(self, session, bucket, owner_id, asset_id):
        self.session = session
        self.bucket = resource(bucket, r"[a-z0-9][a-z0-9.-]{2,61}[a-z0-9]")
        self.prefix = f"{owner_id}/{asset_id}/"

    def object_url(self, key):
        if not key.startswith(self.prefix) or any(p in {".", "..", ""} for p in key.split("/")):
            raise ValueError("OBJECT_OWNERSHIP_MISMATCH")
        return f"https://storage.googleapis.com/storage/v1/b/{self.bucket}/o/{quote(key, safe='')}"

    def call(self, method, url, *, accepted=(200, 201, 204, 404), **kwargs):
        try:
            response = self.session.request(
                method, url, timeout=(5, 20), allow_redirects=False, **kwargs
            )
        except Exception as error:
            raise CloudFailure("STORAGE_TRANSPORT_FAILURE") from error
        if response.status_code not in accepted:
            response.close()
            raise CloudFailure(
                "STORAGE_REQUEST_REJECTED", retryable=response.status_code in {429, 500, 503}
            )
        return response

    def session_url(self, value):
        try:
            if not isinstance(value, str) or len(value) > 8192:
                raise ValueError
            parsed = urlparse(value)
            query = parse_qs(parsed.query, strict_parsing=True)
        except ValueError:
            raise CloudFailure("INVALID_UPLOAD_SESSION", retryable=False) from None
        if (
            parsed.scheme != "https"
            or parsed.netloc != "storage.googleapis.com"
            or parsed.path != f"/upload/storage/v1/b/{self.bucket}/o"
            or parsed.fragment
            or set(query) - {"uploadType", "name", "upload_id", "ifGenerationMatch"}
            or any(len(values) != 1 for values in query.values())
            or query.get("uploadType") != ["resumable"]
            or query.get("name") != [self.prefix + "source.mp4"]
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,2048}", query.get("upload_id", [""])[0])
            or query.get("ifGenerationMatch", ["0"]) != ["0"]
        ):
            raise CloudFailure("INVALID_UPLOAD_SESSION", retryable=False)
        return value

    def begin_upload(self, key, size, md5_hash, session_id):
        self.object_url(key)
        if key != self.prefix + "source.mp4" or not 0 < size <= 536870912:
            raise ValueError("INVALID_UPLOAD_OBJECT")
        response = self.call(
            "POST",
            f"https://storage.googleapis.com/upload/storage/v1/b/{self.bucket}/o",
            params={"uploadType": "resumable", "name": key, "ifGenerationMatch": "0"},
            headers={"X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/mp4"},
            json={
                "name": key,
                "contentType": "video/mp4",
                "md5Hash": md5_hash,
                "metadata": {"upload_session_id": str(session_id)},
            },
            accepted=(200, 201),
        )
        return self.session_url(response.headers.get("Location", ""))

    def upload_status(self, session, size):
        response = self.call(
            "PUT",
            self.session_url(session),
            data=b"",
            headers={"Content-Length": "0", "Content-Range": f"bytes */{size}"},
            accepted=(200, 201, 308, 404, 410),
        )
        if response.status_code in {404, 410}:
            raise CloudFailure("UPLOAD_SESSION_EXPIRED", retryable=False)
        if response.status_code in {200, 201}:
            return size
        header = response.headers.get("Range", "")
        if not header:
            return 0
        match = re.fullmatch(r"bytes=0-([0-9]{1,12})", header)
        if not match or not 0 < int(match[1]) + 1 <= size:
            raise CloudFailure("INVALID_UPLOAD_OFFSET", retryable=False)
        return int(match[1]) + 1

    def cancel_upload(self, session):
        if session:
            self.call(
                "DELETE",
                self.session_url(session),
                headers={"Content-Length": "0"},
                accepted=(204, 404, 410, 499),
            )

    def inspect_object(self, key):
        response = self.call("GET", self.object_url(key), accepted=(200, 404))
        if response.status_code == 404:
            raise CloudFailure("OBJECT_UNAVAILABLE", retryable=False)
        body = response.json()
        resource(str(body.get("generation", "")), r"[1-9][0-9]{0,29}")
        return body

    def range_stream(self, key, generation, start, end, size, check):
        resource(str(generation), r"[1-9][0-9]{0,29}")
        response = self.call(
            "GET",
            self.object_url(key),
            params={"alt": "media", "generation": generation, "ifGenerationMatch": generation},
            headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"},
            stream=True,
            accepted=(206,),
        )
        try:
            if (
                response.headers.get("Content-Range") != f"bytes {start}-{end}/{size}"
                or response.headers.get("Content-Encoding", "identity") != "identity"
            ):
                raise CloudFailure("INVALID_MEDIA_RANGE", retryable=False)
            remaining = end - start + 1
            for block in response.iter_content(chunk_size=65536):
                check()
                if len(block) > remaining:
                    raise CloudFailure("INVALID_MEDIA_LENGTH", retryable=False)
                remaining -= len(block)
                yield block
            if remaining:
                raise CloudFailure("INVALID_MEDIA_LENGTH", retryable=False)
        finally:
            response.close()

    def delete_object(self, key, generation):
        resource(str(generation), r"[1-9][0-9]{0,29}")
        self.call(
            "DELETE",
            self.object_url(key),
            params={"generation": generation, "ifGenerationMatch": generation},
        )

    def delete_asset(self, key):
        self.object_url(key)
        token = None
        seen = set()
        for _ in range(100):
            params = {"prefix": self.prefix, "versions": "true", "maxResults": 100}
            if token:
                params["pageToken"] = token
            response = self.call(
                "GET", f"https://storage.googleapis.com/storage/v1/b/{self.bucket}/o", params=params
            )
            if response.status_code != 200:
                raise CloudFailure("STORAGE_LIST_UNAVAILABLE")
            body = response.json()
            for item in body.get("items", []):
                self.delete_object(item["name"], item["generation"])
            token = body.get("nextPageToken")
            if not token:
                return
            if token in seen:
                break
            seen.add(token)
        raise CloudFailure("STORAGE_PURGE_INCOMPLETE")

    def download(self, key, generation, destination, size):
        resource(str(generation), r"[1-9][0-9]{0,29}")
        if not 0 < size <= 536870912:
            raise ValueError("INVALID_OBJECT_SIZE")
        response = self.call(
            "GET",
            self.object_url(key),
            params={
                "alt": "media",
                "generation": generation,
                "ifGenerationMatch": generation,
            },
            stream=True,
        )
        try:
            if response.status_code != 200:
                raise CloudFailure("OBJECT_UNAVAILABLE", retryable=False)
            total = 0
            with destination.open("xb") as stream:
                for block in response.iter_content(chunk_size=65536):
                    from analysis.process import execution_check

                    check = execution_check.get()
                    if check:
                        check()
                    total += len(block)
                    if total > size:
                        raise ValueError("OBJECT_SIZE_CHANGED")
                    stream.write(block)
            if total != size:
                raise ValueError("OBJECT_SIZE_CHANGED")
        finally:
            response.close()
