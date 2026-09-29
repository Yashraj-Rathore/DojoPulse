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
fencing token. No cloud adapter, IAM binding or resumable upload integration is claimed here.
Those dependencies are release-gated in docs/architecture/deployment.md.

Cloud design remains Cloud Run API, Cloud Run Jobs, Cloud SQL and private Cloud Storage;
Cloud Tasks can dispatch work after a real need, with explicit job caps and a reconciler.
A versioned deployment must include backup/restore and deletion rehearsals before public use.
