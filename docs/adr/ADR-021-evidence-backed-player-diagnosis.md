# ADR-021: Evidence-backed player diagnosis and reviewed priorities

Date: 2026-10-05. Status: accepted for local engineering. Architecture: 2.13.0.

Frozen comparison baselines already store descriptive summaries, but a baseline is
not independently a diagnosis. M10 adds a bounded, read-only player-model projection
over current canonical publications. It shares neither provider schemas nor detector
transport logic. Original matches, events and frozen evaluations remain immutable.

Group observations by situation, metric, player context, exact captured build,
knowledge version/hash, detector, platform and real/synthetic scope. Do not combine
incompatible groups or rank them against one another. Preserve outcome/eligibility
unknowns and disclose missing publications and unavailable evidence. Use all available
candidate windows in the selected scope; forbid favorable outcome/eligibility filters.

Version the proposed diagnosis thresholds and expose their hash. A descriptive failure
pattern requires sufficient known outcomes, multiple distinct reviewed sessions,
coverage and independent reviewer agreement. Real diagnosis remains gated on actual
expert and player-utility qualification, regardless of counts or approved fixture flags.

Priority assessment is an optional part of an immutable governed drill version.
Two independent M07 reviewers therefore review the exact relative value, trainability
and rationale alongside its sources/dependencies. A new assessment needs a new version;
withdrawal immediately removes authority. Missing, ambiguous, malformed or out-of-scope
assessments have no default values or score. Legacy approvals are synthetic fixtures only.

The research score multiplies eligible candidate-window share, reviewed relative value,
the conservative failure interval lower bound times raw reviewer agreement, and reviewed
trainability. It is an explanatory research policy, not a calibrated accuracy, skill,
damage, expected benefit or commercial outcome. Bound ranked priorities to three within
one compatible profile; the current release scope remains one situation (M21 unchanged).

Serialize reads with owner/capacity locks used by consent, shared review withdrawal and
publication. Memoize identical source grants only within that transaction. Keep no new
persistent diagnosis cache, so deletion, expiry, reanalysis, restore erasure and consent
changes take effect on the next authorized read. The UI clears cards on failed reads,
polls while visible and exposes private timestamp links and provenance hashes.

Recorded match results and monthly gameplay counts are separate descriptive views.
Neither establishes causal improvement; frozen M12 evaluation remains the comparison
mechanism. Actual expert agreement, utility/usability, occurrence/selection bias and
hosted performance remain release requirements.

See [player-model contract](../architecture/player-model.md),
[M10 qualification](../experiment-results/m10-player-model.md) and
[product tracker](../../PRODUCT_PROGRESS.md).
