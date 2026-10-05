# Reviewed practice workflow

Architecture 2.14.0, 2026-10-05. Local engineering contract; real drill reproducibility,
expert/player usability, G4 and effectiveness remain NOT_RUN.

M07 drill versions may contain `practice_workflow/1`: exact supported context, response,
success criteria, 1-12 bounded native setup/alternative/capture steps and immutable
`practice-progression/1` rules. Both independent reviewers approve the complete source-pinned
payload. Existing versions are unchanged; adding instructions/rules requires a new version.
No generic Tekken response or setup is invented for an older drill.

Reviewed rules require 40-200 known trials, 2-10 distinct sessions, at least 90% outcome
and eligibility coverage, at least 80% raw independent-review agreement, and a descriptive
lower success interval bound between 50% and 100%. These are proposed research thresholds,
not validated practice standards. The frozen plan can require greater exposure. Real
practice always remains `REAL_PRACTICE_VALIDATION_PENDING` when otherwise sufficient.

An assignment pins the immutable drill hash and optionally a complete current M10 diagnosis:
card identity, evidence/policy hashes, exact scope, summary and bounded membership (2000
windows maximum). The server recomputes the supplied filters/card before accepting the
proof; favorable filters and unqualified/stale cards fail. Diagnosis-bound assignment creation
requires an owner-scoped request UUID. A retry returns the same historical assignment,
never silently changes its diagnosis. Legacy setup-only assignments remain separate from
evidenced prescriptions and cannot establish a weakness merely by freezing a baseline.

Freeze a complete current ranked baseline before linking practice. Link every row of the
chosen current reviewed capture, including unknown and excluded windows. Require exact
situation/metric/context/build/knowledge version and hash/detector/platform/dataset scope,
current source rights/retention/attribution, independent review and verified chronology.
The recording must start after the baseline cutoff and its validated full duration must end
before follow-up starts. Real practice must also occur after plan creation. Source-end time
becomes `TrainingSession.completed_at`; upload/assignment time cannot substitute for exposure.

Owner/capacity locks serialize reads and writes with shared source withdrawal and account
deletion. Source event and played-opportunity uniqueness prevents counting reanalysis twice;
optional request UUIDs make practice-link retries idempotent. Limit an assignment to 2000
linked trials. Sessions and their source/version pins are immutable. Reanalysis, expiry,
deletion or rights withdrawal removes old links from current guidance/exposure; original
links and frozen comparisons remain historical. No source replacement is automatic. An
unavailable linked trial blocks progression and positive reevaluation rather than silently
selecting the remaining favorable outcomes. Overview exposes historical versus available
links separately. No persistent progression cache exists.

Progression checks a sufficient available frozen baseline, current exact-scope practice,
sample/session counts, uncertainty, coverage and review agreement. States request more
practice, evidence/baseline review, the same reviewed setup, or the declared later follow-up.
They never automatically increase difficulty, rewrite dates/metrics, authorize a real drill
or claim causality. Evidence playback links show a bounded sample; counts use all valid rows.

`PracticeLog` stores owned immutable COMPLETED/INTERRUPTED/SKIPPED self-reports, aware ordered
times (maximum eight hours; five-minute clock tolerance), 0-2000 reported attempts and a
categorical obstacle. Completed requires attempts; skipped requires zero. No free-text
private notes. These logs add **zero** DrillAttempts and no M12 exposure, even with large counts.
The owner/request UUID and payload/drill/workflow/optional-plan hashes pin retries. Up to 1000
receipts per assignment; the guide shows the latest 50, account export includes all bounded
own records. Delete tombstones personal fields/pins but retains the minimal UUID receipt,
so a delayed retry cannot resurrect the report. Cancellation stops new assignment work and
guidance; historical frozen results remain separate.

Processing withdrawal stops new work and guidance; retained self-reports remain exportable
and deletable under the existing account policy. Account deletion erases all reports and
assignment diagnosis JSON. Every quarantined restore conservatively erases reports and
diagnoses and cancels restored assignments before reads, preventing backup resurrection
without trusting stale authorization. Migration 0019 backfills existing drill hashes and
refuses rollback once M11 private/version-pinned history exists; use a reviewed forward fix.

Private API: GET `assignments/<id>/training`, POST `assignments/<id>/reports`, DELETE
`practice-reports/<id>`, POST `assignments/<id>/cancel`, plus the existing assignment/practice
endpoints with request IDs/proof. Session authentication, CSRF, owner checks, consent and
existing request/rate bounds apply. The guided UI uses only reviewed native steps, separates
reports from current measured trials, clears failed reads, polls while visible and preserves
retry IDs after a failed mutation. No provider transport or undocumented endpoint is added.
