# M17 operations qualification

2026-10-02. Local synthetic engineering only. M17.01–M17.07, M14.05,
M15.06, M16.05 and M19.02. No real provider endpoint, gameplay recognition,
cloud provisioning, payment, invoice, production SLO or alert delivery was enabled.

## Delivered engineering

- Durable RunBudget reservation/policy snapshot/settlement, daily media/time and
  reanalysis caps, retry exhaustion, optional-work pause and upload admission preview.
- Fenced attempt queue/wall/CPU/RAM/bytes measurements; fixed-label response metrics,
  fixed-code framework/worker logs and missing-measurement coverage.
- Staff-only monitoring UI/API, own usage, bounded snapshot/CLI alerts, time/cost
  input idempotency, scoped null-safe allocated unit cost and current evaluation
  denominators that retain inconclusive/no-change/deterioration results.
- Owner export and deletion, retention without early refunds, budget rollback guard,
  indexed history pages, operations/support/patch procedures and actual-offer protocol.
- Migrations 0010–0012 prepared/applied locally. Architecture 2.8.0, ADR-016/D027 and
  authoritative/historical progress tracking updated in the same implementation.

## Actual checks so far

The first full PostgreSQL regression checkpoint passed **274 tests in 101.37s**,
with seven Docker checks skipped locally. Later instrumentation/logging/cost
denominator and mobile changes require final checks; those are recorded below
when completed, not inferred from this checkpoint.

The corrected browser checkpoint passed **17 Edge journeys in 21.4s**. Three new
journeys cover mobile operations, unknown cost/proposed objectives, denied access,
CSRF and same-key time-write retry. Initial lint findings were corrected without
disabling rules; two selectors were scoped to `main` to distinguish the product
alert from Next's route announcer. A later mobile card layout awaits final check.
Screenshot inspection confirmed readable layout, with the objective state column
subsequently made visible on mobile without horizontal scrolling.

The synthetic load scenario generated **2,250 metadata matches across nine owners**;
queried owner-only pages of 100/100/50 rows; observed 22/16/16 SQL statements and
approximately 31/32/16ms at the initial local checkpoint. The PostgreSQL plan used
`history_owner_played`. It filled 32 pending analyses, refused a 33rd and allowed
only two active slots on distinct owners. Eight controlled retryable dispatch
failures reached attention; stale/cancelled work retained slots until explicit
authoritative stop. Each reservation fixture declared 512MiB, without writing or
decoding those files. Timing is machine/test-specific, not an approved service
objective or estimate of video throughput. CI retains `reports/m17-load.json`.

The separate existing Docker job must check its **600s/512MiB actual media fixture**
and six other isolation tests on the M17 commit. Local Docker checks are skipped,
not counted as successful here. M16's earlier CI receipt remains historical evidence.

Final local validation passed **281 PostgreSQL/Python tests in 84.75s**, seven
local Docker skips, and **17 Edge journeys in 21.4s** after the mobile layout fix.
Native PostgreSQL 17 dump/restore/forward-reverse-forward/controls-before-reads/
repeated replay passed again after migration 0012. Ruff check/format, mypy (23
sources), Django system/migration checks, frontend lint/build/types and diff check
passed. Final load pages measured approximately 32/32/31ms with the same 22/16/16
statement counts; these are synthetic machine-specific observations.

Automatic approval review rejected rolling back/reapplying the existing local
M17 schema because it could drop ledger/metric records. A safe forward migration
preserves all rows, sets unmeasured historical dates to null and refuses unsafe
reverse conversion. It applied successfully and passed explicit ledger/date tests.
No destructive reset was performed. Main publication and six remote jobs remain
pending; the completed publication/CI receipt will be appended.

Final permission follow-up rechecks the current staff flag under the owner lock,
including a stale authenticated user whose staff permission was revoked concurrently.
All **26 operations tests passed in 17.31s** after correcting the loader call;
static/diff checks and documentation links passed. Player requests now show DRF
budget/rate-limit detail rather than hiding the admission reason. Remote CI will
run the complete final 282-test backend collection and all browser journeys.

## Acceptance that remains external

M17 stays PARTIAL for its whole-product exit. Proposed p95 queue ≤120s, processing
≤390s, technical completion ≥95% and observed response availability ≥99% need
approved workload/window/error-budget decisions and representative captures/hosting.
At least 20 observations is only a reporting guard, not statistical or release proof.

Actual hosted compute/storage/transfer/provider/reviewer/support amounts remain
unknown. Financial observations are operator-entered exact-window evidence,
not automatic invoice reconciliation. No actual willingness-to-pay/payment/renewal
study has run. Named primary/deputy, external alert scheduler/missing-heartbeat
handling, support-response exercise, production retention and post-backup quota
reconciliation are not qualified. Provider permission/schema, real-game/reviewer
G1–G6, equivalent hosted media isolation and source-integrity review remain gates.
