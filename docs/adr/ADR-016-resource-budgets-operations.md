# ADR-016: Retain resource budgets through physical stop and measure cost by evidence scope

Date: 2026-10-02. Status: accepted local engineering; deployed qualification and
commercial/SLO decisions pending. Requirements: M17.01–M17.07, M14.05, M15.06.

M16's physical execution caps and M15's byte/job admission limit concurrent work,
but do not settle per-day processing/media time or expose operational coverage.
Retries, ambiguous launches, midnight rollover and cancellation make early refunds
unsafe. Small synthetic timings cannot establish total recurring economics.

Use a durable one-to-one RunBudget with conservative media/deadline reservations,
policy snapshots and owner-before-global locking. Hold until terminal state and
physical stop, charge unknown attempts at their full deadline, and settle once on
the UTC settlement day. Preserve storage/physical/request caps and bound reanalysis.
Do not pretend these application budgets guarantee all cloud spend.

Record fenced allowlisted attempt measurements, fixed-label response aggregates
and explicit scoped human work/cost observations. Keep missing inputs null and
synthetic/observed measurements separate. Staff-only aggregates, own usage/export,
deletion/retention, fixed-code logs, proposed objectives, CLI alerts and runbooks
provide local operational tools. Current comparison revisions count nonpositive
results and cannot inflate comparable yield with earlier favorable revisions.

Consequences: conservative reservations may reject work that would fit using a
perfect estimate; failed or deleted unmeasured attempts still consume safe quotas.
Actual hosted costs, independent alert delivery, operator response, SLO approval,
representative content and actual willingness to pay remain release prerequisites.
Restore requires current quota reconciliation as well as signed deletion controls.
See [the contract](../architecture/operations-economics.md) and
[qualification](../experiment-results/m17-operations.md).
