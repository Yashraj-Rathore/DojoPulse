# M16: asynchronous delivery and recovery

Decision D026 / ADR-015, 2026-10-02. Google Cloud remains the selected design, as
confirmed by the user. This document describes implemented local engineering and
controlled-client contracts. No region, billable project, staging deployment or
production release is approved or claimed.

## Durable work and bounded execution

Upload, recording attachment and reprocessing create `AnalysisRun` and its
`RunDispatch` in the same admission/owner transaction. Migration 0009 backfills
queued work. Local polling repairs legacy queued intents. The dispatcher performs
only short control RPCs; HTTP never invokes FFmpeg or waits for analysis.

Each outbox generation has a deterministic Cloud Tasks name. An enqueue timeout
can retry that name; ALREADY_EXISTS is an acknowledgement. Transport retry uses
eight attempts and bounded backoff. Task delivery, submission and result completion
are separate states. The authenticated handler accepts only a UUID/generation
pair, validates Google OIDC audience and the exact service-account email, and
refuses unqualified or quarantined work. Task-name headers are not authentication.

Cloud Run `jobs.run` has no request-id field in the reviewed REST contract. Before
that RPC, the database persists LAUNCHING and reserves an `ExecutionSlot`. A timeout,
unknown launch response or coordinator crash produces UNCERTAIN. A subsequent
delivery cannot submit another execution for that generation. An operation receipt
is stored even if cancellation or worker start races with the response. Missing
receipts require an audited runtime inventory/operator resolution; they are never
interpreted as proof of no execution. Completed operations do not by themselves
prove the execution has stopped.

Physical slots count toward both the global cap (two) and one execution per owner,
including uncertain launches, expired leases and cancelled jobs. An expired lease
revokes publication and requests a stop; it does not release a slot. Only bounded
local cleanup or an authoritative remote terminal observation releases capacity.
An unavailable runtime therefore stalls admission safely. `reconcile_runs
--confirmed-stopped-run UUID --fence N` is an operator acknowledgement, not a kill
command: first inspect/stop the exact execution and retain its receipt.

Worker entry is accepted once per fence. Heartbeats renew a 30-second lease up to
an absolute 420-second attempt deadline. Progress is a coarse phase marker,
not an estimate of percentage of media processed. Cancellation, deletion,
withdrawal, quarantine, owner/asset mismatch, stale fence, lease expiry and deadline
expiry prevent publication. The source hash must still match. Whole-run retries
remain bounded to three attempts; any future managed Job must disable layered
automatic retries. Parser cleanup failure retains capacity for investigation.

Migration 0009 reserves LEGACY slots for pre-existing PROCESSING records, which
require confirmed shutdown during cutover. Reverse migration refuses unreleased
slots or GCS assets. Stop ingress/workers, inspect physical executions, back up and
review data compatibility before rollback; an application rollback is not a
general permission to downgrade a live database.

## Google Cloud compatibility boundary

The current qualified parser depends on host Docker: no network, credentials,
database, host output mount, privilege escalation or writable root. Cloud Run does
not offer the host capabilities required for nested Docker. Its metadata service
also makes the service identity relevant to the isolation review. Running FFmpeg
directly inside a credentialed Cloud Run coordinator would change M15's boundary.

`CLOUD_MEDIA_RUNTIME_QUALIFIED` is therefore false in code, cannot be enabled by an
environment variable, and blocks managed launch, task handling and dispatched
worker execution in Cloud Run. Terraform deliberately contains no media Job.
Qualification needs an equivalent independent sandbox/deadline, hostile-input and
maximum-profile tests, restricted identity/network access, cancellation/stop
receipts and an explicit architecture review. A separate Google-hosted sandbox
executor is an option to review; it has not been selected or provisioned.

## Private storage

`ReplayAsset.storage_provider` and `storage_generation` retain storage identity
outside canonical Match/GameplayEvent contracts. Existing assets remain LOCAL.
The official GCS REST adapter receives an ADC-authorized session, a configured
private bucket and an owner/asset prefix. It performs bounded generation-pinned
downloads and generation-preconditioned deletion of all versions under that exact
prefix. Repeated 404 deletes are harmless; failed listings, pagination loops or
unfinished purges remain failures. Temporary worker copies are removed on exit.

[M06 resumable sessions](evidence-storage.md) now use durable reservations, validated
fixed GCS session URLs and background full-byte verification. Private generation-pinned
range playback and cleanup contracts are tested with controlled clients. External
uploads and real GCS operation remain disabled pending actual IAM/CORS, generation,
ownership, cancellation, late-finalization, range and erasure qualification. No live GCS
object, signed URL or credential was obtained during implementation. The template
enforces uniform bucket access, public-access prevention and no retention lock;
soft delete is disabled so generation deletion can meet the proposed erasure
policy. These settings and independent backup retention still need privacy review.

## Independent controls and restore quarantine

Before an asset/account/match deletion or consent withdrawal mutates the database,
the owner-locked service fsyncs a signed control intent and a signed completeness
checkpoint. A global database mutex serializes checkpoints across owners. Intents
contain internal owner/asset IDs, private object keys and HMAC match suppressions,
not email, player labels, clips or raw provider identifiers. They are still private
control data. Journal failure rolls back the database operation. A transaction
rollback may retain an intent: recovery conservatively favors revocation.

The checkpoint detects missing or changed records in the supplied snapshot. It
does not prove that a supplied snapshot is the latest one. Production requires an
independently replicated, durable control service and a verified current checkpoint;
the local filesystem implementation is not that service. Never restore this
journal from the older database/media backup or use Cloud Run ephemeral scratch
as the production journal. Separate stable keys, namespace, retention, access
control, off-site replication and key recovery/rotation must be reviewed. There is
no empty-journal bootstrap command; missing controls fail closed.

Restore procedure:

1. Stop ingress, dispatch, workers and provider sync in the source and recovery
   environments. Prove old executions stopped; database restore cannot kill them.
2. Restore the database and private media into an isolated environment with
   `RESTORE_QUARANTINE=1`. All HTTP, including readiness/private media, returns 503;
   claims and heartbeats fail closed.
3. Recover the current independent journal and stable journal/suppression keys for
   the same deployment namespace. Verify completeness/freshness against the
   independent checkpoint inventory before replay.
4. Run `python manage.py apply_restore_controls`. This verifies signatures before
   mutations, invalidates all restored sessions/challenges/jobs and revokes prior
   processing/training/link consent. It reapplies account/asset/match deletions,
   HMAC suppressions and post-backup object erasure. Account intents include their
   asset inventory so a crash before individual purge cannot lose that inventory.
5. Retry failed purges under quarantine. Verify object versions/backups against
   policy, old executions, ownership, authorization and the journal. The command
   never turns quarantine off. Only a reviewed handoff may expose data again;
   surviving users must explicitly renew processing consent/re-link.

`rehearse_recovery --confirm-isolated-local` creates two random, new loopback
PostgreSQL databases, exercises migration forward/reverse/forward, takes a native
custom-format pg_dump of synthetic data, records later deletion/withdrawal,
restores with pg_restore, replays twice and checks controls before reads. Only its
new disposable databases are dropped. It does not restore/modify the source
database. Production backup restore, regional failover, RPO/RTO and retained-copy
erasure are separate acceptance requirements.

Linux CI uses `--postgres-container-image postgres:17` for matching dump/restore
client versions; the runner's PostgreSQL 16 client cannot dump a PostgreSQL 17
server. Only that official image and a fresh rehearsal directory are accepted;
database credentials stay in the child environment.

## Deployment preparation and release gates

API WSGI and Next standalone images run as unprivileged users. The API image is a
control-plane image, contains no Docker daemon or FFmpeg and does not poll work.
TLS/proxy trust, allowed hosts, CSRF origins and numeric secret versions require
explicit configuration. The web image retains its loopback API rewrite: qualified
same-origin routing or a reviewed colocated API is still required before hosting.

Terraform supplies private API/Cloud SQL/GCS, a bounded Tasks queue and per-secret
IAM references. It defaults to quarantine, has no public invoker grant, stores no
secret values and refuses provisioning without explicit approval, positive budget
and recovery objectives. Existing private VPC/subnet/service access, project APIs,
SQL user/secret creation, remote state, billing alerting, persistent control service,
web routing, job identity and migrations remain provisioning prerequisites. The
budget variable records a decision; it is not a hard billing cap or live alert.
Development, staging and production need separate projects/state/namespaces/keys.

No general release flag bypasses scientific, provider, privacy or security gates.
External uploads, live match providers and automatic gameplay recognition retain
their existing gates. Keep the source-integrity investigation open. Mock contracts,
container startup and software CI do not establish hosted product readiness.

## Reviewed primary references

- [Cloud Run container contract](https://docs.cloud.google.com/run/docs/container-contract)
- [Cloud Run jobs.run REST contract](https://docs.cloud.google.com/run/docs/reference/rest/v2/projects.locations.jobs/run)
- [Execute Cloud Run Jobs](https://docs.cloud.google.com/run/docs/execute/jobs)
- [HTTP-target Cloud Tasks](https://docs.cloud.google.com/tasks/docs/creating-http-target-tasks)
- [Google OIDC verification](https://google-auth.readthedocs.io/en/latest/reference/google.oauth2.id_token.html)
- [GCS request preconditions](https://docs.cloud.google.com/storage/docs/request-preconditions)
- [Terraform Google Cloud Run service](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_run_v2_service)

The installed Next 16.3.6 output/self-hosting guides were also read before enabling
standalone output. Provider REST schemas still require permitted staging fixtures.
