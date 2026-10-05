# ADR-020: Governed dataset collections and revocable snapshots

Date: 2026-10-05. Architecture: 2.12.0. Status: accepted local engineering.
Requirements: M08.01-M08.07, M07.05, M09.04, M12.02, M14.04/.05,
M15.01/.06, M16.05, M18.07, M01.05/.06 and M19.02.

M18 already supplies consent, private source grants, prospective logs, blinded
independent review and adjudication. Its draft target and study-local splits cannot
qualify a reproducible multi-study dataset. Reuse that workflow instead of creating
a second consent or annotation system.

A collection seals one M07 governed knowledge release, its exact build/platform,
dependency hashes and bounded Jin semantics, plus a predeclared coverage checklist.
Only newly created linked studies can join: their immutable protocol and explicit
self-consent include these pins and the split-guard retention rule. Existing consent
is never extended retroactively. Real intake, knowledge publication and recognition
release remain disabled. Coverage floors are a software checklist, not a scientific
sample-size decision, and no model-training grant is exported.

Keyed collection-specific player, session and source partitions serialize under the
existing owner -> capacity -> domain lock order. They bind original split and source
assignment across linked studies, snapshots and withdrawals without retaining raw
IDs, session codes or source hashes. Minimal guards remain until collection closure;
snapshot labels and source grants do not. Key rotation and independence across
different collections require a separately reviewed migration/protocol. Repeatedly
testing previously observed held-out footage is not independently validated by a
new collection ID.

Freeze all inputs/predictions before manager-held-out label access. Reviews may finish
after freezing; every revision invalidates and erases prior snapshots. Sealing requires
retained unchanged exact-platform source evidence, full-source independent QC and
resolved reviews. Missing categories remain explicit, and missing/invalid/zero session
logs remain in the input manifest. Success, failure, excluded near misses, uncertain
windows and target-absent sources are distinct. Unobserved timestamps stay null;
reference-relative prediction error and reviewer frame/timestamp agreement do not
establish actual in-game timing accuracy.

Snapshots are immutable content-hashed receipts; invalidation erases private JSON while
preserving receipt hashes/sequence/reason. Reads and exports recheck current consent,
review roles, retention, chronology, source metadata/generation and measurement grants.
Withdrawal, source/account deletion, reviewed-definition withdrawal and quarantine
invalidate derived event contributions and evaluations. Retired valid definitions
remain usable for already frozen history, but cannot start new intake. Privacy closure
remains available when pinned knowledge is unavailable. Restore closes all restored
collection grants and erases labels before application reads. Migration 0018 refuses
reverse migration over dataset history or source pins.

Canonical import stays explicit and uses the existing owner/operator publisher. One
currently valid snapshot may grant its exact reviewed batch and measurement only for
that participant's owned source. This does not grant general use of another workspace's
knowledge or drills. Events pin snapshot/measurement hashes; Match's original build
and initial knowledge are unchanged. No source-specific code enters Match, event rules,
statistics or player-model summaries, and no bulk or automatic publication is added.

Local software and synthetic evidence can qualify this module. Permitted representative
real captures, qualified independent experts/adjudicator, external blindness, timing
ground truth, rights/retention review and hosted erasure remain independent acceptance
criteria for the real golden dataset and M09 recognition.
