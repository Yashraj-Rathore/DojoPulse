# M18 local pilot-management qualification

Date: 2026-10-02. Scope: local synthetic engineering. Real studies: NOT_RUN.

Implemented the coherent M18 preparation module: study creation/invitations,
explicit self-consent/pseudonyms, prospective splits/comparator allocation/session
logs, retained source registration, role-scoped media, independent blinded reviews,
third-party adjudication, annotation export, canonical evaluation links, frozen
G1–G6 evidence packs and independent decisions. Extended own export, retention,
withdrawal, source/account deletion, expiry maintenance and signed restore controls.
Architecture 2.9.0, ADR-017/D028; migrations 0013–0015 applied forward locally.

Actual checkpoint: **304 PostgreSQL/Python tests passed in 107.67s**, seven Docker
checks skipped locally because no qualified local Docker image was configured.
An earlier 301-test checkpoint passed in 83.86s. New pilot cases cover role/consent,
blinding/idempotency, adjudication, phase/time/hash/split/overlap constraints,
unknown evidence, sparse/null reports, erasure/expiry/retention, streaming stop,
revocation, cross-account review/withdrawal concurrency and perfect held-out
synthetic thresholds without scientific promotion. Follow-up **24 pilot tests
passed in 10.07s**, including canonical event/hash/evaluation linking, nonpositive
comparison results, CSRF and all three reverse guards. Final consent follow-up
passed **24 in 10.46s**; remote CI will execute the final complete collection.

**21 Edge journeys passed in 21.9s** at the invitation-fix checkpoint. Follow-up
source-chronology controls exposed an ambiguous browser label selector and two
JSX apostrophe lint errors; these were corrected. The final **21 Edge journeys
passed in 23.9s**, with lint/build/types passing and mobile screenshot reviewed.
The initial invitation fragment issue was corrected to preserve the token through
development effect replay while removing it from the URL. No test gate was weakened.

Native PostgreSQL 17 dump/restore, fresh-database migration forward/reverse/forward,
signed pilot withdrawal before reads, restored grant/label erasure and repeat replay
passed. Local restore now verifies no active study grants, labels or private report
payloads survive. The final three-guard migration/recovery rehearsal passed again.
Ruff check/format, mypy (23 sources), Django system/schema and diff checks passed.
Main publication and all six remote CI jobs remain pending.

Fetch found an unexpected force rewrite of the prior receipt: remote `2a20380`
reintroduced obfuscated eval code in Next config. Its sole tree difference from
verified local `5c1e78c` is that configuration. No payload was run locally.
Keep the verified clean tree while retaining remote ancestry; repository access
and possible prior execution remain an open release finding.

Published M18 implementation `135464f` and ancestry-preserving clean-tree merge
`2bbb645` to origin/main without force. Reconciliation has exactly the tested
implementation tree and clean Next config. Remote CI registration/monitoring is
pending; no hosted resources were provisioned.

## Final remote receipt

[CI 37041450168](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37041450168)
completed SUCCESS at **17:37:02 UTC**, first attempt, exact head
`2bbb6457757f9c27236e83ca439e82bf598a45bb`. All six jobs passed.
**306 PostgreSQL/Python tests passed in 44.70s**, seven skips exercised in the
separate **seven Docker isolation/max-profile tests in 139.35s**, including the
actual 600s/512MiB profile. **21 Chromium journeys passed in 18.5s**.
Three mocked Terraform plans, native PostgreSQL dump/restore/round-trip through
0015/pilot-grant-label erasure/signed controls/repeat replay, API/web Linux image
builds and unprivileged/quarantined/standalone startup passed. Static/system/schema,
frontend lint/build/types and both Python/npm audits passed. Downloaded JUnit
artifacts corroborate the logs. No CI retry or relaxed gate.

The repository main ref was verified as the qualified clean head after CI.
M18.07 local software is DONE; M18 remains PARTIAL for actual approved real study
intake, expert/reviewers/captures/comparator findings and scientific decisions.
G1–G6 remain NOT_RUN. Production, provider, commercial and repository-access review
gates remain open. The final receipt changes documentation only and uses `[skip ci]`.

Scientific evidence was not collected. No real reviewer, expert, participant,
capture, approved game fact, live provider, hosted resource, external message,
invoice or payment was created. Real intake is hardcoded off; all reports retain
NOT_RUN and no automatic canonical publication. G6 utility/allocation proposals
need independent protocol review. Hosted scheduling/playback/revocation, performance,
replicated control currentness and retained-copy erasure remain unqualified.
