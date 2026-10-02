# Local pilot-management tools

Version: local-pilot/1. Architecture 2.9.0, ADR-017/D028. Requirements:
M18.01–M18.07, M08.01/.03/.04/.06, M14.04/.05, M16.05 and M19.02.

`/pilots` and the session/CSRF-protected `/api/pilots` API rehearse a complete
study workflow with synthetic sources. `PILOT_REAL_DATA_APPROVED=False` is a
code-level gate; synthetic access also requires DEBUG. No environment release
flag, expert button or synthetic metric approves real intake, knowledge,
recognition, hosting or training. Scientific gates remain NOT_RUN. A real study
needs reviewed rights, adult intake, retention, sampling, comparator allocation
and explicit release decisions. No real participant data has been collected.

## Consent and source intake

An active current staff member manages only owned studies and creates 24-hour
signed role invitations tied to an immutable protocol digest. Invitations use a
scrubbed URL fragment or pasted token, never a request URL. Recipients explicitly
accept adult study consent and participants attest recording-sharing rights.
One account has one role: participant, reviewer, adjudicator or expert. The
manager cannot be an independent member. Study tables use random pseudonyms
without contact identity. Self-attestation is not qualified age/rights verification.
Account model-training consent is separate and cannot authorize study-label reuse.

Assign player-disjoint development/validation/held-out splits and comparator order
before any session. Allocation is a reviewed human choice, not an automated
randomized trial. Freeze dates at creation: seven baseline days, two practice
days, 28 follow-up days and seven audit days, within the proposed 60-day maximum.
Sessions must follow enrollment and fall inside their phase; no future observed
evidence. Native/usual observations use the follow-up window. Preserve CAPTURED,
MISSING, ZERO_OPPORTUNITIES and INVALID attempts and null measured durations.

Register an owned, retained source after bounded media validation and reviewed
chronology. Original session code/time, exact build, source hash and dataset scope
must match. The UI can copy original chronology without losing precision. A hash
cannot cross study players/sessions/splits. Registration explicitly grants review
and extends retention through study consent. Withdrawal restores original private
retention, preserving other live grants, without deleting workspace footage.

## Independent review and canonical boundary

QC covers the full source. Non-overlapping target/practice-trial windows are
bounded by validated duration and must use the appropriate phase. Two reviewers
and a third adjudicator need active unexpired role consent. Optional offline
predictions pin detector version/source time before reviews. Reviewers cannot
see predictions or colleagues' labels before dual submission; managers cannot
see held-out labels before source inputs are frozen.

Reviews are immutable, idempotent and record measured seconds. Required evidence
conditions are explicit true/false/unknown; existing deterministic rules derive
eligibility/outcome. Uncertain/unobservable evidence must abstain. Any structured
label difference requires the assigned third reviewer after two disagreements.
Local streaming rechecks current role/account, consent, retention, hash and
chronology for each chunk and stops when evidence/grant disappears.

Freezing prevents new memberships, splits, allocations, sessions, sources, tasks
or predictions. Assigned reviews can finish, invalidating previous reports.
Frozen `annotation/1` exports require every exported task to be resolved and pass
the existing independent-review validator. An authorized operator must separately
publish through the canonical evidence boundary and its knowledge/version/consent
checks. No GameplayEvents or game definitions are approved automatically.
Match/GameplayEvent/player-model processing remains provider-independent.

## G1–G6 reports and decisions

Revisioned evidence packs include protocol/dataset/source hashes, exact builds,
participant splits, independent-review time, disagreement states, denominators
and missing coverage. The manifest hashes sessions, assignments, predictions and
review digests. Stale reports are withheld from export and regenerated with a new
revision. Missing, unknown and adverse observations cannot become positive data.

| Gate | Local calculation / sample guard |
|---|---|
| G1 | 20 captures, complete QC, ≥90% resolvable target windows; pending windows remain in denominator; >20% unobservable proposes narrowing |
| G2 | Held-out targets/negatives, one detector version, ≥300 accepted predictions, no unfinished labels; existing one-to-one harness reports precision/recall/F1, abstention, timing and exact one-sided bounds for success/failure |
| G3 | First baseline attempt per player including missing/invalid; ≥15 participants, complete unaided/setup observations, ≥80% valid, median setup ≤600s |
| G4 | ≥10 players × ≥40 practice trials, complete truth, ≥90% prediction coverage, ≥95% prediction/truth agreement; false accepted predictions reduce agreement; <80% coverage proposes stop |
| G5 | ≥20 histories, ended fixed follow-up, ≥60% reach 40 known opportunities/five original sessions per period; preserve missing/zero/invalid play and duration gaps; incomplete review/duration withholds frequency |
| G6 | Latest valid source-linked canonical evaluations use exact study target/windows/scope; ≥60% comparable including nonpositive results; complete native/usual/structured ratings, preserved allocation order and two groups of five |

G6 additionally proposes ≥60% reported added utility: useful structured insight
beats a non-useful comparator or takes less time than each useful comparator.
This conservative software proposal is **not an approved scientific threshold**
or causal inference. Real protocol review must approve design, balance, adherence,
bias and interpretation before intake. Non-useful ratings may retain null insight
time; useful ratings require measured time. No payment study is conducted here.

Independent consenting experts record immutable WAIT/CONTINUE/NARROW/STOP with a
fixed reason and offline reference code. CONTINUE requires current sufficient
candidate evidence and never changes scientific/release gates. A regression
checks that perfect synthetic G2 metrics still leave scientific_gate=NOT_RUN,
release_approval=false and GameplayEvents unpublished.

## Erasure and recovery

Writes follow owner lock → global admission mutex, serializing reviews against
cross-account withdrawal/deletion. Participant withdrawal erases study sessions,
captures/tasks/labels and dependent reports. Reviewer/expert withdrawal erases
their labels/decisions and invalidates packs. Account deletion and processing
withdrawal extend these controls. Study closure erases all member evidence.
Own account exports contain only own memberships, sessions, captures and reviews.

PILOT_WITHDRAW/PILOT_CLOSE join the independently signed restore journal.
Quarantine revokes every restored study grant and erases labels before reads,
then replays controls and normal asset purge. Native PostgreSQL recovery exercises
withdrawal and repeat replay. Migration 0013 refuses reversal over study history;
round trips use new empty disposable databases. Forward migrations 0013–0015 add
the workflow, original-retention pin and prospective allocation without reset.
`python manage.py pilot_maintenance` erases expired grants/evidence.

Caps: 20 studies/operator, 100 memberships, 4,000 sessions and 10,000 tasks/study;
fixed serializers and existing request throttles apply. Local per-chunk database
authorization is not a hosted-throughput claim. Hosted scheduling/playback,
revocation, retained-copy erasure and 10,000-task performance remain unqualified.
Honest logs, representative captures, expertise, blindness outside the app and
complete real-world play remain protocol/real-study duties.
