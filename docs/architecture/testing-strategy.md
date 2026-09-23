# Testing strategy

Pure rules: absent evidence, reach, spacing, stance, resources, wall and timing ambiguity.
Statistics: unknown exclusion, Beta/Dirichlet estimates, session clustering, zero denominators.
Evaluation: immutable membership, chronology, definitions, insufficient exposure and all statuses.
Persistence/API: owner isolation, invalid nested refs, immutable plans, duplicate publication,
reanalysis replacement, deleted evidence invalidation and job leases.
Pipeline: generated non-game videos, malformed input, oversized declarations, timestamp gaps,
resource bounds, sample extraction, template temporal deduplication and strict sidecars.
Dataset: disjoint source/player/session groups, two reviewers, adjudication and consent.
Frontend: typecheck, lint, production build and a thin loop smoke test.

Real golden regression is a separate NOT_RUN gate until private manifest data exists. Never
rename synthetic fixture accuracy as gameplay precision. Dataset evaluator reports per-outcome
precision/recall/F1, abstention, coverage and time error with one-to-one matching.
CI runs PostgreSQL-backed tests; SQLite fallback does not validate locking/concurrency semantics.

## Ingestion contract checks

tests/test_ingestion_contracts.py uses synthetic Wavu-shaped metadata with deliberately large
integer IDs. It checks case/namespace preservation, ambiguous names, unknown versions/results,
metadata/evidence separation, provider/purpose gates, Retry-After and bounded cursor overlap.
No test calls an external provider. Relational import tests now cover source-record deduplication,
identity revocation, metadata-only deletion, migration preservation and concurrent fencing.
API tests exercise signed candidate confirmation, owner isolation, CSRF, provider gates,
worker quarantine/retries, paging and conservative coverage. Browser tests exercise linking,
consent, imports, removal, empty lookup and mobile incomplete/expired evidence states using
mocked HTTP responses. PostgreSQL API tests separately execute the real domain/worker path.
Live transport, shared provider quotas and replay decoding still require later integration tests.
