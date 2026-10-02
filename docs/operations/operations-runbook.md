# Operations and support runbook

2026-10-02; M17.01–M17.06. Executable local procedures; named production primary,
deputy, notification destination, acknowledgement/escalation times and SLO approval
remain required before hosting. No external notification is configured or sent.

## Inspect and respond

Sign in as an active staff account and open `/operations`, or run:

```powershell
python manage.py operations_snapshot --days 1 --fail-on-alert
python manage.py operations_snapshot --days 30 --prune
```

The first command emits bounded redacted JSON and exits nonzero when configured
alerts are present. Do not paste private database reports or invoices into public
tickets. Snapshot absence is not evidence of health: an external scheduler must
also alert on command failure/missing heartbeat before production use. Schedule
retention daily only after the deployment owner has accepted the policy.

| Signal | Immediate response | Verification before resuming |
|---|---|---|
| Stale slot / stop pending | Cancel affected work with owner authorization; inspect exact parser/execution through the M16 runtime adapter | Authoritative stop observed, retained slot released; no manual counter reset |
| Uncertain launch | Keep capacity reserved; inspect authoritative operation/execution state | Reconciler proves termination or recovers a known execution; never blindly relaunch |
| Dispatch attention | Check fixed cloud error code, queue IAM/configuration and allowed runtime | Controlled retry with same intent/generation, no duplicate execution; exhausted intents require reviewed recovery |
| Queue delay / resource budget | Pause optional admission and investigate workload, failures, unknown settlements and retained deletion bytes | Backlog drains within limits; reconcile reservations rather than deleting them |
| Purge pending | Run `purge_expired` after storage recovers; preserve tombstones | Private source gone and purge receipt recorded; dependent evidence stays withdrawn |
| Source attention | Keep live provider disabled; inspect permitted adapter error codes and version/expiry | Contract and usage rights reconfirmed with approved fixtures; no undocumented endpoint substitution |
| Objective breach / truncated window | Inspect admitted workload, failure slice and measurement completeness | Representative measurement and reporting capacity resolved; do not relax thresholds to make a report green |

To pause optional processing, set `OPTIONAL_PROCESSING_PAUSED=1` in both API and
worker environments and restart those project processes. The flag stops admission
and new claims; it does not terminate existing jobs. Use fenced cancellation and
authoritative stop for existing jobs. Keep account/deletion/export available.
Resume with `0` after verification. Live provider transports remain gated and the
local synthetic source can be disabled with `LOCAL_MATCH_IMPORTS=0`.

## Support and patches

Feedback stays in the existing local owner queue; no mail, Slack or webhook is
sent. Record REVIEW/SUPPORT seconds in the staff dashboard with evidence scope.
Use fixed problem categories and restricted incident records. Never infer human
review time from API handler latency. Human response time/roster is NOT qualified.

Follow the [security runbook](security-runbook.md) for containment, credential and
vulnerability response. An authorization, privacy, parser-escape or deletion
regression blocks external release. Patch, add a relevant regression test, rebuild
immutable images, run all applicable CI jobs and require independent hosted review.
The existing source-integrity investigation remains unresolved; do not reintroduce
the removed obfuscated Next configuration.

## Recovery and qualification

Follow the [M16 delivery contract](../architecture/hosted-delivery.md) and signed
quarantine restore command. Never drop an open RunBudget or physically retained
ExecutionSlot to clear an alert. Migrations 0010–0012 refuse budget-table rollback
while holds or current charged-day amounts exist. Only an empty/drained scratch
database or expired closed-charge state can rehearse rollback. Migration 0012 also
refuses a rollback that would replace unknown historical attempt dates with invented
timestamps; preserve the nullable field until a reviewed migration can safely remove it.

The synthetic load test exercises 2,250 history rows, nine owners, queue/physical
saturation, indexed history pages and eight bounded mocked dispatch failures. The
Docker CI separately exercises the supported 600s/512MiB media boundary. These
are separate engineering tests, not a representative simultaneous production
workload or permitted live-provider outage test. Qualify real captures, hosted
max-file uploads, ingress/egress, database saturation, scheduled alerts and the
named operator's response before approving the proposed objectives.
