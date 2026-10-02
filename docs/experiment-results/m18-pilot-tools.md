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

Scientific evidence was not collected. No real reviewer, expert, participant,
capture, approved game fact, live provider, hosted resource, external message,
invoice or payment was created. Real intake is hardcoded off; all reports retain
NOT_RUN and no automatic canonical publication. G6 utility/allocation proposals
need independent protocol review. Hosted scheduling/playback/revocation, performance,
replicated control currentness and retained-copy erasure remain unqualified.
