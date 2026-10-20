# Local infrastructure and gated hosting

compose.yaml starts only a loopback PostgreSQL 17 database. It does not deploy the product.
CI uses a separate disposable PostgreSQL service. The workspace's native cluster uses port
55432 instead and is controlled only by tools/dev_postgres.ps1.

Dockerfile.analysis supplies the offline media sandbox. Local Docker qualification was
performed on 2026-09-29; see [M15 evidence](../docs/experiment-results/m15-security.md).
Build from the repository root with:
`docker build -f infrastructure/Dockerfile.analysis -t dojopulse-parser:m15 .`

`backend/core/parser.py` enforces UID 10001, no network/credentials, read-only root/input,
dropped capabilities, no privilege escalation, hard PID/CPU/memory/scratch limits and a
bounded JSON report. There is no host output mount. Set PARSER_IMAGE to the image's sha256
ID; do not use a mutable tag. Production still requires an independent orchestrator deadline,
container/OS vulnerability qualification, complex hostile fixtures and an independent review.
The host Python RSS watchdog is additional defense, not the kernel allocation limit.

To reproduce local qualification, set PARSER_TEST_IMAGE to that ID, PARSER_MAX_PROFILE=1,
and run `pytest tests/test_parser_sandbox.py -v`. This generates a 600-second/512-MiB
synthetic fixture and deliberately tests OOM, PID and scratch exhaustion in disposable
containers. It does not contact a replay provider or validate gameplay recognition.

The parser container must not receive database/cloud credentials. A coordinator leases work,
stages one private source, invokes the sandbox, validates its output and publishes with a
fencing token. Official GCS/Batch adapters and IAM templates are now prepared and
controlled-client tested; actual hosting remains release-gated in
[deployment](../docs/architecture/deployment.md).

Cloud design is Cloud Run website/private API, Cloud SQL, private Cloud Storage and
Cloud Tasks dispatch. ADR-031 previews use dedicated Batch VMs with an offline
decoder; Cloud Run Jobs perform bounded lightweight maintenance.
A versioned deployment must include backup/restore and deletion rehearsals before public use.

M16 adds `Dockerfile.api` (unprivileged WSGI/control plane), `Dockerfile.web`
(Next standalone), pinned optional `requirements-cloud.lock`, and
`google-cloud/` Terraform with a private API/SQL/bucket, bounded Tasks and an
explicit provisioning precondition. `terraform init -backend=false`, `validate`
and `test` need no cloud credentials with the supplied mocks. Never apply the
example variables: no project/region/budget or recovery targets have been approved.

The API defaults to restore quarantine in Terraform. External uploads/hosted
playback and managed media execution remain gated. Optional `preview.tf` prepares
a private VM template, three independent versioned CMEK journal buckets with
create/get/list roles, a server-only website identity bridge and paused scheduled
maintenance. No VM job is launched during planning. `Dockerfile.preview-coordinator`
is trusted/root for the host Docker socket; the decoder remains offline and
unprivileged with no socket/secrets. Cloud Run cannot host that nested boundary.
Actual journal durability/freshness, secret/user creation, VPC/service access,
IAM/CORS/runtime isolation, retention/load/cost and live integration remain
dependencies. See the [hosted preview procedure](../docs/architecture/hosted-recording-previews.md)
and the
[M16 contract](../docs/architecture/hosted-delivery.md) for the operator stop and
restore procedures. Local rehearsal:

```powershell
python manage.py rehearse_recovery --confirm-isolated-local --postgres-bin 'C:\Program Files\PostgreSQL\17\bin'
```

On Linux, install native PostgreSQL client binaries and omit `--postgres-bin`.
With Linux Docker, `--postgres-container-image postgres:17` uses matching clients.
The command creates/drops only its fresh synthetic databases; it does not restore
the configured source database. Hosted RPO/RTO are not measured by this rehearsal.
