# Event and opportunity contract

Observation: what a parser/reviewer saw, at source PTS, with uncertainty and provenance.
Event: reconciled interpretation of observations. Conclusion: rule result over events and
pinned knowledge. Confidence is null until calibrated; template similarity is not probability.

Opportunity identity is `(match, situation version, played opportunity key)` independent
of analysis revision. Current revision selection prevents double-counting. Distinct replay
passes do not create played opportunities. Human annotations retain source hash and versions.

Eligibility: ELIGIBLE, INELIGIBLE, UNKNOWN. Outcome: SUCCESS, FAILURE, UNKNOWN.
SUCCESS or FAILURE requires ELIGIBLE, complete required evidence and a verified outcome path.
Missing attack or absent PUNISH text alone never establishes failure. Reasons accompany abstention.

Retain actor ID, match mode, game build, knowledge, detector, metric and situation versions,
evidence IDs, source hash, start/end microseconds and timing uncertainty. Use integer source
times; decode-frame index is navigation, not game simulation time. A no-action outcome is
different from an unobserved window. All inference remains context-specific.
