# Local infrastructure and gated hosting

compose.yaml starts only a loopback PostgreSQL 17 database. It does not deploy the product.
CI uses a separate disposable PostgreSQL service. The workspace's native cluster uses port
55432 instead and is controlled only by tools/dev_postgres.ps1.

Dockerfile.analysis is an offline parser **candidate**, not tested here: Docker Desktop's
daemon was unavailable. Build from the repository root with:
`docker build -f infrastructure/Dockerfile.analysis -t ptp-analysis .`

Before hostile input, run as UID 10001 with no network, no credentials, read-only root,
no extra capabilities, no privilege escalation, bounded PIDs/CPU/memory/time, read-only
input mount and a separately quota-bounded output volume. Allow a bounded temporary directory.
Use the orchestrator's hard deadline as well as the Python watchdog. Test maximum-duration,
maximum-complexity and hostile files on the actual host. The current 20ms RSS watchdog is
a local development defense, not a hard allocation limit.

The parser container must not receive database/cloud credentials. A coordinator leases work,
stages one private source, invokes the sandbox, validates its output and publishes with a
fencing token. No cloud adapter, IAM binding or resumable upload integration is claimed here.
Those dependencies are release-gated in docs/architecture/deployment.md.

Cloud design remains Cloud Run API, Cloud Run Jobs, Cloud SQL and private Cloud Storage;
Cloud Tasks can dispatch work after a real need, with explicit job caps and a reconciler.
A versioned deployment must include backup/restore and deletion rehearsals before public use.
