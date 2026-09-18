# Player statistics

Binary outcome uses Beta(1 + successes, 1 + failures), with observed k/n and 95% credible
interval. Unknown outcomes are excluded from n and separately shown. Eligible outcome coverage
is known outcomes / all known-eligible opportunities. Unknown eligibility is separately reported.
This coverage is NOT detector recall; only external labels establish recall.

Categorical actions use declared Dirichlet pseudocounts and mutually exclusive first actions.
No neural embedding, arbitrary skill score, or rank-derived competence label. Context starts
with player, own/opponent character, situation and compatible build. Side/resources are recorded
but not multiplied into sparse buckets before data supports them.

Independent-event credible intervals are descriptive. Match-transfer inference uses paired
period/session blocks, enough independent sessions and a prespecified meaningful difference.
Current estimates are projections from selected contributions. Reanalysis replaces contributions.
