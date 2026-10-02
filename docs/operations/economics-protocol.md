# Recurring economics and actual-offer protocol

2026-10-02; M17.04/M17.07; prepared protocol, no actual commercial experiment run.
The [experiment plan](../architecture/experiment-plan.md) remains controlling:
proposed recurring COGS/net-revenue targets are ≤25% median and ≤40% p90, not results.

Before the pilot, record the permitted scope, actual offer/price/access duration,
currency/tax/payment/refund terms, recruitment/consent, reviewer/support ownership,
cost allocation policy and continue/narrow/stop thresholds. Obtain product/legal
approval for an actual offer; do not collect payment through an unreviewed endpoint.
No speculative subscription amount is configured by this implementation.

For each prespecified window, reconcile compute/database/storage/transfer and
hosting overhead, provider fees, reviewer time × observed rate and support time ×
observed rate. Use actual permitted receipts, including free-tier/zero amounts
explicitly verified. Separate one-time development/research/annotation costs from
recurring service COGS without hiding their amounts. Record currency conversion
source/date when applicable. The dashboard accepts already measured USD component
amounts; it does not determine tax or perform currency conversion.

Record all eligible offers, declines, payments, failed payments, refunds and
repeat use/renewals. A stated willingness to pay is not payment evidence. Report
conversion and retention with uncertainty and all eligible denominators, including
negative/no-change/inconclusive/noncomparable outcomes. Pilot samples do not prove
population economics or causal efficacy. Keep player details outside aggregate
financial telemetry and apply the approved consent/retention process.

Use [the operations contract](../architecture/operations-economics.md) for exact
window/scope cost inputs and units. Report costs per capture, all analysis attempts
including failure/reanalysis overhead, completed loop and comparable evaluation.
Investigate missing data rather than imputing zero. A complete zero-cost window
with zero unit denominator still has unknown unit cost. Report p50/p90 recurring
COGS/net revenue only from enough observed independent user/windows; zero net
revenue is undefined, never treated as zero COGS share.

Store a dated restricted evidence receipt and an aggregate result under
`docs/experiment-results`. Explicitly decide continue, narrow once or stop under
the agreed targets. M17.04 remains dependent on actual costs and M17.07 remains
dependent on an approved offer and real payment/repeat-use evidence. No result,
participant, invoice, approval or commercial readiness is asserted here.
