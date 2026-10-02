# Operations, budgets and measured economics

2026-10-02; Architecture 2.8.0; M17.01–M17.07. Local engineering contract,
not approved production service objectives, real player evidence or commercial validation.

## Resource admission and settlement

Owner lock precedes the global capacity mutex. Producer transactions create an
AnalysisRun, one RunBudget and one dispatch intent together. Request retries reuse
the same run/reservation; a conflicting asset/pipeline rejects the request.
Legacy queued rows acquire a reservation before execution. Existing storage,
upload, request, daily-job, pending-job and physical-capacity caps remain enforced.
Upload admission previews the time budget before reading a body, then producer
admission rechecks atomically; preview is not a second reservation.

Each analysis reserves 600 media seconds and 3 × 420 processing seconds. These
are conservative supported-profile upper bounds, not predicted cost. Defaults:

| Resource | Owner | Global |
|---|---:|---:|
| Media seconds per UTC day | 7,200 | 86,400 |
| Processing seconds per UTC day | 7,200 | 86,400 |
| Pending analysis jobs | 4 | 32 |
| Physically active executions | 1 | 2 |
| Stored source bytes, including pending purge | 2 GiB | 16 GiB |

Initial analysis plus two deliberate reanalyses per asset per UTC day is the local
limit; cancellation still counts as an admission. Transport retries do not create
new analyses. Runtime retry/deadline policy is snapshotted in each budget. Reaching
the attempt limit fails visibly and settles after known stops. Optional processing
pause rejects uploads/new runs and stops new claims; existing work must be cancelled
and authoritatively stopped through M16's controls.

Open reservations survive midnight. Terminal status, lease expiry, deletion or
an ambiguous launch alone cannot refund a hold. After physical stop, settlement
charges rounded-up measured attempt wall time; missing attempts charge their full
snapshotted deadline. Media duration is the maximum measured duration, otherwise
600 seconds when an attempt exists. Never-started cancelled work charges zero.
Settlement charges the UTC day of settlement, once. Unknown measurements remain
unknown even when a conservative quota charge is available. Overshoot is charged
in full and blocks further admission; it is not silently clipped to the reserve.
This is application processing control, not a hard guarantee of total cloud spend.

## Measurements and bounded reporting

One AttemptMetric belongs to one fenced ExecutionSlot. The worker records queue
wait (initial creation or prior stop through claim), coordinator wall time/CPU and
sampled coordinator peak RSS; the parser supplies decoder CPU/peak RSS, derived
bytes and media duration through its existing validated allowlist. Decoder and
coordinator values describe distinct processes. Hard process crashes may leave
null fields. Pre-M17 slot claim dates remain null rather than receiving invented
migration-time measurements; historical coverage gaps are counted separately.
Failures, retries, missing measurements and unsettled holds remain
visible. Reviewed annotations never fabricate processing telemetry.

HTTP measurements aggregate into minute buckets with four fixed route classes;
no URL, query string, cookie, user, external ID, payload or private path is stored.
Health probes and operations traffic are excluded from the availability estimate.
Client errors, including 429, count as an available response and are separately
counted; 5xx responses do not. This is observed response availability, not external
uptime, and cannot observe a completely unavailable process. Framework request,
security and server logs replace variable messages/tracebacks with fixed codes.
Worker terminal output similarly omits run identifiers. External ingress and cloud
logging require their own deployment-specific redaction/retention qualification.

Active staff can use `/operations` and `/api/operations?days=1..30`. APIs enforce
authentication, active owner, staff permission, CSRF on writes and private/no-store
responses. Other owners can read only their own `/api/usage`. Dashboard aggregates
omit identities, run IDs, raw results and invoice references. Percentiles use nearest
rank and at most 20,000 attempts; truncation raises an alert and cannot pass an
objective. Cohorts are whole UTC days; current queue/holds are reported separately.
Technical completion counts COMPLETED/PARTIAL/REVIEW_REQUIRED against terminal
noncancelled runs, not verified gameplay success or pilot benefit.

| Proposed objective | Local proposal | Required evidence |
|---|---:|---|
| Claim queue p95 | ≤120s | Declared admitted workload and representative capture/owner mix |
| Processing p95 | ≤390s | All attempts including failure; supported max files and representative content |
| Technical completion | ≥95% | Noncancelled terminal cohort; valid and rejected input slices separately |
| Observed API availability | ≥99% | External uptime/probes and hosted ingress failure evidence in addition to response buckets |

Fewer than 20 samples produces INSUFFICIENT_DATA. WITHIN_PROPOSAL never means
release approval. Targets need an accountable owner, representative measurements,
window/error-budget decisions and an explicit beta approval before becoming SLOs.

## Costs and evidence

Staff record bounded review/support seconds as SYNTHETIC or OBSERVED, with an
idempotent request UUID and no free text. These logs are operator-reported time;
they are not independent reviewer qualification or automatic payroll costs.

Cost observations are USD amounts for an exact 1–30 whole-day window and scope.
Four components are mandatory: INFRASTRUCTURE (compute, database, storage, transfer
and other hosting overhead), PROVIDER, REVIEW and SUPPORT. Each needs an offline
evidence reference code; no invoice content, credential or automatic price lookup
is accepted. Verified zero requires an explicit zero observation. Missing any
component keeps total and every per-unit cost null. Synthetic/observed components
cannot be mixed. Costs do not roll up mismatched windows or invent daily allocations.

Allocated whole-window cost is reported per capture, all analyses (including
failed/reprocessed work), completed loop and comparable evaluation. Asset-linked
match/evaluation dataset kind supplies the denominator scope. Records without
known scope are not attributed to either. Deleted evidence is excluded, leaving
costs conservative. Loops require completed practice, verified trials and measured
baseline/follow-up. Only the current evaluation revision counts, once per plan;
inconclusive/no-change/deterioration comparisons count alongside improvement.
NOT_COMPARABLE and INSUFFICIENT_EXPOSURE do not inflate comparable yield. A zero
denominator leaves unit cost null. This is allocated cost, not marginal pricing or
invoice reconciliation; observed entry alone does not qualify deployed economics.

The [economics protocol](../operations/economics-protocol.md) specifies actual offer,
payment, refund and recurring-cost evidence. There is no billing implementation,
actual willingness-to-pay result, revenue assumption or approved price in M17.

## Retention, deletion and restore

`operations_snapshot --prune` removes response/time measurements older than 30
days, old released attempts of settled budgets, and old closed budget rows. It
preserves every open hold and current-day charge. Cost observations are aggregate
nonplayer financial evidence with operator-controlled retention; jurisdiction and
production financial retention policy remain unapproved.

Account export includes own metrics, budget rows and own operator time. Asset
deletion erases its attempt measurements; account deletion also erases operator
time. Small numeric run reservations/charges remain while required for safety and
are pruned later. Deleted workers cannot recreate erased measurements. Signed
deletion replay invokes the same services. Restore quarantine prevents processing
until controls and physical capacity are reconciled. Backup-era budgets do not
establish post-backup spend: a hosted restart requires current independent quota
history or a conservative hold through the next UTC day. No production restore
or billing capability is enabled by this module.
