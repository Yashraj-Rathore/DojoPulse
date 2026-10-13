# M06.13 preview write recovery qualification

Date: 2026-10-13. Controlled storage failure injection and synthetic native
PostgreSQL recovery only. No live cloud or new gameplay validation. M06.11 actual
hosting remains PARTIAL.

Initial focused run: 109 passes/one Windows symlink-creation skip in 75.16s across
preview recovery, private previews, resumable upload and hosted-delivery tests.
Coverage includes uncertain final PUT/probe, publication, stop/erase outages,
late session handles, orphan capacity, SQL rollback/cancellation, bounded retry,
signed store/mirror rollback, missing/tampered/torn/foreign-deployment ledger,
independent lock serialization, redacted maintenance and official metadata/
all-version deletion/empty-inventory contracts. Later deletion-order/capacity
fixes and their regression test require final full-suite and CI results below.

Native disposable PostgreSQL dump/restore and guarded forward/reverse/forward
passed on final implementation, including repeated controls before reads, pending
upload/private-preview erasure and independently preserved post-backup ledger
recovery. Its orphan PLANNED attempt was absent from restored SQL and safely
erased without any remote RPC. Production RPO/RTO were not measured.

Prior main 149fd4039f5ecec6571e5149e4d6b5785f309c46 separately passed all seven
checks in [run 38427144648](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/38427144648):
654 Python passes/12 Docker-platform skips (all 30 preview), 11 actual Docker,
17 Windows, 62 Chromium, three Terraform mocks, audits/static/build/container and
native restore. That is prior evidence, not qualification of these new changes.
The [earlier owner HEVC trial](private-recording-previews.md) remains separately
scoped; no new media processing, actual hosting or gameplay approval is claimed.

Final local qualification:157 passes/one Windows symlink skip in 97.44s over the
final preview/recovery/upload/hosted/security/operations source. All 25 ledger
cases (24 passes/one privilege skip) and all 30 private-preview cases ran. The
pre-final broad run passed673/16 platform-Docker skips/715.34s before the last
cancellation/publication/guard edits; it is not claimed as final full-source
qualification. Final Ruff280, Linux/Windows mypy42, schema/system checks and all
102 Markdown local-link targets pass. Native final-source rehearsal is checked
separately. Source `d932fc0ed843a2f2611ba7361067b3b11d9107d6` published directly to main and passed all seven
checks in [run38436918455](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/38436918455), completed
2026-10-13 17:27:27 UTC. Independent check-run metadata confirms every successful
check on the same SHA. Downloaded artifacts/logs show691 Python cases:679 passes,
12 separate sandbox/platform skips, zero failures/errors,710.188s XML. All25
ledger cases and30 private-preview cases pass with no skips. Actual Docker11/
no skips/91.466s, Windows17/no skips/1.467s, Chromium62/1.1m and three Terraform
mocks pass. Python/cloud/production npm audits, Ruff280/mypy42, schema/load,
production web build, unprivileged containers and native independent-ledger
post-backup erasure rehearsal pass. The live watcher was transiently throttled;
completion was independently established from the completed run, seven check
records, downloaded JUnit and completed logs. Ordinary final receipt retains
CI and requires actual latest-tip monitoring; no check is skipped. Production flags remain false. The bounded
file store does not prove replicated durability, protected capabilities, whole
store freshness after SQL restore, actual late-write behavior or managed isolation.

Final rollback-guard correction:0025 now requires an available verified ledger whenever any SQL mirror or qualification requirement exists, including all-erased mirrors. Added missing-ledger/erased-mirror regression; final78 affected passes/one Windows symlink skip/79.23s (26 ledger cases,30 preview), native guard/restore recheck and static/schema pass. d932fc0 all-seven above remains prior scoped evidence; superseded88f04fd receipt CI cancelled. Corrected ordinary latest-main checks must be verified at handoff; they cannot be inferred from that earlier run. Production flags remain false.
