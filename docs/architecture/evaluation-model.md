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

Bootstrap resamples sessions independently within each period, retaining all events within a
selected session. Seed and method version are pinned. This does not remove selection bias,
confounding or few-cluster limitations. Minimum 5 sessions/period is an engineering floor,
not a guarantee of power. Default 40 known outcomes/period is exploratory; power the later
comparative study using observed variance. Freeze target and analysis before seeing follow-up.

The runtime checks complete selected membership; missing/deleted IDs cannot silently shrink
denominators. No user-supplied numerator, verified flag or result status is accepted by the API.
