# Deployment and execution

Current M16 engineering: [delivery/recovery contract](hosted-delivery.md),
[ADR-015](../adr/ADR-015-hosted-delivery-recovery.md) and
[local evidence](../experiment-results/m16-delivery.md). Google adapters are
controlled-client contracts; Terraform is private, approval-gated and quarantined.
Nested Docker is not available in Cloud Run, so managed media launch remains disabled.

Now: local CLI + Django API + PostgreSQL + Next.js, bound to loopback. Docker Compose supplies
PostgreSQL when Docker is available. No paid cloud resources are provisioned by this task.

As of 2026-09-29, the local database worker defaults to the tested Docker parser with an
immutable image ID, bounded ephemeral scratch and no host output mount. PostgreSQL-backed
request/admission budgets and atomic run finalization are implemented. See
[security architecture](security.md) for exact limits, lock ordering and remaining gates.
Hosted request-spooling quotas, an independent kill deadline, IAM and deployment-specific
failure tests are still required; local Docker evidence does not establish these.

Hosted design: one region; private object storage; Cloud SQL; Cloud Run API; Cloud Tasks short
dispatch -> Cloud Run Job; durable PostgreSQL run state/outbox; scheduled reconciler. Lease
fencing protects publication; task acknowledgement is not completion. Bound total active Jobs
independently of queue dispatch concurrency. Whole-job retries are initially controlled by the
application, avoiding layered retry multiplication. Poll status with backoff.

States: UPLOADED, VALIDATING, QUEUED, PROCESSING, REVIEW_REQUIRED, COMPLETED, PARTIAL,
FAILED, CANCELLED. Cancellation and deletion block publication. Errors have stable reason codes.

External release prerequisites: G1-G6 decision; PostgreSQL integration checks; parser isolation
review and malicious fixtures; private storage adapter tests; resumable cancellation/late-finalization
integration test; secrets and identity configuration; restore/deletion rehearsal; measured maximum
file memory; operational cost cap. Scaffold/configuration is not deployed or production-certified.

Cloud Run scratch files consume memory: stream bounded output and test the maximum profile.
Keep one media image and shared domain package. No Redis/Celery or HTTP-bound FFmpeg execution.
