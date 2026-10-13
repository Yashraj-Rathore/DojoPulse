# Independent preview write recovery

2026-10-13: ADR-030 / D045, architecture 2.23.0. M06.13 covers controlled
engineering. Actual hosted M06.11 remains PARTIAL.

A database snapshot cannot establish whether a later cloud upload stopped. Every
new GCS derivative attempt records three bounded artifact hashes, byte counts,
owner/asset/preview/run/fence and bucket before initialization. Its deterministic
intent UUID survives SQL rollback. Session capabilities are stored independently
before any media PUT, never in SQL, API responses, exports or operator status.

`preview_ledger.py` is a controlled file-store prototype: signed deployment-scoped
sequence snapshots, hash chain/completeness checkpoint, independent cross-process
file lock, fsynced temporary records, atomic replacement, regular-file/link checks
and bounded reads. There are at most 4,096 events of 16 KiB each. Exhaustion,
missing/torn/extra records, bad signatures or a foreign deployment fail closed.
There is no automatic rebootstrap, truncation, compaction or silent repair. An
operator must investigate and restore the independently retained verified store;
discarding uncertainty is not recovery.

Attempt states are OPEN, PUBLISHED, CLEANUP and ERASED. Artifact states are
PLANNED, INITIALIZING, SESSION, FINALIZED and STOPPED. Initialization intent
precedes RPC; a missing initialization receipt remains INITIALIZING indefinitely.
A client timeout, run deadline or guessed expiry is insufficient stop evidence.
A late session handle may be attached during CLEANUP for cancellation. Revocation
is durable before SQL changes and irreversible. Every PUT/probe checks both the
live job lease/fence and OPEN state. Late completion cannot revive stopped work.

Publication uses the official GCS resumable API with `ifGenerationMatch=0`, fixed
origin/bucket/owned prefixes, bounded 8 MiB chunks, observed offsets and bounded
completion metadata verifying bucket/name/size/MD5/generation. Uncertain PUTs
probe the same persisted session; initialization is never blindly retried. Each
artifact permits three retryable failures with bounded backoff and 256 total
operations. READY still requires current owned SQL authority and immutable source
and manifest. No Match, GameplayEvent or scientific approval is inferred.

Cleanup cancels known sessions before deleting attempt objects. PLANNED artifacts
need no cloud call; INITIALIZING without a handle blocks cleanup. Every object
generation is deleted under the exact attempt prefix, then a fresh all-version
inventory must be empty before ERASED releases its hold. Outages retain quota and
can be retried. Asset deletion stops derivative capabilities before sweeping its
cloud prefix. Actual execution stop and local staging erasure remain required
before child/parent reservations can be refunded.

Migration 0025 adds `PreviewWriteHold`, a quota projection without foreign keys or
session secrets. Admission verifies the independent store and projects orphan
post-backup attempts, even with absent owners/assets. One matching child
reservation covers its current attempt; stale/orphan attempts add their whole
hold. New fences recheck capacity. Newer SQL sequences detect relative store
rollback; omissions fail closed. Reversal requires both stores' holds erased.

Restore verifies the ledger before trusting restored SQL, projects post-backup
holds, revokes attempts, stops known execution and reconciles sessions/objects.
Uncertainty retains quarantine. The native PostgreSQL rehearsal retains the
ledger outside SQL/media backups and recovers a PLANNED post-backup attempt absent
from the restored database. Remote failure cases use controlled adapters only.

`python manage.py preview_write_maintenance` reports counts and reserved bytes.
`--cleanup` retries revoked attempts; `--initialize-local-ledger` creates an empty
DEBUG-only local store explicitly. Neither enables cloud writes. Never put
capability URIs on a CLI, in reports or public logs. Restore/migration need the
independently retained store/key, not an empty replacement.

## Unmet hosted acceptance

`GCS_PREVIEW_WRITES_QUALIFIED`, `CLOUD_PREVIEW_RUNTIME_QUALIFIED` and
`PREVIEW_LEDGER_RUNTIME_QUALIFIED` remain false in production code. Activation
requires an authorized region/budget, equivalent worker isolation, restricted
IAM/CORS, an encrypted private independently replicated store outside SQL/media
restore boundaries, separate signing-key custody, multi-host CAS/freshness anchor,
protected capability storage and measured retention, outage, concurrent capacity,
late-write/all-version and restore tests. A local lock does not prove multi-host
correctness. HMACs do not detect rollback of an entire formerly valid store when
its SQL mirror also rolls back. POSIX permissions/fsync do not establish Windows
ACL or hosted durability. Rotation must be qualified before this bounded store
fills. Legacy ambiguous media POSTs without session receipts remain blocked.

This changes no Tekken provider classification, usage approval, automatic replay
acquisition or scientific gate. USER_UPLOAD remains the working fallback; no
private/undocumented game endpoint is accessed.

Primary references reviewed 2026-10-13:
[GCS objects.insert](https://docs.cloud.google.com/storage/docs/json_api/v1/objects/insert)
and [resumable upload/status/cancellation](https://docs.cloud.google.com/storage/docs/performing-resumable-uploads).
JSON session cancellation returns 499. Observed receipts govern retry, rather
than sent bytes or local time. These mechanics do not constitute hosting or
game-data usage approval.
