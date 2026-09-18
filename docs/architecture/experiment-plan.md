# Experiment plan

All thresholds are preregistered proposals. No real-game experiments have run. Between success
and failure thresholds: narrow once, collect evidence, then explicitly decide; never silently pass.

| ID | Hypothesis / dataset / method | Success | Failure / response |
|---|---|---|---|
| G1 | Target human-observable; 20 consented captures, critical dual review | >=90% target windows resolvable | >20% unobservable: narrow target/profile |
| G2 | Templates/OCR plus rules suffice; independent sessions, >=300 accepted critical predictions plus negatives | precision >=.98, one-sided 95% lower >=.95, recall >=.60, both success/failure slices | precision <.95 at recall >=.50 after two iterations: stop automation |
| G3 | Capture workflow accepted; 15-20 users, unaided capture | >=80% valid; median setup <=10 min | <50% after revision: change ingestion |
| G4 | Practice measurable; 10 players x >=40 attempts, adjudicated truth | >=90% coverage, >=95% outcome agreement | <80% coverage or systematic bias: withhold verified practice |
| G5 | Natural target frequency supports comparison; 20 prospective histories, 4 weeks | >=60% have exploratory baseline/follow-up evidence | <30%: choose backup, do not manufacture exposure |
| G6 | Complete loop comparable/useful; frozen plan and prospective later matches | >=60% evaluable; report inconclusive results; compare native/usual workflow | <30% comparable or no additional utility: revise product |

Results must include hypothesis, dataset revision, method, metric, threshold, actual result,
decision, exclusions, reviewer time/cost and source artifact hashes. Store under experiment-results.
No experiment can promote a detector based on the same captures used to tune it.

Comparative protocol: record usual practice first; assign native replay tips/usual practice vs
the single structured drill using an opt-in delayed-start pilot. Equalize observation windows,
record adherence and concurrent coaching; blind outcome reviewers where possible. Select target
before follow-up. This pilot estimates feasibility, not causal efficacy. Power a later trial.

Economics: cost/capture, completed analysis, complete loop and comparable evaluation include
review minutes, failed/reprocessed work, storage and transfer. Target <=25% median and <=40%
p90 recurring COGS/net revenue; validate actual payment rather than hypothetical willingness.
