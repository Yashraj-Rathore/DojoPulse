# M06.11 hosted-preview preparation qualification

Date: 2026-10-20. Requirements: M06.02/.05/.06/.07/.11/.13, M13.03/.06,
M15.01/.06, M16.02-.05, M17.03 and M19.02. Architecture 2.24.0 / ADR-031 / D046.

Implemented the coherent cloud preparation module: independent create-only signed
GCS journals, Batch execution intent/stop recovery, existing offline decoder
boundary, private source/derivative integration, bounded scheduled maintenance,
server-only website identity bridge and optional quarantined Terraform.
See the [contract and activation checklist](../architecture/hosted-recording-previews.md).

All HTTP calls in `tests/test_hosted_previews.py` use controlled fake Google
clients with the actual API/coordinator/adapter code and local PostgreSQL. Worker
bootstrap uses controlled local image inspection; conversion output is a
synthetic bundle. These are not live Google, real multi-host replication/IAM,
actual Batch VM or new gameplay footage tests.

Covered: concurrent append arbitration, genesis/gate failure, missing sequence,
changed-generation tamper despite cache, lost-append read receipt, independent
control after SQL rollback; API upload/resume/exact verification, deterministic
dispatch/duplicate/ambiguous creation, pinned worker entry, private owned ranges
and no canonical rows; irreversible cancellation/late receipt, missing SQL slot,
orphan quota, missing receipt, partial VM inventory, foreign fingerprint,
backend-disable holds and repeated full restore. Maintenance overlap uses an
actual separate PostgreSQL advisory-lock session.

Initial broad affected run: **132 passed, one Windows symlink privilege skip**
from 133 cases / 123.10s. Expanded 21 hosted cases passed / 26.14s after correcting
the controlled fixture to select Docker for worker entry. Neither supersedes
final-source regression/CI below. The initial fixture failure did not weaken the
production gate.

Final boundary review added run tombstones before any execution intent and
reconciliation of independently stopped/restored SQL slots. A post-create archive
outage is explicitly ambiguous and cannot refund a running worker. **All 28 final
hosted cases passed / 31.89s**. The earlier broad run was deliberately interrupted
for these fixes and is not reported as a full pass.

Final local checks already passed: **62 Edge browser regressions / 1.1m**, **six
server bridge tests**, production build/lint/typecheck, Linux and Windows mypy
(42 files each), Ruff/format, schema/migration dry run, **five Terraform mock plans**
and native disposable PostgreSQL dump/restore/guard/repeated control/pending
upload/private preview/post-backup independent-ledger recovery. **409 local links**
and **179 unique valid requirement rows** checked; all six production flags
confirmed false from settings syntax. The final full PostgreSQL/media suite on corrected source6e920a1 completed:
**720 cases / 704 passed / 16 skipped / zero failures or errors / 875.25s**.
All28 hosted cases and30 private-preview cases pass without skips;26 independent
write-recovery cases have25 passes and one Windows symlink privilege skip.
The16 full-suite skips are11 opt-in Docker/profile cases and five Windows
symlink-privilege cases. Actual Docker isolation/new coordinator container build
and new remote Chromium/CI remain **NOT_RUN** on this source, pending publication
approval; prior baseline CI is only dated evidence, not a substitute.

No cloud resources, credentials, project/region/budget approval, permitted live
Tekken access or game automation were used. Production flags remain false;
scheduler paused; API/maintenance quarantine defaults retained. Actual owner
HEVC playback evidence from October 13 remains separately scoped, with no new
real-game, hosted, automatic-acquisition or scientific approval. M06.11 remains
PARTIAL until actual hosted acceptance; M06.13's earlier controlled engineering
qualification does not qualify replication or production freshness.

Publication boundary:clean implementation committed locally as6e920a1. Remote
main was forcibly rewritten to be09338; its sole baseline tree difference is an
obfuscated Next config payload, inspected as text only. Automatic approval review
rejected retaining this suspicious ancestry in a clean-tree merge without
explicit user approval. No merge/push/new remote CI performed. Final local full
results and a reviewable receipt precede that request; earlier green CI is not
substituted for this source. Repository access/history review remains open.

Final verification on the frozen implementation:native disposable guarded restore
was repeated after the final code corrections and passed all reported controls;
production RPO/RTO remains NOT_MEASURED. Fresh pinned Python/core/cloud audits
found no known vulnerabilities; production npm audit found zero. All six hard
production gates remain false; Next config is the reviewed clean source.
No merge/push has occurred. Local documentation receipt follows on main with
ordinary CI semantics; its future exact-tip checks must be monitored after
specific history-reconciliation approval. M06.11 remains PARTIAL for publication CI/container checks and actual hosting;
the implemented preparation has completed the stated local controlled checks.

2026-10-20 approval update:user explicitly approved clean-tree history merge,
main push and monitoring. Remote be09338 was rechecked; approved merge preserves
reviewed4646706 files exactly before documentation updates, discarding all
injected executable changes without running them. Publication/current-tip CI are
now authorized and pending. Prior rejection is historical, not a current consent
block. Actual cloud activation remains unauthorized/unqualified; flags false.

## Published source qualification

User-approved clean-tree merge **e33bfa4d6e813dabca877930060fcc9f50cb5225**
published on main only. [All seven CI checks](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/39453977429) passed, completed
**2026-10-20 16:17:10 UTC**. Independent check-runs bind the same SHA; watcher
exit0. Completed metadata/logs and downloaded JUnit are stored under ignored
`reports/hosted-preview-ci-source`.

| Actual source evidence | Result |
|---|---|
| PostgreSQL/Python |720 cases,708 passes,12 separate platform-Docker skips,zero errors/failures,722.584s |
| Hosted module / independent write recovery / private previews |28 /26 /30 cases,all pass,no skips in these modules |
| Actual offline Docker isolation/maximum profile |11 cases,all pass,no skips,151.351s |
| Actual Windows helper |17 cases,all pass,no skips,1.398s |
| Chromium / server bridge |62 browser passes/51.5s;six native bridge passes |
| Infrastructure |Five Terraform mock plans plus fmt/validation pass;no apply |
| Images/startup |API/web/coordinator builds pass;coordinator disabled-before-qualification guard,unprivileged API quarantine and standalone web pass |
| Static/schema/dependencies |Ruff289,mypy42,schema/migration/load/build and pinned core/cloud/production npm audits pass |
| Native recovery |Guarded disposable dump/restore/migration/repeated controls,pending upload/private preview/post-backup ledger recovery pass;production RPO/RTO NOT_MEASURED |

This supersedes the earlier NOT_RUN statements only for these exact-source remote
software/container checks. No actual Batch VM, Google IAM/CMEK/freshness/CORS/
late-write/full hosted restore/load/cost was qualified. All live flags remain
false; M06.11 actual hosted acceptance is PARTIAL. Repository access/history
review remains open. Final documentation receipt uses ordinary CI; verify its
actual latest-main checks before handoff rather than reuse this source result.
