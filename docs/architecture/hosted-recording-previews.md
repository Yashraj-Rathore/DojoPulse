# Hosted private recording previews

Architecture 2.24.0 / ADR-031 / D046, 2026-10-20. This is implemented preparation
for M06.11, with controlled HTTP clients and local PostgreSQL qualification.
No Google Cloud resources have been provisioned or live flags enabled.
M06.11 remains PARTIAL until the deployment-specific acceptance below is met.
Existing [private preview](private-recording-previews.md) and
[write recovery](preview-write-recovery.md) contracts continue to apply.

## Processing and trust boundaries

| Component | Responsibility and boundary |
|---|---|
| Next website | Server-only `/api/*` bridge; service identity stays out of browser JavaScript, response headers and logs. Default local route still targets loopback. Cloud configuration pins one HTTPS Cloud Run API and its expected host |
| Private Django API | End-user sessions, ownership, CSRF, admission, source verification, outbox and private generation-pinned range playback. No FFmpeg in requests |
| Cloud Tasks | Deterministic short dispatch, root service audience and exact service-account verification. Duplicate delivery cannot duplicate creation |
| Google Batch VM | One attempt, one task, zero task retries. Named tested VM image/template, immutable coordinator and decoder digests. Private networking; trusted coordinator owns the Docker socket and staging |
| Offline decoder | Existing UID 10001, read-only root/input, no network/credentials/socket, dropped capabilities, no privilege escalation, PID/CPU/memory/tmpfs limits, bounded descriptor-based output extraction. Docker sandbox qualification is separate from actual VM qualification |
| Maintenance Cloud Run Job | One bounded verification/reconciliation/dispatch pass, one task, zero retries, PostgreSQL session advisory lock. Scheduler starts paused; job/API start quarantined |
| Private media bucket | Retained original plus separately reserved preview attempts. Create-only resumable writes, pinned generations, cancellation before all-version erasure and verified empty inventory |
| Three independent journal buckets | Preview-write recovery, account/control intent and physical worker intent. Separate from database backups and media restore; encrypted with explicit CMEK, versioned, retained and append-only for application principals |

The credentialed coordinator is trusted and runs as root to control host Docker.
It must never be confused with the hostile-media decoder. Its image contains no
FFmpeg. The decoder image is pulled by immutable Artifact Registry digest; worker
entry checks the local RepoDigest and uses its immutable local image ID with
`--pull never`. Secrets are pinned numeric Secret Manager version references,
resolved into the trusted task environment, never command-line values. Runtime
IAM must prevent an untrusted principal creating a job with forged labels/specs.

This path is a future explicitly qualified **staff preview pilot**. It does not
enable the older analysis launcher, general public upload/signup or scientific
intake. Preview READY still means private playback; no Match or GameplayEvent is
created and precise-gameplay/scientific approval remains false. Provider classes
and external IDs remain unchanged. Google infrastructure APIs confer no Tekken
data-access permission; no game endpoint or replay acquisition is implemented.

## Shared journal contract

`PREVIEW_LEDGER_BACKEND=GCS` and `CONTROL_JOURNAL_BACKEND=GCS` select the official
JSON storage adapter. FILE remains the local default. Each kind uses an explicit
deployment namespace and a separate bucket. Its prefix hashes the namespace;
signed contents also bind the full namespace, kind and schema version.

An operator explicitly creates `00000000.json`, a signed genesis. Admission and
restore never invent a missing genesis. Each subsequent immutable object binds
its sequence and previous object's SHA-256. `ifGenerationMatch=0` arbitrates
concurrent writers; a collision rereads the winner and reapplies the transition,
up to six times. Lost append responses resolve only through identical read
receipts; no unconfirmed append authorizes SQL changes or refunds.

Readers always fetch fresh bounded inventory, then verify every pinned generation
and signature/hash-chain link. A missing sequence, changed generation/signature,
foreign namespace, unavailable store, torn record or bound overflow fails closed.
Only immutable generation-pinned bytes use a process-wide **8 MiB LRU cache**;
inventory is never cached. The current bound is **4,096 events per kind and 16 KiB
per signed record**, at most 34 bounded inventory pages. This is a bounded pilot
archive, not an unlimited production log. No automatic compaction, namespace
rotation, journal deletion or checkpoint reset is implemented. Plan capacity and
approved rotation before enabling workload; never truncate to regain service.

The Terraform append role grants only create/get/list, with no overwrite/delete.
Generation preconditions, retention and resource IAM must be tested on the actual
project. Project administrators/full archive replacement, key compromise and
cross-region recovery are not solved by HMAC or mocked tests. Keep independently
protected archive/key custody and freshness evidence outside SQL/media restores.
Journal contents are sensitive: signed IDs, deletion intent and encrypted upload
capabilities need a reviewed retention, access and privacy policy.

## Execution, cancellation and recovery

The execution journal pins run/fence, owner/asset, original bytes/hash/generation,
dispatch generation, timeout, deterministic job name and spec fingerprint.
Configuration/source validation precedes a physical slot claim. PLANNED is
durable before SUBMITTING; SUBMITTING precedes the create RPC. A lost response
does not authorize a second POST. Reconciliation can recover the original UID;
foreign fingerprints/changed UIDs never authorize deletion. Late receipts cannot
revive a revoked attempt. Cloud-generated labels may be added to the expected
application labels.

Application admission retains the global two-worker and one-per-owner caps,
including independent orphan attempts missing from restored SQL. Startup gets at
most ten minutes within the existing 1,920-second preview deadline; after entry,
regular fenced heartbeats apply. Expiry/terminal output is not stop proof.
Only a completed successful delete operation, a complete empty Compute inventory
filtered by verified `batch-job-uid`, and an absent job permit STOPPED/refund.
Unknown create/delete handles, 404 alone, partial/unreachable inventory and
transport failures retain slots. Missing durable receipts require audited
operator investigation; elapsed time alone never establishes erasure/shutdown.

Cancellation/withdrawal/deletion durably revoke execution and preview intent
before SQL mutation. The revocation survives transaction rollback and blocks
heartbeat/reclaim. A run-level tombstone is recorded even before its first
execution/output intent, closing the queued/claim-to-plan cancellation interval.
An independently STOPPED attempt also acknowledges a resurrected SQL slot without
another remote stop request. Source quota missing from restored SQL stays charged even
after its VM stops; no automatic source erasure or false refund is inferred.
Operators must reconcile the original using verified source or deletion records.

Restore procedure extends M16:

1. Stop ingress, pause scheduler/Tasks, stop every old API/maintenance/worker
   process and retain runtime inventory. Environment quarantine on a new revision
   alone does not recall already running processes.
2. Restore SQL/media **without replacing the current three journals**. Preserve
   namespace and key versions. Set `RESTORE_QUARANTINE=1` for all new roles.
3. Run `apply_restore_controls`. It verifies all independent stores, revokes
   restored sessions/consents/work, stops known and post-backup Batch workers,
   cancels write capabilities and erases derived generations. A failure leaves
   quarantine and quota intact; repeat only after resolving the observed failure.
4. Verify originals retained where policy requires, all removed artifacts absent,
   no stale worker/session can republish and orphan charges are reconciled.
   Re-authorization/release requires the actual M16 acceptance procedure.

`preview_write_maintenance --reconcile-cloud-workers --cleanup` provides a bounded
operator pass. Status output is redacted counts, never capability URLs or secrets.
Do not use local confirmed-stop overrides as substitutes for cloud inventory.

## Preparation and activation gates

`infrastructure/google-cloud/preview.tf` is optional (`preview=null` by default).
No `terraform apply` is part of this implementation. The base module still needs
an explicitly authorized project, region, budget and recovery targets. Budget
alerts are not a hard spending cap.

After authorization, prepare the quarantined base API first, then copy its exact
`api_uri` into `preview.api_origin`. The route precondition prevents sending user
cookies to another service. Supply immutable images, a named pretested Batch VM
image with Docker/Python3/Batch agent, journal geography/CMEK/retention and the
separate pinned PREVIEW_LEDGER_KEY. Terraform prepares private VM/SQL/media,
three protected journals, least-role templates and the public website/private
API bridge. Scheduler remains paused, API/maintenance quarantined.

Before a reviewed code change enables any production qualification flag, obtain
and record actual evidence for:

- Region/privacy/budget, pinned image/OS vulnerability review and independent
  isolation/security approval. Verify offline decoder cannot reach VM metadata,
  network, socket, secrets or other owners, and hard limits/deadlines hold.
- VPC/private Google access or controlled NAT, SQL connectivity/credentials,
  Secret Manager numeric versions, Artifact Registry pulls and exact IAM.
  Prove journal writers cannot overwrite/delete or escape namespace/bucket.
- CMEK service-agent permissions, geography, retention/key custody, independent
  archive freshness, concurrent multi-host appends, outage/torn-tail recovery
  and projected archive capacity/read cost. No mock establishes these.
- Browser sign-in/CSRF and private service invocation, ownership/foreign ranges,
  request streaming/time limits, direct GCS resumable CORS and capability
  cancellation/late completion/all-version erasure on the real service.
- Maximum-profile real conversion, startup/queue/kill timing, concurrency,
  failure/retry/cancel/delete/withdrawal, absent SQL workers, full controlled
  restore and operational RPO/RTO; measured resource/cost bounds and response owner.
- Explicit initialization of all three **new empty** namespaces using
  `preview_write_maintenance --initialize-cloud-journals --confirm-empty-namespace`.
  Never bootstrap over missing production history. Keep stable keys/namespace.

`GCS_STORAGE_QUALIFIED`, `GCS_PREVIEW_WRITES_QUALIFIED`,
`CLOUD_MEDIA_RUNTIME_QUALIFIED`, `CLOUD_PREVIEW_RUNTIME_QUALIFIED`,
`PREVIEW_LEDGER_RUNTIME_QUALIFIED` and `HOSTED_PREVIEW_UPLOADS_QUALIFIED` remain
**false in source**, with no environment override. Controlled tests explicitly
override them against fake clients. Activation needs a reviewed qualification
change, deliberate quarantine removal and scheduler resume. Existing M04/M05,
M07-M12, M14 and G1-G6 release gates remain independent.

## Primary API references

Reviewed 2026-10-20 for mechanics, not deployment or game-provider permission:
[GCS consistency](https://docs.cloud.google.com/storage/docs/consistency),
[generation preconditions](https://docs.cloud.google.com/storage/docs/request-preconditions),
[object insert](https://docs.cloud.google.com/storage/docs/json_api/v1/objects/insert),
[CORS API differences](https://docs.cloud.google.com/storage/docs/cross-origin),
[Batch create](https://docs.cloud.google.com/batch/docs/reference/rest/v1/projects.locations.jobs/create),
[Batch delete](https://docs.cloud.google.com/batch/docs/reference/rest/v1/projects.locations.jobs/delete),
[Batch VM labels](https://docs.cloud.google.com/batch/docs/organize-resources-using-labels),
[Batch secret references](https://docs.cloud.google.com/batch/docs/create-run-job-secret-manager),
[service identity and audiences](https://docs.cloud.google.com/run/docs/authenticating/service-to-service)
and [internal ingress](https://docs.cloud.google.com/run/docs/securing/ingress).
