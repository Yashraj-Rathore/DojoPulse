# Security incident and vulnerability runbook

2026-09-29; M15.04–M15.07. Local engineering procedure, pending production owner acceptance.

| Responsibility | Current assignment / acceptance |
|---|---|
| Technical containment and remediation | Repository technical maintainer; named operator and deputy must be assigned before hosting |
| Privacy/provider rights and affected-player decisions | Product owner; named privacy reviewer and jurisdiction-specific process still required |
| Independent review and release decision | Reviewer separate from the implementer; appointment/approval outstanding |

Do not record credentials, raw player identifiers or private media in incident tickets.
Use a restricted incident record with UTC times, affected code/image versions, fixed error
codes, scope, consent implications, decisions, remediation and verification receipts.

## Containment and recovery

1. Keep ingress on loopback. Disable `LOCAL_OPERATOR_UPLOADS`, `LOCAL_MATCH_IMPORTS` and `LOCAL_ACCOUNT_SIGNUP`
   in the API environment and restart that API. Stop this project's worker with Ctrl+C;
   cancellation/deletion through the authenticated API remains available. Do not stop other
   Docker containers or the system PostgreSQL service.
2. Inspect only project parser containers with
   `docker ps --filter label=dojopulse.role=parser`. If the coordinator is unavailable,
   stop/remove an explicitly verified project container by its exact ID. Never use a
   blanket Docker prune. The local lifetime handler is a fallback, not a compromised-code
   guarantee; confirm no remaining parser before restarting workers.
3. For an affected source, cancel its queued/processing run or delete its asset through
   its owner's API. This increments the fence; deleting evidence also invalidates dependent
   conclusions. Do not manually reset fences or publish a partial decoder report.
4. If storage deletion failed, leave the tombstone intact and run
   `python manage.py purge_expired`; retry after storage recovery. Deleted bytes continue
   to count against admission until purge completion. Never restore an old database/media
   snapshot into a serving environment without replaying deletion/suppression records.
5. Run `python manage.py security_maintenance` to remove expired request budgets and
   upload reservations, expired account challenges/sessions and consumed/expired/orphan local
   mailbox envelopes. This does not terminate a blocked web request or remove arbitrary
   temp files. Shut down the relevant server first and inspect its specific temp artifacts
   before any manual cleanup.
6. For suspected secret exposure, revoke/rotate affected credentials through their actual
   owner/provider, invalidate sessions and investigate access. Do not copy secrets into
   logs. Production rotation and session-revocation rehearsals remain release gates.
7. Rebuild a patched image, record its immutable ID, run the regression/sandbox/advisory
   checks, and review impact before resuming trusted local ingestion. Expired analysis leases
   are fenced and stopped first; only authoritative termination permits a new attempt,
   at most three attempts under the run's snapshotted policy. Exhausted jobs fail visibly;
   create a deliberate reprocess request only after fixing the cause.

## Vulnerability handling

An exploit affecting cross-account access, secrets, deletion integrity or parser escape
blocks external release immediately. Contain exposure before gathering more evidence.
Record reproducible synthetic steps privately, patch, add a regression test, and require
independent verification for an external release. Other findings receive severity,
applicability, owner and a dated remediation decision; no silent scanner suppressions.

The owner requires only `main`, so automatic dependency-update PRs are disabled.
Review dependencies weekly and apply needed patches directly on `main`, running
both lockfile checks, the API regression suite and parser image qualification.
Keep CI audits active; disabling version PRs does not replace dependency maintenance.
Production additionally needs an OS/container scanner and
managed alert delivery. Current CI definitions do not prove that a deployed system is safe.

## Local rehearsal and untested operations

Automated rehearsal covers parser memory/scratch/PID limits, its lifetime handler,
cancellation/removal, durable upload/worker capacity races, account deletion revoking an
upload, stale completion rejection, source-hash integrity, request throttling, and existing
partial-purge/deletion retry and synthetic-provider failure tests. See the dated evidence
file for actual results. Human incident ownership, notification, production restore,
secret rotation and live-provider failure injection have **not** been rehearsed.


## M06 upload cleanup and dependency follow-up (2026-10-03)

Run `process_uploads` regularly and `purge_expired` at least hourly; normal polling
`process_runs` also performs verification/cleanup. An incomplete upload remains
unreadable and creates no canonical analysis until its actual bytes verify. Stop
admission while investigating repeated PURGING/initialization failures; retained
bytes/capacity are deliberate. Never print session URLs or retry an ambiguous GCS
session initialization. Inspect nonsecret state/deadline/error codes instead.

A missing capability URI with a future upstream deadline cannot establish erasure.
Keep tombstones/quota and restore quarantine, retry prefix cleanup after the deadline,
and verify actual generations. Migration 0016 reversal requires completed physical
erasure of every upload session. Follow the existing independent-controls restore
procedure, including storage outside the database snapshot.

Both Python locks and production npm dependencies were audited on 2026-10-03.
The full npm development audit separately reports the unpatched
[braces GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)
through the trusted ESLint/Next lint glob chain (five high findings). No application
user input enters those globs. A patched braces version was not available at review;
track upstream remediation, keep lint/config inputs trusted, and review/test its
patch on main. Do not suppress the finding or downgrade Next/ESLint with force-fix.
Production audit success does not close this development dependency finding.
