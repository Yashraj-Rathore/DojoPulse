# Evaluation model

EvaluationPlan freezes metric/situation version, baseline event IDs and content hashes,
knowledge/detector compatibility, target context, baseline/follow-up boundaries, practice
requirement, minimum known outcomes and sessions, coverage tolerance, exclusions, stop rules,
and minimum meaningful change. A new definition means a new plan. Never overwrite a plan.

An ImprovementEvaluation revision freezes follow-up IDs and hashes, baseline/follow-up counts,
eligible unknowns, exclusions, detector/knowledge versions, observation duration, opportunity
frequency, practice exposure, coverage, raw change, interval method and result. Frequencies
need observed duration; absent duration stays unknown. Prior revisions remain auditable.

Decision order: deleted evidence/version/context/chronology incompatibility -> NOT_COMPARABLE;
insufficient verified practice/counts/sessions -> INSUFFICIENT_EXPOSURE; excessive differential
coverage -> NOT_COMPARABLE; otherwise use a session-cluster bootstrap interval for change.
Interval wholly above +delta: OBSERVED_IMPROVEMENT; wholly below -delta: OBSERVED_DETERIORATION;
wholly inside [-delta,+delta]: NO_MEANINGFUL_CHANGE; otherwise INCONCLUSIVE.

The change interval envelopes the session bootstrap with a difference of simultaneous 97.5%
Beta intervals, providing a conservative finite-sample floor when bootstrap variance collapses.
This floor still does not establish a generative model of all session dependence.
Bootstrap resamples sessions independently within each period, retaining all events within a
selected session. Seed and method version are pinned. This does not remove selection bias,
confounding or few-cluster limitations. Minimum 5 sessions/period is an engineering floor,
not a guarantee of power. Default 40 known outcomes/period is exploratory; power the later
comparative study using observed variance. Freeze target and analysis before seeing follow-up.

The runtime checks complete selected membership; missing/deleted IDs cannot silently shrink
denominators. No user-supplied numerator, verified flag or result status is accepted by the API.

Implementation policy /1 pins the capture profile, exclusions and fixed-window stop rules.
Real plans must be frozen before future follow-up starts; counted real practice must occur
after plan creation. Evaluation waits until the fixed window ends. Selection includes every
reviewed row of a chosen capture, and real follow-up includes every recorded target row in
that window. Complete play/session logging remains an operator responsibility: software cannot
detect unsubmitted recordings. Both eligibility coverage and outcome coverage must be stable.
Practice IDs/hashes are stored with the result; deleting any counted practice invalidates it.
